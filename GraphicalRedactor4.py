import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import numpy as np
import math

CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600
DEFAULT_FILENAME = 'cube.txt'
SELECTION_THRESHOLD = 7
SELECTED_VERTEX_COLOR = 'red'
VERTEX_DRAW_RADIUS = 3

def translation_matrix(tx, ty, tz):
    """Матрица перемещения"""
    return np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ])

def rotation_matrix_x(angle_rad):
    """Матрица поворота вокруг оси X"""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return np.array([
        [1, 0, 0, 0],
        [0, c, -s, 0],
        [0, s, c, 0],
        [0, 0, 0, 1]
    ])

def rotation_matrix_y(angle_rad):
    """Матрица поворота вокруг оси Y"""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return np.array([
        [c, 0, s, 0],
        [0, 1, 0, 0],
        [-s, 0, c, 0],
        [0, 0, 0, 1]
    ])

def rotation_matrix_z(angle_rad):
    """Матрица поворота вокруг оси Z"""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return np.array([
        [c, -s, 0, 0],
        [s, c, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

def scaling_matrix(sx, sy, sz):
    """Матрица масштабирования"""
    return np.array([
        [sx, 0, 0, 0],
        [0, sy, 0, 0],
        [0, 0, sz, 0],
        [0, 0, 0, 1]
    ])

def reflection_matrix_xy():
    """Матрица отражения относительно плоскости XY"""
    return np.array([
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0,-1, 0],
        [0, 0, 0, 1]
    ])

def reflection_matrix_xz():
    """Матрица отражения относительно плоскости XZ"""
    return np.array([
        [1, 0, 0, 0],
        [0,-1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
    ])

def reflection_matrix_yz():
    """Матрица отражения относительно плоскости YZ"""
    return np.array([
        [-1, 0, 0, 0],
        [ 0, 1, 0, 0],
        [ 0, 0, 1, 0],
        [ 0, 0, 0, 1]
    ])

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Лабораторная работа: 3D Преобразования")
        self.geometry(f"{CANVAS_WIDTH+250}x{CANVAS_HEIGHT+50}")

        self.original_vertices = []
        self.current_vertices = []
        self.edges = []
        self.filename = DEFAULT_FILENAME
        self.selected_vertices_indices = set()
        self.projected_points_cache = []

        self.projection_type = tk.StringVar(value="orthographic")
        self.perspective_d = 5.0
        self.center_x = CANVAS_WIDTH / 2
        self.center_y = CANVAS_HEIGHT / 2
        self.scale_factor = 100

        self.create_widgets()
        self.load_object(self.filename)
        self.bind_keys()
        self.bind_mouse()

    def create_widgets(self):
        self.canvas = tk.Canvas(self, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg='white')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        control_frame = tk.Frame(self, width=250, padx=10, pady=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)

        load_button = tk.Button(control_frame, text="Загрузить объект", command=self.browse_file)
        load_button.pack(pady=5, fill=tk.X)
        self.filename_label = tk.Label(control_frame, text=f"Файл: {self.filename}", wraplength=230)
        self.filename_label.pack(pady=2)

        reset_button = tk.Button(control_frame, text="Сбросить вид", command=self.reset_view)
        reset_button.pack(pady=5, fill=tk.X)

        scale_selected_button = tk.Button(control_frame, text="Масштабировать выбранное", command=self.ask_scale_selected)
        scale_selected_button.pack(pady=5, fill=tk.X)
        clear_selection_button = tk.Button(control_frame, text="Снять выделение", command=self.clear_selection)
        clear_selection_button.pack(pady=5, fill=tk.X)


        proj_label = tk.Label(control_frame, text="Проекция:")
        proj_label.pack(pady=(10, 0))
        ortho_radio = tk.Radiobutton(control_frame, text="Ортографическая", variable=self.projection_type, value="orthographic", command=self.redraw_object)
        ortho_radio.pack(anchor=tk.W)
        persp_radio = tk.Radiobutton(control_frame, text="Перспективная", variable=self.projection_type, value="perspective", command=self.redraw_object)
        persp_radio.pack(anchor=tk.W)

        controls_label = tk.Label(control_frame, text="Управление:", font=('Arial', 10, 'bold'))
        controls_label.pack(pady=(15, 5))

        controls_text = (
            "Клавиатура:\n"
            " Перемещение: W/A/S/D (XY)\n"
            " Поворот: Стрелки (XY), PgUp/PgDn (Z)\n"
            " Общий масштаб: + / -\n"
            " Отражение: 1 (XY), 2 (XZ), 3 (YZ)\n"
            " Сброс: R\n\n"
            "Мышь (на холсте):\n"
            " ЛКМ: Выбрать/снять выбор вершины\n"
        )
        controls_info = tk.Label(control_frame, text=controls_text, justify=tk.LEFT, anchor=tk.NW)
        controls_info.pack(fill=tk.X)


    def bind_keys(self):
        self.bind("<KeyPress>", self.handle_keypress)
        self.focus_set()

    def bind_mouse(self):
        self.canvas.bind("<Button-1>", self.handle_canvas_click)

    def handle_keypress(self, event):
        key = event.keysym
        translate_step = 10 / self.scale_factor
        rotate_step = math.radians(5)
        scale_step = 1.1

        transform_matrix = np.identity(4)

        if key == 'w':
            transform_matrix = translation_matrix(0, -translate_step, 0)
        elif key == 's':
            transform_matrix = translation_matrix(0, translate_step, 0)
        elif key == 'a':
            transform_matrix = translation_matrix(-translate_step, 0, 0)
        elif key == 'd':
            transform_matrix = translation_matrix(translate_step, 0, 0)
        elif key == 'q':
            transform_matrix = translation_matrix(0, 0, translate_step)
        elif key == 'e':
            transform_matrix = translation_matrix(0, 0, -translate_step)
        elif key == 'Up': transform_matrix = rotation_matrix_x(-rotate_step)
        elif key == 'Down': transform_matrix = rotation_matrix_x(rotate_step)
        elif key == 'Left': transform_matrix = rotation_matrix_y(-rotate_step)
        elif key == 'Right': transform_matrix = rotation_matrix_y(rotate_step)
        elif key == 'Prior': transform_matrix = rotation_matrix_z(-rotate_step)
        elif key == 'Next': transform_matrix = rotation_matrix_z(rotate_step)
        elif key == 'plus' or key == 'equal':
             transform_matrix = scaling_matrix(scale_step, scale_step, scale_step)
        elif key == 'minus':
             transform_matrix = scaling_matrix(1/scale_step, 1/scale_step, 1/scale_step)
        elif key == '1': transform_matrix = reflection_matrix_xy()
        elif key == '2': transform_matrix = reflection_matrix_xz()
        elif key == '3': transform_matrix = reflection_matrix_yz()
        elif key == 'r' or key == 'R':
            self.reset_view()
            return

        if not np.array_equal(transform_matrix, np.identity(4)):
            self.apply_transformation(transform_matrix)


    def handle_canvas_click(self, event):
        if not self.projected_points_cache:
            return

        click_x, click_y = event.x, event.y
        min_dist_sq = (SELECTION_THRESHOLD + 1)**2
        found_index = -1

        for i, point in enumerate(self.projected_points_cache):
            if point is not None:
                px, py = point
                dist_sq = (click_x - px)**2 + (click_y - py)**2
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    found_index = i

        if found_index != -1:
            if found_index in self.selected_vertices_indices:
                self.selected_vertices_indices.remove(found_index)
            else:
                self.selected_vertices_indices.add(found_index)
            self.redraw_object()


    def clear_selection(self):
        if self.selected_vertices_indices:
            self.selected_vertices_indices.clear()
            self.redraw_object()

    def apply_transformation(self, matrix):
        if not self.current_vertices:
            return

        if not isinstance(matrix, np.ndarray) or matrix.shape != (4, 4):
            print(
                f"Ошибка: Неверный формат матрицы в apply_transformation: {type(matrix)}, shape {getattr(matrix, 'shape', 'N/A')}")
            return

        new_vertices_homogeneous = []
        for i, vertex_h in enumerate(self.current_vertices):
            if not isinstance(vertex_h, np.ndarray) or vertex_h.shape != (4, 1):
                print(
                    f"Ошибка: Неверный формат вершины {i} в apply_transformation: {type(vertex_h)}, shape {getattr(vertex_h, 'shape', 'N/A')}")
                try:
                    current_v = np.array(vertex_h).reshape((4, 1))
                except:
                    print(" -> Не удалось преобразовать вершину. Пропускаем.")
                    new_vertices_homogeneous.append(vertex_h)
                    continue
            else:
                current_v = vertex_h

            try:
                new_vertex_h = matrix @ current_v
                new_vertices_homogeneous.append(new_vertex_h)
            except Exception as e:
                print(f"Ошибка при умножении матрицы на вершину {i}: {e}")
                print(f"Matrix:\n{matrix}")
                print(f"Vertex:\n{current_v}")
                new_vertices_homogeneous.append(current_v)

        self.current_vertices = new_vertices_homogeneous
        self.redraw_object()


    def load_object(self, filename):
        try:
            self.original_vertices = []
            self.edges = []
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if parts[0] == 'v' and len(parts) == 4:
                        try:
                            vertex = [float(p) for p in parts[1:]]
                            self.original_vertices.append(vertex)
                        except ValueError:
                            print(f"Предупреждение: Неверный формат вершины в строке: {line}")
                    elif parts[0] == 'e' and len(parts) == 3:
                        try:
                            idx1 = int(parts[1]) - 1
                            idx2 = int(parts[2]) - 1
                            self.edges.append((idx1, idx2))
                        except (ValueError, IndexError):
                             print(f"Предупреждение: Неверный формат ребра или индекса в строке: {line}")
                    else:
                        print(f"Предупреждение: Неизвестный или некорректный формат строки: {line}")


            if not self.original_vertices:
                 messagebox.showerror("Ошибка загрузки", f"Не найдено вершин в файле {filename}")
                 return False

            self.filename = filename
            self.filename_label.config(text=f"Файл: {filename.split('/')[-1]}")
            self.reset_view()
            return True
        except FileNotFoundError:
            messagebox.showerror("Ошибка", f"Файл не найден: {filename}")
            return False
        except Exception as e:
            messagebox.showerror("Ошибка загрузки", f"Произошла ошибка при чтении файла:\n{e}")
            return False


    def browse_file(self):
        filepath = filedialog.askopenfilename(
            title="Выберите файл объекта (.txt)",
            filetypes=(("Текстовые файлы", "*.txt"), ("Все файлы", "*.*"))
        )
        if filepath:
            self.load_object(filepath)


    def reset_view(self):
        if not self.original_vertices:
            return
        self.current_vertices = []
        for v in self.original_vertices:
            self.current_vertices.append(np.array([[v[0]], [v[1]], [v[2]], [1.0]]))
        self.selected_vertices_indices.clear()
        self.redraw_object()


    def project_vertex(self, vertex_h):
        v = vertex_h.flatten()
        x, y, z, w = v[0], v[1], v[2], v[3]

        if abs(w) < 1e-6: w = 1e-6

        x_dec = x / w
        y_dec = y / w
        z_dec = z / w

        if self.projection_type.get() == "perspective":
            if z_dec <= 0.1:
                return None

            d_scaled = self.perspective_d

            x_screen = x_dec * d_scaled / z_dec
            y_screen = y_dec * d_scaled / z_dec

            x_screen *= self.scale_factor
            y_screen *= self.scale_factor

        else:
             x_screen = x_dec * self.scale_factor
             y_screen = y_dec * self.scale_factor

        canvas_x = self.center_x + x_screen
        canvas_y = self.center_y - y_screen

        return int(canvas_x), int(canvas_y)


    def redraw_object(self):
        self.canvas.delete("all")
        if not self.current_vertices:
            return

        self.projected_points_cache = [self.project_vertex(v) for v in self.current_vertices]

        for edge in self.edges:
            idx1, idx2 = edge
            if 0 <= idx1 < len(self.projected_points_cache) and 0 <= idx2 < len(self.projected_points_cache):
                p1 = self.projected_points_cache[idx1]
                p2 = self.projected_points_cache[idx2]
                if p1 is not None and p2 is not None:
                    self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill='black', width=1)

        for i, p in enumerate(self.projected_points_cache):
            if p is not None:
                x, y = p
                radius = VERTEX_DRAW_RADIUS
                color = 'black'
                if i in self.selected_vertices_indices:
                    color = SELECTED_VERTEX_COLOR
                    radius += 1

                self.canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill=color, outline=color
                )


    def ask_scale_selected(self):
        if not self.selected_vertices_indices:
            messagebox.showinfo("Масштабирование", "Нет выбранных вершин для масштабирования.")
            return

        try:
            factors = simpledialog.askstring("Масштабирование выбранного",
                                             "Введите sx sy sz (через пробел):",
                                             initialvalue="1.1 1.1 1.1")
            if factors:
                sx, sy, sz = map(float, factors.split())
                if sx == 0: sx = 1e-6
                if sy == 0: sy = 1e-6
                if sz == 0: sz = 1e-6

                self.scale_selected_vertices(sx, sy, sz)

        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверный формат: {e}")


    def scale_selected_vertices(self, sx, sy, sz):
        if not self.selected_vertices_indices:
            return

        selected_coords = []
        for i in self.selected_vertices_indices:
             v = self.current_vertices[i].flatten()
             selected_coords.append(v[:3])

        if not selected_coords:
            return

        center_mass = np.mean(np.array(selected_coords), axis=0)
        cx, cy, cz = center_mass[0], center_mass[1], center_mass[2]

        to_origin_matrix = translation_matrix(-cx, -cy, -cz)
        scale_matrix = scaling_matrix(sx, sy, sz)
        from_origin_matrix = translation_matrix(cx, cy, cz)

        transform_matrix = from_origin_matrix @ scale_matrix @ to_origin_matrix

        for i in self.selected_vertices_indices:
            self.current_vertices[i] = transform_matrix @ self.current_vertices[i]

        self.redraw_object()


    def ask_translate(self):
        try:
            coords = simpledialog.askstring("Перемещение", "Введите tx ty tz (через пробел):")
            if coords:
                tx, ty, tz = map(float, coords.split())
                matrix = translation_matrix(tx, ty, tz)
                self.apply_transformation(matrix)
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверный формат: {e}")

    def ask_rotate(self):
         try:
            params = simpledialog.askstring("Поворот", "Введите ось (x, y, z) и угол (градусы):")
            if params:
                axis, angle_deg = params.split()
                angle_rad = math.radians(float(angle_deg))
                axis = axis.lower()
                if axis == 'x': matrix = rotation_matrix_x(angle_rad)
                elif axis == 'y': matrix = rotation_matrix_y(angle_rad)
                elif axis == 'z': matrix = rotation_matrix_z(angle_rad)
                else: raise ValueError("Неверная ось")
                self.apply_transformation(matrix)
         except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверный формат: {e}")

    def ask_scale(self):
        try:
            factors = simpledialog.askstring("Общее Масштабирование", "Введите sx sy sz (через пробел):")
            if factors:
                sx, sy, sz = map(float, factors.split())
                if sx == 0: sx = 1e-6
                if sy == 0: sy = 1e-6
                if sz == 0: sz = 1e-6
                matrix = scaling_matrix(sx, sy, sz)
                self.apply_transformation(matrix)
        except Exception as e:
            messagebox.showerror("Ошибка ввода", f"Неверный формат: {e}")


if __name__ == "__main__":
    app = Application()
    app.mainloop()