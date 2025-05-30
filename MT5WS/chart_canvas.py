import tkinter as tk
from datetime import datetime, timezone
from PIL import ImageTk
import pyautogui

# ロウソク足チャートを描画するキャンバス
# 移動平均線の期間（任意に設定可能）
DEFAULT_MA_PERIODS = [20, 75, 200]

class CandleChart(tk.Canvas):
    def __init__(self, master, rates, info_labels, symbol_short, timeframe, chart_x, chart_y, chart_width, chart_height, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.chart_x = chart_x
        self.chart_y = chart_y
        self.chart_width = chart_width
        self.chart_height = chart_height
        self.rates = rates
        self.info_labels = info_labels
        self.symbol_short = symbol_short
        self.timeframe = timeframe
        self.candle_width = 2
        self.candle_gap = 1
        self.bg_image_id = None
        self.bg_image = None
        self.dashed_line_id = None
        self.chart_visible = True  # チャートの表示状態を保持
        self.ma_visible = False    # 移動平均線の表示状態
        self.ma_lines = []         # 移動平均線IDリスト

        # 背景画像の初期描画とロウソク足描画
        self.update_background_image()
        self.draw_candles()
        self.bind("<Motion>", self.on_mouse_move)

    # 背景画像を取得・表示
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

        if self.bg_image_id:
            self.itemconfig(self.bg_image_id, image=self.bg_image)
        else:
            self.bg_image_id = self.create_image(0, 0, anchor='nw', image=self.bg_image)
        self.redraw_only_candles()

    # ロウソク足を描画
    def draw_candles(self):
        if not self.chart_visible:  # チャート非表示なら描画しない
            return
        
        height = int(self['height'])
        width = int(self['width'])

        highs = [r['high'] for r in self.rates]
        lows = [r['low'] for r in self.rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price or 1

        space_per_candle = self.candle_width + self.candle_gap

        def price_to_y(price):
            return height - int((price - min_price) / price_range * height)

        for i, r in enumerate(self.rates):
            x = width - (len(self.rates) - i) * space_per_candle
            open_y = price_to_y(r['open'])
            close_y = price_to_y(r['close'])
            high_y = price_to_y(r['high'])
            low_y = price_to_y(r['low'])
            body_top = min(open_y, close_y)
            body_bottom = max(open_y, close_y)

            # 上ヒゲ
            self.create_rectangle(x, high_y, x + self.candle_width, body_top, fill='red', width=0, tags="candle")
            # 下ヒゲ
            self.create_rectangle(x, body_bottom, x + self.candle_width, low_y, fill='red', width=0, tags="candle")
            # 実体
            self.create_rectangle(x, body_top, x + self.candle_width, body_bottom, fill='green', width=0, tags="candle")

    # ロウソク足だけを再描画
    def redraw_only_candles(self):
        self.delete("candle")
        self.draw_candles()
        if self.ma_visible:
            self.draw_moving_averages(DEFAULT_MA_PERIODS)

    # チャートの表示・非表示を切り替える
    def toggle_chart_visibility(self):
        self.chart_visible = not self.chart_visible
        self.redraw_only_candles()
    
    # 移動平均線の表示・非表示を切り替える
    def toggle_moving_averages(self):
        self.ma_visible = not self.ma_visible
        for line_id in self.ma_lines:
            self.delete(line_id)
        self.ma_lines.clear()
        if self.ma_visible:
            self.draw_moving_averages(DEFAULT_MA_PERIODS)

    # 移動平均線を描画
    def draw_moving_averages(self, periods):
        import statistics

        height = int(self['height'])
        width = int(self['width'])
        highs = [r['high'] for r in self.rates]
        lows = [r['low'] for r in self.rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price or 1
        space_per_candle = self.candle_width + self.candle_gap

        def price_to_y(price):
            return height - int((price - min_price) / price_range * height)

        closes = [r['close'] for r in self.rates]

        for period in periods:
            if len(closes) < period:
                continue
            ma_points = []
            for i in range(period - 1, len(closes)):
                avg = statistics.mean(closes[i - period + 1:i + 1])
                x = width - (len(closes) - i) * space_per_candle
                y = price_to_y(avg)
                ma_points.append((x, y))

            for i in range(1, len(ma_points)):
                x1, y1 = ma_points[i - 1]
                x2, y2 = ma_points[i]
                line_id = self.create_line(x1, y1, x2, y2, fill='black', width=1, tags='ma')
                self.ma_lines.append(line_id)

    # Y座標を価格に変換
    def y_to_price(self, y):
        height = int(self['height'])
        highs = [r['high'] for r in self.rates]
        lows = [r['low'] for r in self.rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price or 1
        return min_price + (height - y) / height * price_range

    # マウス移動に応じて情報ラベルを更新
    def on_mouse_move(self, event):
        x = event.x
        width = int(self['width'])
        space_per_candle = self.candle_width + self.candle_gap
        index = len(self.rates) - (width - x) // space_per_candle - 1

        if 0 <= index < len(self.rates):
            r = self.rates[index]
            dt = datetime.fromtimestamp(r["time"], tz=timezone.utc)
            time_str = dt.strftime("%Y.%m.%d %H:%M")
            updated_values = [
                self.symbol_short,
                self.timeframe,
                time_str,
                f"{r['open']:.3f}",
                f"{r['high']:.3f}",
                f"{r['low']:.3f}",
                f"{r['close']:.3f}",
            ]
            for i, val in enumerate(updated_values):
                self.info_labels[i].config(text=val)

    # 新しいレートデータで更新
    def update_rates(self, new_rates, new_timeframe):
        self.rates = new_rates
        self.timeframe = new_timeframe
        self.update_background_image()
        # timeframe切替時に古い移動平均線を削除
        for line_id in self.ma_lines:
            self.delete(line_id)
        self.ma_lines.clear()
        self.update_background_image()
        # ma_visible が True の場合、移動平均線を再描画
        if self.ma_visible:
            self.draw_moving_averages(DEFAULT_MA_PERIODS)

    # ダッシュライン表示
    def show_dashed_line(self, y):
        if self.dashed_line_id:
            self.delete(self.dashed_line_id)
        self.dashed_line_id = self.create_line(0, y, self.chart_width, y, fill='black', dash=(4, 2))

    # ダッシュライン非表示
    def hide_dashed_line(self):
        if self.dashed_line_id:
            self.delete(self.dashed_line_id)
            self.dashed_line_id = None
