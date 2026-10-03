# 참고서 출고·반품 진단

- `data/` 원자료 3종(참고서출고·반품입고·도서마스터) + 분석 프롬프트
- `analysis/analyze.py`·`synth.py` Part 1 계산 → `results.json`
- `analysis/검산_워크북.xlsx` Excel 수식 검산(40항목, Python 값과 일치)
- `report/반품진단_핵심브리핑.html` 핵심 요약 단일 HTML(카드 클릭 시 상세 드로어)
- `report/참고서_반품진단_리포트.html` 시각화 리포트(Part 1 + 문서 1·2 탭)
- `report/doc1_교육모듈.md/.docx` 사내 교육 모듈 · `report/doc2_협의공문.md/.docx` 거래처 협의 공문

재생성: `python3 analysis/analyze.py && python3 analysis/synth.py && python3 analysis/page_data.py && python3 report/build.py && python3 report/build_brief.py`

## 반품 모니터링 대시보드(샘플 데이터 시제품)
- `dashboard/engine.js` 계산 모듈(시차곡선·예측·군집·공헌이익·손익분기·경보) — `node dashboard/test_engine.js`로 검증
- `dashboard/src.html` 화면 → `python3 dashboard/build.py` → `dashboard/반품모니터링_대시보드.html`(claude.ai 아티팩트, db·user 기능)
- `dashboard/make_seed.py` 샘플 CSV → 월별 저장 문서, `dashboard/검산_공헌이익.xlsx` 공헌이익·손익분기 Excel 검산
