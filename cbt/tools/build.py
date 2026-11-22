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
        s = sec_of(sid, q)
        if s:
            item['s'] = s
        if q.get('cat'):
            item['c'] = q['cat']
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

os.makedirs(os.path.join(APP, 'img'), exist_ok=True)
for f in used_imgs:
    shutil.copy(os.path.join(OUT, f), os.path.join(APP, f))
json.dump(data, open(os.path.join(APP, 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('official', stats['official'], 'written', stats['written'], 'propagated', stats.get('propagated', 0), 'missing', len(stats['none']), 'imgs', len(used_imgs),
      'size', os.path.getsize(os.path.join(APP, 'data.json')))
json.dump(stats['none'], open(os.path.join(OUT, 'missing_expl.json'), 'w'))
print('reordered propagated:', stats.get('reorder', []))
