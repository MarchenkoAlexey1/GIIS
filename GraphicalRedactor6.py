# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, Menu, Frame, Button, Label, Checkbutton, simpledialog, colorchooser
import math
import time
from collections import defaultdict, deque
import traceback

DEFAULT_FILL_COLOR = "lightblue"
POLYGON_OUTLINE_COLOR = "blue"
CANVAS_BG_COLOR = "white"
SEED_MARKER_COLOR = "red"
FILL_ITEM_TAG = "fill_item"
DEBUG_DELAY_MS = 50
PIXEL_CHECK_LIMIT = 500000

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

class EdgeEntry:
    def __init__(self, y_max, x_at_y_min, inv_slope):
        self.y_max = y_max
        self.x = x_at_y_min
        self.inv_slope = inv_slope

    def __lt__(self, other):
        return self.x < other.x

    def __repr__(self):
        return f"Edge(y_max={self.y_max}, x={self.x:.2f}, inv_slope={self.inv_slope:.2f})"

class PolygonEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Редактор Полигонов с Заполнением")
        self.master.geometry("900x750")

        self.points = []
        self.polygon_id = None
        self.point_ids = []
        self.hull_id = None
        self.normal_ids = []
        self.line_points = []
        self.line_id = None
        self.intersection_point_ids = []
        self.seed_point = None
        self.seed_marker_id = None
        self.fill_color = tk.StringVar(value=DEFAULT_FILL_COLOR)
        self._polygon_points_cache = None

        self.current_mode = tk.StringVar(value="draw_polygon")
        self.selected_hull_method = tk.StringVar(value="graham")
        self.selected_fill_algorithm = tk.StringVar(value="scanline_et_aet")
        self.debug_mode = tk.BooleanVar(value=False)
        self.waiting_for_seed = False

        self.mode_translations = {
            "draw_polygon": "Рисование Полигона",
            "draw_line": "Рисование Линии",
            "point_test": "Тест Точки в Полигоне",
            "select_seed": "Выбор Затравки"
        }

        self.fill_algorithm_translations = {
            "scanline_et_aet": "Сканлайн с ТР и САР",
            "scanline_aet": "Сканлайн с САР",
            "simple_seed_fill": "Простая Затравка",
            "scanline_seed_fill": "Построчная Затравка"
        }

        top_frame = Frame(master)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        toolbar1 = Frame(top_frame, bd=1, relief=tk.RAISED)
        toolbar1.pack(side=tk.TOP, fill=tk.X)

        toolbar2 = Frame(top_frame, bd=1, relief=tk.RAISED)
        toolbar2.pack(side=tk.TOP, fill=tk.X)

        self.status_label = Label(master, text="Режим: Рисование Полигона", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(master, bg=CANVAS_BG_COLOR, width=880, height=650)
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
        mode_menu.add_radiobutton(label="Рисование Линии", variable=self.current_mode, value="draw_line", command=self.update_status)
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

        fill_menu = Menu(menubar, tearoff=0)
        fill_algo_menu = Menu(fill_menu, tearoff=0)
        fill_algo_menu.add_radiobutton(label="Сканлайн с ТР и САР", variable=self.selected_fill_algorithm, value="scanline_et_aet")
        fill_algo_menu.add_radiobutton(label="Сканлайн с САР", variable=self.selected_fill_algorithm, value="scanline_aet")
        fill_algo_menu.add_radiobutton(label="Простая Затравка", variable=self.selected_fill_algorithm, value="simple_seed_fill")
        fill_algo_menu.add_radiobutton(label="Построчная Затравка", variable=self.selected_fill_algorithm, value="scanline_seed_fill")
        fill_menu.add_cascade(label="Выбрать Алгоритм", menu=fill_algo_menu)
        fill_menu.add_command(label="Выбрать Цвет Заливки", command=self.select_fill_color_action)
        fill_menu.add_separator()
        fill_menu.add_command(label="Заполнить Полигон", command=self.fill_polygon_action)
        fill_menu.add_separator()
        fill_menu.add_checkbutton(label="Режим Отладки", variable=self.debug_mode, onvalue=True, offvalue=False)
        menubar.add_cascade(label="Заполнение", menu=fill_menu)

        btn_poly = Button(toolbar1, text="Полигон", command=lambda: self.set_mode("draw_polygon"))
        btn_poly.pack(side=tk.LEFT, padx=2, pady=2)
        btn_line = Button(toolbar1, text="Линия", command=lambda: self.set_mode("draw_line"))
        btn_line.pack(side=tk.LEFT, padx=2, pady=2)
        btn_point_test = Button(toolbar1, text="Тест Т.", command=lambda: self.set_mode("point_test"))
        btn_point_test.pack(side=tk.LEFT, padx=2, pady=2)

        lbl_hull = Label(toolbar1, text=" Оболочка:")
        lbl_hull.pack(side=tk.LEFT, padx=(10, 0), pady=2)
        btn_graham = Button(toolbar1, text="Грэхем", command=lambda: self.run_hull("graham"))
        btn_graham.pack(side=tk.LEFT, padx=2, pady=2)
        btn_jarvis = Button(toolbar1, text="Джарвис", command=lambda: self.run_hull("jarvis"))
        btn_jarvis.pack(side=tk.LEFT, padx=2, pady=2)

        btn_clear = Button(toolbar1, text="Очистить", command=self.clear_canvas)
        btn_clear.pack(side=tk.RIGHT, padx=5, pady=2)

        lbl_fill = Label(toolbar2, text="Заполнение: ")
        lbl_fill.pack(side=tk.LEFT, padx=(5,0), pady=2)
        btn_fill_scan_et = Button(toolbar2, text="Сканл.+ТР", command=lambda: self.set_fill_algorithm("scanline_et_aet"))
        btn_fill_scan_et.pack(side=tk.LEFT, padx=2, pady=2)
        btn_fill_scan_aet = Button(toolbar2, text="Сканл.+САР", command=lambda: self.set_fill_algorithm("scanline_aet"))
        btn_fill_scan_aet.pack(side=tk.LEFT, padx=2, pady=2)
        btn_fill_seed_simple = Button(toolbar2, text="Затравка", command=lambda: self.set_fill_algorithm("simple_seed_fill"))
        btn_fill_seed_simple.pack(side=tk.LEFT, padx=2, pady=2)
        btn_fill_seed_scan = Button(toolbar2, text="Постр.Затр.", command=lambda: self.set_fill_algorithm("scanline_seed_fill"))
        btn_fill_seed_scan.pack(side=tk.LEFT, padx=2, pady=2)

        self.fill_color_label = Label(toolbar2, text=f"Цвет: {self.fill_color.get()}", bg=self.fill_color.get(), width=10)
        self.fill_color_label.pack(side=tk.LEFT, padx=5, pady=2)
        btn_color = Button(toolbar2, text="Выбрать Цвет", command=self.select_fill_color_action)
        btn_color.pack(side=tk.LEFT, padx=2, pady=2)

        btn_fill = Button(toolbar2, text="ЗАЛИТЬ", command=self.fill_polygon_action, font=('Arial', 10, 'bold'))
        btn_fill.pack(side=tk.LEFT, padx=10, pady=2)

        check_debug = Checkbutton(toolbar2, text="Отладка", variable=self.debug_mode)
        check_debug.pack(side=tk.RIGHT, padx=5, pady=2)

        self.update_status()

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        mode = self.current_mode.get()

        if self.waiting_for_seed:
            poly = self._polygon_points_cache
            if poly and self.is_point_inside_polygon((x, y), poly, check_boundary=False):
                self.seed_point = (x, y)
                self.waiting_for_seed = False
                if self.seed_marker_id: self.canvas.delete(self.seed_marker_id)
                self.seed_marker_id = self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=SEED_MARKER_COLOR, outline=SEED_MARKER_COLOR, tags="seed_marker")
                self.update_status(f"Затравочная точка ({x},{y}) выбрана. Запускаем заливку...")
                self.master.after(100, self._execute_fill)
            else:
                self.update_status("Ошибка: Точка затравки должна быть строго внутри полигона. Попробуйте еще раз.")
            return

        if mode == "draw_polygon":
            if self.canvas.find_withtag(FILL_ITEM_TAG):
                 messagebox.showwarning("Рисование Полигона", "Полигон уже залит. Очистите холст для рисования нового полигона.")
                 return
            self.add_point(x, y)
            self.draw_polygon_dynamic()
        elif mode == "draw_line":
            if len(self.line_points) < 2:
                self.line_points.append((x,y))
                pid = self.draw_point_marker(x, y, "blue")
                self.point_ids.append(pid) # Сохраняем ID маркера
                if len(self.line_points) == 2:
                    self.draw_line_segment()
                    self.update_status("Линия нарисована. Готово к следующему действию.")
            else:
                # Находим и удаляем маркеры старой линии
                line_markers_ids = []
                temp_points = list(self.points) # Копия для безопасной итерации
                temp_ids = list(self.point_ids)
                indices_to_remove = []
                for i, p in enumerate(temp_points):
                    if p in self.line_points:
                        line_markers_ids.append(temp_ids[i])
                        indices_to_remove.append(i)

                # Удаляем точки и ID в обратном порядке
                for index in sorted(indices_to_remove, reverse=True):
                    del self.points[index]
                    del self.point_ids[index]

                self.clear_specific_items([self.line_id] + self.intersection_point_ids + line_markers_ids)
                self.line_id = None
                self.intersection_point_ids = []
                # self.point_ids уже очищен от маркеров линии
                self.line_points = [(x,y)]
                pid = self.draw_point_marker(x, y, "blue")
                self.point_ids.append(pid) # Добавляем ID нового маркера
                self.points.append((x,y)) # Добавляем точку в общий список тоже
                self.update_status("Начата новая линия (точка 1/2).")
        elif mode == "point_test":
            self.perform_point_in_polygon_test(x, y)


    def on_right_click(self, event):
        if self.current_mode.get() == "draw_polygon" and len(self.points) >= 3:
            if self.canvas.find_withtag(FILL_ITEM_TAG):
                 messagebox.showwarning("Рисование Полигона", "Полигон уже залит. Очистите холст для рисования нового полигона.")
                 return
            # Удаляем точки линии, если они есть, перед завершением полигона
            if self.line_points:
                 self.clear_specific_items([self.line_id])
                 line_markers_ids = []
                 indices_to_remove = []
                 temp_points = list(self.points)
                 temp_ids = list(self.point_ids)
                 for i, p in enumerate(temp_points):
                     if p in self.line_points:
                         line_markers_ids.append(temp_ids[i])
                         indices_to_remove.append(i)
                 for index in sorted(indices_to_remove, reverse=True):
                     del self.points[index]
                     del self.point_ids[index]
                 self.clear_specific_items(line_markers_ids)
                 self.line_points = []
                 self.line_id = None


            self.draw_polygon_final()
            self.update_status(f"Полигон завершен с {len(self.points)} вершинами.")
        elif self.current_mode.get() == "draw_polygon" and len(self.points) < 3:
            self.update_status("Нужно минимум 3 точки для завершения полигона.")

    def set_mode(self, mode):
        if self.waiting_for_seed:
            self.waiting_for_seed = False
            self.clear_specific_items([self.seed_marker_id])
            self.seed_marker_id = None
            self.seed_point = None
            self._polygon_points_cache = None

        self.current_mode.set(mode)
        self.update_status()

        if mode != "draw_line":
             # Находим и удаляем маркеры линии
             line_markers_ids = []
             indices_to_remove = []
             temp_points = list(self.points) # Копия
             temp_ids = list(self.point_ids)
             for i, p in enumerate(temp_points):
                 if p in self.line_points:
                     line_markers_ids.append(temp_ids[i])
                     indices_to_remove.append(i)
             # Удаляем точки и ID в обратном порядке
             for index in sorted(indices_to_remove, reverse=True):
                 if index < len(self.points): del self.points[index]
                 if index < len(self.point_ids): del self.point_ids[index]

             self.clear_specific_items([self.line_id] + self.intersection_point_ids + line_markers_ids)
             self.line_id = None
             self.line_points = []
             self.intersection_point_ids = []
             # self.point_ids уже обновлен


    def update_status(self, message=None):
        if message:
            self.status_label.config(text=message)
        else:
            mode = self.current_mode.get()
            if self.waiting_for_seed:
                 mode_rus = self.mode_translations["select_seed"]
                 status = f"Режим: {mode_rus}. Кликните внутри полигона."
            else:
                mode_rus = self.mode_translations.get(mode, mode.replace('_', ' ').title())
                status = f"Режим: {mode_rus}"
                if mode == "draw_polygon":
                    # Считаем только точки полигона (исключая точки линии)
                    poly_point_count = len([p for p in self.points if p not in self.line_points])
                    status += f" | Точек: {poly_point_count}"
                elif mode == "draw_line":
                    status += f" | Точек: {len(self.line_points)}/2"

            fill_algo = self.selected_fill_algorithm.get()
            fill_algo_rus = self.fill_algorithm_translations.get(fill_algo, fill_algo)
            status += f" | Заливка: {fill_algo_rus}"
            if self.debug_mode.get():
                status += " | Отладка ВКЛ"

            self.status_label.config(text=status)

    def select_fill_color_action(self):
        color_code = colorchooser.askcolor(title="Выберите Цвет Заливки", initialcolor=self.fill_color.get())
        if color_code and color_code[1]:
            self.fill_color.set(color_code[1])
            self.fill_color_label.config(bg=self.fill_color.get(), text=f"Цвет: {self.fill_color.get()}")
            self.update_status(f"Цвет заливки изменен на {self.fill_color.get()}")

    def set_fill_algorithm(self, algo_name):
        self.selected_fill_algorithm.set(algo_name)
        self.update_status()

    def add_point(self, x, y):
        # Не добавляем точку, если она совпадает с последней
        if self.points and self.points[-1] == (x, y):
            return
        self.points.append((x, y))
        pid = self.draw_point_marker(x, y)
        self.point_ids.append(pid)
        self.update_status()


    def draw_point_marker(self, x, y, color="red", size=3):
        return self.canvas.create_oval(x - size, y - size, x + size, y + size, fill=color, outline=color, tags="point_marker")

    def draw_polygon_dynamic(self):
        if self.canvas.find_withtag(FILL_ITEM_TAG): return
        if self.polygon_id:
            self.canvas.delete(self.polygon_id)
            self.polygon_id = None

        # Рисуем только точки полигона
        poly_points_only = [p for p in self.points if p not in self.line_points]

        if len(poly_points_only) >= 2:
            dynamic_tag = "dynamic_poly_line"
            self.canvas.delete(dynamic_tag)
            for i in range(len(poly_points_only) - 1):
                p1 = poly_points_only[i]
                p2 = poly_points_only[i+1]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="black", tags=dynamic_tag)

    def draw_polygon_final(self, hull_points=None, color=POLYGON_OUTLINE_COLOR, width=2, fill_poly=""):
        self.clear_specific_items([self.polygon_id, self.hull_id])
        self.canvas.delete("dynamic_poly_line")
        self.polygon_id = None
        self.hull_id = None

        # Определяем точки для рисования (оболочка или основной полигон)
        if hull_points:
             points_to_draw_list = list(hull_points)
        else:
             # Берем только точки полигона, исключая точки линии
             points_to_draw_list = [p for p in self.points if p not in self.line_points]

        if not hull_points:
            self.clear_fill()
            self._polygon_points_cache = list(points_to_draw_list)
        else:
             self._polygon_points_cache = list(points_to_draw_list)

        points_to_draw = self._polygon_points_cache

        if len(points_to_draw) >= 3:
            flat_points = [coord for point in points_to_draw for coord in point]
            if hull_points:
                 self.hull_id = self.canvas.create_polygon(flat_points, outline="green", width=1, fill="", tags="hull")
            else:
                 self.polygon_id = self.canvas.create_polygon(flat_points, outline=color, width=width, fill=fill_poly, tags="polygon")
            self.canvas.tag_raise("point_marker")
            return True
        return False

    def draw_line_segment(self):
        self.clear_specific_items([self.line_id])
        if len(self.line_points) == 2:
            p1 = self.line_points[0]
            p2 = self.line_points[1]
            self.line_id = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="green", width=2, tags="line")
            self.canvas.tag_raise("point_marker")
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
            nid = self.canvas.create_line(mid_x, mid_y, end_x, end_y, fill="purple", arrow=tk.LAST, tags="normal")
            self.normal_ids.append(nid)
        self.update_status("Отображены внутренние нормали.")

    def draw_intersection_point(self, x, y):
        size = 4
        ipid = self.canvas.create_oval(x - size, y - size, x + size, y + size, fill="orange", outline="black", tags="intersection")
        self.intersection_point_ids.append(ipid)

    def draw_scanline_fill(self, y, x_start, x_end, color):
        self.canvas.create_line(int(x_start), y, int(x_end) + 1, y, fill=color, width=1, tags=(FILL_ITEM_TAG, "fill_scanline"))
        if self.debug_mode.get():
            self.master.update()
            time.sleep(DEBUG_DELAY_MS / 1000.0)

    def draw_fill_pixel(self, x, y, color):
        self.canvas.create_rectangle(x, y, x+1, y+1, fill=color, outline=color, tags=(FILL_ITEM_TAG, "fill_pixel"))

    def get_polygon_points(self):
        if self._polygon_points_cache:
             return self._polygon_points_cache

        # Формируем полигон из точек, не являющихся частью линии
        current_poly_points = [p for p in self.points if p not in self.line_points]

        if len(current_poly_points) >= 3:
            if not self.polygon_id and not self.hull_id: # Если полигон не нарисован
                 self.draw_polygon_final() # Рисуем основной полигон, это обновит кэш
            elif not self._polygon_points_cache: # Если нарисован, но кэш пуст
                 self._polygon_points_cache = current_poly_points
            return self._polygon_points_cache
        else:
            return None


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
        temp_poly_points = list(poly_points)
        if area < 0:
            temp_poly_points = temp_poly_points[::-1]
            print("Полигон был по часовой стрелке, нормали посчитаны для CCW.")
        normals = []
        for i in range(n):
            p1 = temp_poly_points[i]
            p2 = temp_poly_points[(i + 1) % n]
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

        hull = [points[0], points[1]]
        for i in range(2, n):
            top = hull.pop()
            while len(hull) > 0 and orientation(hull[-1], top, points[i]) != 2:
                top = hull.pop()
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
            if len(hull) > n :
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
        epsilon = 1e-9
        return (q[0] <= max(p[0], r[0]) + epsilon and q[0] >= min(p[0], r[0]) - epsilon and
                q[1] <= max(p[1], r[1]) + epsilon and q[1] >= min(p[1], r[1]) - epsilon)

    def find_intersection_point(self, p1, q1, p2, q2):
        A1 = q1[1] - p1[1]; B1 = p1[0] - q1[0]; C1 = A1 * p1[0] + B1 * p1[1]
        A2 = q2[1] - p2[1]; B2 = p2[0] - q2[0]; C2 = A2 * p2[0] + B2 * p2[1]
        determinant = A1 * B2 - A2 * B1
        epsilon = 1e-9
        if abs(determinant) < epsilon:
            return None
        else:
            x = (B2 * C1 - B1 * C2) / determinant
            y = (A1 * C2 - A2 * C1) / determinant
            on_seg1 = (min(p1[0], q1[0]) - epsilon <= x <= max(p1[0], q1[0]) + epsilon and
                       min(p1[1], q1[1]) - epsilon <= y <= max(p1[1], q1[1]) + epsilon)
            on_seg2 = (min(p2[0], q2[0]) - epsilon <= x <= max(p2[0], q2[0]) + epsilon and
                       min(p2[1], q2[1]) - epsilon <= y <= max(p2[1], q2[1]) + epsilon)
            if on_seg1 and on_seg2: return (x, y)
            else: return None

    def is_point_inside_polygon(self, point, poly_points, check_boundary=True):
        n = len(poly_points)
        if n < 3: return False

        x, y = point
        inside = False
        epsilon = 1e-9

        on_boundary = False
        p1 = poly_points[0]
        for i in range(n + 1):
            p2 = poly_points[i % n]
            if abs(orientation(p1, p2, point)) < epsilon and self.on_segment(p1, point, p2):
                on_boundary = True
                break
            p1 = p2

        if on_boundary:
            return check_boundary

        p1 = poly_points[0]
        for i in range(n + 1):
            p2 = poly_points[i % n]
            y1, y2 = p1[1], p2[1]
            x1, x2 = p1[0], p2[0]

            if y1 == y2: # Игнорируем горизонтальные ребра
                p1 = p2
                continue

            # Проверяем пересечение с лучом y=const
            if min(y1, y2) <= y < max(y1, y2):
                 # Вычисляем x пересечения
                 x_intersection = (y - y1) * (x2 - x1) / (y2 - y1) + x1
                 # Если точка слева от пересечения
                 if x < x_intersection - epsilon: # Добавляем эпсилон для строгого сравнения
                     inside = not inside

            p1 = p2

        return inside

    def build_edge_table(self, poly_points):
        edge_table = defaultdict(list)
        y_min_global = float('inf')
        y_max_global = float('-inf')

        n = len(poly_points)
        for i in range(n):
            p1 = poly_points[i]
            p2 = poly_points[(i + 1) % n]

            if p1[1] == p2[1]: continue

            y_min_edge = min(p1[1], p2[1])
            y_max_edge = max(p1[1], p2[1])
            x_at_y_min = p1[0] if p1[1] < p2[1] else p2[0]

            y_min_global = min(y_min_global, y_min_edge)
            y_max_global = max(y_max_global, y_max_edge)

            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            inv_slope = dx / dy

            edge_entry = EdgeEntry(y_max_edge, x_at_y_min, inv_slope)
            edge_table[y_min_edge].append(edge_entry)

        for y in edge_table:
             edge_table[y].sort(key=lambda e: e.x)

        return edge_table, int(math.ceil(y_min_global)), int(math.floor(y_max_global))


    def scanline_fill_et_aet(self, poly_points, fill_color):
        edge_table, y_min, y_max = self.build_edge_table(poly_points)
        if y_min == float('inf') or y_min >= y_max : return

        active_edge_table = []
        # Начинаем со строки, где есть первое ребро
        current_y = min(y for y in edge_table if edge_table[y]) if edge_table else y_max
        y_min = current_y # Обновляем y_min до реального начала

        scanline_marker = None
        if self.debug_mode.get():
            scanline_marker = self.canvas.create_line(0, current_y, self.canvas.winfo_width(), current_y, fill="gray", dash=(2, 2), tags="debug")

        while current_y < y_max: # Условие изменено на < y_max
            if self.debug_mode.get() and scanline_marker:
                 self.canvas.coords(scanline_marker, 0, current_y, self.canvas.winfo_width(), current_y)
                 aet_info = sorted([f"{e.x:.1f}({e.y_max})" for e in active_edge_table])
                 self.update_status(f"Сканлайн Y={current_y}, AET({len(active_edge_table)}): {aet_info}")
                 self.master.update()
                 time.sleep(DEBUG_DELAY_MS / 1000.0)

            # Удаляем ребра, чей y_max <= текущей строки (было ==)
            active_edge_table = [edge for edge in active_edge_table if edge.y_max > current_y]

            if current_y in edge_table:
                active_edge_table.extend(edge_table[current_y])

            active_edge_table.sort()

            for i in range(0, len(active_edge_table), 2):
                if i + 1 < len(active_edge_table):
                    x_start = math.ceil(active_edge_table[i].x)
                    x_end = math.floor(active_edge_table[i+1].x)
                    if x_start <= x_end:
                        self.draw_scanline_fill(current_y, x_start, x_end, fill_color)

            current_y += 1

            for edge in active_edge_table:
                 edge.x += edge.inv_slope

            # Выходим, если AET пуста И больше нет ребер в ET для добавления
            if not active_edge_table and not any(y >= current_y for y in edge_table):
                  break

        if self.debug_mode.get() and scanline_marker:
            self.canvas.delete(scanline_marker)

    def scanline_fill_aet_only(self, poly_points, fill_color):
        self.scanline_fill_et_aet(poly_points, fill_color)

    def simple_seed_fill(self, seed_x, seed_y, fill_color, poly_points):
        if not poly_points or len(poly_points) < 3: return

        if not self.is_point_inside_polygon((seed_x, seed_y), poly_points, check_boundary=False):
             messagebox.showerror("Ошибка Затравки", "Начальная точка находится вне полигона или на его границе.")
             self.update_status("Ошибка: Неверная точка затравки.")
             return

        q = deque([(seed_x, seed_y)])
        painted = set([(seed_x, seed_y)])
        self.draw_fill_pixel(seed_x, seed_y, fill_color)

        max_x = self.canvas.winfo_width()
        max_y = self.canvas.winfo_height()
        processed_count = 0

        while q:
            if processed_count > PIXEL_CHECK_LIMIT:
                 print(f"Предупреждение: Simple Seed Fill превысил лимит проверок ({PIXEL_CHECK_LIMIT}). Прервано.")
                 messagebox.showwarning("Заливка Прервана", "Алгоритм заливки обработал слишком много пикселей и был остановлен.")
                 break

            x, y = q.popleft()
            processed_count += 1

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy

                if not (0 <= nx < max_x and 0 <= ny < max_y):
                    continue

                if (nx, ny) in painted:
                    continue

                if self.is_point_inside_polygon((nx, ny), poly_points, check_boundary=False):
                    self.draw_fill_pixel(nx, ny, fill_color)
                    painted.add((nx, ny))
                    q.append((nx, ny))

                    if self.debug_mode.get() and processed_count % 100 == 0:
                         self.update_status(f"Заливка: {processed_count} пикс.")
                         self.master.update()


        self.update_status(f"Простая затравка: Закрашено ~{len(painted)} пикс.")

    def scanline_seed_fill(self, seed_x, seed_y, fill_color, poly_points):
        if not poly_points or len(poly_points) < 3: return

        if not self.is_point_inside_polygon((seed_x, seed_y), poly_points, check_boundary=False):
            messagebox.showerror("Ошибка Затравки", "Начальная точка находится вне полигона или на его границе.")
            self.update_status("Ошибка: Неверная точка затравки.")
            return

        q = deque([(seed_x, seed_y)])
        processed_seeds = set([(seed_x, seed_y)])

        max_x = self.canvas.winfo_width()
        max_y = self.canvas.winfo_height()
        processed_count = 0
        painted_pixel_count = 0

        def is_pixel_strictly_inside(x, y):
            nonlocal processed_count
            processed_count +=1
            if not (0 <= x < max_x and 0 <= y < max_y): return False
            if processed_count > PIXEL_CHECK_LIMIT: return False
            return self.is_point_inside_polygon((x, y), poly_points, check_boundary=False)

        while q:
            if processed_count > PIXEL_CHECK_LIMIT:
                 print(f"Предупреждение: Scanline Seed Fill превысил лимит проверок ({PIXEL_CHECK_LIMIT}). Прервано.")
                 messagebox.showwarning("Заливка Прервана", "Алгоритм заливки обработал слишком много пикселей и был остановлен.")
                 break

            x_seed, y_seed = q.popleft()

            x_left = x_seed
            while is_pixel_strictly_inside(x_left - 1, y_seed):
                x_left -= 1

            x_right = x_seed
            while is_pixel_strictly_inside(x_right + 1, y_seed):
                x_right += 1

            # Проверяем, не был ли этот спан уже закрашен (достаточно проверить одну точку)
            # Это нужно, т.к. разные затравки могут вести к одному спану
            if (x_left, y_seed) in processed_seeds and (x_right, y_seed) in processed_seeds:
                 continue

            self.draw_scanline_fill(y_seed, x_left, x_right, fill_color)
            painted_pixel_count += (x_right - x_left + 1)

            for x_span in range(x_left, x_right + 1):
                processed_seeds.add((x_span, y_seed))

            y_above = y_seed - 1
            if y_above >= 0:
                x_curr = x_left
                while x_curr <= x_right:
                    found_potential_seed = False
                    start_span = -1
                    while x_curr <= x_right and is_pixel_strictly_inside(x_curr, y_above):
                         if (x_curr, y_above) not in processed_seeds:
                              found_potential_seed = True
                              if start_span == -1: start_span = x_curr # Запоминаем начало потенциального спана
                         x_curr += 1

                    if found_potential_seed and start_span != -1:
                         # Добавляем только одну затравку для найденного интервала (например, первую точку)
                         seed_candidate = (start_span, y_above)
                         # Проверяем еще раз перед добавлением
                         if seed_candidate not in processed_seeds:
                              q.append(seed_candidate)
                              # Помечаем всю найденную линию как обработанную, чтобы не добавлять ее снова
                              # Это может быть не оптимально, но предотвращает дублирование
                              for x_p in range(start_span, x_curr):
                                   processed_seeds.add((x_p, y_above))


                    while x_curr <= x_right and not is_pixel_strictly_inside(x_curr, y_above):
                        x_curr += 1

            y_below = y_seed + 1
            if y_below < max_y:
                x_curr = x_left
                while x_curr <= x_right:
                    found_potential_seed = False
                    start_span = -1
                    while x_curr <= x_right and is_pixel_strictly_inside(x_curr, y_below):
                        if (x_curr, y_below) not in processed_seeds:
                            found_potential_seed = True
                            if start_span == -1: start_span = x_curr
                        x_curr += 1

                    if found_potential_seed and start_span != -1:
                        seed_candidate = (start_span, y_below)
                        if seed_candidate not in processed_seeds:
                            q.append(seed_candidate)
                            for x_p in range(start_span, x_curr):
                                processed_seeds.add((x_p, y_below))

                    while x_curr <= x_right and not is_pixel_strictly_inside(x_curr, y_below):
                        x_curr += 1

            if self.debug_mode.get():
                 self.update_status(f"Заливка: {processed_count} пр./{painted_pixel_count} пкс.")
                 self.master.update()

        if processed_count <= PIXEL_CHECK_LIMIT:
            self.update_status(f"Построчная затравка: ~{painted_pixel_count} пикс.")

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
        self.seed_point = None
        self.seed_marker_id = None
        self.waiting_for_seed = False
        self._polygon_points_cache = None
        self.fill_color.set(DEFAULT_FILL_COLOR)
        self.fill_color_label.config(bg=self.fill_color.get(), text=f"Цвет: {self.fill_color.get()}")
        self.update_status("Холст очищен.")

    def clear_fill(self):
        self.canvas.delete(FILL_ITEM_TAG)
        self.clear_specific_items([self.seed_marker_id])
        self.seed_marker_id = None
        self.seed_point = None

    def clear_specific_items(self, item_ids_or_tags):
        for item_id_or_tag in item_ids_or_tags:
            if item_id_or_tag:
                self.canvas.delete(item_id_or_tag)

    def check_convexity_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showwarning("Проверка Выпуклости", "Пожалуйста, сначала нарисуйте и завершите полигон (минимум 3 точки, правый клик).")
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
            messagebox.showwarning("Показать Нормали", "Пожалуйста, сначала нарисуйте и завершите полигон.")
            return
        target_poly = poly
        is_hull = bool(self.hull_id)

        if is_hull and self._polygon_points_cache:
             target_poly = self._polygon_points_cache
             print("Показ нормалей для выпуклой оболочки.")
        else:
             target_poly = self._polygon_points_cache if self._polygon_points_cache else [p for p in self.points if p not in self.line_points]
             print("Показ нормалей для исходного полигона.")
             if not self.is_convex(target_poly):
                  messagebox.showwarning("Показать Нормали", "Исходный полигон невыпуклый. Внутренние нормали могут быть некорректны.")


        normals_data = self.calculate_inner_normals(list(target_poly))

        if normals_data:
            self.draw_normals(normals_data)
            norm_target = "выпуклой оболочки" if is_hull else "полигона"
            self.update_status(f"Отображены внутренние нормали для {norm_target}.")
        else:
             messagebox.showerror("Показать Нормали", "Не удалось рассчитать нормали.")
             self.update_status("Не удалось рассчитать нормали.")

    def run_hull_algorithm(self, points_to_hull):
        method = self.selected_hull_method.get()
        # Используем только точки полигона (не линии) для построения оболочки
        poly_points_only = [p for p in points_to_hull if p not in self.line_points]
        if len(poly_points_only) < 3:
            messagebox.showwarning("Выпуклая Оболочка", "Нужно минимум 3 точки полигона для построения выпуклой оболочки.")
            return None
        try:
            start_time = time.time()
            if method == "graham":
                hull_points = self.graham_scan(poly_points_only)
            elif method == "jarvis":
                hull_points = self.jarvis_march(poly_points_only)
            else:
                messagebox.showerror("Выпуклая Оболочка", "Выбран неверный метод построения оболочки.")
                return None
            end_time = time.time()
            print(f"Hull ({method}) computed in {end_time - start_time:.4f}s for {len(poly_points_only)} points -> {len(hull_points)} hull points")
            return hull_points
        except Exception as e:
            messagebox.showerror("Ошибка Вычисления Оболочки", f"Произошла ошибка: {e}")
            print(f"Ошибка при вычислении оболочки ({method}): {e}")
            traceback.print_exc()
            return None


    def compute_convex_hull_action(self):
        poly_points_only = [p for p in self.points if p not in self.line_points]
        if len(poly_points_only) < 3:
             messagebox.showwarning("Выпуклая Оболочка", "Нужно минимум 3 исходные точки полигона.")
             return
        self.clear_specific_items([self.hull_id] + self.normal_ids)
        self.hull_id = None
        self.normal_ids = []
        self.clear_fill()

        hull_points = self.run_hull_algorithm(self.points) # Передаем все точки, функция отфильтрует

        if hull_points:
            method_name_map = {"graham": "Грэхема", "jarvis": "Джарвиса"}
            method_name = method_name_map.get(self.selected_hull_method.get(), "Неизвестный метод")
            self.update_status(f"Выпуклая оболочка ({method_name}) построена с {len(hull_points)} вершинами.")
            self.draw_polygon_final(hull_points=hull_points)


    def run_hull(self, method):
         self.selected_hull_method.set(method)
         self.compute_convex_hull_action()


    def find_intersections_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showwarning("Поиск Пересечений", "Пожалуйста, сначала нарисуйте и завершите полигон.")
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

            intersection = self.find_intersection_point(line_p1, line_p2, poly_p1, poly_p2)
            if intersection:
                 is_duplicate = False
                 for found_p in intersections_found:
                     if dist_sq(intersection, found_p) < 1e-6:
                         is_duplicate = True
                         break
                 if not is_duplicate:
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
            self.update_status("Тест точки: Сначала нарисуйте и завершите полигон.")
            return

        point = (x, y)
        temp_marker = self.canvas.create_oval(x-2, y-2, x+2, y+2, fill="cyan", outline="black", tags="debug")

        on_boundary = False
        p1 = poly[0]
        n = len(poly)
        epsilon = 1e-9
        for i in range(n + 1):
            p2 = poly[i % n]
            if abs(orientation(p1, p2, point)) < epsilon and self.on_segment(p1, point, p2):
                on_boundary = True
                break
            p1 = p2

        if on_boundary:
             result_text = "НА ГРАНИЦЕ"
        elif self.is_point_inside_polygon(point, poly, check_boundary=False):
             result_text = "ВНУТРИ"
        else:
             result_text = "СНАРУЖИ"

        messagebox.showinfo("Тест Точки в Полигоне", f"Точка ({x}, {y}) находится {result_text} полигона.")
        self.update_status(f"Тест: Точка ({x}, {y}) {result_text} полигона.")

        self.master.after(2000, lambda: self.canvas.delete(temp_marker))

    def fill_polygon_action(self):
        poly = self.get_polygon_points()
        if not poly:
            messagebox.showerror("Ошибка Заливки", "Сначала нарисуйте и завершите полигон (правый клик).")
            return

        self.clear_fill()

        algo = self.selected_fill_algorithm.get()

        if algo in ["simple_seed_fill", "scanline_seed_fill"]:
            self._polygon_points_cache = list(poly)
            self.waiting_for_seed = True
            self.update_status("Ожидание точки затравки: Кликните ВНУТРИ полигона.")
        else:
            self._polygon_points_cache = list(poly)
            self.seed_point = None
            self._execute_fill()


    def _execute_fill(self):
        poly = self._polygon_points_cache
        if not poly:
            messagebox.showerror("Ошибка Заливки", "Не найдены точки полигона для заливки.")
            self.update_status("Ошибка: Не найден полигон.")
            self.waiting_for_seed = False
            return

        algo = self.selected_fill_algorithm.get()
        fill_c = self.fill_color.get()
        algo_rus = self.fill_algorithm_translations.get(algo, algo)
        start_time = time.time()

        self.update_status(f"Заливка '{algo_rus}' начата...")
        self.master.update()

        try:
            poly_copy = list(poly)
            if algo == "scanline_et_aet":
                self.scanline_fill_et_aet(poly_copy, fill_c)
            elif algo == "scanline_aet":
                self.scanline_fill_aet_only(poly_copy, fill_c)
            elif algo == "simple_seed_fill":
                if self.seed_point:
                    self.simple_seed_fill(self.seed_point[0], self.seed_point[1], fill_c, poly_copy)
                else:
                    messagebox.showerror("Ошибка Заливки", "Точка затравки не была выбрана.")
                    self.update_status("Ошибка: Затравка не выбрана.")
                    return
            elif algo == "scanline_seed_fill":
                 if self.seed_point:
                    self.scanline_seed_fill(self.seed_point[0], self.seed_point[1], fill_c, poly_copy)
                 else:
                    messagebox.showerror("Ошибка Заливки", "Точка затравки не была выбрана.")
                    self.update_status("Ошибка: Затравка не выбрана.")
                    return
            else:
                messagebox.showerror("Ошибка", f"Неизвестный алгоритм заливки: {algo}")
                self.update_status(f"Ошибка: Неизвестный алгоритм {algo}.")
                return

            end_time = time.time()
            duration = end_time - start_time
            final_status = self.status_label.cget("text")
            if not final_status.startswith(("Заливка", "Построчная", "Простая")):
                  self.update_status(f"{final_status} (за {duration:.3f} сек.)")
            elif not final_status.endswith("сек.)") and not final_status.endswith("пикс.") and not final_status.endswith("пкс."):
                 self.update_status(f"{final_status} (за {duration:.3f} сек.)")


        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            messagebox.showerror("Ошибка во время Заливки", f"Произошла ошибка: {e}\nАлгоритм: {algo_rus}\nВремя: {duration:.3f} сек.")
            self.update_status(f"Ошибка при заливке '{algo_rus}'.")
            print(f"Ошибка при заливке ({algo}): {e}")
            traceback.print_exc()
        finally:
             self.waiting_for_seed = False
             self.canvas.tag_raise("point_marker")
             self.canvas.tag_raise("line")
             self.canvas.tag_raise("intersection")
             self.canvas.tag_raise("seed_marker")


if __name__ == "__main__":
    root = tk.Tk()
    app = PolygonEditor(root)
    root.mainloop()