"""Resolve U+2063 wrap-join markers into '' or ' ' using corpus statistics.

Corpus = PDF raw text lines + extracted texts split at the markers + hand-written explanations,
so a wrap join never counts as evidence for itself.
"""
import re, os, json, glob

MK = '⁣'
PUNCT = '.,?!:;)]}’”\'"'
PARTICLE_END = set('은는을를의에와과로서며고면도만한된인할될던여게지니까나요다')
BOUND = set('수것등및때더중안곳줄뿐데후전')
CONT_START = set('을를이가은는의에와과로도만며고서다요한된할함적성들화시하되')


def build_corpus(texts):
    segs = []
    for t in texts:
        for seg in re.split(r'[\n' + MK + ']', t):
            seg = seg.strip()
            if seg:
                segs.append(seg)
    return '\n'.join(segs)


def count(corpus, s):
    return corpus.count(s) if s else 0


def decide(corpus, a, b):
    """returns (sep, how)"""
    a2 = a.rstrip(PUNCT) if a.rstrip(PUNCT) else a
    b2 = re.split(r'[\s' + re.escape(PUNCT) + ']', b)[0] or b
    levels = [(a, b2), (a2[-4:], b2[:4]), (a2[-3:], b2[:3]), (a2[-2:], b2[:2])]
    for x, y in levels:
        if len(x) < 1 or len(y) < 1:
            continue
        if len(x) + len(y) < 3:
            continue
        cs, cj = count(corpus, x + ' ' + y), count(corpus, x + y)
        if cs or cj:
            if cs >= 2 * cj and cs > cj:
                return ' ', f'corpus {x}|{y} sp={cs} jn={cj}'
            if cj >= 2 * cs and cj > cs:
                return '', f'corpus {x}|{y} sp={cs} jn={cj}'
    # heuristics
    if a.endswith('→') or b.startswith('→'):
        return ' ', 'heur arrow'
    if re.match(r'[가-힣]', a[-1:] or '') and re.match(r'[A-Z]', b[:1] or ''):
        return ' ', 'heur hangul+Latin'
    if a.endswith('고') and b2.startswith('자'):
        return '', 'heur -고자'
    if len(b2) == 1 and re.match(r'[가-힣]', b2) and b2 not in BOUND:
        return '', 'heur single-syllable tail'
    if a and a[-1] in PUNCT and b and re.match(r'[가-힣A-Za-z0-9(]', b[0]):
        return ' ', 'heur punct'
    if b and b[0] in CONT_START and not (a and a[-1] in PUNCT):
        return '', 'heur cont-start'
    if a and a[-1] in PARTICLE_END and len(a) >= 2:
        return ' ', 'heur particle-end'
    if re.match(r'[A-Za-z0-9]', a[-1:] or '') and re.match(r'[가-힣]', b[:1] or ''):
        return '', 'heur latin+hangul'
    return '', 'default-join'


def resolve_text(corpus, s, log, where):
    if MK not in s:
        return s
    parts = s.split(MK)
    out = parts[0]
    for nxt in parts[1:]:
        a = re.split(r'\s', out)[-1]
        b = re.split(r'\s', nxt)[0] if nxt else ''
        sep, how = decide(corpus, a, b)
        log.append((where, a, b, sep, how))
        out = out + sep + nxt
    return out


def resolve_data(data, extra_texts):
    texts = list(extra_texts)
    for qs in data['q'].values():
        for q in qs:
            for part in [q['stem'], q['e']] + q['ch']:
                for b in part:
                    if 's' in b:
                        texts.append(b['s'])
    corpus = build_corpus(texts)
    log = []
    for sid, qs in data['q'].items():
        for q in qs:
            for name, part in [('stem', q['stem']), ('e', q['e'])] + [('ch%d' % (i + 1), c) for i, c in enumerate(q['ch'])]:
                for b in part:
                    if 's' in b:
                        b['s'] = resolve_text(corpus, b['s'], log, f'{sid}/{q["n"]}/{name}')
    return log
