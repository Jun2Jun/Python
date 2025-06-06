import tkinter as tk
from datetime import datetime, timezone
from PIL import ImageTk
import pyautogui
import asyncio
from config import moving_average_periods, auto_update_interval

class CandleChart(tk.Canvas):
    def __init__(self, master, rates, info_labels, symbol_short, timeframe,
                 chart_x, chart_y, chart_width, chart_height, candle_display_count=250,
                 format_func=None, update_func=None, symbol_entry=None, **kwargs):
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
        self.ma_visible = False    # 移動平均線の表示状態を保持
        self.ma_lines = []         # 移動平均線IDリスト
        self.format_func = format_func or (lambda v: f"{v:.3f}")
        self.candle_display_count = candle_display_count
        self.divider_visible = False # 区切りの縦線描画状態を保持
        self.divider_lines = []  # 区切り縦線の描画IDリスト
        self.update_func = update_func # 自動更新で使用する更新関数（非同期）
        self.hline_mode = False        # 水平線描画モードの状態
        self.temp_hline_id = None      # 一時的な破線の水平線ID
        self.hline_ids = []            # 確定した水平線IDのリスト
        self.hline_data = {}  # 通貨ペアごとの価格リスト: {symbol_short: [price1, price2, ...]}
        self.selected_hline_index = None   # 選択中の水平線インデックス
        self.hline_handle_ids = []         # 四角形ハンドルのID
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<Button-1>", self.on_left_click)
        self.symbol_entry = symbol_entry # 通貨入力エリアのインスタンス。自動更新の実施有無を判定するときに使用する。

        # 背景画像の初期描画とロウソク足描画
        self.update_background_image()
        self.draw_candles()
        self.bind("<Motion>", self.on_mouse_move)

        # 自動更新の設定（ミリ秒単位）
        self.auto_update_interval = auto_update_interval * 1000  # 自動更新間隔（ミリ秒）
        if self.auto_update_interval > 0:
            self.schedule_auto_update()
    
    # 水平線描画モード切替用メソッド
    def toggle_horizontal_line_mode(self):
        self.hline_mode = not self.hline_mode
        if not self.hline_mode:
            self.hide_temp_hline()

    # 水平線の破線表示
    def show_temp_hline(self, y):
        if self.temp_hline_id:
            self.delete(self.temp_hline_id)
        self.temp_hline_id = self.create_line(0, y, self.chart_width, y, fill='black', dash=(4, 2))

    # 水平線の破線削除
    def hide_temp_hline(self):
        if self.temp_hline_id:
            self.delete(self.temp_hline_id)
            self.temp_hline_id = None

    # 左クリックで確定線を描画し、モード終了
    def on_left_click(self, event):
        if self.hline_mode:
            y = event.y
            price = self.y_to_price(y)

            symbol = self.symbol_short
            if symbol not in self.hline_data:
                self.hline_data[symbol] = []
            self.hline_data[symbol].append(price) # シンボルと価格を記録
            
            line_id = self.create_line(0, y, self.chart_width, y, fill='black')
            self.hline_ids.append(line_id)

            self.hline_mode = False
            self.hide_temp_hline()
        else:
            # 水平線選択判定
            y_click = event.y
            tolerance = 5
            height = int(self['height'])
            display_rates = self.rates[-self.candle_display_count:]
            highs = [r['high'] for r in display_rates]
            lows = [r['low'] for r in display_rates]
            max_price = max(highs)
            min_price = min(lows)
            price_range = max_price - min_price or 1

            def price_to_y(price):
                return height - int((price - min_price) / price_range * height)

            symbol = self.symbol_short
            prices = self.hline_data.get(symbol, [])
            for i, price in enumerate(prices):
                y = price_to_y(price)
                if abs(y - y_click) <= tolerance:
                    self.hide_hline_handles()  # 既存ハンドル削除
                    self.selected_hline_index = i
                    self.show_hline_handles(y)
                    break
            else:
                self.hide_hline_handles()  # 選択なし

    # 水平線のハンドルを描画するメソッド
    def show_hline_handles(self, y):
        size = 10
        half = size // 2
        positions = [0, self.chart_width // 2, self.chart_width]
        for x in positions:
            handle = self.create_rectangle(x - half, y - half, x + half, y + half, outline="black", width=1)
            self.hline_handle_ids.append(handle)
    
    # 水平線のハンドルを削除するメソッド
    def hide_hline_handles(self):
        for hid in self.hline_handle_ids:
            self.delete(hid)
        self.hline_handle_ids.clear()
        self.selected_hline_index = None

    # 指定間隔で auto_update をスケジュール実行
    def schedule_auto_update(self):
        self.after(self.auto_update_interval, self.auto_update)

    # update_func が指定されていれば定期的に呼び出して更新
    def auto_update(self):
        # 通貨入力エリア表示中なら自動更新をスキップ
        if hasattr(self, 'symbol_entry') and self.symbol_entry and self.symbol_entry.winfo_ismapped():
            self.schedule_auto_update()
            return

        # update_funcが渡されてれば更新が行われる。
        if self.update_func:
            # main.pyで渡しているので設定した時間で更新されるようになっている。
            asyncio.run(self.update_func(self.timeframe))
        self.schedule_auto_update()
    
    # 区切り縦線の表示を切り替える
    def toggle_time_dividers(self):
        self.divider_visible = not self.divider_visible
        if self.divider_visible:
            self.draw_time_dividers()
        else:
            for line_id in self.divider_lines:
                self.delete(line_id)
            self.divider_lines.clear()
    
    # 区切り縦線の描画
    def draw_time_dividers(self):
        self.divider_lines.clear()
        self.delete("divider")

        width = int(self['width'])
        height = int(self['height'])
        display_rates = self.rates[-self.candle_display_count:]
        space_per_candle = self.candle_width + self.candle_gap

        prev_key = None
        for i, r in enumerate(display_rates):
            dt = datetime.fromtimestamp(r["time"], tz=timezone.utc)
            key = None
            tf = self.timeframe.upper()
            if tf in ["M1", "M5", "M15", "M30", "H1"]:
                key = dt.date()
            elif tf == "H4":
                key = (dt.year, dt.isocalendar().week)  # 年と週
            elif tf == "D1":
                key = (dt.year, dt.month)
            elif tf == "W1":
                key = dt.year
            elif tf == "MN1":
                continue  # 表示しない

            if key != prev_key and prev_key is not None:
                x = width - (len(display_rates) - i) * space_per_candle + self.candle_width // 2
                line_id = self.create_line(x, 0, x, height, fill='black', dash=(3, 2), tags="divider")
                self.divider_lines.append(line_id)
            prev_key = key

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
        # 選択状態の保持のため水平線も含めて再描画
        self.redraw_only_candles()
        self.redraw_horizontal_lines()

    # ロウソク足を描画
    def draw_candles(self):
        if not self.chart_visible:  # チャート非表示なら描画しない
            return
        
        height = int(self['height'])
        width = int(self['width'])

        display_rates = self.rates[-self.candle_display_count:]  # 表示する250本
        highs = [r['high'] for r in display_rates]
        lows = [r['low'] for r in display_rates]
        max_price = max(highs)
        min_price = min(lows)

        # highs = [r['high'] for r in self.rates]
        # lows = [r['low'] for r in self.rates]
        # max_price = max(highs)
        # min_price = min(lows)
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
            self.draw_moving_averages(moving_average_periods)
    
    
    def redraw_horizontal_lines(self):
        # 現在の通貨ペアの水平線取得
        symbol = self.symbol_short
        prices = self.hline_data.get(symbol, [])

        # 現在選択されている価格を記憶（インデックスより安定）
        selected_price = None
        if self.selected_hline_index is not None:
            if 0 <= self.selected_hline_index < len(prices):
                selected_price = prices[self.selected_hline_index]

        # ハンドルのみ削除（選択インデックスは維持）
        for hid in self.hline_handle_ids:
            self.delete(hid)
        self.hline_handle_ids.clear()

        # 既存水平線の削除
        for line_id in self.hline_ids:
            self.delete(line_id)
        self.hline_ids.clear()

        if not prices:
            self.selected_hline_index = None
            return

        # 現在のチャート高さ・価格範囲取得
        height = int(self['height'])
        display_rates = self.rates[-self.candle_display_count:]
        highs = [r['high'] for r in display_rates]
        lows = [r['low'] for r in display_rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price or 1

        def price_to_y(price):
            return height - int((price - min_price) / price_range * height)

        # 水平線の再描画＋ハンドル復元
        for i, price in enumerate(prices):
            y = price_to_y(price)
            line_id = self.create_line(0, y, self.chart_width, y, fill='black')
            self.hline_ids.append(line_id)

            if selected_price is not None and abs(price - selected_price) < 1e-8:
                self.selected_hline_index = i
                self.show_hline_handles(y)

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
            self.draw_moving_averages(moving_average_periods)

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
        display_rates = self.rates[-self.candle_display_count:]
        highs = [r['high'] for r in display_rates]
        lows = [r['low'] for r in display_rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price or 1
        return min_price + (height - y) / height * price_range

    # マウス移動に応じて情報ラベルを更新
    def on_mouse_move(self, event):
        if self.hline_mode:
            # 水平線モード中は破線を表示
            self.show_temp_hline(event.y)
            return

        # 通常モードでは情報ラベルを更新
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
                self.format_func(r['open']),
                self.format_func(r['high']),
                self.format_func(r['low']),
                self.format_func(r['close']),
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
            self.draw_moving_averages(moving_average_periods)
        # 区切り縦線の表示状態に応じて再描画
        if self.divider_visible:
            for line_id in self.divider_lines:
                self.delete(line_id)
            self.divider_lines.clear()
            self.draw_time_dividers()
        # timeframe切替後の描画再調整
        self.redraw_horizontal_lines()

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
