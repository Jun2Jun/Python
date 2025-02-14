import json
import os
import sys
import TradeByGmo
from PyQt5.QtCore import Qt, QPoint, QTimer, QEvent
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit
from PyQt5.QtGui import QPalette, QColor

# CutomWindow, CustomTextEdit共通のイベントハンドラを定義
class EventHandlder:
    def __init__(self, parent):
        self.parent = parent
        self.old_pos = None
    
    def handleMousePressEvent(self, event):
        # ドラッグを開始
        if event.button() == Qt.LeftButton :
            self.old_pos = event.globalPos()

    def handleMouseMoveEvent(self, event):
        # ドラッグ中、ウィンドウの位置を更新
        if self.old_pos is not None:
            delta = event.globalPos() - self.old_pos
            self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
            self.old_pos = event.globalPos()

    def handleMouseReleaseEvent(self, event):
        # ドラッグ終了
        self.old_pos = None

    def handleKeyPressEvent(self, event):
        # スペースキーが押されたら入力ボックスを表示
        if event.key() == Qt.Key_Space:
            self.parent.input_box_pair.show()
            self.parent.input_box_pair.setFocus()  # 入力ボックスにフォーカスを移動
        
        # 上キーが押されたらウィンドウと文字の透明度を上げる
        elif event.key() == Qt.Key_Up:
            current_opacity = self.parent.windowOpacity()
            new_opacity = min(current_opacity + 0.1, 1.0)
            self.parent.setWindowOpacity(new_opacity)
            for widget in self.parent.findChildren(QWidget):
                widget.setWindowOpacity(new_opacity)
        
        # 下キーが押されたらウィンドウと文字の透明度を下げる
        elif event.key() == Qt.Key_Down:
            current_opacity = self.parent.windowOpacity()
            new_opacity = max(current_opacity - 0.1, 0.1) # 0になるとドラッグできなくなる
            self.parent.setWindowOpacity(new_opacity)
            for widget in self.parent.findChildren(QWidget):
                widget.setWindowOpacity(new_opacity)
        
        # 右キーが押されたらロットの表示を1カウントアップ
        elif event.key() == Qt.Key_Right:
            current_value = int(self.parent.label_lot.text())
            new_lot = current_value + 1
            if new_lot > 50:  # ロットの上限を50に設定
                new_lot = 50
            self.parent.label_lot.setText(str(new_lot))

        # 左キーが押されたらロットの表示を1カウントダウン
        elif event.key() == Qt.Key_Left:
            current_value = int(self.parent.label_lot.text())
            new_lot = current_value - 1
            if new_lot < 1:  # ロットの下限を1に設定
                new_lot = 1
            self.parent.label_lot.setText(str(new_lot))

        # Enterキーが押されたら入力ボックスを閉じる
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.parent.input_box_pair.isVisible():
                self.parent.input_box_pair.hide()  # 入力ボックスを非表示
                if self.parent.input_box_pair.text() != "":
                    self.parent.label_pair.setText(self.parent.input_box_pair.text()) # ペアをラベルに表示
                    self.parent.input_box_pair.clear()  # 入力ボックスをクリア
                self.parent.setFocus()  # ウィンドウにフォーカスを戻す
        
        # Ctrl + Shift + Aが押されたら買いエントリを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_A:
            # ロットの計算
            lot = 10000 * int(self.parent.label_lot.text())
            # 買いエントリ
            trade_result = TradeByGmo.TradeByGmo().entry_position(self.parent.label_pair.text(), lot, "BUY")
            if trade_result[0] == '0':
                self.parent.label_message.setText(trade_result[1])
            else:
                self.parent.label_message.setText(f"{trade_result[1]['message_code']} {trade_result[1]['message_string']}")
        
        # Ctrl + Shift + Bが押されたら売りエントリを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_B:
            # ロットの計算
            lot = 10000 * int(self.parent.label_lot.text())
            # 売りエントリ
            trade_result = TradeByGmo.TradeByGmo().entry_position(self.parent.label_pair.text(), lot, "SELL")
            if trade_result[0] == '0':
                self.parent.label_message.setText(trade_result[1])
            else:
                self.parent.label_message.setText(f"{trade_result[1][0]['message_code']} {trade_result[1][0]['message_string']}")
        
        # Ctrl + Shift + C押されたらポジションクローズを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_C:
            # ポジション一覧を取得
            result = TradeByGmo.TradeByGmo().get_position()
            # 取得成功の場合
            if result[0] == '0':
                position_list = result[1]
                # 保有ポジションがあればクローズを行う
                TradeByGmo.TradeByGmo().position_close(position_list)
            # 取得失敗の場合
            else:
                self.parent.label_message.setText(f"{trade_result[1][0]['message_code']}:{trade_result[1][0]['message_string']}")


# カスタムテキストエディットクラスを定義
# テキストエディット上で、マウスイベントを処理するために、カスタムテキストエディットクラスを作成
# -> ウィンドウ内のどこでもマウスイベント、キーイベントを拾えるようにしたかったが、
#    Ctrl + Shift + A/B/Cのキーイベントが拾えなかったため、カスタムテキストエディットのイベント処理はコメントアウト
#    ウィンドウとラベルの部分のみでイベントを拾うようにする
class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.event_handler = EventHandlder(parent)

    # def mousePressEvent(self, event):
    #     self.event_handler.handleMousePressEvent(event)
    #     super().mousePressEvent(event)

    # def mouseMoveEvent(self, event):
    #     self.event_handler.handleMouseMoveEvent(event)
    #     super().mouseMoveEvent(event)

    # def mouseReleaseEvent(self, event):
    #     self.event_handler.handleMouseReleaseEvent(event)
    #     super().mouseReleaseEvent(event)
    
    # def keyPressEvent(self, event):
    #     self.event_handler.handleKeyPressEvent(event)
    #     super().keyPressEvent(event)

class CustomWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.event_handler = EventHandlder(self)
        # 画面のサイズを取得
        screen_rect = QApplication.desktop().screenGeometry()
        screen_width = screen_rect.width()
        screen_height = screen_rect.height()

        # ウィンドウの設定
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # フレームレスで常に最前面
        self.setAttribute(Qt.WA_TranslucentBackground)  # ウィンドウを透明に設定
        self.setGeometry(screen_width - (200 + FONT_SIZE), 0, 200 + FONT_SIZE, 10*FONT_SIZE)  # ウィンドウのサイズを設定
        self.setStyleSheet("background-color: rgba(0, 0, 255, 0.01);")  # 背景色を設定 

        # ドラッグ用のラベルを追加
        self.label_drag_area = QLabel("", self)
        self.label_drag_area.setGeometry(0, 0, FONT_SIZE, self.height())
        self.label_drag_area.setStyleSheet("background-color: lightgray;")

        # ペアを表示するラベルを追加
        self.label_pair = QLabel("", self)
        self.label_pair.setGeometry(FONT_SIZE, 0, 100, FONT_SIZE)
        self.label_pair.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定

        # ペアの入力ボックスを非表示で初期化
        self.input_box_pair = QLineEdit(self)
        self.input_box_pair.setGeometry(FONT_SIZE, 0, 100, FONT_SIZE)
        self.input_box_pair.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定
        self.input_box_pair.hide()

        # Lotを表示するラベルを追加
        self.label_lot = QLabel('1', self)
        self.label_lot.setGeometry(FONT_SIZE, FONT_SIZE, 100, FONT_SIZE)
        self.label_lot.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定

        # Bidを表示するラベルを追加
        self.label_bid = QLabel('', self)
        self.label_bid.setGeometry(FONT_SIZE, 2*FONT_SIZE, 100, FONT_SIZE)
        self.label_bid.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定

        # Askを表示するラベルを追加
        self.label_ask = QLabel('', self)
        self.label_ask.setGeometry(FONT_SIZE, 3*FONT_SIZE, 100, FONT_SIZE)
        self.label_ask.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定

        # メッセージを表示するラベルを追加
        self.label_message = QLabel('', self)
        self.label_message.setGeometry(FONT_SIZE, 4*FONT_SIZE, 200, 2*FONT_SIZE)
        self.label_message.setStyleSheet(f"font-size: {FONT_SIZE}px;")  # フォントサイズを設定
        self.label_message.setAlignment(Qt.AlignTop)  # 上揃いに設定

        # ポジション一覧を表示するエリア
        self.edit_position = CustomTextEdit(self)
        self.edit_position.setGeometry(FONT_SIZE, 6*FONT_SIZE, 200, 4*FONT_SIZE)
        self.edit_position.setStyleSheet(f"font-size: {FONT_SIZE}px; border: none; background-color: rgba(0, 0, 255, 0.01);")  # フォントサイズを設定
        self.edit_position.setReadOnly(True)  # 編集不可に設定

        # 資産を表示するエリア
        self.edit_assets = CustomTextEdit(self)
        self.edit_assets.setGeometry(100 + FONT_SIZE, 0, 100, 120)
        self.edit_assets.setStyleSheet(f"font-size: {FONT_SIZE}px; border: none; background-color: rgba(0, 0, 255, 0.01);")  # フォントサイズを設定
        self.edit_assets.setReadOnly(True)  # 編集不可に設定

        # ドラッグを開始するための変数
        self.old_pos = None

        self.setFocusPolicy(Qt.StrongFocus)  # キーボードイベントを受け取るように設定

    def mousePressEvent(self, event):
        self.event_handler.handleMousePressEvent(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.event_handler.handleMouseMoveEvent(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.event_handler.handleMouseReleaseEvent(event)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        self.event_handler.handleKeyPressEvent(event)
        super().keyPressEvent(event)

    # 価格を更新する関数
    def UpdatePrice(self):
        bid, ask = TradeByGmo.TradeByGmo().get_price(self.label_pair.text())
        self.label_bid.setText(f"{bid}")
        self.label_ask.setText(f"{ask}")

    # メッセージをクリアする関数
    def ClearMessage(self):
        self.label_message.setText('')

    # 保有ポジションを更新する関数
    def UpdatePosition(self):
        str_position = ''
        result = TradeByGmo.TradeByGmo().get_position()
        # 取得成功し、ポジションがある場合
        if result[0] == '0':
            position_list = result[1]
            if position_list:
                for position in position_list:
                    symbol = position['symbol'][0] + position['symbol'][4]
                    side = position['side'][0]
                    size = str(int(position['size']) / 10000)
                    price = position['price']
                    loss_gain = position['lossGain']
                    str_position += f'{symbol}  {side}  {size}  {price}  {loss_gain}\n'
            self.edit_position.setText(str_position)
        # 取得失敗の場合
        else:
            self.label_message.setText(f"{result[1][0]['message_code']}\n{result[1][0]['message_string']}")
    
    # 資産情報を更新する関数
    def UpdateAssets(self):
        result = TradeByGmo.TradeByGmo().get_assets()
        # 取得成功し、ポジションがある場合
        if result[0] == '0':
            assets = result[1]
            equity = assets['equity'].split('.')[0]
            available = assets['availableAmount'].split('.')[0]
            margin_ratio = float(assets['marginRatio'])
            if margin_ratio > 1000:
                margin = 'Over 1000 %'
            else:
                margin = f'{assets["marginRatio"]} %'
            str_assets = f'{equity}\n{available}\n{margin}'
            self.edit_assets.setText(str_assets)
        # 取得失敗の場合
        else:
            self.label_message.setText(f"{result[1][0]['message_code']}\n{result[1][0]['message_string']}")

if __name__ == "__main__":
    # 設定の読み込み
    # 設定ファイル名
    config_file = "setting.json"
    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 設定ファイルのパスを生成
    config_path = os.path.join(script_dir, config_file)
    with open(config_path, "r") as f:
        config = json.load(f)
        REFRESH_INTERVAL = config["refresh_interval"]
        FONT_SIZE = config["font_size"]

    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()

    # 5秒ごとに価格とポジションの表示を更新
    timer = QTimer()
    timer.timeout.connect(window.UpdatePrice)
    timer.timeout.connect(window.ClearMessage)
    timer.timeout.connect(window.UpdatePosition)
    timer.timeout.connect(window.UpdateAssets)
    timer.start(REFRESH_INTERVAL)

    sys.exit(app.exec_())
