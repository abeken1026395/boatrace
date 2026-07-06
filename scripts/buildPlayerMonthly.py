# -*- coding: utf-8 -*-
# buildPlayerMonthly.py
# results/YYYYMMDD.json（buildResults.py出力・艇データ入り）を全件集計し、
# 選手（登番）×月の成績を docs/data/playerMonthly.json に出力する。
# 集計項目: 出走数・1着数・2連対数・3連対数・平均ST（F/L等の非数値STは平均から除外）
# 出典: BoatraceOpenAPI経由の公式レース結果（results/配下）
import io
import os
import json
import glob
import datetime

RESULTS_DIR = "results"
OUT_PATH = os.path.join("docs", "data", "playerMonthly.json")


def main():
    files = sorted(glob.glob(os.path.join(RESULTS_DIR, "????????.json")))
    players = {}   # 登番 -> {"氏名": str, "月別": {YYYY-MM: {...}}}
    used = 0
    skipped = 0

    for path in files:
        try:
            with io.open(path, "r", encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            skipped += 1
            continue
        hd = d.get("開催日") or os.path.basename(path)[:8]
        month = "%s-%s" % (hd[:4], hd[4:6])
        has_boat = False
        for race in d.get("結果", []):
            for b in race.get("艇", []):
                has_boat = True
                toban = b.get("登番")
                place = b.get("着")
                if not toban or not place:
                    continue
                key = str(toban)
                p = players.setdefault(key, {"氏名": b.get("氏名") or "", "月別": {}})
                if b.get("氏名"):
                    p["氏名"] = b["氏名"]
                m = p["月別"].setdefault(month, {
                    "出走": 0, "1着": 0, "2連": 0, "3連": 0,
                    "ST合計": 0.0, "ST数": 0})
                m["出走"] += 1
                if place == 1:
                    m["1着"] += 1
                if place <= 2:
                    m["2連"] += 1
                if place <= 3:
                    m["3連"] += 1
                st = b.get("ST")
                if isinstance(st, (int, float)) and 0 < st < 1:
                    m["ST合計"] += st
                    m["ST数"] += 1
        if has_boat:
            used += 1
        else:
            skipped += 1

    # 平均STに変換し、中間フィールドを削除
    for p in players.values():
        for m in p["月別"].values():
            if m["ST数"] > 0:
                m["平均ST"] = round(m["ST合計"] / m["ST数"], 3)
            else:
                m["平均ST"] = None
            del m["ST合計"]
            del m["ST数"]

    months = sorted({mo for p in players.values() for mo in p["月別"]})
    obj = {
        "生成時刻": datetime.datetime.now().isoformat(timespec="seconds"),
        "対象月": months,
        "対象日数": used,
        "出典": "公式レース結果（BoatraceOpenAPI経由・results/配下）",
        "選手": players,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with io.open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT_PATH, "players", len(players),
          "months", len(months), "days used", used, "skipped", skipped)


if __name__ == "__main__":
    main()
