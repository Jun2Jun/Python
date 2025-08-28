#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dukascopy 1分足 CSV → （MT4サーバー時間へ変換）→ ForexTester6 インポート形式へ変換

Dukascopyからヒストリカルデータをダウンロードするときの設定：
- 売買サイド：BID
- 1日の開始時間：EET
- 取引量の表示単位：any（どれを選択しても良いが、小数点以下があるとFT6がフリーズするのでスクリプト内で小数点以下は処理する）
- フラット期間：全フラット期間
- 現地時間/GMT：現地時間（現在の処理はGMT+9を想定しているので現地時間にしておく）

入力フォーマット（例）:
Local time,Open,High,Low,Close,Volume
16.08.2025 00:00:00.000 GMT+0900,146.851,146.878,146.851,146.876,192000000
...

出力フォーマット（FT6）:
Date,Time,Open,High,Low,Close,Volume
2025.08.15,17:00,146.851,146.878,146.851,146.876,192000000
...

機能:
- 入力日時文字列 "dd.MM.yyyy HH:mm:ss.SSS GMT±ZZZZ" を厳密パース
- 指定の MT4 サーバータイムゾーンに変換（DST 自動対応）
- Volume == 0 の行を削除（既定。オプションで保持も可）
- 出力は ForexTester6 形式（Date, Time, OHLC, Volume）
- 日付/時刻フォーマットはオプションで変更可

使い方:
python convert_dukascopy_to_forextester6.py input.csv output.csv \
  --mt4-tz "Europe/Athens" \
  --date-format "%Y.%m.%d" \
  --time-format "%H:%M"

※ --mt4-tz（既定: "Europe/Athens"）は IANA タイムゾーン名を指定（例："Europe/Berlin", "Europe/London" など）
※ 固定オフセットを使う場合は --mt4-fixed-offset "+02:00"（--mt4-tz と同時指定不可）
"""

import argparse
import sys
from datetime import timedelta, timezone
import re

import pandas as pd

try:
    # Python 3.9+: 標準のタイムゾーンDB
    from zoneinfo import ZoneInfo
    _HAS_ZONEINFO = True
except Exception:
    _HAS_ZONEINFO = False


def parse_fixed_offset(s: str) -> timezone:
    """
    "+02:00" / "-03:30" のような文字列を datetime.timezone に変換
    """
    m = re.fullmatch(r'([+-])(\d{1,2}):(\d{2})', s.strip())
    if not m:
        raise ValueError("固定オフセットは +HH:MM / -HH:MM 形式で指定してください（例: +02:00）")
    sign = 1 if m.group(1) == '+' else -1
    hh = int(m.group(2))
    mm = int(m.group(3))
    if hh > 23 or mm > 59:
        raise ValueError("オフセットの範囲が不正です")
    delta = timedelta(hours=sign*hh, minutes=sign*mm)
    return timezone(delta)


def parse_args():
    """
    コマンドライン引数を定義・解析する。

    Returns:
        argparse.Namespace: フォーマット指定、MT4時間設定、ゼロボリューム保持設定を含むパラメータ
                           （入力・出力ファイルは実行時に自動設定）
    """
    p = argparse.ArgumentParser(
        description="Convert Dukascopy 1-min CSV to ForexTester6 CSV with MT4 time conversion."
    )

    # 出力の日時フォーマット
    p.add_argument("--date-format", default="%Y.%m.%d",
                   help='出力のDateフォーマット（既定: "%%Y.%%m.%%d"）')
    p.add_argument("--time-format", default="%H:%M",
                   help='出力のTimeフォーマット（既定: "%%H:%%M"）')

    # MT4サーバー時間指定（タイムゾーン or 固定オフセット）
    p.add_argument("--mt4-tz", default="Europe/Athens",
                   help='MT4サーバーのタイムゾーン（既定: "Europe/Athens"、DST自動対応）')
    p.add_argument("--mt4-fixed-offset", default=None,
                   help='MT4サーバーの固定オフセット "+HH:MM" / "-HH:MM"（--mt4-tz と同時指定不可）')

    return p.parse_args()


def main():
    """
    Dukascopyの1分足CSVを読み込み、MT4サーバー時間に変換した上で
    ForexTester6にインポート可能なCSV形式に変換・保存するメイン処理。

    処理の流れ:
    1. コマンドライン引数の解析
    2. 入力CSVの読み込みとフォーマット検証
    3. Local time列の日時をパースし、指定されたMT4タイムゾーン/オフセットに変換
    4. Volume==0の行を除外（オプション指定時は保持）
    5. 出力フォーマット（日付・時刻書式含む）に整形
    6. BOM付きUTF-8でCSV書き出し
    7. 実行結果を標準出力に表示

    Exit Codes:
        0: 正常終了
        1: エラー終了（入力不備・変換失敗など）
    """
    args = parse_args()

    if args.mt4_fixed_offset and args.mt4_tz:
        # 同時指定は不可にする（固定オフセット優先にしたい場合は --mt4-tz を空に）
        print("エラー: --mt4-tz と --mt4-fixed-offset は同時に指定できません。", file=sys.stderr)
        sys.exit(1)
    
     # 実行時にユーザーへ入力ファイル名を求める
    input_file = input("入力CSVファイル名を入力してください: ").strip()
    if not input_file:
        print("エラー: 入力ファイル名が指定されていません。", file=sys.stderr)
        sys.exit(1)

    # 出力ファイル名を自動設定
    output_file = "output_" + input_file

    # 入力読み込み
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"入力CSVの読み込みに失敗: {e}", file=sys.stderr)
        sys.exit(1)

    required_cols = ["Local time", "Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"必要な列が不足しています: {missing}", file=sys.stderr)
        sys.exit(1)

    # 入力の日時を厳密にパース（例: "16.08.2025 00:00:00.000 GMT+0900"）
    try:
        dt_src = pd.to_datetime(
            df["Local time"].astype(str),
            format="%d.%m.%Y %H:%M:%S.%f GMT%z",
            errors="raise",
        )
    except Exception as e:
        print(f"日時のパースに失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # 変換先タイムゾーンを決定
    target_tz = None
    if args.mt4_fixed_offset:
        try:
            target_tz = parse_fixed_offset(args.mt4_fixed_offset)
        except Exception as e:
            print(f"固定オフセットの解釈に失敗: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        if not _HAS_ZONEINFO:
            print("エラー: この環境では zoneinfo が利用できません。--mt4-fixed-offset をお使いください。", file=sys.stderr)
            sys.exit(1)
        try:
            target_tz = ZoneInfo(args.mt4_tz)
        except Exception as e:
            print(f"タイムゾーン '{args.mt4_tz}' の解決に失敗: {e}", file=sys.stderr)
            sys.exit(1)

    # タイムゾーン変換（入力は tz-aware → 目的の tz へ）
    try:
        dt_mt4 = dt_src.dt.tz_convert(target_tz)
    except Exception as e:
        print(f"タイムゾーン変換に失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # 出力用（タイムゾーン情報を落として文字列化）
    dt_naive = dt_mt4.dt.tz_localize(None)

    # 出力DF生成。Volumeは小数点以下を切り捨て。
    try:
        df_out = pd.DataFrame({
            "Date": dt_naive.dt.strftime(args.date_format),
            "Time": dt_naive.dt.strftime(args.time_format),
            "Open": pd.to_numeric(df["Open"], errors="coerce"),
            "High": pd.to_numeric(df["High"], errors="coerce"),
            "Low":  pd.to_numeric(df["Low"], errors="coerce"),
            "Close": pd.to_numeric(df["Close"], errors="coerce"),
            "Volume": pd.to_numeric(df["Volume"], errors="coerce").fillna(0).astype(int)
        })
    except Exception as e:
        print(f"出力データの整形に失敗: {e}", file=sys.stderr)
        sys.exit(1)

    # 列順を保険で固定
    df_out = df_out[["Date", "Time", "Open", "High", "Low", "Close", "Volume"]]

    # 書き出し（Excel互換の BOM 付き UTF-8）
    try:
        df_out.to_csv(output_file, index=False, encoding="utf-8-sig")
    except Exception as e:
        print(f"出力CSVの書き込みに失敗: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"変換完了: {output_file}（行数: {len(df_out)}）")
    if args.mt4_fixed_offset:
        print(f"MT4時間: 固定オフセット {args.mt4_fixed_offset} を適用")
    else:
        print(f"MT4時間: タイムゾーン '{args.mt4_tz}' を適用（DST自動）")


if __name__ == "__main__":
    main()
