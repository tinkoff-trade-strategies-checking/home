// Кликабельный прототип продукта v2 в концепции E «Дашборд».
const V = DATA.v2, V1 = DATA.v1;
const T0 = V.warmup - 1;
const ME = "Денис М.";
const algoById = id => V.algos.find(a => a.id === id) || userAlgos().find(a => a.id === id);
const paperById = id => V.papers.find(p => p.id === id);
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const cls = v => v > 0 ? "pos" : v < 0 ? "neg" : "";

// --- хранилище: только удобства одного зрителя, всё работает и без него ---------------------
const store = {
  get(k, d) { try { const v = localStorage.getItem("pak2." + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem("pak2." + k, JSON.stringify(v)); } catch (e) { /* приватный режим */ } },
  del(k) { try { localStorage.removeItem("pak2." + k); } catch (e) { /* приватный режим */ } },
};
const memo = { sessions: null, active: undefined, algos: null };
function userSessions() { return memo.sessions ??= store.get("sessions", []); }
function saveUserSessions(list) { memo.sessions = list; store.set("sessions", list); }
function activeSession() { if (memo.active === undefined) memo.active = store.get("active", null); return memo.active; }
function saveActive(s) { memo.active = s; if (s) store.set("active", s); else store.del("active"); }
function userAlgos() { return memo.algos ??= store.get("algos", []); }
function saveUserAlgos(list) { memo.algos = list; store.set("algos", list); }

function allSessions() {
  const builtIn = V.sessions.map(s => ({ ...s, days: V.days, compare: s.compare || ["sma"] }));
  return [...userSessions().slice().reverse(), ...builtIn];
}
const sessionById = id => allSessions().find(s => s.id === id);
const sessPapers = s => V.papers.filter(p => s.papers.includes(p.id));
const lastDay = s => T0 + (s.days || V.days);

function rng(seed) { let x = seed * 9301 + 49297; return () => ((x = (x * 9301 + 49297) % 233280) / 233280); }
function journalOf(s) {
  if (s.demo) return V.demo_journal;
  if (s.journal) return s.journal;
  // журнал для сессий коллег: детерминированно по seed
  const r = rng(s.seed || 1), out = [], ps = s.papers.split("");
  for (let d = 0; d < 56; d += 3 + Math.floor(r() * 6)) {
    const p = ps[Math.floor(r() * ps.length)], side = r() < 0.55 ? "buy" : "sell";
    out.push({ t: T0 + d, paper: p, side, type: "market", qty: side === "buy" ? 600 + Math.floor(r() * 12) * 100 : 5000 });
  }
  return out;
}

// --- анализ с кэшем -----------------------------------------------------------------------
const cache = {};
function cmpOf(s) {
  const st = state.cmp[s.id] || { primary: (s.compare || ["sma"])[0], consensus: (s.compare || []).length > 1 || !!s.demo };
  return st;
}
function algoIdsOf(s) {
  const c = cmpOf(s);
  return c.consensus ? [c.primary, ...V.algos.map(a => a.id).filter(id => id !== c.primary)] : [c.primary];
}
function analysis(s) {
  const ids = algoIdsOf(s), key = s.id + ids.join();
  if (cache[key]) return cache[key];
  let r;
  if (s.who === "human") {
    r = analyzeSession(sessPapers(s), journalOf(s), ids, s.days || V.days);
    r.m = metrics(r.human); r.ma = metrics(r.algo);
  } else {
    const a = algoById(s.algo), days = s.days || V.days;
    const honest = runAlgo(a, sessPapers(s), { days }), naive = runAlgo(a, sessPapers(s), { naive: true, days });
    r = { honest, naive, bench: benchmark(sessPapers(s), days), m: metrics(honest.engine), mn: metrics(naive.engine), algo: a };
  }
  r.benchRet = r.bench[r.bench.length - 1].v / V.capital - 1;
  return (cache[key] = r);
}
function lightOf(s) {
  if (s.who === "human") return ["ok", "ok", "ok"];
  const r = analysis(s), a = r.algo;
  const fut = a.lint && a.lint.length ? "warn" : "ok";
  const gain = r.mn.final - V.capital, lost = r.mn.final - r.m.final;
  const cost = gain > 0 && r.m.ret <= 0 ? "fail" : gain > 0 && lost > gain * 0.5 ? "warn" : "ok";
  return ["ok", fut, cost];
}
const LIGHT_WORD = { ok: "в порядке", warn: "есть пометка", fail: "ошибка", off: "не учтено" };
function lightHtml(st, big) {
  const names = ["Данные", "Будущее", "Издержки"];
  return `<span class="light${big ? " l" : ""}" title="${st.map((x, i) => names[i] + ": " + LIGHT_WORD[x]).join("\n")}">${st.map(x => `<i class="${x}"></i>`).join("")}</span>`;
}
function lightLegend() {
  return `<span class="row small muted">${lightHtml(["ok", "warn", "fail"])}&nbsp;Данные, будущее, издержки</span>`;
}

// --- иконки ----------------------------------------------------------------------------------
const IC = {
  home: '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none"/>',
  pause: '<path d="M8 5v14M16 5v14" stroke-width="3"/>',
  step: '<path d="M6 5v14l9-7z" fill="currentColor" stroke="none"/><path d="M18 5v14" stroke-width="2.5"/>',
  arena: '<path d="M4 19V9M9.5 19V5M15 19v-7M20.5 19V8"/>',
  report: '<path d="M6 3h9l4 4v14H6z"/><path d="M9 13h7M9 17h5M9 9h3"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v4h4M12 7v5l3 2"/>',
  flask: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/><path d="M7.5 15h9"/>',
  db: '<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  fork: '<circle cx="6" cy="5" r="2"/><circle cx="18" cy="5" r="2"/><circle cx="12" cy="19" r="2"/><path d="M6 7v2a3 3 0 0 0 3 3h6a3 3 0 0 0 3-3V7M12 12v5"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  news: '<path d="M4 5h13v14H6a2 2 0 0 1-2-2zM17 9h3v8a2 2 0 0 1-2 2"/><path d="M8 9h5M8 13h5M8 16h3"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  check: '<path d="m5 12 5 5 9-10"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
  replay: '<path d="M4 12a8 8 0 1 0 2.3-5.7L4 8.5"/><path d="M4 4v4.5h4.5"/><path d="M10 9v6l5-3z" fill="currentColor" stroke="none"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
};
const icon = (n, size = 16) => `<svg class="ic" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${IC[n]}</svg>`;

// --- состояние экрана ---------------------------------------------------------------------
const state = {
  cmp: {}, tab: {}, divFilter: "all", divSel: null, hist: { who: "all", blind: false }, ws: { filter: "all", q: "" },
  form: { who: "human", days: 60, start: "random", papers: "ABC", primary: "sma", consensus: true, algo: "sma" },
  arena: { paper: "A", playing: false, speed: 5, pauseNews: true, overlays: { sma20: true, sma50: false }, tab: "active",
           ticket: { side: "buy", type: "market", qty: 1000, tif: "day" } },
  draft: null,
};
let engine = null, timer = null;

// --- оболочка -----------------------------------------------------------------------------
const NAV = [
  ["home", "#/", "Главная"], ["plus", "#/new", "Новая сессия"], ["arena", "#/arena", "Арена"],
  ["history", "#/history", "История сессий"], null, ["flask", "#/workshop", "Мастерская"], ["db", "#/data", "Данные"],
];
function shell() {
  document.getElementById("app").innerHTML = `
  <div class="app" id="shell">
    <aside class="sidebar">
      <div class="brand" data-go="#/"><div class="brand-mark"><i style="background:var(--ok)"></i><i style="background:var(--warn)"></i><i style="background:var(--bad)"></i></div>
        <b class="label">Тренажёр<br>и лаборатория</b></div>
      <div class="project"><div class="small">Проект</div><b>ПАК, учебная команда</b></div>
      <nav class="nav" id="nav"></nav>
      <div class="sb-foot"><div class="avatar">ДМ</div><div class="label"><b>${DATA.user}</b><div class="small" style="color:var(--sb-t2)">фронтенд</div></div></div>
    </aside>
    <div class="main">
      <header class="topbar"><div class="crumbs" id="crumbs"></div>
        <div class="search">${icon("search")}<span>Поиск по сессиям и алгоритмам</span></div>
        <button class="btn primary" data-go="#/new">${icon("plus")}Новая сессия</button></header>
      <main class="content" id="content"></main>
    </div>
  </div>`;
}
function navHtml(route) {
  const act = activeSession();
  return NAV.map(n => {
    if (!n) return '<div class="sep"></div>';
    const [ic, href, label] = n, on = route === href || (href !== "#/" && route.startsWith(href));
    let extra = "";
    if (href === "#/arena" && act) extra = '<span class="live" title="Идёт сессия"></span>';
    if (href === "#/history") extra = `<span class="cnt">${allSessions().length}</span>`;
    if (href === "#/workshop") extra = `<span class="cnt">${V.algos.length + userAlgos().length}</span>`;
    return `<a href="${href}" class="${on ? "on" : ""}" title="${label}">${icon(ic)}<span class="label">${label}</span>${extra}</a>`;
  }).join("");
}
function crumbs(list) {
  document.getElementById("crumbs").innerHTML = list.map((c, i) =>
    i === list.length - 1 ? `<b>${c[0]}</b>` : `<a href="${c[1]}">${c[0]}</a><span>/</span>`).join("");
}
function head(title, meta = "", actions = "") {
  return `<div class="page-head"><div><h1>${title}</h1>${meta ? `<div class="meta">${meta}</div>` : ""}</div>${actions ? `<div class="actions">${actions}</div>` : ""}</div>`;
}
const disclaimer = () => `<div class="disclaimer">${DATA.disclaimer} Демо-данные синтетические, по форме повторяют весну 2020 года.</div>`;
function toast(html, ms = 4200) {
  const d = document.createElement("div");
  d.className = "toast"; d.innerHTML = `${icon("info", 18)}<div>${html}</div>`;
  document.body.appendChild(d);
  setTimeout(() => d.remove(), ms);
}
function modal(html) {
  closeModal();
  const d = document.createElement("div");
  d.className = "modal-bg"; d.id = "modal"; d.innerHTML = `<div class="modal">${html}</div>`;
  d.onclick = e => { if (e.target === d) closeModal(); };
  document.body.appendChild(d);
}
function closeModal() { document.getElementById("modal")?.remove(); }

// --- роутер ---------------------------------------------------------------------------------
const ROUTES = [
  [/^#\/$/, home], [/^#\/new$/, newSession], [/^#\/arena$/, arena], [/^#\/replay\/(.+)$/, replay],
  [/^#\/run\/(.+)$/, runProgress], [/^#\/report\/(.+)$/, report], [/^#\/history$/, history],
  [/^#\/workshop$/, workshop], [/^#\/algo\/new$/, algoNew], [/^#\/algo\/([^/]+)$/, algoCard], [/^#\/data$/, dataPage],
];
function render() {
  const h = location.hash || "#/";
  if (!h.startsWith("#/arena") && !h.startsWith("#/replay")) stopTimer();
  const shellEl = document.getElementById("shell");
  shellEl.classList.toggle("collapsed", h.startsWith("#/arena") || h.startsWith("#/replay"));
  for (const [re, fn] of ROUTES) {
    const m = h.match(re);
    if (m) { fn(...m.slice(1)); break; }
  }
  document.getElementById("nav").innerHTML = navHtml(h.replace(/^(#\/[^/]*).*/, "$1"));
}
function go(h) { if (location.hash === h) render(); else location.hash = h; }
window.addEventListener("hashchange", () => { window.scrollTo(0, 0); render(); });
window.addEventListener("resize", () => { clearTimeout(window._rz); window._rz = setTimeout(render, 150); });

// Делегирование кликов: data-go — переход, data-act — действие
const ACT = {};
document.addEventListener("click", e => {
  const g = e.target.closest("[data-go]");
  if (g) { e.preventDefault(); go(g.dataset.go); return; }
  const a = e.target.closest("[data-act]");
  if (a && ACT[a.dataset.act]) { e.preventDefault(); ACT[a.dataset.act](a, e); }
});
document.addEventListener("change", e => {
  const a = e.target.closest("[data-change]");
  if (a && ACT[a.dataset.change]) ACT[a.dataset.change](a, e);
});
document.addEventListener("input", e => {
  const a = e.target.closest("[data-input]");
  if (a && ACT[a.dataset.input]) ACT[a.dataset.input](a, e);
});

// --- общие куски ------------------------------------------------------------------------
const whoLabel = s => s.who === "human" ? "Человек" : (algoById(s.algo)?.name || "Алгоритм");
const modeBadges = s => (s.blind ? '<span class="badge dark">Слепая</span>' : '<span class="badge warn">Неслепая</span>') +
  ` <span class="badge">${s.who === "human" ? "Ручная" : "Алгоритм"}</span>`;
const papersLabel = (s, revealed) => sessPapers(s).map(p => revealed ? p.ticker : p.id).join(", ");
const dayOf = t => t - T0;
const dateOf = t => V.dates[t];
const shortDate = t => V.dates[t].slice(0, 5);
const sectorBadge = sec => `<span class="badge">${sec || "Весь рынок"}</span>`;
const divBadge = type => `<span class="badge ${{ extra: "bad", missed: "warn", timing: "info", news: "" }[type]}">${DIV_TYPES[type]}</span>`;
function sessionResult(s) {
  const r = analysis(s);
  return s.who === "human" ? r.m.ret : r.m.ret;
}
function vsAlgo(s) {
  if (s.who !== "human") return null;
  const r = analysis(s);
  return -r.errSum / V.capital;  // насколько алгоритм на месте человека был бы лучше
}
function pctCell(v) { return `<span class="${cls(v)}">${fmtPct(v)}</span>`; }

// =========================================================================================
// Главная
// =========================================================================================
function home() {
  crumbs([["Главная"]]);
  const ss = allSessions(), humans = ss.filter(s => s.who === "human");
  const act = activeSession();
  const gaps = humans.map(s => analysis(s)).map(r => r.errSum);
  const avgGap = gaps.reduce((a, b) => a + b, 0) / gaps.length;
  const types = { extra: 0, missed: 0, timing: 0, news: 0 };
  humans.forEach(s => analysis(s).divs.forEach(d => types[d.type]++));
  const tmax = Math.max(...Object.values(types));
  const top = [...V.algos].sort((a, b) => b.rating.score - a.rating.score);
  document.getElementById("content").innerHTML = `
    ${head("Главная", `<span>ПАК, учебная команда</span>`, `<button class="btn" data-go="#/workshop">${icon("flask")}Открыть мастерскую</button>`)}
    ${act ? `<div class="callout y"><div style="flex:1"><b>Сессия ${act.id} не завершена.</b> День ${dayOf(act.last)} из ${act.days}, бумаг: ${act.papers.length}. Журнал заявок сохранён, продолжите с того же места.</div>
      <button class="btn primary" data-go="#/arena">${icon("play")}Продолжить сессию</button></div>` : ""}
    <div class="panel"><div class="kpis">
      <div class="kpi"><div class="l">Сессий в команде</div><div class="v">${ss.length}</div><div class="h">людей ${humans.length}, алгоритмов ${ss.length - humans.length}</div></div>
      <div class="kpi"><div class="l">Слепых сессий</div><div class="v">${ss.filter(s => s.blind).length}</div><div class="h">период раскрывается в конце</div></div>
      <div class="kpi"><div class="l">Цена расхождений, в среднем</div><div class="v ${cls(avgGap)}">${fmtSR(avgGap)}</div><div class="h">за сессию, человек против алгоритма</div></div>
      <div class="kpi"><div class="l">Алгоритмов в мастерской</div><div class="v">${V.algos.length + userAlgos().length}</div><div class="h">открыто под MIT, ${V.algos.filter(a => a.forked_from).length} форк</div></div>
    </div></div>
    <div class="panel"><div class="panel-h"><h3>Как устроен продукт</h3></div>
      <div class="kpis">${[
        ["01", "Запуск", "Кто торгует, сколько свечей, с какой даты, какие бумаги", "#/new"],
        ["02", "Арена", "Слепой плеер: пауза, шаг, ×1/×5/×10, все типы заявок, новости", act ? "#/arena" : "#/new"],
        ["03", "Отчёт", "Раскрытие периода и разбор расхождений с алгоритмом", "#/report/s-0027"],
        ["04", "Мастерская", "Алгоритмы на DSL с because, форки, рейтинг на закрытых окнах", "#/workshop"],
      ].map(([n, t, d, h]) => `<div class="kpi" style="cursor:pointer" data-go="${h}"><div class="faint">${n}</div><div style="font-weight:700;font-size:16px;margin:4px 0">${t}</div><div class="h" style="color:var(--text2)">${d}</div></div>`).join("")}</div></div>
    <div class="grid g-12">
      <div class="panel s-8"><div class="panel-h"><h3>Последние сессии</h3><div class="right">${lightLegend()}<a href="#/history" class="small">Вся история</a></div></div>
        ${sessionsTable(ss.slice(0, 6), true)}</div>
      <div class="col s-4" style="gap:16px">
        <div class="panel"><div class="panel-h"><h3>Где люди расходятся с алгоритмами</h3></div><div class="panel-b bars-h">
          ${Object.entries(types).map(([k, v]) => `<div class="bar-h" style="grid-template-columns:150px 1fr 28px"><span class="small">${DIV_TYPES[k]}</span><span class="track"><i style="left:0;width:${v / tmax * 100}%;background:${{ extra: "var(--bad)", missed: "var(--warn)", timing: "var(--accent)", news: "var(--bench)" }[k]}"></i></span><span class="small r num">${v}</span></div>`).join("")}
          <div class="hint">По всем ручным сессиям команды, основной алгоритм — «Пересечение SMA».</div></div></div>
        <div class="panel"><div class="panel-h"><h3>Лучшие алгоритмы</h3><div class="right"><a href="#/workshop" class="small">Каталог</a></div></div>
          <table class="t dense">${top.slice(0, 4).map(a => `<tr class="click" data-go="#/algo/${a.id}"><td style="min-width:240px"><b>${esc(a.name)}</b><div class="small muted">${esc(a.author)}, v${a.version}</div></td><td class="r">${scoreHtml(a.rating.score)}</td></tr>`).join("")}</table></div>
      </div>
    </div>${disclaimer()}`;
}

function sessionsTable(list, compact) {
  if (!list.length) return `<div class="empty">Сессий под этот фильтр нет.</div>`;
  return `<div class="scroll"><table class="t"><thead><tr><th>Сессия</th><th>Кто торговал</th>${compact ? "" : "<th>Автор</th>"}<th>Бумаги</th><th>Режим</th>${compact ? "" : "<th>Начало</th>"}<th class="r">Результат</th><th class="r">Цена расхождений</th><th>Честность</th><th></th></tr></thead><tbody>
    ${list.map(s => {
      const r = analysis(s), res = r.m.ret, gap = s.who === "human" ? r.errSum : null;
      return `<tr class="click" data-go="#/report/${s.id}"><td class="w"><b>${s.id}</b></td><td>${esc(whoLabel(s))}</td>${compact ? "" : `<td class="w">${esc(s.author)}</td>`}
        <td class="w">${papersLabel(s, !s.blind)}</td><td class="w">${modeBadges(s)}</td>${compact ? "" : `<td class="w muted">${s.started}</td>`}
        <td class="r">${pctCell(res)}</td><td class="r">${gap == null ? '<span class="faint">—</span>' : `<span class="${cls(gap)}">${fmtSR(gap)}</span>`}</td>
        <td>${lightHtml(lightOf(s))}</td><td class="r w"><button class="btn s" data-go="#/replay/${s.id}" title="Воспроизвести по журналу">${icon("replay", 14)}Воспроизвести</button></td></tr>`;
    }).join("")}</tbody></table></div>`;
}
function scoreHtml(v) { return `<span class="score"><span class="track"><i style="width:${v}%"></i></span><b class="num">${v}</b></span>`; }

// =========================================================================================
// Новая сессия
// =========================================================================================
function newSession() {
  crumbs([["Главная", "#/"], ["Новая сессия"]]);
  const f = state.form, human = f.who === "human", own = f.start === "own";
  const algo = algoById(f.algo);
  const c = V.costs;
  const seg = (key, items) => `<div class="seg">${items.map(([v, l]) => `<button class="${String(f[key]) === String(v) ? "on" : ""}" data-act="form" data-k="${key}" data-v="${v}">${l}</button>`).join("")}</div>`;
  const algoOpts = sel => V.algos.map(a => `<option value="${a.id}" ${a.id === sel ? "selected" : ""}>${esc(a.name)}, v${a.version}</option>`).join("");
  document.getElementById("content").innerHTML = `
    ${head("Новая сессия", "Три параметра и бумаги. Остальное — честное исполнение по общим правилам.")}
    <div class="grid g-12">
      <div class="col s-8" style="gap:16px">
        <div class="panel"><div class="panel-h"><h3>Кто торгует</h3></div><div class="panel-b col">
          ${seg("who", [["human", "Человек"], ["algo", "Алгоритм"]])}
          <div class="hint">${human ? "Ручной режим: вы ведёте сессию в плеере, видите обезличенные новости, ставите заявки любого типа."
            : "Алгоритм на DSL исполняется детерминированно и новостей не видит. Прогон займёт пару секунд."}</div>
          ${human ? "" : `<div class="fields f2"><div class="field sel"><label>Алгоритм из мастерской</label><select data-change="formSel" data-k="algo">${algoOpts(f.algo)}</select></div>
            <div class="field ro"><label>Версия</label><input readonly value="v${algo.version} от ${algo.updated}, неизменяемая"></div></div>`}
        </div></div>
        <div class="panel"><div class="panel-h"><h3>Длительность</h3></div><div class="panel-b col">
          ${seg("days", [[20, "20 свечей"], [40, "40 свечей"], [60, "60 свечей"]])}
          <div class="hint">Свечи дневные. Время виртуальное, его ведёт сервер: на скорости ×5 60 свечей идут около 20 секунд, пауза и шаг доступны всегда.</div>
        </div></div>
        <div class="panel"><div class="panel-h"><h3>Начало</h3></div><div class="panel-b col">
          ${seg("start", [["random", "Случайная закрытая дата"], ["own", "Своя дата"]])}
          ${own ? `<div class="fields f2"><div class="field"><label>Дата начала</label><input value="26.02.2020"></div><div></div></div>
            <div class="callout"><span class="badge warn">Неслепая</span><div class="small">Период и бумаги видны сразу. Сессия участвует во всех сравнениях, в истории её можно отфильтровать.</div></div>`
            : `<div class="hint">Дата выбирается из закрытых окон истории MOEX. Реальный период и бумаги раскроются в отчёте.</div>`}
        </div></div>
        <div class="panel"><div class="panel-h"><h3>Бумаги</h3><div class="right muted small">выбрано ${f.papers.length} из 3</div></div><div class="panel-b col">
          <div class="row" style="flex-wrap:wrap">${V.papers.map(p => `<button class="chip ${f.papers.includes(p.id) ? "on" : ""}" data-act="paper" data-p="${p.id}">${f.papers.includes(p.id) ? icon("check", 14) : ""}${own ? `${p.ticker}, ${p.name}` : `Бумага ${p.id}`}<span class="muted" style="font-weight:400">${p.sector}</span></button>`).join("")}</div>
          <div class="hint">${own ? "Своя дата: тикеры видны." : "В слепом режиме название и тикер скрыты, сектор экономики виден. Бумаги выбираются случайно из IMOEX, цены масштабированы: первая свеча = 100."}</div>
        </div></div>
        ${human ? `<div class="panel"><div class="panel-h"><h3>С кем сравнить в отчёте</h3></div><div class="panel-b col">
          <div class="fields f2"><div class="field sel"><label>Основной алгоритм</label><select data-change="formSel" data-k="primary">${algoOpts(f.primary)}</select></div>
          <div class="row"><button class="toggle ${f.consensus ? "on" : ""}" data-act="form" data-k="consensus" data-v="${!f.consensus}"></button><span>Консенсус всех алгоритмов мастерской</span></div></div>
          <div class="hint">Алгоритм ставится на ваше место в каждой точке с учётом вашей позиции. С консенсусом в отчёте появится «4 из 5 здесь не покупали бы».</div>
        </div></div>` : ""}
      </div>
      <div class="col s-4" style="gap:16px">
        <div class="panel" style="position:sticky;top:72px"><div class="panel-h"><h3>Сводка</h3></div><div class="panel-b">
          <div class="kv"><span>Кто торгует</span><span>${human ? "Человек" : esc(algo.name)}</span></div>
          <div class="kv"><span>Длительность</span><span>${f.days} свечей D1</span></div>
          <div class="kv"><span>Начало</span><span>${own ? "26.02.2020, неслепая" : "случайная закрытая"}</span></div>
          <div class="kv"><span>Бумаги</span><span>${f.papers.split("").map(id => own ? paperById(id).ticker : id).join(", ")}</span></div>
          <div class="kv"><span>Капитал</span><span>${fmtR(V.capital)}</span></div>
          <div class="kv"><span>Комиссия и сбор</span><span>${fmtN(c.commission * 100, 2)} % + ${fmtN(c.fee * 100, 2)} %</span></div>
          <div class="kv"><span>Спред и проскальзывание</span><span>${fmtN(c.spread * 100, 2)} % + ${fmtN(c.slippage * 100, 2)} %</span></div>
          <div class="kv"><span>Ликвидность</span><span>до ${fmtN(c.liquidity * 100)} % объёма свечи</span></div>
          <div class="kv"><span>Исполнение</span><span>по open следующей свечи</span></div>
          <div class="kv"><span>Маржа, шорт, пополнения</span><span class="muted">недоступны</span></div>
          <div style="margin-top:16px" class="col">
            <button class="btn primary l" data-act="start">${human ? icon("play") + "Начать сессию" : icon("play") + "Запустить прогон"}</button>
            <div class="hint">${human ? "Сессия хранится как журнал «номер свечи + заявка»: переживёт обновление страницы и воспроизводится." : "Результат детерминирован: тот же алгоритм на тех же данных даёт тот же отчёт."}</div>
          </div></div></div>
      </div>
    </div>`;
}
ACT.form = el => {
  const k = el.dataset.k, v = el.dataset.v;
  state.form[k] = k === "days" ? +v : k === "consensus" ? v === "true" : v;
  newSession();
};
ACT.formSel = el => { state.form[el.dataset.k] = el.value; newSession(); };
ACT.paper = el => {
  const f = state.form, p = el.dataset.p;
  if (f.papers.includes(p)) { if (f.papers.length > 1) f.papers = f.papers.replace(p, ""); }
  else f.papers = (f.papers + p).split("").sort().join("");
  newSession();
};
function nextId() {
  const nums = allSessions().map(s => +s.id.slice(2)).concat(activeSession() ? [+activeSession().id.slice(2)] : []);
  return "s-" + String(Math.max(...nums) + 1).padStart(4, "0");
}
function nowStr() {
  const d = new Date(), p = n => String(n).padStart(2, "0");
  return `${p(d.getDate())}.${p(d.getMonth() + 1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
ACT.start = () => {
  const f = state.form;
  if (f.who === "human") {
    const go_ = () => {
      saveActive({ id: nextId(), who: "human", author: ME, blind: f.start === "random", papers: f.papers, days: f.days,
                   compare: f.consensus ? [f.primary, ...V.algos.map(a => a.id).filter(x => x !== f.primary)] : [f.primary],
                   journal: [], last: T0, started: nowStr() });
      engine = null; state.arena.paper = f.papers[0]; state.arena.playing = false;
      go("#/arena");
    };
    if (activeSession()) {
      modal(`<h2>Начать новую сессию?</h2><div>Сессия ${activeSession().id} не завершена. Её журнал будет сохранён в истории как завершённый на дне ${dayOf(activeSession().last)}.</div>
        <div class="row"><span class="spacer"></span><button class="btn" data-act="closeModal">Отмена</button><button class="btn primary" data-act="startAnyway">Начать новую</button></div>`);
      ACT.startAnyway = () => { closeModal(); finishActive(false); go_(); };
    } else go_();
  } else {
    const s = { id: nextId(), who: "algo", algo: f.algo, author: ME, blind: f.start === "random", papers: f.papers, days: f.days, started: nowStr() };
    saveUserSessions([...userSessions(), s]);
    go("#/run/" + s.id);
  }
};
ACT.closeModal = closeModal;

function runProgress(id) {
  const s = sessionById(id);
  if (!s) return go("#/history");
  crumbs([["История сессий", "#/history"], [`Прогон ${id}`]]);
  const steps = ["Снапшот данных ds-0007 зафиксирован", "Статанализ: чтение будущего не найдено", `Исполнение ${s.days} свечей по open следующего бара`, "Расчёт метрик и наивного прогона"];
  document.getElementById("content").innerHTML = `${head(`Прогон ${id}`, `${esc(whoLabel(s))} на ${s.papers.length} бумагах, ${s.days} свечей`)}
    <div class="panel" style="max-width:640px"><div class="panel-b" style="padding-top:20px" id="runsteps"></div></div>`;
  let i = 0;
  const tick = () => {
    const el = document.getElementById("runsteps");
    if (!el) return;
    el.innerHTML = `<div class="progress" style="margin-bottom:16px"><div class="bar" style="width:${i / steps.length * 100}%"></div></div>` +
      steps.map((t, k) => `<div class="kv"><span>${t}</span><span>${k < i ? `<span class="badge ok">${icon("check", 12)}готово</span>` : k === i ? '<span class="badge info">идёт</span>' : '<span class="faint">ждёт</span>'}</span></div>`).join("");
    if (i++ < steps.length) setTimeout(tick, 420); else setTimeout(() => go("#/report/" + id), 300);
  };
  tick();
}

// =========================================================================================
// Арена
// =========================================================================================
function arenaSession() { return activeSession(); }
function ensureEngine(s) {
  if (!engine || engine._sid !== s.id || engine._last !== s.last) {
    engine = replayJournal(sessPapers(s), s.journal, s.last);
    engine._sid = s.id; engine._last = s.last;
  }
  return engine;
}
function arena() {
  const s = arenaSession();
  if (!s) {
    crumbs([["Арена"]]);
    document.getElementById("content").innerHTML = `${head("Арена")}<div class="panel"><div class="empty">
      <h2 style="margin-bottom:8px">Активной сессии нет</h2><div style="margin-bottom:16px">Запустите ручную сессию или посмотрите, как прошла демо-сессия.</div>
      <div class="row" style="justify-content:center"><button class="btn primary" data-go="#/new">${icon("play")}Новая сессия</button><button class="btn" data-go="#/replay/s-0027">${icon("replay")}Воспроизвести демо</button></div></div></div>`;
    return;
  }
  if (!state.arena._restored) {
    state.arena._restored = true;
    if (s.journal.length) toast(`Сессия ${s.id} восстановлена из журнала: ${s.journal.length} ${plural(s.journal.length, "запись", "записи", "записей")}, день ${dayOf(s.last)}.`);
  }
  if (!s.papers.includes(state.arena.paper)) state.arena.paper = s.papers[0];
  arenaView(s, false);
}
function replay(id) {
  const s = sessionById(id);
  if (!s) return go("#/history");
  if (!state.replay || state.replay.id !== id) {
    state.replay = { id, who: s.who, papers: s.papers, days: s.days || V.days, blind: s.blind, last: T0,
                     journal: s.who === "human" ? journalOf(s) : [], algo: s.algo, src: s };
    stopTimer(); state.arena.playing = false; engine = null; state.arena.paper = s.papers[0];
  }
  arenaView(state.replay, true);
}
function plural(n, a, b, c) { const m = n % 10, h = n % 100; return m === 1 && h !== 11 ? a : m >= 2 && m <= 4 && (h < 10 || h >= 20) ? b : c; }

function replayEngine(r) {
  if (r.who === "algo") {
    if (!engine || engine._sid !== "rp" + r.id || engine._last !== r.last) {
      engine = runAlgo(algoById(r.algo), sessPapers(r), { days: r.last - T0 }).engine; engine._sid = "rp" + r.id; engine._last = r.last;
    }
    return engine;
  }
  if (!engine || engine._sid !== "rp" + r.id || engine._last !== r.last) {
    engine = replayJournal(sessPapers(r), r.journal, r.last); engine._sid = "rp" + r.id; engine._last = r.last;
  }
  return engine;
}

function arenaView(s, ro) {
  const e = ro ? replayEngine(s) : ensureEngine(s), A = state.arena, end = T0 + s.days;
  const p = paperById(A.paper), cc = p.candles, last = s.last;
  const blind = s.blind && last < end;
  const pname = q => blind ? `Бумага ${q.id}` : `${q.ticker}`;
  crumbs(ro ? [["История сессий", "#/history"], [`Воспроизведение ${s.id}`]] : [["Арена"], [s.id]]);
  const newsSeen = s.who === "algo" ? [] : V.news.filter(n => n.t <= last && n.t > T0 - 5).reverse();
  const eqNow = e.value(last), pnl = eqNow - V.capital;
  const visFills = e.fills.filter(f => f.t <= last);
  const activeOrders = e.orders.filter(o => o.status === "active" && o.t <= last);
  document.getElementById("content").innerHTML = `
    ${head(ro ? `Воспроизведение ${s.id}` : "Арена",
      `${s.blind ? '<span class="badge dark">Слепая</span>' : '<span class="badge warn">Неслепая</span>'}<span class="badge">${s.who === "human" ? "Ручная сессия" : esc(algoById(s.algo).name)}</span><span>${s.id}</span><span>бумаг: ${s.papers.length}</span>${ro ? '<span class="badge info">Только просмотр: заявки из журнала</span>' : ""}`,
      ro ? `<button class="btn" data-go="#/report/${s.id}">${icon("report")}Открыть отчёт</button>`
         : `<button class="btn" data-act="finish">Завершить сессию</button>`)}
    <div class="panel"><div class="player">
      <button class="btn icon-btn ${A.playing ? "" : "primary"}" data-act="play" title="${A.playing ? "Пауза" : "Запустить"}" ${last >= end ? "disabled" : ""}>${icon(A.playing ? "pause" : "play")}</button>
      <button class="btn" data-act="stepBar" ${last >= end ? "disabled" : ""}>${icon("step")}Следующая свеча</button>
      <div class="seg">${[1, 5, 10].map(x => `<button class="${A.speed === x ? "on" : ""}" data-act="speed" data-v="${x}">×${x}</button>`).join("")}</div>
      ${s.who === "human" ? `<span class="row small"><button class="toggle ${A.pauseNews ? "on" : ""}" data-act="pauseNews"></button>Пауза на новости</span>` : ""}
      <div class="progress" title="Жёлтые отметки — новости">${s.who === "human" ? V.news.filter(n => n.t > T0 && n.t <= end).map(n => `<span class="tick" style="left:${(n.t - T0) / s.days * 100}%;opacity:${n.t <= last ? 1 : .35}"></span>`).join("") : ""}
        <div class="bar" style="width:${(last - T0) / s.days * 100}%"></div></div>
      <b class="num" style="white-space:nowrap">День ${dayOf(last)} из ${s.days}</b>
    </div></div>
    <div class="arena">
      <div class="col" style="gap:16px;min-width:0">
        <div class="panel">
          <div class="papers">${sessPapers(s).map(q => {
            const c0 = q.candles[T0].c, cn = q.candles[last].c, ch = cn / c0 - 1;
            const sp = q.candles.slice(Math.max(0, last - 30), last + 1).map(b => b.c);
            return `<div class="paper-tab ${q.id === A.paper ? "on" : ""}" data-act="paperTab" data-p="${q.id}">
              <div><b>${pname(q)}</b> <span class="muted small">${q.sector}</span></div><div class="small r ${cls(ch)}">${fmtPct(ch)}</div>
              <div class="px">${fmtP(cn)}</div><div>${spark(sp, 72, 22, ch >= 0 ? "#2FA57D" : "#E5483A")}</div></div>`;
          }).join("")}</div>
          <div class="row" style="padding:10px 16px 0">
            <span class="small muted">Индикаторы</span>
            <button class="chip ${A.overlays.sma20 ? "on" : ""}" style="height:24px;font-size:12px" data-act="ov" data-k="sma20">SMA 20</button>
            <button class="chip ${A.overlays.sma50 ? "on" : ""}" style="height:24px;font-size:12px" data-act="ov" data-k="sma50">SMA 50</button>
            <span class="spacer"></span>
            <span class="legend"><span><i style="background:#FFDD2D"></i>горизонт знания</span><span><i style="background:#FFC700;height:8px;width:8px;border-radius:50%"></i>новость</span><span>▲ покупка ▼ продажа</span></span>
          </div>
          <div class="chart-wrap" id="chart" style="padding:4px 4px 8px 8px"></div>
        </div>
        <div class="grid g-12">
          <div class="panel ${s.who === "human" ? "s-6" : "s-12"}" style="${s.who === "human" ? "" : "display:none"}">
            <div class="panel-h"><h3>Новости</h3><div class="right"><span class="badge">${newsSeen.length}</span></div></div>
            <div style="max-height:340px;overflow:auto">${newsSeen.length ? newsSeen.map(n => `<div class="news-item ${n.t === last ? "fresh" : ""}">
              <div class="row">${sectorBadge(n.sector)}<span class="small muted">${n.t <= T0 ? "до старта" : "день " + dayOf(n.t)}, ${n.time}</span></div>
              <div>${esc(n.text)}</div></div>`).join("") : `<div class="empty">Новостей пока нет. Новость появляется только после момента публикации.</div>`}</div>
          </div>
          <div class="panel ${s.who === "human" ? "s-6" : "s-12"}">
            <div class="tabs">${[["active", "Активные", activeOrders.length], ["fills", "Исполненные", visFills.length], ["journal", "Журнал", s.who === "human" ? s.journal.filter(j => j.t <= last).length : e.orders.length]].map(([k, l, n]) =>
              `<button class="${A.tab === k ? "on" : ""}" data-act="arenaTab" data-k="${k}">${l}<span class="cnt">${n}</span></button>`).join("")}</div>
            <div style="max-height:300px;overflow:auto">${ordersBlock(s, e, A.tab, ro, pname)}</div>
          </div>
        </div>
      </div>
      <div class="col" style="gap:16px">
        ${ro ? "" : `<div class="panel"><div class="panel-h"><h3>Заявка</h3></div>${ticketHtml(s, e, pname)}</div>`}
        <div class="panel"><div class="panel-h"><h3>Портфель</h3></div><div class="panel-b">
          <div class="row" style="align-items:baseline;gap:12px"><span style="font-size:28px;font-weight:700" class="num">${fmtR(eqNow)}</span><span class="${cls(pnl)} num">${fmtSR(pnl)}</span></div>
          <div class="kv"><span>Деньги</span><span>${fmtR(e.cash)}</span></div>
          <div class="kv"><span>В бумагах</span><span>${fmtR(eqNow - e.cash)}</span></div>
          <div class="kv"><span>Издержки с начала</span><span>${fmtR(Object.values(e.costByKind).reduce((a, b) => a + b, 0))}</span></div>
        </div>
        <table class="t dense"><thead><tr><th>Бумага</th><th class="r">Шт.</th><th class="r">Средняя</th><th class="r">P&amp;L</th></tr></thead><tbody>
          ${sessPapers(s).map(q => { const ps = e.pos[q.id], px = q.candles[last].c, pl = ps.qty * px - ps.cost;
            return `<tr><td>${pname(q)}</td><td class="r">${fmtN(ps.qty)}</td><td class="r">${ps.qty ? fmtP(ps.cost / ps.qty) : "—"}</td><td class="r ${cls(pl)}">${ps.qty ? fmtSR(pl) : "—"}</td></tr>`; }).join("")}
        </tbody></table></div>
      </div>
    </div>`;
  const ov = [];
  if (A.overlays.sma20) ov.push({ color: "#526ED3", values: Object.fromEntries(cc.map((_, t) => [t, t >= 19 ? sma(cc, t, 20) : null])) });
  if (A.overlays.sma50) ov.push({ color: "#8E5BD0", values: Object.fromEntries(cc.map((_, t) => [t, t >= 49 ? sma(cc, t, 50) : null])) });
  const levels = [];
  for (const o of activeOrders.filter(o => o.paper === p.id)) {
    const col = o.side === "buy" ? "#008764" : "#EB1700";
    if (o.limit) levels.push({ price: o.limit, color: col, label: `${ORDER_TYPES[o.type]}, ${fmtN(o.qty)} шт.` });
    if (o.stop) levels.push({ price: o.stop, color: "#E07B39", label: `Стоп, ${fmtN(o.qty)} шт.` });
    if (o.tp) levels.push({ price: o.tp, color: col, label: `Тейк, ${fmtN(o.qty)} шт.` });
    if (o.type === "trailing") levels.push({ price: o.peak * (1 - o.trail / 100), color: "#E07B39", label: `Трейлинг ${o.trail} %` });
  }
  const from = Math.max(0, T0 - 29);
  candleChart(document.getElementById("chart"), {
    candles: cc, from, last, slots: end - from + 1, height: 380, startT: T0 + 1, overlays: ov, levels,
    news: s.who === "human" ? V.news.filter(n => n.t <= last && (!n.sector || n.sector === p.sector)) : [],
    markers: visFills.filter(f => f.paper === p.id).map(f => ({ t: f.t, side: f.side, label: `${f.side === "buy" ? "Покупка" : "Продажа"} ${fmtN(f.qty)} шт. по ${fmtP(f.price)}` })),
    label: t => blind ? (t <= T0 ? String(t - T0) : "д" + dayOf(t)) : shortDate(t),
  });
}
function orderDesc(o) {
  const parts = [];
  if (o.limit) parts.push(`лимит ${fmtP(o.limit)}`);
  if (o.stop) parts.push(`стоп ${fmtP(o.stop)}`);
  if (o.tp) parts.push(`тейк ${fmtP(o.tp)}`);
  if (o.trail) parts.push(`отступ ${o.trail} %`);
  return parts.join(", ");
}
const STATUS = { active: ["info", "активна"], filled: ["ok", "исполнена"], partial: ["warn", "частично"], expired: ["", "истёк срок"], cancelled: ["", "отменена"], rejected: ["bad", "отклонена"] };
function ordersBlock(s, e, tab, ro, pname) {
  const last = s.last;
  if (tab === "active") {
    const list = e.orders.filter(o => o.status === "active" && o.t <= last);
    if (!list.length) return `<div class="empty">Активных заявок нет.</div>`;
    return `<table class="t dense"><thead><tr><th>Бумага</th><th>Тип</th><th class="r">Шт.</th><th>Условия</th><th>Срок</th><th></th></tr></thead><tbody>${list.map(o =>
      `<tr><td class="w"><span class="${o.side === "buy" ? "pos" : "neg"}">${o.side === "buy" ? "Купить" : "Продать"}</span> ${pname(paperById(o.paper))}</td><td class="w">${ORDER_TYPES[o.type]}</td>
       <td class="r">${fmtN(o.qty - o.filled)}</td><td class="small">${orderDesc(o) || "по рынку"}</td><td class="small w">${o.tif === "gtc" ? "до отмены" : "день"}</td>
       <td class="r">${ro ? "" : `<button class="btn s" data-act="cancelOrder" data-id="${o.id}">Отменить</button>`}</td></tr>`).join("")}</tbody></table>`;
  }
  if (tab === "fills") {
    const list = e.fills.filter(f => f.t <= last).slice().reverse();
    if (!list.length) return `<div class="empty">Исполнений пока нет. Заявка исполняется не раньше открытия следующей свечи.</div>`;
    return `<table class="t dense"><thead><tr><th>День</th><th>Бумага</th><th class="r">Шт.</th><th class="r">Цена</th><th>Пометка</th></tr></thead><tbody>${list.map(f =>
      `<tr><td class="w">${dayOf(f.t)}</td><td class="w"><span class="${f.side === "buy" ? "pos" : "neg"}">${f.side === "buy" ? "Покупка" : "Продажа"}</span> ${pname(paperById(f.paper))}</td>
       <td class="r">${fmtN(f.qty)}</td><td class="r">${fmtP(f.price)}</td><td class="small">${[f.partial ? '<span class="badge warn">частично</span>' : "", f.note ? esc(f.note) : "", f.because ? `<span class="because">${esc(f.because)}</span>` : ""].join(" ")}</td></tr>`).join("")}</tbody></table>`;
  }
  const rows = s.who === "human" ? s.journal.filter(j => j.t <= last).map(j => [j.t, j.cancel ? `Отмена заявки №${j.cancel}` : `№${s.journal.filter(x => !x.cancel).indexOf(j) + 1} ${j.side === "buy" ? "купить" : "продать"} ${pname(paperById(j.paper))}, ${ORDER_TYPES[j.type].toLowerCase()}, ${fmtN(j.qty)} шт. ${orderDesc(j)}`])
    : e.orders.filter(o => o.t <= last).map(o => [o.t, `${o.side === "buy" ? "купить" : "продать"} ${pname(paperById(o.paper))}, ${fmtN(o.qty)} шт.`]);
  if (!rows.length) return `<div class="empty">Журнал пуст. Каждая заявка записывается с номером свечи, которую вы видели.</div>`;
  let k = 0;
  return `<table class="t dense"><thead><tr><th>Свеча</th><th>Запись</th><th>Статус</th></tr></thead><tbody>${rows.map(([t, txt]) => {
    const o = txt.startsWith("Отмена") ? null : e.orders[k++], ss = o ? STATUS[o.status] : null;
    return `<tr><td class="w mono">${t - T0}</td><td class="small">${txt}</td><td>${ss ? `<span class="badge ${ss[0]}">${ss[1]}</span>` : ""}</td></tr>`; }).join("")}</tbody></table>`;
}
function ticketHtml(s, e, pname) {
  const A = state.arena, tk = A.ticket, p = paperById(A.paper), px = p.candles[s.last].c, pos = e.pos[p.id].qty;
  if (SELL_ONLY[tk.type]) tk.side = "sell";
  const f = (k, label, def) => `<div class="field"><label>${label}</label><input type="number" step="0.1" value="${tk[k] ?? def}" data-input="tk" data-k="${k}"></div>`;
  let extra = "";
  const r1 = v => Math.round(v * 10) / 10;
  if (tk.type === "limit") extra = f("limit", "Цена лимита", r1(px * (tk.side === "buy" ? 0.97 : 1.03)));
  if (tk.type === "stop") extra = f("stop", "Цена стопа", r1(px * (tk.side === "buy" ? 1.03 : 0.95)));
  if (tk.type === "stop_limit") extra = `<div class="fields f2">${f("stop", "Стоп", r1(px * (tk.side === "buy" ? 1.03 : 0.95)))}${f("limit", "Лимит", r1(px * (tk.side === "buy" ? 1.04 : 0.94)))}</div>`;
  if (tk.type === "take_profit") extra = f("tp", "Цена тейка", r1(px * 1.08));
  if (tk.type === "trailing") extra = f("trail", "Отступ от пика, %", 4);
  if (tk.type === "oco") extra = `<div class="fields f2">${f("tp", "Тейк", r1(px * 1.08))}${f("stop", "Стоп", r1(px * 0.94))}</div>`;
  const amount = tk.qty * px, k = V.costs.commission + V.costs.fee;
  const warn = tk.side === "sell" && pos === 0 ? "Позиции нет: продать нечего, шорт недоступен."
    : tk.side === "buy" && amount * (1 + k) > e.cash ? `Денег хватает на ${fmtN(Math.floor(e.cash / (px * (1 + k + V.costs.spread + V.costs.slippage))))} шт.` : "";
  return `<div class="ticket">
    <div class="field sel"><label>Бумага</label><select data-change="tkPaper">${sessPapers(s).map(q => `<option value="${q.id}" ${q.id === p.id ? "selected" : ""}>${pname(q)}, ${q.sector}</option>`).join("")}</select></div>
    <div class="seg wide buy-sell"><button class="buy ${tk.side === "buy" ? "on" : ""}" data-act="tkSide" data-v="buy" ${SELL_ONLY[tk.type] ? "disabled" : ""}>Купить</button><button class="sell ${tk.side === "sell" ? "on" : ""}" data-act="tkSide" data-v="sell">Продать</button></div>
    <div class="field sel"><label>Тип заявки</label><select data-change="tkType">${Object.entries(ORDER_TYPES).map(([k_, l]) => `<option value="${k_}" ${k_ === tk.type ? "selected" : ""}>${l}</option>`).join("")}</select></div>
    ${extra}
    <div class="field"><label>Количество, шт.</label><input type="number" step="100" min="1" value="${tk.qty}" data-input="tk" data-k="qty"><span class="suf">≈ ${fmtR(amount)}</span></div>
    <div class="pct">${[10, 25, 50, 100].map(x => `<button class="btn s" data-act="tkPct" data-v="${x}">${x} %</button>`).join("")}</div>
    <div class="seg wide"><button class="${tk.tif === "day" ? "on" : ""}" data-act="tkTif" data-v="day">На день</button><button class="${tk.tif === "gtc" ? "on" : ""}" data-act="tkTif" data-v="gtc">До отмены</button></div>
    <div class="hint">Исполнится не раньше открытия дня ${dayOf(s.last) + 1}. Комиссия ${fmtN(V.costs.commission * 100, 2)} %, сбор ${fmtN(V.costs.fee * 100, 2)} %${["market", "stop", "trailing"].includes(tk.type) ? ", спред и проскальзывание" : ""}; больше ${fmtN(V.costs.liquidity * 100)} % объёма свечи — частично.</div>
    ${warn ? `<div class="hint neg">${warn}</div>` : ""}
    <button class="btn primary l" data-act="placeOrder" ${s.last >= T0 + s.days ? "disabled" : ""}>Выставить заявку</button>
  </div>`;
}
ACT.tk = el => {
  const tk = state.arena.ticket, v = parseFloat(el.value);
  if (!isNaN(v)) tk[el.dataset.k] = el.dataset.k === "qty" ? Math.max(1, Math.round(v)) : v;
  if (el.dataset.k === "qty") { const suf = el.parentElement.querySelector(".suf"); if (suf) suf.textContent = "≈ " + fmtR(tk.qty * paperById(state.arena.paper).candles[arenaSession().last].c); }
};
ACT.tkSide = el => { state.arena.ticket.side = el.dataset.v; arena(); };
ACT.tkTif = el => { state.arena.ticket.tif = el.dataset.v; arena(); };
ACT.tkType = el => {
  const tk = state.arena.ticket;
  tk.type = el.value; delete tk.limit; delete tk.stop; delete tk.tp; delete tk.trail;
  tk.tif = tk.type === "market" ? "day" : tk.type === "limit" ? tk.tif : "gtc";
  arena();
};
ACT.tkPaper = el => { state.arena.paper = el.value; arena(); };
ACT.tkPct = el => {
  const s = arenaSession(), e = ensureEngine(s), tk = state.arena.ticket, p = paperById(state.arena.paper), px = p.candles[s.last].c;
  const k = +el.dataset.v / 100;
  tk.qty = Math.max(1, tk.side === "buy" ? Math.floor(e.cash * k / (px * 1.0025)) : Math.floor(e.pos[p.id].qty * k) || 1);
  arena();
};
ACT.placeOrder = () => {
  const s = arenaSession(), tk = state.arena.ticket, p = paperById(state.arena.paper), px = p.candles[s.last].c;
  const r1 = v => Math.round(v * 10) / 10;
  const j = { t: s.last, paper: p.id, side: tk.side, type: tk.type, qty: tk.qty, tif: tk.tif };
  const need = { limit: ["limit"], stop: ["stop"], stop_limit: ["stop", "limit"], take_profit: ["tp"], trailing: ["trail"], oco: ["tp", "stop"] }[tk.type] || [];
  const defaults = { limit: r1(px * (tk.side === "buy" ? 0.97 : 1.03)), stop: r1(px * (tk.side === "buy" ? 1.03 : 0.95)), tp: r1(px * 1.08), trail: 4 };
  if (tk.type === "stop_limit") defaults.limit = r1(px * (tk.side === "buy" ? 1.04 : 0.94));
  if (tk.type === "oco") defaults.stop = r1(px * 0.94);
  for (const k of need) j[k] = tk[k] ?? defaults[k];
  if (j.side === "sell" && tk.type !== "market" && tk.type !== "limit" && j.stop && j.stop >= px) return toast("Стоп для продажи ставится ниже текущей цены. Поднимите тейк или опустите стоп.");
  if (tk.type === "oco" && j.tp <= px) return toast("Тейк в OCO должен быть выше текущей цены.");
  s.journal.push(j);
  saveActive(s); engine = null;
  toast(`Заявка записана в журнал: свеча ${dayOf(s.last)}, ${ORDER_TYPES[tk.type].toLowerCase()}, ${fmtN(tk.qty)} шт.`, 2500);
  arena();
};
ACT.cancelOrder = el => {
  const s = arenaSession();
  s.journal.push({ t: s.last, cancel: +el.dataset.id });
  saveActive(s); engine = null; arena();
};
ACT.paperTab = el => { state.arena.paper = el.dataset.p; rerenderArena(); };
ACT.ov = el => { state.arena.overlays[el.dataset.k] = !state.arena.overlays[el.dataset.k]; rerenderArena(); };
ACT.arenaTab = el => { state.arena.tab = el.dataset.k; rerenderArena(); };
ACT.pauseNews = () => { state.arena.pauseNews = !state.arena.pauseNews; rerenderArena(); };
ACT.speed = el => { state.arena.speed = +el.dataset.v; if (state.arena.playing) { stopTimer(); startTimer(); } rerenderArena(); };
ACT.play = () => { state.arena.playing = !state.arena.playing; state.arena.playing ? startTimer() : stopTimer(); rerenderArena(); };
ACT.stepBar = () => { advance(); };
function curArena() { return (location.hash.startsWith("#/replay") ? state.replay : arenaSession()); }
function rerenderArena() { location.hash.startsWith("#/replay") ? replay(state.replay.id) : arena(); }
function startTimer() { stopTimer(); timer = setInterval(advance, { 1: 1500, 5: 330, 10: 160 }[state.arena.speed]); }
function stopTimer() { if (timer) clearInterval(timer); timer = null; }
function advance() {
  const s = curArena();
  if (!s) return stopTimer();
  const end = T0 + s.days;
  if (s.last >= end) return;
  s.last++;
  if (!location.hash.startsWith("#/replay")) saveActive(s);
  const news = s.who === "human" && V.news.some(n => n.t === s.last);
  if (news && state.arena.pauseNews && state.arena.playing) { state.arena.playing = false; stopTimer(); }
  if (s.last >= end) { state.arena.playing = false; stopTimer(); }
  rerenderArena();
  if (s.last >= end && !location.hash.startsWith("#/replay")) {
    modal(`<h2>Сессия завершена</h2><div>Все ${s.days} свечей пройдены. Отчёт раскроет реальный период и бумаги, сравнит ваши решения с алгоритмами и покажет цену каждого расхождения.</div>
      <div class="row"><span class="spacer"></span><button class="btn primary l" data-act="finishGo">Раскрыть период и открыть отчёт</button></div>`);
  }
}
function finishActive(goReport = true) {
  const s = activeSession();
  if (!s) return;
  const done = { ...s, finishedAt: dayOf(s.last) };
  delete done.last;
  saveUserSessions([...userSessions(), done]);
  saveActive(null); engine = null; stopTimer(); state.arena.playing = false; state.arena._restored = false;
  if (goReport) go("#/report/" + done.id);
}
ACT.finishGo = () => { closeModal(); finishActive(true); };
ACT.finish = () => {
  const s = activeSession();
  stopTimer(); state.arena.playing = false;
  modal(`<h2>Завершить сессию на дне ${dayOf(s.last)}?</h2><div>Оставшиеся ${s.days - dayOf(s.last)} свечей пройдут без новых решений: заявки «до отмены» продолжат работать, позиции досчитаются по последней свече.</div>
    <div class="row"><span class="spacer"></span><button class="btn" data-act="closeModal">Продолжить торговлю</button><button class="btn primary" data-act="finishGo">Завершить и открыть отчёт</button></div>`);
};

// =========================================================================================
// Отчёт
// =========================================================================================
function report(id) {
  const s = sessionById(id);
  if (!s) return go("#/history");
  crumbs([["История сессий", "#/history"], [`Отчёт ${id}`]]);
  const r = analysis(s), human = s.who === "human", c = cmpOf(s);
  const tab = state.tab[id] || (human ? "divs" : "trades");
  const ps = sessPapers(s), end = T0 + s.days;
  const algoOpts = V.algos.map(a => `<option value="${a.id}" ${a.id === c.primary ? "selected" : ""}>${esc(a.name)}</option>`).join("");
  const revealHtml = `<div class="panel"><div class="panel-h"><h3>${s.blind ? "Период раскрыт" : "Период и бумаги"}</h3><div class="right small muted">${s.blind ? "во время сессии были скрыты название, тикер и даты" : "неслепая сессия: всё было видно сразу"}</div></div>
    <div class="reveal">${ps.map(p => `<div><div class="small muted">${p.sector}</div>${s.blind ? `<div class="from">Бумага ${p.id}</div>` : ""}<div class="to">${p.ticker}</div><div class="small muted">${p.name}, 1 пункт = ${fmtP(p.real_start / 100)} ₽</div></div>`).join("")}
      <div><div class="small muted">Период</div>${s.blind ? `<div class="from">день 1 — день ${s.days}</div>` : ""}<div class="to">${dateOf(T0 + 1)} — ${dateOf(end)}</div><div class="small muted">весна 2020: обвал и отскок</div></div></div></div>`;
  let kpis, chartSeries, tabs, body;
  if (human) {
    const m = r.m, ma = r.ma, onPlace = (m.final - r.errSum) / V.capital - 1;
    kpis = `<div class="kpi"><div class="l">Ваш результат</div><div class="v ${cls(m.ret)}">${fmtPct(m.ret)}</div><div class="h">${fmtR(m.final)}</div></div>
      <div class="kpi"><div class="l">Алгоритм на вашем месте</div><div class="v ${cls(onPlace)}">${fmtPct(onPlace)}</div><div class="h">если бы в точках расхождений вы поступали как «${esc(r.primary.name)}»</div></div>
      <div class="kpi"><div class="l">Независимый портфель алгоритма</div><div class="v ${cls(ma.ret)}">${fmtPct(ma.ret)}</div><div class="h">тот же алгоритм с нуля, ${ma.trades} ${plural(ma.trades, "сделка", "сделки", "сделок")}</div></div>
      <div class="kpi"><div class="l">Рынок</div><div class="v ${cls(r.benchRet)}">${fmtPct(r.benchRet)}</div><div class="h">равные доли бумаг сессии</div></div>
      <div class="kpi"><div class="l">Издержки</div><div class="v">${fmtR(m.costs)}</div><div class="h">${m.trades} исполнений, частичных ${m.partial}</div></div>`;
    chartSeries = [
      { name: "Вы", color: "#526ED3", pts: [{ t: T0, v: V.capital }, ...r.human.equity], width: 2.5 },
      { name: r.primary.name, color: "#8E5BD0", pts: [{ t: T0, v: V.capital }, ...r.algo.equity] },
      { name: "Рынок", color: "#B8BBC8", pts: r.bench, dash: "5 4" },
    ];
    const cnt = t => r.divs.filter(d => t === "all" || d.type === t).length;
    tabs = [["divs", "Расхождения", r.divs.length], ["reverse", "Обратная проверка", r.reverse.length], ["trades", "Сделки", r.human.fills.length], ["news", "Новости", V.news.filter(n => n.t > T0 - 5 && n.t <= end).length], ["metrics", "Метрики и издержки", null]];
    if (tab === "divs") {
      const f = state.divFilter, list = r.divs.filter(d => f === "all" || d.type === f);
      const worst = r.divs.filter(d => d.type !== "news").sort((a, b) => a.impact - b.impact)[0];
      body = `<div class="panel-b" style="padding-top:12px">
        <div class="callout" style="margin-bottom:12px">${icon("info", 18)}<div>Расхождения обошлись вам в <b class="${cls(r.errSum)}">${fmtSR(r.errSum)}</b>${worst ? `, дороже всего — ${DIV_TYPES[worst.type].toLowerCase()} на дне ${dayOf(worst.t)} (${fmtSR(worst.impact)})` : ""}.
          Цена ошибки — разница результата за 10 свечей, если бы вы здесь поступили как алгоритм. Реакция на новость (1–2 свечи после неё) ошибкой не считается: алгоритм новостей не видит.</div></div>
        <div class="row" style="flex-wrap:wrap">${[["all", "Все"], ["extra", DIV_TYPES.extra], ["missed", DIV_TYPES.missed], ["timing", DIV_TYPES.timing], ["news", DIV_TYPES.news]].map(([k, l]) =>
          `<button class="chip ${f === k ? "on" : ""}" data-act="divFilter" data-k="${k}">${l}<span class="muted" style="font-weight:400">${cnt(k)}</span></button>`).join("")}</div></div>
        <div class="scroll"><table class="t"><thead><tr><th>День</th><th>Бумага</th><th>Тип</th><th>Вы</th><th>Алгоритм</th><th class="r">Цена ошибки</th><th>Причина из because</th>${c.consensus ? "<th>Консенсус</th>" : ""}</tr></thead><tbody>
        ${list.map(d => { const i = r.divs.indexOf(d), sel = state.divSel === i, p = paperById(d.paper);
          return `<tr class="click ${sel ? "sel" : ""}" data-act="divSel" data-i="${i}"><td class="w"><b>${dayOf(d.t)}</b> <span class="small muted">${shortDate(d.t)}</span></td><td class="w">${p.ticker} <span class="small muted">${p.sector}</span></td><td>${divBadge(d.type)}</td>
            <td class="small">${d.humanDid}</td><td class="small">${d.algoDid}</td>
            <td class="r">${d.type === "news" ? `<span class="faint">${fmtSR(d.impact)}</span><div class="small faint">не ошибка</div>` : `<span class="${cls(d.impact)}"><b>${fmtSR(d.impact)}</b></span><div class="small muted">${d.impact > 0 ? "здесь прав человек" : "в пользу алгоритма"}</div>`}</td>
            <td><span class="because">${esc(d.because)}</span>${d.news ? `<div class="small muted" style="margin-top:4px">новость: ${esc(d.news.text.slice(0, 60))}…</div>` : ""}</td>
            ${c.consensus ? `<td class="small w">${consensusText(d)}</td>` : ""}</tr>
            ${sel ? `<tr><td colspan="${c.consensus ? 8 : 7}" style="background:var(--alt);padding:12px 16px"><div class="small muted" style="margin-bottom:6px">${p.ticker}: свечи вокруг дня ${dayOf(d.t)}. ▲▼ синие — ваши исполнения, фиолетовые — сделки независимого портфеля алгоритма.</div><div class="chart-wrap panel" id="divchart"></div></td></tr>` : ""}`; }).join("")}
        </tbody></table></div>`;
    } else if (tab === "reverse") {
      body = `<div class="panel-b" style="padding-top:12px"><div class="callout y" style="margin-bottom:12px">${icon("info", 18)}<div>Прибыльные сделки, которых у алгоритма «${esc(r.primary.name)}» не было. Если за ними стоит правило, опишите его на DSL: так появляются новые эвристики. Защиты от подгонки нет — пользователю доверяем.</div></div></div>
        ${r.reverse.length ? `<table class="t"><thead><tr><th>Бумага</th><th>Вход</th><th>Выход</th><th class="r">Шт.</th><th class="r">Покупка</th><th class="r">Продажа</th><th class="r">Прибыль</th><th></th></tr></thead><tbody>
        ${r.reverse.map((x, i) => `<tr><td>${paperById(x.paper).ticker}</td><td class="w">день ${dayOf(x.buyT)}</td><td class="w">день ${dayOf(x.sellT)}</td><td class="r">${fmtN(x.qty)}</td><td class="r">${fmtP(x.buy)}</td><td class="r">${fmtP(x.sell)}</td>
          <td class="r pos"><b>${fmtSR(x.profit)}</b></td><td class="r"><button class="btn s" data-act="heuristic" data-sid="${s.id}" data-i="${i}">Написать эвристику</button></td></tr>`).join("")}</tbody></table>`
        : `<div class="empty">Прибыльных сделок, которых не было у алгоритма, в этой сессии нет.</div>`}`;
    } else if (tab === "trades") {
      body = fillsTable(r.human, false);
    } else if (tab === "news") {
      body = `<table class="t"><thead><tr><th>День</th><th>Сектор</th><th>Что видел человек</th><th>Оригинал</th><th>Ваша реакция</th></tr></thead><tbody>
        ${V.news.filter(n => n.t > T0 - 5 && n.t <= end).map(n => { const re = r.human.fills.find(f => f.t - 1 >= n.t && f.t - 1 <= n.t + 2 && (!n.sector || paperById(f.paper).sector === n.sector));
          return `<tr><td class="w">${n.t <= T0 ? "до старта" : dayOf(n.t)}<div class="small muted">${n.date}, ${n.time}</div></td><td>${sectorBadge(n.sector)}</td><td class="small">${esc(n.text)}</td><td class="small muted">${esc(n.original)}</td>
          <td class="small">${re ? `${re.side === "buy" ? "Покупка" : "Продажа"} ${paperById(re.paper).ticker} на дне ${dayOf(re.t)}` : '<span class="faint">нет</span>'}</td></tr>`; }).join("")}</tbody></table>`;
    } else body = metricsBlock(r.human, r.m);
  } else {
    const m = r.m, mn = r.mn;
    kpis = `<div class="kpi"><div class="l">Честный результат</div><div class="v ${cls(m.ret)}">${fmtPct(m.ret)}</div><div class="h">${fmtR(m.final)}</div></div>
      <div class="kpi"><div class="l">Наивный результат</div><div class="v ${cls(mn.ret)}">${fmtPct(mn.ret)}</div><div class="h">по close той же свечи, без издержек</div></div>
      <div class="kpi"><div class="l">Разница</div><div class="v">${fmtN((m.ret - mn.ret) * 100, 1)} п.п.</div><div class="h">задержка, издержки, ликвидность</div></div>
      <div class="kpi"><div class="l">Рынок</div><div class="v ${cls(r.benchRet)}">${fmtPct(r.benchRet)}</div><div class="h">равные доли бумаг сессии</div></div>
      <div class="kpi"><div class="l">Издержки</div><div class="v">${fmtR(m.costs)}</div><div class="h">${m.trades} исполнений, частичных ${m.partial}</div></div>`;
    chartSeries = [
      { name: "Честный", color: "#526ED3", pts: [{ t: T0, v: V.capital }, ...r.honest.engine.equity], width: 2.5 },
      { name: "Наивный", color: "#7A7D93", pts: [{ t: T0, v: V.capital }, ...r.naive.engine.equity], dash: "6 4" },
      { name: "Рынок", color: "#B8BBC8", pts: r.bench, dash: "5 4" },
    ];
    tabs = [["trades", "Сделки и причины", r.honest.engine.fills.length], ["delta", "Наивный и честный", null], ["metrics", "Метрики и издержки", null]];
    if (tab === "trades") body = fillsTable(r.honest.engine, true);
    else if (tab === "delta") {
      const ck = r.honest.engine.costByKind, total = (mn.final - m.final);
      const costSum = Object.values(ck).reduce((a, b) => a + b, 0);
      const rows = [["Задержка: исполнение по open следующей свечи и лимит ликвидности", total - costSum], ["Спред", ck.spread], ["Проскальзывание", ck.slippage], ["Комиссия брокера", ck.commission], ["Биржевой сбор", ck.fee]];
      const mx = Math.max(...rows.map(x => Math.abs(x[1])));
      body = `<div class="panel-b" style="padding-top:16px"><div class="row" style="gap:24px;margin-bottom:16px;flex-wrap:wrap"><div><div class="small muted">Наивный</div><div style="font-size:28px;font-weight:700" class="num">${fmtPct(mn.ret)}</div></div><div style="font-size:24px" class="faint">—</div>
        <div><div class="small muted">Честный</div><div style="font-size:28px;font-weight:700" class="num">${fmtPct(m.ret)}</div></div><div class="hint" style="max-width:420px">Разница разложена по вкладам в рублях. Подробное разложение на длинной истории — в карточке алгоритма, вкладка «Честность».</div></div>
        <div class="bars-h">${rows.map(([l, v]) => `<div class="bar-h"><span class="small">${l}</span><span class="track"><i style="left:0;width:${Math.abs(v) / mx * 100}%;background:${v >= 0 ? "var(--neg)" : "var(--pos)"}"></i></span><span class="small r num">${fmtSR(-v)}</span></div>`).join("")}</div></div>`;
    } else body = metricsBlock(r.honest.engine, m);
  }
  const lt = lightOf(s);
  document.getElementById("content").innerHTML = `
    ${head(`Отчёт сессии ${s.id}`, `${modeBadges(s)}<span>${esc(whoLabel(s))}</span><span>${esc(s.author)}, ${s.started}</span>${s.finishedAt && s.finishedAt < s.days ? `<span class="badge">завершена на дне ${s.finishedAt}</span>` : ""}`,
      `<button class="btn" data-go="#/replay/${s.id}">${icon("replay")}Воспроизвести</button>`)}
    <div class="panel"><div class="row" style="padding:12px 16px;gap:24px;flex-wrap:wrap">
      <div class="row">${lightHtml(lt, true)}<span class="small muted">Данные: ${LIGHT_WORD[lt[0]]}. Будущее: ${LIGHT_WORD[lt[1]]}${human ? ", новости только после публикации" : ""}. Издержки: ${LIGHT_WORD[lt[2]]}.</span></div>
      ${human ? `<span class="spacer"></span><div class="row"><div class="field sel" style="width:240px;padding-top:3px;padding-bottom:4px"><label>Сравнить с</label><select data-change="cmpPrimary" data-sid="${s.id}">${algoOpts}</select></div>
        <span class="row small"><button class="toggle ${c.consensus ? "on" : ""}" data-act="cmpCons" data-sid="${s.id}"></button>Консенсус ${V.algos.length} алгоритмов</span></div>` : ""}
    </div></div>
    ${revealHtml}
    <div class="panel"><div class="kpis">${kpis}</div></div>
    <div class="panel"><div class="panel-h"><h3>Кривая капитала</h3><div class="right legend">${chartSeries.map(se => `<span><i style="background:${se.color}"></i>${esc(se.name)}</span>`).join("")}${human ? '<span><i style="background:#FFC700;width:3px;height:10px"></i>расхождения</span>' : ""}</div></div>
      <div class="chart-wrap" id="eqchart" style="padding:0 4px 8px 8px"></div></div>
    <div class="panel"><div class="tabs">${tabs.map(([k, l, n]) => `<button class="${tab === k ? "on" : ""}" data-act="repTab" data-sid="${s.id}" data-k="${k}">${l}${n != null ? `<span class="cnt">${n}</span>` : ""}</button>`).join("")}</div>${body}</div>
    ${disclaimer()}`;
  lineChart(document.getElementById("eqchart"), {
    series: chartSeries, height: 260, base: V.capital, label: shortDate, yfmt: v => fmtN(v / 1000) + " тыс.",
    marks: human ? r.divs.filter(d => d.type !== "news").map(d => ({ t: d.t })) : [],
  });
  if (human && tab === "divs" && state.divSel != null && r.divs[state.divSel]) {
    const d = r.divs[state.divSel], p = paperById(d.paper), from = Math.max(0, d.t - 20), to = Math.min(end, d.t + 12);
    candleChart(document.getElementById("divchart"), {
      candles: p.candles, from, last: to, slots: to - from + 1, height: 240, volume: false,
      markers: [...r.human.fills.filter(f => f.paper === p.id).map(f => ({ t: f.t, side: f.side, color: "#526ED3", label: `Вы: ${f.side === "buy" ? "покупка" : "продажа"} ${fmtN(f.qty)} шт.` })),
                ...r.algo.fills.filter(f => f.paper === p.id).map(f => ({ t: f.t, side: f.side, color: "#8E5BD0", label: `Алгоритм: ${f.because}` }))],
      levels: [], news: V.news.filter(n => !n.sector || n.sector === p.sector), label: shortDate,
      overlays: r.primary.impl.kind === "sma" ? [{ color: "#526ED3", values: Object.fromEntries(p.candles.map((_, t) => [t, t >= 19 ? sma(p.candles, t, 20) : null])) },
                                                 { color: "#8E5BD0", values: Object.fromEntries(p.candles.map((_, t) => [t, t >= 49 ? sma(p.candles, t, 50) : null])) }] : [],
    });
  }
}
function consensusText(d) {
  const { agree, total } = d.consensus;
  const verb = d.type === "missed" ? (d.side === "buy" ? "купили бы" : "продали бы") : d.type === "timing" ? "поступили бы иначе" : (d.side === "buy" ? "не покупали бы" : "не продавали бы");
  return `<b>${agree} из ${total}</b> ${verb}`;
}
function fillsTable(e, withBecause) {
  if (!e.fills.length) return `<div class="empty">Сделок не было.</div>`;
  return `<div class="scroll"><table class="t"><thead><tr><th>День</th><th>Бумага</th><th>Сторона</th><th>Заявка</th><th class="r">Шт.</th><th class="r">Цена</th><th class="r">Издержки</th><th>${withBecause ? "Причина из because" : "Пометки"}</th></tr></thead><tbody>
    ${e.fills.map(f => `<tr><td class="w">${dayOf(f.t)} <span class="small muted">${shortDate(f.t)}</span></td><td>${paperById(f.paper).ticker}</td><td class="${f.side === "buy" ? "pos" : "neg"}">${f.side === "buy" ? "Покупка" : "Продажа"}</td>
      <td class="small w">${ORDER_TYPES[f.type]}</td><td class="r">${fmtN(f.qty)}</td><td class="r">${fmtP(f.price)}</td><td class="r">${fmtR(Object.values(f.cost).reduce((a, b) => a + b, 0))}</td>
      <td class="small">${withBecause && f.because ? `<span class="because">${esc(f.because)}</span> ` : ""}${f.partial ? '<span class="badge warn">частично</span> ' : ""}${f.note ? `<span class="${/одной свечой/.test(f.note) ? "badge warn" : "muted"}">${esc(f.note)}</span>` : ""}</td></tr>`).join("")}</tbody></table></div>`;
}
function metricsBlock(e, m) {
  const ck = e.costByKind, mx = Math.max(...Object.values(ck), 1);
  return `<div class="grid g-12" style="padding:16px">
    <div class="s-6"><div class="kv"><span>Итоговый капитал</span><span>${fmtR(m.final)}</span></div><div class="kv"><span>Доходность</span><span class="${cls(m.ret)}">${fmtPct(m.ret)}</span></div>
      <div class="kv"><span>Макс. просадка</span><span class="neg">${fmtPct(m.dd)}</span></div><div class="kv"><span>Sharpe, годовой</span><span>${fmtN(m.sharpe, 2)}</span></div>
      <div class="kv"><span>Исполнений</span><span>${m.trades}</span></div><div class="kv"><span>Частичных исполнений</span><span>${m.partial}</span></div>
      <div class="kv"><span>Отклонённых заявок</span><span>${m.rejected}</span></div><div class="kv"><span>Стоп и тейк одной свечой</span><span>${m.pessimistic}</span></div></div>
    <div class="s-6"><h3 style="margin-bottom:12px">Издержки по видам, всего ${fmtR(m.costs)}</h3><div class="bars-h">
      ${[["Комиссия брокера", ck.commission], ["Биржевой сбор", ck.fee], ["Спред", ck.spread], ["Проскальзывание", ck.slippage]].map(([l, v]) =>
        `<div class="bar-h" style="grid-template-columns:150px 1fr 90px"><span class="small">${l}</span><span class="track"><i style="left:0;width:${v / mx * 100}%;background:var(--accent)"></i></span><span class="small r num">${fmtR(v)}</span></div>`).join("")}</div>
      <div class="hint" style="margin-top:12px">Исполнение по open следующей свечи, не больше ${fmtN(V.costs.liquidity * 100)} % объёма свечи. Маржи, шорта и пополнений нет.</div></div></div>`;
}
ACT.repTab = el => { state.tab[el.dataset.sid] = el.dataset.k; state.divSel = null; report(el.dataset.sid); };
ACT.divFilter = el => { state.divFilter = el.dataset.k; state.divSel = null; report(location.hash.split("/")[2]); };
ACT.divSel = el => { const i = +el.dataset.i; state.divSel = state.divSel === i ? null : i; report(location.hash.split("/")[2]); };
ACT.cmpPrimary = el => { const s = sessionById(el.dataset.sid); state.cmp[s.id] = { ...cmpOf(s), primary: el.value }; state.divSel = null; report(s.id); };
ACT.cmpCons = el => { const s = sessionById(el.dataset.sid), c = cmpOf(s); state.cmp[s.id] = { ...c, consensus: !c.consensus }; report(s.id); };
ACT.heuristic = el => {
  const s = sessionById(el.dataset.sid), x = analysis(s).reverse[+el.dataset.i], p = paperById(x.paper);
  state.draft = { name: `Эвристика: ${p.sector.toLowerCase()} на дне ${dayOf(x.buyT)}`, code: [
    `algorithm "Моя эвристика"`, `// Из обратной проверки ${s.id}: ${p.ticker}, день ${dayOf(x.buyT)} — день ${dayOf(x.sellT)}, ${fmtSR(x.profit)}`,
    "param size = 20%", "", "let r = rsi(close, 14)", "let vol_avg = sma(volume, 20)", "",
    "when r < 25 and volume > vol_avg * 1.5 and position = 0 -> buy size equity",
    '  because "капитуляция: RSI = {r}, объём в 1,5 раза выше среднего"',
    "when close > sma(close, 20) * 1.15 -> sell all",
    '  because "отскок исчерпан: цена на 15 % выше SMA20"'].join("\n") };
  go("#/algo/new");
};

// =========================================================================================
// История
// =========================================================================================
function history() {
  crumbs([["История сессий"]]);
  const h = state.hist;
  const list = allSessions().filter(s => (h.who === "all" || s.who === h.who) && (!h.blind || s.blind));
  document.getElementById("content").innerHTML = `
    ${head("История сессий", "Каждая сессия воспроизводится: ручная — по журналу заявок, алгоритм — детерминированно.", `<button class="btn primary" data-go="#/new">${icon("plus")}Новая сессия</button>`)}
    <div class="panel"><div class="row" style="padding:12px 16px;flex-wrap:wrap;gap:16px">
      <div class="seg">${[["all", "Все"], ["human", "Люди"], ["algo", "Алгоритмы"]].map(([k, l]) => `<button class="${h.who === k ? "on" : ""}" data-act="hist" data-k="who" data-v="${k}">${l}</button>`).join("")}</div>
      <span class="row"><button class="toggle ${h.blind ? "on" : ""}" data-act="hist" data-k="blind" data-v="${!h.blind}"></button>Только слепые</span>
      <span class="spacer"></span>${lightLegend()}<span class="muted small">${list.length} ${plural(list.length, "сессия", "сессии", "сессий")}</span></div>
      ${sessionsTable(list, false)}</div>
    <div class="hint">Неслепые сессии участвуют во всех сравнениях наравне со слепыми. Цена расхождений — сколько человек потерял (−) или выиграл (+) относительно основного алгоритма на своём месте.</div>
    ${disclaimer()}`;
}
ACT.hist = el => { state.hist[el.dataset.k] = el.dataset.k === "blind" ? el.dataset.v === "true" : el.dataset.v; history(); };

// =========================================================================================
// Мастерская
// =========================================================================================
function allAlgos() { return [...V.algos, ...userAlgos()]; }
function regimeHtml(rg) {
  if (!rg) return '<span class="faint small">считается</span>';
  const mx = 7, bar = (v, l) => `<i title="${l}: ${fmtN(v, 1)} %" style="height:${Math.max(3, Math.abs(v) / mx * 26)}px;background:${v >= 0 ? "var(--up)" : "var(--down)"};opacity:${v >= 0 ? 1 : .8}"></i>`;
  return `<span class="regime">${bar(rg.up, "Рост")}${bar(rg.down, "Падение")}${bar(rg.flat, "Боковик")}</span>`;
}
function workshop() {
  crumbs([["Мастерская"]]);
  const w = state.ws;
  let list = allAlgos().filter(a => (w.filter === "all" || (w.filter === "mine" && a.author === DATA.user) || (w.filter === "forks" && a.forked_from)) && (!w.q || a.name.toLowerCase().includes(w.q.toLowerCase())));
  list = list.filter(a => !(state.hidden?.[a.id]) || w.filter === "mine");
  list.sort((a, b) => (b.rating?.score || 0) - (a.rating?.score || 0));
  document.getElementById("content").innerHTML = `
    ${head("Мастерская", "Открытая бесплатная библиотека алгоритмов под MIT. Опубликованные версии неизменяемы, форки сохраняют автора.", `<button class="btn primary" data-go="#/algo/new">${icon("plus")}Создать алгоритм</button>`)}
    <div class="grid g-12">
      <div class="panel s-12"><div class="row" style="padding:12px 16px;flex-wrap:wrap">
        <div class="seg">${[["all", "Все"], ["mine", "Мои"], ["forks", "Форки"]].map(([k, l]) => `<button class="${w.filter === k ? "on" : ""}" data-act="wsF" data-v="${k}">${l}</button>`).join("")}</div>
        <div class="field" style="width:260px;padding:4px 12px"><input placeholder="Найти алгоритм" value="${esc(w.q)}" data-input="wsQ"></div>
        <span class="spacer"></span><span class="small muted">Сортировка: рейтинг</span></div>
        <div class="scroll"><table class="t"><thead><tr><th>Алгоритм</th><th>Автор</th><th>Версия</th><th>Рейтинг</th><th class="r">Медиана окна</th><th class="r">Прибыльных окон</th><th>Рост, падение, боковик</th><th>Линтер</th><th class="r">Форки</th></tr></thead><tbody>
        ${list.map(a => `<tr class="click" data-go="#/algo/${a.id}"><td style="min-width:240px"><b>${esc(a.name)}</b>${a.forked_from ? ` <span class="badge">${icon("fork", 12)}форк</span>` : ""}${a.user ? ' <span class="badge info">черновик</span>' : ""}<div class="small muted">${esc(a.desc)}</div></td>
          <td class="w">${esc(a.author)}</td><td class="w">v${a.version}</td><td>${a.rating ? scoreHtml(a.rating.score) : '<span class="faint small">считается</span>'}</td>
          <td class="r">${a.rating?.median || "—"}</td><td class="r">${a.rating?.profitable || "—"}</td><td>${regimeHtml(a.rating?.regimes)}</td>
          <td>${(a.lint || []).length ? `<span class="badge warn">${a.lint.length} ${plural(a.lint.length, "константа", "константы", "констант")}</span>` : '<span class="badge ok">чисто</span>'}</td><td class="r">${a.forks || 0}</td></tr>`).join("")}
        </tbody></table></div></div>
      <div class="col s-6" style="gap:16px">
        <div class="panel"><div class="panel-h"><h3>Как считается рейтинг</h3></div><div class="panel-b small col" style="gap:10px">
          <div>Платформа сама прогоняет каждую версию на 200 случайных закрытых окнах истории, как «слепую дату» у людей.</div>
          <div>Метрики — после издержек, с разбивкой по режимам рынка: рост, падение, боковик.</div>
          <div>Рейтинг привязан к версии. Новая версия считается заново.</div>
          <div>Предупреждения линтера видны на карточке, но рейтинг не снижают.</div></div></div></div>
        <div class="col s-6" style="gap:16px"><div class="panel"><div class="panel-h"><h3>Лицензия</h3></div><div class="panel-b small col" style="gap:10px">
          <div><span class="badge info">MIT</span> Все алгоритмы открыты и бесплатны, автор указан.</div>
          <div>Автор может скрыть алгоритм из каталога: форки и прошлые прогоны продолжают работать. Удаление насовсем — через модерацию.</div></div></div>
      </div>
    </div>${disclaimer()}`;
}
ACT.wsF = el => { state.ws.filter = el.dataset.v; workshop(); };
ACT.wsQ = el => { state.ws.q = el.value; clearTimeout(window._wq); window._wq = setTimeout(() => { workshop(); const i = document.querySelector('[data-input="wsQ"]'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }, 250); };

function highlight(line, magic = []) {
  let h = esc(line);
  if (/^\s*\/\//.test(line)) return `<span class="cm">${h}</span>`;
  const strs = [];
  h = h.replace(/&quot;.*?&quot;/g, m => { strs.push(m); return `\u0001${String.fromCharCode(97 + strs.length - 1)}\u0001`; });
  for (const c of magic) h = h.replace(new RegExp(`(?<![\\w.])${c.replace(".", "\\.")}(?![\\w.])`), `<span class="magic numl" title="Магическая константа: вынесите в параметр">${c}</span>`);
  h = h.replace(/(?<![\w">])(\d[\d_.]*%?)(?![\w<])/g, '<span class="numl">$1</span>');
  h = h.replace(/\b(algorithm|param|let|when|and|or|buy|sell|all|equity|crosses_above|crosses_below|fork|of|by|version)\b/g, '<span class="kw">$1</span>');
  h = h.replace(/\bbecause\b/g, '<span class="bc"><b>because</b></span>');
  h = h.replace(/\u0001([a-z])\u0001/g, (_, i) => `<span class="${/because/.test(line) ? "bc" : "str"}">${strs[i.charCodeAt(0) - 97]}</span>`);
  return h;
}
// Линтер магических констант: числа вне строк param, кроме 0 и 1
function lintCode(lines) {
  const out = [];
  lines.forEach((l, i) => {
    if (/^\s*(param|algorithm|fork|\/\/)/.test(l) || /^\s*because/.test(l)) return;
    const body = l.replace(/"[^"]*"/g, "");
    for (const m of body.matchAll(/(?<![\w.\[])(\d+(?:\.\d+)?)(?![\w.%\]])/g)) {
      if (m[1] === "0" || m[1] === "1") continue;
      out.push({ line: i + 1, const: m[1] });
    }
  });
  return out;
}
function algoCard(id) {
  const a = algoById(id);
  if (!a) return go("#/workshop");
  crumbs([["Мастерская", "#/workshop"], [a.name]]);
  const tab = state.tab["algo-" + id] || "code";
  const code = (state.fixed?.[id]) || a.dsl;
  const lint = lintCode(code);
  const hidden = state.hidden?.[id];
  const mine = a.author === DATA.user;
  const tabs = [["code", "Код"], ["rating", "Рейтинг"], ["versions", "Версии и форки"], ["honesty", "Честность"]];
  if (id === "sma") tabs.push(["wf", "Walk-forward"]);
  let body = "";
  if (tab === "code") {
    const params = code.filter(l => /^param /.test(l)).map(l => l.replace("param ", "").split(" = "));
    body = `<div class="grid g-12" style="padding:16px;gap:16px">
      <div class="s-8 panel" style="overflow:hidden"><div class="panel-h"><h3>DSL</h3><div class="right"><span class="badge">только чтение: версия опубликована</span></div></div>
        <div class="code">${code.map((l, i) => `<div class="ln ${lint.some(x => x.line === i + 1) ? "warn" : ""}"><span>${highlight(l, lint.filter(x => x.line === i + 1).map(x => x.const)) || " "}</span></div>`).join("")}</div></div>
      <div class="s-4 col" style="gap:16px">
        <div class="panel"><div class="panel-h"><h3>Параметры</h3></div><table class="t dense"><tbody>${params.map(([n, v]) => `<tr><td class="mono">${n}</td><td class="r mono">${v}</td></tr>`).join("")}</tbody></table>
          <div class="panel-b hint" style="padding-top:8px">Параметры перебирает walk-forward. Константы в коде линтер просит вынести сюда.</div></div>
        <div class="panel"><div class="panel-h"><h3>Линтер</h3><div class="right">${lint.length ? `<span class="badge warn">${lint.length}</span>` : '<span class="badge ok">чисто</span>'}</div></div>
          <div class="panel-b col">${lint.length ? lint.map(x => `<div class="row" style="align-items:flex-start"><span class="badge warn">стр. ${x.line}</span><div style="flex:1" class="small">Константа <span class="mono">${x.const}</span> — вынесите в именованный параметр, чтобы её перебирал walk-forward.</div>
              <button class="btn s" data-act="fixConst" data-id="${id}" data-line="${x.line}" data-c="${x.const}">Вынести</button></div>`).join("")
            : '<div class="small muted">Магических констант нет.</div>'}<div class="hint">Предупреждения видны на карточке и рейтинг не снижают.</div></div></div>
        <div class="panel"><div class="panel-h"><h3>Чтение будущего</h3><div class="right"><span class="badge ok">OK</span></div></div>
          <div class="panel-b small">Все ряды читаются до бара t включительно, сделки исполняются по open t+1. Новости алгоритму недоступны.</div></div>
      </div></div>`;
  } else if (tab === "rating") {
    const rt = a.rating;
    if (!rt) body = `<div class="empty">Рейтинг считается: платформа прогоняет версию на 200 случайных закрытых окнах. Обычно это занимает несколько минут.</div>`;
    else {
      const r_ = rng(rt.score), hist = Array.from({ length: 16 }, (_, i) => Math.round(Math.exp(-((i - 8 - (rt.score - 60) / 8) ** 2) / 10) * 34 + r_() * 5));
      const hm = Math.max(...hist);
      body = `<div class="kpis" style="border-bottom:1px solid var(--div)">
        <div class="kpi"><div class="l">Рейтинг</div><div class="v">${rt.score}</div><div class="h">из 100, версия ${a.version}</div></div>
        <div class="kpi"><div class="l">Закрытых окон</div><div class="v">${rt.windows}</div><div class="h">случайные, по 60 свечей</div></div>
        <div class="kpi"><div class="l">Медиана окна</div><div class="v">${rt.median}</div><div class="h">после издержек</div></div>
        <div class="kpi"><div class="l">Прибыльных окон</div><div class="v">${rt.profitable}</div><div class="h">доля окон с плюсом</div></div>
        <div class="kpi"><div class="l">Худшая просадка</div><div class="v neg">${rt.dd}</div><div class="h">медиана по окнам</div></div></div>
        <div class="grid g-12" style="padding:16px">
          <div class="s-6"><h3 style="margin-bottom:12px">По режимам рынка</h3><div class="bars-h">${[["Рост", rt.regimes.up], ["Падение", rt.regimes.down], ["Боковик", rt.regimes.flat]].map(([l, v]) =>
            `<div class="bar-h" style="grid-template-columns:90px 1fr 70px"><span>${l}</span><span class="track"><i style="${v >= 0 ? "left:50%" : `left:${50 - Math.abs(v) / 8 * 50}%`};width:${Math.abs(v) / 8 * 50}%;background:${v >= 0 ? "var(--up)" : "var(--down)"}"></i></span><span class="r num ${cls(v)}">${v > 0 ? "+" : ""}${fmtN(v, 1)} %</span></div>`).join("")}</div>
            <div class="hint" style="margin-top:12px">Средняя доходность окна в каждом режиме. Слабые места алгоритма видны здесь и в разборах расхождений с людьми.</div></div>
          <div class="s-6"><h3 style="margin-bottom:12px">Доходность по окнам</h3><div class="row" style="align-items:flex-end;height:120px;gap:3px">${hist.map((v, i) => `<i style="flex:1;height:${v / hm * 110}px;background:${i < 7 ? "var(--down)" : "var(--up)"};opacity:.75;border-radius:3px 3px 0 0;display:block"></i>`).join("")}</div>
            <div class="row small muted" style="justify-content:space-between;margin-top:4px"><span>−12 %</span><span>0</span><span>+12 %</span></div></div></div>`;
    }
  } else if (tab === "versions") {
    const vs = V.versions[id] || [[a.version, a.updated, "c3e1…9f27", "Первая публикация"]];
    const fk = V.forks[id] || [];
    body = `<div class="grid g-12" style="padding:16px">
      <div class="s-7"><h3 style="margin-bottom:8px">Версии</h3><table class="t"><thead><tr><th>Версия</th><th>Дата</th><th>sha</th><th>Что изменилось</th><th></th></tr></thead><tbody>
        ${vs.map(([v, d, sha, what], i) => `<tr><td><b>v${v}</b> ${i === 0 ? '<span class="badge ok">текущая</span>' : ""}</td><td class="w">${d}</td><td class="mono">${sha}</td><td class="small">${what}</td><td class="r"><span class="badge">неизменяема</span></td></tr>`).join("")}</tbody></table>
        <div class="hint" style="margin-top:8px">Правка опубликованной версии создаёт новую. Прогоны и рейтинг ссылаются на конкретную версию.</div></div>
      <div class="s-5"><h3 style="margin-bottom:8px">Форки</h3>${fk.length ? `<table class="t"><tbody>${fk.map(([n, au, v]) => `<tr><td>${icon("fork", 14)} <b>${n}</b><div class="small muted">${au}, ${v}</div></td></tr>`).join("")}</tbody></table>`
        : a.forked_from ? `<div class="callout">${icon("fork", 18)}<div>Это форк «<a href="#/algo/${a.forked_from[0]}">${esc(algoById(a.forked_from[0]).name)}</a>» v${a.forked_from[1]}, исходный автор — ${a.forked_from[2]}.</div></div>` : '<div class="empty">Форков пока нет.</div>'}</div></div>`;
  } else if (tab === "honesty") {
    if (id === "sma") {
      const mx = Math.max(...V1.delta.map(x => Math.abs(x[1])));
      body = `<div class="panel-b" style="padding-top:16px"><div class="row" style="gap:24px;flex-wrap:wrap;margin-bottom:16px">
        <div><div class="small muted">Наивный прогон, SBER и др. 2020–2025</div><div style="font-size:28px;font-weight:700">${V1.result_naive.total}</div></div><div class="faint" style="font-size:24px">—</div>
        <div><div class="small muted">Честный прогон</div><div style="font-size:28px;font-weight:700">${V1.result_honest.total}</div></div>
        <div class="callout y" style="flex:1;min-width:260px">${icon("info", 18)}<div>Издержки и задержка съели 62 % наивной прибыли. Всего издержек ${V1.costs_total}.</div></div></div>
        <div class="bars-h">${V1.delta.map(([l, v, rub]) => `<div class="bar-h" style="grid-template-columns:280px 1fr 140px"><span class="small">${l}</span><span class="track"><i style="left:0;width:${Math.abs(v) / mx * 100}%;background:var(--neg)"></i></span><span class="small r num">${fmtN(v, 1)} п.п.${rub ? `, ${rub}` : ""}</span></div>`).join("")}</div>
        <h3 style="margin:20px 0 8px">Проверка чтения будущего на прошлых версиях</h3>
        <table class="t"><tbody>${V1.lookahead.map(x => `<tr><td class="w"><span class="badge ${{ ok: "ok", warning: "warn", error: "bad" }[x.level]}">${{ ok: "OK", warning: "подозрительно", error: "ошибка" }[x.level]}</span></td><td class="mono w">стр. ${x.line}: ${esc(x.code)}</td><td class="small">${esc(x.msg)}</td></tr>`).join("")}</tbody></table>
        <h3 style="margin:20px 0 8px">Воспроизводимость</h3>${Object.entries({ "Прогон": V1.repro.run, "Датасет": V1.repro.dataset, "Стратегия": V1.repro.strategy, "Движок": V1.repro.engine, "Seed": V1.repro.seed }).map(([k, v]) => `<div class="kv"><span>${k}</span><span class="mono">${v}</span></div>`).join("")}</div>`;
    } else {
      const ps = V.papers, h = metrics(runAlgo(a, ps).engine), n = metrics(runAlgo(a, ps, { naive: true }).engine);
      body = `<div class="panel-b" style="padding-top:16px"><div class="row" style="gap:24px;flex-wrap:wrap">
        <div><div class="small muted">Наивный прогон на демо-окне</div><div style="font-size:28px;font-weight:700">${fmtPct(n.ret)}</div></div><div class="faint" style="font-size:24px">—</div>
        <div><div class="small muted">Честный прогон</div><div style="font-size:28px;font-weight:700">${fmtPct(h.ret)}</div></div>
        <div class="hint" style="max-width:420px">Разница — задержка исполнения до open следующей свечи, спред, проскальзывание, комиссия, сбор и лимит ликвидности. Издержки: ${fmtR(h.costs)}.</div></div></div>`;
    }
  } else if (tab === "wf") {
    const wf = V1.walk_forward, mx = Math.max(...wf.map(x => Math.max(Math.abs(x.test_ret), x.train_ret)));
    body = `<div class="kpis" style="border-bottom:1px solid var(--div)">${[["Окон", V1.wf_summary.windows], ["Прибыльных вне выборки", V1.wf_summary.positive], ["В выборке", V1.wf_summary.is_avg], ["Вне выборки", V1.wf_summary.oos_avg], ["Деградация", V1.wf_summary.degradation]].map(([l, v]) => `<div class="kpi"><div class="l">${l}</div><div class="v" style="font-size:22px">${v}</div></div>`).join("")}</div>
      <div class="panel-b" style="padding-top:12px"><div class="hint" style="margin-bottom:8px">1 год подбора, 3 месяца проверки, сдвиг 3 месяца. ${V1.wf_summary.stable_param}.</div>
      <div class="row" style="align-items:center;height:160px;gap:4px">${wf.map(x => `<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;height:160px;position:relative" title="Окно ${x.n}: подбор ${fmtN(x.train_ret, 1)} %, проверка ${fmtN(x.test_ret, 1)} %, параметры ${x.params}">
        <i style="position:absolute;bottom:80px;width:40%;left:10%;height:${x.train_ret / mx * 76}px;background:var(--bench);border-radius:2px 2px 0 0"></i>
        <i style="position:absolute;${x.test_ret >= 0 ? "bottom:80px" : "top:80px"};width:40%;left:50%;height:${Math.abs(x.test_ret) / mx * 76}px;background:${x.test_ret >= 0 ? "var(--up)" : "var(--down)"};border-radius:2px"></i></div>`).join("")}</div>
      <div class="legend" style="margin-top:8px"><span><i style="background:var(--bench)"></i>в выборке</span><span><i style="background:var(--up)"></i>вне выборки</span></div></div>`;
  }
  document.getElementById("content").innerHTML = `
    ${head(esc(a.name), `<span class="badge ok">v${a.version} опубликована</span><span class="badge info">MIT</span><span>${esc(a.author)}</span>${a.forked_from ? `<span>${icon("fork", 14)} форк «${esc(algoById(a.forked_from[0]).name)}» v${a.forked_from[1]}, автор ${a.forked_from[2]}</span>` : ""}${hidden ? '<span class="badge warn">скрыт из каталога</span>' : ""}`,
      `${mine ? `<button class="btn" data-act="hideAlgo" data-id="${id}">${icon("eye")}${hidden ? "Вернуть в каталог" : "Скрыть из каталога"}</button>` : ""}
       <button class="btn" data-act="forkAlgo" data-id="${id}">${icon("fork")}Форкнуть</button>
       <button class="btn primary" data-act="useAlgo" data-id="${id}">${icon("play")}Запустить на сессии</button>`)}
    <div class="panel"><div class="kpis">
      <div class="kpi"><div class="l">Рейтинг</div><div class="v">${a.rating ? a.rating.score : "—"}</div><div class="h">на 200 закрытых окнах</div></div>
      <div class="kpi"><div class="l">Прогонов</div><div class="v">${a.runs || 0}</div><div class="h">людей сравнивали с ним</div></div>
      <div class="kpi"><div class="l">Форков</div><div class="v">${a.forks || 0}</div><div class="h">с указанием автора</div></div>
      <div class="kpi"><div class="l">Линтер</div><div class="v">${lint.length}</div><div class="h">${lint.length ? "предупреждений, рейтинг не снижают" : "предупреждений нет"}</div></div>
    </div></div>
    <div class="panel"><div class="tabs">${tabs.map(([k, l]) => `<button class="${tab === k ? "on" : ""}" data-act="algoTab" data-id="${id}" data-k="${k}">${l}</button>`).join("")}</div>${body}</div>
    ${disclaimer()}`;
}
ACT.algoTab = el => { state.tab["algo-" + el.dataset.id] = el.dataset.k; algoCard(el.dataset.id); };
ACT.fixConst = el => {
  const id = el.dataset.id, a = algoById(id);
  state.fixed = state.fixed || {};
  const code = (state.fixed[id] || a.dsl).slice(), ln = +el.dataset.line - 1, c = el.dataset.c;
  const known = (a.lint || []).find(x => x.const === c);
  const name = known ? known.name : "p_" + c.replace(".", "_");
  code[ln] = code[ln].replace(new RegExp(`(?<![\\w.])${c.replace(".", "\\.")}(?![\\w.])`), name);
  const lastParam = code.reduce((k, l, i) => /^param /.test(l) ? i : k, 0);
  code.splice(lastParam + 1, 0, `param ${name} = ${c}`);
  state.fixed[id] = code;
  toast(`Константа ${c} вынесена в параметр ${name}. Чтобы изменение попало в каталог, форкните алгоритм или опубликуйте новую версию.`);
  algoCard(id);
};
ACT.hideAlgo = el => { state.hidden = state.hidden || {}; state.hidden[el.dataset.id] = !state.hidden[el.dataset.id]; algoCard(el.dataset.id); };
ACT.forkAlgo = el => {
  const a = algoById(el.dataset.id);
  state.draft = { name: `${a.name} (форк)`, forked_from: [a.id, a.version, a.author], code: (state.fixed?.[a.id] || a.dsl).map((l, i) => i === 0 ? `algorithm "${a.name} (форк)"` : l)
    .join("\n").replace(/^(algorithm .*)$/m, `$1\nfork of "${a.name}" v${a.version} by "${a.author}"`) };
  go("#/algo/new");
};
ACT.useAlgo = el => {
  const id = el.dataset.id;
  if (algoById(id).user) return toast("Черновик ещё не опубликован: запустить на сессии можно после расчёта рейтинга.");
  state.form = { ...state.form, who: "algo", algo: id, primary: id };
  go("#/new");
};

function algoNew() {
  crumbs([["Мастерская", "#/workshop"], ["Новый алгоритм"]]);
  const d = state.draft || (state.draft = { name: "Мой алгоритм", code: ['algorithm "Мой алгоритм"', "param size = 20%", "", "let r = rsi(close, 14)", "",
    "when r < 30 and position = 0 -> buy size equity", '  because "перепроданность, RSI = {r}"', "when r > 60 -> sell all", '  because "RSI вернулся к середине, RSI = {r}"'].join("\n") });
  const lines = d.code.split("\n"), lint = lintCode(lines), noBecause = lines.some((l, i) => /^\s*when/.test(l) && !/^\s*because/.test(lines[i + 1] || ""));
  document.getElementById("content").innerHTML = `
    ${head("Новый алгоритм", `${d.forked_from ? `<span>${icon("fork", 14)} форк «${esc(algoById(d.forked_from[0]).name)}» v${d.forked_from[1]}, исходный автор ${esc(d.forked_from[2])}</span>` : "<span>черновик, виден только вам</span>"}`,
      `<button class="btn" data-go="#/workshop">Отмена</button><button class="btn primary" data-act="publish">Опубликовать версию 1</button>`)}
    <div class="grid g-12">
      <div class="panel s-8" style="overflow:hidden"><div class="panel-h"><h3>DSL</h3><div class="right small muted">каждое правило — с причиной because</div></div>
        <textarea id="dsl" data-input="dsl" spellcheck="false" style="width:100%;min-height:360px;border:0;border-top:1px solid var(--div);padding:12px 16px;font:13px/22px var(--mono);resize:vertical;outline:0;background:#FBFBFC">${esc(d.code)}</textarea></div>
      <div class="s-4 col" style="gap:16px">
        <div class="panel"><div class="panel-h"><h3>Линтер</h3><div class="right" id="lintcnt">${lint.length ? `<span class="badge warn">${lint.length}</span>` : '<span class="badge ok">чисто</span>'}</div></div>
          <div class="panel-b col" id="lintlist">${lintList(lint, noBecause)}</div></div>
        <div class="panel"><div class="panel-h"><h3>Что будет при публикации</h3></div><div class="panel-b small col" style="gap:8px">
          <div>Версия 1 станет неизменяемой и получит sha.</div><div>Лицензия MIT, автор — ${DATA.user}${d.forked_from ? `, исходный автор — ${esc(d.forked_from[2])}` : ""}.</div>
          <div>Платформа посчитает рейтинг на 200 случайных закрытых окнах.</div></div></div>
      </div>
    </div>`;
}
function lintList(lint, noBecause) {
  return (lint.length ? lint.map(x => `<div class="row" style="align-items:flex-start"><span class="badge warn">стр. ${x.line}</span><div style="flex:1" class="small">Константа <span class="mono">${x.const}</span> — вынесите в параметр</div><button class="btn s" data-act="draftFix" data-line="${x.line}" data-c="${x.const}">Вынести</button></div>`).join("")
    : '<div class="small muted">Магических констант нет.</div>') + (noBecause ? '<div class="small neg">У правила when нет строки because: причина не попадёт в разбор расхождений.</div>' : "");
}
ACT.dsl = el => {
  state.draft.code = el.value;
  const lines = el.value.split("\n"), lint = lintCode(lines), noBecause = lines.some((l, i) => /^\s*when/.test(l) && !/^\s*because/.test(lines[i + 1] || ""));
  document.getElementById("lintlist").innerHTML = lintList(lint, noBecause);
  document.getElementById("lintcnt").innerHTML = lint.length ? `<span class="badge warn">${lint.length}</span>` : '<span class="badge ok">чисто</span>';
};
ACT.draftFix = el => {
  const lines = state.draft.code.split("\n"), ln = +el.dataset.line - 1, c = el.dataset.c;
  const nm = "p_" + c.replace(".", "_");
  lines[ln] = lines[ln].replace(new RegExp(`(?<![\\w.])${c.replace(".", "\\.")}(?![\\w.])`), nm);
  const lastParam = lines.reduce((k, l, i) => /^param /.test(l) ? i : k, 0);
  lines.splice(lastParam + 1, 0, `param ${nm} = ${c}`);
  state.draft.code = lines.join("\n");
  algoNew();
};
ACT.publish = () => {
  const d = state.draft, lines = d.code.split("\n");
  const name = (lines[0].match(/algorithm "(.+)"/) || [])[1] || d.name;
  const id = "u" + Date.now().toString(36);
  const a = { id, user: true, name, author: DATA.user, version: 1, updated: nowStr().slice(0, 10), desc: d.forked_from ? `Форк «${algoById(d.forked_from[0]).name}»` : "Черновик из мастерской",
              dsl: lines, lint: lintCode(lines).map(x => ({ ...x, name: "p_" + x.const.replace(".", "_") })), forks: 0, runs: 0, forked_from: d.forked_from, rating: null };
  saveUserAlgos([...userAlgos(), a]);
  state.draft = null;
  toast(`«${esc(name)}» v1 опубликован под MIT. Рейтинг считается на 200 закрытых окнах.`);
  go("#/algo/" + id);
};

// =========================================================================================
// Данные
// =========================================================================================
function dataPage() {
  crumbs([["Данные"]]);
  const st = { "актуальный": "ok", "заменён ds-0007": "", "устаревшая схема": "warn", "после MVP": "info" };
  document.getElementById("content").innerHTML = `
    ${head("Данные", "Неизменяемые снапшоты котировок и новостной конвейер. Сессии и прогоны ссылаются на версию снапшота.")}
    <div class="panel"><div class="panel-h"><h3>Снапшоты котировок</h3></div><div class="scroll"><table class="t"><thead><tr><th>Снапшот</th><th>Источник</th><th>Бумаги</th><th>Интервал</th><th>Период</th><th>sha</th><th>Статус</th><th class="r">Используется</th></tr></thead><tbody>
      ${V1.datasets.map(d => `<tr><td class="w"><b>${d.id}</b></td><td class="w">${d.source}</td><td class="small">${d.tickers}</td><td>${d.interval}</td><td class="w small">${d.period}</td><td class="mono">${d.sha}</td><td><span class="badge ${st[d.status] ?? ""}">${d.status}</span></td><td class="r">${d.used_in}</td></tr>`).join("")}</tbody></table></div></div>
    <div class="grid g-12">
      <div class="panel s-7"><div class="panel-h"><h3>Новостной конвейер</h3><div class="right"><span class="badge">только для людей</span></div></div>
        <div class="panel-b small" style="margin-bottom:4px">Реальные новости с точным временем публикации. В сессии новость появляется только после этого момента. Обезличивание убирает компании, людей, даты, суммы и приметы эпохи, сектор экономики сохраняется.</div>
        <table class="t"><thead><tr><th>Видит человек</th><th>Оригинал</th></tr></thead><tbody>${V.news.slice(1, 5).map(n => `<tr><td class="small">${sectorBadge(n.sector)} ${esc(n.text)}</td><td class="small muted">${esc(n.original)}</td></tr>`).join("")}</tbody></table></div>
      <div class="panel s-5"><div class="panel-h"><h3>Момент доступности полей</h3></div><table class="t dense"><tbody>
        ${V1.fields.map(([f, w]) => `<tr><td class="mono">${f}</td><td class="small ${/запрещено/.test(w) ? "neg" : ""}">${w}</td></tr>`).join("")}</tbody></table>
        <div class="panel-b" style="padding-top:12px"><div class="callout">${icon("info", 18)}<div class="small">Торги не проводились ${V1.calendar_gap[0]} — ${V1.calendar_gap[1]}. В слепой сессии разрыв показывается как «торги приостановлены» без длительности.</div></div></div></div>
    </div>${disclaimer()}`;
}

// --- старт ---------------------------------------------------------------------------------
shell();
render();
