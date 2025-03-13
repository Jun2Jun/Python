from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
import os
import json
import time
import sys

# ChromeDriverのパスを指定（ChromeDriverのインストールが必要です）
chrome_driver_path = "chromedriver.exe"

# オプション設定（ヘッドレスモードや他の設定を必要に応じて）
chrome_options = Options()
#chrome_options.add_argument("--headless")  # ヘッドレスモード（ブラウザを表示しない）

# WebDriverの起動
try:
    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
except WebDriverException as e:
    print(f"ChromeDriverの起動に失敗しました: {e}")
    sys.exit()

# GMOのマイページにアクセス
driver.get("https://sec-sso.click-sec.com/loginweb/")

# useridとpasswordの読み込み
# 設定ファイル名
config_file = "setting.json"
# スクリプトのディレクトリを取得
script_dir = os.path.dirname(os.path.abspath(__file__))
# 設定ファイルのパスを生成
config_path = os.path.join(script_dir, config_file)
with open(config_path, "r") as f:
    config = json.load(f)
    USER_ID = config["userid"]
    PASSWORD = config["password"]

# ユーザ名を入力する
try:
    # id属性を使って入力フィールドを探す
    input_field = driver.find_element(By.ID, "j_username")
    
    # ユーザ名を入力する
    input_field.send_keys(USER_ID)
except Exception as e:
    print("ユーザ名の入力に失敗しました:", e)

# パスワードを入力する
try:
    # id属性を使って入力フィールドを探す
    input_field = driver.find_element(By.ID, "j_password")
    
    # パスワードを入力する
    input_field.send_keys(PASSWORD)
except Exception as e:
    print("パスワードの入力に失敗しました:", e)

# ボタンをクリックする
try:
    # name属性を使ってボタンを探す
    button = driver.find_element(By.NAME, "LoginForm")
    
    # ボタンをクリック
    button.click()
    print("ボタンをクリックしました")
except Exception as e:
    print("ボタンのクリックに失敗しました:", e)

# 処理を待つ場合は少しスリープ
time.sleep(3)

# ブラウザを閉じる
driver.quit()
