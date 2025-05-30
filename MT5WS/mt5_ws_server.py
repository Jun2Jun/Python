import asyncio
import json
import websockets
import MetaTrader5 as mt5
from datetime import datetime, timezone

# WebSocket サーバのホストとポート
HOST = '0.0.0.0'
PORT = 8765

# 時間足の文字列を MT5 の定数に変換するマップ
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}

# MT5 を初期化する関数

def init_mt5():
    if not mt5.initialize():
        return False, "MT5 initialization failed"
    return True, ""

# クライアントからのリクエストに基づいてレートデータを取得する非同期関数
# from_time が指定された場合、その時刻以降のレートを取得
async def get_rates(symbol, timeframe_str, count, from_time=None):
    ok, err = init_mt5()
    if not ok:
        return {"error": err}

    timeframe = TIMEFRAME_MAP.get(timeframe_str.upper())
    if timeframe is None:
        return {"error": f"Invalid timeframe: {timeframe_str}"}

    if from_time:
        try:
            # from_time はすでに UTC 時間（UNIX秒）として渡されるため、再度の補正を避ける
            utc_from = datetime.fromtimestamp(int(from_time), tz=timezone.utc)
            rates = mt5.copy_rates_from(symbol, timeframe, utc_from, count)
        except Exception as e:
            return {"error": str(e)}
    else:
        # from_time が指定されていない場合は最新から count 件取得
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

    if rates is None:
        return {"error": f"Failed to get rates for {symbol} with timeframe {timeframe_str}"}

    # numpy 型を通常の Python 型に変換
    rates_list = []
    for row in rates:
        rates_list.append({
            "time": int(row["time"]),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "tick_volume": int(row["tick_volume"]),
            "spread": int(row["spread"]),
            "real_volume": int(row["real_volume"]),
        })

    return {
        "type": "rates",
        "symbol": symbol,
        "timeframe": timeframe_str,
        "count": count,
        "data": rates_list
    }

# WebSocket 接続ごとの処理（メッセージ受信 → レート取得 → 応答送信）
async def handle_connection(websocket):
    async for message in websocket:
        print(f"[Request] {message}")
        try:
            request = json.loads(message)
            symbol = request.get("symbol")
            timeframe = request.get("timeframe")
            count = int(request.get("count", 100))
            from_time = request.get("from_time")  # オプション: 差分取得用の開始時刻

            if not symbol or not timeframe:
                raise ValueError("Missing 'symbol' or 'timeframe'")

            data = await get_rates(symbol.upper(), timeframe.upper(), count, from_time)
        except Exception as e:
            data = {"error": str(e)}

        await websocket.send(json.dumps(data))

# サーバ起動のエントリーポイント
async def main():
    print(f"WebSocket server starting on ws://{HOST}:{PORT}")
    async with websockets.serve(handle_connection, HOST, PORT):
        await asyncio.Future()  # 永続実行

if __name__ == "__main__":
    asyncio.run(main())
