# -*- coding: utf-8 -*-
# buildResults.py
# mbrace公式競走成績配布(LZH)から当日の全24場・全レースの
# 着順(3連単組番=1-2-3着艇番)と3連単配当を抽出し results/YYYYMMDD.json に出力。
# 見立て検証(verifyPredictions.py)の結果側データ。
# 本番: 環境変数なしで当日分をmbraceからDL。
# 検証: 環境変数 LOCAL_LZH にローカルlzhパス, HD に日付(YYYYMMDD)を指定するとDLせず解凍のみ。
import io
import os
import re
import json
import time
import datetime
import urllib.request

BASE = "http://www1.mbrace.or.jp/od2/K/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) boatrace-data-collector"

SEI = "\uff3b\u6210\u7e3e\uff3d"   # ［成績］
PAY = "\u6255\u623b\u91d1"         # 払戻金
PAYLINE = re.compile(r"\s*(\d{1,2})R\s+(\d)-(\d)-(\d)\s+(\d+)")

# 正規化場名 -> jcd(公式2桁)
JCD = {
    "桐生": "01", "戸田": "02", "江戸川": "03", "平和島": "04", "多摩川": "05",
    "浜名湖": "06", "蒲郡": "07", "常滑": "08", "津": "09", "三国": "10",
    "びわこ": "11", "住之江": "12", "尼崎": "13", "鳴門": "14", "丸亀": "15",
    "児島": "16", "宮島": "17", "徳山": "18", "下関": "19", "若松": "20",
    "芦屋": "21", "福岡": "22", "唐津": "23", "大村": "24",
}


def norm(s):
    return s.replace("\u3000", "").replace(" ", "").strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.read()
    except Exception:
        return None


def extract_all(txt):
    """全場ぶんの {jcd: {rno: {combo, payout, name}}} を返す"""
    res = {}
    cur = None
    inpay = False
    for ln in txt.split("\n"):
        if SEI in ln:
            nm = norm(ln.split(SEI)[0])
            cur = JCD.get(nm)
            inpay = False
            continue
        if cur is None:
            continue
        if PAY in ln:
            inpay = True
            continue
        if inpay:
            m = PAYLINE.match(ln)
            if m:
                rno = int(m.group(1))
                combo = m.group(2) + "-" + m.group(3) + "-" + m.group(4)
                res.setdefault(cur, {})[rno] = {
                    "combo": combo, "payout": int(m.group(5)),
                }
            elif res.get(cur) and not re.search(r"\d", ln):
                inpay = False
    return res


def load_text():
    local = os.environ.get("LOCAL_LZH", "").strip()
    if local:
        import lhafile
        a = lhafile.Lhafile(local)
        name = a.infolist()[0].filename
        hd = os.environ.get("HD", datetime.date.today().strftime("%Y%m%d"))
        return a.read(name).decode("shift_jis", "ignore"), hd
    # 本番: 当日(JST)分をDL
    today = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    d = today.date()
    hd = d.strftime("%Y%m%d")
    url = "{0}{1}/k{2}.lzh".format(BASE, d.strftime("%Y%m"), d.strftime("%y%m%d"))
    raw = fetch(url)
    time.sleep(1.0)
    if not raw or len(raw) < 100:
        return None, hd
    import lhafile
    tmp = "/tmp/k%s.lzh" % d.strftime("%y%m%d")
    open(tmp, "wb").write(raw)
    a = lhafile.Lhafile(tmp)
    name = a.infolist()[0].filename
    return a.read(name).decode("shift_jis", "ignore"), hd


def main():
    txt, hd = load_text()
    if not txt:
        print("no data for", hd)
        return
    res = extract_all(txt)
    races = []
    for jcd in sorted(res):
        for rno in sorted(res[jcd]):
            r = res[jcd][rno]
            top3 = r["combo"].split("-")
            races.append({
                "場コード": jcd,
                "レース": "%dR" % rno,
                "着順": r["combo"],
                "1着": int(top3[0]), "2着": int(top3[1]), "3着": int(top3[2]),
                "三連単配当": r["payout"],
            })
    os.makedirs("results", exist_ok=True)
    outpath = os.path.join("results", "%s.json" % hd)
    obj = {"開催日": hd, "取得時刻": datetime.datetime.now().isoformat(timespec="seconds"),
           "レース数": len(races), "結果": races}
    with io.open(outpath, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    print("wrote", outpath, "races", len(races), "venues", len(res))


if __name__ == "__main__":
    main()
