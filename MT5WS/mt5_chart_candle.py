import asyncio
import pyautogui
import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime, timezone
from mt5_ws_client import get_rates
from PIL import Image, ImageTk


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

        # 背景画像を設定
        self.update_background_image()
        self.draw_candles()
        self.bind("<Motion>", self.on_mouse_move)
    
    # 背景画像を更新するメソッド
    def update_background_image(self):
        # 自ウィンドウ非表示にしてスクリーンショット取得、背景更新
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
        self.draw_candles()

    # ロウソク足を描画するメソッド
    def draw_candles(self):
        height = int(self['height'])
        width = int(self['width'])

        # 価格の最大・最小を計算
        highs = [r['high'] for r in self.rates]
        lows = [r['low'] for r in self.rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price
        if price_range == 0:
            price_range = 1  # 0除算防止

        space_per_candle = self.candle_width + self.candle_gap

        def price_to_y(price):
            # 価格をキャンバス座標に変換（上下逆なのでheight -）
            return height - int((price - min_price) / price_range * height)

        for i, r in enumerate(self.rates):
            x = width - (len(self.rates) - i) * space_per_candle
            open_y = price_to_y(r['open'])
            close_y = price_to_y(r['close'])
            high_y = price_to_y(r['high'])
            low_y = price_to_y(r['low'])

            body_top = min(open_y, close_y)
            body_bottom = max(open_y, close_y)

            # ヒゲ(上)
            self.create_rectangle(
                x, high_y,
                x + self.candle_width, body_top,
                fill='red', width=0
            )
            # ヒゲ(下)
            self.create_rectangle(
                x, body_bottom,
                x + self.candle_width, low_y,
                fill='red', width=0
            )
            # 実体
            self.create_rectangle(
                x, body_top,
                x + self.candle_width, body_bottom,
                fill='green', width=0
            )

    def y_to_price(self, y):
        height = int(self['height'])
        highs = [r['high'] for r in self.rates]
        lows = [r['low'] for r in self.rates]
        max_price = max(highs)
        min_price = min(lows)
        price_range = max_price - min_price
        if price_range == 0:
            price_range = 1
        return min_price + (height - y) / height * price_range
    
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

            # ラベルを更新
            for i, val in enumerate(updated_values):
                self.info_labels[i].config(text=val)
    
    # ratesを更新して再描画
    def update_rates(self, new_rates):
        self.rates = new_rates
        self.update_background_image()

def main():
    symbol = "USDJPY"     # 通貨ペア指定
    timeframe = "M5"      # タイムフレーム指定
    candle_count = 250    # ロウソク足の数
    short_ma_period = 20    # 短期移動平均の期間
    medinum_ma_period = 90  # 中期移動平均の期間
    long_ma_period = 200    # 長期移動平均の期間

    # asyncioで非同期関数を実行して、ratesを取得
    rates = asyncio.run(get_rates(symbol, timeframe, candle_count))

    root = tk.Tk()
    root.overrideredirect(True)  # タイトルバー・枠なし
    root.config(bg='white')
    root.wm_attributes('-transparentcolor', 'white')

    # 初期透明度
    opacity = 0.3
    root.wm_attributes('-alpha', opacity)

    # 画面サイズを取得
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 最新のローソク足データ
    latest = rates[-1]

    # レイアウトのサイズを設定
    candle_width = 2
    candle_gap = 1
    chart_width = candle_count * (candle_width + candle_gap)
    info_width = 120     # 左の情報エリア幅
    rate_display_width = 40 # レート表示エリアの幅
    rate_control_width = 20 # レートコントロールエリアの幅
    drag_width = 10      # ドラッグエリアの幅
    height = 300

    # --- レイアウト間隔の定義 ---
    gap_between_chart_and_control = 0  # チャートと操作の間
    gap_between_control_and_drag = 0    # 操作とドラッグの間

    # ウィンドウ全体幅の計算
    total_width = (
        info_width
        + rate_display_width
        + chart_width
        + gap_between_chart_and_control
        + rate_control_width
        + gap_between_control_and_drag
        + drag_width
    )

    # 起動位置（右下）を計算
    x_pos = screen_width - total_width
    y_pos = screen_height - height

    # ウィンドウ位置とサイズを指定
    root.geometry(f"{total_width}x{height}+{x_pos}+{y_pos}")

    # --- 情報表示エリア（左） ---
    info_frame = tk.Frame(root, bg='white', width=info_width, height=height)
    info_frame.place(x=0, y=0)

    # フォントサイズ9で表示
    font = tkFont.Font(size=9)

    # ラベルはなしで数値のみ表示
    # 通貨ペアは略称で表示
    symbol_short = symbol[0] + symbol[3]
    # 日付時刻を表示形式に変換
    dt = datetime.fromtimestamp(latest["time"], tz=timezone.utc)
    time_str = dt.strftime("%Y.%m.%d %H:%M")
    info_values = [
        symbol_short,
        timeframe,
        time_str,
        f"{latest['open']:.3f}",
        f"{latest['high']:.3f}",
        f"{latest['low']:.3f}",
        f"{latest['close']:.3f}",
        ]
    # 情報ラベルを保持（後で更新するため）
    info_labels = []
    for i, text in enumerate(info_values):
        label = tk.Label(info_frame, text=text, anchor="w", font=font, bg='white')
        label.place(x=5, y=5 + i * 14)
        info_labels.append(label)

    # --- レート表示エリア（情報エリアとチャートエリアの間） ---
    rate_display_label = tk.Label(root, text="", font=font, bg='white', anchor="e")
    rate_display_label.place(x=info_width, y=5, width=rate_display_width)

    # スクリーンショットを取得して背景画像を作成
    root.withdraw() # 自分のウィンドウを非表示に
    root.update() # 非表示状態を即座に反映
    screenshot = pyautogui.screenshot() # 自分のウィンドウが映り込まないように撮影
    chart_x = x_pos + info_width + rate_display_width
    bg_crop = screenshot.crop((chart_x, y_pos, chart_x + chart_width, y_pos + height))
    bg_image = ImageTk.PhotoImage(bg_crop)
    root.deiconify() # ウィンドウを再表示

    # ---チャート表示エリア（情報エリアの右）---
    chart = CandleChart(
        root, rates, info_labels=info_labels, symbol_short=symbol_short,
        timeframe=timeframe,
        chart_x=chart_x, chart_y=y_pos, chart_width=chart_width, chart_height=height,
        width=chart_width, height=height, bg='white', highlightthickness=0
    )
    chart.place(x=info_width + rate_display_width, y=0)

    # ---レート表示操作エリア(チャート表示エリアの右)---
    rate_control_area = tk.Frame(root, bg="gray", width=rate_control_width, height=height)
    rate_control_area.place(x=info_width + rate_display_width + chart_width + gap_between_chart_and_control, y=0)

    def on_rate_drag(event):
        y = event.y
        if 0 <= y <= height:
            price = chart.y_to_price(y)
            rate_display_label.config(text=f"{price:.3f}")

    def on_rate_release(event):
        rate_display_label.config(text="")

    rate_control_area.bind("<B1-Motion>", on_rate_drag)
    rate_control_area.bind("<ButtonRelease-1>", on_rate_release)

    # ---ドラッグエリア（右端）---
    drag_area = tk.Frame(root, bg='gray', width=drag_width, height=height)
    drag_area.place(x=info_width + rate_display_width + chart_width + gap_between_chart_and_control + rate_control_width + gap_between_control_and_drag, y=0)

    # マウスの押下時の位置を記録（ウィンドウ移動の起点）
    def start_move(event):
        root._drag_start_x = event.x_root
        root._drag_start_y = event.y_root

    # ドラッグ移動処理(マウスドラッグ)
    def on_drag(event):
        dx = event.x_root - root._drag_start_x
        dy = event.y_root - root._drag_start_y
        x = root.winfo_x() + dx
        y = root.winfo_y() + dy
        root.geometry(f"+{x}+{y}")
        root._drag_start_x = event.x_root
        root._drag_start_y = event.y_root
    
    # ドラッグ移動処理(マウスリリース)
    def on_drag_release(event):
        x = root.winfo_x()
        y = root.winfo_y()
        chart.chart_x = x + info_width + rate_display_width
        chart.chart_y = y
        chart.update_background_image()

    # ドラッグエリアにマウスイベントをバインド
    drag_area.bind("<ButtonPress-1>", start_move)
    drag_area.bind("<B1-Motion>", on_drag)
    drag_area.bind("<ButtonRelease-1>", on_drag_release)

    # 透明度を変更
    def increase_opacity(event=None):
        nonlocal opacity
        if opacity < 1.0:
            opacity = min(1.0, round(opacity + 0.1, 1))
            root.wm_attributes('-alpha', opacity)
            print(f"Opacity increased to: {opacity}")
    # 透明度を減少
    def decrease_opacity(event=None):
        nonlocal opacity
        if opacity > 0.1:
            opacity = max(0.1, round(opacity - 0.1, 1))
            root.wm_attributes('-alpha', opacity)
            print(f"Opacity decreased to: {opacity}")

    # timeframe変更イベント
    async def update_timeframe(new_timeframe):
        new_rates = await get_rates(symbol, new_timeframe, candle_count)
        chart.update_rates(new_rates)

        latest = new_rates[-1]
        dt = datetime.fromtimestamp(latest["time"], tz=timezone.utc)
        time_str = dt.strftime("%Y.%m.%d %H:%M")
        updated_values = [
            symbol_short,
            new_timeframe,
            time_str,
            f"{latest['open']:.3f}",
            f"{latest['high']:.3f}",
            f"{latest['low']:.3f}",
            f"{latest['close']:.3f}",
        ]
        for i, val in enumerate(updated_values):
            info_labels[i].config(text=val)
    
    # キーイベントでtimeframe変更
    def on_keypress(event):
        key = event.keysym
        if key == "Up":
            increase_opacity()
        elif key == "Down":
            decrease_opacity()
        elif key == "1":
            asyncio.run(update_timeframe("M1"))
        elif key == "2":
            asyncio.run(update_timeframe("M5"))
        elif key == "3":
            asyncio.run(update_timeframe("M15"))
        elif key == "4":
            asyncio.run(update_timeframe("M30"))
        elif key == "5":
            asyncio.run(update_timeframe("H1"))
        elif key == "6":
            asyncio.run(update_timeframe("H4"))
        elif key == "7":
            asyncio.run(update_timeframe("D1"))
        elif key == "8":
            asyncio.run(update_timeframe("W1"))
        elif key == "9":
            asyncio.run(update_timeframe("MN1"))

    # キーイベントをバインド
    root.bind("<Key>", on_keypress)

    # メインインベントのループ
    root.mainloop()

if __name__ == "__main__":
    main()
