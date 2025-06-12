import yaml

# settings.yaml を読み込む
with open("settings.yaml", "r", encoding="utf-8") as f:
    settings = yaml.safe_load(f)

# 移動平均線で使用する期間のリスト
moving_average_periods = settings.get("moving_average_periods", [20, 75, 200])

# チャート自動更新の間隔（秒単位）デフォルトは60秒
auto_update_interval = settings.get("auto_update_interval", 60)

# MT5 WebSocketサーバの接続先URI（デフォルトはローカルホスト）
websocket_uri = settings.get("websocket_uri", "ws://localhost:8765")