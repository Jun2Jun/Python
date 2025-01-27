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

# ロットの計算処理
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

# OrderIdをキーにポジションの有無を判定
def have_position(side) -> bool:
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
    # print (json.dumps(res.json(), indent=2))

    # 成功？
    if res.json()['status'] == 0:
        if len(res.json()['data']['list']) > 0:
            if res.json()['data']['list'][0]['positionId'] > 0 and res.json()['data']['list'][0]['side'] == side:
                return True
    return False

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

    # 成功？
    if res.json()['status'] == 0:
        return res.json()['data'][0]['orderId']
    else:
        return -1

# ポジションクローズ
def position_close(trade_action) -> bool:
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

    # 成功？
    if res.json()['status'] == 0:
        return True
    else:
        return False

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

    # 成功？
    if res.json()['status'] == 0:
        return res.json()['data']['list'][0]['positionId']
    else:
        return 0

def is_nenmatu_nensi() -> bool:
    pc_time = datetime.now()
    
    nenmatu = pc_time.month == 12 and pc_time.day >= 25
    nensi = pc_time.month == 1 and pc_time.day <= 6

    return nenmatu or nensi

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
    # テスト用に全てTrueを返す
    return True

    pc_time = datetime.now()
    amari = pc_time.day % 5
    if amari == 0:
        return True

    # 週末が5-10日の場合、金曜日(weekdayが4)を5-10日とする
    if pc_time.weekday() == 4 and amari in (3, 4):
        return True
    return False

# 4:25～9:54だとtrueを返す
# デフォルトでは5-10日が木曜日の場合、falseを返す
def is_buy_time() -> bool:
    pc_time = datetime.now()
    hour = pc_time.hour
    minute = pc_time.minute

    # 木曜日ならfalse
    if pc_time.weekday() == 3:
        return False

    # 4:25～9:54ならTrue    
    if (hour == 4 and minute > 24) or (5 <= hour <= 8) or (hour == 9 and minute <= 54):
        return True

    return False

# 9:55～10:25だとtrueを返す
def is_sell_time() -> bool:
    pc_time = datetime.now()
    hour = pc_time.hour
    minute = pc_time.minute

    # 9:55-10:25ならTrue
    if (hour == 10 and minute <= 25) or (hour == 9 and minute >= 55):
        return True

    return False

# 月曜から金曜(weekdayが0～4)だとTrueを返す
def is_weekday() -> bool:
    pc_time = datetime.now()
    weekday = pc_time.weekday()
    return weekday < 5

# 金曜日(weekdayが4)の判定
def is_friday() -> bool:
    pc_time = datetime.now()
    return pc_time.weekday() == 4

# テスト用のコード
nenmatu = is_nenmatu_nensi()
# OrderId = position_entry("SELL")
#OrderId = 12093313
#have_position()
# PositionId = get_position_id()
# position_close("BUY")


# メインの処理　1秒毎に売買の判定処理を行う
while True:
    current_time = datetime.now()

    # 23時に売買フラグをTrueに戻す
    if current_time.hour == 23:
        buy_entry_on = True
        sell_entry_on = True

    # ポジションエントリの判定
    if is_buy() and is_spread_ok() and not have_position("BUY") and buy_entry_on and not is_nenmatu_nensi():
        # 買いのエントリを行う
        # OrderId = position_entry("BUY")
        current_time.strftime("%Y-%m-%d %H:%M:%S")
        print(current_time.strftime("%Y-%m-%d %H:%M:%S") + " BUY Entry")

    if input_sell_on:
        if is_sell() and is_spread_ok() and not have_position("SELL") and sell_entry_on and not is_nenmatu_nensi():
            # 売りのエントリを行う
            # OrderId = position_entry("SELL")
            print(current_time.strftime("%Y-%m-%d %H:%M:%S") + " SELL Entry")


    # ポジションクローズの判定
    if not is_buy() and is_spread_ok() and have_position("BUY"):
        position_close("BUY")

    if not is_sell() and is_spread_ok() and have_position("SELL"):
        position_close("SELL")

    # ポジションを確認して、buy_entory_on、sell_entory_onを更新する
    if have_position("BUY"):
        buy_entry_on = False
    if have_position("SELL"):
        sell_entry_on = False

    time.sleep(1)
