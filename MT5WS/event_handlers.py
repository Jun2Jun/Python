from utils import take_full_screenshot

# レート操作エリアでドラッグされたときの処理をバインド
def bind_drag_events(canvas, chart, label, height, info_width, rate_display_width):
    def on_drag(event):
        y = event.y
        if 0 <= y <= height:
            price = chart.y_to_price(y)
            label.config(text=chart.format_func(price))
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

        # レート操作キャンバスの位置も更新
        rate_control_canvas.chart_x = chart.chart_x + config['chart_width']
        rate_control_canvas.chart_y = y

        # スクリーンショットを取得
        screenshot = take_full_screenshot()
        
        # 各キャンバスに crop 済みの画像を渡す
        chart.update_background_image(screenshot)
        rate_control_canvas.update_background_image(screenshot)

        root.focus_force()
    
    return start_move, on_drag, on_release
