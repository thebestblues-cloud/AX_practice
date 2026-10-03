"""src.html + engine.js → 반품모니터링_대시보드.html (아티팩트 게시본)"""
import pathlib
D=pathlib.Path(__file__).parent
s=(D/'src.html').read_text().replace('%%ENGINE%%',(D/'engine.js').read_text())
assert '</script' not in (D/'engine.js').read_text()
(D/'반품모니터링_대시보드.html').write_text(s); print(len(s))
