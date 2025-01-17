import requests

# 5-10日のトレード
from enum import Enum
import datetime
import time

# Constants for trade settings
MAGIC_NUMBER = 1115111
SLIPPAGE = 10
SPREAD_LIMIT = 0.003
LOT_SIZE = 0.1
HUKURI_ON = True

# 各種フラグ
buy_entry_on = True
sell_entry_on = True
input_sell_on = True
input_friday_on = True

# 売買の列挙型を定義
class TradeAction(Enum):
    BUY = 0
    SELL = 1

# Time Calculation Enum Equivalent in Python
class UseTimes:
    GMT9 = 0
    GMT9_BACKTEST = 1
    GMT_KOTEI = 2

set_time = UseTimes.GMT9
natu = 6  # Summer time
huyu = 7  # Winter time

# Time calculation function
def calculate_time(current_time):
    if set_time == UseTimes.GMT9:
        return current_time + datetime.timedelta(hours=9)
    elif set_time == UseTimes.GMT9_BACKTEST:
        return current_time  # In a backtest scenario, actual time adjustments may be different
    elif set_time == UseTimes.GMT_KOTEI:
        return current_time + datetime.timedelta(hours=9)
    return current_time

# スプレッドの判定
def is_spread_ok() -> bool:
    # GMOコインの全データを取得するPublic APIのURL
    ticker_url = "https://forex-api.coin.z.com/public/v1/ticker"

    # 取得する通貨ペア
    pair = "USD_JPY"

    try:
        # APIリクエスト
        response = requests.get(f"{ticker_url}")
        data = response.json()

        # データを抽出
        for list in data.items():
            if list[0] == "data":
                for item in list[1]:
                    if item['symbol'] == pair:
                        # スプレッドの計算
                        spread = round(float(item['ask']) - float(item['bid']), 3)
                        # スプレッドが許容内か判定する
                        if spread <= SPREAD_LIMIT:
                            return True
    except Exception as e:
        print(f"Error: {e}")
    
    return False

def position_count(trade_action):
    return 0

def position_entry(trade_action):
    if trade_action == TradeAction.BUY:
        print("Buying position opened")
    else:
        print("Selling position opened")

def position_close(trade_action):
    if trade_action == TradeAction.BUY:
        print("Buying position closed")
    else:
        print("Selling position closed")

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

# メインの処理　1秒毎に売買の判定処理を行う
while True:
    current_time = datetime.datetime.now()

    # 23時に売買フラグをTrueに戻す
    if current_time.hour == 23:
        buy_entry_on = True
        sell_entry_on = True

    # 買いの判定
    if is_buy() and is_spread_ok() and position_count(TradeAction.BUY) < 1 and buy_entry_on and not is_nenmatu_nensi():
        position_entry(TradeAction.BUY)

    # 売りの判定
    if input_sell_on:
        if is_sell() and is_spread_ok() and position_count(TradeAction.SELL) < 1 and sell_entry_on and not is_nenmatu_nensi():
            position_entry(TradeAction.SELL)

    # Closing positions if conditions are no longer met
    if not is_buy() and is_spread_ok() and position_count(TradeAction.BUY) > 0:
        position_close(TradeAction.BUY)

    if not is_sell() and is_spread_ok() and position_count(TradeAction.SELL) > 0:
        position_close(TradeAction.SELL)

    # Update entry flags based on current position counts
    if position_count(TradeAction.BUY) > 0:
        buy_entry_on = False
    if position_count(TradeAction.SELL) > 0:
        sell_entry_on = False

    time.sleep(1)
