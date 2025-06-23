import tkinter as tk
from datetime import datetime, timezone
import asyncio
import json
import os
from config import moving_average_periods, moving_average_colors, auto_update_interval
from utils import get_cropped_screenshot_from_image, take_full_screenshot

class CandleChart(tk.Canvas):
    LINE_DATA_PATH = "line_data.json" # ラインデータの保存パス

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
        self.chart_visible = True  # チャートの表示状態
        self.ma_visible = False    # 移動平均線の表示状態
        self.ma_lines = []         # 移動平均線の描画ID保持
        self.line_data_cache = {} # 水平線の情報のキャッシュ
        self.diagonal_styles = {} # 斜め線の情報のキャッシュ
        self.format_func = format_func or (lambda v: f"{v:.3f}")
        self.candle_display_count = candle_display_count
        self.divider_visible = False  # 区切り線の表示状態
        self.divider_lines = []       # 区切り線ID保持
        self.update_func = update_func  # 自動更新関数

        # フラグ
        self.hline_editing = False  # ラインの編集中フラグ
        self.settings_editing = False  # 設定画面編集中フラグ

        # 水平線描画関連
        self.hline_mode = False
        self.temp_hline_id = None
        self.hline_ids = []
        self.hline_data = {}  # 通貨ごとの水平線価格リスト
        self.selected_hline_index = None
        self.hline_handle_ids = []
        self.hline_styles = {} # 水平線の属性リスト

        # 斜め線描画関連
        self.diagonal_mode = False
        self.diagonal_start = None
        self.temp_diagonal_id = None
        self.diagonal_line_ids = []
        self.diagonal_data = []  # (symbol, t1, price1, t2, price2)

        # 移動平均線関連
        self.ma_periods = moving_average_periods
        self.ma_colors = moving_average_colors

        # マウス操作をバインド
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<Button-1>", self.on_left_click)
        self.bind("<Button-3>", self.on_right_click)
        self.symbol_entry = symbol_entry

        # 背景画像の初期描画とロウソク足描画
        self.update_background_image()
        self.draw_candles()

        # 自動更新の設定（ミリ秒単位）
        self.auto_update_interval = auto_update_interval * 1000  # 自動更新間隔（ミリ秒）
        if self.auto_update_interval > 0:
            self.schedule_auto_update()
    
    # 移動平均線の設定
    def set_moving_average_config(self, periods, colors):
        self.ma_periods = periods
        self.ma_colors = colors
        if self.ma_visible:
            self.toggle_moving_averages()  # 一旦消して
            self.toggle_moving_averages()  # 再描画

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
    
     # 斜め線モード切替（水平線モード解除も含む）
    def toggle_diagonal_line_mode(self):
        self.diagonal_mode = not self.diagonal_mode
        self.diagonal_start = None
        if self.temp_diagonal_id:
            self.delete(self.temp_diagonal_id)
            self.temp_diagonal_id = None
        if self.hline_mode:
            self.hline_mode = False
            self.hide_temp_hline()

    # 左クリック時の処理（斜め線・水平線の描画や選択）
    def on_left_click(self, event):
        if self.diagonal_mode:
            if self.diagonal_start is None:
                price1 = self.y_to_price(event.y)
                index = self.get_index_from_x(event.x)
                t1 = self.rates[index]['time']
                self.diagonal_start = (t1, price1)
            else:
                t1, price1 = self.diagonal_start
                price2 = self.y_to_price(event.y)
                index = self.get_index_from_x(event.x)
                t2 = self.rates[index]['time']
                x1 = self.get_x_from_time(t1)
                x2 = self.get_x_from_time(t2)
                y1 = self.price_to_y(price1)
                y2 = self.price_to_y(price2)
                if x1 is not None and x2 is not None:
                    line_id = self.create_line(x1, y1, x2, y2, fill='black')
                    self.diagonal_line_ids.append(line_id)
                    symbol = self.symbol_short
                    self.diagonal_data.append((symbol, t1, price1, t2, price2))
                    self.diagonal_mode = False
                if self.temp_diagonal_id:
                    self.delete(self.temp_diagonal_id)
                    self.temp_diagonal_id = None
        elif self.hline_mode:
            y = event.y
            price = self.y_to_price(y)
            symbol = self.symbol_short
            if symbol not in self.hline_data:
                self.hline_data[symbol] = []
            self.hline_data[symbol].append(price)
            line_id = self.create_line(0, y, self.chart_width, y, fill='black', width=1) # 水平線を作成
            self.hline_ids.append(line_id) # 水平線リストに追加
            self.hline_styles[(symbol, len(self.hline_ids) - 1)] = {"color": "black", "width": 1} # 属性をリストにキャッシュ
            self.hline_mode = False
            self.hide_temp_hline()
            self.update_line_data_cache(self.symbol_short) # キャッシュにライン情報を保存
        else:
            # 線の選択処理
            self.select_line(event)

    # 右クリック時の処理（水平線の属性設定）
    def on_right_click(self, event):
        import tkinter as tk
        from tkinter import colorchooser

        symbol = self.symbol_short

        # 水平線が選択されている場合
        if self.selected_hline_index is not None:
            index = self.selected_hline_index
            style_key = (symbol, index)
            current_style = self.hline_styles.get(style_key, {"color": "black", "width": 1})
        # 斜め線が選択されている場合
        elif self.selected_diagonal_index is not None:
            index = self.selected_diagonal_index
            style_key = (symbol, index)
            current_style = self.diagonal_styles.get(style_key, {"color": "black", "width": 1})
        else:
            return  # 何も選択されていない

        self.hline_editing = True  # 編集中フラグON
        
        dialog = tk.Toplevel(self)
        dialog.title("")  # タイトルバーの文字を消す
        dialog.resizable(False, False) # サイズ変更なし
        dialog.transient(self.master)     # チャートを親に
        dialog.grab_set()                 # モーダルに
        dialog.focus_set() # フォーカスをセット

        # Windowsならこのスタイルで枠が小さくなる（macOS/Linuxでは無視される可能性あり）
        dialog.wm_attributes("-toolwindow", True)

        # カラー選択
        def pick_color():
            color = colorchooser.askcolor(title="色を選択", initialcolor=current_style["color"])
            if color[1]:
                current_style["color"] = color[1]
                color_label.config(bg=color[1])

        tk.Label(dialog, text="色:").grid(row=0, column=0, padx=5, pady=5)
        color_label = tk.Label(dialog, bg=current_style["color"], width=10)
        color_label.grid(row=0, column=1, padx=5)
        tk.Button(dialog, text="変更", command=pick_color).grid(row=0, column=2, padx=5)

        tk.Label(dialog, text="太さ:").grid(row=1, column=0, padx=5, pady=5)
        width_var = tk.IntVar(value=current_style["width"])
        spinbox = tk.Spinbox(dialog, from_=1, to=10, textvariable=width_var, width=5)
        spinbox.grid(row=1, column=1, columnspan=2, padx=5)

        # "OK"を押下したときの処理
        def apply_changes():
            current_style["width"] = width_var.get() # 太さを設定
            if self.selected_hline_index is not None:
                self.hline_styles[style_key] = current_style # スタイルを設定
                self.redraw_horizontal_lines() # 水平線を再描画
            elif self.selected_diagonal_index is not None:
                self.diagonal_styles[style_key] = current_style # スタイルを設定
                self.redraw_diagonal_lines() # 斜め線を再描画
            self.hline_editing = False  # 編集終了でフラグOFF
            dialog.destroy()
            self.update_line_data_cache(self.symbol_short) # キャッシュにライン情報を保存

        # "OK"ボタンの見た目と動作設定
        tk.Button(dialog, text="OK", command=apply_changes).grid(row=2, column=0, columnspan=4, pady=5)

        # サイズ確定
        dialog.update_idletasks()
        dialog_width = dialog.winfo_width()

        # メインウィンドウ内に表示
        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()

        # メインウィンドウ右上から少し内側に
        x_pos = master_x + master_width - dialog_width - 10
        y_pos = master_y + 10

        # 編集画面の位置を確定
        dialog.geometry(f"+{x_pos}+{y_pos}")

        # xボタンは表示してないが、閉じる操作が発生した場合の安全措置
        dialog.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "hline_editing", False), dialog.destroy()))
    
    # 線選択の関数
    def select_line(self, event):
        x_click, y_click = event.x, event.y
        tolerance = 5

        # --- 水平線から探す ---
        symbol = self.symbol_short
        h_prices = self.hline_data.get(symbol, [])
        for i, price in enumerate(h_prices):
            y = self.price_to_y(price)
            if abs(y - y_click) <= tolerance:
                self.clear_selected_line()
                self.selected_hline_index = i
                self.show_hline_handles(y)
                return

        # --- 斜め線から探す ---
        for i, (s, t1, p1, t2, p2) in enumerate(self.diagonal_data):
            if s != symbol:
                continue
            x1 = self.get_x_from_time(t1)
            x2 = self.get_x_from_time(t2)
            y1 = self.price_to_y(p1)
            y2 = self.price_to_y(p2)

            if x1 is None or x2 is None:
                continue

            # 線分上の距離チェック（クリック位置と直線距離）
            if self._is_near_line(x_click, y_click, x1, y1, x2, y2, tolerance):
                self.clear_selected_line()
                self.selected_diagonal_index = i
                self.show_diagonal_handles(x1, y1, x2, y2)
                return

        # どちらも該当なし
        self.clear_selected_line()
    
    # 線選択の補助関数
    def _is_near_line(self, x, y, x1, y1, x2, y2, tol):
        # 線分と点の距離を計算（ベクトル内積で）
        import math
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1) <= tol

        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx*dx + dy*dy)))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(x - proj_x, y - proj_y) <= tol

    # ハンドル削除の処理
    def clear_selected_line(self):
        self.hide_hline_handles()
        self.hide_diagonal_handles()
        self.selected_hline_index = None
        self.selected_diagonal_index = None


    # 水平線のハンドルを描画する関数
    def show_hline_handles(self, y):
        size = 10
        half = size // 2
        positions = [0, self.chart_width // 2, self.chart_width]
        for x in positions:
            handle = self.create_rectangle(x - half, y - half, x + half, y + half, outline="black", width=1)
            self.hline_handle_ids.append(handle)
    
    # 水平線のハンドルを削除する関数
    def hide_hline_handles(self):
        for hid in self.hline_handle_ids:
            self.delete(hid)
        self.hline_handle_ids.clear()
        self.selected_hline_index = None
    
    # 斜め線のハンドルを描画する関数
    def show_diagonal_handles(self, x1, y1, x2, y2):
        size = 10
        half = size // 2
        for x, y in [(x1, y1), (x2, y2), ((x1 + x2) // 2, (y1 + y2) // 2)]:
            handle = self.create_rectangle(x - half, y - half, x + half, y + half, outline="black", width=1)
            self.hline_handle_ids.append(handle)  # 使い回す

    # 斜め線のハンドルを削除する関数
    def hide_diagonal_handles(self):
        for hid in self.hline_handle_ids:
            self.delete(hid)
        self.hline_handle_ids.clear()

    # 指定間隔で auto_update をスケジュール実行
    def schedule_auto_update(self):
        self.after(self.auto_update_interval, self.auto_update)

    # update_func が指定されていれば定期的に呼び出して更新
    def auto_update(self):
        # 編集ダイアログ or 通貨入力エリア表示中はスキップ
        if (hasattr(self, 'symbol_entry') and self.symbol_entry and self.symbol_entry.winfo_ismapped()) or self.hline_editing or self.settings_editing:
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
    def update_background_image(self, full_screenshot=None):
        self.master.withdraw() # Tkinterのウィンドウを一時的に非表示
        self.master.update() # 画面の状態を更新して完全に非表示に反映

        # 自ウィンドウを含まないようにスクリーンショットの取得
        if full_screenshot is None:
            full_screenshot = take_full_screenshot()

        # スクリーンショットの切り取り
        self.bg_image = get_cropped_screenshot_from_image(
            full_screenshot,
            self.chart_x, self.chart_y,
            self.chart_width, self.chart_height
        )
        self.master.deiconify() # 非表示を解除

        # 既存のすべてをクリアしてから背景＋再描画
        self.delete("all")  # キャンバス上の全アイテムを削除
        self.bg_image_id = self.create_image(0, 0, anchor='nw', image=self.bg_image)
        
        # 選択状態の保持のため水平線も含めて再描画
        self.redraw_only_candles()
        self.redraw_horizontal_lines()
        self.redraw_diagonal_lines()

    # ロウソク足を描画
    def draw_candles(self):
        if not self.chart_visible:  # チャート非表示なら描画しない
            return
        width = int(self['width'])
        space_per_candle = self.candle_width + self.candle_gap
        display_rates = self.rates[-self.candle_display_count:]

        for i, r in enumerate(display_rates):
            x = width - (len(display_rates) - i) * space_per_candle
            open_y = self.price_to_y(r['open'])
            close_y = self.price_to_y(r['close'])
            high_y = self.price_to_y(r['high'])
            low_y = self.price_to_y(r['low'])
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
    
    # 水平線の再描画
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

        # 水平線の再描画＋ハンドル復元
        for i, price in enumerate(prices):
            y = self.price_to_y(price)
            style = self.hline_styles.get((symbol, i), {"color": "black", "width": 1})
            line_id = self.create_line(0, y, self.chart_width, y, fill=style["color"], width=style["width"])
            # line_id = self.create_line(0, y, self.chart_width, y, fill='black')
            self.hline_ids.append(line_id)

            if selected_price is not None and abs(price - selected_price) < 1e-8:
                self.selected_hline_index = i
                self.show_hline_handles(y)

    # 斜め線の再描画（通貨ペア変更や更新時）
    def redraw_diagonal_lines(self):
        for line_id in self.diagonal_line_ids:
            self.delete(line_id)
        self.diagonal_line_ids.clear()

        symbol = self.symbol_short
        for i, (s, t1, price1, t2, price2) in enumerate(self.diagonal_data):
            if s != symbol:
                continue
            x1 = self.get_x_from_time(t1)
            x2 = self.get_x_from_time(t2)
            y1 = self.price_to_y(price1)
            y2 = self.price_to_y(price2)
            if x1 is not None and x2 is not None:
                style = self.diagonal_styles.get((symbol, i), {"color": "black", "width": 1})
                line_id = self.create_line(x1, y1, x2, y2, fill=style["color"], width=style["width"])
                self.diagonal_line_ids.append(line_id)

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
        width = int(self['width'])
        space_per_candle = self.candle_width + self.candle_gap
        closes = [r['close'] for r in self.rates]
        periods = periods or self.ma_periods

        # periodごとの移動平均を計算
        for idx, period in enumerate(self.ma_periods):
            if len(closes) < period:
                continue
            ma_points = []
            # 移動平均を計算
            for i in range(period - 1, len(closes)):
                avg = statistics.mean(closes[i - period + 1:i + 1])
                x = width - (len(closes) - i) * space_per_candle
                y = self.price_to_y(avg)
                ma_points.append((x, y))
            # 座標に変換
            for i in range(1, len(ma_points)):
                x1, y1 = ma_points[i - 1]
                x2, y2 = ma_points[i]
                line_id = self.create_line(x1, y1, x2, y2, fill=self.ma_colors[idx], width=1, tags='ma')
                self.ma_lines.append(line_id)

    # マウス移動に応じて情報ラベルを更新
    def on_mouse_move(self, event):
        # 水平線モード中は破線を表示
        if self.hline_mode:
            self.show_temp_hline(event.y)
            return
        
        # 斜め線モード中は破線を表示
        if self.diagonal_mode and self.diagonal_start:
            t1, price1 = self.diagonal_start
            x1 = self.get_x_from_time(t1)
            if x1 is None:
                return
            y1 = self.price_to_y(price1)
            x2 = event.x
            y2 = event.y
            if self.temp_diagonal_id:
                self.delete(self.temp_diagonal_id)
            self.temp_diagonal_id = self.create_line(x1, y1, x2, y2, fill='black', dash=(4, 2))
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
    
    # x座標からIndexを取得する
    def get_index_from_x(self, x):
        space = self.candle_width + self.candle_gap
        width = int(self['width'])
        index = len(self.rates) - (width - x) // space - 1
        return max(0, min(len(self.rates) - 1, index))

    # timeからx座標を取得する
    def get_x_from_time(self, t):
        space = self.candle_width + self.candle_gap
        times = [r['time'] for r in self.rates[-self.candle_display_count:]]
        if not times:
            return None
        closest_index = min(range(len(times)), key=lambda i: abs(times[i] - t))
        i = closest_index
        return int(self['width']) - (len(times) - i) * space + self.candle_width // 2

    # Y座標を価格に変換
    def y_to_price(self, y):
        height = int(self['height'])
        min_price, _, price_range = self.get_price_bounds()
        return min_price + (height - y) / height * price_range
    
    # 価格からy座標に変換    
    def price_to_y(self, price):
        height = int(self['height'])
        min_price, _, price_range = self.get_price_bounds() 
        return height - int((price - min_price) / price_range * height)

    # チャートの最大値と最小値、レンジを取得する関数
    def get_price_bounds(self):
        display_rates = self.rates[-self.candle_display_count:]
        highs = [r['high'] for r in display_rates]
        lows = [r['low'] for r in display_rates]
        min_price = min(lows)
        max_price = max(highs)
        return min_price, max_price, max_price - min_price or 1

    # 新しいレートデータで更新
    def update_rates(self, new_rates, new_timeframe):
        self.rates = new_rates
        self.timeframe = new_timeframe
        self.refresh_chart(update_timeframe=True)

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
    
    # チャートの再描画
    def refresh_chart(self, update_timeframe=False):
        # 背景更新
        self.update_background_image()

        # 移動平均線の削除
        for line_id in self.ma_lines:
            self.delete(line_id)
        self.ma_lines.clear()

        # 移動平均線の再描画
        if self.ma_visible:
            self.draw_moving_averages(moving_average_periods)

        # 区切り線の再描画（timeframe更新時のみ）
        if update_timeframe and self.divider_visible:
            for line_id in self.divider_lines:
                self.delete(line_id)
            self.divider_lines.clear()
            self.draw_time_dividers()

        # 水平線・斜め線を再描画
        self.redraw_horizontal_lines()
        self.redraw_diagonal_lines()

        # ロウソク足のみ再描画（表示中であれば）
        self.redraw_only_candles()

    # ラインの保存処理
    def save_line_data(self):
        symbol = self.symbol_short

        # --- 水平線データを構造化 ---
        hlines = []
        prices = self.hline_data.get(symbol, [])
        for i, price in enumerate(prices):
            style = self.hline_styles.get((symbol, i), {"color": "#000000", "width": 1})
            hlines.append({
                "price": price,
                "color": style.get("color", "#000000"),
                "width": style.get("width", 1)
            })

        # --- 斜め線データを構造化 ---
        dlines = []
        for s, t1, p1, t2, p2 in self.diagonal_data:
            if s != symbol:
                continue
            dlines.append({
                "t1": t1, "p1": p1,
                "t2": t2, "p2": p2,
                "color": "#000000",  # 今は固定（後で拡張可）
                "width": 1
            })

        # --- 全体データ構築 ---
        new_entry = {
            symbol: {
                "horizontal": hlines,
                "diagonal": dlines
            }
        }

        try:
            if os.path.exists(self.LINE_DATA_PATH):
                with open(self.LINE_DATA_PATH, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
            else:
                all_data = {}

            all_data.update(new_entry)

            with open(self.LINE_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2)
        except Exception as e:
            print(f"[保存失敗] {e}")
    
    # ラインの読み込み処理
    def load_all_line_data(self):
        if not os.path.exists(self.LINE_DATA_PATH):
            return
        try:
            with open(self.LINE_DATA_PATH, "r", encoding="utf-8") as f:
                self.line_data_cache = json.load(f)
        except Exception as e:
            print(f"[読み込み失敗] {e}")
    
    # symbolで指定したラインを適用する処理
    def apply_line_data_to_chart(self, symbol):
        self.symbol_short = symbol
        self.hline_data[symbol] = []
        self.hline_styles = {k: v for k, v in self.hline_styles.items() if k[0] != symbol}
        self.diagonal_data = []

        data = self.line_data_cache.get(symbol)
        if not data:
            return

        # 水平線のデータを適用
        for i, h in enumerate(data.get("horizontal", [])):
            self.hline_data[symbol].append(h["price"])
            self.hline_styles[(symbol, i)] = {
                "color": h.get("color", "#000000"),
                "width": h.get("width", 1)
            }
        # 斜め線のデータを適用        
        for i, d in enumerate(data.get("diagonal", [])):
            self.diagonal_data.append((symbol, d["t1"], d["p1"], d["t2"], d["p2"]))
            self.diagonal_styles[(symbol, i)] = {
                "color": d.get("color", "#000000"),
                "width": d.get("width", 1)
    }
    
    # symbolで指定したラインをキャッシュする処理
    def update_line_data_cache(self, symbol):
        hlines = []
        for i, price in enumerate(self.hline_data.get(symbol, [])):
            style = self.hline_styles.get((symbol, i), {"color": "#000000", "width": 1})
            hlines.append({"price": price, "color": style["color"], "width": style["width"]})

        dlines = []
        for i, (s, t1, p1, t2, p2) in enumerate(self.diagonal_data):
            if s == symbol:
                style = self.diagonal_styles.get((symbol, i), {"color": "#000000", "width": 1})
                dlines.append({
                    "t1": t1, "p1": p1, "t2": t2, "p2": p2,
                    "color": style["color"],
                    "width": style["width"]
                })

        self.line_data_cache[symbol] = {
            "horizontal": hlines,
            "diagonal": dlines
        }
    
    # キャッシュしているラインの保存処理
    def save_all_line_data(self):
        try:
            with open(self.LINE_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(self.line_data_cache, f, indent=2)
        except Exception as e:
            print(f"[保存失敗] {e}")