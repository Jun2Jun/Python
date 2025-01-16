import requests
import datetime
import time
import csv
import pytz

# GMOコインの全データを取得するPublic APIのURL
TICKER_URL = "https://forex-api.coin.z.com/public/v1/ticker"

# 取得する通貨ペア
PAIR = "USD_JPY"

# CSVファイルの出力先
CSV_FILE = "usd_jpy_spread.csv"

# ヘッダーを作成
headers = ["time", "ask", "bid", "spread"]

# 初期化
with open(CSV_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)

# 無限ループで1分ごとにデータを取得し、CSVに書き込む
while True:
    try:
        # APIリクエスト
        response = requests.get(f"{TICKER_URL}")
        data = response.json()

        # データを抽出
        for list in data.items():
            if list[0] == "data":
                for item in list[1]:
                    if item['symbol'] == PAIR:
                        # スプレッドの計算
                        spread = round(float(item['ask']) - float(item['bid']), 3)

                        # 取得した時間を日本時間に変換
                        timestamp = datetime.datetime.fromisoformat(item['timestamp'])
                        jst = pytz.timezone('Asia/Tokyo')
                        jst_timestamp = timestamp.astimezone(jst)
                        formatted_jst_timestamp = jst_timestamp.strftime("%Y/%m/%d %H:%M:%S")

                        # CSVに書き込み
                        with open(CSV_FILE, 'a', newline='') as f:
                            writer = csv.writer(f)
                            writer.writerow([formatted_jst_timestamp, item['ask'], item['bid'], spread])
                            print(f"{formatted_jst_timestamp},{item['ask']},{item['bid']},{spread}")
                        break
    except Exception as e:
        print(f"Error: {e}")

    # 1分間待機
    time.sleep(60)