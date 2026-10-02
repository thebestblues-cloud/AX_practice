"""참고서 출고·반품 진단 분석 — Part 1 전 절차 계산 (결과: analysis/results.json)"""
import pandas as pd, numpy as np, json
S=pd.read_csv('data/참고서출고.csv',encoding='utf-8-sig')
R=pd.read_csv('data/반품입고.csv',encoding='utf-8-sig')
M=pd.read_csv('data/도서마스터.csv',encoding='utf-8-sig')
LOG=1400  # 반품 1부당 왕복 물류비(가정)
months=sorted(S.월.unique()); NM=len(months); LAST=months[-1]
L12=[m for m in months if m>='2025-01']
S['출고액']=S.출고부수_부*S.공급단가_원부
S=S.merge(M[['시리즈명','정가_원','제작원가_원부','과목','학년']],on='시리즈명')
S['정가액']=S.출고부수_부*S.정가_원
# 반품 단가: (거래처×시리즈) 출고 가중평균 공급단가
ps=S.groupby(['거래처명','시리즈명']).agg(q=('출고부수_부','sum'),a=('출고액','sum'))
ps['단가']=ps.a/ps.q
R=R.merge(ps['단가'].reset_index(),on=['거래처명','시리즈명']).merge(M[['시리즈명','제작원가_원부','정가_원']],on='시리즈명')
R['반품액']=R.반품부수_부*R.단가
out={}
# ---- 2 전사
T=dict(ship=int(S.출고부수_부.sum()),ret=int(R.반품부수_부.sum()),rev=float(S.출고액.sum()),retamt=float(R.반품액.sum()))
T['net']=T['ship']-T['ret']; T['rate']=T['ret']/T['ship']; T['netrev']=T['rev']-T['retamt']
T['retamt_ann_avg']=T['retamt']/NM*12; T['retamt_ann_l12']=float(R[R.월.isin(L12)].반품액.sum())
T['rev_l12']=float(S[S.월.isin(L12)].출고액.sum()); T['rev_ann_avg']=T['rev']/NM*12
T['rate_y']={y:dict(ship=int(S[S.월.str[:4]==y].출고부수_부.sum()),ret=int(R[R.월.str[:4]==y].반품부수_부.sum())) for y in ['2024','2025']}
out['total']=T
mon=pd.DataFrame({'ship':S.groupby('월').출고부수_부.sum(),'ret':R.groupby('월').반품부수_부.sum(),'rev':S.groupby('월').출고액.sum(),'retamt':R.groupby('월').반품액.sum()}).fillna(0)
out['monthly']=mon.reset_index().rename(columns={'index':'월'}).to_dict('records')
# ---- 1 lag
first_s=S.groupby(['거래처명','시리즈명']).월.min(); first_r=R.groupby(['거래처명','시리즈명']).월.min()
def mi(m): y,mm=map(int,m.split('-')); return y*12+mm
lag=(first_r.map(mi)-first_s.reindex(first_r.index).map(mi))
out['lag']=dict(min=int(lag.min()),median=float(lag.median()),mean=float(lag.mean()),max=int(lag.max()),first_ret_month=R.월.min(),first_ship_month=S.월.min())
out['check']=dict(S_rows=len(S),R_rows=len(R),M_rows=len(M),partners=S.거래처명.nunique(),ser_ship=S.시리즈명.nunique(),ser_ret=R.시리즈명.nunique(),
  no_ship=sorted(set(M.시리즈명)-set(S.시리즈명)),pairs_S=int(len(ps)),pairs_R=int(R.groupby(['거래처명','시리즈명']).ngroups))
# ---- 3 거래처
P=pd.DataFrame({'ship':S.groupby('거래처명').출고부수_부.sum(),'ret':R.groupby('거래처명').반품부수_부.sum(),
  'rev':S.groupby('거래처명').출고액.sum(),'retamt':R.groupby('거래처명').반품액.sum(),'list':S.groupby('거래처명').정가액.sum()}).fillna(0)
P['net']=P.ship-P.ret; P['rate']=P.ret/P.ship; P['netrev']=P.rev-P.retamt; P['sr']=P.rev/P['list']
P=P.sort_values('rev',ascending=False)
P['rank_ship']=P.rev.rank(ascending=False).astype(int); P['rank_net']=P.netrev.rank(ascending=False).astype(int)
P['move']=P.rank_ship-P.rank_net
out['partners']=P.reset_index().rename(columns={'index':'거래처명'}).to_dict('records')
H=P.rate.idxmax(); h=P.loc[H]
ex=P.drop(H); ex_rate=ex.ret.sum()/ex.ship.sum(); inc_rate=T['rate']
excess=h.ret-h.ship*ex_rate; hp=h.rev/h.ship
hi=dict(name=H,rate=h.rate,ex_rate=ex_rate,inc_rate=inc_rate,mult_ex=h.rate/ex_rate,mult_inc=h.rate/inc_rate,excess=excess,unitprice=hp,
  excess_amt=excess*hp,excess_amt_ann=excess*hp/NM*12)
# 단순평균(거래처 반품률의 산술평균) 참고
hi['ex_rate_simple']=ex.rate.mean()
hm=pd.DataFrame({'ship':S[S.거래처명==H].groupby('월').출고부수_부.sum(),'ret':R[R.거래처명==H].groupby('월').반품부수_부.sum()}).reindex(months).fillna(0)
hm['rate']=hm.ret/hm.ship; hm['cum_rate']=hm.ret.cumsum()/hm.ship.cumsum()
hi['monthly']=hm.reset_index().rename(columns={'index':'월'}).to_dict('records')
# 연속 >전체평균 검산
hi['months_over100']=[r['월'] for r in hi['monthly'] if r['ship']>0 and r['rate']>1]
# 거래처별 월반품률 비교용 : 각 월 H 월반품률 > 타사 합산 월반품률 연속 개월
oth=pd.DataFrame({'ship':S[S.거래처명!=H].groupby('월').출고부수_부.sum(),'ret':R[R.거래처명!=H].groupby('월').반품부수_부.sum()}).reindex(months).fillna(0)
flag=(hm.ret/hm.ship>oth.ret/oth.ship)
hi['months_above_others']=int(flag.sum()); 
run=0;best=0;bestend=None
for m,f in flag.items():
    run=run+1 if f else 0
    if run>best: best=run;bestend=m
hi['longest_run_above_others']=best; hi['longest_run_end']=bestend
hi['reason']=R[R.거래처명==H].groupby('반품사유').반품부수_부.sum().to_dict()
out['high']=hi
# ---- 4 개정판
M['rev']=M.개정판출간월.fillna('')
inrng=M[(M.rev>=months[0])&(M.rev<=LAST)]
outrng=M[(M.rev!='')&~M.시리즈명.isin(inrng.시리즈명)]
def add(m,k): y,mm=map(int,m.split('-')); t=y*12+mm-1+k; return f'{t//12}-{t%12+1:02d}'
rows=[];wins=[]
for _,b in inrng.sort_values('rev').iterrows():
    sname=b.시리즈명; Mm=b.rev; ss=S[S.시리즈명==sname]; rr=R[R.시리즈명==sname]
    w=[add(Mm,-3),add(Mm,-2),add(Mm,-1)]; post=[add(Mm,1),add(Mm,2),add(Mm,3)]
    q=[int(ss[ss.월==x].출고부수_부.sum()) for x in w]
    outside=ss[~ss.월.isin(w)]
    base_all=outside.출고부수_부.sum()/(NM-3)   # 창 밖 전체 월평균(0출고 월 포함)
    base_act=outside.groupby('월').출고부수_부.sum().mean() # 출고 있던 달만
    pre=[add(Mm,-6),add(Mm,-5),add(Mm,-4)]; pre_in=[x for x in pre if x in months]
    base_pre=ss[ss.월.isin(pre)].출고부수_부.sum()/len(pre_in) if pre_in else None
    pr=rr[rr.월.isin(post)]
    rows.append(dict(시리즈=sname,M=Mm,m3=q[0],m2=q[1],m1=q[2],win=sum(q),base_all=base_all,base_act=base_act,base_pre=base_pre,pre_n=len(pre_in),
      mult_all=sum(q)/3/base_all,mult_act=sum(q)/3/base_act,post_ret=int(pr.반품부수_부.sum()),win_rate=pr.반품부수_부.sum()/sum(q),
      repl=int(pr[pr.반품사유=='개정판교체'].반품부수_부.sum()),cost=int(b.제작원가_원부),
      ships_months=int(ss.월.nunique()),avg_ship_month=float(ss.groupby('월').출고부수_부.sum().mean()),
      reasons=pr.groupby('반품사유').반품부수_부.sum().to_dict()))
    wins.append(ss[ss.월.isin(w)].assign(M=Mm))
RV=pd.DataFrame(rows); RV['disp']=RV.repl*RV.cost
W=pd.concat(wins)
wp=W.groupby('거래처명').출고부수_부.sum().sort_values(ascending=False)
# 창 출고 거래처별 vs 창 밖 거래처 점유율
outside_all=pd.concat([S[(S.시리즈명==r['시리즈'])&~S.월.isin([add(r['M'],-3),add(r['M'],-2),add(r['M'],-1)])] for r in rows])
op=outside_all.groupby('거래처명').출고부수_부.sum()
out['revision']=dict(rows=rows,excluded=outrng[['시리즈명','rev']].values.tolist(),
  win_total=int(RV.win.sum()),post_total=int(RV.post_ret.sum()),win_rate=RV.post_ret.sum()/RV.win.sum(),mult_vs_total=(RV.post_ret.sum()/RV.win.sum())/T['rate'],
  repl_total=int(RV.repl.sum()),disp_total=int(RV.disp.sum()),
  reasons=pd.DataFrame([r['reasons'] for r in rows]).fillna(0).sum().to_dict(),
  by_partner={k:int(v) for k,v in wp.items()},by_partner_share={k:v/wp.sum() for k,v in wp.items()},
  outside_partner_share={k:v/op.sum() for k,v in op.items()},
  win_mult_all=RV.win.sum()/3/RV.base_all.sum(),win_mult_act=RV.win.sum()/3/RV.base_act.sum())
# 창 반품 거래처별 (개정판교체)
post_rows=[]
for r in rows:
    post=[add(r['M'],k) for k in (1,2,3)]
    post_rows.append(R[(R.시리즈명==r['시리즈'])&R.월.isin(post)])
PR=pd.concat(post_rows)
out['revision']['post_by_partner']=PR.groupby('거래처명').반품부수_부.sum().to_dict()
out['revision']['repl_by_partner']=PR[PR.반품사유=='개정판교체'].groupby('거래처명').반품부수_부.sum().to_dict()
# 개정판교체 annual split
RR=R[R.반품사유=='개정판교체']
out['revision']['repl_by_year']=RR.groupby(RR.월.str[:4]).apply(lambda d:(d.반품부수_부*d.제작원가_원부).sum()).to_dict()
out['revision']['repl_qty_by_year']=RR.groupby(RR.월.str[:4]).반품부수_부.sum().to_dict()
# 데이터 이후 출간 시리즈 중 창이 데이터에 들어오는 것
fut=[]
for _,b in M[M.rev>LAST].iterrows():
    w=[add(b.rev,-3),add(b.rev,-2),add(b.rev,-1)]; win_in=[x for x in w if x in months]
    ss=S[S.시리즈명==b.시리즈명]
    outside=ss[~ss.월.isin(win_in)]
    base_all=outside.출고부수_부.sum()/(NM-len(win_in)); base_act=outside.groupby('월').출고부수_부.sum().mean()
    q={x:int(ss[ss.월==x].출고부수_부.sum()) for x in win_in}
    wsum=sum(q.values())
    fut.append(dict(시리즈=b.시리즈명,M=b.rev,win_in=win_in,q=q,wsum=wsum,base_all=base_all,base_act=base_act,
      mult_all=(wsum/len(win_in))/base_all if win_in else None,mult_act=(wsum/len(win_in))/base_act if win_in else None,cost=int(b.제작원가_원부),
      exp_ret=wsum*out['revision']['win_rate'],
      repl_ratio=RV.repl.sum()/RV.post_ret.sum(),
      by_partner=ss[ss.월.isin(win_in)].groupby('거래처명').출고부수_부.sum().to_dict(),
      exp_ret_rate_now=float(R[R.시리즈명==b.시리즈명].반품부수_부.sum()/ss.출고부수_부.sum())))
for f in fut:
    f['exp_repl']=f['exp_ret']*f['repl_ratio']; f['exp_disp']=f['exp_repl']*f['cost']; f['exp_log']=f['exp_ret']*LOG
out['future']=fut
# ---- 5 공급률
S['y']=S.월.str[:4]
SR=S.groupby(['거래처명','y']).apply(lambda d:d.출고액.sum()/d.정가액.sum()).unstack()
SR['d']=(SR['2025']-SR['2024'])*100
mf=S.groupby(['거래처명','월']).apply(lambda d:d.출고액.sum()/d.정가액.sum()).unstack()
first=mf.apply(lambda r:r.dropna().iloc[0],axis=1); last=mf.apply(lambda r:r.dropna().iloc[-1],axis=1)
fm=mf.apply(lambda r:r.dropna().index[0],axis=1); lm=mf.apply(lambda r:r.dropna().index[-1],axis=1)
span=lm.map(mi)-fm.map(mi)
SR['fl']=(last-first)*100; SR['fl_ann']=SR.fl/span*12; SR['span']=span
SR['list_l12']=S[S.y=='2025'].groupby('거래처명').정가액.sum()
SR['rev_l12']=S[S.y=='2025'].groupby('거래처명').출고액.sum()
# half-year
S['h']=S.월.map(lambda m: m[:4]+('H1' if int(m[5:])<=6 else 'H2'))
SRh=S.groupby(['거래처명','h']).apply(lambda d:d.출고액.sum()/d.정가액.sum()).unstack()
out['supply']=dict(table=SR.reset_index().to_dict('records'),half=SRh.reset_index().to_dict('records'),monthly={k:v.dropna().to_dict() for k,v in mf.iterrows()})
# ---- 6 반품사유
rs=R.groupby('반품사유').반품부수_부.sum().sort_values(ascending=False)
out['reason']=dict(total=rs.to_dict(),amt=R.groupby('반품사유').반품액.sum().to_dict())
R['브랜드']=R.시리즈명.str.split().str[0]; S['브랜드']=S.시리즈명.str.split().str[0]
def conc(reason):
    a=R[R.반품사유==reason]
    sh=a.groupby('시리즈명').반품부수_부.sum()/R.groupby('시리즈명').반품부수_부.sum()
    br=pd.DataFrame({'reason':a.groupby('브랜드').반품부수_부.sum(),'ret':R.groupby('브랜드').반품부수_부.sum(),'ship':S.groupby('브랜드').출고부수_부.sum()}).fillna(0)
    br['reason_share']=br.reason/br.reason.sum(); br['ship_share']=br.ship/br.ship.sum(); br['conc']=br.reason_share/br.ship_share
    br['in_series_share']=br.reason/br.ret
    srs=pd.DataFrame({'reason':a.groupby('시리즈명').반품부수_부.sum(),'ret':R.groupby('시리즈명').반품부수_부.sum()}).fillna(0)
    srs['share']=srs.reason/srs.ret; srs=srs[srs.reason>0].sort_values('share',ascending=False)
    return br.sort_values('conc',ascending=False),srs
br,srs=conc('파본')
pb=R[R.반품사유=='파본']
pbd=pb.groupby('시리즈명').agg(q=('반품부수_부','sum'),c=('제작원가_원부','first')); pbd['disp']=pbd.q*pbd.c
out['reason']['pabon_brand']=br.reset_index().to_dict('records'); out['reason']['pabon_series']=srs.reset_index().to_dict('records')
out['reason']['pabon_disp']=int(pbd.disp.sum()); out['reason']['pabon_qty']=int(pbd.q.sum())
out['reason']['pabon_disp_by_brand']=pb.assign(d=pb.반품부수_부*pb.제작원가_원부).groupby('브랜드').d.sum().to_dict()
out['reason']['pabon_by_year']=pb.assign(d=pb.반품부수_부*pb.제작원가_원부).groupby(pb.월.str[:4]).d.sum().to_dict()
# 파본 동반 패턴: 실전만점 반품 행 중 파본이 같은 (월,거래처,시리즈)에 동반되는 비율
sj=R[R.브랜드=='실전만점']; g=sj.groupby(['월','거래처명','시리즈명'])
out['reason']['sj_events']=int(g.ngroups); out['reason']['sj_events_with_pabon']=int(g.apply(lambda d:(d.반품사유=='파본').any()).sum())
out['reason']['pabon_ratio_in_sj_events']=float(sj[sj.반품사유=='파본'].반품부수_부.sum()/sj.반품부수_부.sum())
nonsj_pabon=pb[pb.브랜드!='실전만점']
out['reason']['pabon_nonsj']=nonsj_pabon[['월','거래처명','시리즈명','반품부수_부']].to_dict('records')
out['reason']['by_reason_series']=R.groupby(['반품사유','브랜드']).반품부수_부.sum().unstack(fill_value=0).to_dict()
out['reason']['brand_ship']=S.groupby('브랜드').출고부수_부.sum().to_dict()
out['reason']['brand_ret']=R.groupby('브랜드').반품부수_부.sum().to_dict()
out['reason']['brand_rev']=S.groupby('브랜드').출고액.sum().to_dict()
json.dump(out,open('analysis/results.json','w'),ensure_ascii=False,indent=1,default=lambda o: o.item() if hasattr(o,'item') else str(o))
print(json.dumps({k:out[k] for k in ['total','lag','check']},ensure_ascii=False,indent=1,default=str))
