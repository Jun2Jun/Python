import asyncio
from datetime import datetime, timezone

# レート表示エリアでドラッグされたときの処理をバインド

def bind_drag_events(canvas, chart, label, height, info_width, rate_display_width):
    def on_drag(event):
        y = event.y
        if 0 <= y <= height:
            price = chart.y_to_price(y)
            label.config(text=f"{price:.3f}")
            adjusted_y = y - label.winfo_reqheight() // 2
            label.place(x=info_width, y=adjusted_y, width=rate_display_width)
            chart.show_dashed_line(y)

    def on_release(event):
        label.config(text="")
        chart.hide_dashed_line()

    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

# ウィンドウ全体をドラッグ移動させる処理

def bind_drag_window_events(root, chart, rate_control_canvas, config):
    def start_move(event):
        root._drag_start_x = event.x_root
        root._drag_start_y = event.y_root

    def on_drag(event):
        dx = event.x_root - root._drag_start_x
        dy = event.y_root - root._drag_start_y
        x = root.winfo_x() + dx
        y = root.winfo_y() + dy
        root.geometry(f"+{x}+{y}")
        root._drag_start_x = event.x_root
        root._drag_start_y = event.y_root

    def on_release(event):
        x = root.winfo_x()
        y = root.winfo_y()
        chart.chart_x = x + config['info_width'] + config['rate_display_width']
        chart.chart_y = y
        chart.update_background_image()
        rate_control_canvas.chart_x = x + config['info_width'] + config['rate_display_width'] + config['chart_width']
        rate_control_canvas.chart_y = y
        rate_control_canvas.update_background_image()
        root.focus_force()

    return start_move, on_drag, on_release

# キーボード操作でtimeframe変更や透明度変更

def bind_key_events(root, chart, symbol, symbol_short, candle_count, info_labels, opacity_ref, get_rates_func):
    def increase_opacity():
        if opacity_ref[0] < 1.0:
            opacity_ref[0] = min(1.0, round(opacity_ref[0] + 0.1, 1))
            root.wm_attributes('-alpha', opacity_ref[0])

    def decrease_opacity():
        if opacity_ref[0] > 0.1:
            opacity_ref[0] = max(0.1, round(opacity_ref[0] - 0.1, 1))
            root.wm_attributes('-alpha', opacity_ref[0])

    async def update_timeframe(new_timeframe):
        new_rates = await get_rates_func(symbol, new_timeframe, candle_count)
        chart.update_rates(new_rates, new_timeframe)
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
        root.focus_force()

    def on_key(event):
        key = event.keysym
        if key == "Up":
            increase_opacity()
        elif key == "Down":
            decrease_opacity()
        elif key in "123456789":
            timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]
            idx = int(key) - 1
            if idx < len(timeframes):
                asyncio.run(update_timeframe(timeframes[idx]))

    root.bind("<Key>", on_key)
