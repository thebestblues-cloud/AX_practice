"""report/src_brief.html + src.html 차트 함수 + 문서 → report/반품진단_핵심브리핑.html (단일 파일)"""
import json, pathlib
R=pathlib.Path('report'); src=(R/'src.html').read_text(); s=(R/'src_brief.html').read_text()
a=src.index('function el('); b=src.index('function renderAll')
s=s.replace('%%CHARTJS%%',src[a:b])
for k,f in [('%%DOC1%%','doc1_교육모듈.md'),('%%DOC2%%','doc2_협의공문.md'),('%%CHECK%%','check_검산가정.md')]:
    t=(R/f).read_text(); assert '</script' not in t; s=s.replace(k,t)
s=s.replace('%%DATA%%',json.dumps(json.load(open(R/'data.json')),ensure_ascii=False))
(R/'반품진단_핵심브리핑.html').write_text(s); print(len(s))
