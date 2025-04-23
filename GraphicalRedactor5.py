import tkinter as tk
from tkinter import messagebox, Menu, Frame, Button, Label, simpledialog
import math
import sys

def orientation(p, q, r):
    if p is None or q is None or r is None: return 0
    val = (q[1] - p[1]) * (r[0] - q[0]) - \
          (q[0] - p[0]) * (r[1] - q[1])
    if val == 0: return 0
    return 1 if val > 0 else 2

def cross_product_z(p1, p2, p3):
    if p1 is None or p2 is None or p3 is None: return 0
    return (p2[0] - p1[0]) * (p3[1] - p2[1]) - (p2[1] - p1[1]) * (p3[0] - p2[0])

def dist_sq(p1, p2):
    if p1 is None or p2 is None: return 0
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def get_vector(p1, p2):
    if p1 is None or p2 is None: return (0, 0)
    return (p2[0] - p1[0], p2[1] - p1[1])

def normalize_vector(v):
    mag = math.sqrt(v[0]**2 + v[1]**2)
    if mag == 0: return (0, 0)
    return (v[0] / mag, v[1] / mag)

class PolygonEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Редактор Полигонов")
        self.master.geometry("800x700")

        self.points = []
        self.polygon_id = None
        self.point_ids = []
        self.hull_id = None
        self.normal_ids = []
        self.line_points = []
        self.line_id = None
        self.intersection_point_ids = []

        self.current_mode = tk.StringVar(value="draw_polygon")
        self.selected_hull_method = tk.StringVar(value="graham")

        self.mode_translations = {
            "draw_polygon": "Рисование Полигона",
            "draw_line": "Рисование Линии",
            "point_test": "Тест Точки в Полигоне"
        }

        toolbar = Frame(master, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.status_label = Label(master, text="Режим: Рисование Полигона", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(master, bg="white", width=780, height=600)
        self.canvas.pack(pady=5, expand=True, fill=tk.BOTH)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

        menubar = Menu(master)
        master.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label="Очистить Холст", command=self.clear_canvas)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=master.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        mode_menu = Menu(menubar, tearoff=0)
        mode_menu.add_radiobutton(label="Рисование Полигона", variable=self.current_mode, value="draw_polygon", command=self.update_status)
        mode_menu.add_radiobutton(label="Рисование Линии (Лаб 1)", variable=self.current_mode, value="draw_line", command=self.update_status)
        mode_menu.add_radiobutton(label="Тест Точки в Полигоне", variable=self.current_mode, value="point_test", command=self.update_status)
        menubar.add_cascade(label="Режим", menu=mode_menu)

        polygon_menu = Menu(menubar, tearoff=0)
        polygon_menu.add_command(label="Проверить на Выпуклость", command=self.check_convexity_action)
        polygon_menu.add_command(label="Показать Внутренние Нормали", command=self.show_normals_action)
        polygon_menu.add_command(label="Найти Пересечения с Линией", command=self.find_intersections_action)
        menubar.add_cascade(label="Полигон", menu=polygon_menu)

        hull_menu = Menu(menubar, tearoff=0)
        hull_submenu = Menu(hull_menu, tearoff=0)
        hull_submenu.add_radiobutton(label="Обход Грэхема", variable=self.selected_hull_method, value="graham")
        hull_submenu.add_radiobutton(label="Алгоритм Джарвиса", variable=self.selected_hull_method, value="jarvis")
        hull_menu.add_cascade(label="Выбрать Метод", menu=hull_submenu)
        hull_menu.add_command(label="Построить Выпуклую Оболочку", command=self.compute_convex_hull_action)
        menubar.add_cascade(label="Выпуклая Оболочка", menu=hull_menu)

        btn_poly = Button(toolbar, text="Полигон", command=lambda: self.set_mode("draw_polygon"))
        btn_poly.pack(side=tk.LEFT, padx=2, pady=2)
        btn_line = Button(toolbar, text="Линия", command=lambda: self.set_mode("draw_line"))
        btn_line.pack(side=tk.LEFT, padx=2, pady=2)
        btn_point_test = Button(toolbar, text="Тест Т.", command=lambda: self.set_mode("point_test"))
        btn_point_test.pack(side=tk.LEFT, padx=2, pady=2)

        lbl_hull = Label(toolbar, text=" Оболочка:")
        lbl_hull.pack(side=tk.LEFT, padx=(10, 0), pady=2)
        btn_graham = Button(toolbar, text="Грэхем", command=lambda: self.run_hull("graham"))
        btn_graham.pack(side=tk.LEFT, padx=2, pady=2)
        btn_jarvis = Button(toolbar, text="Джарвис", command=lambda: self.run_hull("jarvis"))
        btn_jarvis.pack(side=tk.LEFT, padx=2, pady=2)

        btn_clear = Button(toolbar, text="Очистить", command=self.clear_canvas)
        btn_clear.pack(side=tk.RIGHT, padx=5, pady=2)

        self.update_status()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        mode = self.current_mode.get()

        if mode == "draw_polygon":
            self.add_point(x, y)
            self.draw_polygon_dynamic()
        elif mode == "draw_line":
            if len(self.line_points) < 2:
                self.line_points.append((x,y))
                self.draw_point_marker(x, y, "blue")
                if len(self.line_points) == 2:
                    self.draw_line_segment()
                    self.update_status("Линия нарисована. Готово к следующему действию.")
            else:
                self.clear_specific_items([self.line_id] + self.intersection_point_ids)
                self.line_id = None
                self.intersection_point_ids = []
                self.line_points = [(x,y)]
                self.draw_point_marker(x, y, "blue")
                self.update_status("Начата новая линия (точка 1/2).")

        elif mode == "point_test":
            self.perform_point_in_polygon_test(x, y)

    def on_right_click(self, event):
        if self.current_mode.get() == "draw_polygon" and len(self.points) >= 3:
            self.draw_polygon_final()
            self.update_status(f"Полигон завершен с {len(self.points)} вершинами.")
        elif self.current_mode.get() == "draw_polygon" and len(self.points) < 3:
            self.update_status("Нужно минимум 3 точки для завершения полигона.")

    def set_mode(self, mode):
        self.current_mode.set(mode)
        self.update_status()
        if mode != "draw_line":
             self.clear_specific_items([self.line_id] + self.intersection_point_ids)
             self.line_id = None
             self.line_points = []
             self.intersection_point_ids = []

    def update_status(self, message=None):
        if message:
            self.status_label.config(text=message)
        else:
            mode = self.current_mode.get()
            mode_rus = self.mode_translations.get(mode, mode.replace('_', ' ').title())
            status = f"Режим: {mode_rus}"
            if mode == "draw_polygon":
                status += f" | Точек: {len(self.points)}"
            elif mode == "draw_line":
                 status += f" | Точек: {len(self.line_points)}/2"
            self.status_label.config(text=status)

    def add_point(self, x, y):
        self.points.append((x, y))
        self.draw_point_marker(x, y)
        self.update_status()

    def draw_point_marker(self, x, y, color="red", size=3):
        pid = self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color)
        self.point_ids.append(pid)

    def draw_polygon_dynamic(self):
        if self.polygon_id:
            self.canvas.delete(self.polygon_id)
            self.polygon_id = None
        if len(self.points) >= 2:
            dynamic_tag = "dynamic_poly_line"
            self.canvas.delete(dynamic_tag)
            for i in range(len(self.points) - 1):
                p1 = self.points[i]
                p2 = self.points[i+1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="black", tags=dynamic_tag)

    def draw_polygon_final(self, hull_points=None, color="blue", width=2, fill_poly=""):
        self.clear_specific_items([self.polygon_id, self.hull_id])
        self.canvas.delete("dynamic_poly_line")
        self.polygon_id = None
        self.hull_id = None
        points_to_draw = hull_points if hull_points else self.points
        if len(points_to_draw) >= 3:
            flat_points = [coord for point in points_to_draw for coord in point]
            if hull_points:
                 self.hull_id = self.canvas.create_polygon(flat_points, outline=color, width=width, fill=fill_poly, tags="hull")
            else:
                 self.polygon_id = self.canvas.create_polygon(flat_points, outline=color, width=width, fill=fill_poly, tags="polygon")
            return True
        return False

    def draw_line_segment(self):
        self.clear_specific_items([self.line_id])
        if len(self.line_points) == 2:
            p1 = self.line_points[0]
            p2 = self.line_points[1]
            self.line_id = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="green", width=2, tags="line")
            self.update_status("Линия нарисована.")
        else:
             self.update_status("Нужно 2 точки для рисования линии.")

    def draw_normals(self, normals_data):
        self.clear_specific_items(self.normal_ids)
        self.normal_ids = []
        scale = 20
        for mid_x, mid_y, nx, ny in normals_data:
            end_x = mid_x + nx * scale
            end_y = mid_y + ny * scale
            nid = self.canvas.create_line(mid_x, mid_y, end_x, end_y, fill="purple", arrow=tk.LAST)
            self.normal_ids.append(nid)
        self.update_status("Отображены внутренние нормали.")

    def draw_intersection_point(self, x, y):
        size = 4
        ipid = self.canvas.create_oval(x - size, y - size, x + size, y + size, fill="orange", outline="black")
        self.intersection_point_ids.append(ipid)

    def get_polygon_points(self):
        if len(self.points) < 3:
            return None
        return self.points

    def is_convex(self, poly_points):
        n = len(poly_points)
        if n < 3: return False
        sign = 0
        for i in range(n):
            p1 = poly_points[i]
            p2 = poly_points[(i + 1) % n]
            p3 = poly_points[(i + 2) % n]
            cp = cross_product_z(p1, p2, p3)
            if cp != 0:
                if sign == 0: sign = 1 if cp > 0 else -1
                elif (cp > 0 and sign < 0) or (cp < 0 and sign > 0): return False
        return True

    def calculate_inner_normals(self, poly_points):
        n = len(poly_points)
        if n < 3: return []
        area = 0
        for i in range(n):
            j = (i + 1) % n
            area += poly_points[i][0] * poly_points[j][1]
            area -= poly_points[j][0] * poly_points[i][1]
        if area < 0:
            poly_points = poly_points[::-1]
            self.points = poly_points
            self.draw_polygon_final()

        normals = []
        for i in range(n):
            p1 = poly_points[i]
            p2 = poly_points[(i + 1) % n]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            inner_nx, inner_ny = dy, -dx
            norm_nx, norm_ny = normalize_vector((inner_nx, inner_ny))
            mid_x = (p1[0] + p2[0]) / 2
            mid_y = (p1[1] + p2[1]) / 2
            normals.append((mid_x, mid_y, norm_nx, norm_ny))
        return normals

    def graham_scan(self, input_points):
        points = list(set(input_points))
        n = len(points)
        if n <= 2: return points
        pivot_idx = min(range(n), key=lambda i: (points[i][1], points[i][0]))
        pivot = points[pivot_idx]
        points[0], points[pivot_idx] = points[pivot_idx], points[0]
        def polar_angle(p): return math.atan2(p[1] - pivot[1], p[0] - pivot[0])
        points[1:] = sorted(points[1:], key=lambda p: (polar_angle(p), -dist_sq(pivot, p)))
        filtered_points = [points[0]]
        for i in range(1, n):
             while i < n - 1 and orientation(pivot, points[i], points[i+1]) == 0: i += 1
             filtered_points.append(points[i])
        points = filtered_points
        n = len(points)
        if n <= 2: return points
        hull = [points[0], points[1]]
        for i in range(2, n):
            top = hull.pop()
            while len(hull) > 0 and orientation(hull[-1], top, points[i]) != 2: top = hull.pop()
            hull.append(top)
            hull.append(points[i])
        return hull

    def jarvis_march(self, input_points):
        points = list(set(input_points))
        n = len(points)
        if n <= 2: return points
        hull = []
        start_idx = min(range(n), key=lambda i: points[i][0])
        current_idx = start_idx
        while True:
            hull.append(points[current_idx])
            next_candidate_idx = (current_idx + 1) % n
            for i in range(n):
                if i == current_idx: continue
                o = orientation(points[current_idx], points[next_candidate_idx], points[i])
                if o == 2 or (o == 0 and dist_sq(points[current_idx], points[i]) > dist_sq(points[current_idx], points[next_candidate_idx])):
                     next_candidate_idx = i
            current_idx = next_candidate_idx
            if current_idx == start_idx: break
            if len(hull) > n:
                 print("Предупреждение: Алгоритм Джарвиса потенциально зациклился, прерывание.")
                 break
        return hull

    def segments_intersect(self, p1, q1, p2, q2):
        o1 = orientation(p1, q1, p2)
        o2 = orientation(p1, q1, q2)
        o3 = orientation(p2, q2, p1)
        o4 = orientation(p2, q2, q1)
        if o1 != o2 and o3 != o4: return True
        if o1 == 0 and self.on_segment(p1, p2, q1): return True
        if o2 == 0 and self.on_segment(p1, q2, q1): return True
        if o3 == 0 and self.on_segment(p2, p1, q2): return True
        if o4 == 0 and self.on_segment(p2, q1, q2): return True
        return False

    def on_segment(self, p, q, r):
        return (q[0] <= max(p[0], r[0]) and q[0] >= min(p[0], r[0]) and
                q[1] <= max(p[1], r[1]) and q[1] >= min(p[1], r[1]))

    def find_intersection_point(self, p1, q1, p2, q2):
        A1 = q1[1] - p1[1]; B1 = p1[0] - q1[0]; C1 = A1 * p1[0] + B1 * p1[1]
        A2 = q2[1] - p2[1]; B2 = p2[0] - q2[0]; C2 = A2 * p2[0] + B2 * p2[1]
        determinant = A1 * B2 - A2 * B1
        if determinant == 0:
            print("Предупреждение: Параллельные/коллинеарные линии в find_intersection_point")
            return None
        else:
            x = (B2 * C1 - B1 * C2) / determinant
            y = (A1 * C2 - A2 * C1) / determinant
            epsilon = 1e-6
            on_seg1 = (min(p1[0], q1[0]) - epsilon <= x <= max(p1[0], q1[0]) + epsilon and
                       min(p1[1], q1[1]) - epsilon <= y <= max(p1[1], q1[1]) + epsilon)
            on_seg2 = (min(p2[0], q2[0]) - epsilon <= x <= max(p2[0], q2[0]) + epsilon and
                       min(p2[1], q2[1]) - epsilon <= y <= max(p2[1], q2[1]) + epsilon)
            if on_seg1 and on_seg2: return (x, y)
            else:
                print("Предупреждение: Расчетная точка пересечения вне сегментов.")
                return None

    def is_point_inside_polygon(self, point, poly_points):
        n = len(poly_points)
        if n < 3: return False
        x, y = point
        inside = False
        for p in poly_points:
            if p == point: return True
        p1 = poly_points[0]
        for i in range(n + 1):
            p2 = poly_points[i % n]
            if y == p1[1] == p2[1] and min(p1[0],p2[0]) <= x <= max(p1[0], p2[0]): return True
            if min(p1[1], p2[1]) < y <= max(p1[1], p2[1]):
                if x <= max(p1[0], p2[0]):
                    if p1[1] != p2[1]:
                        x_intersection = (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1]) + p1[0]
                        if abs(x - x_intersection) < 1e-9: return True
                        if x < x_intersection: inside = not inside
            if x == p1[0] == p2[0] and min(p1[1],p2[1]) <= y <= max(p1[1], p2[1]): return True
            p1 = p2
        return inside

    def clear_canvas(self):
        self.canvas.delete("all")
        self.points = []
        self.polygon_id = None
        self.point_ids = []
        self.hull_id = None
        self.normal_ids = []
        self.line_points = []
        self.line_id = None
        self.intersection_point_ids = []
        self.update_status("Холст очищен.")

    def clear_specific_items(self, item_ids):
        for item_id in item_ids:
            if item_id:
                self.canvas.delete(item_id)

    def check_convexity_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showwarning("Проверка Выпуклости", "Пожалуйста, сначала нарисуйте полигон (минимум 3 точки).")
            return

        if self.is_convex(poly):
            messagebox.showinfo("Проверка Выпуклости", "Полигон ВЫПУКЛЫЙ.")
            self.update_status("Полигон выпуклый.")
        else:
            messagebox.showinfo("Проверка Выпуклости", "Полигон НЕВЫПУКЛЫЙ (вогнутый).")
            self.update_status("Полигон невыпуклый.")

    def show_normals_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showwarning("Показать Нормали", "Пожалуйста, сначала нарисуйте полигон (минимум 3 точки).")
            return

        if not self.is_convex(poly):
             if messagebox.askyesno("Показать Нормали", "Полигон невыпуклый. Показать нормали для его выпуклой оболочки?"):
                 hull_points = self.run_hull_algorithm(self.points)
                 if hull_points and len(hull_points) >=3:
                     self.draw_polygon_final(hull_points=hull_points, color="green", width=1, fill_poly="")
                     normals_data = self.calculate_inner_normals(hull_points)
                     self.draw_normals(normals_data)
                     self.update_status("Показаны нормали для выпуклой оболочки.")
                 else:
                      messagebox.showerror("Показать Нормали", "Не удалось построить выпуклую оболочку для показа нормалей.")
             else:
                  messagebox.showwarning("Показать Нормали", "Невозможно рассчитать внутренние нормали для невыпуклого полигона.")
                  self.update_status("Невозможно показать нормали для невыпуклого полигона.")
             return

        current_poly_state = list(self.points)
        normals_data = self.calculate_inner_normals(poly)
        if current_poly_state != self.points:
             print("Вершины полигона переупорядочены против часовой стрелки для расчета нормалей.")

        if normals_data:
            self.draw_normals(normals_data)
        else:
             messagebox.showerror("Показать Нормали", "Не удалось рассчитать нормали.")
             self.update_status("Не удалось рассчитать нормали.")

    def run_hull_algorithm(self, points_to_hull):
        method = self.selected_hull_method.get()
        if len(points_to_hull) < 3:
            messagebox.showwarning("Выпуклая Оболочка", "Нужно минимум 3 точки для построения выпуклой оболочки.")
            return None

        if method == "graham":
            hull_points = self.graham_scan(points_to_hull)
        elif method == "jarvis":
            hull_points = self.jarvis_march(points_to_hull)
        else:
            messagebox.showerror("Выпуклая Оболочка", "Выбран неверный метод построения оболочки.")
            return None
        return hull_points

    def compute_convex_hull_action(self):
        self.clear_specific_items([self.hull_id] + self.normal_ids)
        self.hull_id = None
        self.normal_ids = []

        hull_points = self.run_hull_algorithm(self.points)

        if hull_points:
            method_name_map = {"graham": "Грэхема", "jarvis": "Джарвиса"}
            method_name = method_name_map.get(self.selected_hull_method.get(), "Неизвестный метод")
            self.update_status(f"Выпуклая оболочка ({method_name}) построена с {len(hull_points)} вершинами.")
            self.draw_polygon_final(hull_points=hull_points, color="green", width=1, fill_poly="")

    def run_hull(self, method):
         self.selected_hull_method.set(method)
         self.compute_convex_hull_action()

    def find_intersections_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showwarning("Поиск Пересечений", "Пожалуйста, сначала нарисуйте полигон (минимум 3 точки).")
            return
        if len(self.line_points) != 2:
             messagebox.showwarning("Поиск Пересечений", "Пожалуйста, сначала нарисуйте отрезок линии.")
             return

        self.clear_specific_items(self.intersection_point_ids)
        self.intersection_point_ids = []

        line_p1, line_p2 = self.line_points[0], self.line_points[1]
        intersections_found = []
        n = len(poly)

        for i in range(n):
            poly_p1 = poly[i]
            poly_p2 = poly[(i + 1) % n]

            if self.segments_intersect(line_p1, line_p2, poly_p1, poly_p2):
                intersection = self.find_intersection_point(line_p1, line_p2, poly_p1, poly_p2)
                if intersection:
                    intersections_found.append(intersection)
                    self.draw_intersection_point(intersection[0], intersection[1])

        if intersections_found:
            count = len(intersections_found)
            self.update_status(f"Найдено {count} точек пересечения.")
        else:
            self.update_status("Пересечений между линией и сторонами полигона не найдено.")

    def perform_point_in_polygon_test(self, x, y):
        poly = self.get_polygon_points()
        if not poly:
            self.update_status("Тест точки: Сначала нарисуйте полигон.")
            return

        point = (x, y)
        test_marker = self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="cyan", outline="black")

        is_inside = self.is_point_inside_polygon(point, poly)

        result_text = "ВНУТРИ" if is_inside else "СНАРУЖИ"
        messagebox.showinfo("Тест Точки в Полигоне", f"Точка ({x}, {y}) находится {result_text} полигона.")
        self.update_status(f"Точка ({x}, {y}) {result_text} полигона.")

        self.master.after(2000, lambda: self.canvas.delete(test_marker))

if __name__ == "__main__":
    root = tk.Tk()
    app = PolygonEditor(root)
    root.mainloop()