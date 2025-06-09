import tkinter as tk
from utils import get_cropped_screenshot_from_image, take_full_screenshot

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

    # 背景画像を更新
    def update_background_image(self, full_screenshot=None):
        if full_screenshot is None:
            full_screenshot = take_full_screenshot()  # バックアップとして取得

        self.master.withdraw()
        self.master.update()

        # 引数で受け取った全体画像から、自分の領域を切り抜き
        self.bg_image = get_cropped_screenshot_from_image(
            full_screenshot,
            self.chart_x, self.chart_y,
            self.chart_width, self.chart_height
        )
        self.master.deiconify()

        if self.bg_image_id:
            self.delete(self.bg_image_id)
            self.bg_image_id = None

        #self.bg_image_id = self.create_image(0, 0, anchor='nw', image=self.bg_image)

        self.delete("all")
        self.bg_image_id = self.create_image(0, 0, anchor='nw', image=self.bg_image)