"""report/src.html + 문서 md + data.json → report/참고서_반품진단_리포트.html"""
import json, pathlib
R=pathlib.Path('report'); s=(R/'src.html').read_text()
for k,f in [('%%DOC1%%','doc1_교육모듈.md'),('%%DOC2%%','doc2_협의공문.md'),('%%CHECK%%','check_검산가정.md')]:
    t=(R/f).read_text(); assert '</script' not in t; s=s.replace(k,t)
s=s.replace('%%DATA%%',json.dumps(json.load(open(R/'data.json')),ensure_ascii=False))
(R/'참고서_반품진단_리포트.html').write_text(s); print(len(s))
