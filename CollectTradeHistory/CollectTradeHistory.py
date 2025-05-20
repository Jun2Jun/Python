from influxdb_client import InfluxDBClient, Point, WritePrecision
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib3.exceptions import NewConnectionError  # 必要な例外をインポート

import os
import re
import json
import time
import sys
from datetime import datetime

# InfluxDBから最新のタイムスタンプを取得する関数
def get_latest_timestamp(measurement: str) -> str:
    # urlとtokenを設定ファイルから読み込み
    # 設定ファイル名
    config_file = "setting.json"
    # スクリプトのディレクトリを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 設定ファイルのパスを生成
    config_path = os.path.join(script_dir, config_file)
    with open(config_path, "r") as f:
        config = json.load(f)
        influxdb_url = config["InfluxDB"]["url"]
        influxdb_token = config["InfluxDB"]["token"]
        retleave_default_from = config["InfluxDB"]["retleave_default_from"]

    # InfluxDBの接続情報
    org = "organization"               # DOCKER_INFLUXDB_INIT_ORG と同じ
    bucket = "bucket"                  # DOCKER_INFLUXDB_INIT_BUCKET と同じ

    # InfluxDBに接続する
    client = InfluxDBClient(url=influxdb_url, token=influxdb_token, org=org)
    # クエリAPIを使用してInfluxDBにクエリを実行する
    query_api = client.query_api()

    # 過去30日間のデータを取得し、指定した measurement でフィルタリング
    # _time でソートして最新1件のみ取得するFluxクエリを作成
    query = f'from(bucket: "{bucket}") |> range(start: -30d) |> filter(fn: (r) => r._measurement == "{measurement}") |> sort(columns: ["_time"], desc: true) |> limit(n: 1)'

    # 最新のタイムスタンプを取得
    try:
        result = client.query_api().query(query)
    except NewConnectionError as e:
        print("InfluxDBへの接続に失敗しました:", e)
        return retleave_default_from

    if result:
        # タイムスタンプを取得
        latest_record = result[0].records[0]
        latest_timestamp = latest_record.get_time()

        # タイムスタンプを年月日形式に変換
        return latest_timestamp.strftime('%Y%m%d')
    else:
        return retleave_default_from

# ダウンロード中のファイル名を監視してダウンロード完了を検知する関数
def wait_for_download_to_complete(download_directory):
    # 最初のダウンロードを開始した時点でのファイル一覧を取得
    before_files = set(os.listdir(download_directory))
    
    while True:
        time.sleep(1)  # 1秒間隔で確認
        after_files = set(os.listdir(download_directory))  # 現在のファイル一覧
        
        # 新しいファイルが追加され、拡張子が .crdownload の場合はダウンロード中
        new_files = after_files - before_files
        
        # ダウンロード中のファイルが存在しないか、.crdownload が付いていない場合にループ終了
        if not any(file.endswith(".crdownload") for file in new_files):
            print("ダウンロードが完了しました。")
            break  # ダウンロード完了

def load_config(config_file: str) -> dict:
    """設定ファイルを読み込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, config_file)
    with open(config_path, "r") as f:
        return json.load(f)


def setup_webdriver(download_directory: str) -> webdriver.Chrome:
    """WebDriverを初期化する"""
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_directory,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })
    # chrome_options.add_argument("--headless")  # 必要に応じてヘッドレスモードを有効化
    service = Service("chromedriver.exe")
    return webdriver.Chrome(service=service, options=chrome_options)


def login_to_gmo(driver: webdriver.Chrome, user_id: str, password: str):
    """GMOのマイページにログインする"""
    driver.get("https://sec-sso.click-sec.com/loginweb/")
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "j_username")))
        driver.find_element(By.ID, "j_username").send_keys(user_id)
        driver.find_element(By.ID, "j_password").send_keys(password)
        driver.find_element(By.NAME, "LoginForm").click()
        print("ログインに成功しました")
    except Exception as e:
        print("ログインに失敗しました:", e)
        driver.quit()
        sys.exit()


def navigate_to_trade_history(driver: webdriver.Chrome):
    """精算表ページに移動する"""
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.LINK_TEXT, "精算表")))
        driver.find_element(By.LINK_TEXT, "精算表").click()
        print("精算表ページに移動しました")
    except Exception as e:
        print("精算表ページへの移動に失敗しました:", e)
        driver.quit()
        sys.exit()


def set_trade_filters(driver: webdriver.Chrome, latest_timestamp: str):
    """取引のフィルタを設定する"""
    try:
        driver.find_element(By.ID, "torihikiKbnList_3_1").click()  # 取引のチェックボックス
        driver.find_element(By.ID, "torihikiKbnList_3_2").click()  # スワップのチェックボックス
        reference_date_from = driver.find_element(By.ID, "referenceDate_from")
        reference_date_to = driver.find_element(By.ID, "referenceDate_to")
        reference_date_from.clear()
        reference_date_from.send_keys(latest_timestamp)
        reference_date_to.clear()
        reference_date_to.send_keys(datetime.now().strftime('%Y%m%d'))
        print("取引フィルタを設定しました")
    except Exception as e:
        print("取引フィルタの設定に失敗しました:", e)
        driver.quit()
        sys.exit()


def search_and_download(driver: webdriver.Chrome, download_directory: str):
    """検索を実行し、結果をダウンロードする"""
    try:
        driver.find_element(By.ID, "searchButton").click()
        print("検索を実行しました")
        time.sleep(5)  # 検索完了を待つ
        tr_element = driver.find_element(By.XPATH, '/html/body/div[2]/form/div[2]/div[2]/table/tbody/tr[2]')
        button = tr_element.find_element(By.ID, 'linkTradingSearchResultDownload')
        button.click()
        print("ダウンロードボタンをクリックしました")
        wait_for_download_to_complete(download_directory)
    except NoSuchElementException as e:
        print("検索結果が見つかりませんでした:", e)
        driver.quit()
        sys.exit()


def validate_download(download_directory: str, trade_request_key: str):
    """ダウンロードされたファイルを検証する"""
    key_prefix = trade_request_key[:17]
    files_in_directory = os.listdir(download_directory)
    for file_name in files_in_directory:
        if key_prefix in file_name and file_name.endswith(".csv"):
            print(f"{file_name}が見つかりました")
            return
    print(f"{key_prefix}を含む.csvファイルが見つかりませんでした")


def main():
    # 設定ファイルを読み込む
    config = load_config("setting.json")
    user_id = config["GMO"]["userid"]
    password = config["GMO"]["password"]

    # ダウンロードディレクトリを設定
    script_directory = os.path.dirname(os.path.abspath(__file__))
    download_directory = os.path.join(script_directory, "download")
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)

    # WebDriverを初期化
    driver = setup_webdriver(download_directory)

    # 最新のタイムスタンプを取得
    latest_timestamp = get_latest_timestamp("trade_history")

    # GMOにログイン
    login_to_gmo(driver, user_id, password)

    # 精算表ページに移動
    navigate_to_trade_history(driver)

    # 取引フィルタを設定
    set_trade_filters(driver, latest_timestamp)

    # 検索とダウンロードを実行
    search_and_download(driver, download_directory)

    # ダウンロードされたファイルを検証
    trade_request_key = "example_trade_request_key"  # 実際にはボタンのhrefから取得
    validate_download(download_directory, trade_request_key)

    # ブラウザを閉じる
    driver.quit()


if __name__ == "__main__":
    main()
