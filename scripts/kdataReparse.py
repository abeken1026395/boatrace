# -*- coding: utf-8 -*-
"""Re-parse ONLY from saved raw/kfiles/*.TXT (NO network at all).
Reproduces the original per-day processing order (ledger order) so that
races/entries come out byte-identical; payouts gains the dead-heat rows.
Writes into out_reparse/ (does not touch out/).
"""
import os, csv
import kparser  # imports only 're' — no network

SP = os.path.dirname(os.path.abspath(__file__))
RAWDIR = os.path.join(SP, "raw", "kfiles")
SRCLEDGER = os.path.join(SP, "out", "_progress.log")
OUTDIR = os.path.join(SP, "out_reparse")
os.makedirs(OUTDIR, exist_ok=True)

RACE_COLS = ['hd', 'jcd', 'rno', 'raceName', 'distance', 'weather',
             'windDir', 'windMps', 'waveCm', 'kimarite']
ENTRY_COLS = ['hd', 'jcd', 'rno', 'chaku', 'waku', 'toban', 'name',
              'motorNo', 'boatNo', 'tenjiT', 'shinnyu', 'st', 'raceTime']
PAYOUT_COLS = ['hd', 'jcd', 'rno', 'shiki', 'combo', 'payout', 'ninki']
ANOM_COLS = ['hd', 'jcd', 'rno', '種別', '生行']


def append_csv(path, cols, rows):
    if not rows:
        return
    new = not os.path.exists(path)
    with open(path, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    # replicate original order strictly from the ledger (newest->oldest, ok only)
    order = []
    with open(SRCLEDGER, encoding='utf-8') as f:
        for line in f:
            p = line.strip().split(',')
            if len(p) >= 2 and p[1] == 'ok':
                order.append(p[0])

    n = 0
    for ymd in order:
        yyyymm = "20%s%s" % (ymd[0:2], ymd[2:4])  # YYMMDD -> YYYYMM
        txt = os.path.join(RAWDIR, "K%s.TXT" % ymd)
        raw = open(txt, "rb").read()               # LOCAL FILE ONLY
        text = raw.decode('shift_jis', 'replace')
        res = kparser.parse_day(text, ymd)
        append_csv(os.path.join(OUTDIR, "races%s.csv" % yyyymm), RACE_COLS, res['races'])
        append_csv(os.path.join(OUTDIR, "entries%s.csv" % yyyymm), ENTRY_COLS, res['entries'])
        append_csv(os.path.join(OUTDIR, "payouts%s.csv" % yyyymm), PAYOUT_COLS, res['payouts'])
        append_csv(os.path.join(OUTDIR, "parseAnomalies.csv"), ANOM_COLS, res['anomalies'])
        n += 1
    print("reparsed %d days from raw (no network)" % n)


if __name__ == "__main__":
    main()
