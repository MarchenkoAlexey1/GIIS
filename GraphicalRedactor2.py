import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import math
import time

def calculate_circle_points(cx, cy, r):
    points = []
    if r < 1: return points
    steps = max(8, int(2 * math.pi * r / 1.5))
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        x = cx + r * math.cos(t)
        y = cy + r * math.sin(t)
        point = (round(x), round(y))
        if not points or point != points[-1]:
             points.append(point)
    return points

def calculate_ellipse_points(cx, cy, rx, ry):
    points = []
    if rx < 1 or ry < 1: return points
    steps = max(8, int(math.pi * (1.5 * (rx + ry) - math.sqrt(rx * ry)) / 1.5))
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        x = cx + rx * math.cos(t)
        y = cy + ry * math.sin(t)
        point = (round(x), round(y))
        if not points or point != points[-1]:
            points.append(point)
    return points

def calculate_parabola_points(vx, vy, px, py):
    points = []
    dx = px - vx
    dy = py - vy

    if abs(dx) < 1e-6:
        if abs(dy) < 1e-6: return []
        k = dx / (dy**2)
        y_range = 2.5 * abs(dy)
        steps = 100
        for i in range(steps + 1):
            delta_y = -y_range + (2 * y_range * i / steps)
            y = vy + delta_y
            x = vx + k * (delta_y**2)
            point = (round(x), round(y))
            if not points or point != points[-1]:
                points.append(point)
        points.sort(key=lambda p: p[1])

    else:
        if abs(dx) < 1e-6: return []
        k = dy / (dx**2)
        x_range = 2.5 * abs(dx)
        steps = 100
        for i in range(steps + 1):
            delta_x = -x_range + (2 * x_range * i / steps)
            x = vx + delta_x
            y = vy + k * (delta_x**2)
            point = (round(x), round(y))
            if not points or point != points[-1]:
                points.append(point)
        points.sort(key=lambda p: p[0])

    return points


def calculate_hyperbola_points(cx, cy, ax, ay, bx, by):
    points_branch1 = []
    points_branch2 = []

    dx_a = ax - cx
    dy_a = ay - cy
    dx_b = bx - cx
    dy_b = by - cy

    is_horizontal = abs(dx_a) >= abs(dy_a)

    if is_horizontal:
        a = abs(dx_a)
        if a < 1: return [], []
        if abs(dx_b) > 1e-6:
            b = abs(a * dy_b / dx_b)
        else:
             b = abs(dy_b)

        if b < 1: b = a

        x_limit = a * 3
        steps = 100

        for branch in [1, -1]:
            current_branch_points_pos_y = []
            current_branch_points_neg_y = []
            for i in range(steps + 1):
                 x_rel = a + (x_limit - a) * i / steps
                 x = cx + branch * x_rel
                 try:
                     radicand = (x_rel**2 / a**2) - 1
                     if radicand >= 0:
                         delta_y = b * math.sqrt(radicand)
                         py = round(cy + delta_y)
                         ny = round(cy - delta_y)
                         pt_p = (round(x), py)
                         pt_n = (round(x), ny)
                         if not current_branch_points_pos_y or pt_p != current_branch_points_pos_y[-1]:
                              current_branch_points_pos_y.append(pt_p)
                         if not current_branch_points_neg_y or pt_n != current_branch_points_neg_y[-1]:
                              current_branch_points_neg_y.append(pt_n)
                 except ValueError:
                     pass

            if branch == 1:
                 points_branch1.extend(list(reversed(current_branch_points_neg_y)))
                 points_branch1.extend(current_branch_points_pos_y)
            else:
                 points_branch2.extend(list(reversed(current_branch_points_neg_y)))
                 points_branch2.extend(current_branch_points_pos_y)

    else:
        a = abs(dy_a)
        if a < 1: return [], []
        if abs(dy_b) > 1e-6:
             b = abs(a * dx_b / dy_b)
        else:
             b = abs(dx_b)

        if b < 1: b = a

        y_limit = a * 3
        steps = 100

        for branch in [1, -1]:
             current_branch_points_pos_x = []
             current_branch_points_neg_x = []
             for i in range(steps + 1):
                 y_rel = a + (y_limit - a) * i / steps
                 y = cy + branch * y_rel
                 try:
                     radicand = (y_rel**2 / a**2) - 1
                     if radicand >= 0:
                         delta_x = b * math.sqrt(radicand)
                         px = round(cx + delta_x)
                         nx = round(cx - delta_x)
                         pt_p = (px, round(y))
                         pt_n = (nx, round(y))
                         if not current_branch_points_pos_x or pt_p != current_branch_points_pos_x[-1]:
                              current_branch_points_pos_x.append(pt_p)
                         if not current_branch_points_neg_x or pt_n != current_branch_points_neg_x[-1]:
                              current_branch_points_neg_x.append(pt_n)
                 except ValueError:
                     pass

             if branch == 1:
                 points_branch1.extend(list(reversed(current_branch_points_neg_x)))
                 points_branch1.extend(current_branch_points_pos_x)
             else:
                 points_branch2.extend(list(reversed(current_branch_points_neg_x)))
                 points_branch2.extend(current_branch_points_pos_x)

    return points_branch1, points_branch2


class GraphicalEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Элементарный Графический Редактор")
        self.master.geometry("800x650")

        self.current_tool = None
        self.click_points = []
        self.drawn_objects_ids = []
        self.temp_feedback_items = []

        self.debug_mode = tk.BooleanVar(value=False)
        self.debug_window = None
        self.debug_canvas = None
        self.debug_grid_step = 20
        self.debug_pixel_size = 5
        self.debug_delay_ms = 30

        self.setup_menu()
        self.setup_toolbar()

        self.status_bar = tk.Label(self.master, text="Выберите инструмент", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.setup_canvas()
        self.update_status("Готов. Выберите инструмент из меню или панели.")

    def setup_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Очистить холст", command=self.clear_canvas)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.master.quit)

        curves_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Линии второго порядка", menu=curves_menu)
        curves_menu.add_command(label="Окружность", command=lambda: self.set_tool("Circle"))
        curves_menu.add_command(label="Эллипс", command=lambda: self.set_tool("Ellipse"))
        curves_menu.add_command(label="Парабола", command=lambda: self.set_tool("Parabola"))
        curves_menu.add_command(label="Гипербола", command=lambda: self.set_tool("Hyperbola"))

        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_checkbutton(label="Отладочный режим", variable=self.debug_mode, command=self.toggle_debug_mode)

    def setup_toolbar(self):
        toolbar = tk.Frame(self.master, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        lbl = tk.Label(toolbar, text="Инструменты: ", pady=5)
        lbl.pack(side=tk.LEFT, padx=5)

        buttons = [
            ("Окр", "Circle", "Нарисовать окружность (центр, точка на окружности)"),
            ("Элпс", "Ellipse", "Нарисовать эллипс (центр, точка на оси X, точка на оси Y)"),
            ("Парб", "Parabola", "Нарисовать параболу (вершина, другая точка на параболе)"),
            ("Гипб", "Hyperbola", "Нарисовать гиперболу (центр, точка на оси, точка для наклона)"),
            ("Очст", "Clear", "Очистить холст")
        ]

        for text, tool_name, tooltip in buttons:
            if tool_name == "Clear":
                 btn = ttk.Button(toolbar, text=text, width=5, command=self.clear_canvas)
            else:
                btn = ttk.Button(toolbar, text=text, width=5, command=lambda t=tool_name: self.set_tool(t))
            btn.pack(side=tk.LEFT, padx=2, pady=2)
            btn.bind("<Enter>", lambda e, msg=tooltip: self.update_status(msg))
            btn.bind("<Leave>", lambda e: self.update_status_for_tool())


    def setup_canvas(self):
        self.canvas = tk.Canvas(self.master, bg="white", width=780, height=550)
        self.canvas.pack(pady=5, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)

    def update_status(self, message):
        self.status_bar.config(text=message)

    def update_status_for_tool(self):
        if not self.current_tool:
            self.update_status("Готов. Выберите инструмент.")
            return

        clicks_needed = 0
        action = ""
        if self.current_tool == "Circle":
            clicks_needed = 2
            action = "центр" if len(self.click_points) == 0 else "точку на окружности"
        elif self.current_tool == "Ellipse":
             clicks_needed = 3
             actions = ["центр", "точку на горизонтальной оси", "точку на вертикальной оси"]
             action = actions[len(self.click_points)] if len(self.click_points) < 3 else ""
        elif self.current_tool == "Parabola":
             clicks_needed = 2
             action = "вершину" if len(self.click_points) == 0 else "вторую точку параболы"
        elif self.current_tool == "Hyperbola":
             clicks_needed = 3
             actions = ["центр", "точку на оси", "точку для наклона асимптот"]
             action = actions[len(self.click_points)] if len(self.click_points) < 3 else ""

        if len(self.click_points) < clicks_needed:
             self.update_status(f"{self.current_tool}: Кликните, чтобы задать {action} ({len(self.click_points)}/{clicks_needed})")
        else:
             self.update_status(f"{self.current_tool}: Параметры заданы. Отрисовка...")


    def set_tool(self, tool_name):
        self.current_tool = tool_name
        self.clear_temp_feedback()
        self.click_points = []
        print(f"Tool selected: {self.current_tool}")
        self.update_status_for_tool()

    def clear_temp_feedback(self):
        for item_id in self.temp_feedback_items:
            self.canvas.delete(item_id)
        self.temp_feedback_items = []

    def add_temp_feedback_point(self, x, y):
         r = 3
         item_id = self.canvas.create_oval(x-r, y-r, x+r, y+r, fill="red", outline="red")
         self.temp_feedback_items.append(item_id)

    def on_canvas_click(self, event):
        if not self.current_tool:
            messagebox.showwarning("Нет инструмента", "Пожалуйста, сначала выберите инструмент из меню или панели.")
            return

        x, y = event.x, event.y
        self.click_points.append((x, y))
        self.add_temp_feedback_point(x, y)
        print(f"Clicked at: ({x}, {y}), Points: {len(self.click_points)}")
        self.update_status_for_tool()

        draw_final = False
        if self.current_tool == "Circle" and len(self.click_points) == 2:
            self.draw_circle()
            draw_final = True
        elif self.current_tool == "Ellipse" and len(self.click_points) == 3:
            self.draw_ellipse()
            draw_final = True
        elif self.current_tool == "Parabola" and len(self.click_points) == 2:
            self.draw_parabola()
            draw_final = True
        elif self.current_tool == "Hyperbola" and len(self.click_points) == 3:
            self.draw_hyperbola()
            draw_final = True

        if draw_final:
            self.click_points = []
            self.clear_temp_feedback()
            self.update_status_for_tool()


    def on_canvas_motion(self, event):
        pass

    def draw_curve(self, points_list, curve_type, params_desc):
        if not points_list:
            print("Warning: No points generated for the curve.")
            self.update_status(f"Не удалось построить {curve_type}. Проверьте точки.")
            return

        color = "blue"
        width = 2

        if points_list and isinstance(points_list[0], tuple):
            if len(points_list) > 1:
                canvas_id = self.canvas.create_line(points_list, fill=color, width=width, tags="curve")
                self.drawn_objects_ids.append(canvas_id)
                all_points_for_debug = points_list
            else:
                all_points_for_debug = []

        elif points_list and isinstance(points_list[0], list):
            all_points_for_debug = []
            branch_ids = []
            for branch_points in points_list:
                 if len(branch_points) > 1:
                    canvas_id = self.canvas.create_line(branch_points, fill=color, width=width, tags="curve")
                    branch_ids.append(canvas_id)
                    all_points_for_debug.extend(branch_points)
                 elif len(branch_points) == 1:
                      all_points_for_debug.extend(branch_points)
            if branch_ids:
                 self.drawn_objects_ids.append(branch_ids)

        else:
             all_points_for_debug = []


        self.update_status(f"{curve_type} нарисован(а).")

        if self.debug_mode.get() and all_points_for_debug:
            self.show_debug_steps(all_points_for_debug, curve_type, params_desc)


    def draw_circle(self):
        (cx, cy), (px, py) = self.click_points
        r = math.sqrt((px - cx)**2 + (py - cy)**2)
        if r < 1:
             self.update_status("Радиус слишком мал.")
             return
        points = calculate_circle_points(cx, cy, r)
        self.draw_curve(points, "Окружность", f"Центр:({cx},{cy}), R:{r:.1f}")

    def draw_ellipse(self):
        (cx, cy), (px_x, py_x), (px_y, py_y) = self.click_points
        rx = abs(px_x - cx)
        ry = abs(py_y - cy)
        if rx < 1 or ry < 1:
             self.update_status("Радиусы эллипса слишком малы.")
             return
        points = calculate_ellipse_points(cx, cy, rx, ry)
        self.draw_curve(points, "Эллипс", f"Центр:({cx},{cy}), Rx:{rx:.1f}, Ry:{ry:.1f}")


    def draw_parabola(self):
        (vx, vy), (px, py) = self.click_points
        if abs(vx - px) < 1 and abs(vy - py) < 1:
             self.update_status("Точки параболы слишком близки.")
             return
        points = calculate_parabola_points(vx, vy, px, py)
        self.draw_curve(points, "Парабола", f"Верш:({vx},{vy}), Точка:({px},{py})")

    def draw_hyperbola(self):
        (cx, cy), (ax, ay), (bx, by) = self.click_points
        if (abs(cx-ax)<1 and abs(cy-ay)<1) or \
           (abs(cx-bx)<1 and abs(cy-by)<1) or \
           (abs(ax-bx)<1 and abs(ay-by)<1):
            self.update_status("Точки гиперболы слишком близки или совпадают.")
            return

        points1, points2 = calculate_hyperbola_points(cx, cy, ax, ay, bx, by)
        self.draw_curve([points1, points2], "Гипербола", f"Ц:({cx},{cy}), A:({ax},{ay}), B:({bx},{by})")

    def clear_canvas(self):
         self.canvas.delete("curve")
         self.clear_temp_feedback()
         self.drawn_objects_ids = []
         self.click_points = []
         if self.debug_canvas:
             self.debug_canvas.delete("pixels")
             self.debug_canvas.delete("debug_info")
         self.update_status("Холст очищен.")
         if self.current_tool: self.update_status_for_tool()

    def toggle_debug_mode(self):
        if self.debug_mode.get():
            self.ensure_debug_window()
            self.debug_window.deiconify()
        else:
            if self.debug_window:
                self.debug_window.withdraw()

    def ensure_debug_window(self):
         if not self.debug_window or not tk.Toplevel.winfo_exists(self.debug_window):
             self.debug_window = Toplevel(self.master)
             self.debug_window.title("Отладка - Сетка")
             self.debug_window.geometry("500x550")
             self.debug_window.transient(self.master)

             self.debug_window.protocol("WM_DELETE_WINDOW", self.on_debug_close)

             dbg_canvas_size = 450
             self.debug_canvas = tk.Canvas(self.debug_window, bg="#E0E0E0",
                                           width=dbg_canvas_size, height=dbg_canvas_size,
                                           scrollregion=(0, 0, dbg_canvas_size, dbg_canvas_size)) # Set scroll region if needed later
             self.debug_canvas.pack(pady=10, padx=10)

             self.debug_info_label = tk.Label(self.debug_window, text="Информация:", justify=tk.LEFT)
             self.debug_info_label.pack(fill=tk.X, padx=10)

             self.draw_debug_grid()

             if not self.debug_mode.get():
                  self.debug_window.withdraw()

    def on_debug_close(self):
         self.debug_mode.set(False)
         self.debug_window.withdraw()

    def draw_debug_grid(self):
        if not self.debug_canvas: return
        self.debug_canvas.delete("grid")
        w = int(self.debug_canvas.cget("width"))
        h = int(self.debug_canvas.cget("height"))
        step = self.debug_grid_step

        grid_color = "#B0B0B0"

        for i in range(0, w + 1, step):
            self.debug_canvas.create_line(i, 0, i, h, fill=grid_color, tags="grid")
        for i in range(0, h + 1, step):
            self.debug_canvas.create_line(0, i, w, i, fill=grid_color, tags="grid")

        axis_color = "#808080"
        center_x = (w // (2*step)) * step
        center_y = (h // (2*step)) * step
        self.debug_canvas.create_line(center_x, 0, center_x, h, fill=axis_color, width=1, tags="grid")
        self.debug_canvas.create_line(0, center_y, w, center_y, fill=axis_color, width=1, tags="grid")


    def show_debug_steps(self, points_list, curve_type, params_desc):
         if not self.debug_mode.get() or not points_list: return
         self.ensure_debug_window()
         if not self.debug_canvas: return

         self.debug_canvas.delete("pixels")
         self.debug_canvas.delete("debug_info")
         self.draw_debug_grid()

         self.debug_info_label.config(text=f"Кривая: {curve_type}\nПараметры: {params_desc}\nШаги: ...")
         self.master.update_idletasks()

         total_steps = len(points_list)

         def draw_one_step(step_index):
             if step_index >= total_steps:
                 self.debug_info_label.config(text=f"Кривая: {curve_type}\nПараметры: {params_desc}\nШаги: Готово ({total_steps})")
                 return

             x, y = points_list[step_index]

             dc_w = int(self.debug_canvas.cget("width"))
             dc_h = int(self.debug_canvas.cget("height"))

             info_text = f"Шаг {step_index + 1}/{total_steps}: Координаты ({x},{y})"

             if 0 <= x < dc_w and 0 <= y < dc_h:
                 ps = self.debug_pixel_size
                 x0 = x - ps // 2
                 y0 = y - ps // 2
                 x1 = x0 + ps
                 y1 = y0 + ps
                 self.debug_canvas.create_rectangle(x0, y0, x1, y1, fill="red", outline="red", tags=("pixels", "current_pixel"))
                 info_text += " - Нарисован"
             else:
                  info_text += " - Вне границ отладочного холста"
             self.debug_info_label.config(text=f"Кривая: {curve_type}\nПараметры: {params_desc}\n{info_text}")

             self.debug_canvas.itemconfig("current_pixel", fill="darkred", outline="darkred")
             self.debug_canvas.dtag("current_pixel", "current_pixel") # Remove tag

             self.debug_canvas.after(self.debug_delay_ms, draw_one_step, step_index + 1)

         draw_one_step(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphicalEditor(root)
    root.mainloop()