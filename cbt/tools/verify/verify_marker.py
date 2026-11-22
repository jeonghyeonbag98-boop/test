# Independent check: which circled marker glyph (①-④) is printed green inside each question (before [해설])
import pymupdf, json, re, sys
S = sys.argv[1]; M = '①②③④'
d = json.load(open(S + '/app/data.json'))
tot = 0; nomark = []
for sid in ['t01', 't02', 't03', 't04', 't05', 't06']:
    doc = pymupdf.open(f'{S}/pdf/{sid}.pdf')
    chars = []
    for pi, pg in enumerate(doc):
        for b in pg.get_text('rawdict')['blocks']:
            if b['type']: continue
            for l in b['lines']:
                for s in l['spans']:
                    for c in s['chars']:
                        chars.append((pi, round((c['bbox'][1] + c['bbox'][3]) / 2), c['bbox'][0], c['c'], s['color']))
    chars.sort(key=lambda x: (x[0], x[1], x[2]))
    # rebuild crude lines to find question starts
    lines = {}
    for c in chars: lines.setdefault((c[0], c[1]), []).append(c)
    exp = 1; cur = None; res = {}; inexpl = False
    for key in sorted(lines):
        cs = sorted(lines[key], key=lambda c: c[2])
        t = ''.join(c[3] for c in cs).strip()
        m = re.match(r'^(\d{1,3})\s*\.', t)
        if m and int(m.group(1)) == exp and cs[0][2] < 75:
            cur = exp; exp += 1; res[cur] = set(); inexpl = False; continue
        if cur is None: continue
        if '[해설]' in t: inexpl = True
        if inexpl: continue
        for c in cs:
            if c[3] in M and c[4] == 0x008000: res[cur].add(M.index(c[3]))
    qs = {q['n']: q for q in d['q'][sid]}
    bad = [(n, sorted(k + 1 for k in g), qs[n]['a'] + 1) for n, g in res.items() if g and g != {qs[n]['a']}]
    nm = [n for n, g in res.items() if not g]
    nomark += [f'{sid}/{n}' for n in nm]
    print(sid, 'checked', len(res) - len(nm), 'disagreements', bad, 'no green marker:', len(nm))
    tot += len(bad)
print('total disagreements', tot)
print('without green marker:', nomark)
