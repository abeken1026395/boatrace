# -*- coding: utf-8 -*-
# buildMotorHistory.py
# 各場の節が完結した時点（venueMeta の日目＝「最終日」）で、その節のモーター成績
# （モーター番号→最終2連率）を数字だけ docs/data/motorHistory.json に append 蓄積する。
# 次節以降「前節1位モーター（節内2連率トップ）」を表示するための元データ。
#
# 入力（すべて既存データ・新規取得なし・読み取りのみ）:
#   docs/data/venueMeta.json   … jcd→場名/開催日/節名/日目（PR#45）
#   docs/motor/motors_all.csv  … 場コード/モーター番号/モーター2連対率/開催日（累積化 PR#46）
# 出力:
#   docs/data/motorHistory.json … 節完結ごとに1レコード append（上書き禁止・既存不変）
#
# ハルシネーション防止: CSVに実在する数値のみ。未完結の節・CSVに行が無い場は積まない。推測ゼロ。
import os
import csv
import json
import datetime

JST = datetime.timezone(datetime.timedelta(hours=9))

VENUE_META = os.path.join("docs", "data", "venueMeta.json")
MOTORS_CSV = os.path.join("docs", "motor", "motors_all.csv")
OUT = os.path.join("docs", "data", "motorHistory.json")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def load_motor_rows():
    """motors_all.csv を読み、jcd(2桁)→[{番号,2連率,開催日}] にまとめる。"""
    rows_by_jcd = {}
    if not os.path.exists(MOTORS_CSV):
        return rows_by_jcd
    with open(MOTORS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            jcd = str(r.get("場コード", "")).zfill(2)
            no = str(r.get("モーター番号", "")).strip()
            rate = str(r.get("モーター2連対率", "")).strip()
            hd = str(r.get("開催日", "")).strip()
            if not jcd or not no:
                continue
            rows_by_jcd.setdefault(jcd, []).append({"番号": no, "2連率": rate, "開催日": hd})
    return rows_by_jcd


def build_motors_dict(rows, session_hd):
    """該当場の行から、その節の開催日に一致する {番号: 2連率(float)} を作る。
    2連率が数値でない/空の番号は積まない（捏造しない）。"""
    motors = {}
    for r in rows:
        if session_hd and r["開催日"] != session_hd:
            continue  # 前節記録など別開催日の行は混ぜない
        try:
            rate = float(r["2連率"])
        except (ValueError, TypeError):
            continue  # 実数でなければ積まない
        motors[r["番号"]] = rate
    return motors


def main():
    meta = load_json(VENUE_META)
    if not meta or not isinstance(meta.get("venues"), dict):
        print("venueMeta.json が読めないか空。処理中止（既存を変更しない）。")
        return

    rows_by_jcd = load_motor_rows()

    hist = load_json(OUT)
    if not hist or not isinstance(hist.get("sessions"), list):
        hist = {
            "updated": "",
            "note": "各場の節完結時点のモーター2連率（数字のみ・実測）。前節1位判定用。",
            "windowNote": "append方式・既存レコードは不変",
            "sessions": [],
        }

    # 既存の重複防止キー集合（jcd＋節名＋開催日）
    seen = set()
    for s in hist["sessions"]:
        seen.add((str(s.get("jcd", "")).zfill(2), str(s.get("節名", "")), str(s.get("開催日", ""))))

    added = 0
    skipped_dup = 0
    for jcd, v in sorted(meta["venues"].items()):
        jcd = str(jcd).zfill(2)
        if str(v.get("日目", "")) != "最終日":
            continue  # 節完結（最終日）のみ蓄積
        setsu = str(v.get("節名", ""))
        hd = str(v.get("開催日", ""))
        key = (jcd, setsu, hd)
        if key in seen:
            skipped_dup += 1
            continue  # 同一節を二重に積まない
        rows = rows_by_jcd.get(jcd, [])
        motors = build_motors_dict(rows, hd)
        if not motors:
            print("  [skip] {} {} … CSVに該当開催日のモーター数値なし".format(jcd, v.get("場名", "")))
            continue  # 実データが無ければ積まない
        rec = {
            "jcd": jcd,
            "場名": str(v.get("場名", "")),
            "節名": setsu,
            "開催日": hd,
            "motors": motors,
        }
        hist["sessions"].append(rec)
        seen.add(key)
        added += 1
        top_no = max(motors, key=lambda k: motors[k])
        print("  [add] {} {} 「{}」 {} … {}機 / 節内トップ M{}={}".format(
            jcd, v.get("場名", ""), setsu, hd, len(motors), top_no, motors[top_no]))

    if added == 0:
        print("新規に積む節なし（追加0 / 重複スキップ{}）。".format(skipped_dup))
        # 既存が無く初回で追加0でも、空の器は作らず既存を保つ（無ければ生成しない）
        if not os.path.exists(OUT):
            print("motorHistory.json は未生成のまま（積む実データが無いため）。")
            return

    hist["updated"] = datetime.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)
    print("保存: {} … 追加{}節 / 重複スキップ{} / 累計{}節".format(
        OUT, added, skipped_dup, len(hist["sessions"])))


if __name__ == "__main__":
    main()
