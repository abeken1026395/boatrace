#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
regenPredictions.py
過去日の predictions/YYYYMMDD.json を「結果を読まずに」再生成する。
入力:
  出走表・成績・モーター … BoatraceOpenAPI programs（raw.githubusercontent.com）
  天候                   … Open-Meteo アーカイブAPI（取れない日は天候なしで続行。判定/主役/スコアに天候は不使用）
  決まり手               … docs/players/racerKimarite.csv（現行で代用）
ロジック本体は scripts/build_highlights.py（リポジトリ現行＝混戦新ロジック入り）を
実行時にRERUNパッチ（日付ガード無効化・predictions上書き許可）して呼ぶ。
使い方:
  python scripts/regenPredictions.py 20260606 20260705
"""
import json, csv, sys, os, ssl, datetime, subprocess, tempfile, urllib.request, urllib.parse

START = sys.argv[1] if len(sys.argv) > 1 else "20260606"
END   = sys.argv[2] if len(sys.argv) > 2 else "20260705"

BH_SRC   = "scripts/build_highlights.py"
KIM_CSV  = "docs/players/racerKimarite.csv"
PROG_URL = "https://raw.githubusercontent.com/BoatraceOpenAPI/programs/HEAD/docs/v2/{y}/{ymd}.json"
ARCHIVE  = "https://archive-api.open-meteo.com/v1/archive"

JCD_NAME = {1:"桐生",2:"戸田",3:"江戸川",4:"平和島",5:"多摩川",6:"浜名湖",7:"蒲郡",8:"常滑",
            9:"津",10:"三国",11:"びわこ",12:"住之江",13:"尼崎",14:"鳴門",15:"丸亀",16:"児島",
            17:"宮島",18:"徳山",19:"下関",20:"若松",21:"芦屋",22:"福岡",23:"唐津",24:"大村"}
CLASS = {1:"A1",2:"A2",3:"B1",4:"B2"}
COORD = {"01":(36.4205,139.3320),"02":(35.8108,139.6890),"03":(35.6940,139.8730),
         "04":(35.5790,139.7460),"05":(35.6620,139.5090),"06":(34.7130,137.6080),
         "07":(34.8200,137.2200),"08":(34.8830,136.8330),"09":(34.7330,136.5230),
         "10":(36.2210,136.1490),"11":(35.0480,135.9020),"12":(34.6100,135.4790),
         "13":(34.7110,135.4080),"14":(34.1720,134.6100),"15":(34.2940,133.7900),
         "16":(34.4620,133.7900),"17":(34.3030,132.3110),"18":(34.0510,131.8090),
         "19":(33.9610,130.9300),"20":(33.9080,130.8100),"21":(33.9120,130.6620),
         "22":(33.6010,130.4010),"23":(33.4520,129.9720),"24":(32.9210,129.9610)}
DIRS16 = ["北","北北東","北東","東北東","東","東南東","南東","南南東",
          "南","南南西","南西","西南西","西","西北西","北西","北北西"]

HEADER = ["場名","場コード","開催日","レース","枠","登録番号","級別","氏名","F数","L数",
          "平均ST","全国勝率","全国2連率","全国3連率","当地勝率","当地2連率","当地3連率",
          "支部","出身","年齢","締切時刻","節名","企画名","日目"]

def wx_label(code):
    if code is None: return ""
    c = int(code)
    if c == 0: return "快晴"
    if c in (1,2): return "晴"
    if c == 3: return "曇"
    if c in (45,48): return "霧"
    if c in (51,53,55,56,57): return "霧雨"
    if c in (61,63,65,66,67): return "雨"
    if c in (71,73,75,77): return "雪"
    if c in (80,81,82): return "にわか雨"
    if c in (85,86): return "にわか雪"
    if c in (95,96,99): return "雷雨"
    return "—"

def http_json(url, timeout=60):
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode("utf-8"))

def fetch_programs(ymd):
    try:
        return http_json(PROG_URL.format(y=ymd[:4], ymd=ymd))
    except Exception as e:
        print(f"  programs取得不可 {ymd}: {e}")
        return None

def fetch_weather_archive(ymd):
    """その日のアーカイブ天候をweather.json互換形式で返す。失敗はNone。"""
    d = f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
    lats = ",".join(str(v[0]) for v in COORD.values())
    lons = ",".join(str(v[1]) for v in COORD.values())
    q = urllib.parse.urlencode({
        "latitude": lats, "longitude": lons,
        "hourly": "wind_speed_10m,wind_direction_10m,weather_code",
        "wind_speed_unit": "ms", "timezone": "Asia/Tokyo",
        "start_date": d, "end_date": d})
    try:
        data = http_json(f"{ARCHIVE}?{q}", timeout=90)
    except Exception as e:
        print(f"  天候アーカイブ取得不可 {ymd}: {e}（天候なしで続行）")
        return None
    blocks = data if isinstance(data, list) else [data]
    stadiums = {}
    for jcd, blk in zip(COORD.keys(), blocks):
        h = blk.get("hourly", {}) or {}
        rows = []
        for i, t in enumerate(h.get("time", []) or []):
            ws = (h.get("wind_speed_10m") or [None]*99)[i]
            wd = (h.get("wind_direction_10m") or [None]*99)[i]
            wc = (h.get("weather_code") or [None]*99)[i]
            rows.append({"time": t,
                         "wind": round(ws,1) if ws is not None else None,
                         "deg": int(wd) if wd is not None else None,
                         "dir": DIRS16[int((wd%360)/22.5+0.5)%16] if wd is not None else "",
                         "wx": wx_label(wc)})
        stadiums[jcd] = {"name": JCD_NAME[int(jcd)], "hourly": rows}
    return {"updated": d, "stadiums": stadiums}

def g(b, k):
    v = b.get(k)
    return "" if v is None else v

def build_csvs(prog, ymd, racers_path, motors_path):
    n_races = 0
    with open(racers_path, "w", encoding="utf-8-sig", newline="") as rf, \
         open(motors_path, "w", encoding="utf-8-sig", newline="") as mf:
        rw = csv.writer(rf); rw.writerow(HEADER)
        mw = csv.writer(mf); mw.writerow(["場名","場コード","登録番号","モーター2連対率"])
        for p in prog.get("programs", []):
            jcd = str(p["race_stadium_number"]).zfill(2)
            ba = JCD_NAME[p["race_stadium_number"]]
            rc = f"{p['race_number']}R"
            closed = str(p.get("race_closed_at") or "")
            hhmm = closed[11:16] if len(closed) >= 16 else ""
            boats = p.get("boats", [])
            if len(boats) != 6:
                continue
            n_races += 1
            for b in boats:
                rw.writerow([ba, jcd, ymd, rc, b["racer_boat_number"],
                             b["racer_number"], CLASS.get(b.get("racer_class_number"), ""),
                             b["racer_name"], g(b,"racer_flying_count"), g(b,"racer_late_count"),
                             g(b,"racer_average_start_timing"),
                             g(b,"racer_national_top_1_percent"), g(b,"racer_national_top_2_percent"),
                             g(b,"racer_national_top_3_percent"),
                             g(b,"racer_local_top_1_percent"), g(b,"racer_local_top_2_percent"),
                             g(b,"racer_local_top_3_percent"),
                             "", "", g(b,"racer_age"), hhmm,
                             g(p,"race_title"), g(p,"race_subtitle"), ""])
                mv = b.get("racer_assigned_motor_top_2_percent")
                if mv is not None:
                    mw.writerow([ba, jcd, b["racer_number"], mv])
    return n_races

def patched_bh(tmpdir):
    """build_highlights.pyをRERUNパッチして一時ファイルに書く。"""
    src = open(BH_SRC, encoding="utf-8").read()
    a1 = "if kaisai != today:"
    a2 = "if os.path.exists(pred_path):"
    if a1 not in src or a2 not in src:
        raise SystemExit("build_highlights.py のパッチ位置が見つからない（構造変更あり）")
    src = src.replace(a1, "if False:")                       # 日付ガード無効化
    src = src.replace(a2, "if False and os.path.exists(pred_path):")  # 既存predを上書き
    path = os.path.join(tmpdir, "bh_rerun.py")
    open(path, "w", encoding="utf-8").write(src)
    return path

def daterange(s, e):
    d = datetime.date(int(s[:4]), int(s[4:6]), int(s[6:]))
    end = datetime.date(int(e[:4]), int(e[4:6]), int(e[6:]))
    while d <= end:
        yield d.strftime("%Y%m%d")
        d += datetime.timedelta(days=1)

def main():
    ok, ng = [], []
    with tempfile.TemporaryDirectory() as td:
        bh = patched_bh(td)
        for ymd in daterange(START, END):
            print(f"== {ymd} ==")
            prog = fetch_programs(ymd)
            if not prog:
                ng.append(ymd); continue
            racers = os.path.join(td, f"racers_{ymd}.csv")
            motors = os.path.join(td, f"motors_{ymd}.csv")
            n = build_csvs(prog, ymd, racers, motors)
            if n == 0:
                print("  レース0件"); ng.append(ymd); continue
            wpath = os.path.join(td, f"weather_{ymd}.json")
            wj = fetch_weather_archive(ymd)
            if wj:
                json.dump(wj, open(wpath, "w", encoding="utf-8"), ensure_ascii=False)
            else:
                json.dump({"stadiums": {}}, open(wpath, "w", encoding="utf-8"))
            hout = os.path.join(td, f"hl_{ymd}.json")
            r = subprocess.run([sys.executable, bh, racers, motors, hout, KIM_CSV, wpath],
                               capture_output=True, text=True)
            print("  " + (r.stdout or "").strip().replace("\n", " / "))
            if r.returncode != 0:
                print("  ERROR: " + (r.stderr or "")[-300:]); ng.append(ymd); continue
            if os.path.exists(os.path.join("predictions", f"{ymd}.json")):
                ok.append(ymd)
            else:
                ng.append(ymd)
    print(f"完了: 成功{len(ok)}日 / 失敗{len(ng)}日")
    if ng:
        print("失敗日: " + ",".join(ng))

if __name__ == "__main__":
    main()
