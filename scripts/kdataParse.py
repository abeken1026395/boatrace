# -*- coding: utf-8 -*-
import re, csv, sys

SP = r"C:\Users\USER\AppData\Local\Temp\claude\C--Users-USER\c4802c4b-3dd3-445f-87f1-945018f55ba4\scratchpad"
HD = "260710"

text = open(SP + r"\K260710_utf8.txt", encoding="utf-8").read()
lines = text.split("\n")

# ---- regexes ----
KBGN_RE = re.compile(r'^(\d{2})KBGN')
KEND_RE = re.compile(r'^(\d{2})KEND')
# race heading: has  <rno>R ... H<dist>m ... 風 <dir> <mps>m 波 <cm>cm
HEAD_RE = re.compile(
    r'^\s+(\d+)R[\s　]+(.+?)[\s　]+H(\d+)m'
    r'[\s　]+([^\s　]+)[\s　]+風[\s　]+([^\s　]+)[\s　]+(\d+)m'
    r'[\s　]+波[\s　]+(\d+)cm')
# entry line: chaku waku toban NAME motor boat tenji shinnyu st racetime
ENTRY_RE = re.compile(
    r'^\s*(\S+)[\s　]+(\d)[\s　]+(\d{4})[\s　]+(.+?)'
    r'[\s　]+(\d+)[\s　]+(\d+)[\s　]+(\d+\.\d{2})'
    r'[\s　]+(\d)[\s　]+(\S+)[\s　]+(.+?)[\s　]*$')
# lenient fallback for 欠場(K0) rows: chaku waku toban NAME motor boat <rest=欠>
ENTRY_RE2 = re.compile(
    r'^\s*(\S+)[\s　]+(\d)[\s　]+(\d{4})[\s　]+(.+?)'
    r'[\s　]+(\d+)[\s　]+(\d+)[\s　]+(.*)$')

SHIKI = ['単勝', '複勝', '２連単', '２連複', '拡連複', '３連単', '３連複']
SHIKI_NO_NINKI = ('単勝', '複勝')

races = []      # hd,jcd,rno,raceName,distance,weather,windDir,windMps,waveCm,kimarite
entries = []    # hd,jcd,rno,chaku,waku,toban,name,motorNo,boatNo,tenjiT,shinnyu,st,raceTime
payouts = []    # hd,jcd,rno,shiki,combo,payout,ninki
failures = []
empty_entries = []  # 欠場等で tenji/st/racetime 空のエントリー

jcd = None
cur = None          # current race key dict
cur_shiki = None    # current payout shiki for continuation lines
race_index = {}     # (jcd,rno)->race row (to fill kimarite)

def toks(s):
    return re.split(r'[\s　]+', s.strip())

for ln in lines:
    m = KBGN_RE.match(ln)
    if m:
        jcd = m.group(1)
        cur = None
        cur_shiki = None
        continue
    if KEND_RE.match(ln):
        jcd = None
        cur = None
        cur_shiki = None
        continue
    if jcd is None:
        continue

    # race heading
    hm = HEAD_RE.match(ln)
    if hm:
        rno = int(hm.group(1))
        race = {
            'hd': HD, 'jcd': jcd, 'rno': rno,
            'raceName': hm.group(2).strip(),
            'distance': 'H' + hm.group(3) + 'm',
            'weather': hm.group(4),
            'windDir': hm.group(5),
            'windMps': hm.group(6) + 'm',
            'waveCm': hm.group(7) + 'cm',
            'kimarite': '',
        }
        races.append(race)
        race_index[(jcd, rno)] = race
        cur = (jcd, rno)
        cur_shiki = None
        continue

    # column header line -> kimarite = last token
    if '登番' in ln and '選' in ln:
        if cur is not None:
            race_index[cur]['kimarite'] = toks(ln)[-1]
        continue

    if '---' in ln:
        continue

    # payout lines
    t = toks(ln)
    if t and t[0] in SHIKI:
        cur_shiki = t[0]
        rest = t[1:]
        if cur_shiki in SHIKI_NO_NINKI:
            for i in range(0, len(rest) - 1, 2):
                payouts.append({'hd': HD, 'jcd': cur[0], 'rno': cur[1],
                                'shiki': cur_shiki, 'combo': rest[i],
                                'payout': rest[i + 1], 'ninki': ''})
        else:
            ninki = ''
            if '人気' in rest:
                k = rest.index('人気')
                if k + 1 < len(rest):
                    ninki = rest[k + 1]
            payouts.append({'hd': HD, 'jcd': cur[0], 'rno': cur[1],
                            'shiki': cur_shiki, 'combo': rest[0] if rest else '',
                            'payout': rest[1] if len(rest) > 1 else '', 'ninki': ninki})
        continue

    # payout continuation (拡連複 extra rows: start with a combo like d-d)
    if cur_shiki == '拡連複' and t and re.match(r'^\d+-\d+', t[0]):
        rest = t
        ninki = ''
        if '人気' in rest:
            k = rest.index('人気')
            if k + 1 < len(rest):
                ninki = rest[k + 1]
        payouts.append({'hd': HD, 'jcd': cur[0], 'rno': cur[1],
                        'shiki': cur_shiki, 'combo': rest[0],
                        'payout': rest[1] if len(rest) > 1 else '', 'ninki': ninki})
        continue

    # entry line
    em = ENTRY_RE.match(ln)
    if em:
        rt = em.group(10).strip()
        if not re.search(r'\d', rt):
            rt = ''
        entries.append({
            'hd': HD, 'jcd': cur[0] if cur else jcd, 'rno': cur[1] if cur else '',
            'chaku': em.group(1), 'waku': em.group(2), 'toban': em.group(3),
            'name': em.group(4).strip(), 'motorNo': em.group(5), 'boatNo': em.group(6),
            'tenjiT': em.group(7), 'shinnyu': em.group(8), 'st': em.group(9),
            'raceTime': rt,
        })
        continue

    # lenient fallback: 欠場(K0) etc. -> capture with empty tenji/shinnyu/st/raceTime
    em2 = ENTRY_RE2.match(ln)
    if em2 and cur is not None and re.match(r'^\s*(\d|S|F|L|K|欠|失|妨|転)', ln):
        entries.append({
            'hd': HD, 'jcd': cur[0], 'rno': cur[1],
            'chaku': em2.group(1), 'waku': em2.group(2), 'toban': em2.group(3),
            'name': em2.group(4).strip(), 'motorNo': em2.group(5), 'boatNo': em2.group(6),
            'tenjiT': '', 'shinnyu': '', 'st': '', 'raceTime': '',
        })
        empty_entries.append({'jcd': cur[0], 'rno': cur[1], 'chaku': em2.group(1),
                              'toban': em2.group(3), 'line': ln.rstrip()})
        continue

    # if a non-blank line inside a race that looks like data but didn't match -> failure
    if ln.strip() and cur is not None:
        # ignore obvious non-data (title/blank), only flag lines that look like an entry attempt
        if re.match(r'^\s*(\d|S|F|L|K|欠|失|妨|転)', ln) and '登番' not in ln:
            failures.append({'jcd': cur[0], 'rno': cur[1], 'line': ln})

# ---- write CSVs ----
def write_csv(path, cols, rows):
    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)

write_csv(SP + r"\races202607_test.csv",
          ['hd','jcd','rno','raceName','distance','weather','windDir','windMps','waveCm','kimarite'], races)
write_csv(SP + r"\entries202607_test.csv",
          ['hd','jcd','rno','chaku','waku','toban','name','motorNo','boatNo','tenjiT','shinnyu','st','raceTime'], entries)
write_csv(SP + r"\payouts202607_test.csv",
          ['hd','jcd','rno','shiki','combo','payout','ninki'], payouts)

print("races=%d entries=%d payouts=%d failures=%d" % (len(races), len(entries), len(payouts), len(failures)))

# empty-value checks in races
empty_race = []
for r in races:
    for k in ['raceName','distance','weather','windDir','windMps','waveCm','kimarite']:
        if not r[k]:
            empty_race.append((r['jcd'], r['rno'], k))
if empty_race:
    print("EMPTY_RACE_FIELDS:")
    for e in empty_race:
        print("  jcd=%s rno=%s field=%s" % e)

# entries with empty raceTime (expected for chaku>=3 sometimes) - count only
empty_rt = [(e['jcd'], e['rno'], e['chaku']) for e in entries if not e['raceTime']]
print("entries_with_empty_raceTime=%d" % len(empty_rt))

# non-numeric chaku list
odd_chaku = sorted(set(e['chaku'] for e in entries if not re.match(r'^0?\d$', e['chaku'])))
print("non_numeric_chaku_values=%s" % odd_chaku)

if empty_entries:
    print("EMPTY_VALUE_ENTRIES (欠場等 tenji/st/raceTime空):")
    for e in empty_entries:
        print("  jcd=%s rno=%s chaku=%s toban=%s | %s" % (e['jcd'], e['rno'], e['chaku'], e['toban'], e['line']))

if failures:
    print("PARSE_FAILURES:")
    for fa in failures:
        print("  jcd=%s rno=%s | %s" % (fa['jcd'], fa['rno'], fa['line']))
else:
    print("PARSE_FAILURES: none")

# races per jcd sanity
from collections import Counter
c = Counter((r['jcd']) for r in races)
print("races_per_jcd=%s" % dict(sorted(c.items())))
ce = Counter((e['jcd']) for e in entries)
print("entries_per_jcd=%s" % dict(sorted(ce.items())))
