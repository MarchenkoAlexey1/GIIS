import tkinter as tk
from tkinter import ttk, Menu, colorchooser, Toplevel, Scale, Button, Frame, Label
import math
import time

def draw_line_dda(canvas, x1, y1, x2, y2, color="black", plot_pixel_func=None, collect_steps=False):
    steps_data = []
    if plot_pixel_func is None:
        plot_pixel_func = lambda x, y, c: canvas.create_rectangle(x, y, x+1, y+1, fill=c, outline=c)

    dx = x2 - x1
    dy = y2 - y1

    steps = max(abs(dx), abs(dy))
    if steps == 0:
        plot_pixel_func(round(x1), round(y1), color)
        if collect_steps: steps_data.append((round(x1), round(y1)))
        return steps_data

    x_increment = dx / steps if steps != 0 else 0
    y_increment = dy / steps if steps != 0 else 0

    x = float(x1)
    y = float(y1)

    px_start, py_start = round(x), round(y)
    plot_pixel_func(px_start, py_start, color)
    if collect_steps: steps_data.append((px_start, py_start))

    for i in range(int(steps)):
        x += x_increment
        y += y_increment
        px, py = round(x), round(y)
        if not steps_data or (px, py) != steps_data[-1][:2]:
             plot_pixel_func(px, py, color)
             if collect_steps: steps_data.append((px, py))

    px_end, py_end = round(x2), round(y2)
    if not steps_data or (px_end, py_end) != steps_data[-1][:2]:
         plot_pixel_func(px_end, py_end, color)
         if collect_steps: steps_data.append((px_end, py_end))


    return steps_data

def draw_line_bresenham(canvas, x1, y1, x2, y2, color="black", plot_pixel_func=None, collect_steps=False):
    steps_data = []
    if plot_pixel_func is None:
        plot_pixel_func = lambda x, y, c: canvas.create_rectangle(x, y, x+1, y+1, fill=c, outline=c)

    x1_orig, y1_orig, x2_orig, y2_orig = x1, y1, x2, y2

    x1, y1, x2, y2 = int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))

    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)

    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1

    err = dx + dy
    x, y = x1, y1

    while True:
        if not steps_data or (x, y) != steps_data[-1][:2]:
            plot_pixel_func(x, y, color)
            if collect_steps: steps_data.append((x, y))

        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            if x == x2: break
            err += dy
            x += sx
        if e2 <= dx:
            if y == y2: break
            err += dx
            y += sy

    px_end, py_end = int(round(x2_orig)), int(round(y2_orig))
    if not steps_data or (px_end, py_end) != steps_data[-1][:2]:
         if collect_steps: steps_data.append((px_end, py_end))

    return steps_data


def draw_line_wu(canvas, x1, y1, x2, y2, color="black", plot_pixel_func_intensity=None, collect_steps=False):
    steps_data = []
    if plot_pixel_func_intensity is None:
        def default_plotter(x, y, intensity, base_color):
            gray_val = int(255 * (1.0 - intensity))
            if gray_val < 0: gray_val = 0
            if gray_val > 255: gray_val = 255
            hex_color = f'#{gray_val:02x}{gray_val:02x}{gray_val:02x}'
            canvas.create_rectangle(x, y, x+1, y+1, fill=hex_color, outline=hex_color)
        plot_pixel_func_intensity = default_plotter

    dx = x2 - x1
    dy = y2 - y1
    steep = abs(dy) > abs(dx)

    if steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2
        dx, dy = dy, dx

    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        dx = -dx
        dy = -dy

    gradient = dy / dx if dx != 0 else 1.0

    def ipart(x): return math.floor(x)
    def round_coord(x): return ipart(x + 0.5)
    def fpart(x): return x - math.floor(x)
    def rfpart(x): return 1.0 - fpart(x)

    def plot(x, y, intensity):
        px_plot, py_plot = (int(y), int(x)) if steep else (int(x), int(y))
        is_duplicate = False
        if steps_data:
            last_px, last_py, _ = steps_data[-1]
            if px_plot == last_px and py_plot == last_py:
                 is_duplicate = True

        if not is_duplicate:
            plot_pixel_func_intensity(px_plot, py_plot, intensity, color)
            if collect_steps: steps_data.append((px_plot, py_plot, intensity))

    xend = round_coord(x1)
    yend = y1 + gradient * (xend - x1)
    xgap = rfpart(x1 + 0.5)
    xpxl1 = xend
    ypxl1 = ipart(yend)

    plot(xpxl1, ypxl1, rfpart(yend) * xgap)
    plot(xpxl1, ypxl1 + 1, fpart(yend) * xgap)
    intery = yend + gradient

    xend = round_coord(x2)
    yend = y2 + gradient * (xend - x2)
    xgap = fpart(x2 + 0.5)
    xpxl2 = xend
    ypxl2 = ipart(yend)

    plot(xpxl2, ypxl2, rfpart(yend) * xgap)
    plot(xpxl2, ypxl2 + 1, fpart(yend) * xgap)

    for x in range(int(xpxl1 + 1), int(xpxl2)):
        intensity1 = rfpart(intery)
        intensity2 = fpart(intery)
        y_coord = ipart(intery)

        plot(x, y_coord, intensity1)
        plot(x, y_coord + 1, intensity2)
        intery += gradient

    return steps_data


class LineEditorApp:
    DEFAULT_COLOR = "black"
    DEBUG_GRID_SIZE = 20
    DEBUG_CELL_SIZE = 20
    INITIAL_DEBUG_DELAY = 100

    def __init__(self, root):
        self.root = root
        self.root.title("Line Drawing Editor")
        self.root.geometry("800x600")

        self.current_algorithm = tk.StringVar(value="DDA")
        self.points = []
        self.current_color = self.DEFAULT_COLOR
        self.debug_mode = tk.BooleanVar(value=False)
        self.debug_window = None
        self.debug_canvas = None
        self.debug_steps = []
        self.debug_origin = (0, 0)
        self.debug_step_index = 0
        self.debug_delay_ms = tk.IntVar(value=self.INITIAL_DEBUG_DELAY)
        self.debug_after_id = None

        self._setup_ui()
        self._bind_events()

    def _setup_ui(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)
        algo_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Отрезки", menu=algo_menu)
        algo_menu.add_radiobutton(label="ЦДА (DDA)", variable=self.current_algorithm, value="DDA")
        algo_menu.add_radiobutton(label="Брезенхем (цел.)", variable=self.current_algorithm, value="Bresenham")
        algo_menu.add_radiobutton(label="Ву (Wu)", variable=self.current_algorithm, value="Wu")
        options_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Опции", menu=options_menu)
        options_menu.add_command(label="Выбрать цвет", command=self.choose_color)
        options_menu.add_separator()
        options_menu.add_checkbutton(label="Отладочный режим", variable=self.debug_mode, command=self.toggle_debug_window)
        options_menu.add_separator()
        options_menu.add_command(label="Очистить холст", command=self.clear_canvas)
        options_menu.add_command(label="Выход", command=self.root.quit)

        self.canvas = tk.Canvas(self.root, bg="white", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.status_bar = tk.Label(self.root, text="Выберите первую точку отрезка.", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def choose_color(self):
        color_code = colorchooser.askcolor(title="Выберите цвет отрезка")
        if color_code and color_code[1]:
            self.current_color = color_code[1]
            self.status_bar.config(text=f"Выбран цвет: {self.current_color}. Ожидание первой точки.")

    def on_canvas_click(self, event):
        x, y = event.x, event.y
        self.points.append((x, y))

        if len(self.points) == 1:
            self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=self.current_color, outline=self.current_color, tags="marker")
            self.status_bar.config(text=f"Первая точка: ({x},{y}). Выберите вторую точку.")
        elif len(self.points) == 2:
            self.canvas.delete("marker")
            self.draw_line()
            self.points = []
            self.status_bar.config(text="Отрезок построен. Выберите первую точку нового отрезка.")

    def draw_line(self):
        if len(self.points) != 2:
            return

        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        algo = self.current_algorithm.get()
        collect_for_debug = self.debug_mode.get()

        def plot_pixel_wu_intensity(px, py, intensity, base_color):
            try:
                r_base, g_base, b_base = self.canvas.winfo_rgb(base_color)
                r_base, g_base, b_base = r_base/256, g_base/256, b_base/256
                r = int(r_base * intensity + 255 * (1 - intensity))
                g = int(g_base * intensity + 255 * (1 - intensity))
                b = int(b_base * intensity + 255 * (1 - intensity))
                r, g, b = max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                self.canvas.create_rectangle(px, py, px+1, py+1, fill=hex_color, outline=hex_color, tags="line_segment")
            except Exception:
                gray_val = int(255 * intensity)
                hex_color = f'#{gray_val:02x}{gray_val:02x}{gray_val:02x}'
                self.canvas.create_rectangle(px, py, px+1, py+1, fill=hex_color, outline=hex_color, tags="line_segment")

        def plot_pixel_standard(px, py, color):
            self.canvas.create_rectangle(px, py, px+1, py+1, fill=color, outline=color, tags="line_segment")

        self.debug_steps = []
        if algo == "DDA":
            self.debug_steps = draw_line_dda(self.canvas, x1, y1, x2, y2, self.current_color,
                                             plot_pixel_func=plot_pixel_standard,
                                             collect_steps=collect_for_debug)
        elif algo == "Bresenham":
            self.debug_steps = draw_line_bresenham(self.canvas, x1, y1, x2, y2, self.current_color,
                                                 plot_pixel_func=plot_pixel_standard,
                                                 collect_steps=collect_for_debug)
        elif algo == "Wu":
            self.debug_steps = draw_line_wu(self.canvas, x1, y1, x2, y2, self.current_color,
                                             plot_pixel_func_intensity=plot_pixel_wu_intensity,
                                             collect_steps=collect_for_debug)

        if collect_for_debug and self.debug_window and self.debug_canvas:
            self.debug_origin = (int(round(x1)), int(round(y1)))
            self.stop_debug_visualization()
            self.debug_canvas.delete("steps")
            self.debug_info_label.config(text=f"Алгоритм: {algo}. Начало: ({int(round(x1))},{int(round(y1))}). Шагов: {len(self.debug_steps)}")

    def clear_canvas(self):
        self.canvas.delete("all")
        self.points = []
        self.status_bar.config(text="Холст очищен. Выберите первую точку отрезка.")

        if self.debug_mode.get() and self.debug_canvas:
            self.stop_debug_visualization()
            self.debug_canvas.delete("all")
            self.draw_debug_grid()
            self.debug_steps = []
            self.debug_step_index = 0
            self.debug_info_label.config(text="Сетка для отладки. Нарисуйте отрезок.")


    def toggle_debug_window(self):
        if self.debug_mode.get():
            if not self.debug_window or not self.debug_window.winfo_exists():
                self._create_debug_window()
            else:
                self.debug_window.deiconify()
        else:
            if self.debug_window and self.debug_window.winfo_exists():
                self.stop_debug_visualization()
                self.debug_window.withdraw()

    def _create_debug_window(self):
        self.debug_window = Toplevel(self.root)
        self.debug_window.title("Отладка построения отрезка")
        self.debug_window.geometry("500x600")
        self.debug_window.protocol("WM_DELETE_WINDOW", self._on_debug_close)

        self.debug_info_label = tk.Label(self.debug_window, text="Сетка для отладки. Нарисуйте отрезок.")
        self.debug_info_label.pack(pady=5)

        canvas_width = self.DEBUG_GRID_SIZE * self.DEBUG_CELL_SIZE
        canvas_height = self.DEBUG_GRID_SIZE * self.DEBUG_CELL_SIZE
        self.debug_canvas = tk.Canvas(self.debug_window, width=canvas_width, height=canvas_height, bg="lightgrey")
        self.debug_canvas.pack(pady=10, padx=10)
        self.draw_debug_grid()

        controls_frame = Frame(self.debug_window)
        controls_frame.pack(pady=10, fill=tk.X, padx=10)

        start_button = Button(controls_frame, text="Старт/Перезапуск", command=self.start_debug_visualization)
        start_button.pack(side=tk.LEFT, padx=5)

        stop_button = Button(controls_frame, text="Стоп", command=self.stop_debug_visualization)
        stop_button.pack(side=tk.LEFT, padx=5)

        delay_label = Label(controls_frame, text="Задержка (мс):")
        delay_label.pack(side=tk.LEFT, padx=(15, 5))
        delay_scale = Scale(controls_frame, from_=10, to=1000, orient=tk.HORIZONTAL, variable=self.debug_delay_ms, length=150)
        delay_scale.pack(side=tk.LEFT)

    def _on_debug_close(self):
        self.stop_debug_visualization()
        self.debug_mode.set(False)
        self.debug_window.withdraw()

    def draw_debug_grid(self):
        if not self.debug_canvas: return
        self.debug_canvas.delete("grid")
        w = self.DEBUG_GRID_SIZE * self.DEBUG_CELL_SIZE
        h = self.DEBUG_GRID_SIZE * self.DEBUG_CELL_SIZE
        cs = self.DEBUG_CELL_SIZE
        for i in range(0, w + 1, cs):
            self.debug_canvas.create_line(i, 0, i, h, fill="grey", tags="grid")
        for i in range(0, h + 1, cs):
            self.debug_canvas.create_line(0, i, w, i, fill="grey", tags="grid")
        center_x = (self.DEBUG_GRID_SIZE // 2) * cs
        center_y = (self.DEBUG_GRID_SIZE // 2) * cs
        self.debug_canvas.create_line(center_x - cs//2, center_y, center_x + cs//2, center_y, fill="red", width=2, tags="grid")
        self.debug_canvas.create_line(center_x, center_y - cs//2, center_x, center_y + cs//2, fill="red", width=2, tags="grid")

    def start_debug_visualization(self):
        if not self.debug_canvas or not self.debug_steps:
            print("Debug: No steps to visualize.")
            return

        self.stop_debug_visualization()
        self.debug_canvas.delete("steps")
        self.debug_step_index = 0
        print(f"Debug: Starting visualization with {len(self.debug_steps)} steps, delay={self.debug_delay_ms.get()}ms")
        self._draw_debug_step_delayed()

    def stop_debug_visualization(self):
        if self.debug_after_id:
            self.debug_canvas.after_cancel(self.debug_after_id)
            self.debug_after_id = None
            print("Debug: Visualization stopped.")

    def _draw_debug_step_delayed(self):
        if not self.debug_canvas or self.debug_step_index >= len(self.debug_steps):
            self.debug_after_id = None
            print("Debug: Visualization finished.")
            if self.debug_info_label:
                 self.debug_info_label.config(text=self.debug_info_label.cget("text").split(".")[0] + f". Шагов: {len(self.debug_steps)}. Завершено.")
            return

        step_data = self.debug_steps[self.debug_step_index]
        algo = self.current_algorithm.get()
        intensity = 1.0
        if algo == "Wu" and len(step_data) == 3:
            px, py, intensity = step_data
        elif len(step_data) == 2:
            px, py = step_data
        else:
            print(f"Debug: Invalid step data format at index {self.debug_step_index}: {step_data}")
            self.debug_step_index += 1
            self.debug_after_id = self.debug_canvas.after(self.debug_delay_ms.get(), self._draw_debug_step_delayed) # Schedule next
            return

        cs = self.DEBUG_CELL_SIZE
        grid_center_offset_x = self.DEBUG_GRID_SIZE // 2
        grid_center_offset_y = self.DEBUG_GRID_SIZE // 2
        origin_x, origin_y = self.debug_origin
        grid_x = (px - origin_x) + grid_center_offset_x
        grid_y = (py - origin_y) + grid_center_offset_y

        if 0 <= grid_x < self.DEBUG_GRID_SIZE and 0 <= grid_y < self.DEBUG_GRID_SIZE:
            cell_x1 = grid_x * cs
            cell_y1 = grid_y * cs
            cell_x2 = cell_x1 + cs
            cell_y2 = cell_y1 + cs

            if algo == "Wu":
                gray_val = int(255 * (1.0 - intensity))
                fill_color = f'#{gray_val:02x}{gray_val:02x}{gray_val:02x}'
                outline_color = "darkred" if intensity > 0.8 else "red"
            else:
                fill_color = "lightblue"
                outline_color = "blue"

            self.debug_canvas.create_rectangle(cell_x1, cell_y1, cell_x2, cell_y2,
                                               fill=fill_color, outline=outline_color, width=1, tags="steps")
            self.debug_canvas.create_text(cell_x1 + cs//2, cell_y1 + cs//2,
                                           text=str(self.debug_step_index + 1), fill="black", tags="steps", font=("Arial", 7))


        self.debug_step_index += 1
        self.debug_after_id = self.debug_canvas.after(self.debug_delay_ms.get(), self._draw_debug_step_delayed)


if __name__ == "__main__":
    root = tk.Tk()
    app = LineEditorApp(root)
    root.mainloop()