import json, difflib, re, sys
M='①②③④'
def txt(bs): return ' '.join(b.get('s','') for b in bs if b['t']!='img')
def norm(s): return re.sub(r'[\s‘’“”\'"·ㆍ.,()?]','',s)
src=[]
for sid in ['t01','t02','t03','t04','t05','t06']:
    for q in json.load(open(sid+'.json'))['questions']:
        if q['ans'] is None: continue
        src.append((sid,q))
exams=['y2023_1','y2023_2','y2024_1','y2024_2','y2025_1','y2025_2','m2026_01','m2026_02','m2026_03']
res={}
tot=0;hit=0
for e in exams:
    for q in json.load(open(e+'.json'))['questions']:
        tot+=1
        st=norm(txt(q['stem'])); ans=norm(txt(q['choices'][q['ans']]))
        best=None
        for sid,s in src:
            s_st=norm(txt(s['stem']))
            r=difflib.SequenceMatcher(None,st,s_st).quick_ratio()
            if r<0.8: continue
            r=difflib.SequenceMatcher(None,st,s_st).ratio()
            if r<0.85: continue
            s_ans=norm(txt(s['choices'][s['ans']]))
            ra=difflib.SequenceMatcher(None,ans,s_ans).ratio() if (ans or s_ans) else 1
            if ra<0.85: continue
            sc=r+ra
            if best is None or sc>best[0]: best=(sc,sid,s['n'],bool(s.get('expl')))
        if best:
            hit+=1; res['%s/%d'%(e,q['n'])]=best[1:]
print('matched',hit,'of',tot,'with expl',sum(1 for v in res.values() if v[2]))
json.dump(res,open('matches.json','w'),ensure_ascii=False,indent=0)
