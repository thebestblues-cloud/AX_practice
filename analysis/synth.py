"""절차 7 종합 + Part 2 인용값(손익분기·문항·제안조건) 계산 → analysis/results.json 갱신"""
import pandas as pd, json
o=json.load(open('analysis/results.json'))
S=pd.read_csv('data/참고서출고.csv',encoding='utf-8-sig'); R=pd.read_csv('data/반품입고.csv',encoding='utf-8-sig'); M=pd.read_csv('data/도서마스터.csv',encoding='utf-8-sig')
S=S.merge(M,on='시리즈명'); R=R.merge(M,on='시리즈명')
LOG=1400; NM=24; T=o['total']; X={}
# 기본 집계
L12=R.월>='2025-01'
X['log_24']=T['ret']*LOG; X['log_ann_avg']=X['log_24']/NM*12; X['log_l12']=int(R[L12].반품부수_부.sum())*LOG
disp=R[R.반품사유.isin(['개정판교체','파본'])]; disp_amt=(disp.반품부수_부*disp.제작원가_원부)
X['disp_24']=int(disp_amt.sum()); X['disp_ann_avg']=X['disp_24']/2; X['disp_l12']=int(disp_amt[disp.월>='2025-01'].sum())
X['disp_qty']=int(disp.반품부수_부.sum())
sup=pd.DataFrame(o['supply']['table']).set_index('거래처명'); dec=sup[sup.d<-1.0]
X['decl_partners']=list(dec.index)
X['erosion_a']=float((dec.list_l12*(-dec.d)/100).sum()); X['erosion_b']=float((dec.list_l12*(-dec.fl_ann)/100).sum())
X['erosion_a_by']={k:float(v) for k,v in (dec.list_l12*(-dec.d)/100).items()}; X['erosion_b_by']={k:float(v) for k,v in (dec.list_l12*(-dec.fl_ann)/100).items()}
X['cash_ann_avg']=X['log_ann_avg']+X['disp_ann_avg']+X['erosion_a']; X['cash_l12']=X['log_l12']+X['disp_l12']+X['erosion_a']
# 회수 가능분: 한솔 초과반품 / 밀어내기 초과반품 / 중복
h=o['high']; H=h['name']; rv=o['revision']
win=rv['win_total']; post=rv['post_total']
ref_win=(T['ret']-post)/(T['ship']-win)  # 개정판 창 외 반품률(자기 제외 개념)
X['ref_win']=ref_win; X['push_excess']=post-win*ref_win
hs_post=rv['post_by_partner'][H]; hs_win=rv['by_partner'][H]
X['hs_post']=hs_post; X['hs_win']=hs_win
X['overlap']=hs_post-hs_win*ref_win  # 한솔 창 구간 초과반품 = 두 집합 공통
X['hs_excess']=h['excess']
X['dedup']=X['hs_excess']+X['push_excess']-X['overlap']
# 단가: 초과 반품 매출 환산 — 한솔은 한솔 평균공급단가, 밀어내기는 창 구간 반품액/반품부수
# 창 반품 단가(거래처×시리즈 가중평균)
ps=S.assign(a=S.출고부수_부*S.공급단가_원부).groupby(['거래처명','시리즈명']).agg(q=('출고부수_부','sum'),a=('a','sum')); ps['u']=ps.a/ps.q
def add(m,k): y,mm=map(int,m.split('-')); t=y*12+mm-1+k; return f'{t//12}-{t%12+1:02d}'
pr=pd.concat([R[(R.시리즈명==r['시리즈'])&R.월.isin([add(r['M'],k) for k in (1,2,3)])] for r in rv['rows']])
pr=pr.merge(ps['u'].reset_index(),on=['거래처명','시리즈명'])
X['post_unit']=float((pr.반품부수_부*pr.u).sum()/pr.반품부수_부.sum())
X['post_cost_unit']=float((pr.반품부수_부*pr.제작원가_원부).sum()/pr.반품부수_부.sum())
repl_ratio=rv['repl_total']/post; X['repl_ratio']=repl_ratio
# 회수가능 금액(연, 24개월 평균 ÷2)
X['hs_excess_rev_ann']=h['excess_amt_ann']
X['hs_excess_cash_ann']=h['excess']*LOG/2  # 물류비만 (폐기 비중은 별도)
hs_disp_share=(h['reason'].get('개정판교체',0)+h['reason'].get('파본',0))/sum(h['reason'].values())
hsS=S[S.거래처명==H]; hs_cost=float((hsS.출고부수_부*hsS.제작원가_원부).sum()/hsS.출고부수_부.sum())
X['hs_disp_share']=hs_disp_share; X['hs_cost']=hs_cost
X['hs_excess_cash_ann']=h['excess']*(LOG+hs_disp_share*hs_cost)/2
X['push_excess_rev_ann']=X['push_excess']*X['post_unit']/2
X['push_excess_cash_ann']=X['push_excess']*(LOG+repl_ratio*X['post_cost_unit'])/2
hs_unit=h['unitprice']
X['overlap_rev_ann']=X['overlap']*hs_unit/2  # 중복분은 한솔 부수 → 한솔 평균 공급단가
X['overlap_cash_ann']=X['overlap']*(LOG+repl_ratio*X['post_cost_unit'])/2
X['recov_rev_ann']=X['hs_excess_rev_ann']+X['push_excess_rev_ann']-X['overlap_rev_ann']
X['recov_cash_ann']=X['hs_excess_cash_ann']+X['push_excess_cash_ann']-X['overlap_cash_ann']
# 한솔: 창 제외 반품률
X['hs_rate_nowin']=(h['excess']*0+ (sum(h['reason'].values())-hs_post))/(1014080-hs_win)
# 손익분기 반품률 (전사 / 한솔)
p_all=T['rev']/T['ship']; c_all=float((S.출고부수_부*S.제작원가_원부).sum()/S.출고부수_부.sum())
d_all=X['disp_qty']/T['ret']
X.update(p_all=p_all,c_all=c_all,d_all=d_all)
X['be_all']=(p_all-c_all)/(p_all-c_all+LOG+d_all*c_all)
X['be_hs']=(hs_unit-hs_cost)/(hs_unit-hs_cost+LOG+hs_disp_share*hs_cost)
def contrib(p,c,r,d): return (1-r)*(p-c)-r*(LOG+d*c)
X['contrib_hs_now']=contrib(hs_unit,hs_cost,h['rate'],hs_disp_share)
X['contrib_hs_ex']=contrib(hs_unit,hs_cost,h['ex_rate'],hs_disp_share)
X['contrib_all']=contrib(p_all,c_all,T['rate'],d_all)
for cap in (0.20,0.25,0.30):
    X[f'contrib_hs_{int(cap*100)}']=contrib(hs_unit,hs_cost,cap,hs_disp_share)
# 제안 조건: 한솔 연간 출고 (24개월 평균 ÷2)
hs_ship_ann=1014080/2; X['hs_ship_ann']=hs_ship_ann
X['hs_list_l12']=float(sup.loc[H,'list_l12']); X['hs_rev_l12']=float(sup.loc[H,'rev_l12'])
X['hs_ship_l12']=int(hsS[hsS.월>='2025-01'].출고부수_부.sum()); X['hs_ret_l12']=int(R[(R.거래처명==H)&L12].반품부수_부.sum())
for cap in (0.20,0.25,0.30):
    red=(h['rate']-cap)*hs_ship_ann
    X[f'save_{int(cap*100)}']=dict(copies=red,log=red*LOG,disp=red*hs_disp_share*hs_cost,tot=red*(LOG+hs_disp_share*hs_cost))
X['incentive_05']=X['hs_list_l12']*0.005
# 한솔 거래 기간/건수
X['hs_first']=hsS.월.min(); X['hs_last']=hsS.월.max(); X['hs_ship_rows']=len(hsS); X['hs_ret_rows']=int((R.거래처명==H).sum())
X['hs_series']=int(hsS.시리즈명.nunique()); X['hs_months_shipped']=int(hsS.월.nunique())
# 모듈4 문항 데이터
q={}
b=S[S.거래처명=='북웨이브몰']; br=R[R.거래처명=='북웨이브몰']
q['a']=dict(ship=int(b.출고부수_부.sum()),ret=int(br.반품부수_부.sum()),rev=int((b.출고부수_부*b.공급단가_원부).sum()))
q['a']['retamt']=float(pd.DataFrame(o['partners']).set_index('거래처명').loc['북웨이브몰','retamt'])
# (b) 실제 행
rowb=R[(R.월=='2024-06')&(R.거래처명=='글벗문고')&(R.시리즈명=='실전만점 수학 고1')]
q['b']=rowb[['반품사유','반품부수_부','제작원가_원부']].to_dict('records')
# (d) 실전만점 수학 고2
s2=S[S.시리즈명=='실전만점 수학 고2']; mavg=s2.groupby('월').출고부수_부.sum().mean()
p2=float((s2.출고부수_부*s2.공급단가_원부).sum()/s2.출고부수_부.sum()); c2=6730
r=rv['win_rate']
q['d']=dict(months=int(s2.월.nunique()),total=int(s2.출고부수_부.sum()),mavg=mavg,p=p2,c=c2,r=r,d=repl_ratio,
  per_copy=contrib(p2,c2,r,repl_ratio),per_copy_normal=contrib(p2,c2,T['rate'],d_all))
# (e) 파본 비중 상위
X['q']=q
o['synth']=X
json.dump(o,open('analysis/results.json','w'),ensure_ascii=False,indent=1,default=lambda v: v.item() if hasattr(v,'item') else str(v))
for k,v in X.items(): print(k,v)
