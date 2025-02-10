import json
import os
import sys
import TradeByGmo
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QLineEdit
from PyQt5.QtGui import QPalette, QColor

class CustomWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ウィンドウの設定
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # フレームレスで常に最前面
        self.setAttribute(Qt.WA_TranslucentBackground)  # ウィンドウを透明に設定
        self.setGeometry(100, 100, 400, 300)

        # ドラッグ領域を作成
        self.drag_area = QWidget(self)
        self.drag_area.setGeometry(0, 0, 10, self.height())  # 左側にドラッグエリアを配置
        self.drag_area.setStyleSheet("background-color: rgba(0, 0, 255, 0.01);")  # ドラッグ領域の背景色

        # ペアを表示するラベルを追加
        self.label_pair = QLabel("", self)
        self.label_pair.setGeometry(30, 10, 100, 20)

        # ペアの入力ボックスを非表示で初期化
        self.input_box_pair = QLineEdit(self)
        self.input_box_pair.setGeometry(30, 10, 100, 20)
        self.input_box_pair.hide()

        # Lotを表示するラベルを追加
        self.label_lot = QLabel('1', self)
        self.label_lot.setGeometry(140, 10, 100, 20)

        # Bidを表示するラベルを追加
        self.label_bid = QLabel('', self)
        self.label_bid.setGeometry(30, 40, 100, 20)

        # Askを表示するラベルを追加
        self.label_ask = QLabel('', self)
        self.label_ask.setGeometry(140, 40, 100, 20)

        # ポジション一覧を表示するラベルを追加
        self.label_position = QLabel('', self)
        self.label_position.setGeometry(30, 140, 200, 130)

        # メインウィジェットの背景を透明に設定
        main_widget = QWidget(self)
        main_widget.setGeometry(100, 0, 300, self.height())  # 残りの領域をカバー
        main_widget.setStyleSheet("background-color: transparent;")  # 透明に設定

        #layout = QVBoxLayout(main_widget)
        #layout.addWidget(QLabel("Main Content Area (transparent)", self))

        # ドラッグを開始するための変数
        self.old_pos = None

    def mousePressEvent(self, event):
        # ドラッグエリア内でクリックされた場合、ドラッグを開始
        if event.button() == Qt.LeftButton and self.drag_area.geometry().contains(event.pos()):
            self.old_pos = event.pos()

    def mouseMoveEvent(self, event):
        # ドラッグ中、ウィンドウの位置を更新
        if self.old_pos is not None:
            delta = QPoint(event.globalPos() - self.mapToGlobal(self.old_pos))
            self.move(self.x() + delta.x(), self.y() + delta.y())

    def mouseReleaseEvent(self, event):
        # ドラッグ終了
        self.old_pos = None

    def keyPressEvent(self, event):
        # スペースキーが押されたら入力ボックスを表示
        if event.key() == Qt.Key_Space:
            self.input_box_pair.show()
            self.input_box_pair.setFocus()  # 入力ボックスにフォーカスを移動
        
        # 上キーが押されたらロットの表示を1カウントアップ
        elif event.key() == Qt.Key_Up:
            current_value = int(self.label_lot.text())
            new_lot = current_value + 1
            if new_lot > 50:  # ロットの上限を50に設定
                new_lot = 50
            self.label_lot.setText(str(new_lot))

        # 下キーが押されたらロットの表示を1カウントダウン
        elif event.key() == Qt.Key_Down:
            current_value = int(self.label_lot.text())
            new_lot = current_value - 1
            if new_lot < 1:  # ロットの下限を1に設定
                new_lot = 1
            self.label_lot.setText(str(new_lot))

        # Enterキーが押されたら入力ボックスを閉じる
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.input_box_pair.isVisible():
                self.input_box_pair.hide()  # 入力ボックスを非表示
                if self.input_box_pair.text() != "":
                    self.label_pair.setText(self.input_box_pair.text()) # ペアをラベルに表示
                    self.input_box_pair.clear()  # 入力ボックスをクリア
                self.setFocus()  # ウィンドウにフォーカスを戻す
        
        # Ctrl + Shift + Aが押されたら買いエントリを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_A:
            # ロットの計算
            lot = 10000 * int(self.label_lot.text())
            # 買いエントリ
            TradeByGmo.TradeByGmo().entry_position(self.label_pair.text(), lot, "BUY")
        
        # Ctrl + Shift + Bが押されたら売りエントリを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_B:
            # ロットの計算
            lot = 10000 * int(self.label_lot.text())
            # 買いエントリ
            TradeByGmo.TradeByGmo().entry_position(self.label_pair.text(), lot, "SELL")
        
        # Ctrl + Shift + C押されたらポジションクローズを行う
        elif (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.ShiftModifier) and event.key() == Qt.Key_C:
            # ポジション一覧を取得
            position_list = TradeByGmo.TradeByGmo().get_position()
            # 保有ポジションがあればクローズを行う
            TradeByGmo.TradeByGmo().position_close(position_list)

    # 価格を更新する関数
    def UpdatePrice(self):
        bid, ask = TradeByGmo.TradeByGmo().get_price(self.label_pair.text())
        self.label_bid.setText(f"{bid}")
        self.label_ask.setText(f"{ask}")

    # 保有ポジションを更新する関数
    def UpdatePosition(self):
        str_position = ''
        position_list = TradeByGmo.TradeByGmo().get_position()
        if position_list:
            for position in position_list:
                symbol = position['symbol'][0] + position['symbol'][4]
                side = position['side']
                size = position['size']
                price = position['price']
                loss_gain = position['lossGain']
                str_position += f'{symbol}  {side}  {size}  {price}  {loss_gain}\n'
        self.label_position.setText(str_position)

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

    app = QApplication(sys.argv)
    window = CustomWindow()
    window.show()

    # 5秒ごとに価格とポジションの表示を更新
    timer = QTimer()
    timer.timeout.connect(window.UpdatePrice)
    timer.timeout.connect(window.UpdatePosition)
    timer.start(REFRESH_INTERVAL)

    sys.exit(app.exec_())
