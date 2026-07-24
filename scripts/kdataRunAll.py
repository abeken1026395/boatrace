# -*- coding: utf-8 -*-
"""Full-period mbrace K-file harvester.
Usage: py run_all.py [ndays] [startYYMMDD] [outroot]
Defaults: 365  260720  out
DL -> integrity(size+CRC) -> save raw TXT -> parse -> append monthly CSV -> anomaly log.
Incremental writes, resume via ledger, one HTTP try, sleep 1.0s, timeout 8s.
"""
import sys, os, csv, time, urllib.request, urllib.error, datetime, socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unpackLzh
import kparser

SP = os.path.dirname(os.path.abspath(__file__))

NDAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 365
if len(sys.argv) > 2:
    s = sys.argv[2]
    START = datetime.date(2000 + int(s[0:2]), int(s[2:4]), int(s[4:6]))
else:
    START = datetime.date(2026, 7, 20)
OUTROOT = sys.argv[3] if len(sys.argv) > 3 else "out"

OUTDIR = os.path.join(SP, OUTROOT)
RAWDIR = os.path.join(SP, "raw", "kfiles")
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(RAWDIR, exist_ok=True)

LEDGER = os.path.join(OUTDIR, "_progress.log")
ANOM = os.path.join(OUTDIR, "parseAnomalies.csv")
RETRY = os.path.join(OUTDIR, "retry_list.txt")
TMP_LZH = os.path.join(OUTDIR, "_tmp.lzh")

RACE_COLS = ['hd', 'jcd', 'rno', 'raceName', 'distance', 'weather',
             'windDir', 'windMps', 'waveCm', 'kimarite']
ENTRY_COLS = ['hd', 'jcd', 'rno', 'chaku', 'waku', 'toban', 'name',
              'motorNo', 'boatNo', 'tenjiT', 'shinnyu', 'st', 'raceTime']
PAYOUT_COLS = ['hd', 'jcd', 'rno', 'shiki', 'combo', 'payout', 'ninki']
ANOM_COLS = ['hd', 'jcd', 'rno', '種別', '生行']

UA = "Mozilla/5.0 (kfile-harvester)"


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
        f.flush()


def log_anom(rows):
    if not rows:
        return
    new = not os.path.exists(ANOM)
    with open(ANOM, 'a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=ANOM_COLS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)
        f.flush()


def ledger_done():
    done = set()
    if os.path.exists(LEDGER):
        with open(LEDGER, encoding='utf-8') as f:
            for line in f:
                p = line.split(',')
                if p:
                    done.add(p[0])
    return done


def ledger_write(ymd, status, nr, ne, np_, na):
    with open(LEDGER, 'a', encoding='utf-8') as f:
        f.write("%s,%s,%d,%d,%d,%d\n" % (ymd, status, nr, ne, np_, na))
        f.flush()


def retry_add(ymd, reason, url):
    with open(RETRY, 'a', encoding='utf-8') as f:
        f.write("%s,%s,%s\n" % (ymd, reason, url))
        f.flush()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return ("ok", resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            return ("absent", "HTTP %d" % e.code)
        return ("error", "HTTP %d" % e.code)
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        return ("error", "%s" % (getattr(e, 'reason', e),))
    except Exception as e:
        return ("error", repr(e))


def main():
    done = ledger_done()
    tot_races = tot_entries = tot_payouts = tot_anom = 0
    got = absent = errors = corrupt = 0
    processed = 0

    print("START run: ndays=%d from %s outroot=%s (already done=%d)" %
          (NDAYS, START.isoformat(), OUTROOT, len(done)), flush=True)

    for i in range(NDAYS):
        d = START - datetime.timedelta(days=i)
        ymd = "%02d%02d%02d" % (d.year % 100, d.month, d.day)
        yyyymm = "%04d%02d" % (d.year, d.month)
        if ymd in done:
            processed += 1
            continue

        url = "http://www1.mbrace.or.jp/od2/K/%s/k%s.lzh" % (yyyymm, ymd)
        time.sleep(1.0)
        status, payload = fetch(url)

        if status == "absent":
            log_anom([{'hd': ymd, 'jcd': '', 'rno': '', '種別': 'ファイル不在(404)', '生行': url}])
            retry_add(ymd, "不在(404)", url)
            ledger_write(ymd, "absent", 0, 0, 0, 1)
            absent += 1
            tot_anom += 1
            processed += 1
            _tick(processed, got, absent, tot_races)
            continue
        if status == "error":
            log_anom([{'hd': ymd, 'jcd': '', 'rno': '', '種別': '取得失敗', '生行': url + ' :: ' + str(payload)}])
            retry_add(ymd, "取得失敗:" + str(payload), url)
            ledger_write(ymd, "error", 0, 0, 0, 1)
            errors += 1
            tot_anom += 1
            processed += 1
            _tick(processed, got, absent, tot_races)
            continue

        # write temp lzh, decode with integrity check
        with open(TMP_LZH, 'wb') as f:
            f.write(payload)
        try:
            raw, meta = unpackLzh.load_lzh(TMP_LZH)
        except Exception as e:
            log_anom([{'hd': ymd, 'jcd': '', 'rno': '', '種別': '原寸不一致', '生行': url + ' :: ' + repr(e)}])
            retry_add(ymd, "原寸不一致", url)
            ledger_write(ymd, "corrupt", 0, 0, 0, 1)
            corrupt += 1
            tot_anom += 1
            processed += 1
            try:
                os.remove(TMP_LZH)
            except OSError:
                pass
            _tick(processed, got, absent, tot_races)
            continue

        # save raw TXT (shift_jis bytes, as-is)
        with open(os.path.join(RAWDIR, "K%s.TXT" % ymd), 'wb') as f:
            f.write(raw)
        try:
            os.remove(TMP_LZH)
        except OSError:
            pass

        # parse
        text = raw.decode('shift_jis', 'replace')
        try:
            res = kparser.parse_day(text, ymd)
        except Exception as e:
            log_anom([{'hd': ymd, 'jcd': '', 'rno': '', '種別': '例外(ファイル)', '生行': repr(e)}])
            ledger_write(ymd, "parsefail", 0, 0, 0, 1)
            tot_anom += 1
            processed += 1
            _tick(processed, got, absent, tot_races)
            continue

        append_csv(os.path.join(OUTDIR, "races%s.csv" % yyyymm), RACE_COLS, res['races'])
        append_csv(os.path.join(OUTDIR, "entries%s.csv" % yyyymm), ENTRY_COLS, res['entries'])
        append_csv(os.path.join(OUTDIR, "payouts%s.csv" % yyyymm), PAYOUT_COLS, res['payouts'])
        log_anom(res['anomalies'])

        nr, ne, npp, na = (len(res['races']), len(res['entries']),
                           len(res['payouts']), len(res['anomalies']))
        tot_races += nr
        tot_entries += ne
        tot_payouts += npp
        tot_anom += na
        got += 1
        processed += 1
        ledger_write(ymd, "ok", nr, ne, npp, na)
        _tick(processed, got, absent, tot_races)

    print("DONE. got=%d absent=%d errors=%d corrupt=%d | races=%d entries=%d payouts=%d anomalies=%d" %
          (got, absent, errors, corrupt, tot_races, tot_entries, tot_payouts, tot_anom), flush=True)


def _tick(processed, got, absent, tot_races):
    if processed % 10 == 0:
        print("%d/%d done, got=%d absent=%d races=%d" %
              (processed, NDAYS, got, absent, tot_races), flush=True)


if __name__ == "__main__":
    main()
