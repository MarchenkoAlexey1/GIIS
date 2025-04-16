import tkinter as tk
from tkinter import ttk
import numpy as np
import math

M_H = np.array([
    [ 2, -2,  1,  1],
    [-3,  3, -2, -1],
    [ 0,  0,  1,  0],
    [ 1,  0,  0,  0]
])

M_B = np.array([
    [-1,  3, -3,  1],
    [ 3, -6,  3,  0],
    [-3,  3,  0,  0],
    [ 1,  0,  0,  0]
])

M_BS = (1/6) * np.array([
    [-1,  3, -3,  1],
    [ 3, -6,  3,  0],
    [-3,  0,  3,  0],
    [ 1,  4,  1,  0]
])

class CurveEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Графический редактор кривых v2")
        self.geometry("800x600")

        self.all_control_points = []
        self.all_control_point_items = []
        self.active_point_indices = []

        self.curve_segments = []
        self.curve_type = tk.StringVar(value="bezier")
        self.stitching_mode = tk.BooleanVar(value=False)
        self.num_steps = 50
        self.point_radius = 4
        self.selected_point_index = None
        self.drag_offset = (0, 0)

        self._setup_ui()
        self._setup_bindings()
        self._update_status()

    def _setup_ui(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Очистить", command=self.clear_canvas)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)

        curve_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Кривые", menu=curve_menu)
        curve_menu.add_radiobutton(label="Эрмит", variable=self.curve_type, value="hermite", command=self._on_curve_type_change)
        curve_menu.add_radiobutton(label="Безье", variable=self.curve_type, value="bezier", command=self._on_curve_type_change)
        curve_menu.add_radiobutton(label="B-сплайн", variable=self.curve_type, value="bspline", command=self._on_curve_type_change)
        curve_menu.add_separator()
        curve_menu.add_checkbutton(label="Состыковка сегментов", variable=self.stitching_mode,
                                   onvalue=True, offvalue=False, command=self._on_stitching_mode_change)

        toolbar = ttk.Frame(self, padding="5")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(toolbar, text="Кривые:").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(toolbar, text="Эрмит", variable=self.curve_type, value="hermite", command=self._on_curve_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Безье", variable=self.curve_type, value="bezier", command=self._on_curve_type_change).pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="B-сплайн", variable=self.curve_type, value="bspline", command=self._on_curve_type_change).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Checkbutton(toolbar, text="Состыковка", variable=self.stitching_mode,
                        command=self._on_stitching_mode_change).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(toolbar, text="Очистить", command=self.clear_canvas).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self, bg="white", cursor="crosshair")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(self, text="", anchor=tk.W, padding="2 5")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _setup_bindings(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<ButtonPress-3>", self.on_canvas_press_right)
        self.canvas.bind("<B3-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-3>", self.on_canvas_release_right)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

    def _on_curve_type_change(self):
        if self.active_point_indices:
             print("Тип кривой изменен, незавершенный ввод точек сброшен.")
             self.active_point_indices = []
        self._update_status()

    def _on_stitching_mode_change(self):
        if self.active_point_indices:
            print("Режим состыковки изменен, незавершенный ввод точек сброшен.")
            self.active_point_indices = []
        self._update_status()

    def _update_status(self):
        curve_name = self.curve_type.get().capitalize()
        req_points = self._get_required_points_for_segment()
        current_points_for_segment = len(self.active_point_indices)
        stitching = "ВКЛ" if self.stitching_mode.get() else "ВЫКЛ"
        total_points = len(self.all_control_points)

        status_parts = [f"Кривая: {curve_name}", f"Состыковка: {stitching}"]

        if self.selected_point_index is not None:
             status_parts.append(f"Перетаскивание точки {self.selected_point_index}")
        else:
             points_needed_now = req_points - current_points_for_segment
             if points_needed_now > 0:
                 status_parts.append(f"Нужно точек для сегмента: {points_needed_now}/{req_points}")
                 if curve_name == "Hermite":
                     points_desc = ["P0", "P1", "T0_pt", "T1_pt"]
                     if current_points_for_segment < 4:
                         status_parts.append(f"Ожидание: {points_desc[current_points_for_segment]}")
             else:
                 status_parts.append("Готово к вводу нового сегмента")

        status_parts.append(f"Всего точек: {total_points}")
        self.status_label.config(text=" | ".join(status_parts))

    def _get_required_points_for_segment(self):
        curve = self.curve_type.get()
        if curve in ["hermite", "bezier", "bspline"]:
            return 4
        return 0

    def _get_new_points_needed(self):
        req_total = self._get_required_points_for_segment()
        already_have = len(self.active_point_indices)
        return max(0, req_total - already_have)

    def clear_canvas(self):
        self.canvas.delete("all")
        self.all_control_points = []
        self.all_control_point_items = []
        self.active_point_indices = []
        self.curve_segments = []
        self.selected_point_index = None
        print("Холст очищен.")
        self._update_status()

    def on_canvas_motion(self, event):
         pass

    def on_canvas_click(self, event):
        if self._get_new_points_needed() == 0 and not self.stitching_mode.get():
             self.active_point_indices = []

        if self._get_new_points_needed() == 0 and self.stitching_mode.get():
             pass

        x, y = event.x, event.y

        self.all_control_points.append((x, y))
        item_id = self._draw_point(x, y)
        self.all_control_point_items.append(item_id)
        new_point_index = len(self.all_control_points) - 1

        self.active_point_indices.append(new_point_index)

        req_points = self._get_required_points_for_segment()
        print(f"Добавлена точка (глоб. индекс {new_point_index}): ({x}, {y}). Активные индексы: {self.active_point_indices} ({len(self.active_point_indices)}/{req_points})")

        if len(self.active_point_indices) == req_points:
            self.draw_curve()
            if self.stitching_mode.get():
                 self._prepare_for_stitching()
            else:
                 self.active_point_indices = []

        self._update_status()

    def _prepare_for_stitching(self):
        curve = self.curve_type.get()

        if not self.curve_segments:
             self.active_point_indices = []
             return

        last_segment_indices = self.curve_segments[-1]['points_indices']
        new_active_indices = []

        if curve == "hermite":
            p1_index = last_segment_indices[1]
            new_active_indices = [p1_index]
            print(f"Состыковка (Эрмит C0): Используем индекс {p1_index} как P0. Нужно еще 3 точки.")

        elif curve == "bezier":
            p3_index = last_segment_indices[3]
            new_active_indices = [p3_index]
            print(f"Состыковка (Безье C0): Используем индекс {p3_index} как P0. Нужно еще 3 точки.")

        elif curve == "bspline":
             if len(last_segment_indices) == 4:
                 indices_to_keep = last_segment_indices[1:]
                 new_active_indices = list(indices_to_keep)
                 print(f"Состыковка (B-сплайн): Используем индексы {new_active_indices}. Нужно еще 1 точку.")
             else:
                 print("Ошибка: Недостаточно индексов в предыдущем B-сплайн сегменте для состыковки.")
                 new_active_indices = []

        self.active_point_indices = new_active_indices

    def on_canvas_press_right(self, event):
        x, y = event.x, event.y
        self.selected_point_index = None
        min_dist_sq = (self.point_radius * 4)**2
        found_idx = -1

        for idx, pt in enumerate(self.all_control_points):
             px, py = pt
             dist_sq = (x - px)**2 + (y - py)**2
             if dist_sq < min_dist_sq:
                 item_id = self.all_control_point_items[idx]
                 if self.canvas.winfo_exists() and item_id in self.canvas.find_all():
                     min_dist_sq = dist_sq
                     found_idx = idx

        if found_idx != -1:
             self.selected_point_index = found_idx
             px, py = self.all_control_points[self.selected_point_index]
             self.drag_offset = (px - x, py - y)
             item_id = self.all_control_point_items[self.selected_point_index]
             self.canvas.itemconfig(item_id, fill="red")
             self.canvas.config(cursor="hand2")
             print(f"Захвачена точка (глоб. индекс {self.selected_point_index})")
        else:
             self.selected_point_index = None
             self.canvas.config(cursor="crosshair")
        self._update_status()

    def on_canvas_drag(self, event):
        if self.selected_point_index is not None:
            x = max(0, min(event.x + self.drag_offset[0], self.canvas.winfo_width()))
            y = max(0, min(event.y + self.drag_offset[1], self.canvas.winfo_height()))

            self.all_control_points[self.selected_point_index] = (x, y)

            item_id = self.all_control_point_items[self.selected_point_index]
            if self.canvas.winfo_exists() and item_id in self.canvas.find_all():
                 self.canvas.coords(item_id,
                                   x - self.point_radius, y - self.point_radius,
                                   x + self.point_radius, y + self.point_radius)
                 self._redraw_affected_curves(self.selected_point_index)
                 self._update_status()
            else:
                 print(f"Warning: Canvas item {item_id} for point {self.selected_point_index} not found during drag.")
                 self.selected_point_index = None
                 self.canvas.config(cursor="crosshair")
                 self._update_status()

    def on_canvas_release_right(self, event):
        if self.selected_point_index is not None:
            idx = self.selected_point_index
            item_id = self.all_control_point_items[idx]
            if self.canvas.winfo_exists() and item_id in self.canvas.find_all():
                 try:
                     self.canvas.itemconfig(item_id, fill="blue")
                 except tk.TclError:
                     print(f"Warning: Canvas item {item_id} for point {idx} not found on release.")

            print(f"Отпущена точка {self.selected_point_index}")
            self.selected_point_index = None
            self.canvas.config(cursor="crosshair")
            self._update_status()

    def _draw_point(self, x, y):
        radius = self.point_radius
        return self.canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                                       fill="blue", outline="black", tags="point")

    def _redraw_affected_curves(self, changed_point_index):
        print(f"Перерисовка кривых, затронутых точкой {changed_point_index}")
        for i, segment in enumerate(self.curve_segments):
            if changed_point_index in segment['points_indices']:
                print(f"  - Сегмент {i} (тип {segment['type']}, точки {segment['points_indices']}) затронут.")
                for line_id in segment['line_ids']:
                     if self.canvas.winfo_exists() and line_id in self.canvas.find_all():
                         self.canvas.delete(line_id)

                try:
                    segment_points_coords = [self.all_control_points[idx] for idx in segment['points_indices']]
                except IndexError:
                     print(f"Ошибка: Индекс точки вне диапазона при перерисовке сегмента {i}.")
                     continue

                new_line_ids = self._draw_curve_segment(segment['type'], segment_points_coords)
                self.curve_segments[i]['line_ids'] = new_line_ids
                print(f"  - Сегмент {i} перерисован.")

    def draw_curve(self):
        curve = self.curve_type.get()
        current_segment_indices = list(self.active_point_indices)

        if len(current_segment_indices) != self._get_required_points_for_segment():
             print(f"Ошибка: Недостаточно активных индексов для {curve}. Нужно {self._get_required_points_for_segment()}, есть {len(current_segment_indices)}")
             return

        try:
            segment_points_coords = [self.all_control_points[idx] for idx in current_segment_indices]
        except IndexError as e:
             print(f"Ошибка: Неверный индекс точки при попытке нарисовать кривую: {e}")
             print(f"  Индексы: {current_segment_indices}")
             print(f"  Всего точек: {len(self.all_control_points)}")
             self.active_point_indices = []
             self._update_status()
             return

        print(f"Рисуем {curve} с точками (индексы): {current_segment_indices}")
        print(f"Координаты: {segment_points_coords}")

        line_ids = self._draw_curve_segment(curve, segment_points_coords)

        if line_ids:
            self.curve_segments.append({
                'type': curve,
                'points_indices': current_segment_indices,
                'line_ids': line_ids
            })
            print(f"Сегмент сохранен. Всего сегментов: {len(self.curve_segments)}")
        else:
             print("Не удалось нарисовать сегмент.")

    def _draw_curve_segment(self, curve_type, points_coords):
        line_ids = []
        calculated_points = []
        pts = np.array(points_coords)

        if len(pts) != 4:
             print(f"Ошибка (_draw_curve_segment): Ожидалось 4 точки, получено {len(pts)}")
             return []

        if curve_type == "hermite":
            P0 = pts[0]
            P1 = pts[1]
            T0 = pts[2] - P0
            T1 = pts[3] - P1
            G_H = np.array([P0, P1, T0, T1])

            for i in range(self.num_steps + 1):
                t = i / self.num_steps
                T_vec = np.array([t**3, t**2, t, 1])
                point = T_vec @ M_H @ G_H
                calculated_points.append(point)

        elif curve_type == "bezier":
            G_B = pts
            for i in range(self.num_steps + 1):
                t = i / self.num_steps
                T_vec = np.array([t**3, t**2, t, 1])
                point = T_vec @ M_B @ G_B
                calculated_points.append(point)

        elif curve_type == "bspline":
            G_BS = pts
            for i in range(self.num_steps + 1):
                t = i / self.num_steps
                T_vec = np.array([t**3, t**2, t, 1])
                point = T_vec @ M_BS @ G_BS
                calculated_points.append(point)

        if len(calculated_points) > 1:
            color = "red" if curve_type=="hermite" else "green" if curve_type=="bezier" else "purple"
            width = 2
            tag = f"curve_segment_{len(self.curve_segments)}"
            for i in range(len(calculated_points) - 1):
                p1 = calculated_points[i]
                p2 = calculated_points[i+1]
                line_id = self.canvas.create_line(p1[0], p1[1], p2[0], p2[1],
                                                   fill=color, width=width, tags=("curve", tag))
                line_ids.append(line_id)

        return line_ids

if __name__ == "__main__":
    app = CurveEditor()
    app.mainloop()