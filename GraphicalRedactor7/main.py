import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, colorchooser
import math
import copy
import time

from geometry import Point, Triangle, Edge, EPSILON, cross_product
from delaunay import DelaunayTriangulation
from voronoi import VoronoiDiagram

class GraphEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Графический редактор Делоне и Вороного")

        self.root.minsize(800, 600)
        self.root.geometry("1000x750")



        self.points: list[Point] = []
        self.original_points: list[Point] = []
        self.delaunay_triangles: list[Triangle] = []
        self.voronoi_edges: list[tuple] = []
        self.voronoi_vertices: dict[Triangle, Point] = {}


        self.selected_tool = tk.StringVar(value="add_point")
        self.debug_mode = tk.BooleanVar(value=False)
        self.debug_generator = None
        self.debug_state = {}


        self.point_color = "red"
        self.delaunay_color = "blue"
        self.voronoi_color = "green"
        self.super_triangle_color = "lightgrey"
        self.bad_triangle_color = "orange"
        self.hole_edge_color = "purple"
        self.new_triangle_color = "cyan"
        self.debug_point_color = "magenta"
        self.circumcircle_color = "salmon"
        self.point_radius = 3
        self.line_width = 1
        self.voronoi_line_width = 2
        self.debug_line_width_highlight = 2


        self.transform_center = Point(0, 0)
        self.is_dragging = False
        self.drag_start_point = None
        self.drag_start_canvas = None


        self.create_widgets()


        self.root.update_idletasks()
        self.update_transform_center()
        self.redraw_canvas()

    def create_widgets(self):

        control_frame = ttk.Frame(self.root, padding="10", width=220)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        control_frame.pack_propagate(False)

        ttk.Label(control_frame, text="Инструменты", font=("Arial", 12, "bold")).pack(pady=5, anchor=tk.W)

        ttk.Radiobutton(control_frame, text="Добавить точку", variable=self.selected_tool, value="add_point").pack(anchor=tk.W)
        # ttk.Radiobutton(control_frame, text="Переместить холст", variable=self.selected_tool, value="move").pack(anchor=tk.W)
        # ttk.Radiobutton(control_frame, text="Выделить/Переместить точки", variable=self.selected_tool, value="select").pack(anchor=tk.W)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Button(control_frame, text="Триангуляция Делоне", command=self.run_delaunay).pack(fill=tk.X, pady=3)
        ttk.Button(control_frame, text="Диаграмма Вороного", command=self.run_voronoi).pack(fill=tk.X, pady=3)
        ttk.Button(control_frame, text="Очистить всё", command=self.clear_all).pack(fill=tk.X, pady=3)
        ttk.Button(control_frame, text="Очистить вычисления", command=self.clear_calculations).pack(fill=tk.X, pady=3)

        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)


        ttk.Label(control_frame, text="Трансформации", font=("Arial", 12, "bold")).pack(pady=5, anchor=tk.W)

        trans_frame = ttk.Frame(control_frame)
        trans_frame.pack(fill=tk.X)
        ttk.Label(trans_frame, text="dX:").grid(row=0, column=0, padx=2, sticky="w")
        self.translate_dx_entry = ttk.Entry(trans_frame, width=5)
        self.translate_dx_entry.grid(row=0, column=1, padx=2)
        self.translate_dx_entry.insert(0, "10")
        ttk.Label(trans_frame, text="dY:").grid(row=0, column=2, padx=2, sticky="w")
        self.translate_dy_entry = ttk.Entry(trans_frame, width=5)
        self.translate_dy_entry.grid(row=0, column=3, padx=2)
        self.translate_dy_entry.insert(0, "0")
        ttk.Button(trans_frame, text="Сдвиг", command=self.apply_translate).grid(row=0, column=4, padx=5)
        trans_frame.columnconfigure(1, weight=1)
        trans_frame.columnconfigure(3, weight=1)

        scale_frame = ttk.Frame(control_frame)
        scale_frame.pack(fill=tk.X, pady=3)
        ttk.Label(scale_frame, text="Масштаб:").grid(row=0, column=0, padx=2, sticky="w")
        self.scale_factor_entry = ttk.Entry(scale_frame, width=5)
        self.scale_factor_entry.grid(row=0, column=1, padx=2)
        self.scale_factor_entry.insert(0, "1.1")
        ttk.Button(scale_frame, text="Применить", command=self.apply_scale).grid(row=0, column=2, padx=5)
        scale_frame.columnconfigure(1, weight=1)

        rotate_frame = ttk.Frame(control_frame)
        rotate_frame.pack(fill=tk.X, pady=3)
        ttk.Label(rotate_frame, text="Угол (°):").grid(row=0, column=0, padx=2, sticky="w")
        self.rotate_angle_entry = ttk.Entry(rotate_frame, width=5)
        self.rotate_angle_entry.grid(row=0, column=1, padx=2)
        self.rotate_angle_entry.insert(0, "15")
        ttk.Button(rotate_frame, text="Поворот", command=self.apply_rotate).grid(row=0, column=2, padx=5)
        rotate_frame.columnconfigure(1, weight=1)

        ttk.Button(control_frame, text="Сбросить вид", command=self.reset_view).pack(fill=tk.X, pady=3)
        ttk.Button(control_frame, text="Центр в центр холста", command=self.set_transform_center).pack(fill=tk.X, pady=3)


        ttk.Separator(control_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)


        ttk.Label(control_frame, text="Отладка", font=("Arial", 12, "bold")).pack(pady=5, anchor=tk.W)
        ttk.Checkbutton(control_frame, text="Режим отладки", variable=self.debug_mode, command=self.toggle_debug_mode).pack(anchor=tk.W)
        self.debug_step_button = ttk.Button(control_frame, text="Следующий шаг", command=self.run_debug_step, state=tk.DISABLED)
        self.debug_step_button.pack(fill=tk.X, pady=3)

        self.debug_status_label = ttk.Label(control_frame, text="Статус: Ожидание", wraplength=200, justify=tk.LEFT)
        self.debug_status_label.pack(anchor=tk.W, pady=5, fill=tk.X)



        self.canvas = tk.Canvas(self.root, bg="white", highlightthickness=0)
        self.canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)


        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        # self.canvas.bind("<Configure>", self.on_canvas_resize)



    def on_canvas_click(self, event):
        tool = self.selected_tool.get()

        if tool == "add_point" and not self.debug_mode.get():
            x, y = event.x, event.y
            new_point = Point(x, y)

            is_duplicate = False
            for p in self.points:
                 if abs(p.x - x) < self.point_radius * 2 and abs(p.y - y) < self.point_radius * 2:
                      is_duplicate = True
                      break
            if not is_duplicate:
                self.points.append(new_point)
                self.original_points.append(copy.deepcopy(new_point))
                self.draw_point(new_point)
                self.update_transform_center()

                self.clear_calculations(redraw=True)
            else:
                print("Точка слишком близко к существующей, не добавлена.")

        elif tool == "move":
            self.is_dragging = True
            self.drag_start_canvas = (event.x, event.y)
            self.canvas.config(cursor="fleur")


    def on_canvas_drag(self, event):
         pass

    def on_canvas_release(self, event):
        if self.is_dragging:
            self.is_dragging = False
            self.canvas.config(cursor="")



    def run_delaunay(self):

        if self.debug_mode.get():

            self.start_debug_delaunay()
            return


        if len(self.points) < 3:
            messagebox.showwarning("Внимание", "Нужно как минимум 3 точки для триангуляции Делоне.")
            return

        self.clear_calculations(redraw=False)
        try:
            delaunay = DelaunayTriangulation(self.points)


            self.delaunay_triangles = delaunay.triangulate()

            self.voronoi_edges = []
            self.voronoi_vertices = {}
            self.redraw_canvas()
            print(f"Построено {len(self.delaunay_triangles)} треугольников Делоне.")
        except Exception as e:
             messagebox.showerror("Ошибка триангуляции", f"Произошла ошибка при построении триангуляции Делоне:\n{e}")
             print(f"Ошибка триангуляции: {e}")
             self.clear_calculations(redraw=True)


    def run_voronoi(self):
        if self.debug_mode.get():
             messagebox.showwarning("Внимание", "Диаграмма Вороного не строится в пошаговом режиме.\nВыключите режим отладки и запустите триангуляцию Делоне.")
             return

        if not self.delaunay_triangles:
             messagebox.showwarning("Внимание", "Сначала нужно построить триангуляцию Делоне.")
             if len(self.points) >= 3:
                 print("Автоматический запуск триангуляции Делоне перед построением Вороного...")
                 self.run_delaunay()
                 if not self.delaunay_triangles:
                     return
             else:
                 return


        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
             self.root.update_idletasks()
             canvas_width = self.canvas.winfo_width()
             canvas_height = self.canvas.winfo_height()

        bounds = (0, 0, canvas_width, canvas_height)

        try:
            voronoi = VoronoiDiagram(self.delaunay_triangles, bounds)
            self.voronoi_edges = voronoi.compute()
            self.voronoi_vertices = voronoi.vertices
            self.redraw_canvas()
            print(f"Построено {len(self.voronoi_edges)} ребер Вороного.")
        except Exception as e:
             messagebox.showerror("Ошибка диаграммы Вороного", f"Произошла ошибка при построении диаграммы Вороного:\n{e}")
             print(f"Ошибка Вороного: {e}")

             self.voronoi_edges = []
             self.voronoi_vertices = {}
             self.redraw_canvas()



    def toggle_debug_mode(self):

        if self.debug_mode.get():

            self.clear_calculations(redraw=False)
            self.debug_generator = None
            self.debug_state = {}

            if self.points:
                 self.debug_status_label.config(text="Статус: Режим отладки включен.\nНажмите 'Триангуляция Делоне', чтобы инициализировать,\nзатем 'Следующий шаг'.\nДобавление/изменение точек заблокировано.")
                 self.debug_step_button.config(state=tk.DISABLED)
            else:
                 self.debug_status_label.config(text="Статус: Режим отладки включен.\nСначала добавьте точки (выключив этот режим),\nзатем снова включите отладку.")
                 self.debug_step_button.config(state=tk.DISABLED)

            self.redraw_canvas()
        else:

            self.debug_step_button.config(state=tk.DISABLED)
            self.debug_status_label.config(text="Статус: Режим отладки выключен.")
            self.debug_generator = None
            self.debug_state = {}


            self.redraw_canvas()

    def start_debug_delaunay(self):

        if not self.debug_mode.get():
            messagebox.showinfo("Информация", "Сначала включите 'Режим отладки' на панели управления.")
            return

        if len(self.points) < 3:
            messagebox.showwarning("Внимание", "Нужно как минимум 3 точки для начала отладки триангуляции.\nЕсли вы только что включили режим, добавьте точки (предварительно выключив отладку), затем снова включите режим и нажмите эту кнопку.")
            self.debug_status_label.config(text="Статус: Недостаточно точек для отладки.")
            self.debug_step_button.config(state=tk.DISABLED)
            return


        self.debug_generator = None
        self.debug_state = {}
        self.clear_calculations(redraw=False)

        try:
            print("Инициализация отладки Делоне...")
            delaunay_algo = DelaunayTriangulation(self.points)
            self.debug_generator = delaunay_algo.triangulate_stepwise()
            self.debug_state = {}
            self.debug_status_label.config(text="Статус: Отладка Делоне инициализирована. Нажмите 'Следующий шаг'.")

            self.debug_step_button.config(state=tk.NORMAL)

            print("Выполнение первого шага отладки (init)...")
            self.run_debug_step()
        except Exception as e:
             messagebox.showerror("Ошибка инициализации отладки", f"Не удалось запустить отладку:\n{e}")
             self.debug_status_label.config(text="Статус: Ошибка инициализации отладки.")
             self.debug_step_button.config(state=tk.DISABLED)
             print(f"Ошибка инициализации отладки: {e}")


    def run_debug_step(self):
        if not self.debug_mode.get() or self.debug_generator is None:

            if self.debug_mode.get() and self.debug_step_button['state'] == tk.NORMAL:
                 self.debug_status_label.config(text="Статус: Отладка не инициализирована. Нажмите 'Триангуляция Делоне'.")
                 self.debug_step_button.config(state=tk.DISABLED)
            return

        try:
            print(f"Запрос следующего шага отладки...")
            self.debug_state = next(self.debug_generator)
            status = self.debug_state.get('status', 'unknown')
            message = self.debug_state.get('message', f'Шаг: {status}')
            print(f"  Получен шаг: {status}")
            self.debug_status_label.config(text=f"Статус: {message}")
            self.redraw_canvas()

            if status == 'done':
                print("Отладка завершена.")
                self.debug_status_label.config(text="Статус: Отладка Делоне завершена.")
                self.debug_step_button.config(state=tk.DISABLED)
                self.debug_generator = None

                self.delaunay_triangles = list(self.debug_state.get('final', set()))



        except StopIteration:
            print("Генератор отладки завершил работу (StopIteration).")
            self.debug_status_label.config(text="Статус: Отладка Делоне завершена.")
            self.debug_step_button.config(state=tk.DISABLED)
            self.debug_generator = None

            if 'final' in self.debug_state:
                 self.delaunay_triangles = list(self.debug_state.get('final', set()))
            else:


                 last_triangles = self.debug_state.get('triangles', set())

                 st = self.debug_state.get('super_triangle')
                 if st:
                     final_triangles_set = {t for t in last_triangles if t != st}

                     if hasattr(st, 'vertices'):
                         sv = st.vertices
                         final_triangles_set = {t for t in final_triangles_set if not any(v in sv for v in t.vertices)}
                     self.delaunay_triangles = list(final_triangles_set)
                 else:
                      self.delaunay_triangles = list(last_triangles)


            self.redraw_canvas()

        except Exception as e:
            messagebox.showerror("Ошибка отладки", f"Произошла ошибка на шаге отладки:\n{e}")
            print(f"Ошибка отладки на шаге {self.debug_state.get('status', '?')}: {e}")
            import traceback
            traceback.print_exc()
            self.debug_status_label.config(text="Статус: Ошибка отладки.")
            self.debug_step_button.config(state=tk.DISABLED)
            self.debug_generator = None




    def redraw_canvas(self):
        self.canvas.delete("all")


        if self.debug_mode.get() and self.debug_state:

            self.draw_debug_state()
        else:


            for point in self.points:
                self.draw_point(point)


            for triangle in self.delaunay_triangles:
                self.draw_triangle(triangle, self.delaunay_color)


            for edge in self.voronoi_edges:
                self.draw_voronoi_edge(edge, self.voronoi_color)





        if self.transform_center:
            cx, cy = self.transform_center.x, self.transform_center.y
            r = 5
            self.canvas.create_line(cx-r, cy, cx+r, cy, fill="black", width=1, tags="transform_center")
            self.canvas.create_line(cx, cy-r, cx, cy+r, fill="black", width=1, tags="transform_center")


    def draw_debug_state(self):
        """Рисует холст на основе текущего состояния отладки."""
        state = self.debug_state
        status = state.get('status')
        if not status: return


        for point in self.points:
            self.draw_point(point)


        current_triangles = state.get('triangles', set())
        super_triangle = state.get('super_triangle')


        for triangle in current_triangles:

             is_super = super_triangle and triangle == super_triangle
             if not is_super:
                 self.draw_triangle(triangle, self.delaunay_color)




        if super_triangle and status != 'finalize' and status != 'done':

             self.draw_triangle(super_triangle, self.super_triangle_color, dashed=True, tags=("debug", "super_triangle"))


        current_point = state.get('point')
        if current_point:
            self.draw_point(current_point, color=self.debug_point_color, radius=self.point_radius + 2, tags=("debug", "current_point"))


        if status == 'find_bad':
            bad_triangles = state.get('bad_triangles', set())
            for triangle in bad_triangles:

                center, radius_sq = triangle.circumcenter_radius_sq
                if radius_sq != float('inf') and radius_sq > EPSILON:
                    try:
                        radius = math.sqrt(radius_sq)
                        self.draw_circle(center, radius, self.circumcircle_color, tags=("debug", "circumcircle"))
                    except ValueError:
                         print(f"Предупреждение: Не удалось вычислить радиус для {triangle} (radius_sq={radius_sq})")



                self.draw_triangle(triangle, self.bad_triangle_color, fill=True, tags=("debug", "bad_triangle"))


        elif status == 'make_hole':
            hole_edges = state.get('hole_edges', [])

            for edge in hole_edges:
                self.draw_edge(edge, self.hole_edge_color, width=self.debug_line_width_highlight, tags=("debug", "hole_edge"))







        elif status == 'fill_hole':
            new_triangles = state.get('new_triangles', set())

            for triangle in new_triangles:
                self.draw_triangle(triangle, self.new_triangle_color, tags=("debug", "new_triangle"))

            hole_edges = state.get('hole_edges', [])
            for edge in hole_edges:
                self.draw_edge(edge, self.hole_edge_color, width=self.debug_line_width_highlight, tags=("debug", "hole_edge"))



        elif status == 'finalize':

             final_triangles = state.get('final', set())
             for triangle in final_triangles:
                self.draw_triangle(triangle, self.delaunay_color)

             removed = state.get('removed_super', set())
             for triangle in removed:
                self.draw_triangle(triangle, self.super_triangle_color, dashed=True, tags=("debug", "removed_super"))


        elif status == 'done':
            final_triangles = state.get('final', set())
            for triangle in final_triangles:
                self.draw_triangle(triangle, self.delaunay_color)


    def draw_point(self, point: Point, color=None, radius=None, tags=()):
        if color is None: color = self.point_color
        if radius is None: radius = self.point_radius

        if not (math.isfinite(point.x) and math.isfinite(point.y)):
            print(f"Предупреждение: Попытка нарисовать точку с некорректными координатами: {point}")
            return
        x, y = point.x, point.y
        tag_list = list(tags) + ["point"]
        try:
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=color, outline=color, tags=tuple(tag_list)
            )
        except tk.TclError as e:

             print(f"Ошибка Tkinter при рисовании точки ({x},{y}): {e}")


    def draw_edge(self, edge: Edge, color="black", width=1, tags=(), dashed=False):

        if not (math.isfinite(edge.p1.x) and math.isfinite(edge.p1.y) and
                math.isfinite(edge.p2.x) and math.isfinite(edge.p2.y)):
            print(f"Предупреждение: Попытка нарисовать ребро с некорректными координатами: {edge}")
            return

        x1, y1 = edge.p1.x, edge.p1.y
        x2, y2 = edge.p2.x, edge.p2.y
        tag_list = list(tags) + ["edge"]
        dash_opt = ()
        if dashed:
             dash_opt = (4, 4)
        try:
             self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags=tuple(tag_list), dash=dash_opt)
        except tk.TclError as e:
             print(f"Ошибка Tkinter при рисовании ребра ({x1},{y1})-({x2},{y2}): {e}")

    def draw_triangle(self, triangle: Triangle, color="blue", width=None, tags=(), dashed=False, fill=False):
        if width is None: width = self.line_width
        tag_list = list(tags) + ["triangle", "delaunay"]
        coords = []

        valid_coords = True
        for p in triangle.vertices:
            if not (math.isfinite(p.x) and math.isfinite(p.y)):
                print(f"Предупреждение: Попытка нарисовать треугольник с некорректной вершиной: {p} в {triangle}")
                valid_coords = False
                break
            coords.extend([p.x, p.y])

        if not valid_coords:
            return

        fill_color = ""
        if fill:

            fill_color = self._get_light_color(color)

        dash_opt = ()
        if dashed:
             dash_opt = (4, 4)

        try:

            self.canvas.create_polygon(
                coords,
                outline=color,
                fill=fill_color,
                width=width,
                tags=tuple(tag_list),
                dash=dash_opt
            )
        except tk.TclError as e:
            print(f"Ошибка Tkinter при рисовании треугольника {triangle}: {e}")


    def draw_voronoi_edge(self, edge_data: tuple, color="green", width=None, tags=()):
        if width is None: width = self.voronoi_line_width
        tag_list = list(tags) + ["voronoi_edge"]

        if len(edge_data) < 2: return

        v1, v2 = edge_data[0], edge_data[1]


        if not (v1 and v2 and math.isfinite(v1.x) and math.isfinite(v1.y) and
                math.isfinite(v2.x) and math.isfinite(v2.y)):


             return

        x1, y1 = v1.x, v1.y
        x2, y2 = v2.x, v2.y

        try:
            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, tags=tuple(tag_list))
        except tk.TclError as e:
             print(f"Ошибка Tkinter при рисовании ребра Вороного ({x1},{y1})-({x2},{y2}): {e}")


    def draw_circle(self, center: Point, radius: float, color="grey", width=1, tags=(), dashed=False):
        """Рисует окружность."""

        if not (center and math.isfinite(center.x) and math.isfinite(center.y) and math.isfinite(radius) and radius > EPSILON):
            # print(f"Предупреждение: Попытка нарисовать окружность с некорректными параметрами: center={center}, radius={radius}")
            return

        x, y = center.x, center.y
        tag_list = list(tags) + ["circle"]
        dash_opt = ()
        if dashed:
             dash_opt = (3, 5)

        try:
            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                outline=color, width=width, tags=tuple(tag_list), dash=dash_opt
            )
        except tk.TclError as e:
            print(f"Ошибка Tkinter при рисовании окружности (центр=({x},{y}), радиус={radius}): {e}")

    def _get_light_color(self, color_name):
        """Пытается получить более светлый оттенок цвета для заливки."""
        try:

            rgb = self.root.winfo_rgb(color_name)


            increase = 20000
            r = min(rgb[0] + increase, 65535)
            g = min(rgb[1] + increase, 65535)
            b = min(rgb[2] + increase, 65535)

            return f'#{r>>8:02x}{g>>8:02x}{b>>8:02x}'
        except Exception:
             return "whitesmoke"


    def update_transform_center(self):
        """Вычисляет центр масс текущих точек или центр холста, если точек нет."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if not self.points:

            cx = canvas_width / 2.0 if canvas_width > 1 else 300.0
            cy = canvas_height / 2.0 if canvas_height > 1 else 300.0
            self.transform_center = Point(cx, cy)
        else:
            try:
                sum_x = sum(p.x for p in self.points)
                sum_y = sum(p.y for p in self.points)
                count = len(self.points)
                self.transform_center = Point(sum_x / count, sum_y / count)
            except Exception as e:
                 print(f"Ошибка при вычислении центра масс: {e}. Используется центр холста.")
                 cx = canvas_width / 2.0 if canvas_width > 1 else 300.0
                 cy = canvas_height / 2.0 if canvas_height > 1 else 300.0
                 self.transform_center = Point(cx, cy)





    def set_transform_center(self):
        """Устанавливает центр трансформаций в центр видимой области холста."""
        try:
             canvas_width = self.canvas.winfo_width()
             canvas_height = self.canvas.winfo_height()
             if canvas_width <= 1 or canvas_height <= 1:
                 self.root.update_idletasks()
                 canvas_width = self.canvas.winfo_width()
                 canvas_height = self.canvas.winfo_height()

             if canvas_width > 1 and canvas_height > 1:
                 self.transform_center = Point(canvas_width / 2.0, canvas_height / 2.0)
                 self.redraw_canvas()
                 print(f"Центр трансформаций установлен в центр холста: {self.transform_center}")
             else:
                 print("Не удалось получить размеры холста для установки центра.")
        except Exception as e:
             print(f"Не удалось установить центр холста: {e}")


    def apply_transform(self, transform_func):
        """Применяет функцию трансформации ко всем точкам."""
        if not self.points: return


        transformed_points = []
        try:
            for p in self.points:
                transformed_points.append(transform_func(p))
            self.points = transformed_points
        except Exception as e:
             messagebox.showerror("Ошибка трансформации", f"Ошибка при применении трансформации:\n{e}")
             print(f"Ошибка трансформации: {e}")
             return








        self.clear_calculations(redraw=False)

        self.update_transform_center()
        self.redraw_canvas()


    def apply_translate(self):
        try:
            dx = float(self.translate_dx_entry.get())
            dy = float(self.translate_dy_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат смещения (dX, dY). Введите числа.")
            return

        def translate(point: Point) -> Point:
            return Point(point.x + dx, point.y + dy)


        self.apply_transform(translate)



        try:
             self.original_points = [translate(p) for p in self.original_points]
        except Exception as e:
             print(f"Ошибка при обновлении original_points после сдвига: {e}")




    def apply_scale(self):
        try:
            factor = float(self.scale_factor_entry.get())
            if factor <= 0 or not math.isfinite(factor):
                raise ValueError("Масштаб должен быть положительным числом.")
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат масштаба: {e}")
            return


        cx = self.transform_center.x
        cy = self.transform_center.y

        def scale(point: Point) -> Point:

            if abs(point.x - cx) < EPSILON and abs(point.y - cy) < EPSILON:
                return point

            new_x = cx + (point.x - cx) * factor
            new_y = cy + (point.y - cy) * factor

            if not (math.isfinite(new_x) and math.isfinite(new_y)):
                 raise ValueError(f"Результат масштабирования точки {point} некорректен ({new_x}, {new_y})")
            return Point(new_x, new_y)

        self.apply_transform(scale)



    def apply_rotate(self):
        try:
            angle_deg = float(self.rotate_angle_entry.get())
            if not math.isfinite(angle_deg):
                 raise ValueError("Угол должен быть числом.")
            angle_rad = math.radians(angle_deg)
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат угла: {e}")
            return


        cx = self.transform_center.x
        cy = self.transform_center.y
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        def rotate(point: Point) -> Point:

            x_temp = point.x - cx
            y_temp = point.y - cy

            new_x_temp = x_temp * cos_a - y_temp * sin_a
            new_y_temp = x_temp * sin_a + y_temp * cos_a

            new_x = new_x_temp + cx
            new_y = new_y_temp + cy

            if not (math.isfinite(new_x) and math.isfinite(new_y)):
                 raise ValueError(f"Результат поворота точки {point} некорректен ({new_x}, {new_y})")
            return Point(new_x, new_y)

        self.apply_transform(rotate)


    def reset_view(self):
        """Сбрасывает точки к их исходному положению (original_points)."""
        if not self.original_points and not self.points:
            print("Нет исходных точек для сброса.")
            return

        if not self.original_points and self.points:

             messagebox.showwarning("Сброс вида", "Исходное положение точек не сохранено. Невозможно сбросить вид.")
             return

        print("Сброс вида к исходным точкам...")
        self.points = [copy.deepcopy(p) for p in self.original_points]
        self.clear_calculations(redraw=False)
        self.update_transform_center()
        self.redraw_canvas()
        print("Вид сброшен.")



    def clear_calculations(self, redraw=True):
        """Очищает результаты вычислений (Делоне, Вороной) и состояние отладки."""
        needs_redraw = False
        if self.delaunay_triangles:
            self.delaunay_triangles = []
            needs_redraw = True
        if self.voronoi_edges:
            self.voronoi_edges = []
            self.voronoi_vertices = {}
            needs_redraw = True


        if self.debug_generator or self.debug_state:
            self.debug_generator = None
            self.debug_state = {}
            needs_redraw = True
            if self.debug_mode.get():

                self.debug_status_label.config(text="Статус: Вычисления сброшены. Начните отладку заново (нажмите 'Триангуляция Делоне').")
                self.debug_step_button.config(state=tk.DISABLED)

        if redraw and needs_redraw:
            self.redraw_canvas()
        elif redraw and not needs_redraw:


             self.redraw_canvas()

    def clear_all(self):
        """Очищает все: точки и вычисления."""
        print("Очистка всего...")
        self.points = []
        self.original_points = []
        self.clear_calculations(redraw=False)
        self.update_transform_center()


        if self.debug_mode.get():
            self.debug_generator = None
            self.debug_state = {}
            self.debug_status_label.config(text="Статус: Все очищено. Отладка сброшена. Добавьте точки.")
            self.debug_step_button.config(state=tk.DISABLED)


        self.redraw_canvas()


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphEditorApp(root)
    root.mainloop()
