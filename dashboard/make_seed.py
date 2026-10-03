"""샘플 CSV → 대시보드 db 문서(JSON). months/{ym}, meta/master, meta/params"""
import pandas as pd, json
S=pd.read_csv('../data/참고서출고.csv',encoding='utf-8-sig');R=pd.read_csv('../data/반품입고.csv',encoding='utf-8-sig');M=pd.read_csv('../data/도서마스터.csv',encoding='utf-8-sig')
docs={}
for ym in sorted(set(S.월)|set(R.월)):
    s=S[S.월==ym];r=R[R.월==ym]
    docs[ym]={'ym':ym,'ship':s[['거래처명','시리즈명','출고부수_부','공급단가_원부']].values.tolist(),'ret':r[['거래처명','시리즈명','반품부수_부','반품사유']].values.tolist(),'source':'샘플 CSV 초기 등록'}
master=M.fillna('')[['시리즈명','과목','학년','정가_원','제작원가_원부','개정판출간월']].values.tolist()
json.dump({'months':docs,'master':master},open('seed.json','w'),ensure_ascii=False,default=int)
print(len(docs),max(len(json.dumps(d,ensure_ascii=False)) for d in docs.values()))
