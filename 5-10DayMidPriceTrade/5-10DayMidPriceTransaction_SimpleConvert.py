from enum import Enum
from datetime import datetime
import hashlib
import hmac
import json
import requests
import sys
import time

# Constants for trade settings
API_LABEL = "gmo-fx-api"
API_KEY = "OOkd+TEJxLY3DIEzX9x7eDMfQAMyUdcI"
API_SECRET = "iL14cy0Z7txQfEQsuetvZ0VL2gF96ZwlpR1P3FpFB6jkfMw/Z52b0maM27stIgc4"
EA_NAME = "FiveTenDayMidPriceTransaction"
LOT_OPTIMIZE = True # ロットサイズの最適化実施フラグ
DEFAULT_LOT_SIZE = 10000 # デフォルトのロットサイズ
MAX_LOT_SIZE = 500000 # 最大ロットサイズ
LIVERRAGE = 25 # リバレッジ
PAIR = "USD_JPY" # "通貨ペア"
SLIPPAGE = 10
SPREAD_LIMIT = 0.003

# 各種フラグ
buy_entry_on = True
sell_entry_on = True
input_sell_on = True
input_friday_on = True

# 共通変数
LotSize = DEFAULT_LOT_SIZE
OrderId = 0 # エントリ時に返却される注文ID
PositionId = 0 # 決済に使用するポジションID (約定情報からOrderIdをキーに取得する)

# スプレッドの判定
def is_spread_ok() -> bool:
    # GMOコインの全データを取得するPublic APIのURL
    ticker_url = "https://forex-api.coin.z.com/public/v1/ticker"

    try:
        # APIリクエスト
        response = requests.get(f"{ticker_url}")
        data = response.json()

        # データを抽出
        for list in data.items():
            if list[0] == "data":
                for item in list[1]:
                    if item['symbol'] == PAIR:
                        # スプレッドの計算
                        spread = round(float(item['ask']) - float(item['bid']), 3)
                        # スプレッドが許容内か判定する
                        if spread <= SPREAD_LIMIT:
                            return True
    except Exception as e:
        print(f"Error: {e}")
    
    return False

# 価格の取得 Ask
def get_price() -> float:
    # GMOコインの全データを取得するPublic APIのURL
    ticker_url = "https://forex-api.coin.z.com/public/v1/ticker"

    try:
        # APIリクエスト
        response = requests.get(f"{ticker_url}")
        data = response.json()

        # データを抽出
        for list in data.items():
            if list[0] == "data":
                for item in list[1]:
                    if item['symbol'] == PAIR:
                        return round(float(item['ask']), 3)
    except Exception as e:
        print(f"Error: {e}")
    
    return sys.float_info.max

# ロットの最適化処理
def lot_optimize() -> int:
    # 残高の取得
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'GET'
    endPoint  = 'https://forex-api.coin.z.com/private'
    path      = '/v1/account/assets'

    text = timestamp + method + path
    sign = hmac.new(bytes(API_SECRET.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

    headers = {
        "API-KEY": API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.get(endPoint + path, headers=headers)
    amount = int(res.json()['data']['availableAmount'])

    return int(amount * LIVERRAGE / (get_price() * DEFAULT_LOT_SIZE)) * DEFAULT_LOT_SIZE

def position_count(trade_action):
    return 0

# ポジションオープン
# 戻り値：注文ID(orderId)
def position_entry(trade_action) -> int:
    global LotSize
    # ロットの計算
    if LOT_OPTIMIZE:
        LotSize = lot_optimize()
    if LotSize > MAX_LOT_SIZE:
        LotSize = MAX_LOT_SIZE

    # エントリ
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'POST'
    endPoint  = 'https://forex-api.coin.z.com/private'
    path      = '/v1/order'
    reqBody = {
        "symbol": PAIR,
        "side": trade_action,
        "size": str(LotSize),
        "clientOrderId": EA_NAME,
        "executionType": "MARKET"
    }

    text = timestamp + method + path + json.dumps(reqBody)
    sign = hmac.new(bytes(API_SECRET.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

    headers = {
        "API-KEY": API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.post(endPoint + path, headers=headers, data=json.dumps(reqBody))
    print (json.dumps(res.json(), indent=2))

    order_id = res.json()['data'][0]['orderId']
    return order_id

# ポジションクローズ
def position_close(trade_action):
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'POST'
    endPoint  = 'https://forex-api.coin.z.com/private'
    path      = '/v1/closeOrder'
    reqBody = {
        "symbol": PAIR,
        "side": trade_action,
        "clientOrderId": EA_NAME,
        "executionType": "MARKET",
        "settlePosition": [
        {
            "positionId": PositionId,
            "size": str(LotSize)
        }
        ]
    }

    text = timestamp + method + path + json.dumps(reqBody)
    sign = hmac.new(bytes(API_SECRET.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

    headers = {
        "API-KEY": API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.post(endPoint + path, headers=headers, data=json.dumps(reqBody))
    print (json.dumps(res.json(), indent=2))

# OrderIdからpositionIdを取得する
# 戻り値：positionId
def get_position_id() -> int:
    timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
    method    = 'GET'
    endPoint  = 'https://forex-api.coin.z.com/private'
    path      = '/v1/executions'

    text = timestamp + method + path
    sign = hmac.new(bytes(API_SECRET.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
    parameters = {
        "orderId": OrderId
    }

    headers = {
        "API-KEY": API_KEY,
        "API-TIMESTAMP": timestamp,
        "API-SIGN": sign
    }

    res = requests.get(endPoint + path, headers=headers, params=parameters)
    print (json.dumps(res.json(), indent=2))

    position_id = res.json()['data']['list'][0]['positionId']
    return position_id

def is_nenmatu_nensi():
    # Placeholder: Check if it's end-of-year period when trading should be avoided
    return False

# 買いの判定
def is_buy() -> bool:
    if is_gotobi() and is_buy_time() and is_weekday():
        return True
    
    if input_friday_on == True:
        if is_friday() and is_buy_time() and is_weekday():
            return True
    
    return False

# 売りの判定
def is_sell() -> bool:
    if is_gotobi() and is_sell_time() and is_weekday():
        return True
    
    if input_friday_on == True:
        if is_friday() and is_sell_time() and is_weekday():
            return True
    
    return False

# 5-10日の判定
def is_gotobi() -> bool:
    pc_time = datetime.datetime.now()
    day = current_time.day()
    amari = day % 5
    if amari == 0:
        return True
    
    youbi = pc_time.strftime('%A')

    # 週末が5-10日の場合、金曜日を5-10日とする
    if youbi == 'Fraiday' and amari == 3:
        return True
    if youbi == 'Fraiday' and amari == 4:
        return True
    
    return False

# 4:25～9:54だとtrueを返す
# デフォルトでは5-10が木曜日の場合、falseを返す
def is_buy_time() -> bool:
    pc_time = datetime.datetime.now()
    hour = pc_time.hour
    minute = pc_time.minute

    if pc_time.strftime('%A') == 'Thursday':
        return False
    
    if hour == 4 and minute > 24:
        return True
    
    for i in range(5, 9):
        if i == hour:
            return True
        
    if i == 9 and minute <= 54:
        return True
    
    return False

# 9:55～10:25だとtrueを返す
def is_sell_time() -> bool:
    pc_time = datetime.datetime.now()
    hour = pc_time.hour
    minute = pc_time.minute

    if hour == 10 and minute <= 25:
        return True
    
    if hour == 9 and minute >= 55:
        return True

    return False

# 月曜から金曜だとTrueを返す
def is_weekday() -> bool:
    pc_time = datetime.datetime.now()
    youbi = pc_time.strftime('%A')

    if youbi == 'Monday':
        return True
    if youbi == 'Tuesday':
        return True
    if youbi == 'Wednesday':
        return True
    if youbi == 'Thursday':
        return True
    if youbi == 'Friday':
        return True
    return False

# 金曜日の判定
def is_friday() -> bool:
    pc_time = datetime.datetime.now()
    youbi = pc_time.strftime('%A')
    if youbi == 'Fraiday':
        return True

    return False

# テスト用のコード
# OrderId = position_entry("SELL")
OrderId = 12078666
position_id = get_position_id()
# position_close("BUY")

# メインの処理　1秒毎に売買の判定処理を行う
while True:
    current_time = datetime.datetime.now()

    # 23時に売買フラグをTrueに戻す
    if current_time.hour == 23:
        buy_entry_on = True
        sell_entry_on = True

    # 買いの判定
    if is_buy() and is_spread_ok() and position_count("BUY") < 1 and buy_entry_on and not is_nenmatu_nensi():
        position_entry("BUY")

    # 売りの判定
    if input_sell_on:
        if is_sell() and is_spread_ok() and position_count("SELL") < 1 and sell_entry_on and not is_nenmatu_nensi():
            position_entry("SELL")

    # Closing positions if conditions are no longer met
    if not is_buy() and is_spread_ok() and position_count("BUY") > 0:
        position_close("BUY")

    if not is_sell() and is_spread_ok() and position_count("SELL") > 0:
        position_close("SELL")

    # Update entry flags based on current position counts
    if position_count("BUY") > 0:
        buy_entry_on = False
    if position_count("SELL") > 0:
        sell_entry_on = False

    time.sleep(1)
