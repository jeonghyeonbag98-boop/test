import json, re, difflib, sys
S = sys.argv[1]
d = json.load(open(S + '/app/data.json'))
def txt(bs): return ' '.join(b.get('s', '') for b in bs if b['t'] != 'img')
def norm(x): return re.sub(r'[\s‘’“”\'"·ㆍ.,()?<>]', '', x)
items = []
for sid, qs in d['q'].items():
    for q in qs:
        items.append((sid, q['n'], norm(txt(q['stem'])), [norm(txt(c)) for c in q['ch']], q['a']))
pairs = 0; conflicts = []; corroborated = set()
for i in range(len(items)):
    a = items[i]
    for j in range(i + 1, len(items)):
        b = items[j]
        sm = difflib.SequenceMatcher(None, a[2], b[2])
        if sm.real_quick_ratio() < 0.85 or sm.quick_ratio() < 0.85 or sm.ratio() < 0.85:
            continue
        # same choice set (order-insensitive)?
        ca, cb = a[3], b[3]
        if not all(ca) or not all(cb):
            continue
        mapping = {}
        ok = True
        for k, x in enumerate(ca):
            best = max(range(4), key=lambda m: difflib.SequenceMatcher(None, x, cb[m]).ratio())
            if difflib.SequenceMatcher(None, x, cb[best]).ratio() < 0.8: ok = False; break
            mapping[k] = best
        if not ok or len(set(mapping.values())) < 4:
            continue
        pairs += 1
        if mapping[a[4]] != b[4]:
            conflicts.append((a[0], a[1], a[4] + 1, b[0], b[1], b[4] + 1))
        else:
            corroborated.add((a[0], a[1])); corroborated.add((b[0], b[1]))
print('duplicate pairs with same choices:', pairs)
print('answer conflicts:', conflicts)
print('questions corroborated by another copy:', len(corroborated))
json.dump(sorted(corroborated), open(S + '/out/corroborated.json', 'w'))
