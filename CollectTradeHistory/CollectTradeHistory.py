from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import re
import json
import time
import sys

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

# ChromeDriverのパスを指定（ChromeDriverのインストールが必要です）
chrome_driver_path = "chromedriver.exe"

# スクリプトの場所（.pyファイルが存在するディレクトリ）を起点にする
script_directory = os.path.dirname(os.path.abspath(__file__))

# スクリプトのディレクトリにあるdownloadフォルダを指定
download_directory = os.path.join(script_directory, "download")

# ダウンロードフォルダが存在しない場合は作成
if not os.path.exists(download_directory):
    os.makedirs(download_directory)

# オプション設定（ヘッドレスモードや他の設定を必要に応じて）
chrome_options = Options()
chrome_options.add_experimental_option("prefs", {
  "download.default_directory": download_directory,  # ダウンロードの保存先を指定
  "download.prompt_for_download": False,  # ダウンロード時にダイアログを表示しない
  "download.directory_upgrade": True,  # 保存先のディレクトリを自動でアップグレード
  "safebrowsing.enabled": True  # セーフブラウジングを有効にする
})
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

# ユーザ名の入力ボックスが表示されるまでWebページの表示を待つ
try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "j_username")))
    print("ページの読み込みが完了しました")
except Exception as e:
    print("ページの読み込みに失敗しました:", e)

# useridとpasswordを設定ファイルから読み込み
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

# ログインボタンをクリックする
try:
    # name属性を使ってボタンを探す
    button = driver.find_element(By.NAME, "LoginForm")
    
    # ログインボタンをクリック
    button.click()
    print("ログインボタンをクリックしました")
except Exception as e:
    print("ログインボタンのクリックに失敗しました:", e)

# 画面の表示を待つ
time.sleep(5)

# 精算表のリンクが表示されるまでWebページの表示を待つ
try:
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.LINK_TEXT, "精算表")))
    print("ページの読み込みが完了しました")
except Exception as e:
    print("ページの読み込みに失敗しました:", e)

# 「精算表」リンクをクリックする
driver.find_element(By.LINK_TEXT, "精算表").click()

# 取引のチェックボックスをクリックする
try:
    # id属性を使って取引のチェックボックスを探す
    checkbox_deal = driver.find_element(By.ID, "torihikiKbnList_3_1")
    # チェックボックスをクリック
    checkbox_deal.click()

    # id属性を使ってスワップのチェックボックスを探す
    checkbox_swap = driver.find_element(By.ID, "torihikiKbnList_3_2")
    # チェックボックスをクリック
    checkbox_swap.click()
except Exception as e:
    print("チェックボックスのクリックに失敗しました:", e)

# 参照する日付の期間を入力する
try:
    # id属性を使って入力フィールドを探す
    reference_date_from = driver.find_element(By.ID, "referenceDate_from")
    reference_date_to = driver.find_element(By.ID, "referenceDate_to")
    
    # 参照する日付の期間を入力する
    reference_date_from.clear()
    reference_date_from.send_keys("20250312")
    reference_date_to.clear()
    reference_date_to.send_keys("20250315")

except Exception as e:
    print("参照する期間の入力に失敗しました:", e)

# 検索ボタンをクリックする
try:
    # name属性を使ってボタンを探す
    button = driver.find_element(By.ID, "searchButton")
    
    # 検索ボタンをクリック
    button.click()
    print("検索ボタンをクリックしました")
except Exception as e:
    print("検索ボタンのクリックに失敗しました:", e)

# 検索完了まで待つ
time.sleep(5)

try:
    # 検索結果の一番上に表示されるtr[2]要素をXPathで取得
    tr_element = driver.find_element(By.XPATH, '/html/body/div[2]/form/div[2]/div[2]/table/tbody/tr[2]')
    
    # tr要素内にid="linkTradingSearchResultDownload"のボタンがあるか確認
    button = tr_element.find_element(By.ID, 'linkTradingSearchResultDownload')
    
    # ボタンが存在すればクリック
    button.click()
    print("ダウンロードボタンをクリックしました。")

    # ダウンロード完了を待機
    wait_for_download_to_complete(download_directory)

    # buttonからhref属性を取得
    href_value = button.get_attribute("href")

    # 正規表現を使ってtradeRequestKeyの値を取得
    trade_request_key = re.search(r'tradeRequestKey=([0-9]+)', href_value).group(1)
    # trade_request_keyの先頭17文字を取得
    key_prefix = trade_request_key[:17]

    # ディレクトリ内のファイル一覧を取得
    files_in_directory = os.listdir(download_directory)
    
    # trade_request_keyを含む.csvファイルが存在するかチェック
    for file_name in files_in_directory:
        if key_prefix in file_name and file_name.endswith(".csv"):
            print(f"{file_name}が見つかりました。")
            break
        else:
            print(f"{key_prefix}を含む.csvファイルが見つかりませんでした。")

except NoSuchElementException as e:
    # ダウンロードボタンが見つからない場合の例外処理
    print("指定されたtr要素が見つからない、または、検索結果がありませんでした。", e)

# ブラウザを閉じる
driver.quit()
