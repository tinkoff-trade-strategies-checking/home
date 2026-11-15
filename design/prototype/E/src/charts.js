// Графики на SVG: свечи с «будущим скрыто», линии капитала, спарклайны.

const SVGNS = 'xmlns="http://www.w3.org/2000/svg"';

function niceTicks(min, max, n = 4) {
  const span = max - min || 1, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(s => s >= step0);
  const out = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) out.push(v);
  return out;
}

function spark(values, w = 80, h = 24, color = "var(--accent)") {
  if (values.length < 2) return "";
  const mn = Math.min(...values), mx = Math.max(...values), k = (h - 4) / (mx - mn || 1);
  const pts = values.map((v, i) => `${(i / (values.length - 1) * w).toFixed(1)},${(h - 2 - (v - mn) * k).toFixed(1)}`).join(" ");
  return `<svg ${SVGNS} width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round"/></svg>`;
}

// Свечной график. Видны бары from..last, справа до from+slots-1 — скрытое будущее.
function candleChart(el, o) {
  const W = Math.max(320, el.clientWidth || 800), H = o.height || 360;
  const padL = 8, padR = 56, padT = 12, padB = 26, volH = o.volume === false ? 0 : 44;
  const pw = W - padL - padR, ph = H - padT - padB - volH - (volH ? 8 : 0);
  const c = o.candles, from = o.from, last = o.last, slots = o.slots;
  const vis = c.slice(from, last + 1);
  let mn = Math.min(...vis.map(b => b.l)), mx = Math.max(...vis.map(b => b.h));
  for (const l of o.levels || []) { mn = Math.min(mn, l.price); mx = Math.max(mx, l.price); }
  const pad = (mx - mn) * 0.08; mn -= pad; mx += pad;
  const sw = pw / slots, X = t => padL + (t - from + 0.5) * sw, Y = v => padT + (mx - v) / (mx - mn) * ph;
  const vmax = Math.max(...vis.map(b => b.v)), vy0 = padT + ph + 8 + volH;
  let s = `<svg ${SVGNS} width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`;
  s += `<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#F6F6F7"/><line x1="0" y1="0" x2="0" y2="6" stroke="#DADBE2" stroke-width="2"/></pattern></defs>`;
  for (const v of niceTicks(mn, mx, 5)) {
    s += `<line x1="${padL}" x2="${padL + pw}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ECEDF0"/>`;
    s += `<text x="${W - padR + 8}" y="${Y(v) + 4}" font-size="11" fill="#A4A5B1">${fmtN(v, v < 20 ? 1 : 0)}</text>`;
  }
  // будущее
  if (last < from + slots - 1) {
    const fx = padL + (last - from + 1) * sw;
    s += `<rect x="${fx}" y="${padT}" width="${padL + pw - fx}" height="${H - padT - padB}" fill="url(#hatch)"/>`;
    s += `<line x1="${fx}" x2="${fx}" y1="${padT}" y2="${H - padB}" stroke="#FFDD2D" stroke-width="2"/>`;
    if (padL + pw - fx > 110) s += `<text x="${fx + (padL + pw - fx) / 2}" y="${padT + ph / 2}" text-anchor="middle" font-size="12" fill="#6B6D80" font-weight="700">Будущее скрыто</text>`;
  }
  // уровни заявок
  for (const l of o.levels || []) {
    s += `<line x1="${padL}" x2="${padL + pw}" y1="${Y(l.price)}" y2="${Y(l.price)}" stroke="${l.color}" stroke-dasharray="4 3"/>`;
    s += `<rect x="${W - padR + 2}" y="${Y(l.price) - 9}" width="${padR - 4}" height="18" rx="4" fill="${l.color}"/>`;
    s += `<text x="${W - padR / 2}" y="${Y(l.price) + 4}" text-anchor="middle" font-size="11" fill="#fff" font-weight="700">${fmtN(l.price, 1)}</text>`;
    s += `<text x="${padL + 4}" y="${Y(l.price) - 4}" font-size="11" fill="${l.color}" font-weight="700">${l.label}</text>`;
  }
  // оверлеи
  for (const ov of o.overlays || []) {
    const pts = [];
    for (let t = from; t <= last; t++) if (ov.values[t] != null) pts.push(`${X(t).toFixed(1)},${Y(ov.values[t]).toFixed(1)}`);
    s += `<polyline points="${pts.join(" ")}" fill="none" stroke="${ov.color}" stroke-width="1.5" opacity=".9"/>`;
  }
  // свечи и объём
  const bw = Math.max(1, Math.min(10, sw * 0.62));
  for (let t = from; t <= last; t++) {
    const b = c[t], up = b.c >= b.o, col = up ? "#2FA57D" : "#E5483A", x = X(t);
    s += `<line x1="${x}" x2="${x}" y1="${Y(b.h)}" y2="${Y(b.l)}" stroke="${col}"/>`;
    const y1 = Y(Math.max(b.o, b.c)), hh = Math.max(1, Math.abs(Y(b.o) - Y(b.c)));
    s += `<rect x="${x - bw / 2}" y="${y1}" width="${bw}" height="${hh}" fill="${col}"/>`;
    if (volH) { const vh = b.v / vmax * volH; s += `<rect x="${x - bw / 2}" y="${vy0 - vh}" width="${bw}" height="${vh}" fill="${col}" opacity=".28"/>`; }
  }
  if (o.startT != null && o.startT > from && o.startT <= last) {
    const sx = padL + (o.startT - from) * sw;
    s += `<line x1="${sx}" x2="${sx}" y1="${padT}" y2="${H - padB}" stroke="#A4A5B1" stroke-dasharray="2 3"/>`;
    s += `<text x="${sx + 4}" y="${padT + 12}" font-size="11" fill="#A4A5B1">старт сессии</text>`;
  }
  // новости
  for (const n of o.news || []) {
    if (n.t < from || n.t > last) continue;
    s += `<circle cx="${X(n.t)}" cy="${H - padB + 2}" r="4" fill="#FFC700" stroke="#fff" stroke-width="1.5"/>`;
  }
  // сделки
  for (const m of o.markers || []) {
    if (m.t < from || m.t > last) continue;
    const b = c[m.t], x = X(m.t), buy = m.side === "buy", col = m.color || (buy ? "#008764" : "#EB1700");
    const y = buy ? Y(b.l) + 8 : Y(b.h) - 8, d = buy ? 1 : -1;
    s += `<path d="M${x} ${y} l-6 ${d * 9} h12 z" fill="${col}" stroke="#fff" stroke-width="1"/>`;
  }
  // подписи оси X
  const every = Math.max(1, Math.ceil(slots / (pw / 70)));
  for (let t = from; t < from + slots; t += every)
    s += `<text x="${X(t)}" y="${H - 6}" text-anchor="middle" font-size="11" fill="#A4A5B1">${o.label(t)}</text>`;
  s += `<line class="xh" x1="0" x2="0" y1="${padT}" y2="${H - padB}" stroke="#1B1F3B" stroke-opacity=".25" visibility="hidden"/>`;
  s += `</svg><div class="tip"></div>`;
  el.innerHTML = s;
  const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), xh = el.querySelector(".xh");
  svg.onmousemove = ev => {
    const r = svg.getBoundingClientRect(), mx_ = (ev.clientX - r.left) * (W / r.width);
    const t = from + Math.floor((mx_ - padL) / sw);
    if (t < from || t > last) { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); return; }
    const b = c[t];
    xh.setAttribute("x1", X(t)); xh.setAttribute("x2", X(t)); xh.setAttribute("visibility", "visible");
    const mk = (o.markers || []).filter(m => m.t === t).map(m => `<br>${m.label}`).join("");
    const nw = (o.news || []).filter(n => n.t === t).length ? "<br>Новость" : "";
    tip.innerHTML = `<b>${o.label(t)}</b><br>O ${fmtP(b.o)} H ${fmtP(b.h)} L ${fmtP(b.l)} C ${fmtP(b.c)}${mk}${nw}`;
    tip.style.display = "block";
    const left = X(t) / W * r.width;
    tip.style.left = Math.min(r.width - tip.offsetWidth - 4, left + 12) + "px";
    tip.style.top = "8px";
  };
  svg.onmouseleave = () => { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); };
}

// Линии капитала: series = [{name, color, pts:[{t,v}], dash, width}]
function lineChart(el, o) {
  const W = Math.max(320, el.clientWidth || 800), H = o.height || 260;
  const padL = 8, padR = 72, padT = 12, padB = 26, pw = W - padL - padR, ph = H - padT - padB;
  const all = o.series.flatMap(s => s.pts);
  const t0 = Math.min(...all.map(p => p.t)), t1 = Math.max(...all.map(p => p.t));
  let mn = Math.min(...all.map(p => p.v)), mx = Math.max(...all.map(p => p.v));
  if (o.base != null) { mn = Math.min(mn, o.base); mx = Math.max(mx, o.base); }
  const pad = (mx - mn) * 0.08 || 1; mn -= pad; mx += pad;
  const X = t => padL + (t - t0) / (t1 - t0 || 1) * pw, Y = v => padT + (mx - v) / (mx - mn) * ph;
  let s = `<svg ${SVGNS} width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">`;
  for (const v of niceTicks(mn, mx, 4)) {
    s += `<line x1="${padL}" x2="${padL + pw}" y1="${Y(v)}" y2="${Y(v)}" stroke="#ECEDF0"/>`;
    s += `<text x="${W - padR + 8}" y="${Y(v) + 4}" font-size="11" fill="#A4A5B1">${o.yfmt ? o.yfmt(v) : fmtN(v)}</text>`;
  }
  if (o.base != null) s += `<line x1="${padL}" x2="${padL + pw}" y1="${Y(o.base)}" y2="${Y(o.base)}" stroke="#A4A5B1" stroke-dasharray="3 3"/>`;
  for (const m of o.marks || []) {
    s += `<line x1="${X(m.t)}" x2="${X(m.t)}" y1="${padT}" y2="${padT + ph}" stroke="${m.color || '#FFC700'}" stroke-width="1.5" opacity=".7"/>`;
  }
  for (const se of o.series) {
    const pts = se.pts.map(p => `${X(p.t).toFixed(1)},${Y(p.v).toFixed(1)}`).join(" ");
    s += `<polyline points="${pts}" fill="none" stroke="${se.color}" stroke-width="${se.width || 2}" ${se.dash ? `stroke-dasharray="${se.dash}"` : ""} stroke-linejoin="round"/>`;
  }
  const every = Math.max(1, Math.ceil((t1 - t0) / (pw / 80)));
  for (let t = t0; t <= t1; t += every)
    s += `<text x="${X(t)}" y="${H - 6}" text-anchor="${t === t0 ? "start" : "middle"}" font-size="11" fill="#A4A5B1">${o.label(t)}</text>`;
  s += `<line class="xh" x1="0" x2="0" y1="${padT}" y2="${padT + ph}" stroke="#1B1F3B" stroke-opacity=".25" visibility="hidden"/></svg><div class="tip"></div>`;
  el.innerHTML = s;
  const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), xh = el.querySelector(".xh");
  svg.onmousemove = ev => {
    const r = svg.getBoundingClientRect(), mx_ = (ev.clientX - r.left) * (W / r.width);
    const t = Math.round(t0 + (mx_ - padL) / pw * (t1 - t0));
    if (t < t0 || t > t1) return;
    xh.setAttribute("x1", X(t)); xh.setAttribute("x2", X(t)); xh.setAttribute("visibility", "visible");
    tip.innerHTML = `<b>${o.label(t)}</b>` + o.series.map(se => {
      const p = se.pts.find(q => q.t === t);
      return p ? `<br><span style="color:${se.color}">●</span> ${se.name}: ${o.yfmt ? o.yfmt(p.v) : fmtN(p.v)}` : "";
    }).join("");
    tip.style.display = "block";
    tip.style.left = Math.min(r.width - tip.offsetWidth - 4, X(t) / W * r.width + 12) + "px";
    tip.style.top = "8px";
  };
  svg.onmouseleave = () => { tip.style.display = "none"; xh.setAttribute("visibility", "hidden"); };
}
