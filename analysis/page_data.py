"""리포트 페이지용 압축 데이터(report/data.json)"""
import pandas as pd, json
o=json.load(open('analysis/results.json'))
S=pd.read_csv('data/참고서출고.csv',encoding='utf-8-sig')
def add(m,k): y,mm=map(int,m.split('-')); t=y*12+mm-1+k; return f'{t//12}-{t%12+1:02d}'
ev=[]
for r in o['revision']['rows']:
    ss=S[S.시리즈명==r['시리즈']].groupby('월').출고부수_부.sum()
    pts=[]
    for k in range(-6,4):
        m=add(r['M'],k)
        pts.append(None if m<'2024-01' or m>'2025-12' else round(float(ss.get(m,0))/r['base_act'],2))
    ev.append(dict(s=r['시리즈'],M=r['M'],pts=pts))
D=dict(monthly=[dict(m=x['월'],ship=int(x['ship']),ret=int(x['ret'])) for x in o['monthly']],
 partners=[dict(n=p['거래처명'],ship=int(p['ship']),ret=int(p['ret']),rate=round(p['rate'],4),rev=round(p['rev']/1e8,2),netrev=round(p['netrev']/1e8,2),sr=round(p['sr'],4),r1=p['rank_ship'],r2=p['rank_net']) for p in o['partners']],
 hs=[dict(m=x['월'],ship=int(x['ship']),ret=int(x['ret']),rate=round(x['rate'],4),cum=round(x['cum_rate'],4)) for x in o['high']['monthly']],
 ev=ev,
 share=[dict(n=k,win=round(v,4),out=round(o['revision']['outside_partner_share'].get(k,0),4)) for k,v in sorted(o['revision']['by_partner_share'].items(),key=lambda x:-x[1])],
 sr={k:{m:round(v,4) for m,v in d.items()} for k,d in o['supply']['monthly'].items()},
 reasons=o['reason']['total'],
 pabon=[dict(b=b['브랜드'],rs=round(b['reason_share'],4),ss=round(b['ship_share'],4),c=round(b['conc'],2)) for b in o['reason']['pabon_brand']])
json.dump(D,open('report/data.json','w'),ensure_ascii=False)
print(len(json.dumps(D,ensure_ascii=False)))
for e in ev: print(e)
