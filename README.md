# 참고서 출고·반품 진단

- `data/` 원자료 3종(참고서출고·반품입고·도서마스터) + 분석 프롬프트
- `analysis/analyze.py`·`synth.py` Part 1 계산 → `results.json`
- `analysis/검산_워크북.xlsx` Excel 수식 검산(40항목, Python 값과 일치)
- `report/반품진단_핵심브리핑.html` 핵심 요약 단일 HTML(카드 클릭 시 상세 드로어)
- `report/참고서_반품진단_리포트.html` 시각화 리포트(Part 1 + 문서 1·2 탭)
- `report/doc1_교육모듈.md/.docx` 사내 교육 모듈 · `report/doc2_협의공문.md/.docx` 거래처 협의 공문

재생성: `python3 analysis/analyze.py && python3 analysis/synth.py && python3 analysis/page_data.py && python3 report/build.py && python3 report/build_brief.py`
