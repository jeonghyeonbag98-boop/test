"""Merge extracted sets + explanations into app/data.json and copy images.
usage: python3 -I build.py <out_dir> <expl_dir> <app_dir>
"""
import json, os, sys, shutil, re

OUT, EXPL, APP = sys.argv[1:4]
SETS = [
    ('m2026_01', '2026년 상시 01', 'exam'),
    ('m2026_02', '2026년 상시 02', 'exam'),
    ('m2026_03', '2026년 상시 03', 'exam'),
    ('y2025_1', '2025년 상시 01', 'exam'),
    ('y2025_2', '2025년 상시 02', 'exam'),
    ('y2024_1', '2024년 상시 01', 'exam'),
    ('y2024_2', '2024년 상시 02', 'exam'),
    ('y2023_1', '2023년 상시 01', 'exam'),
    ('y2023_2', '2023년 상시 02', 'exam'),
    ('t04', '잘못된 문장 찾기 200', 'topic'),
    ('t05', '키워드 찾기 50', 'topic'),
    ('t01', '필수 함수 문제 30', 'topic'),
    ('t02', '필수 계산 문제 20', 'topic'),
    ('t03', '필수 코드 문제 25', 'topic'),
    ('t06', '종류·순서 묻는 문제 10', 'topic'),
]
# answer-key corrections (source key error); value = 0-based choice index
# optional subject map for topical sets: {"set/n": 1|2|3}, kept beside the explanations dir
_SUBJ = os.path.join(os.path.dirname(EXPL.rstrip('/')), 'subjects.json')
SUBJ = json.load(open(_SUBJ)) if os.path.exists(_SUBJ) else {}
# optional study cards: topic_map.json {"set/n": card id} + cards.json {id: {t, b}}
_DIR = os.path.dirname(EXPL.rstrip('/'))
TMAP = json.load(open(os.path.join(_DIR, 'topic_map.json'))) if os.path.exists(os.path.join(_DIR, 'topic_map.json')) else {}
CARDS = json.load(open(os.path.join(_DIR, 'cards.json'))) if os.path.exists(os.path.join(_DIR, 'cards.json')) else {}
OVERRIDE = {('m2026_03', 6): 2}
SEC = {1: '컴퓨터 일반', 2: '스프레드시트 일반', 3: '데이터베이스 일반'}

matches = json.load(open(os.path.join(OUT, 'matches.json')))
raw = {sid: json.load(open(os.path.join(OUT, sid + '.json')))['questions'] for sid, _, _ in SETS}
by = {sid: {q['n']: q for q in qs} for sid, qs in raw.items()}


def text_blocks(s):
    out = []
    for para in s.strip().split('\n'):
        para = para.rstrip()
        if para.strip():
            out.append({'t': 'p', 's': para})
    return out


def clean(blocks):
    res = []
    for b in blocks:
        b = dict(b)
        if b['t'] == 'img':
            b = {'t': 'img', 'src': b['src'], 'w': b['w'], 'h': b['h']}
        res.append(b)
    return res


def sec_of(sid, q):
    if q.get('sec'):
        m = re.search(r'제\s*(\d)\s*과목', q['sec'])
        if m:
            return int(m.group(1))
    if sid.startswith(('y', 'm')):
        return 1 if q['n'] <= 20 else (2 if q['n'] <= 40 else 3)
    return None


data = {'sets': [], 'q': {}, 'secs': SEC}
stats = {'official': 0, 'written': 0, 'none': []}
used_imgs = set()
for sid, title, kind in SETS:
    mine = {}
    p = os.path.join(EXPL, sid + '.json')
    if os.path.exists(p):
        mine = {int(k): v for k, v in json.load(open(p)).items()}
    qs = []
    for q in raw[sid]:
        e = None
        if q['n'] in mine:
            e = text_blocks(mine[q['n']]); stats['written'] += 1
        elif q.get('expl'):
            e = clean(q['expl']); stats['official'] += 1
        else:
            m = matches.get('%s/%d' % (sid, q['n']))
            if m and m[2]:
                src = by[m[0]][m[1]]
                e = clean(src['expl']); stats['official'] += 1
        if e is None:
            stats['none'].append('%s/%d' % (sid, q['n']))
            e = []
        item = {'n': q['n'], 'stem': clean(q['stem']), 'ch': [clean(c) for c in q['choices']],
                'a': OVERRIDE.get((sid, q['n']), q['ans']), 'e': e}
        s = sec_of(sid, q) or SUBJ.get('%s/%d' % (sid, q['n']))
        if s:
            item['s'] = s
        if q.get('cat'):
            item['c'] = q['cat']
        k = TMAP.get('%s/%d' % (sid, q['n']))
        if k in CARDS:
            item['k'] = k
        qs.append(item)
        for part in [item['stem'], item['e']] + item['ch']:
            for b in part:
                if b['t'] == 'img':
                    used_imgs.add(b['src'])
                for m2 in re.finditer(r'⟦(img/[^⟧]+)⟧', b.get('s', '')):
                    used_imgs.add(m2.group(1))
    data['sets'].append({'id': sid, 'title': title, 'kind': kind, 'count': len(qs)})
    data['q'][sid] = qs

# propagate explanations to near-identical questions (same answer text, similar stem)
import difflib
def _txt(bs): return ' '.join(b.get('s', '') for b in bs if b['t'] != 'img')
def _norm(x): return re.sub(r'[\s‘’“”\'"·ㆍ.,()?<>]', '', x)
donors = []
for sid, qs in data['q'].items():
    for it in qs:
        if it['e'] and it['a'] is not None:
            donors.append((_norm(_txt(it['stem'])), _norm(_txt(it['ch'][it['a']])), it['e'], it))
still = []
for name in stats['none']:
    sid, n = name.split('/')
    it = next(x for x in data['q'][sid] if x['n'] == int(n))
    if it['a'] is None:
        still.append(name); continue
    st, an = _norm(_txt(it['stem'])), _norm(_txt(it['ch'][it['a']]))
    best = None
    for dst, dan, de, dit in donors:
        if not an or not dan:
            continue
        if difflib.SequenceMatcher(None, an, dan).ratio() < 0.9:
            continue
        sm = difflib.SequenceMatcher(None, st, dst)
        if sm.quick_ratio() < 0.85 or sm.ratio() < 0.85:
            continue
        r = sm.ratio()
        if best is None or r > best[0]:
            best = (r, de, dit)
    if best:
        it['e'] = best[1]; stats['propagated'] = stats.get('propagated', 0) + 1
        same = all(difflib.SequenceMatcher(None, _txt(x), _txt(y)).ratio() > 0.85 for x, y in zip(it['ch'], best[2]['ch']))
        if not same and re.search('[①②③④]', _txt(best[1])):
            stats.setdefault('reorder', []).append(name)
    else:
        still.append(name)
stats['none'] = still

# resolve wrap-join spacing markers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spacing, glob
extra = [open(f).read() for f in glob.glob(os.path.join(OUT, 'raw_*.txt'))]
for f in glob.glob(os.path.join(EXPL, '*.json')):
    extra += list(json.load(open(f)).values())
splog = spacing.resolve_data(data, extra)

# typo / formatting corrections: [scope ('*' or 'set/n'), old, new] or [scope, '@choice'|'@stem', index, blocks]
FIX = os.path.join(os.path.dirname(EXPL.rstrip('/')), 'fixes.json')
fixcount = {}
if os.path.exists(FIX):
    for fx in json.load(open(FIX)):
        scope = fx[0]
        for sid, qs in data['q'].items():
            for q in qs:
                key = '%s/%d' % (sid, q['n'])
                if scope != '*' and scope != key:
                    continue
                if fx[1] == '@choice':
                    q['ch'][fx[2]] = fx[3]; fixcount[str(fx[:3])] = fixcount.get(str(fx[:3]), 0) + 1; continue
                if fx[1] == '@stem':
                    q['stem'] = fx[3]; fixcount[str(fx[:2])] = fixcount.get(str(fx[:2]), 0) + 1; continue
                old, new = fx[1], fx[2]
                for part in [q['stem'], q['e']] + q['ch']:
                    for b in part:
                        if 's' in b and old in b['s']:
                            b['s'] = b['s'].replace(old, new)
                            fixcount[old] = fixcount.get(old, 0) + 1
                    if '\n' in new:   # split a paragraph into several blocks
                        part[:] = [nb for b in part for nb in
                                   ([dict(b, s=x) for x in b['s'].split('\n')] if b.get('t') == 'p' and '\n' in b.get('s', '') else [b])]
                    part[:] = [b for b in part if not ('s' in b and not b['s'].strip())]
    unused = [fx for fx in json.load(open(FIX)) if (str(fx[:3]) if fx[1] == '@choice' else str(fx[:2]) if fx[1] == '@stem' else fx[1]) not in fixcount]
    print('fixes applied', sum(fixcount.values()), 'unused', unused)
with open(os.path.join(OUT, 'spacing_log.tsv'), 'w') as fh:
    for row in splog:
        fh.write('\t'.join(str(x) for x in row) + '\n')
print('spacing joins', len(splog), 'spaced', sum(1 for r in splog if r[3] == ' '))

os.makedirs(os.path.join(APP, 'img'), exist_ok=True)
for f in used_imgs:
    shutil.copy(os.path.join(OUT, f), os.path.join(APP, f))
used_cards = {q['k'] for qs in data['q'].values() for q in qs if 'k' in q}
data['cards'] = {k: v for k, v in CARDS.items() if k in used_cards}
json.dump(data, open(os.path.join(APP, 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('official', stats['official'], 'written', stats['written'], 'propagated', stats.get('propagated', 0), 'missing', len(stats['none']), 'imgs', len(used_imgs),
      'size', os.path.getsize(os.path.join(APP, 'data.json')))
json.dump(stats['none'], open(os.path.join(OUT, 'missing_expl.json'), 'w'))
print('reordered propagated:', stats.get('reorder', []))
