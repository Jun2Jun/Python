import asyncio
import websockets
import json

# WebSocketサーバのURI
SERVER_URI = "ws://localhost:8765"

async def get_rates(
    symbol: str,
    timeframe: str,
    count: int = 100,
    ):
    """
    WebSocketでサーバに為替レートの取得を依頼し、ロウソク足データを受信して返す。
    symbol: 通貨ペア (例: "USDJPY")
    timeframe: タイムフレーム (例: "M1", "H1")
    count: 取得するロウソク足の本数
    
    返り値: 
      [
        {"time": int, "open": float, "high": float, "low": float, "close": float, "tick_volume": float},
        ...
      ]
    """
    request_data = {
        "symbol": symbol,
        "timeframe": timeframe,
        "count": count,
    }
    async with websockets.connect(SERVER_URI) as websocket:
        await websocket.send(json.dumps(request_data))
        response = await websocket.recv()
        data = json.loads(response)

        if "error" in data:
            raise RuntimeError(f"Server error: {data['error']}")

        rates = data.get("data", [])
        return rates

# テスト実行用コード（直接実行時のみ）
if __name__ == "__main__":
    import sys

    symbol = "USDJPY"
    timeframe = "H1"
    count = 10

    async def test():
        try:
            rates = await get_rates(symbol, timeframe, count)
            print(f"Received {len(rates)} candles for {symbol} timeframe {timeframe}")
            for r in rates:
                print(r)
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
