/* 반품 모니터링 계산 모듈 — 순수 함수(브라우저·Node 공용). 입력: 월별 원자료 + 도서마스터 + 파라미터 */
(function (root) {
  const DISP = new Set(['개정판교체', '파본']);
  const REPL = '개정판교체', PABON = '파본';
  const ymAdd = (m, k) => { const y = +m.slice(0, 4), mm = +m.slice(5, 7); const t = y * 12 + mm - 1 + k; return `${Math.floor(t / 12)}-${String(t % 12 + 1).padStart(2, '0')}`; };
  const ymRange = (a, b) => { const out = []; for (let m = a; m <= b; m = ymAdd(m, 1)) out.push(m); return out; };
  const sum = a => a.reduce((x, y) => x + y, 0);
  const add = (o, k, v) => { o[k] = (o[k] || 0) + v; };

  /* 시차곡선: 월 정상반품 ≈ Σ_k 출고[t−k]·p_k, p≥0, 인접 평활 λ. 투영경사법(결정적) */
  function fitLag(ship, ret, K = 12, lam = 0.1, iters = 20000) {
    const T = ship.length, sc = sum(ship) / T || 1, n = K + 1;
    const A = []; for (let t = 0; t < T; t++) { const row = []; for (let k = 0; k < n; k++) row.push(t - k >= 0 ? ship[t - k] / sc : 0); A.push(row); }
    const y = ret.map(v => v / sc);
    const H = Array.from({ length: n }, () => new Array(n).fill(0)), g = new Array(n).fill(0);
    for (let t = 0; t < T; t++) for (let i = 0; i < n; i++) { g[i] += A[t][i] * y[t]; for (let j = 0; j < n; j++) H[i][j] += A[t][i] * A[t][j]; }
    for (let i = 0; i < n - 1; i++) { H[i][i] += lam; H[i + 1][i + 1] += lam; H[i][i + 1] -= lam; H[i + 1][i] -= lam; }
    // 최대 고유값(거듭제곱법)으로 스텝 결정
    let v = new Array(n).fill(1), Lp = 1;
    for (let it = 0; it < 200; it++) { const w = H.map(r => sum(r.map((x, j) => x * v[j]))); Lp = Math.sqrt(sum(w.map(x => x * x))); v = w.map(x => x / Lp); }
    let p = new Array(n).fill(0);
    for (let it = 0; it < iters; it++) { const Hp = H.map(r => sum(r.map((x, j) => x * p[j]))); p = p.map((x, i) => Math.max(0, x - (Hp[i] - g[i]) / Lp)); }
    const pred = A.map(r => sum(r.map((x, k) => x * p[k])) * sc);
    return { p, pred };
  }

  function kmeans(X, k, iters = 100) {
    const n = X.length, d = X[0].length, dist = (a, b) => sum(a.map((x, i) => (x - b[i]) ** 2));
    const C = [X[0].slice()]; // 첫 중심 = 첫 행(호출 측에서 반품률 최고 거래처를 첫 행으로 정렬)
    while (C.length < k) { let best = -1, bi = 0; X.forEach((x, i) => { const m = Math.min(...C.map(c => dist(x, c))); if (m > best) { best = m; bi = i; } }); C.push(X[bi].slice()); }
    let lab = new Array(n).fill(0);
    for (let it = 0; it < iters; it++) {
      const nl = X.map(x => { let b = 0, bd = Infinity; C.forEach((c, j) => { const dd = dist(x, c); if (dd < bd) { bd = dd; b = j; } }); return b; });
      for (let j = 0; j < k; j++) { const mem = X.filter((_, i) => nl[i] === j); if (mem.length) for (let q = 0; q < d; q++) C[j][q] = sum(mem.map(m => m[q])) / mem.length; }
      if (nl.every((v, i) => v === lab[i]) && it > 0) { lab = nl; break; } lab = nl;
    }
    return { lab, C };
  }

  function build(monthDocs, masterRows, params, asOfIn, opt = {}) {
    const L = +params.logistics || 1400;
    const docs = monthDocs.slice().sort((a, b) => a.ym < b.ym ? -1 : 1);
    if (!docs.length) return null;
    const first = docs[0].ym, last = docs[docs.length - 1].ym, asOf = asOfIn && asOfIn <= last ? asOfIn : last;
    const months = ymRange(first, asOf), NM = months.length, mi = Object.fromEntries(months.map((m, i) => [m, i]));
    const L12 = months.slice(-12), L12s = new Set(L12), H2 = new Set(months.slice(-6)), H1 = new Set(months.slice(-12, -6));
    const M = {}; for (const r of masterRows) M[r[0]] = { subj: r[1], grade: r[2], list: +r[3], cost: +r[4], rev: r[5] || '' };
    const S = [], R = [];
    for (const d of docs) { if (d.ym > asOf) continue; for (const r of d.ship || []) S.push({ m: d.ym, p: r[0], s: r[1], q: +r[2], price: +r[3] }); for (const r of d.ret || []) R.push({ m: d.ym, p: r[0], s: r[1], q: +r[2], why: r[3] }); }
    // 반품 단가: (거래처×시리즈) 출고 가중평균 → 없으면 거래처 평균
    const pq = {}, pa = {}, qq = {}, qa = {};
    for (const r of S) { const k = r.p + '|' + r.s; add(pq, k, r.q); add(pa, k, r.q * r.price); add(qq, r.p, r.q); add(qa, r.p, r.q * r.price); }
    let fallback = 0;
    for (const r of R) { const k = r.p + '|' + r.s; if (pq[k]) r.price = pa[k] / pq[k]; else { r.price = qq[r.p] ? qa[r.p] / qq[r.p] : 0; fallback += r.q; } r.amt = r.q * r.price; r.cost = (M[r.s] || {}).cost || 0; r.disp = DISP.has(r.why); }
    for (const r of S) { const m = M[r.s] || {}; r.list = (m.list || 0) * r.q; r.cost = (m.cost || 0) * r.q; r.amt = r.q * r.price; }
    // ---- 전사
    const T = { ship: sum(S.map(r => r.q)), ret: sum(R.map(r => r.q)), rev: sum(S.map(r => r.amt)), retamt: sum(R.map(r => r.amt)) };
    T.rate = T.ret / T.ship; T.netrev = T.rev - T.retamt; T.list = sum(S.map(r => r.list)); T.sr = T.rev / T.list;
    T.shipCost = sum(S.map(r => r.cost)); T.dispQ = sum(R.filter(r => r.disp).map(r => r.q));
    T.dispCost = sum(R.filter(r => r.disp).map(r => r.q * r.cost)); T.resellCost = sum(R.filter(r => !r.disp).map(r => r.q * r.cost));
    T.log = T.ret * L; T.contrib = T.netrev - (T.shipCost - T.resellCost) - T.log; T.d = T.dispQ / T.ret;
    T.ship12 = sum(S.filter(r => L12s.has(r.m)).map(r => r.q)); T.ret12 = sum(R.filter(r => L12s.has(r.m)).map(r => r.q));
    T.rev12 = sum(S.filter(r => L12s.has(r.m)).map(r => r.amt)); T.retamt12 = sum(R.filter(r => L12s.has(r.m)).map(r => r.amt));
    T.cash12 = T.ret12 * L + sum(R.filter(r => r.disp && L12s.has(r.m)).map(r => r.q * r.cost));
    T.pabonShare = sum(R.filter(r => r.why === PABON).map(r => r.q)) / T.ret;
    T.fallbackQ = fallback; T.months = NM; T.first = first; T.asOf = asOf; T.last = last;
    const reasons = {}; for (const r of R) add(reasons, r.why, r.q); T.reasons = reasons;
    const mon = months.map(m => ({ m, ship: 0, ret: 0, retN: 0, rev: 0, retamt: 0 }));
    for (const r of S) { const o = mon[mi[r.m]]; o.ship += r.q; o.rev += r.amt; }
    for (const r of R) { const o = mon[mi[r.m]]; o.ret += r.q; o.retamt += r.amt; if (r.why !== REPL) o.retN += r.q; }
    // ---- 거래처
    const P = {};
    const gp = n => P[n] || (P[n] = { n, ship: 0, ret: 0, rev: 0, retamt: 0, list: 0, shipCost: 0, dispQ: 0, dispCost: 0, resellCost: 0, ship12: 0, ret12: 0, pabon12: 0, a1: 0, l1: 0, a2: 0, l2: 0, pabon: 0, mon: months.map(() => [0, 0]) });
    for (const r of S) { const p = gp(r.p); p.ship += r.q; p.rev += r.amt; p.list += r.list; p.shipCost += r.cost; p.mon[mi[r.m]][0] += r.q; if (L12s.has(r.m)) p.ship12 += r.q; if (H1.has(r.m)) { p.a1 += r.amt; p.l1 += r.list; } if (H2.has(r.m)) { p.a2 += r.amt; p.l2 += r.list; } }
    for (const r of R) { const p = gp(r.p); p.ret += r.q; p.retamt += r.amt; p.mon[mi[r.m]][1] += r.q; if (r.disp) { p.dispQ += r.q; p.dispCost += r.q * r.cost; } else p.resellCost += r.q * r.cost; if (r.why === PABON) p.pabon += r.q; if (L12s.has(r.m)) { p.ret12 += r.q; if (r.why === PABON) p.pabon12 += r.q; } }
    const PL = Object.values(P);
    for (const p of PL) {
      p.rate = p.ship ? p.ret / p.ship : null; p.netrev = p.rev - p.retamt; p.sr = p.list ? p.rev / p.list : null;
      p.log = p.ret * L; p.contrib = p.netrev - (p.shipCost - p.resellCost) - p.log; p.cm = p.rev ? p.contrib / p.rev : null;
      p.price = p.ship ? p.rev / p.ship : 0; p.unitCost = p.ship ? p.shipCost / p.ship : 0; p.d = p.ret ? p.dispQ / p.ret : T.d;
      const m = p.price - p.unitCost; p.be = m > 0 ? m / (m + L + p.d * p.unitCost) : 0;
      p.contribPer = p.ship ? (1 - p.rate) * m - p.rate * (L + p.d * p.unitCost) : 0;
      p.headroom = p.be - (p.rate || 0);
      p.rate12 = p.ship12 ? p.ret12 / p.ship12 : null; p.srChg = (p.l1 && p.l2) ? (p.a2 / p.l2 - p.a1 / p.l1) * 100 : null;
      p.pabonShare12 = p.ret12 ? p.pabon12 / p.ret12 : null;
      const ex = (T.ret - p.ret) / (T.ship - p.ship); p.exRate = ex; p.excess = p.ret - p.ship * ex; p.excessAmt = p.excess * p.price;
    }
    const rk = (arr, key) => { const s = arr.slice().sort((a, b) => b[key] - a[key]); s.forEach((p, i) => p['rk_' + key] = i + 1); };
    rk(PL, 'rev'); rk(PL, 'netrev'); rk(PL, 'contrib');
    PL.forEach(p => p.move = p.rk_rev - p.rk_netrev);
    // ---- 경보(거래처 4항목)
    for (const p of PL) {
      const al = [];
      if (p.rate12 != null) { const lv = p.rate12 > 2 * T.rate ? 2 : p.rate12 > T.rate ? 1 : 0; if (lv) al.push({ k: 'rate', lv, v: p.rate12 }); }
      if (p.move <= -1) al.push({ k: 'rank', lv: p.move <= -2 ? 2 : 1, v: p.move });
      if (p.srChg != null) { const lv = p.srChg <= -0.5 ? 2 : p.srChg <= -0.1 ? 1 : 0; if (lv) al.push({ k: 'sr', lv, v: p.srChg }); }
      if (p.pabonShare12 != null) { const lv = p.pabonShare12 > 2 * T.pabonShare ? 2 : p.pabonShare12 > T.pabonShare ? 1 : 0; if (lv) al.push({ k: 'pabon', lv, v: p.pabonShare12 }); }
      p.alerts = al; p.sev = sum(al.map(a => a.lv));
    }
    // ---- 개정판(시리즈)
    const serMon = {}; for (const r of S) { (serMon[r.s] || (serMon[r.s] = {}))[r.m] = (serMon[r.s][r.m] || 0) + r.q; }
    const events = [], upcoming = [];
    for (const [s, m] of Object.entries(M)) {
      const Mm = m.rev; if (!Mm || !/^\d{4}-\d{2}$/.test(Mm)) continue;
      const pre = [-3, -2, -1].map(k => ymAdd(Mm, k)), post = [1, 2, 3].map(k => ymAdd(Mm, k));
      const sm = serMon[s] || {};
      const outside = months.filter(x => !pre.includes(x) && (sm[x] || 0) > 0);
      const base = outside.length ? sum(outside.map(x => sm[x])) / outside.length : 0;
      const q = pre.map(x => (x in mi) ? (sm[x] || 0) : null);
      const pr = R.filter(r => r.s === s && post.includes(r.m));
      const ev = { s, M: Mm, pre, post, q, base, win: sum(q.map(x => x || 0)), postRet: sum(pr.map(r => r.q)), repl: sum(pr.filter(r => r.why === REPL).map(r => r.q)),
        cost: m.cost, postObs: post.filter(x => x <= asOf).length, preObs: pre.filter(x => x in mi).length,
        byOff: post.map(x => sum(pr.filter(r => r.m === x && r.why === REPL).map(r => r.q))) };
      ev.mult = base ? ev.win / ev.preObs / base : null;
      ev.caps = [1.0, 0.7, 0.5].map(c => c * base);
      ev.byPartner = {}; for (const r of S) if (r.s === s && pre.includes(r.m)) add(ev.byPartner, r.p, r.q);
      if (Mm >= first && Mm <= asOf && ev.preObs === 3) events.push(ev);
      if (Mm > asOf && ev.preObs > 0 || (Mm > asOf && ymAdd(Mm, -6) <= asOf)) upcoming.push(ev);
    }
    events.sort((a, b) => a.M < b.M ? -1 : 1); upcoming.sort((a, b) => a.M < b.M ? -1 : 1);
    const done = events.filter(e => e.postObs === 3);
    const REV = { events, upcoming, n: done.length, win: sum(done.map(e => e.win)), post: sum(done.map(e => e.postRet)), repl: sum(done.map(e => e.repl)) };
    REV.rate = REV.win ? REV.post / REV.win : null; REV.replRate = REV.win ? REV.repl / REV.win : null;
    const offTot = [0, 1, 2].map(i => sum(done.map(e => e.byOff[i]))); REV.offShare = offTot.map(x => sum(offTot) ? x / sum(offTot) : 1 / 3);
    REV.base3 = sum(done.map(e => e.base * 3)); REV.mult = REV.base3 ? REV.win / REV.base3 : null;
    // 구간 출고 비중(거래처)
    const winP = {}; for (const e of done) for (const [p, q] of Object.entries(e.byPartner)) add(winP, p, q);
    for (const p of PL) p.winShare = p.ship ? (winP[p.n] || 0) / p.ship : 0;
    REV.winPartner = Object.entries(winP).sort((a, b) => b[1] - a[1]);
    // ---- 시차곡선 + 예측
    const lag = fitLag(mon.map(o => o.ship), mon.map(o => o.retN));
    lag.cum = []; lag.p.reduce((a, x) => { lag.cum.push(a + x); return a + x; }, 0);
    lag.total = sum(lag.p); lag.wape = sum(mon.map((o, i) => Math.abs(o.retN - lag.pred[i]))) / sum(mon.map(o => o.retN));
    const futShip = f => { const ly = ymAdd(f, -12); return ly in mi ? mon[mi[ly]].ship : sum(mon.slice(-12).map(o => o.ship)) / Math.min(12, NM); };
    const shipAt = m => (m in mi) ? mon[mi[m]].ship : futShip(m);
    const fc = [1, 2, 3].map(h => {
      const f = ymAdd(asOf, h); let normal = 0, normalKnown = 0;
      lag.p.forEach((pk, k) => { const src = ymAdd(f, -k); const v = shipAt(src) * pk; normal += v; if (src in mi) normalKnown += v; });
      let rev = 0; const revItems = [];
      for (const e of events.concat(upcoming)) { const off = e.post.indexOf(f); if (off < 0) continue;
        const sm = serMon[e.s] || {}; const win = sum(e.pre.map(x => (x in mi) ? (sm[x] || 0) : (sm[ymAdd(x, -12)] || e.base))); const v = win * (REV.replRate || 0) * REV.offShare[off]; rev += v; revItems.push({ s: e.s, M: e.M, v, cost: e.cost, win, est: e.pre.some(x => !(x in mi)) }); }
      return { m: f, normal, normalKnown, rev, total: normal + rev, revItems };
    });
    // 백테스트: 6개월 전 시점까지로 적합 → 이후 6개월 정상반품 예측(실제 출고 사용)
    let bt = null;
    if (NM >= 18) { const cut = NM - 6; const f2 = fitLag(mon.slice(0, cut).map(o => o.ship), mon.slice(0, cut).map(o => o.retN));
      bt = mon.slice(cut).map((o, j) => { const t = cut + j; let v = 0; f2.p.forEach((pk, k) => { if (t - k >= 0) v += mon[t - k].ship * pk; }); return { m: o.m, act: o.retN, pred: v }; });
      bt.wape = sum(bt.map(x => Math.abs(x.act - x.pred))) / sum(bt.map(x => x.act)); }
    // ---- 군집
    const feats = ['rate', 'sr', 'lsize', 'winShare', 'pabonShare'];
    const CL = PL.filter(p => p.ship > 0).map(p => ({ n: p.n, rate: p.rate, sr: p.sr || T.sr, lsize: Math.log10(p.ship), winShare: p.winShare, pabonShare: p.ret ? p.pabon / p.ret : 0 }));
    CL.sort((a, b) => b.rate - a.rate);
    const mu = {}, sd = {}; feats.forEach(f => { const v = CL.map(c => c[f]); mu[f] = sum(v) / v.length; sd[f] = Math.sqrt(sum(v.map(x => (x - mu[f]) ** 2)) / v.length) || 1; });
    const K = Math.min(opt.k || 3, CL.length);
    const km = kmeans(CL.map(c => feats.map(f => (c[f] - mu[f]) / sd[f])), K);
    CL.forEach((c, i) => c.cl = km.lab[i]);
    const clusters = km.C.map((z, j) => { const mem = CL.filter(c => c.cl === j); const raw = Object.fromEntries(feats.map((f, q) => [f, z[q] * sd[f] + mu[f]]));
      const tag = []; tag.push(z[0] > 0.5 ? '고반품' : z[0] < -0.5 ? '저반품' : '반품 중간'); tag.push(z[1] > 0.5 ? '고공급률' : z[1] < -0.5 ? '저공급률' : '공급률 중간'); tag.push(z[2] > 0.5 ? '대형' : z[2] < -0.5 ? '소형' : '중형');
      if (z[3] > 0.8) tag.push('개정판 직전 물량 多'); if (z[4] > 0.8) tag.push('파본 多');
      return { j, z, raw, tag: tag.join(' · '), members: mem.map(c => c.n), ship: sum(mem.map(c => P[c.n].ship)), contrib: sum(mem.map(c => P[c.n].contrib)) }; });
    // 반품률 높은 군집 순으로 번호 재부여
    const order = clusters.slice().sort((a, b) => b.raw.rate - a.raw.rate).map(c => c.j); const remap = Object.fromEntries(order.map((j, i) => [j, i]));
    clusters.forEach(c => c.j = remap[c.j]); clusters.sort((a, b) => a.j - b.j); CL.forEach(c => { c.cl = remap[c.cl]; P[c.n].cl = c.cl; });
    // ---- 시리즈 경보(개정판 직전 출고 배수)
    const serAlerts = [];
    for (const e of upcoming) e.pre.forEach((x, i) => { if (x in mi && e.base) { const v = (serMon[e.s] || {})[x] || 0; const r = v / e.base; const lv = r > 1.5 ? 2 : r > 1.0 ? 1 : 0; if (lv) serAlerts.push({ s: e.s, M: e.M, m: x, off: i - 3, v, r, cap: e.caps[i], lv }); } });
    return { T, mon, months, P: PL.sort((a, b) => b.rev - a.rev), PM: P, REV, lag, fc, bt, CL, clusters, feats, serAlerts, L, asOf };
  }
  const api = { build, fitLag, kmeans, ymAdd, ymRange, DISP };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.Engine = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
