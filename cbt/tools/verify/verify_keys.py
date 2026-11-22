import json, re, subprocess, sys
S = sys.argv[1]
M = '①②③④'
d = json.load(open(S + '/app/data.json'))
exams = ['y2023_1','y2023_2','y2024_1','y2024_2','y2025_1','y2025_2','m2026_01','m2026_02','m2026_03']
bad = 0
for e in exams:
    txt = subprocess.run(['pdftotext', '-layout', f'{S}/pdf/{e}.pdf', '-'], capture_output=True, text=True).stdout
    tail = txt[txt.rfind('정답'):]
    key = {int(a): M.index(b) for a, b in re.findall(r'(\d{1,2})\.\s*([①②③④])', tail)}
    qs = {q['n']: q for q in d['q'][e]}
    diffs = [(n, M[key.get(n, -1)] if n in key else None, M[qs[n]['a']]) for n in range(1, 61) if key.get(n) != qs[n]['a']]
    print(e, 'key entries', len(key), 'questions', len(qs), 'diffs', diffs)
    bad += len(diffs)
print('total diffs', bad)
