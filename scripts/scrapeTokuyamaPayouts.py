# -*- coding: utf-8 -*-
# 徳山(jcd=18) 3連単払戻 収集スクレイパー（公式競走成績配布版）
# mbrace.or.jp の競走成績配布(LZH)を1日1ファイル取得・解凍し、徳山の払戻金を抽出。
# スクレイピング不要。1日1ファイルなので安定。徳山非開催日は自動スキップ。
# 環境変数 YM 指定でその月のみ、DAYS 指定で遡る日数を変更可。
import io
import os
import re
import csv
import glob
import time
import datetime
import tempfile
import subprocess
import urllib.request

# https直叩き（http://は301でhttpsへ飛ぶ。urllibはリダイレクト追従するがhttps固定で往復を省く）
BASE = "https://www1.mbrace.or.jp/od2/K/"
OUT = os.path.join("docs", "payouts", "tokuyamaPayouts.csv")
SLEEP = 1.0  # サーバ負荷軽減（高速版）
DAYS_BACK = 365

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) boatrace-data-collector"

# LZH解凍はWindows同梱bsdtar(libarchive)を使う。lhafileはPython3.14でC拡張ビルド不可のため。
BSDTAR = os.environ.get(
    "BSDTAR",
    os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "tar.exe"),
)

TOKU = "\u5fb3\u3000\u5c71\uff3b\u6210\u7e3e\uff3d"   # 徳　山［成績］
SEISEKI = "\uff3b\u6210\u7e3e\uff3d"                  # ［成績］
PAY = "\u6255\u623b\u91d1"                            # 払戻金
PAYLINE = re.compile(r"\s*(\d{1,2})R\s+(\d)-(\d)-(\d)\s+(\d+)")


def fetch(url):
    # urllibは301/302を自動追従する。mbraceは応答が遅め(~20s)なのでtimeoutを長めに。
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.read()
    except Exception:
        return None


def unlzh(raw):
    """LZHバイト列をbsdtarで解凍し、内側テキスト(K*.TXT)のバイト列を返す。失敗時None。"""
    with tempfile.TemporaryDirectory() as td:
        lzh = os.path.join(td, "k.lzh")
        with open(lzh, "wb") as f:
            f.write(raw)
        try:
            subprocess.run(
                [BSDTAR, "-xf", lzh, "-C", td],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return None
        txts = glob.glob(os.path.join(td, "*.TXT")) + glob.glob(os.path.join(td, "*.txt"))
        if not txts:
            return None
        with open(txts[0], "rb") as f:
            return f.read()


def extract_tokuyama(txt):
    """SJISデコード済みテキストから徳山の (rno, combo, payout) を返す"""
    out = []
    in_toku = False
    in_pay = False
    for ln in txt.split("\n"):
        if SEISEKI in ln:
            in_toku = TOKU in ln
            in_pay = False
            continue
        if not in_toku:
            continue
        if PAY in ln:
            in_pay = True
            continue
        if in_pay:
            m = PAYLINE.match(ln)
            if m:
                rno = int(m.group(1))
                combo = m.group(2) + "-" + m.group(3) + "-" + m.group(4)
                payout = int(m.group(5))
                out.append((rno, combo, payout))
            elif out and not re.search(r"\d", ln):
                in_pay = False
    return out


def load_done():
    done = set()
    if os.path.exists(OUT):
        with io.open(OUT, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    done.add((row[0], row[1]))
    return done


def last_collected_date():
    """CSVに記録済みの最終開催日(datetime.date)。無ければNone。"""
    if not os.path.exists(OUT):
        return None
    last = None
    with io.open(OUT, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if not row:
                continue
            hd = row[0]
            if len(hd) == 8 and hd.isdigit():
                if last is None or hd > last:
                    last = hd
    if last is None:
        return None
    return datetime.date(int(last[0:4]), int(last[4:6]), int(last[6:8]))


def date_list():
    today = datetime.date.today()
    ym = os.environ.get("YM", "").strip()
    if ym:
        y, m = int(ym[0:4]), int(ym[4:6])
        d = datetime.date(y, m, 1)
        out = []
        while d.month == m and d <= today:
            out.append(d)
            d += datetime.timedelta(days=1)
        return out

    # daily差分: 前回取得日の翌日 〜 昨日（全期間の再取得はしない）
    yesterday = today - datetime.timedelta(days=1)
    last = last_collected_date()
    if last is not None:
        start = last + datetime.timedelta(days=1)
    else:
        start = yesterday - datetime.timedelta(days=int(os.environ.get("DAYS", str(DAYS_BACK))))
    out = []
    d = start
    while d <= yesterday:
        out.append(d)
        d += datetime.timedelta(days=1)
    return out


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    done = load_done()
    new_file = not os.path.exists(OUT)
    out = io.open(OUT, "a", encoding="utf-8", newline="")
    writer = csv.writer(out)
    if new_file:
        writer.writerow(["hd", "rno", "combo", "payout"])

    collected = 0
    days_with_data = 0
    for d in date_list():
        hd = d.strftime("%Y%m%d")
        # この日が既に全レース取得済みならスキップ
        if (hd, "1") in done and (hd, "12") in done:
            continue
        yyyymm = d.strftime("%Y%m")
        yymmdd = d.strftime("%y%m%d")
        url = "{0}{1}/k{2}.lzh".format(BASE, yyyymm, yymmdd)
        raw = fetch(url)
        time.sleep(SLEEP)
        if not raw or len(raw) < 100:
            continue
        # LZH解凍（bsdtar）
        data = unlzh(raw)
        if not data:
            continue
        txt = data.decode("shift_jis", "ignore")
        rows = extract_tokuyama(txt)
        if rows:
            days_with_data += 1
        for rno, combo, payout in rows:
            if (hd, str(rno)) in done:
                continue
            writer.writerow([hd, rno, combo, payout])
            out.flush()
            collected += 1

    out.close()
    print("collected:", collected, "days_with_tokuyama:", days_with_data)


if __name__ == "__main__":
    main()
