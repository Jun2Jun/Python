import yaml
from ruamel.yaml import YAML

# settings.yaml を読み込む
yaml = YAML()
with open("settings.yaml", "r", encoding="utf-8") as f:
    settings = yaml.load(f)

# 移動平均線で使用する期間のリスト
moving_average_periods = settings.get("moving_average_periods", [20, 75, 200])

# 移動平均線の色リスト
moving_average_colors = settings.get("moving_average_colors", ["black", "black", "black"])

# チャート自動更新の間隔（秒単位）デフォルトは60秒
auto_update_interval = settings.get("auto_update_interval", 60)

# MT5 WebSocketサーバの接続先URI（デフォルトはローカルホスト）
websocket_uri = settings.get("websocket_uri", "ws://localhost:8765")


