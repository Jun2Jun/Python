import tkinter as tk
from PIL import ImageTk
import pyautogui

# チャート右側の背景付き操作キャンバス
class RateControlCanvas(tk.Canvas):
    def __init__(self, master, chart_x, chart_y, width, height, **kwargs):
        super().__init__(master, width=width, height=height, bg='white', highlightthickness=0, **kwargs)
        self.chart_x = chart_x
        self.chart_y = chart_y
        self.chart_width = width
        self.chart_height = height
        self.bg_image = None
        self.bg_image_id = None
        self.update_background_image()

    # チャート位置に合わせて背景画像を更新
    def update_background_image(self):
        self.master.withdraw()
        self.master.update()

        screenshot = pyautogui.screenshot()
        crop = screenshot.crop((
            self.chart_x, self.chart_y,
            self.chart_x + self.chart_width,
            self.chart_y + self.chart_height
        ))
        self.bg_image = ImageTk.PhotoImage(crop)
        self.master.deiconify()

        self.delete("all")
        self.bg_image_id = self.create_image(0, 0, anchor='nw', image=self.bg_image)
