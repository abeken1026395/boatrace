#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetchTideToday.py
当日開催の潮汐場について open-meteo Marine から当日の潮位を取得し、
満潮/干潮の時刻・現在潮位・当日の干満差・潮回り(月齢)を docs/data/tideToday.json に出力。
※水面コンディションの「事実提示」のみ。荒れ/勝敗予想には一切踏み込まない
（実測で潮汐と波乱率は無相関＝紐づけない）。
"""
import csv, json, sys, os, ssl, datetime, urllib.request, urllib.parse
RACERS = sys.argv[1] if len(sys.argv) > 1 else "docs/racers/racers_today.csv"
OUT    = sys.argv[2] if len(sys.argv) > 2 else "docs/data/tideToday.json"
MARINE = "https://marine-api.open-meteo.com/v1/marine"
COORD = {"03":(35.6940,139.8730),"04":(35.5790,139.7460),"06":(34.7130,137.6080),
         "07":(34.8200,137.2200),"08":(34.8830,136.8330),"09":(34.7330,136.5230),
         "13":(34.7110,135.4080),"14":(34.1720,134.6100),"15":(34.2940,133.7900),
         "16":(34.4620,133.7900),"17":(34.3030,132.3110),"18":(34.0510,131.8090),
         "19":(33.9610,130.9300),"20":(33.9080,130.8100),"21":(33.9120,130.6620),
         "22":(33.6010,130.4010),"23":(33.4520,129.9720),"24":(32.9210,129.9610)}
# 上記18場（干満差のある海水/汽水場）。内陸淡水6場はMarine非対応のため対象外。

def jst_now():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))

def http(url, t=25):
    with urllib.request.urlopen(url, timeout=t, context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8"))

def moon_age(ymd):
    y, m, d = int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8])
    jd = 367*y - (7*(y+((m+9)//12)))//4 + (275*m)//9 + d + 1721013.5
    return (jd - 2451549.5) % 29.530588853

def shio(age):
    a = age % 29.53
    if a <= 2 or 13 <= a <= 17 or a >= 28: return "大潮"
    if 7 <= a <= 9 or 22 <= a <= 24: return "小潮"
    if abs(a-10) < 0.6 or abs(a-25) < 0.6: return "長潮"
    if abs(a-11) < 0.6 or abs(a-26) < 0.6: return "若潮"
    return "中潮"

def extrema(times, tides):
    """満潮(極大)/干潮(極小)の(時刻HH:MM, 高さ)を返す。"""
    hi, lo = [], []
    for i in range(1, len(tides)-1):
        a, b, c = tides[i-1], tides[i], tides[i+1]
        if b is None or a is None or c is None: continue
        hm = times[i][11:16] if len(times[i]) >= 16 else ""
        if b >= a and b > c: hi.append((hm, round(b, 2)))
        if b <= a and b < c: lo.append((hm, round(b, 2)))
    return hi, lo

def main():
    try:
        with open(RACERS, encoding="utf-8-sig") as fp:
            rows = list(csv.DictReader(fp))
    except Exception as e:
        print("racers読込不可:", e); return
    if not rows:
        print("出走表空"); return
    hd = rows[0].get("開催日", "")
    open_jcd = {r.get("場コード") for r in rows if r.get("場コード")}
    d = f"{hd[:4]}-{hd[4:6]}-{hd[6:8]}"
    now = jst_now(); now_min = now.hour*60 + now.minute
    stad = {}
    for jcd in sorted(COORD):
        if jcd not in open_jcd:
            continue
        lat, lon = COORD[jcd]
        q = urllib.parse.urlencode({"latitude": lat, "longitude": lon,
            "hourly": "sea_level_height_msl", "timezone": "Asia/Tokyo",
            "start_date": d, "end_date": d})
        try:
            data = http(f"{MARINE}?{q}")
        except Exception as e:
            print(f"  {jcd} 取得不可: {e}"); continue
        h = data.get("hourly", {}) or {}
        times = h.get("time", []) or []
        tides = h.get("sea_level_height_msl", []) or []
        tv = [x for x in tides if isinstance(x, (int, float))]
        if not tv:
            continue
        hi, lo = extrema(times, tides)
        # 現在（最も近い時刻）の潮位
        cur = None; bd = 1e9
        for i, t in enumerate(times):
            if len(t) < 16 or not isinstance(tides[i], (int, float)): continue
            tm = int(t[11:13])*60 + int(t[14:16])
            if abs(tm-now_min) < bd: bd = abs(tm-now_min); cur = round(tides[i], 2)
        stad[jcd] = {"満潮": [f"{t} {v:+.2f}m" for t, v in hi],
                     "干潮": [f"{t} {v:+.2f}m" for t, v in lo],
                     "現在潮位": cur, "干満差": round(max(tv)-min(tv), 2)}
        print(f"  {jcd} 満潮{[t for t,_ in hi]} 干潮{[t for t,_ in lo]} 現在{cur}m 干満差{stad[jcd]['干満差']}m")
    doc = {"updatedJst": now.strftime("%Y-%m-%d %H:%M"), "開催日": hd,
           "潮回り": shio(moon_age(hd)) if hd else None,
           "source": "open-meteo Marine（潮位・事実情報／荒れ予想には用いない）",
           "stadiums": stad}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"OK: {len(stad)}場 潮回り{doc['潮回り']} → {OUT}")

if __name__ == "__main__":
    main()
