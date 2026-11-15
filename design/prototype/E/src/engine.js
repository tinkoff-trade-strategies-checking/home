// Честный движок: общий для человека и алгоритма.
// Заявка привязана к последней свече, которую видел торгующий (t), исполняется начиная с бара t+1.

const ORDER_TYPES = {
  market: "Рыночная", limit: "Лимитная", stop: "Стоп-рыночная", stop_limit: "Стоп-лимитная",
  take_profit: "Тейк-профит", trailing: "Трейлинг-стоп", oco: "OCO (тейк + стоп)",
};
const SELL_ONLY = { take_profit: true, trailing: true, oco: true };

class Engine {
  constructor({ papers, costs, capital, naive = false }) {
    this.papers = papers;
    this.byId = Object.fromEntries(papers.map(p => [p.id, p]));
    this.costs = costs;
    this.naive = naive;
    this.capital = capital;
    this.cash = capital;
    this.pos = Object.fromEntries(papers.map(p => [p.id, { qty: 0, cost: 0 }]));
    this.orders = [];
    this.fills = [];
    this.equity = [];
    this.costByKind = { commission: 0, fee: 0, spread: 0, slippage: 0 };
    this.volUsed = {};
    this.seq = 0;
  }

  bar(pid, t) { return this.byId[pid].candles[t]; }

  value(t) {
    let v = this.cash;
    for (const p of this.papers) v += this.pos[p.id].qty * this.bar(p.id, t).c;
    return v;
  }

  place(o) {
    o = { tif: o.type === "market" || o.type === "limit" ? "day" : "gtc", ...o, id: ++this.seq, status: "active", filled: 0, fills: [] };
    if (o.type === "trailing") o.peak = this.bar(o.paper, o.t).c;
    this.orders.push(o);
    if (this.naive) this._fillNaive(o);
    return o;
  }

  cancel(id) {
    const o = this.orders.find(x => x.id === id);
    if (o && o.status === "active") o.status = o.filled ? "partial" : "cancelled";
    return o;
  }

  active() { return this.orders.filter(o => o.status === "active"); }

  // Бар t стал известен: исполняем заявки, поставленные раньше, и фиксируем капитал по close t.
  step(t) {
    for (const o of this.orders) {
      if (o.status !== "active" || o.t >= t) continue;
      this._try(o, t);
      if (o.status === "active" && o.tif === "day" && t >= o.t + 1) o.status = o.filled ? "partial" : "expired";
    }
    this.equity.push({ t, v: this.value(t) });
  }

  _fillNaive(o) {
    // Наивный прогон: исполнение по close той же свечи, без издержек и лимита ликвидности.
    const b = this.bar(o.paper, o.t);
    this._exec(o, o.t, b.c, o.qty, false, null, true);
  }

  _try(o, t) {
    const b = this.bar(o.paper, t), sell = o.side === "sell";
    let px = null, mkt = true, note = null;
    switch (o.type) {
      case "market":
        px = b.o; break;
      case "limit":
        if (sell ? b.h >= o.limit : b.l <= o.limit) { px = sell ? Math.max(b.o, o.limit) : Math.min(b.o, o.limit); mkt = false; }
        break;
      case "stop":
        if (sell ? b.l <= o.stop : b.h >= o.stop) px = sell ? Math.min(b.o, o.stop) : Math.max(b.o, o.stop);
        break;
      case "stop_limit":
        if (!o.triggered && (sell ? b.l <= o.stop : b.h >= o.stop)) { o.triggered = true; o.trigT = t; }
        if (o.triggered && (sell ? b.h >= o.limit : b.l <= o.limit)) {
          px = sell ? Math.max(Math.min(b.o, o.stop), o.limit) : Math.min(Math.max(b.o, o.stop), o.limit);
          mkt = false;
        }
        break;
      case "take_profit":
        if (b.h >= o.tp) { px = Math.max(b.o, o.tp); mkt = false; }
        break;
      case "trailing": {
        const lvl = o.peak * (1 - o.trail / 100);  // уровень по пику до этой свечи — пессимистично
        if (b.l <= lvl) { px = Math.min(b.o, lvl); note = `Трейлинг от пика ${fmtP(o.peak)}`; }
        else o.peak = Math.max(o.peak, b.h);
        break;
      }
      case "oco": {
        const hitTp = b.h >= o.tp, hitSl = b.l <= o.stop;
        if (hitTp && hitSl) { px = Math.min(b.o, o.stop); note = "Стоп и тейк задеты одной свечой: исполнен стоп"; o.pessimistic = true; }
        else if (hitSl) { px = Math.min(b.o, o.stop); note = "Сработал стоп"; }
        else if (hitTp) { px = Math.max(b.o, o.tp); mkt = false; note = "Сработал тейк"; }
        break;
      }
    }
    if (px == null) return;
    const used = this.volUsed[o.paper + t] || 0;
    const maxQ = Math.max(0, Math.floor(b.v * this.costs.liquidity) - used);
    const want = o.qty - o.filled;
    let q = Math.min(want, maxQ);
    if (q <= 0) { o.status = o.filled ? "partial" : "rejected"; o.reason = "Объём заявки больше 5 % объёма свечи"; return; }
    this._exec(o, t, px, q, mkt, note, false, b.v);
  }

  _exec(o, t, px, q, mkt, note, naive, vol) {
    const c = this.costs, sell = o.side === "sell", pos = this.pos[o.paper];
    let slip = 0, spread = 0;
    if (!naive && mkt) { spread = c.spread; slip = c.slippage + c.slip_k * (q / vol); }
    const price = px * (sell ? 1 - spread - slip : 1 + spread + slip);
    const k = naive ? 0 : c.commission + c.fee;
    if (sell) {
      if (pos.qty <= 0) { o.status = "rejected"; o.reason = "Нет позиции: шорт недоступен"; return; }
      if (q > pos.qty) { q = pos.qty; note = note || "Исполнено по размеру позиции"; o.qty = o.filled + q; }
    } else {
      const maxByCash = Math.floor(this.cash / (price * (1 + k)));
      if (maxByCash <= 0) { o.status = o.filled ? "partial" : "rejected"; o.reason = "Недостаточно денег"; return; }
      if (q > maxByCash) { q = maxByCash; note = note || "Урезано до доступных денег"; }
    }
    const gross = q * price;
    const fee = { commission: naive ? 0 : gross * c.commission, fee: naive ? 0 : gross * c.fee,
                  spread: q * px * spread, slippage: q * px * slip };
    for (const kk in fee) this.costByKind[kk] += fee[kk];
    if (sell) {
      const avg = pos.qty ? pos.cost / pos.qty : 0;
      pos.cost -= avg * q; pos.qty -= q;
      this.cash += gross - fee.commission - fee.fee;
    } else {
      pos.qty += q; pos.cost += gross + fee.commission + fee.fee;
      this.cash -= gross + fee.commission + fee.fee;
    }
    this.volUsed[o.paper + t] = (this.volUsed[o.paper + t] || 0) + q;
    o.filled += q;
    const partial = o.filled < o.qty;
    const f = { order: o.id, t, paper: o.paper, side: o.side, type: o.type, qty: q, price, px, cost: fee,
                partial, note, because: o.because || null, src: o.src || "human" };
    o.fills.push(f);
    this.fills.push(f);
    if (!partial) o.status = "filled";
    else if (o.type === "market" || o.tif === "day") { o.status = "partial"; o.reason = "Остаток больше 5 % объёма свечи"; }
  }
}

// --- индикаторы ---------------------------------------------------------------------------
function sma(c, t, n) { let s = 0; for (let i = t - n + 1; i <= t; i++) s += c[i].c; return s / n; }
function rsi(c, t, n) {
  let g = 0, l = 0;
  for (let i = t - n + 1; i <= t; i++) { const d = c[i].c - c[i - 1].c; if (d > 0) g += d; else l -= d; }
  return l === 0 ? 100 : 100 - 100 / (1 + g / l);
}
function atr(c, t, n) {
  let s = 0;
  for (let i = t - n + 1; i <= t; i++) s += Math.max(c[i].h - c[i].l, Math.abs(c[i].h - c[i - 1].c), Math.abs(c[i].l - c[i - 1].c));
  return s / n;
}

// Сигнал алгоритма на баре t при данной позиции. Возвращает {action, because} или null.
function algoSignal(algo, c, t, holding) {
  const p = algo.impl;
  const fill = (tpl, a, b) => tpl.replace(/\{(\w+)\}/g, (_, k) =>
    k === "a" ? fmtN(a, 1) : k === "b" ? fmtN(b, 1) : k === "enter" && p.kind === "mom" ? fmtN(p.enter * 100, 0) : (p[k] ?? k));
  if (t < 51) return null;  // алгоритмам нужна история: SMA 50 и сдвиг на бар
  if (p.kind === "sma") {
    const f = sma(c, t, p.fast), s = sma(c, t, p.slow), fp = sma(c, t - 1, p.fast), sp = sma(c, t - 1, p.slow);
    const calm = p.atr ? atr(c, t, p.atr) / c[t].c < p.atr_max : true;
    if (!holding && fp <= sp && f > s && calm) return { action: "buy", because: fill(algo.buy_because, f, s) };
    if (holding && fp >= sp && f < s) return { action: "sell", because: fill(algo.sell_because, f, s) };
  } else if (p.kind === "rsi") {
    const r = rsi(c, t, p.period);
    if (!holding && r < p.low) return { action: "buy", because: fill(algo.buy_because, r) };
    if (holding && r > p.high) return { action: "sell", because: fill(algo.sell_because, r) };
  } else if (p.kind === "mom") {
    const m = (c[t].c / c[t - p.lookback].c - 1) * 100;
    if (!holding && m > p.enter * 100) return { action: "buy", because: fill(algo.buy_because, m) };
    if (holding && m < p.exit * 100) return { action: "sell", because: fill(algo.sell_because, m) };
  } else if (p.kind === "brk") {
    let top = -Infinity, bot = Infinity;
    for (let i = t - p.enter; i < t; i++) top = Math.max(top, c[i].h);
    for (let i = t - p.exit; i < t; i++) bot = Math.min(bot, c[i].l);
    if (!holding && c[t].c > top) return { action: "buy", because: fill(algo.buy_because, c[t].c, top) };
    if (holding && c[t].c < bot) return { action: "sell", because: fill(algo.sell_because, c[t].c, bot) };
  }
  return null;
}

// Независимый прогон алгоритма на сессии: честный или наивный.
function runAlgo(algo, papers, { naive = false, days = DATA.v2.days } = {}) {
  const V = DATA.v2, t0 = V.warmup - 1, t1 = t0 + days;
  const e = new Engine({ papers, costs: V.costs, capital: V.capital, naive });
  const signals = [];
  const decide = t => {
    if (t >= t1) return;
    for (const p of papers) {
      const sig = algoSignal(algo, p.candles, t, e.pos[p.id].qty > 0);
      if (!sig) continue;
      const qty = sig.action === "buy" ? Math.floor(algo.impl.size * e.value(t) / p.candles[t].c) : e.pos[p.id].qty;
      if (qty <= 0) continue;
      signals.push({ t, paper: p.id, ...sig });
      e.place({ t, paper: p.id, side: sig.action, type: "market", qty, because: sig.because, src: algo.id });
    }
  };
  decide(t0);
  for (let t = t0 + 1; t <= t1; t++) { if (!naive) e.step(t); else e.equity.push({ t, v: e.value(t) }); decide(t); }
  return { engine: e, signals };
}

// Восстановление ручной сессии из журнала «номер свечи + заявка».
function replayJournal(papers, journal, upto) {
  const V = DATA.v2, t0 = V.warmup - 1;
  const e = new Engine({ papers, costs: V.costs, capital: V.capital });
  const apply = t => {
    for (const j of journal) {
      if (j.t !== t) continue;
      if (j.cancel) { const o = e.orders[j.cancel - 1]; if (o) e.cancel(o.id); }
      else e.place({ ...j });
    }
  };
  apply(t0);
  for (let t = t0 + 1; t <= upto; t++) { e.step(t); apply(t); }
  return e;
}

// --- разбор расхождений человека и алгоритма ------------------------------------------------
const DIV_TYPES = {
  extra: "Лишнее действие", missed: "Упущенное действие", timing: "Размер или момент", news: "Реакция на новость",
};

function analyzeSession(papers, journal, algoIds, days = DATA.v2.days) {
  const V = DATA.v2, t0 = V.warmup - 1, t1 = t0 + days, H = 10;
  const algos = algoIds.map(id => DATA.v2.algos.find(a => a.id === id));
  const primary = algos[0];
  const human = replayJournal(papers, journal, t1);
  const fills = human.fills;

  // позиция человека после закрытия бара t (с учётом исполнений на этом баре)
  const posAt = (pid, t) => fills.filter(f => f.paper === pid && f.t <= t).reduce((s, f) => s + (f.side === "buy" ? f.qty : -f.qty), 0);
  const eqAt = t => (human.equity.find(x => x.t === t) || { v: V.capital }).v;
  const c = pid => human.byId[pid].candles;
  const newsNear = (p, t) => V.news.find(n => n.t <= t && n.t >= t - 2 && (!n.sector || n.sector === p.sector));

  // решения человека: исполнение на баре tf означает решение после бара tf-1
  const acts = [];
  for (const f of fills) {
    const last = acts.find(a => a.paper === f.paper && a.side === f.side && a.order === f.order);
    if (last) { last.qty += f.qty; continue; }
    acts.push({ t: f.t - 1, tf: f.t, paper: f.paper, side: f.side, qty: f.qty, price: f.price, order: f.order, type: f.type });
  }
  // решения алгоритма на месте человека: в каждой точке с учётом позиции человека
  const sigs = algo => {
    const out = [];
    for (const p of papers) for (let t = t0; t < t1; t++) {
      const s = algoSignal(algo, c(p.id), t, posAt(p.id, t) > 0);
      if (s) out.push({ t, paper: p.id, ...s });
    }
    return out;
  };
  const algoSigs = algos.map(sigs);
  const prim = algoSigs[0];
  const near = (list, paper, side, t, w) => list.find(s => s.paper === paper && s.action === side && Math.abs(s.t - t) <= w);

  const divs = [];
  const used = new Set();
  for (const a of acts) {
    const p = human.byId[a.paper], cc = c(a.paper), tEnd = Math.min(a.tf + H, t1);
    const pnl = a.side === "buy" ? a.qty * (cc[tEnd].c - a.price) : a.qty * (a.price - cc[tEnd].c);
    const same = near(prim, a.paper, a.side, a.t, 0);
    if (same) { used.add(same); continue; }
    const close = near(prim, a.paper, a.side, a.t, 3);
    const n = newsNear(p, a.t);
    let d;
    if (close) {
      used.add(close);
      const ap = cc[close.t + 1].o, k = close.t - a.t;
      d = { type: "timing", impact: a.side === "buy" ? a.qty * (ap - a.price) : a.qty * (a.price - ap),
            algoDid: `${a.side === "buy" ? "купил" : "продал"} бы ${k > 0 ? `на ${k} св. позже` : `на ${-k} св. раньше`}`,
            because: close.because };
    } else {
      d = { type: n ? "news" : "extra", impact: pnl, algoDid: a.side === "buy" ? "не покупал бы" : "держал бы позицию",
            because: holdReason(primary, cc, a.t, a.side), news: n || null };
    }
    divs.push({ t: a.t, paper: a.paper, side: a.side, humanDid: `${a.side === "buy" ? "Купил" : "Продал"} ${fmtN(a.qty, 0)} шт. по ${fmtP(a.price)}`,
                qty: a.qty, ...d });
  }
  // упущенные действия: сигнал алгоритма без похожего решения человека, повторы подряд схлопываем
  let prev = {};
  for (const s of prim) {
    if (used.has(s)) continue;
    if (acts.find(a => a.paper === s.paper && a.side === s.action && Math.abs(a.t - s.t) <= 3)) continue;
    const key = s.paper + s.action;
    if (prev[key] !== undefined && s.t - prev[key] <= 3) { prev[key] = s.t; continue; }
    prev[key] = s.t;
    const cc = c(s.paper), ent = cc[s.t + 1].o, tEnd = Math.min(s.t + 1 + H, t1);
    let impact, qty;
    if (s.action === "buy") {
      qty = Math.floor(primary.impl.size * eqAt(s.t) / ent);
      impact = -qty * (cc[tEnd].c - ent * 1.0024);
    } else {
      qty = posAt(s.paper, s.t);
      impact = -qty * (ent - cc[tEnd].c);
    }
    divs.push({ t: s.t, paper: s.paper, side: s.action, type: "missed", qty, impact,
                humanDid: s.action === "buy" ? "Не покупал" : "Держал позицию",
                algoDid: `${s.action === "buy" ? "купил" : "продал"} бы ${fmtN(qty, 0)} шт.`, because: s.because });
  }
  divs.sort((a, b) => a.t - b.t);
  // консенсус: сколько алгоритмов поступили бы так же, как основной
  for (const d of divs) {
    let agree = 0;
    algoSigs.forEach(list => {
      const has = near(list, d.paper, d.side, d.t, 3);
      if (d.type === "missed" ? has : !has || d.type === "timing") agree++;
    });
    d.consensus = { agree, total: algos.length };
  }
  // обратная проверка: прибыльные сделки человека, которых нет у алгоритма
  const reverse = [];
  for (const p of papers) {
    const lots = [];
    for (const f of fills.filter(x => x.paper === p.id)) {
      if (f.side === "buy") { lots.push({ ...f, left: f.qty }); continue; }
      let q = f.qty;
      while (q > 0 && lots.length) {
        const l = lots[0], m = Math.min(q, l.left);
        const profit = m * (f.price - l.price);
        if (profit > 0 && !near(prim, p.id, "buy", l.t - 1, 3))
          reverse.push({ paper: p.id, buyT: l.t, sellT: f.t, qty: m, buy: l.price, sell: f.price, profit });
        l.left -= m; q -= m;
        if (!l.left) lots.shift();
      }
    }
  }
  const algoRun = runAlgo(primary, papers, { days });
  const bench = benchmark(papers, days);
  const errSum = divs.filter(d => d.type !== "news").reduce((s, d) => s + d.impact, 0);
  return { human, divs, reverse, algo: algoRun.engine, algoSignals: algoRun.signals, bench, errSum, algos, primary };
}

function holdReason(algo, c, t, side) {
  const p = algo.impl;
  if (p.kind === "sma") {
    const f = sma(c, t, p.fast), s = sma(c, t, p.slow);
    const rel = `SMA${p.fast} = ${fmtN(f, 1)} ${f > s ? "выше" : "ниже"} SMA${p.slow} = ${fmtN(s, 1)}`;
    return side === "sell" ? `нет пересечения сверху вниз: ${rel}` : `нет пересечения снизу вверх: ${rel}`;
  }
  if (p.kind === "rsi") return `RSI = ${fmtN(rsi(c, t, p.period), 1)}, между ${p.low} и ${p.high}`;
  if (p.kind === "mom") return `рост за ${p.lookback} дней = ${fmtN((c[t].c / c[t - p.lookback].c - 1) * 100, 1)} %, сигнала нет`;
  return "цена внутри канала";
}

function benchmark(papers, days = DATA.v2.days) {
  // Равные доли всех бумаг сессии с первого дня, без ребалансировки
  const V = DATA.v2, t0 = V.warmup - 1, out = [];
  for (let t = t0; t <= t0 + days; t++)
    out.push({ t, v: V.capital * papers.reduce((s, p) => s + p.candles[t].c / p.candles[t0 + 1].o, 0) / papers.length });
  return out;
}

function metrics(e) {
  const eq = e.equity.map(x => x.v), cap = e.capital;
  let peak = cap, dd = 0;
  for (const v of eq) { peak = Math.max(peak, v); dd = Math.min(dd, v / peak - 1); }
  const rets = eq.map((v, i) => v / (i ? eq[i - 1] : cap) - 1);
  const mean = rets.reduce((s, x) => s + x, 0) / rets.length;
  const sd = Math.sqrt(rets.reduce((s, x) => s + (x - mean) ** 2, 0) / rets.length);
  const costs = Object.values(e.costByKind).reduce((s, x) => s + x, 0);
  const final = eq.length ? eq[eq.length - 1] : cap;
  return {
    final, ret: final / cap - 1, dd, sharpe: sd ? mean / sd * Math.sqrt(252) : 0, costs,
    trades: e.fills.length, partial: e.orders.filter(o => o.status === "partial" || (o.fills.some(f => f.partial))).length,
    rejected: e.orders.filter(o => o.status === "rejected").length,
    pessimistic: e.orders.filter(o => o.pessimistic).length,
  };
}

// --- форматирование -------------------------------------------------------------------------
function fmtN(v, d = 0) {
  return (v < 0 ? "−" : "") + Math.abs(v).toLocaleString("ru-RU", { minimumFractionDigits: d, maximumFractionDigits: d }).replace(/ /g, " ");
}
function fmtP(v) { return fmtN(v, 2); }
function fmtR(v) { return fmtN(Math.round(v), 0) + " ₽"; }
function fmtPct(v, d = 1, sign = true) { return (sign && v > 0 ? "+" : "") + fmtN(v * 100, d) + " %"; }
function fmtSR(v) { return (v > 0 ? "+" : "") + fmtR(v); }
