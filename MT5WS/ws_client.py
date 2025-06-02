import asyncio
import json
import websockets

# MT5 WebSocket サーバと通信するクライアントクラス
class MT5WebSocketClient:
    def __init__(self, uri="ws://192.168.1.39:8765"):
        # WebSocket サーバのURIを初期化
        self.uri = uri

    # 為替レートデータをリクエストし、結果を返す（非同期）
    # from_time を指定すれば差分のみ取得できる
    async def request_rates(self, symbol: str, timeframe: str, count: int = 100, from_time: int = None):
        payload = self._build_request(symbol, timeframe, count, from_time)
        async with websockets.connect(self.uri) as ws:
            await ws.send(json.dumps(payload))  # リクエスト送信
            response = await ws.recv()          # 非同期で応答受信
            return self._handle_response(response)  # 同期関数で処理

    # リクエストデータの作成
    def _build_request(self, symbol: str, timeframe: str, count: int, from_time: int = None):
        req = {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": count,
        }
        if from_time:
            req["from_time"] = from_time  # 差分取得開始時刻（UNIX秒）
        return req

    # サーバからの応答を検証・抽出する
    def _handle_response(self, raw_response: str):
        try:
            data = json.loads(raw_response)
            if "error" in data:
                raise RuntimeError(f"Server error: {data['error']}")
            if "data" not in data:
                raise ValueError("No 'data' field in response.")
            return data["data"]
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON response received")

# テスト用の実行スクリプト（直接実行された場合のみ動作）
if __name__ == "__main__":
    async def test():
        client = MT5WebSocketClient()
        try:
            candles = await client.request_rates("USDJPY", "H1", 10)
            for c in candles:
                print(c)
        except Exception as e:
            print("Error:", e)

    asyncio.run(test())
