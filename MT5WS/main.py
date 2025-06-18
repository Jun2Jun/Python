import asyncio
import tkinter as tk
import tkinter.font as tkFont
import tkinter.simpledialog
from datetime import datetime, timezone
from PIL import ImageTk
import pyautogui

from chart_canvas import CandleChart
from config import moving_average_periods
from rate_control_canvas import RateControlCanvas
from event_handlers import bind_drag_events, bind_drag_window_events
from ws_client import MT5WebSocketClient

# --- 通貨コード → 正式通貨ペアへのマッピング ---
SYMBOL_MAP = {
    "UJ": "USDJPY",
    "EU": "EURUSD",
    "EJ": "EURJPY",
    "GU": "GBPUSD",
    "GJ": "GBPJPY",
    "AU": "AUDUSD",
    "AJ": "AUDJPY",
    "XU": "GOLD",
}

# 通貨ペア略称に応じた小数点桁数
DECIMAL_PLACES_MAP = {
    "EU": 5, "GU": 5, "AU": 5,
    "UJ": 3, "EJ": 3, "GJ": 3, "AJ": 3,
    "XU": 2,
}

def get_format_func(symbol_short):
    digits = DECIMAL_PLACES_MAP.get(symbol_short.upper(), 3) # デフォルト3桁
    return lambda value: f"{value:.{digits}f}"

# アプリケーションのエントリーポイント
def main():
    symbol = "USDJPY"     # 通貨ペア指定
    timeframe = "M5"      # タイムフレーム指定
    candle_count = 250    # ロウソク足の数を指定

    max_ma_period = max(moving_average_periods)  # 最大移動平均期間を取得
    required_candle_count = candle_count + max_ma_period  # 表示＋移動平均に必要な本数

    # WebSocketクライアントを初期化
    client = MT5WebSocketClient()

    # timeframeごとのキャッシュを保持する辞書
    cached_data = {}

    # 同期的にレートを取得する関数（初期表示用）
    def fetch_rates_sync(symbol, timeframe, count):
        return asyncio.run(client.request_rates(symbol, timeframe, count))

    # キャッシュがなければ初回データを取得
    cache_key = f"{symbol}_{timeframe}"
    if cache_key not in cached_data:
        cached_data[cache_key] = fetch_rates_sync(symbol, timeframe, required_candle_count)
    rates = cached_data[cache_key][-required_candle_count:] # 表示用だけでなく移動平均用の期間も含める

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
    fmt = get_format_func(symbol_short)
    info_values = [
        symbol_short, timeframe, time_str,
        fmt(latest['open']),
        fmt(latest['high']),
        fmt(latest['low']),
        fmt(latest['close']),
    ]
    info_labels = []
    for i, text in enumerate(info_values):
        label = tk.Label(info_frame, text=text, anchor="w", font=font, bg='white')
        label.place(x=5, y=5 + i * 14)
        info_labels.append(label)

    # --- レート表示ラベル（情報エリアとチャートの間） ---
    rate_display_label = tk.Label(root, text="", font=font, bg='white', anchor="e")
    rate_display_label.place(x=info_width, y=5, width=rate_display_width)

    root.withdraw()
    root.update()
    root.deiconify()

    # --- エントリ入力エリアの作成（透明、フォント一致） ---
    symbol_entry = tk.Entry(root, font=font)
    symbol_entry.place_forget()

    # --- チャート表示エリア ---
    chart = CandleChart(
        root, rates, info_labels=info_labels, symbol_short=symbol_short, timeframe=timeframe,
        chart_x=x_pos + info_width + rate_display_width, chart_y=y_pos,
        chart_width=chart_width, chart_height=height, candle_display_count=candle_count,
        width=chart_width, height=height, bg='white', highlightthickness=0,
        format_func=fmt, symbol_entry=symbol_entry
    )
    chart.place(x=info_width + rate_display_width, y=0)

    chart.load_all_line_data() # ラインの読み込み
    chart.apply_line_data_to_chart(symbol) # ラインの反映
    chart.redraw_horizontal_lines() # 水平線の再描画
    chart.redraw_diagonal_lines() # 斜め線の再描画

    # --- レート操作エリア（チャートの右） ---
    rate_control_canvas = RateControlCanvas(
        root,
        chart_x=x_pos + info_width + rate_display_width + chart_width,
        chart_y=y_pos,
        width=rate_control_width,
        height=height
    )
    rate_control_canvas.place(x=info_width + rate_display_width + chart_width, y=0)

    # --- 通貨切替処理 ---
    def switch_symbol(new_short):
        nonlocal symbol, symbol_short, rates
        mapped = SYMBOL_MAP.get(new_short.upper())
        if not mapped:
            return
        symbol = mapped
        symbol_short = new_short.upper()
        fmt = get_format_func(symbol_short)

        cache_key = f"{symbol}_{chart.timeframe}"
        if cache_key not in cached_data:
            cached_data[cache_key] = fetch_rates_sync(symbol, chart.timeframe, required_candle_count)
        rates = cached_data[cache_key][-required_candle_count:]

        chart.rates = rates
        chart.symbol_short = symbol_short
        chart.format_func = fmt

        # --- 古い移動平均線を削除 ---
        for line_id in chart.ma_lines:
            chart.delete(line_id)
        chart.ma_lines.clear()

        # ラインの反映
        chart.apply_line_data_to_chart(symbol)

        # チャートのリフレッシュ
        chart.refresh_chart()

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
        cache_key = f"{symbol}_{tf}" # キャッシュキーを通貨ペア(symbol)とタイムフレーム(tf)で作成
        # キャッシュに該当データがない場合、サーバから新規に取得してキャッシュに格納
        if cache_key not in cached_data:
            cached_data[cache_key] = await client.request_rates(symbol, tf, count)
        else:
            # キャッシュの最新データの時刻を取得
            last_time = cached_data[cache_key][-1]["time"]
            # 最新時刻以降のデータを100件取得（過去の更新を含める可能性も考慮）
            new_data = await client.request_rates(symbol, tf, count=100, from_time=last_time)
            if new_data:
                # 新しいデータの中で、last_time以降のデータのみを抽出（重複防止）
                updated = [d for d in new_data if d["time"] >= last_time]
                if updated:
                     # 既存の最後のデータを新しいデータで置き換え（同一時刻でも内容が更新されている可能性があるため）
                    cached_data[cache_key][-1] = updated[0]
                    # 残りの新規データをキャッシュに追加
                    cached_data[cache_key].extend(updated[1:])
        return cached_data[cache_key]

    # --- EnterとSpaceでの通貨入力・表示切替対応 ---
    def on_key_custom(event):
        if event.keysym == "space":
            symbol_entry.delete(0, tk.END)  # 前回の入力をクリア
            symbol_entry.place(x=5, y=5 + 7 * 14, width=info_width - 10)
            symbol_entry.lift()
            symbol_entry.focus_set()
        elif event.keysym == "Return":
            if symbol_entry.winfo_ismapped():
                text = symbol_entry.get().strip()
                symbol_entry.place_forget()
                if text:
                    switch_symbol(text)
                root.after_idle(lambda: root.focus_force())
            else:
                chart.toggle_chart_visibility()

    # --- カスタムキーバインド（元の bind_key_events の内容含む） ---
    async def update_timeframe(new_timeframe):
        nonlocal fmt
        new_rates = await get_rates_func(symbol, new_timeframe, required_candle_count)
        fmt = get_format_func(symbol_short)  # 通貨ペアに対応する桁数を再取得   
        chart.format_func = fmt # チャートにも反映
        chart.update_rates(new_rates, new_timeframe)
        latest = new_rates[-1]
        dt = datetime.fromtimestamp(latest["time"], tz=timezone.utc)
        time_str = dt.strftime("%Y.%m.%d %H:%M")
        updated_values = [
            symbol_short, new_timeframe, time_str,
            fmt(latest['open']),
            fmt(latest['high']),
            fmt(latest['low']),
            fmt(latest['close']),
        ]
        for i, val in enumerate(updated_values):
            info_labels[i].config(text=val)
        root.focus_force()
    
    # ここでchart.update_funcにupdate_timeframeの処理を設定
    chart.update_func = update_timeframe

    def bind_custom_keys():
        def on_all_keys(event):
            on_key_custom(event)
            key = event.keysym
            if key == "h":
                chart.toggle_horizontal_line_mode()
            elif key == "d":
                chart.toggle_diagonal_line_mode()
            elif key == "m":
                chart.toggle_moving_averages()
            elif key == "t":
                chart.toggle_time_dividers()
            elif key == "Up":
                if opacity[0] < 1.0:
                    opacity[0] = round(min(1.0, opacity[0] + 0.1), 1)
                    root.wm_attributes('-alpha', opacity[0])
            elif key == "Down":
                if opacity[0] > 0.1:
                    opacity[0] = round(max(0.1, opacity[0] - 0.1), 1)
                    root.wm_attributes('-alpha', opacity[0])
            elif key == "Delete":
                symbol = chart.symbol_short
                # 水平線が選択されている場合
                if chart.selected_hline_index is not None:
                    idx = chart.selected_hline_index
                    chart.delete(chart.hline_ids[idx])      # 線削除
                    del chart.hline_ids[idx]
                    del chart.hline_data[symbol][idx]
                    # スタイルも削除
                    chart.hline_styles = {
                        (s, i if i < idx else i - 1): style
                        for (s, i), style in chart.hline_styles.items()
                        if s == symbol and i != idx
                    }
                    chart.hide_hline_handles()
                    chart.selected_hline_index = None
                    chart.update_line_data_cache(symbol)

                # 斜め線が選択されている場合
                elif chart.selected_diagonal_index is not None:
                    idx = chart.selected_diagonal_index
                    chart.delete(chart.diagonal_line_ids[idx])  # 線削除
                    del chart.diagonal_line_ids[idx]
                    del chart.diagonal_data[idx]
                    # スタイルも削除
                    chart.diagonal_styles = {
                        (s, i if i < idx else i - 1): style
                        for (s, i), style in chart.diagonal_styles.items()
                        if s == symbol and i != idx
                    }
                    chart.hide_diagonal_handles()
                    chart.selected_diagonal_index = None
                    chart.update_line_data_cache(symbol)
            elif key in "123456789": # タイムフレームの切り替え
                timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
                idx = int(key) - 1
                if idx < len(timeframes):
                    asyncio.run(update_timeframe(timeframes[idx]))
            elif key == "Escape": # プログラムの終了
                on_close()

        root.bind("<Key>", on_all_keys)

    bind_custom_keys()

    root.focus_force() # メインループ前にrootに強制的にフォーカスをセット

    # 終了時の処理
    def on_close():
        chart.save_all_line_data()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # メインループ開始
    root.mainloop()

if __name__ == "__main__":
    main()
