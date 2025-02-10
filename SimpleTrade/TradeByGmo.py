from datetime import datetime
import hashlib
import hmac
import json
import os
import requests
import sys
import time

class TradeByGmo:
    # APIキーとシークレットキーの読み込み
    # 設定ファイル名
    config_file = "setting.json"
    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 設定ファイルのパスを生成
    config_path = os.path.join(script_dir, config_file)
    with open(config_path, "r") as f:
        config = json.load(f)
        API_KEY = config["api_key"]
        SECRET_KEY = config["secret_key"]

    # ペアのリストを定義する
    pair_list = {"UJ": "USD_JPY", "EU": "EUR_USD", "EJ": "EUR_JPY", "GU": "GBP_USD", "GJ": "GBP_JPY", "AU": "AUD_USD", "AJ": "AUD_JPY"}

    # BidとAskの取得
    def get_price(self, pair) -> float:
        # GMOコインの全データを取得するPublic APIのURL
        ticker_url = 'https://forex-api.coin.z.com/public/v1/ticker'

        try:
            # APIリクエスト
            response = requests.get(f"{ticker_url}")
            data = response.json()

            # データを抽出
            for list in data.items():
                if list[0] == "data":
                    for item in list[1]:
                        if item['symbol'] == self.pair_list[pair]:
                            print(f'{item['ask']}')
                            return item['bid'], item['ask']
        except Exception as e:
            print(f'{e}')
        
        return None, None

    # ポジションエントリ
    def entry_position(self, pair, lot, trade_action) -> int:
        try:
            # ペアが存在するか確認
            symbol = self.pair_list[pair]
        except KeyError:
            return -1
        
        # エントリ
        timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
        method    = 'POST'
        endPoint  = 'https://forex-api.coin.z.com/private'
        path      = '/v1/order'
        reqBody = {
            "symbol": symbol,
            "side": trade_action,
            "size": str(lot),
            "executionType": "MARKET"
        }

        text = timestamp + method + path + json.dumps(reqBody)
        sign = hmac.new(bytes(self.SECRET_KEY.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

        headers = {
            "API-KEY": self.API_KEY,
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
    
    # ポジション一覧を取得する
    def get_position(self) -> list:
        timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
        method    = 'GET'
        endPoint  = 'https://forex-api.coin.z.com/private'
        path      = '/v1/openPositions'

        text = timestamp + method + path
        sign = hmac.new(bytes(self.SECRET_KEY.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()
        parameters = {
        }

        headers = {
            "API-KEY": self.API_KEY,
            "API-TIMESTAMP": timestamp,
            "API-SIGN": sign
        }

        res = requests.get(endPoint + path, headers=headers, params=parameters)
        print (json.dumps(res.json(), indent=2))

        # 成功ならポジション一覧を返す
        if res.json()['status'] == 0:
            if res.json()['data']['list']:
                return res.json()['data']['list']
        return None
    
    # ポジションクローズ
    def position_close(self, position_list) -> bool:
        for position in position_list:
            # クローズ処理
            timestamp = '{0}000'.format(int(time.mktime(datetime.now().timetuple())))
            method    = 'POST'
            endPoint  = 'https://forex-api.coin.z.com/private'
            path      = '/v1/closeOrder'
            if position['side'] == 'BUY':
                side = 'SELL'
            elif position['side'] == 'SELL':
                side = 'BUY'

            reqBody = {
                "symbol": position['symbol'],
                "side": side,
                "executionType": "MARKET",
                "settlePosition": [
                {
                    "positionId": position['positionId'],
                    "size": position['size']
                }
                ]
            }

            text = timestamp + method + path + json.dumps(reqBody)
            sign = hmac.new(bytes(self.SECRET_KEY.encode('ascii')), bytes(text.encode('ascii')), hashlib.sha256).hexdigest()

            headers = {
                "API-KEY": self.API_KEY,
                "API-TIMESTAMP": timestamp,
                "API-SIGN": sign
            }

            res = requests.post(endPoint + path, headers=headers, data=json.dumps(reqBody))
            print (json.dumps(res.json(), indent=2))


    