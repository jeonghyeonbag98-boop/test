"""Extract CBT questions from 시나공 컴활1급 필기 PDFs.
usage: python3 -I extract.py <pdf> <set_id> <kind: exam|topic> <out_dir>
Writes <out_dir>/<set_id>.json and images into <out_dir>/img/
"""
import pymupdf, re, json, sys, os, io
from PIL import Image

pdf, SID, KIND, OUT = sys.argv[1:5]
os.makedirs(os.path.join(OUT, 'img'), exist_ok=True)
MARK = '①②③④'
GREEN = 0x008000
RED = 0xff0000
SCALE = 2.5

doc = pymupdf.open(pdf)
rdoc = pymupdf.open(pdf)  # render copy (watermark removed)


def is_watermark(b):
    x0, y0, x1, y1 = b
    w, h = x1 - x0, y1 - y0
    return 190 < w < 250 and 190 < h < 250 and abs((x0 + x1) / 2 - 297.6) < 20


def page_bounds(pno):
    if KIND == 'exam':
        return (205 if pno == 0 else 60), 795
    return (135 if pno == 0 else 20), 815


def ncols(page):
    return 2 if KIND == 'exam' else 1


def col_of(x, page):
    if ncols(page) == 1:
        return 0
    return 0 if x < page.rect.width / 2 else 1


def overlap(a, b, pad=0):
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


def union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def inside(pt, r, pad=0.5):
    return r[0] - pad <= pt[0] <= r[2] + pad and r[1] - pad <= pt[1] <= r[3] + pad


# ---------------------------------------------------------------- page parse
def parse_page(pno):
    page = doc[pno]
    top, bot = page_bounds(pno)
    W = page.rect.width
    # ---- chars
    chars = []
    raw = page.get_text('rawdict')
    for b in raw['blocks']:
        if b['type'] != 0:
            continue
        for l in b['lines']:
            for s in l['spans']:
                for ch in s['chars']:
                    x0, y0, x1, y1 = ch['bbox']
                    cy = (y0 + y1) / 2
                    if cy < top or cy > bot:
                        continue
                    chars.append(dict(c=ch['c'], x0=x0, x1=x1, y0=y0, y1=y1, cy=cy,
                                      size=s['size'], color=s['color']))
    # ---- images
    imgs = []
    for info in page.get_image_info(xrefs=True):
        bb = list(info['bbox'])
        if is_watermark(bb):
            try:
                rdoc[pno].delete_image(info['xref'])
            except Exception:
                pass
            continue
        if bb[0] < -5 or bb[2] > W + 5 or bb[1] < top - 2 or bb[3] > bot + 20:
            continue
        if (bb[2] - bb[0]) < 6 or (bb[3] - bb[1]) < 6:
            continue
        imgs.append(bb)
    # ---- drawings -> segments
    segs = []
    for dr in page.get_drawings():
        r = dr['rect']
        if r.y1 < top or r.y0 > bot:
            continue
        if KIND == 'exam' and abs(r.x0 - W / 2) < 3 and abs(r.x1 - W / 2) < 3 and r.height > 200:
            continue  # column divider
        fill = dr.get('fill')
        if fill and all(abs(fill[i] - v) < 0.02 for i, v in enumerate((0.847, 0.863, 0.847))):
            continue
        if fill and all(abs(fill[i] - v) < 0.02 for i, v in enumerate((0.376, 0.392, 0.376))):
            continue
        if any(abs(r.x0 - b[0]) < 2.5 and abs(r.y0 - b[1]) < 2.5 and abs(r.x1 - b[2]) < 2.5 and abs(r.y1 - b[3]) < 2.5 for b in imgs):
            continue  # image frame
        has_curve = False
        for it in dr['items']:
            if it[0] == 'l':
                p1, p2 = it[1], it[2]
                segs.append([min(p1.x, p2.x), min(p1.y, p2.y), max(p1.x, p2.x), max(p1.y, p2.y)])
            elif it[0] == 're':
                rr = it[1]
                segs += [[rr.x0, rr.y0, rr.x1, rr.y0], [rr.x0, rr.y1, rr.x1, rr.y1],
                         [rr.x0, rr.y0, rr.x0, rr.y1], [rr.x1, rr.y0, rr.x1, rr.y1]]
            elif it[0] == 'qu':
                rr = it[1].rect
                segs += [[rr.x0, rr.y0, rr.x1, rr.y0], [rr.x0, rr.y1, rr.x1, rr.y1],
                         [rr.x0, rr.y0, rr.x0, rr.y1], [rr.x1, rr.y0, rr.x1, rr.y1]]
            elif it[0] == 'c':
                has_curve = True
        if has_curve:
            segs += [[r.x0, r.y0, r.x1, r.y0], [r.x0, r.y1, r.x1, r.y1],
                     [r.x0, r.y0, r.x0, r.y1], [r.x1, r.y0, r.x1, r.y1]]
    # cluster segments
    clusters = []
    for s in segs:
        merged = None
        for c in clusters:
            if overlap(c['bb'], s, 1.5):
                if merged is None:
                    c['bb'] = union(c['bb'], s); c['segs'].append(s); merged = c
                else:
                    merged['bb'] = union(merged['bb'], c['bb']); merged['segs'] += c['segs']; c['dead'] = True
        clusters = [c for c in clusters if not c.get('dead')]
        if merged is None:
            clusters.append({'bb': list(s), 'segs': [s]})
    # repeat merge until stable
    changed = True
    while changed:
        changed = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if overlap(clusters[i]['bb'], clusters[j]['bb'], 1.5):
                    clusters[i]['bb'] = union(clusters[i]['bb'], clusters[j]['bb'])
                    clusters[i]['segs'] += clusters[j]['segs']
                    del clusters[j]; changed = True; break
            if changed:
                break

    # ---- lines from chars (per column)
    lines = []
    for col in range(ncols(page)):
        cc = [c for c in chars if col_of((c['x0'] + c['x1']) / 2, page) == col]
        cc.sort(key=lambda c: c['cy'])
        groups = []
        for c in cc:
            g = None
            for gg in groups[-4:]:
                if abs(gg['cy'] - c['cy']) <= max(2.6, 0.33 * c['size']):
                    g = gg; break
            if g is None:
                g = {'cy': c['cy'], 'chars': [], 'n': 0}
                groups.append(g)
            g['chars'].append(c)
            if c['c'].strip():
                g['cy'] = (g['cy'] * g['n'] + c['cy']) / (g['n'] + 1); g['n'] += 1
        for g in groups:
            cs = sorted(g['chars'], key=lambda c: (c['x0'], c['x1']))
            out = []
            for c in cs:
                if out and out[-1]['c'] == c['c'] and abs(out[-1]['x0'] - c['x0']) < 0.8:
                    continue  # fake-bold duplicate
                out.append(c)
            cs = [c for c in out]
            vis = [c for c in cs if c['c'].strip()]
            if not vis:
                continue
            text = ''
            meta = []  # per char color, aligned with text
            prev = None
            for c in cs:
                if prev is not None:
                    gap = c['x0'] - prev['x1']
                    if gap > 0.28 * c['size'] and prev['c'] != ' ' and c['c'] != ' ':
                        text += ' '; meta.append((prev['color'], prev['x1']))
                text += c['c']; meta.append((c['color'], c['x0']))
                prev = c
            # strip
            lstrip = len(text) - len(text.lstrip())
            text2 = text.strip()
            meta = meta[lstrip:lstrip + len(text2)]
            ln = dict(text=text2, meta=meta, x0=min(c['x0'] for c in vis), x1=max(c['x1'] for c in vis),
                      y0=min(c['y0'] for c in vis), y1=max(c['y1'] for c in vis),
                      size=max(c['size'] for c in vis), col=col, page=pno,
                      trailing_space=text.endswith(' '))
            ln['cy'] = (ln['y0'] + ln['y1']) / 2
            lines.append(ln)

    # ---- tiny inline images -> token inside text line
    big = []
    for b in imgs:
        if (b[2] - b[0]) < 22 and (b[3] - b[1]) < 22:
            cy = (b[1] + b[3]) / 2
            cands = [l for l in lines if l['col'] == col_of((b[0] + b[2]) / 2, page) and abs(l['cy'] - cy) < 6
                     and l['x0'] - 30 <= b[0] <= l['x1'] + 30]
            if cands:
                l = min(cands, key=lambda l: abs(l['cy'] - cy))
                name = '%s_i%d_%d.webp' % (SID, pno, len(INLINE))
                clip = pymupdf.Rect(b[0] - 0.5, b[1] - 0.5, b[2] + 0.5, b[3] + 0.5)
                pix = rdoc[pno].get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=clip, alpha=False)
                Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB').save(os.path.join(OUT, 'img', name), 'WEBP', quality=85)
                INLINE.append(name)
                idx = len(l['text'])
                for i, (c_, x) in enumerate(l['meta']):
                    if x > b[0]:
                        idx = i; break
                tok = '⟦img/%s⟧' % name
                l['text'] = l['text'][:idx] + tok + l['text'][idx:]
                l['meta'] = l['meta'][:idx] + [(0, b[0])] * len(tok) + l['meta'][idx:]
                l['x0'] = min(l['x0'], b[0]); l['x1'] = max(l['x1'], b[2])
                continue
        big.append(b)
    imgs = big
    # ---- classify drawing clusters
    figs = [list(b) for b in imgs]
    boxes = []
    for c in clusters:
        bb = c['bb']
        if bb[2] - bb[0] < 4 and bb[3] - bb[1] < 4:
            continue
        inner = [l for l in lines if inside((l['x0'] + 1, l['cy']), bb) and inside((l['x1'] - 1, l['cy']), bb)]
        if any(re.match(r'^제\s*\d\s*과목', l['text']) for l in inner):
            continue
        if any(l['text'].startswith('[해설]') for l in inner) or any(l['text'].startswith('[해설]') and inside((l['x0'] + 1, l['cy']), bb) for l in lines):
            boxes.append({'bb': bb, 'kind': 'expl'}); continue
        if any(overlap(bb, f, 2) for f in imgs):
            figs.append(list(bb)); continue
        hy = set(); vx = set()
        for s in c['segs']:
            if abs(s[3] - s[1]) < 1.0 and s[2] - s[0] > 3:
                hy.add(round(s[1] / 2.5))
            elif abs(s[2] - s[0]) < 1.0 and s[3] - s[1] > 3:
                vx.add(round(s[0] / 2.5))
        # merge near-duplicate coordinates
        def ncoord(v):
            v = sorted(v); n = 0; last = None
            for x in v:
                if last is None or x - last > 1:
                    n += 1
                last = x
            return n
        nh, nv = ncoord(hy), ncoord(vx)
        if not inner and (bb[3] - bb[1] < 3 or bb[2] - bb[0] < 3):
            continue  # stray rule line
        if any(l['text'].startswith('[해설]') for l in inner):
            boxes.append({'bb': bb, 'kind': 'expl'}); continue
        if nh <= 2 and nv <= 2:
            if inner:
                boxes.append({'bb': bb, 'kind': 'box'})
            continue
        if not inner and nh <= 1 and nv <= 1:
            continue
        figs.append(list(bb))
    # merge figures (overlap or side-by-side on same band with small gap)
    changed = True
    while changed:
        changed = False
        for i in range(len(figs)):
            for j in range(i + 1, len(figs)):
                a, b = figs[i], figs[j]
                same_band = min(a[3], b[3]) - max(a[1], b[1]) > 0.5 * min(a[3] - a[1], b[3] - b[1])
                close_h = (b[0] - a[2] < 45 and a[0] - b[2] < 45)
                def marker_between(a, b):
                    lo, hi = (a[2], b[0]) if a[0] < b[0] else (b[2], a[0])
                    y0, y1 = max(a[1], b[1]) - 4, min(a[3], b[3]) + 4
                    for l in lines:
                        if y0 <= l['cy'] <= y1:
                            for ch, (col_, x) in zip(l['text'], l['meta']):
                                if ch in MARK and lo - 3 <= x <= hi + 3:
                                    return True
                    return False
                if overlap(a, b, 1) or (same_band and close_h and col_of((a[0]+a[2])/2, page) == col_of((b[0]+b[2])/2, page) and not marker_between(a, b)):
                    figs[i] = union(a, b); del figs[j]; changed = True; break
            if changed:
                break
    # drop lines inside figures, assign box ids
    keep = []
    for l in lines:
        infig = False
        for f in figs:
            if inside((l['x0'] + 1, l['cy']), f, 1.5) and inside((l['x1'] - 1, l['cy']), f, 1.5):
                infig = True; break
        if infig:
            continue
        # strip characters that sit inside a figure (line shares a row with a figure)
        for f in figs:
            if f[1] - 1.5 <= l['cy'] <= f[3] + 1.5 and l['x0'] < f[0] - 1 and l['x1'] > f[0] + 4:
                keepi = [i for i, (c_, x) in enumerate(l['meta']) if not (f[0] - 1.5 <= x <= f[2] + 1.5)]
                t2 = ''.join(l['text'][i] for i in keepi)
                m2 = [l['meta'][i] for i in keepi]
                lead = len(t2) - len(t2.lstrip())
                t3 = t2.strip()
                l['text'] = t3; l['meta'] = m2[lead:lead + len(t3)]
                if m2:
                    l['x1'] = min(l['x1'], f[0])
        if not l['text']:
            continue
        # split a line that starts outside a box (e.g. a choice marker) and continues inside it
        parts = [l]
        for b in boxes:
            bb = b['bb']
            if b['kind'] == 'box' and bb[1] - 1 <= l['cy'] <= bb[3] + 1 and l['x0'] < bb[0] - 2 and l['x1'] > bb[0] + 2:
                cut = next((i for i, (c_, x) in enumerate(l['meta']) if x >= bb[0] - 1), None)
                if cut:
                    left, right = dict(l), dict(l)
                    lt, rt = l['text'][:cut], l['text'][cut:]
                    left['text'] = lt.rstrip(); left['meta'] = l['meta'][:len(left['text'])]
                    rl = len(rt) - len(rt.lstrip())
                    right['text'] = rt.strip(); right['meta'] = l['meta'][cut + rl:cut + rl + len(right['text'])]
                    left['x1'] = bb[0] - 1
                    right['x0'] = right['meta'][0][1] if right['meta'] else bb[0]
                    parts = [p_ for p_ in (left, right) if p_['text']]
                break
        for l in parts:
            l['box'] = None
            for bi, b in enumerate(boxes):
                if b['kind'] == 'box' and inside((l['x0'] + 1, l['cy']), b['bb'], 1) and inside((l['x1'] - 1, l['cy']), b['bb'], 1):
                    l['box'] = '%d_%d' % (pno, bi); l['box_bb'] = b['bb']
            keep.append(l)
    items = []
    for l in keep:
        l['type'] = 'line'
        items.append(l)
    for f in figs:
        items.append(dict(type='fig', bb=f, page=pno, col=col_of((f[0] + f[2]) / 2, page),
                          cy=(f[1] + f[3]) / 2 + 0.01, y0=f[1]))
    items.sort(key=lambda it: (it['col'], it['cy'] if it['type'] == 'fig' else it['cy']))
    return items


INLINE = []
all_items = []
for p in range(len(doc)):
    all_items += parse_page(p)

# ------------------------------------------------------------- figure render
fig_counter = {}


def render_fig(it, qkey):
    pno = it['page']
    bb = it['bb']
    clip = pymupdf.Rect(bb[0] - 1.5, bb[1] - 1.5, bb[2] + 1.5, bb[3] + 1.5)
    pix = rdoc[pno].get_pixmap(matrix=pymupdf.Matrix(SCALE, SCALE), clip=clip, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    n = fig_counter.get(qkey, 0) + 1
    fig_counter[qkey] = n
    name = '%s_%s_%d.webp' % (SID, qkey, n)
    img.save(os.path.join(OUT, 'img', name), 'WEBP', quality=80, method=6)
    return {'t': 'img', 'src': 'img/' + name, 'w': round(bb[2] - bb[0]), 'h': round(bb[3] - bb[1])}


# ------------------------------------------------------------ segmentation
BULLET = tuple('•ㆍ·-※❶❷❸❹❺❻❼❽❾❿①②③④⑤㉠㉡㉢㉣㉤㉮㉯㉰㉱ⓐⓑⓒⓓ∴▶■□○●◎<[(') + ('Sub ', 'End ', 'If ', 'For ', 'Next', 'Dim ', 'Else', 'Do ', 'Loop', 'Case', 'Select')


def right_margin_of(lines):
    return max(l['x1'] for l in lines) if lines else 0


def assemble(items, qkey, code=False):
    """items: list of lines/figs -> list of blocks"""
    blocks = []
    # right margin per (page,col)
    rm = {}
    for it in items:
        if it['type'] == 'line':
            k = (it['page'], it['col'], it.get('box'))
            rm[k] = max(rm.get(k, 0), it['x1'])
    prev = None
    for it in items:
        if it['type'] == 'fig':
            blocks.append(render_fig(it, qkey)); prev = None; continue
        t = it['text']
        kind = 'box' if it.get('box') else 'p'
        k = (prev['page'], prev['col'], prev.get('box')) if prev is not None else None
        margin = rm.get(k, 0)
        if kind == 'box' and prev is not None and prev.get('box_bb'):
            margin = max(margin, prev['box_bb'][2] - 14)
        samecol = prev is not None and prev['page'] == it['page'] and prev['col'] == it['col']
        def _code(x):
            v = [ch for ch in x if ch.strip()]
            return bool(v) and sum(1 for ch in v if ord(ch) < 128) / len(v) >= 0.7
        wrap = (prev is not None and blocks and blocks[-1]['t'] == kind and prev.get('box') == it.get('box')
                and not it.get('hard') and not prev.get('hard')
                and not (kind == 'box' and _code(prev['text']) and _code(t))
                and prev['x1'] >= margin - 14 and not t.startswith(BULLET)
                and (not samecol or abs(it['y0'] - prev['y1']) < 12))
        if wrap:
            sep = ' ' if (prev.get('trailing_space') or re.search(r'[A-Za-z0-9,)\]]$', blocks[-1]['s'][-1:]) and re.match(r'^[A-Za-z0-9(]', t)) else ''
            if prev.get('trailing_space'):
                sep = ' '
            blocks[-1]['s'] += sep + t
        elif kind == 'box' and blocks and blocks[-1]['t'] == 'box' and blocks[-1].get('id') == it.get('box'):
            indent = max(0, int(round((it['x0'] - blocks[-1]['x0']) / 4.5)))
            blocks[-1]['s'] += '\n' + ' ' * min(indent, 12) + t
        elif kind == 'box':
            blocks.append({'t': 'box', 's': t, 'id': it.get('box'), 'x0': it['x0']})
        else:
            blocks.append({'t': 'p', 's': t})
        prev = it
    for b in blocks:
        b.pop('id', None); b.pop('x0', None)
    return blocks


questions = []
answer_key = {}
cur = None
category = None
expected = 1
in_key = False
SECTION = None
KEY_PAGES = set()
if KIND == 'exam':
    for pi, pg in enumerate(doc):
        if len(re.findall(r'(\d{1,2})\s*\.\s*([①②③④])', pg.get_text())) >= 30:
            KEY_PAGES.add(pi)
for it in all_items:
    if it['page'] in KEY_PAGES:
        continue
    if it['type'] == 'line':
        t = it['text']
        if KIND == 'exam' and (t == '정답' or in_key):
            if t == '정답':
                in_key = True
                continue
            for m in re.finditer(r'(\d{1,2})\s*\.\s*([①②③④])', t):
                answer_key[int(m.group(1))] = MARK.index(m.group(2))
            continue
        if re.match(r'^제\s*\d\s*과목', t):
            SECTION = re.sub(r'\s+', ' ', t)
            continue
        if t.startswith('※ 다음 문제를') or t.startswith('답란('):
            continue
        reds = sum(1 for c in it['meta'] if c[0] == RED)
        if KIND == 'topic' and re.match(r'^\[[^\]]+\]$', t) and t != '[해설]' and reds >= len(t.replace(' ', '')) * 0.5:
            category = t.strip('[]').strip()
            continue
        m = re.match(r'^(\d{1,3})\s*\.\s*(.*)$', t)
        if m and int(m.group(1)) == expected and not (cur and cur.get('_expl') and it['x0'] > 70 and KIND == 'topic' and False):
            # new question
            cur = {'num': expected, 'category': category, 'section': SECTION, 'items': [], '_expl': False}
            rest = m.group(2)
            meta = it['meta'][len(t) - len(rest):]
            first = dict(it); first['text'] = rest; first['meta'] = meta
            cur['items'].append(first)
            questions.append(cur)
            expected += 1
            continue
    if cur is not None:
        cur['items'].append(it)


def split_markers(line):
    """returns list of (marker_index|None, text, meta)"""
    t, meta = line['text'], line['meta']
    pos = [i for i, ch in enumerate(t) if ch in MARK]
    if not pos:
        return [(None, t, meta, None)]
    def st(a, b):
        seg, m = t[a:b], meta[a:b]
        l = len(seg) - len(seg.lstrip())
        seg2 = seg.strip()
        return seg2, m[l:l + len(seg2)]
    out = []
    if pos[0] > 0:
        out.append((None,) + st(0, pos[0]) + (None,))
    for k, p in enumerate(pos):
        e = pos[k + 1] if k + 1 < len(pos) else len(t)
        out.append((MARK.index(t[p]),) + st(p + 1, e) + (meta[p][0],))
    return out
    return out


KEY = {}
if KIND == 'exam':
    for pg in doc:
        txt = pg.get_text()
        found = re.findall(r'(\d{1,2})\s*\.\s*([①②③④])', txt)
        if len(found) >= 30:
            for a, b in found:
                KEY[int(a)] = MARK.index(b)
result = []
for q in questions:
    items = q['items']
    stem, expl = [], []
    choices = [[] for _ in range(4)]
    green = [0, 0, 0, 0]; total = [0, 0, 0, 0]; mgreen = [0, 0, 0, 0]
    # explanation split
    body = []
    state = 'body'
    for it in items:
        if state == 'body' and it['type'] == 'line' and it['text'].startswith('[해설]'):
            state = 'expl'
            rest = it['text'][4:].strip()
            if rest:
                l2 = dict(it); l2['text'] = rest; l2['meta'] = it['meta'][len(it['text']) - len(rest):]; expl.append(l2)
            continue
        (expl if state == 'expl' else body).append(it)
    # find first choice line
    first = None
    for i, it in enumerate(body):
        if it['type'] == 'line' and it['text'][:1] == '①':
            first = i; break
    markers = []  # (k, page, col, x, cy, order)
    if first is not None:
        for i, it in enumerate(body[first:]):
            if it['type'] != 'line':
                continue
            for ch, (c_, x) in zip(it['text'], it['meta']):
                if ch in MARK:
                    markers.append((MARK.index(ch), it['page'], it['col'], x, it['cy'], first + i))
    # boxes beside a choice marker belong to that choice
    allmk = []
    for it in body:
        if it['type'] == 'line' and not it.get('box'):
            for ch, (c_, x) in zip(it['text'], it['meta']):
                if ch in MARK:
                    allmk.append((MARK.index(ch), it['page'], it['col'], x, it['cy']))
    box_owner = {}
    for it in body:
        if it['type'] == 'line' and it.get('box') and it['box'] not in box_owner:
            bb = it['box_bb']
            cand = [m for m in allmk if m[1] == it['page'] and m[2] == it['col'] and m[3] < bb[0] and bb[1] - 4 <= m[4] <= bb[3] + 4]
            box_owner[it['box']] = cand[0][0] if len(cand) == 1 else None
    boxed = {}
    if any(v is not None for v in box_owner.values()):
        rest = []
        for it in body:
            k = box_owner.get(it.get('box')) if it['type'] == 'line' else None
            if k is not None:
                boxed.setdefault(k, []).append(it)
            else:
                rest.append(it)
        body = rest
        if True:
            first = next((i for i, it in enumerate(body) if it['type'] == 'line' and it['text'][:1] in MARK), first)
    figs_choice = []
    ci = None
    grid = None
    for i, it in enumerate(body):
        if it['type'] == 'fig':
            is_choice = False
            if first is not None:
                if i > first:
                    is_choice = True
                else:
                    for m in markers:
                        if m[1] == it['page'] and m[2] == it['col'] and it['bb'][1] - 6 <= m[4] <= it['bb'][3] + 6:
                            is_choice = True
            if is_choice:
                figs_choice.append(it)
            else:
                stem.append(it)
            continue
        if first is None or i < first:
            stem.append(it); continue
        t = it['text']
        mk = [(MARK.index(ch), m[1]) for ch, m in zip(t, it['meta']) if ch in MARK]
        if len(mk) >= 2:
            mk.sort(key=lambda z: z[1])
            grid = (mk[0][0], mk[-1][0], mk[-1][1] - 3, it['page'], it['col'])
        elif len(mk) == 1:
            grid = None
        if not mk and grid and grid[3] == it['page'] and grid[4] == it['col']:
            li = [i2 for i2, m in enumerate(it['meta']) if m[1] < grid[2]]
            cut = (li[-1] + 1) if li else 0
            parts = []
            for gi, seg, sm in ((grid[0], t[:cut], it['meta'][:cut]), (grid[1], t[cut:], it['meta'][cut:])):
                l0 = len(seg) - len(seg.lstrip())
                seg2 = seg.strip()
                if seg2:
                    parts.append((gi, seg2, sm[l0:l0 + len(seg2)], None, True))
            for gi, txt, meta, _, _ in parts:
                l2 = dict(it); l2['text'] = txt; l2['meta'] = meta; l2['hard'] = True
                l2['x0'] = meta[0][1] if meta else it['x0']
                choices[gi].append(l2)
                vis = [c for c, ch in zip(meta, txt) if ch.strip()]
                green[gi] += sum(1 for c in vis if c[0] == GREEN); total[gi] += len(vis)
            continue
        parts = split_markers(it) if any(ch in t for ch in MARK) else [(None, t, it['meta'], None)]
        for mi, txt, meta, mcol in parts:
            if mi is not None:
                ci = mi
                if mcol == GREEN:
                    mgreen[ci] = 1
            if ci is None:
                continue
            l2 = dict(it); l2['text'] = txt; l2['meta'] = meta
            if txt:
                choices[ci].append(l2)
            vis = [c for c, ch in zip(meta, txt) if ch.strip()]
            green[ci] += sum(1 for c in vis if c[0] == GREEN); total[ci] += len(vis)
    for f in figs_choice:
        fx0, fy0, fx1, fy1 = f['bb']
        same = [m for m in markers if m[1] == f['page'] and m[2] == f['col']]
        cands = [m for m in same if fy0 - 6 <= m[4] <= fy1 + 6]
        pick = None
        if cands:
            left = [m for m in cands if m[3] <= fx0 + 4]
            pick = max(left, key=lambda m: m[3]) if left else min(cands, key=lambda m: abs(m[3] - fx0))
        else:
            above = [m for m in same if m[4] < fy0 + 3]
            if above:
                ymax = max(m[4] for m in above)
                row = [m for m in above if m[4] >= ymax - 4]
                left = [m for m in row if m[3] <= fx0 + 12]
                pick = max(left, key=lambda m: m[3]) if left else min(row, key=lambda m: abs(m[3] - fx0))
            elif markers:
                pick = markers[-1]
        if pick is None:
            stem.append(f)
        else:
            choices[pick[0]].append(f)
    for k, its in boxed.items():
        for it in its:
            choices[k].append(it)
            vis = [c for c, ch in zip(it['meta'], it['text']) if ch.strip()]
            green[k] += sum(1 for c in vis if c[0] == GREEN); total[k] += len(vis)
    for k in range(4):
        choices[k].sort(key=lambda it: (it['page'], it['col'], it['cy']))
    stem.sort(key=lambda it: (it['page'], it['col'], it['cy']))
    key = str(q['num'])
    qd = {'n': q['num'], 'stem': assemble(stem, key)}
    f0 = items[0]
    qd['pos'] = [f0['page'], f0['col'], round(f0.get('y0', 0))]
    if q['category']:
        qd['cat'] = q['category']
    if q['section']:
        qd['sec'] = q['section']
    ch_blocks = []
    for k in range(4):
        bl = assemble(choices[k], key + 'c%d' % (k + 1)) if choices[k] else []
        # merge choice paragraphs into one text when simple
        ch_blocks.append(bl)
    qd['choices'] = ch_blocks
    if KIND == 'topic':
        ratios = [green[k] / total[k] if total[k] else 0 for k in range(4)]
        best = max(range(4), key=lambda k: ratios[k])
        if ratios[best] > 0.4:
            qd['ans'] = best
        elif sum(mgreen) == 1:
            qd['ans'] = mgreen.index(1)
        else:
            qd['ans'] = None
        qd['expl'] = assemble(expl, key + 'e') if expl else []
    else:
        qd['ans'] = KEY.get(q['num'])
    result.append(qd)

json.dump({'id': SID, 'questions': result}, open(os.path.join(OUT, SID + '.json'), 'w'), ensure_ascii=False, indent=1)
missing = [q['n'] for q in result if q['ans'] is None]
nochoice = [q['n'] for q in result if sum(1 for c in q['choices'] if c) < 4]
print(SID, 'questions', len(result), 'missing ans', missing, 'incomplete choices', nochoice,
      'figs', sum(fig_counter.values()))
