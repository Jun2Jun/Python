import asyncio
import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime, timezone
from PIL import ImageTk
import pyautogui

from chart_canvas import CandleChart
from rate_control_canvas import RateControlCanvas
from event_handlers import bind_drag_events, bind_drag_window_events, bind_key_events
from ws_client import MT5WebSocketClient

# アプリケーションのエントリーポイント

def main():
    symbol = "USDJPY"     # 通貨ペア指定
    timeframe = "M5"      # タイムフレーム指定
    candle_count = 250    # ロウソク足の数を指定

    # WebSocketクライアントを初期化
    client = MT5WebSocketClient()

    # ★ timeframeごとのキャッシュを保持する辞書
    cached_data = {}

    # 同期的にレートを取得する関数（初期表示用）
    def fetch_rates_sync(symbol, timeframe, count):
        return asyncio.run(client.request_rates(symbol, timeframe, count))

    # キャッシュがなければ初回データを取得
    if timeframe not in cached_data:
        cached_data[timeframe] = fetch_rates_sync(symbol, timeframe, candle_count)
    rates = cached_data[timeframe]

    # メインウィンドウの設定
    root = tk.Tk()
    root.overrideredirect(True)  # タイトルバー・枠なし
    root.config(bg='white')
    root.wm_attributes('-transparentcolor', 'white')
    opacity = [0.3]  # 初期透明度
    root.wm_attributes('-alpha', opacity[0])

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    latest = rates[-1]

    # レイアウトサイズ定義
    candle_width = 2
    candle_gap = 1
    chart_width = candle_count * (candle_width + candle_gap)
    info_width = 120     # 情報エリアの幅
    rate_display_width = 40 # レート表示ラベルの幅
    rate_control_width = 20 # マウス操作エリアの幅
    drag_width = 10      # ドラッグ領域の幅
    height = 300

    total_width = info_width + rate_display_width + chart_width + rate_control_width + drag_width

    # ウィンドウの表示位置（右下）
    x_pos = screen_width - total_width
    y_pos = screen_height - height
    root.geometry(f"{total_width}x{height}+{x_pos}+{y_pos}")

    # --- 情報表示エリア（左） ---
    info_frame = tk.Frame(root, bg='white', width=info_width, height=height)
    info_frame.place(x=0, y=0)
    font = tkFont.Font(size=9)
    symbol_short = symbol[0] + symbol[3]
    dt = datetime.fromtimestamp(latest["time"], tz=timezone.utc)
    time_str = dt.strftime("%Y.%m.%d %H:%M")
    info_values = [symbol_short, timeframe, time_str, f"{latest['open']:.3f}", f"{latest['high']:.3f}", f"{latest['low']:.3f}", f"{latest['close']:.3f}"]
    info_labels = []
    for i, text in enumerate(info_values):
        label = tk.Label(info_frame, text=text, anchor="w", font=font, bg='white')
        label.place(x=5, y=5 + i * 14)
        info_labels.append(label)

    # --- レート表示ラベル（情報エリアとチャートの間） ---
    rate_display_label = tk.Label(root, text="", font=font, bg='white', anchor="e")
    rate_display_label.place(x=info_width, y=5, width=rate_display_width)

    # 背景取得用にスクリーンショットを撮影
    root.withdraw()
    root.update()
    screenshot = ImageTk.PhotoImage(
        pyautogui.screenshot().crop((x_pos + info_width + rate_display_width, y_pos, x_pos + info_width + rate_display_width + chart_width, y_pos + height))
    )
    root.deiconify()

    # --- チャート表示エリア ---
    chart = CandleChart(
        root, rates, info_labels=info_labels, symbol_short=symbol_short, timeframe=timeframe,
        chart_x=x_pos + info_width + rate_display_width, chart_y=y_pos,
        chart_width=chart_width, chart_height=height,
        width=chart_width, height=height, bg='white', highlightthickness=0
    )
    chart.place(x=info_width + rate_display_width, y=0)

    # --- レート操作エリア（チャートの右） ---
    rate_control_canvas = RateControlCanvas(
        root,
        chart_x=x_pos + info_width + rate_display_width + chart_width,
        chart_y=y_pos,
        width=rate_control_width,
        height=height
    )
    rate_control_canvas.place(x=info_width + rate_display_width + chart_width, y=0)

    # マウス操作イベントをバインド
    bind_drag_events(rate_control_canvas, chart, rate_display_label, height, info_width, rate_display_width)

    # --- ウィンドウのドラッグ移動エリア（右端） ---
    drag_area = tk.Frame(root, bg='gray', width=drag_width, height=height)
    drag_area.place(x=info_width + rate_display_width + chart_width + rate_control_width, y=0)

    # ウィンドウドラッグ処理の構成情報
    config = {
        'info_width': info_width,
        'rate_display_width': rate_display_width,
        'chart_width': chart_width
    }
    start_move, on_drag, on_release = bind_drag_window_events(root, chart, rate_control_canvas, config)
    drag_area.bind("<ButtonPress-1>", start_move)
    drag_area.bind("<B1-Motion>", on_drag)
    drag_area.bind("<ButtonRelease-1>", on_release)

    # キャッシュに追記する get_rates_func（差分取得対応）
    async def get_rates_func(symbol, tf, count):
        if tf not in cached_data:
            cached_data[tf] = await client.request_rates(symbol, tf, count)
        else:
            last_time = cached_data[tf][-1]["time"]
            new_data = await client.request_rates(symbol, tf, count=100, from_time=last_time)
            if new_data:
                # 前回の最新ロウソク足を置き換え、後続を追加
                updated = [d for d in new_data if d["time"] >= last_time]
                if updated:
                    cached_data[tf][-1] = updated[0]  # 上書き
                    cached_data[tf].extend(updated[1:])  # それ以降を追加

        return cached_data[tf]

    # キーボードイベント（透明度変更・timeframe変更）
    bind_key_events(root, chart, symbol, symbol_short, candle_count, info_labels, opacity, get_rates_func)

    # メインループ開始
    root.mainloop()

if __name__ == "__main__":
    main()
