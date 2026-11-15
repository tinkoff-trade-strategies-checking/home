"""Концепция B. Терминал — графики в центре.

Нейтральный графит, тайлинг панелей, «линия знания» на свечах.
Запуск: python gen.py  ->  out/B1.svg … out/B7.svg
"""
import os
import sys
from bisect import bisect_left
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from svg import *  # noqa: E402,F401
import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --- палитра -------------------------------------------------------------------------
BASE = "#15171C"
PANEL = "#1C1F26"
SURF = "#242833"
SURF2 = "#2A2F3A"
GRID = "#2C313C"
LINE = "#343A47"
T1 = "#E8EAED"
T2 = "#9AA0AA"
T3 = "#666C78"
UP = "#44C596"
DN = "#FF4D4D"
SEL = "#70B6F6"
Y = "#FFDD2D"
WARN = "#FFC700"
INK = "#15171C"

# --- сетка оболочки -----------------------------------------------------------------
W = 1440
TOP = 48
TAPE = 32
Y0 = TOP + TAPE          # 80 — начало рабочей области
LW = 240                 # watchlist
RW = 300                 # лента справа
G = 4                    # зазор между тайлами
CX = LW + G              # 244
CR = W - RW - G          # 1136
CW = CR - CX             # 892
RX = W - RW              # 1140
SCRUB = 56

NAV = ["Датасеты", "Стратегия", "Прогон", "Отчёт", "Сравнение", "Walk-forward", "История"]

TICKERS = [("SBER", "Сбербанк", 7), ("GAZP", "Газпром", 23), ("LKOH", "Лукойл", 31),
           ("GMKN", "Норникель", 11), ("YDEX", "Яндекс", 47), ("MOEX", "Мосбиржа", 59),
           ("IMOEX", "Индекс Мосбиржи", 61)]

CANDLES = D.candles()
CAND_DAYS = [d for d in D.DAYS if date(2025, 9, 1) <= d <= date(2025, 12, 31)]
KNOW_I = 76  # позиция «линии знания» на свечах (индекс бара)


def cday(i):
    return CAND_DAYS[round(i * (len(CAND_DAYS) - 1) / (len(CANDLES) - 1))]


def dstr(d, year=True):
    return d.strftime("%d.%m.%Y") if year else d.strftime("%d.%m")


def num(v, digits=1):
    return f"{v:.{digits}f}".replace(".", ",")


# --- базовые компоненты ---------------------------------------------------------------
def tc(s, x, yc, txt, size=14, **kw):
    """Текст, вертикально центрированный по yc."""
    s.text(x, yc + size * 0.36, txt, size=size, **kw)


def button(s, x, y, label, kind="primary", h=32, icon=None, w=None, size=None):
    size = size or (14 if h >= 40 else 13)
    tw = measure(label, size, 700)
    pad = 16 if h >= 40 else 12
    iw = 16 + 8 if icon else 0
    w = w or (tw + iw + pad * 2)
    fill, col, stroke = {"primary": (Y, INK, None), "secondary": (SURF2, T1, None),
                         "outline": ("none", T1, LINE), "ghost": ("none", T2, None)}[kind]
    s.rect(x, y, w, h, fill, rx=8 if h < 40 else 10, stroke=stroke)
    cx = x + (w - tw - iw) / 2
    if icon:
        s.icon(icon, cx, y + h / 2 - 8, col)
        cx += iw
    tc(s, cx, y + h / 2, label, size=size, fill=col, weight=700)
    return w


def badge(s, x, yc, label, color, size=12, solid=False):
    w = measure(label, size, 700) + 12
    if solid:
        s.rect(x, yc - 10, w, 20, color, rx=4)
        tc(s, x + 6, yc, label, size=size, fill=INK, weight=700)
    else:
        s.rect(x, yc - 10, w, 20, color, rx=4, opacity=0.16)
        tc(s, x + 6, yc, label, size=size, fill=color, weight=700)
    return w


def chip(s, x, yc, label, active=False, size=12, h=24):
    w = measure(label, size, 400) + 16
    s.rect(x, yc - h / 2, w, h, SURF2 if not active else Y, rx=6)
    tc(s, x + 8, yc, label, size=size, fill=INK if active else T1)
    return w


def field(s, x, y, w, label, value, h=44, mono=False, suffix=None, select=False, note_color=None):
    """Поле ввода Taiga: подпись внутри сверху, значение снизу."""
    s.rect(x, y, w, h, SURF, rx=10)
    s.text(x + 12, y + 17, label, size=12, fill=T3)
    vw = w - 24 - (20 if select else 0) - (measure(suffix, 13) + 8 if suffix else 0)
    s.text(x + 12, y + 35, truncate(value, vw, 14, mono=mono), size=14, fill=T1, mono=mono)
    if suffix:
        s.text(x + w - 12 - (20 if select else 0), y + 35, suffix, size=13, fill=T3, anchor="end")
    if select:
        s.icon("chevron-down", x + w - 28, y + h / 2 - 8, T2)


def small_select(s, x, y, w, value, h=32, mono=False, color=T1, active=False):
    s.rect(x, y, w, h, SURF, rx=8, stroke=SEL if active else None)
    tc(s, x + 10, y + h / 2, truncate(value, w - 34, 13, mono=mono), size=13, fill=color, mono=mono)
    s.icon("chevron-down", x + w - 22, y + h / 2 - 7, T3, s=14)


def toggle(s, x, yc, on=True):
    s.rect(x, yc - 10, 36, 20, Y if on else SURF2, rx=10)
    s.circle(x + (26 if on else 10), yc, 7, fill=INK if on else T2)


def checkbox(s, x, yc, on=True):
    s.rect(x, yc - 8, 16, 16, Y if on else "none", rx=4, stroke=None if on else T3)
    if on:
        s.icon("check", x + 1, yc - 7, INK, s=14, sw=2)


def radio(s, x, yc, on=True):
    s.circle(x + 8, yc, 7.5, stroke=Y if on else T3, sw=1.5)
    if on:
        s.circle(x + 8, yc, 4, fill=Y)


def seg(s, x, y, w, items, active, h=32, size=13):
    """Сегментированный переключатель Taiga."""
    s.rect(x, y, w, h, SURF, rx=8)
    sw_ = (w - 4) / len(items)
    for i, it in enumerate(items):
        sx = x + 2 + i * sw_
        if i == active:
            s.rect(sx, y + 2, sw_, h - 4, SURF2 if active is not None else SURF, rx=6, stroke=LINE)
        tw = measure(it, size, 700 if i == active else 400)
        tc(s, sx + (sw_ - tw) / 2, y + h / 2, it, size=size, fill=T1 if i == active else T2,
           weight=700 if i == active else 400)


def panel(s, x, y, w, h, title, sub=None, hdr=36):
    """Тайл терминала: заголовок 36 px + тело. Возвращает y тела."""
    s.rect(x, y, w, h, PANEL)
    s.text(x + 12, y + hdr / 2 + 5, title, size=13, fill=T1, weight=700)
    if sub:
        tx = x + 12 + measure(title, 13, 700) + 10
        s.text(tx, y + hdr / 2 + 5, sub, size=12, fill=T3)
    s.line(x, y + hdr, x + w, y + hdr, GRID)
    return y + hdr


def legend(s, xr, yc, items, size=12):
    """Легенда справа налево. items: (label, color, kind) kind=line|dash|box|dot."""
    x = xr
    for label, color, kind in reversed(items):
        tw = measure(label, size)
        x -= tw
        s.text(x, yc + size * 0.36, label, size=size, fill=T2)
        x -= 20
        if kind == "line":
            s.line(x, yc, x + 14, yc, color, sw=2)
        elif kind == "dash":
            s.line(x, yc, x + 14, yc, color, sw=2, dash="3 2")
        elif kind == "box":
            s.rect(x + 2, yc - 5, 10, 10, color, rx=2)
        else:
            s.circle(x + 7, yc, 4, fill=color)
        x -= 16
    return x


def hatch(s, x, y, w, h, color=T3, step=7, opacity=0.5, sw=1):
    s.clip(x, y, w, h)
    k = -h
    while k < w:
        s.line(x + k, y + h, x + k + h, y, color, sw=sw, opacity=opacity)
        k += step
    s.end()


def tabs(s, x, y, items, active, h=36, size=13):
    cx = x
    for i, t in enumerate(items):
        tw = measure(t, size, 700 if i == active else 400)
        tc(s, cx, y + h / 2, t, size=size, fill=T1 if i == active else T2, weight=700 if i == active else 400)
        if i == active:
            s.rect(cx, y + h - 2, tw, 2, Y)
        cx += tw + 20
    return cx


def kv(s, x, y, w, k, v, size=13, vcol=T1, kcol=T2, mono=False, bold=False):
    s.text(x, y, k, size=size, fill=kcol)
    s.text(x + w, y, truncate(v, w - measure(k, size) - 12, size, 700 if bold else 400, mono), size=size,
           fill=vcol, anchor="end", mono=mono, weight=700 if bold else 400)


def disclaimer(s, x, y, w, size=11):
    return s.para(x, y, D.DISCLAIMER, w, size=size, lh=15, fill=T3)


# --- время ----------------------------------------------------------------------------
T_START, T_END = D.DAYS[0], D.DAYS[-1]


def tx_of(d, x, w, a=T_START, b=T_END):
    return x + w * (d - a).days / (b - a).days


def tseries(s, values, x, y, w, h, vmin, vmax, stroke, sw=1.6, dash=None, step=2, area=None, opacity=None,
            days=None, a=T_START, b=T_END):
    days = days or D.DAYS
    span = vmax - vmin
    pts = []
    for i in list(range(0, len(values), step)) + [len(values) - 1]:
        pts.append((tx_of(days[i], x, w, a, b), y + h - h * (values[i] - vmin) / span))
    d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    if area:
        s.path(d + f" L{pts[-1][0]:.1f} {y + h:.1f} L{pts[0][0]:.1f} {y + h:.1f} Z", fill=s.gradient(area, 0.22, 0))
    s.path(d, stroke=stroke, sw=sw, dash=dash, opacity=opacity)
    return pts


def year_axis(s, x, y, w, a=T_START, b=T_END, size=11, grid_top=None, color=T3):
    for yr in range(a.year, b.year + 2):
        d = date(yr, 1, 1)
        if d < a or d > b:
            continue
        px = tx_of(d, x, w, a, b)
        if grid_top is not None:
            s.line(px, grid_top, px, y - 6, GRID)
        s.text(px + 4, y + 8, str(yr), size=size, fill=color)


def stress_bands(s, x, y, w, h, labels=True, a=T_START, b=T_END):
    """Март 2020, 24.02.2022 и разрыв торгов 28.02–23.03.2022."""
    x1, x2 = tx_of(date(2020, 2, 24), x, w, a, b), tx_of(date(2020, 3, 23), x, w, a, b)
    s.rect(x1, y, x2 - x1, h, DN, opacity=0.08)
    g1, g2 = tx_of(date(2022, 2, 28), x, w, a, b), tx_of(date(2022, 3, 23), x, w, a, b)
    s.rect(g1, y, g2 - g1, h, BASE, opacity=0.7)
    hatch(s, g1, y, g2 - g1, h, T3, step=5, opacity=0.6)
    xs = tx_of(date(2022, 2, 24), x, w, a, b)
    s.line(xs, y, xs, y + h, DN, sw=1, dash="3 3")
    if labels:
        s.text(x1 + 4, y + 14, "Март 2020", size=11, fill=DN)
        s.text(xs - 4, y + 14, "24.02.2022", size=11, fill=DN, anchor="end")
        s.text(g2 + 4, y + 14, "Торгов нет 18 дней", size=11, fill=T2)
    return xs


# --- оболочка -------------------------------------------------------------------------
def topbar(s, active):
    s.rect(0, 0, W, TOP, PANEL)
    s.line(0, TOP, W, TOP, GRID)
    # знак: свеча + линия знания + штриховка
    s.rect(16, 12, 24, 24, SURF2, rx=6)
    hatch(s, 30, 14, 8, 20, T2, step=4, opacity=0.7)
    s.rect(27, 12, 2, 24, Y)
    s.rect(20, 19, 4, 10, UP)
    s.line(22, 16, 22, 32, UP, sw=1)
    s.text(52, 29, D.PRODUCT, size=14, fill=T1, weight=700)
    x = 52 + measure(D.PRODUCT, 14, 700) + 32
    for i, t in enumerate(NAV):
        on = i == active
        tw = measure(t, 13, 700 if on else 400)
        tc(s, x, TOP / 2, t, size=13, fill=T1 if on else T2, weight=700 if on else 400)
        if on:
            s.rect(x, TOP - 2, tw, 2, Y)
        x += tw + 24
    # справа
    s.circle(W - 32, TOP / 2, 14, fill=SURF2)
    tc(s, W - 32 - measure("ДМ", 11, 700) / 2, TOP / 2, "ДМ", size=11, fill=T1, weight=700)
    bw = measure("Запустить прогон", 13, 700) + 24 + 24
    button(s, W - 56 - bw, 8, "Запустить прогон", icon="play")
    return x


def tape(s, items):
    """Тикерная лента: пары подпись/значение, разделённые тонкими вертикалями."""
    s.rect(0, TOP, W, TAPE, BASE)
    s.line(0, Y0, W, Y0, GRID)
    x = 16
    yc = TOP + TAPE / 2
    for i, it in enumerate(items):
        k, v = it[0], it[1]
        col = it[2] if len(it) > 2 else T1
        if k:
            s.text(x, yc + 4.3, k, size=12, fill=T3, mono=True)
            x += measure(k, 12, mono=True) + 8
        s.text(x, yc + 4.3, v, size=12, fill=col, mono=True, weight=700)
        x += measure(v, 12, 700, mono=True) + 14
        if i < len(items) - 1:
            s.line(x, TOP + 9, x, Y0 - 9, LINE)
            x += 14


def run_tape(s):
    R = D.RESULT_HONEST
    tape(s, [("", D.RUN_ID, T2), ("", "SMA 20/50, честный", T1), ("Итог", R["total"], UP), ("CAGR", R["cagr"], UP),
             ("Просадка", R["max_dd"], DN), ("Sharpe", R["sharpe"]), ("Sortino", R["sortino"]),
             ("Сделки", R["trades"]), ("Издержки", D.COSTS_TOTAL, DN), ("IMOEX", R["benchmark"], T2),
             ("Наивный", D.RESULT_NAIVE["total"], T2)])


def watchlist(s, y0, y1, selected="SBER", title="Вселенная", sub="01.09 — 31.12.2025", extra=None):
    s.rect(0, Y0, LW, y1 - Y0, PANEL)
    s.text(16, y0 + 23, title, size=13, fill=T1, weight=700)
    s.text(LW - 16, y0 + 23, sub, size=12, fill=T3, anchor="end")
    s.line(0, y0 + 36, LW, y0 + 36, GRID)
    y = y0 + 36
    rh = 48
    for tk, name, seed in TICKERS:
        c = D.candles(seed=seed) if seed != 7 else CANDLES
        closes = [b["c"] for b in c]
        ch = closes[-1] / c[0]["o"] - 1
        on = tk == selected
        if on:
            s.rect(0, y, LW, rh, SURF)
            s.rect(0, y, 2, rh, SEL)
        s.text(16, y + 21, tk, size=13, fill=T1, weight=700)
        s.text(16, y + 38, truncate(name, 84, 12), size=12, fill=T3)
        col = UP if ch >= 0 else DN
        s.series(closes, 100, y + 12, 56, 24, min(closes), max(closes), col, sw=1.2, step=2)
        s.text(LW - 16, y + 21, fmt_pct(ch * 100), size=13, fill=col, weight=700, anchor="end")
        s.text(LW - 16, y + 38, "за период", size=11, fill=T3, anchor="end")
        y += rh
    s.line(LW, Y0, LW, y1, GRID)
    return y


def right_col(s, y1):
    s.rect(RX, Y0, RW, y1 - Y0, PANEL)
    s.line(RX, Y0, RX, y1, GRID)


def scrubber(s, y, mode="run", pos=None, window=None, train=None, rlabel=None, rvalue=None):
    """Таймлайн-скраббер всего периода с отметками стресс-событий."""
    s.rect(0, y, W, SCRUB, PANEL)
    s.line(0, y, W, y, GRID)
    # слева: управление воспроизведением
    s.rect(16, y + 12, 32, 32, SURF2, rx=8)
    s.icon("play", 24, y + 20, T1)
    s.text(60, y + 25, "Период прогона", size=12, fill=T3)
    s.text(60, y + 43, D.RUN_CONFIG["period"], size=12, fill=T1, weight=700)
    # дорожка
    tx, tw_ = CX + 8, CW - 16
    ty, th = y + 8, 30
    eq = D.EQUITY_HONEST
    s.rect(tx, ty, tw_, th, BASE, rx=4)
    tseries(s, eq, tx, ty + 4, tw_, th - 8, min(eq), max(eq), T3, sw=1, step=4, area=T3)
    stress_bands(s, tx, ty, tw_, th, labels=False)
    if train:
        a, b = train
        xa, xb = tx_of(a, tx, tw_), tx_of(b, tx, tw_)
        s.rect(xa, ty, xb - xa, th, T2, opacity=0.14)
    if window:
        a, b = window
        xa, xb = tx_of(a, tx, tw_), tx_of(b, tx, tw_)
        s.rect(xa, ty, xb - xa, th, SEL, opacity=0.22, stroke=SEL, sw=1)
    year_axis(s, tx, y + 42, tw_, size=11)
    if pos:
        px = tx_of(pos, tx, tw_)
        s.rect(px, ty, tx + tw_ - px, th, BASE, opacity=0.55)
        hatch(s, px, ty, tx + tw_ - px, th, T3, step=5, opacity=0.5)
        s.rect(px - 1, ty - 4, 2, th + 8, Y)
        s.rect(px - 5, ty - 6, 10, 6, Y, rx=2)
    # справа: позиция
    s.text(RX + 16, y + 25, rlabel or ("Линия знания" if pos else "Окно"), size=12, fill=T3)
    if rvalue:
        s.text(RX + 16, y + 43, rvalue, size=12, fill=T1, weight=700)
    if pos:
        s.text(RX + 16, y + 43, dstr(pos), size=12, fill=Y, weight=700)
        s.text(W - 16, y + 25, "Скорость", size=12, fill=T3, anchor="end")
        s.text(W - 16, y + 43, "1 бар = 0,2 с", size=12, fill=T1, anchor="end")


# --- графики --------------------------------------------------------------------------
def price_axis(s, x, y, h, lo, hi, n=5, fmt=lambda v: num(v, 0), x2=None, w=None):
    for k in range(n):
        v = lo + (hi - lo) * k / (n - 1)
        py = y + h - h * k / (n - 1)
        if w:
            s.line(x2 - w, py, x2, py, GRID)
        s.text(x, py + 4, fmt(v), size=11, fill=T3)


def candle_chart(s, x, y, w, h, know_i=KNOW_I, markers=True, sma=True, vol_h=48, label_future=True):
    """Свечи SBER + объём + маркеры сделок + линия знания. Возвращает геометрию."""
    axis_w = 52
    pw = w - axis_w
    ph = h - vol_h - 24
    lo = min(c["l"] for c in CANDLES)
    hi = max(c["h"] for c in CANDLES)
    lo_p, hi_p = lo - (hi - lo) * 0.08, hi + (hi - lo) * 0.10
    # сетка
    for k in range(5):
        v = lo_p + (hi_p - lo_p) * (k + 0.5) / 5
        py = y + ph - ph * (v - lo_p) / (hi_p - lo_p)
        s.line(x, py, x + pw, py, GRID)
        s.text(x + pw + 8, py + 4, num(v, 0), size=11, fill=T3)
    pad_top = ph * (hi_p - hi) / (hi_p - lo_p)
    pad_bot = ph * (lo - lo_p) / (hi_p - lo_p)
    geo = s.candles(CANDLES, x, y + pad_top, pw, ph - pad_top - pad_bot, UP, DN, gap=0.35)
    X, Yf, bw = geo["X"], geo["Y"], geo["bw"]
    if sma:
        closes = [c["c"] for c in CANDLES]
        for per, col, dash in ((20, T2, None), (50, SEL, None)):
            pts = []
            for i in range(per - 1, len(closes)):
                v = sum(closes[i - per + 1:i + 1]) / per
                pts.append((X(i), Yf(v)))
            s.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts), stroke=col, sw=1.4, opacity=0.9, dash=dash)
    # объём
    vy = y + ph + 4
    vmax = max(c["v"] for c in CANDLES)
    for i, c in enumerate(CANDLES):
        hh = (vol_h - 8) * c["v"] / vmax
        s.rect(X(i) - bw * 0.33, vy + vol_h - 4 - hh, bw * 0.66, hh, UP if c["c"] >= c["o"] else DN, opacity=0.35)
    s.line(x, vy, x + pw, vy, GRID)
    s.text(x + pw + 8, vy + 14, "Объём", size=11, fill=T3)
    # даты
    for i in (0, 21, 43, 64, 86):
        s.text(X(i), y + h - 6, dstr(cday(i), False), size=11, fill=T3, anchor="middle")
    # маркеры сделок
    if markers:
        for idx, kind, lbl in D.TRADE_MARKERS:
            c = CANDLES[idx]
            mx = X(idx)
            if kind in ("buy", "partial"):
                col = UP if kind == "buy" else WARN
                my = Yf(c["l"]) + 8
                s.path(f"M{mx:.1f} {my:.1f} L{mx - 6:.1f} {my + 9:.1f} L{mx + 6:.1f} {my + 9:.1f} Z", fill=col)
            elif kind == "sell":
                my = Yf(c["h"]) - 8
                s.path(f"M{mx:.1f} {my:.1f} L{mx - 6:.1f} {my - 9:.1f} L{mx + 6:.1f} {my - 9:.1f} Z", fill=DN)
            else:
                my = Yf(c["l"]) + 14
                s.circle(mx, my, 6, stroke=T2, sw=1.5)
                s.line(mx - 3.5, my - 3.5, mx + 3.5, my + 3.5, T2, sw=1.5)
    # линия знания
    if know_i is not None:
        kx = X(know_i) + bw / 2
        fw = x + pw - kx
        s.rect(kx, y, fw, ph + vol_h + 4, BASE, opacity=0.62)
        hatch(s, kx, y, fw, ph + vol_h + 4, T2, step=8, opacity=0.35)
        s.rect(kx - 1, y, 2, ph + vol_h + 4, Y)
        # флажок с датой
        lbl = "Знание до " + dstr(cday(know_i))
        lw_ = measure(lbl, 12, 700) + 16
        s.rect(kx - lw_, y + 8, lw_, 22, Y, rx=4)
        tc(s, kx - lw_ + 8, y + 19, lbl, size=12, fill=INK, weight=700)
        if label_future:
            cx_ = kx + fw / 2
            lines = wrap("Будущее скрыто от стратегии", fw - 28, 12, 700)
            bh = 44 + len(lines) * 16
            by_ = y + 44
            s.rect(kx + 8, by_, fw - 16, bh, BASE, rx=8, stroke=LINE)
            s.icon("lock", cx_ - 8, by_ + 12, T1)
            for j, ln in enumerate(lines):
                s.text(cx_, by_ + 48 + j * 16, ln, size=12, fill=T1, weight=700, anchor="middle")
    return dict(X=X, Y=Yf, bw=bw, pw=pw, ph=ph)


def equity_chart(s, x, y, w, h, series, vmin=0.5, vmax=1.9, labels=True, dd=None, dd_h=0, ticks=(0.6, 1.0, 1.4, 1.8)):
    axis_w = 48
    pw = w - axis_w
    eh = h - dd_h - 20 - (8 if dd_h else 0)
    for v in ticks:
        py = y + eh - eh * (v - vmin) / (vmax - vmin)
        s.line(x, py, x + pw, py, GRID if v != 1.0 else LINE, dash=None if v != 1.0 else "4 3")
        s.text(x + pw + 8, py + 4, num(v, 1) + " млн", size=11, fill=T3)
    stress_bands(s, x, y, pw, eh, labels=labels)
    for vals, col, sw, dash in series:
        tseries(s, vals, x, y, pw, eh, vmin, vmax, col, sw=sw, dash=dash)
    if dd:
        dy = y + eh + 8
        dmin = -0.45
        s.line(x, dy, x + pw, dy, LINE)
        for v in (-0.15, -0.30, -0.45):
            py = dy + dd_h * (v / dmin)
            s.line(x, py, x + pw, py, GRID)
            s.text(x + pw + 8, py + 4, num(v * 100, 0) + " %", size=11, fill=T3)
        s.text(x + pw + 8, dy + 12, "0 %", size=11, fill=T3)
        span = dmin
        pts = [(tx_of(D.DAYS[i], x, pw), dy + dd_h * (dd[i] / span)) for i in range(0, len(dd), 2)]
        d_ = f"M{x:.1f} {dy:.1f} L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + f" L{x + pw:.1f} {dy:.1f} Z"
        s.path(d_, fill=DN, fill_opacity=0.22)
        s.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts), stroke=DN, sw=1.2)
        # макс. просадка
        i_min = dd.index(min(dd))
        mx, my = tx_of(D.DAYS[i_min], x, pw), dy + dd_h * (dd[i_min] / span)
        s.circle(mx, my, 3.5, fill=DN)
        s.text(mx + 8, my + 4, D.RESULT_HONEST["max_dd"], size=11, fill=T1, weight=700)
        # период под водой 24.02.2022 — 05.01.2023
        ua, ub = tx_of(date(2022, 2, 24), x, pw), tx_of(date(2023, 1, 5), x, pw)
        by_ = dy + dd_h - 8
        s.line(ua, by_, ub, by_, T1, sw=1)
        s.line(ua, by_ - 4, ua, by_ + 4, T1, sw=1)
        s.line(ub, by_ - 4, ub, by_ + 4, T1, sw=1)
        s.text(ub + 6, by_ + 4, "214 дней под водой, до 05.01.2023", size=11, fill=T2)
        year_axis(s, x, dy + dd_h + 6, pw)
    else:
        year_axis(s, x, y + eh + 6, pw)
    return pw


# --- экран B4: Отчёт прогона ---------------------------------------------------------
def b4():
    H = 1080
    s = Svg(W, H, BASE)
    topbar(s, 3)
    run_tape(s)
    ys = H - SCRUB
    watchlist(s, Y0, ys)
    # слои графика под watchlist
    wy = Y0 + 36 + 48 * 7 + 16
    s.line(0, wy - 16, LW, wy - 16, GRID)
    s.text(16, wy + 14, "Слои графика", size=13, fill=T1, weight=700)
    layers = [("Сделки", True, None), ("SMA 20", True, T2), ("SMA 50", True, SEL), ("Объём", True, None),
              ("Линия знания", True, Y), ("Сделки наивного прогона", False, None)]
    ly = wy + 36
    for name, on, col in layers:
        checkbox(s, 16, ly, on)
        s.text(42, ly + 5, name, size=13, fill=T1 if on else T2)
        if col:
            s.line(LW - 36, ly, LW - 16, ly, col, sw=2)
        ly += 28
    s.line(0, ly, LW, ly, GRID)
    s.text(16, ly + 28, "Прогон на графиках", size=13, fill=T1, weight=700)
    seg(s, 16, ly + 44, LW - 32, ["Честный", "Наивный", "Оба"], 0)
    ly += 44 + 32 + 16
    s.line(0, ly, LW, ly, GRID)
    bar_n = D.DAYS.index(cday(KNOW_I)) + 1
    s.text(16, ly + 28, "Позиция воспроизведения", size=12, fill=T3)
    s.text(16, ly + 48, dstr(cday(KNOW_I)) + ", бар " + f"{bar_n:,}".replace(",", " ") + " из " + f"{len(D.DAYS):,}".replace(",", " "), size=13, fill=T1, weight=700)
    s.para(16, ly + 72, "Стратегия видит только бары левее жёлтой линии. Правее — то, что ей ещё неизвестно.", LW - 32,
           size=12, lh=18, fill=T2)

    # тайл 1: свечи
    y = Y0 + G
    th = 364
    body = panel(s, CX, y, CW, th, "SBER, D1", "01.09 — 31.12.2025, 90 баров")
    legend(s, CR - 12, y + 18, [("Покупка", UP, "dot"), ("Частично", WARN, "dot"), ("Продажа", DN, "dot"),
                                ("Отказ", T2, "dot"), ("SMA 20", T2, "line"), ("SMA 50", SEL, "line")])
    g = candle_chart(s, CX + 12, body + 8, CW - 24, th - 36 - 12)
    # подписи сделок
    for idx, kind, lbl in D.TRADE_MARKERS:
        c = CANDLES[idx]
        mx = g["X"](idx)
        lows = min(CANDLES[j]["l"] for j in range(max(0, idx - 3), min(len(CANDLES), idx + 4)))
        ty_ = g["Y"](lows) + 34
        my0 = g["Y"](c["l"]) + (18 if kind != "sell" else 4)
        if kind == "sell":
            my0 = g["Y"](c["l"]) + 6
        col = {"buy": UP, "partial": WARN, "sell": DN, "rejected": T2}[kind]
        tw_ = measure(lbl, 11, 700) + 12
        lx = mx - 12 if kind in ("buy", "partial", "sell") else mx - tw_ + 12
        if kind == "rejected":
            lows2 = min(CANDLES[j]["l"] for j in range(idx - 10, idx + 4))
            ty_ = g["Y"](lows2) + 30
            s.line(mx, g["Y"](c["l"]) + 21, mx, ty_ - 9, col, sw=1, opacity=0.6)
        else:
            s.line(mx, my0 + 4, mx, ty_ - 9, col, sw=1, opacity=0.6)
        s.rect(lx, ty_ - 9, tw_, 18, BASE, rx=4, stroke=col)
        tc(s, lx + 6, ty_, lbl, size=11, fill=col, weight=700)

    # тайл 2: капитал + underwater
    y2 = y + th + G
    lw2 = 560
    h2 = 360
    body = panel(s, CX, y2, lw2, h2, "Капитал и просадка", "1 000 000 ₽ на старте")
    legend(s, CX + lw2 - 12, y2 + 18, [("Честный", T1, "line"), ("Наивный", T2, "dash"), ("IMOEX", T3, "line")])
    equity_chart(s, CX + 12, body + 12, lw2 - 24, h2 - 36 - 20,
                 [(D.EQUITY_IMOEX, T3, 1.3, None), (D.EQUITY_NAIVE, T2, 1.5, "4 3"), (D.EQUITY_HONEST, T1, 2, None)],
                 dd=D.drawdown(D.EQUITY_HONEST), dd_h=84)
    # конечные значения справа от линий
    # тайл 3: издержки
    y3 = y2 + h2 + G
    h3 = ys - G - y3
    body = panel(s, CX, y3, lw2, h3, "Куда ушли 52,6 п.п.", "из наивных +84,2 %")
    s.text(CX + lw2 - 12, y3 + 23, "Издержки " + D.COSTS_TOTAL, size=12, fill=T2, anchor="end")
    bx, bw_ = CX + 12, lw2 - 24
    by = body + 14
    tot = 84.2
    cols = ["#FF4D4D", "#E0605A", "#C46E69", "#A87A77", "#8C8584", "#73787F"]
    # шкала: честный кусок + вклады
    hon_w = bw_ * 31.6 / tot
    s.rect(bx, by, hon_w, 20, UP, rx=3)
    tc(s, bx + 8, by + 10, "Честный +31,6 %", size=12, fill=INK, weight=700)
    cx_ = bx + hon_w
    for (name, v, rub), col in zip(D.DELTA_BREAKDOWN, cols):
        ww = bw_ * (-v) / tot
        s.rect(cx_ + 1, by, ww - 1, 20, col)
        if ww > 34:
            tc(s, cx_ + ww / 2 - measure(num(v), 11, 700) / 2, by + 10, num(v), size=11, fill=INK, weight=700)
        cx_ += ww
    s.text(bx, by + 36, "0", size=11, fill=T3)
    s.text(bx + bw_, by + 36, "+84,2 % наивный", size=11, fill=T3, anchor="end")
    # легенда-таблица 2×3
    ly = by + 60
    colw = (bw_ - 24) / 2
    for i, ((name, v, rub), col) in enumerate(zip(D.DELTA_BREAKDOWN, cols)):
        cx2 = bx + (i % 2) * (colw + 24)
        ry = ly + (i // 2) * 24
        s.rect(cx2, ry - 9, 10, 10, col, rx=2)
        vtxt = num(v) + " п.п."
        s.text(cx2 + colw, ry, vtxt, size=12, fill=T1, weight=700, anchor="end")
        rubw = 0
        if rub:
            s.text(cx2 + colw - measure(vtxt, 12, 700) - 10, ry, rub, size=12, fill=T3, anchor="end")
            rubw = measure(rub, 12) + 10
        s.text(cx2 + 18, ry, truncate(name, colw - 18 - measure(vtxt, 12, 700) - rubw - 12, 12), size=12, fill=T2)

    # тайл 4: метрики
    mx0 = CX + lw2 + G
    mw = CR - mx0
    mh = ys - G - y2
    body = panel(s, mx0, y2, mw, mh, "Метрики", "честный прогон")
    R = D.RESULT_HONEST
    s.text(mx0 + 16, body + 52, R["total"], size=40, fill=UP, weight=700)
    s.text(mx0 + 16, body + 76, "Итог за 6 лет, " + R["final"], size=13, fill=T2)
    s.text(mx0 + mw - 16, body + 30, "Наивный", size=12, fill=T3, anchor="end")
    s.text(mx0 + mw - 16, body + 50, D.RESULT_NAIVE["total"], size=16, fill=T2, weight=700, anchor="end")
    s.text(mx0 + mw - 16, body + 76, "IMOEX " + R["benchmark"], size=13, fill=T2, anchor="end")
    s.line(mx0 + 16, body + 96, mx0 + mw - 16, body + 96, GRID)
    rows = [("CAGR", R["cagr"], UP), ("Gross / net", R["gross"] + " / " + R["net"], T1),
            ("Макс. просадка", R["max_dd"], DN), ("Под водой", R["dd_days"], T1),
            ("Волатильность", R["vol"], T1), ("Sharpe / Sortino", R["sharpe"] + " / " + R["sortino"], T1),
            ("Оборот", R["turnover"], T1), ("Сделки / win rate", R["trades"] + " / " + R["win_rate"], T1),
            ("Частичные / отказы", R["partial"] + " / " + R["rejected"], WARN), ("HHI", R["hhi"], T1),
            ("Крупнейшая позиция", R["top_position"], T1), ("Против IMOEX", R["vs_benchmark"], UP)]
    ry = body + 124
    for k, v, col in rows:
        kv(s, mx0 + 16, ry, mw - 32, k, v, size=13, vcol=col, bold=True)
        ry += 30
    s.line(mx0 + 16, y2 + mh - 64, mx0 + mw - 16, y2 + mh - 64, GRID)
    disclaimer(s, mx0 + 16, y2 + mh - 40, mw - 32, size=11)

    # правая колонка: предупреждения, лента, воспроизводимость
    right_col(s, ys)
    x0 = RX + 16
    rw = RW - 32
    yy = Y0 + 4
    tx_ = x0
    for i, (tname, cnt) in enumerate([("Предупреждения", "4"), ("Лента", "6")]):
        on = i == 0
        tw_ = measure(tname, 13, 700 if on else 400)
        tc(s, tx_, yy + 18, tname, size=13, fill=T1 if on else T2, weight=700 if on else 400)
        cw_ = measure(cnt, 11, 700) + 10
        s.rect(tx_ + tw_ + 6, yy + 9, cw_, 18, WARN if on else SURF2, rx=4, opacity=0.18 if on else None)
        tc(s, tx_ + tw_ + 11, yy + 18, cnt, size=11, fill=WARN if on else T2, weight=700)
        if on:
            s.rect(tx_, yy + 34, tw_ + 6 + cw_, 2, Y)
        tx_ += tw_ + 6 + cw_ + 16
    s.line(RX, yy + 36, W, yy + 36, GRID)
    yy += 52
    for f in D.FLAGS:
        col = WARN if f["level"] == "warning" else SEL
        s.icon("warn" if f["level"] == "warning" else "info", x0, yy, col)
        yy = s.para(x0 + 26, yy + 13, f["text"], rw - 26, size=13, lh=19, fill=T1) + 6
    s.line(RX, yy, W, yy, GRID)
    yy += 24
    s.text(x0, yy, "Ключевые события", size=13, fill=T1, weight=700)
    yy += 12
    events = [("24.02.2022", "Стресс: гэп по индексу, начало просадки −27,4 %", DN),
              ("28.02 — 23.03.2022", "Торгов нет, заявки не исполнялись", T2)]
    for idx, kind, lbl in D.TRADE_MARKERS:
        col = {"buy": UP, "partial": WARN, "sell": DN, "rejected": T2}[kind]
        events.append((dstr(cday(idx)), "SBER: " + lbl[0].lower() + lbl[1:], col))
    for dt, txt, col in events:
        yy += 10
        s.rect(x0, yy + 2, 3, 30, col, rx=1.5)
        s.text(x0 + 14, yy + 12, dt, size=12, fill=T3)
        s.text(x0 + 14, yy + 30, truncate(txt, rw - 14, 13), size=13, fill=T1)
        yy += 32
    yy += 12
    s.line(RX, yy, W, yy, GRID)
    yy += 24
    s.text(x0, yy, "Воспроизводимость", size=13, fill=T1, weight=700)
    yy += 8
    P = D.REPRO
    for k, v in [("Прогон", P["run"]), ("Датасет", P["dataset"]), ("Стратегия", P["strategy"]),
                 ("Движок", P["engine"]), ("Seed", P["seed"]), ("Запущен", P["started"]),
                 ("Длительность", P["duration"])]:
        yy += 22
        kv(s, x0, yy, rw, k, v, size=12)
    yy += 16
    button(s, x0, yy, "Воспроизвести", kind="secondary", h=44, icon="repeat", w=rw)

    scrubber(s, ys, pos=cday(KNOW_I))
    return s


# --- экран B2: Стратегия -------------------------------------------------------------
DSL_KW = {"strategy", "universe", "capital", "let", "when", "buy", "sell", "all"}
DSL_FN = {"sma", "crosses_above", "crosses_below", "drawdown"}


def dsl_line(s, x, y, line, size=13):
    """Простая подсветка DSL в графитовой палитре."""
    import re
    if "//" in line:
        code, com = line.split("//", 1)
        com = "//" + com
    else:
        code, com = line, ""
    toks = re.findall(r'"[^"]*"|\d[\d_]*%?|[A-Za-zА-Яа-я_]+|->|\[\+?\d\]|\S|\s+', code)
    cx = x
    for t in toks:
        if t.isspace():
            cx += measure(t, size, mono=True)
            continue
        col, wt = T2, 400
        if t.startswith('"'):
            col = UP
        elif t in DSL_KW:
            col, wt = T1, 700
        elif t in DSL_FN:
            col = SEL
        elif t[0].isdigit() or t == "-":
            col = WARN
        elif t == "->":
            col = T3
        elif t in ("fast", "slow", "close", "position", "equity", "RUB"):
            col = T1
        s.text(cx, y, t, size=size, fill=col, mono=True, weight=wt)
        cx += measure(t, size, wt, mono=True)
    if com:
        s.text(cx, y, com, size=size, fill=T3, mono=True)


def plural(n, one, few, many):
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def rule_parts(s, x, yc, parts):
    cx = x
    for p in parts:
        if isinstance(p, str):
            tc(s, cx, yc, p, size=13, fill=T3)
            cx += measure(p, 13) + 8
        else:
            label, kind = p
            bold = kind in ("act", "sell")
            tw = measure(label, 13, 700 if bold else 400)
            bw = tw + 32
            col = {"var": T1, "op": SEL, "act": UP, "sell": DN, "num": WARN}[kind]
            s.rect(cx, yc - 14, bw, 28, BASE, rx=6)
            tc(s, cx + 8, yc, label, size=13, fill=col, weight=700 if bold else 400)
            s.icon("chevron-down", cx + bw - 19, yc - 6, T3, s=12)
            cx += bw + 6
    return cx


def rule_card(s, x, y, w, line1, line2, dsl_line_no, active=False):
    """Правило конструктора в две строки: условие и действие."""
    h = 80
    s.rect(x, y, w, h, SURF2 if active else SURF, rx=10, stroke=SEL if active else None)
    rule_parts(s, x + 12, y + 22, line1)
    rule_parts(s, x + 12, y + 58, line2)
    s.text(x + w - 12, y + 63, "строка " + str(dsl_line_no), size=11, fill=SEL if active else T3, anchor="end", mono=True)
    s.icon("x", x + w - 26, y + 15, T3, s=14)


def b2():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 1)
    tape(s, [("", "SMA 20/50", T1), ("Версия", "4", T1), ("sha", "8d10…4ab2", T2), ("Чтение будущего", "не найдено", UP),
             ("Исполнение", "open t+1", T1), ("Вселенная", "6 бумаг", T1), ("Капитал", "1 000 000 RUB", T1),
             ("Прогонов", "12", T1), ("Изменена", "04.10.2026", T2)])
    yb = H
    # левая колонка: стратегии
    s.rect(0, Y0, LW, yb - Y0, PANEL)
    s.line(LW, Y0, LW, yb, GRID)
    s.text(16, Y0 + 23, "Стратегии", size=13, fill=T1, weight=700)
    s.text(LW - 16, Y0 + 23, "4", size=12, fill=T3, anchor="end")
    s.line(0, Y0 + 36, LW, Y0 + 36, GRID)
    y = Y0 + 36
    for i, st in enumerate(D.STRATEGIES):
        on = i == 0
        lines = wrap(st["desc"], LW - 32, 12)[:3]
        rh = 64 + len(lines) * 17
        if on:
            s.rect(0, y, LW, rh, SURF)
            s.rect(0, y, 2, rh, SEL)
        s.text(16, y + 24, truncate(st["name"], LW - 32, 13, 700), size=13, fill=T1, weight=700)
        for j, ln in enumerate(lines):
            s.text(16, y + 44 + j * 17, ln, size=12, fill=T2)
        s.text(16, y + rh - 14, f"{st['runs']} " + plural(st["runs"], "прогон", "прогона", "прогонов"), size=11, fill=T3)
        s.text(LW - 16, y + rh - 14, "изменена " + st["updated"], size=11, fill=T3, anchor="end")
        s.line(16, y + rh, LW - 16, y + rh, GRID)
        y += rh
    button(s, 16, y + 16, "Новая стратегия", kind="outline", icon="plus", w=LW - 32)

    # центр: конструктор (левая колонка тайлов, во всю высоту)
    y = Y0 + G
    cw1 = 452
    h1 = H - G - y
    body = panel(s, CX, y, cw1, h1, "Конструктор правил", "изменения пересобирают DSL")
    fx = CX + 16
    fw = cw1 - 32
    field(s, fx, body + 16, fw - 152 - 8, "Название", "Пересечение SMA 20/50")
    field(s, fx + fw - 152, body + 16, 152, "Капитал", "1 000 000", suffix="₽")
    yy = body + 76
    s.text(fx, yy + 14, "Вселенная", size=12, fill=T3)
    cx_ = fx + 72
    for tk in ["SBER", "GAZP", "LKOH", "GMKN", "YDEX", "MOEX"]:
        cx_ += chip(s, cx_, yy + 10, tk) + 6
    s.rect(cx_, yy - 2, 24, 24, "none", rx=6, stroke=LINE)
    s.icon("plus", cx_ + 5, yy + 3, T2, s=14)
    yy += 40
    s.line(fx, yy, fx + fw, yy, GRID)
    yy += 28
    s.text(fx, yy, "Индикаторы", size=13, fill=T1, weight=700)
    yy += 12
    for nm, per in (("fast", "20"), ("slow", "50")):
        s.rect(fx, yy, fw, 44, SURF, rx=10)
        tc(s, fx + 12, yy + 22, nm, size=13, fill=T1, weight=700, mono=True)
        tc(s, fx + 54, yy + 22, "=", size=13, fill=T3)
        small_select(s, fx + 70, yy + 6, 84, "SMA", h=32)
        tc(s, fx + 164, yy + 22, "от", size=13, fill=T3)
        small_select(s, fx + 186, yy + 6, 92, "close", h=32)
        tc(s, fx + 288, yy + 22, "за", size=13, fill=T3)
        s.rect(fx + 308, yy + 6, 44, 32, BASE, rx=8)
        tc(s, fx + 320, yy + 22, per, size=13, fill=WARN, weight=700)
        tc(s, fx + 362, yy + 22, "баров", size=13, fill=T3)
        yy += 52
    button(s, fx - 4, yy - 4, "Добавить индикатор", kind="ghost", icon="plus", h=32)
    yy += 36
    s.line(fx, yy, fx + fw, yy, GRID)
    yy += 28
    s.text(fx, yy, "Правила", size=13, fill=T1, weight=700)
    s.text(fx + fw, yy, "сигнал на закрытии бара t", size=12, fill=T3, anchor="end")
    yy += 12
    rules = [
        (["Когда", ("fast", "var"), ("пересекает снизу вверх", "op"), ("slow", "var")],
         ["то", ("купить", "act"), ("20 % капитала", "num")], True, 8),
        (["Когда", ("fast", "var"), ("пересекает сверху вниз", "op"), ("slow", "var")],
         ["то", ("продать всё", "sell")], False, 9),
        (["Когда", ("просадка позиции", "var"), ("ниже", "op"), ("−12 %", "num")],
         ["то", ("продать всё", "sell"), "стоп-лосс"], False, 10),
    ]
    for l1, l2, active, ln in rules:
        rule_card(s, fx, yy, fw, l1, l2, ln, active)
        yy += 88
    button(s, fx - 4, yy - 4, "Добавить правило", kind="ghost", icon="plus", h=32)
    yy += 36
    s.line(fx, yy, fx + fw, yy, GRID)
    yy += 16
    s.rect(fx, yy, fw, 44, SURF, rx=10)
    s.icon("lock", fx + 12, yy + 14, T3)
    s.text(fx + 40, yy + 18, "Исполнение заявок", size=12, fill=T3)
    s.text(fx + 40, yy + 36, "по open следующего бара, задаёт движок", size=13, fill=T1)
    fy = y + h1 - 16 - 44
    s.text(fx, fy + 27, "Сохранено как версия 4, 04.10.2026", size=12, fill=T3)
    s.rect(fx + fw - 168, fy, 168, 44, SURF, rx=10)
    tc(s, fx + fw - 168 + (168 - measure("Изменений нет", 14, 700)) / 2, fy + 22, "Изменений нет", size=14, fill=T3, weight=700)

    # центр справа сверху: DSL-превью
    dx = CX + cw1 + G
    dw = CR - dx
    hd = 404
    body = panel(s, dx, y, dw, hd, "DSL", "только чтение")
    badge(s, dx + 12 + measure("DSL", 13, 700) + 10 + measure("только чтение", 12) + 10, y + 18, "версия 4", T2)
    button(s, dx + dw - 12 - 96, y + 4, "Копировать", kind="ghost", h=28, w=96, size=12)
    ly = body + 10
    lh = 22
    for i, ln in enumerate(D.DSL_MAIN):
        n = i + 1
        yl = ly + i * lh
        if n == 8:
            s.rect(dx, yl, dw, lh, SEL, opacity=0.10)
            s.rect(dx, yl, 2, lh, SEL)
        s.text(dx + 30, yl + 15, str(n), size=12, fill=T3 if n != 8 else SEL, mono=True, anchor="end")
        if ln:
            dsl_line(s, dx + 42, yl + 15, ln, size=12)
    yl = ly + len(D.DSL_MAIN) * lh + 12
    s.line(dx, yl, dx + dw, yl, GRID)
    yl += 26
    s.text(dx + 16, yl, "Строка 8 собрана из первого правила", size=13, fill=T1, weight=700)
    yl = s.para(dx + 16, yl + 22, "Сигнал считается по закрытию бара t, заявка исполняется по open бара t+1 "
                "на 20 % текущего капитала.", dw - 32, size=13, lh=20, fill=T2)
    s.para(dx + 16, yl + 6, "Чтобы изменить код, правьте правила слева: DSL пересоберётся и пройдёт проверку заново.",
           dw - 32, size=12, lh=18, fill=T3)

    # центр справа снизу: что видит стратегия (линия знания)
    y3 = y + hd + G
    h3 = H - G - y3
    body = panel(s, dx, y3, dw, h3, "Что видит стратегия", "решение на баре t")
    cx0 = dx + 12
    cwid = dw - 24 - 40
    first = 44
    sub = CANDLES[first:]
    ch_y, ch_h = body + 44, h3 - 36 - 44 - 64
    lo = min(c["l"] for c in sub)
    hi = max(c["h"] for c in sub)
    for k in range(4):
        py = ch_y + ch_h * k / 3
        s.line(cx0, py, cx0 + cwid, py, GRID)
        s.text(cx0 + cwid + 8, py + 4, num(hi - (hi - lo) * k / 3, 0), size=11, fill=T3)
    geo = s.candles(sub, cx0, ch_y, cwid, ch_h, UP, DN, gap=0.35)
    X, bw = geo["X"], geo["bw"]
    ki = KNOW_I - first
    kx = X(ki) + bw / 2
    top = ch_y - 30
    # окно sma 20
    wx = X(ki - 19) - bw / 2
    s.rect(wx, top, kx - wx, ch_h + 30, SEL, opacity=0.08)
    s.line(wx, top + 10, kx - 2, top + 10, SEL, sw=1.5)
    s.line(wx, top + 5, wx, top + 15, SEL, sw=1.5)
    s.text(wx + 6, top + 26, "sma(close, 20)", size=11, fill=SEL, weight=700)
    # будущее
    fw_ = cx0 + cwid - kx
    s.rect(kx, top, fw_, ch_h + 30, BASE, opacity=0.62)
    hatch(s, kx, top, fw_, ch_h + 30, T2, step=8, opacity=0.35)
    nx = X(ki + 1)
    c1 = sub[ki + 1]
    s.rect(nx - bw / 2, top, bw, ch_h + 30, DN, opacity=0.22)
    s.circle(nx, geo["Y"](c1["c"]), 4, fill=DN)
    s.rect(kx - 1, top, 2, ch_h + 30, Y)
    lbl = "t"
    s.rect(kx - 9, top - 2, 18, 18, Y, rx=4)
    s.text(kx, top + 11, lbl, size=11, fill=INK, weight=700, anchor="middle")
    for j, ln in enumerate(wrap("Будущее скрыто от стратегии", fw_ - 20, 11, 700)):
        s.text(kx + fw_ / 2 + 4, top + 26 + j * 14, ln, size=11, fill=T1, weight=700, anchor="middle")
    for i in (0, 15, 30, 45):
        s.text(X(i), ch_y + ch_h + 18, dstr(cday(first + i), False), size=11, fill=T3, anchor="middle")
    # пояснение под графиком
    ny = ch_y + ch_h + 34
    s.rect(cx0, ny, 10, 10, DN, rx=2, opacity=0.8)
    s.para(cx0 + 18, ny + 9, "close[+1] — бар t+1. Если правило его читает, проверка остановит прогон до запуска.",
           dw - 24 - 18, size=12, lh=17, fill=T2)

    # правая колонка: проверка
    right_col(s, H)
    x0 = RX + 16
    rw = RW - 32
    yy = Y0 + 23
    s.text(x0, yy, "Проверка чтения будущего", size=13, fill=T1, weight=700)
    s.line(RX, Y0 + 36, W, Y0 + 36, GRID)
    yy = Y0 + 52
    s.rect(x0, yy, rw, 88, UP, rx=12, opacity=0.10)
    s.icon("check", x0 + 14, yy + 16, UP, s=20, sw=2)
    s.text(x0 + 44, yy + 32, "Версия 4 чистая", size=16, fill=T1, weight=700)
    s.para(x0 + 44, yy + 54, "Все индикаторы читают бары до t включительно", rw - 56, size=12, lh=17, fill=T2)
    yy += 88 + 24
    s.text(x0, yy, "Три уровня проверки", size=12, fill=T3)
    yy += 8
    ctx = {"ok": ("OK", UP, "Версия 4, сейчас"), "warning": ("Подозрительно", WARN, "Версия 3, исправлено"),
           "error": ("Ошибка", DN, "Версия 2, run-0139 невалиден")}
    for chk in D.LOOKAHEAD_CHECKS:
        lbl, col, where = ctx[chk["level"]]
        yy += 12
        top = yy
        bw_ = badge(s, x0 + 12, yy + 22, lbl, col)
        s.text(x0 + rw - 12, yy + 26, "строка " + str(chk["line"]), size=12, fill=T3, anchor="end")
        s.rect(x0 + 12, yy + 40, rw - 24, 26, BASE, rx=6)
        s.text(x0 + 20, yy + 57, truncate(chk["code"], rw - 40, 12, mono=True), size=12, fill=T1, mono=True)
        ey = s.para(x0 + 12, yy + 86, chk["msg"], rw - 24, size=12, lh=17, fill=T2)
        s.text(x0 + 12, ey + 4, where, size=11, fill=T3)
        yy = ey + 16
        s.rect(x0, top, rw, yy - top, "none", rx=10, stroke=GRID)
        s.rect(x0, top + 10, 2, yy - top - 20, col)
    yy += 16
    bw_ = button(s, x0, yy, "Проверить снова", kind="secondary", h=44, icon="repeat", w=rw)
    return s


# --- общие для таблиц ----------------------------------------------------------------
def col_x(x, cols):
    out, cx = [], x
    for c in cols:
        out.append(cx)
        cx += c[1]
    return out


def table_head(s, x, y, w, cols, h=32):
    xs = col_x(x + 12, cols)
    for (label, cw, al), cx in zip(cols, xs):
        if al == "r":
            s.text(cx + cw - 12, y + h / 2 + 4, label, size=12, fill=T3, anchor="end")
        else:
            s.text(cx, y + h / 2 + 4, label, size=12, fill=T3)
    s.line(x, y + h, x + w, y + h, GRID)
    return xs


def cell(s, cx, cw, al, yb, txt, size=13, fill=T1, weight=400, mono=False):
    room = cw - 12
    txt = truncate(txt, room, size, weight, mono)
    if al == "r":
        s.text(cx + cw - 12, yb, txt, size=size, fill=fill, weight=weight, anchor="end", mono=mono)
    else:
        s.text(cx, yb, txt, size=size, fill=fill, weight=weight, mono=mono)


STATUS_COL = {"valid": UP, "warning": WARN, "invalid": DN}


# --- экран B1: Датасеты --------------------------------------------------------------
def b1():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 0)
    ds = D.DATASET_CURRENT
    tape(s, [("", ds["id"], T1), ("Источник", ds["source"]), ("Интервал", ds["interval"]), ("Строк", ds["rows"]),
             ("sha", ds["sha"], T2), ("Схема", ds["schema"]), ("Получен", ds["fetched"]),
             ("В прогонах", str(ds["used_in"])), ("Статус", ds["status"], UP)])
    yl = watchlist(s, Y0, H, selected=None, title="Тикеры снапшота", sub=ds["id"])
    s.line(0, yl, LW, yl, GRID)
    s.text(16, yl + 32, "Источники", size=13, fill=T1, weight=700)
    yy = yl + 44
    for name, cnt, note in (("MOEX ISS", "3", None), ("ЦБ РФ", "1", None), ("Генератор", "", "после MVP")):
        yy += 8
        s.rect(16, yy, LW - 32, 36, SURF if name == "MOEX ISS" else "none", rx=8)
        s.icon("db" if not note else "lock", 28, yy + 10, T2 if not note else T3)
        tc(s, 54, yy + 18, name, size=13, fill=T1 if not note else T3)
        if note:
            badge(s, LW - 24 - measure(note, 11, 700) - 12, yy + 18, note, T3, size=11)
        else:
            s.text(LW - 28, yy + 23, cnt, size=13, fill=T2, anchor="end")
        yy += 36

    # тайл: снапшоты
    y = Y0 + G
    th = 308
    body = panel(s, CX, y, CW, th, "Снапшоты", "неизменяемые: правка данных создаёт новый снапшот")
    button(s, CR - 12 - 224, y + 4, "Загрузить новый снапшот", kind="outline", icon="download", h=28, w=224, size=12)
    cols = [("Снапшот", 80, "l"), ("Источник и тикеры", 184, "l"), ("Инт.", 40, "l"), ("Период", 160, "l"),
            ("Получен", 124, "l"), ("sha и схема", 96, "l"), ("Прогоны", 64, "r"), ("Статус", 120, "l")]
    xs = table_head(s, CX, body, CW, cols)
    ry = body + 32
    st_col = {"актуальный": UP, "заменён ds-0007": T2, "устаревшая схема": WARN, "после MVP": T3}
    for d in D.DATASETS:
        rh = 48
        on = d["id"] == ds["id"]
        mvp = d["status"] == "после MVP"
        if on:
            s.rect(CX, ry, CW, rh, SURF)
            s.rect(CX, ry, 2, rh, SEL)
        c1 = T3 if mvp else T1
        cell(s, xs[0], cols[0][1], "l", ry + 21, d["id"], 13, c1, 700)
        cell(s, xs[1], cols[1][1], "l", ry + 21, d["source"], 13, c1)
        cell(s, xs[1], cols[1][1], "l", ry + 38, d["tickers"], 12, T3)
        cell(s, xs[2], cols[2][1], "l", ry + 21, d["interval"], 13, c1)
        cell(s, xs[3], cols[3][1], "l", ry + 21, d["period"], 13, c1)
        if d["rows"] != "—":
            cell(s, xs[3], cols[3][1], "l", ry + 38, d["rows"] + " строк", 12, T3)
        cell(s, xs[4], cols[4][1], "l", ry + 21, d["fetched"], 13, c1)
        cell(s, xs[5], cols[5][1], "l", ry + 21, d["sha"], 12, c1, mono=True)
        cell(s, xs[5], cols[5][1], "l", ry + 38, "схема " + d["schema"], 12, T3)
        cell(s, xs[6], cols[6][1], "r", ry + 21, str(d["used_in"]) if d["used_in"] else "—", 13, c1)
        lbl = d["status"] if d["status"] != "заменён ds-0007" else "заменён"
        badge(s, xs[7], ry + 16, lbl, st_col[d["status"]], size=11)
        if d["status"] == "заменён ds-0007":
            s.text(xs[7], ry + 40, "на ds-0007", size=12, fill=T3)
        s.line(CX, ry + rh, CR, ry + rh, GRID)
        ry += rh

    # тайл: торговый календарь
    y2 = y + th + G
    h2 = 252
    body = panel(s, CX, y2, CW, h2, "Торговый календарь", ds["period"] + ", каждая клетка — неделя")
    legend(s, CR - 12, y2 + 18, [("5 торговых дней", UP, "box"), ("Неполная неделя", "#2E6B57", "box"),
                                 ("Торгов не было", DN, "box")])
    all_days = D.trading_days(date(2019, 1, 3), date(2026, 9, 25))
    dset = set(all_days)
    gx0 = CX + 52
    gw = CW - 52 - 16
    cwk = gw / 53
    gy0 = body + 32
    rowh = 18
    months = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    for m in range(12):
        mx = gx0 + cwk * ((date(2021, m + 1, 1) - date(2021, 1, 1)).days / 7)
        s.text(mx, body + 22, months[m], size=11, fill=T3)
    from datetime import timedelta
    gap_cells = []
    for r, yr in enumerate(range(2019, 2027)):
        ry = gy0 + r * rowh
        s.text(CX + 12, ry + 12, str(yr), size=12, fill=T2 if yr != 2022 else T1, weight=700 if yr == 2022 else 400)
        for k in range(53):
            d0 = date(yr, 1, 1) + timedelta(days=7 * k)
            if d0.year != yr:
                continue
            days = [d0 + timedelta(days=j) for j in range(7)]
            n = sum(1 for d in days if d in dset)
            cx = gx0 + k * cwk
            in_cov = date(2019, 1, 3) <= d0 + timedelta(days=6) and d0 <= date(2026, 9, 25)
            in_gap = any(date(2022, 2, 28) <= d <= date(2022, 3, 23) for d in days)
            if not in_cov:
                s.rect(cx, ry, cwk - 3, rowh - 6, SURF, rx=2)
            elif in_gap and n < 5:
                s.rect(cx, ry, cwk - 3, rowh - 6, DN, rx=2, opacity=0.85 if n == 0 else 0.45)
                gap_cells.append((cx, ry))
            elif n == 5:
                s.rect(cx, ry, cwk - 3, rowh - 6, UP, rx=2, opacity=0.55)
            else:
                s.rect(cx, ry, cwk - 3, rowh - 6, "#2E6B57", rx=2)
    # выноска к разрыву
    gx_a = min(c[0] for c in gap_cells)
    gx_b = max(c[0] for c in gap_cells) + cwk - 3
    gy_ = gap_cells[0][1]
    s.rect(gx_a - 3, gy_ - 3, gx_b - gx_a + 6, rowh, "none", rx=3, stroke=DN, sw=1.5)
    ay = gy0 + 8 * rowh + 8
    s.line(gx_a + 10, gy_ + rowh - 3, gx_a + 10, ay + 4, DN, sw=1)
    s.line(gx_a + 10, ay + 4, gx_a + 22, ay + 4, DN, sw=1)
    s.text(gx_a + 28, ay + 8, f"{D.CALENDAR_GAP[0]} — {D.CALENDAR_GAP[1]}: {D.CALENDAR_GAP[2]}", size=12, fill=T1,
           weight=700)
    s.text(gx_a + 28, ay + 24, "Движок пропускает эти дни: сигналы не считаются, заявки ждут первого торгового дня.",
           size=12, fill=T2)

    # тайл: поля и момент доступности
    y3 = y2 + h2 + G
    h3 = H - G - y3
    body = panel(s, CX, y3, CW, h3, "Поля и момент доступности", "когда значение бара t становится известно стратегии")
    lx = CX + 16
    ax0 = CX + 136
    ax1 = CR - 24
    P = {"open": 0.10, "close": 0.52, "next": 0.90}
    X = lambda f: ax0 + (ax1 - ax0) * f
    ay0 = body + 26
    rows_y0 = ay0 + 10
    rh = 24
    n = len(D.DATASET_FIELDS)
    s.line(ax0, ay0, ax1, ay0, LINE)
    for key, lbl, col in (("open", "10:00, день t", T2), ("close", "18:50, закрытие t", Y), ("next", "10:00, день t+1", T2)):
        px = X(P[key])
        s.line(px, ay0 - 4, px, rows_y0 + n * (rh + 4), col, sw=1 if col != Y else 2, dash=None if col == Y else "3 3")
        s.text(px + 6, ay0 - 6, lbl, size=11, fill=col if col == Y else T2, weight=700 if col == Y else 400)
    s.text(X(P["close"]) - 6, rows_y0 + n * (rh + 4) + 14, "решение стратегии", size=11, fill=Y, anchor="end")
    s.text(X(P["next"]) - 6, rows_y0 + n * (rh + 4) + 14, "исполнение заявки", size=11, fill=T2, anchor="end")
    for i, (fld, note) in enumerate(D.DATASET_FIELDS):
        ry = rows_y0 + i * (rh + 4)
        forbidden = "запрещено" in note
        s.text(lx, ry + 16, fld, size=12, fill=T1 if not forbidden else DN, mono=True, weight=700)
        if forbidden:
            s.rect(ax0, ry, ax1 - ax0, rh, DN, opacity=0.08, rx=4)
            hatch(s, ax0, ry, ax1 - ax0, rh, DN, step=8, opacity=0.25)
            s.rect(ax0 + 8, ry + 3, measure(note, 12, 700) + 16, rh - 6, BASE, rx=4)
            s.text(ax0 + 16, ry + 16, note, size=12, fill=DN, weight=700)
        else:
            f0 = P["open"] if fld == "open" else P["close"]
            s.rect(X(f0), ry, ax1 - X(f0), rh, UP, opacity=0.16, rx=4)
            s.rect(X(f0), ry, 3, rh, UP, rx=1)
            s.text(X(f0) + 12, ry + 16, note, size=12, fill=T1)
            if fld != "open":
                s.text(X(P["open"]) + 8, ry + 16, "ещё неизвестно", size=12, fill=T3)

    # правая колонка: карточка снапшота
    right_col(s, H)
    x0 = RX + 16
    rw = RW - 32
    yy = Y0 + 40
    s.text(x0, yy, ds["id"], size=24, fill=T1, weight=700)
    badge(s, x0 + measure(ds["id"], 24, 700) + 12, yy - 8, ds["status"], UP)
    s.text(x0, yy + 24, ds["source"] + ", дневные бары", size=13, fill=T2)
    yy += 52
    s.line(RX, yy, W, yy, GRID)
    yy += 8
    for k, v, mono in (("Период", ds["period"], False), ("Получен", ds["fetched"], False), ("Строк", ds["rows"], False),
                       ("sha", ds["sha"], True), ("Схема", ds["schema"], False)):
        yy += 26
        kv(s, x0, yy, rw, k, v, size=13, mono=mono)
    yy += 26
    s.text(x0, yy, "Тикеры", size=13, fill=T2)
    yy = s.para(x0 + 72, yy, ds["tickers"], rw - 72, size=13, lh=20, fill=T1)
    yy += 10
    s.rect(x0, yy, rw, 76, SURF, rx=10)
    s.icon("lock", x0 + 12, yy + 12, T2)
    s.para(x0 + 38, yy + 25, "Снапшот нельзя изменить. Новые данные загружаются отдельным снапшотом с новым sha.",
           rw - 50, size=12, lh=17, fill=T2)
    yy += 76 + 28
    s.text(x0, yy, "Используется в 9 прогонах", size=13, fill=T1, weight=700)
    yy += 4
    for r in [r for r in D.RUNS if r["dataset"] == ds["id"]][:5]:
        yy += 28
        s.circle(x0 + 4, yy - 4, 3.5, fill=STATUS_COL[r["status"]])
        s.text(x0 + 16, yy, r["id"], size=13, fill=T1)
        s.text(x0 + 88, yy, truncate(r["strategy"] + ", " + r["mode"], rw - 88, 12), size=12, fill=T2)
    yy += 24
    s.text(x0, yy, "Показать все 9", size=13, fill=SEL)
    button(s, x0, H - 16 - 44, "Загрузить новый снапшот", kind="secondary", h=44, icon="download", w=rw)
    s.text(x0, H - 16 - 44 - 12, "Прежние снапшоты не изменятся", size=12, fill=T3)
    return s


# --- экран B3: Настройка прогона ------------------------------------------------------
def b3():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 2)
    C = D.RUN_CONFIG
    tape(s, [("", "Новый прогон", T1), ("Стратегия", "SMA 20/50 v4"), ("Датасет", C["dataset"]), ("Период", C["period"]),
             ("Баров", "1 545"), ("Капитал", C["capital"]), ("Исполнение", "open t+1"), ("Seed", C["seed"], T2)])
    yl = watchlist(s, Y0, H, selected=None, sub="SMA 20/50")
    s.line(0, yl, LW, yl, GRID)
    s.text(16, yl + 32, "Взять настройки из прогона", size=13, fill=T1, weight=700)
    yy = yl + 44
    for rid, txt in (("run-0142", "честный и наивный"), ("run-0134", "стресс 24.02.2022"), ("run-0136", "RSI-откат, ds-0006")):
        yy += 6
        s.rect(16, yy, LW - 32, 44, SURF if rid == "run-0142" else "none", rx=8, stroke=None if rid == "run-0142" else GRID)
        s.text(28, yy + 19, rid, size=13, fill=T1, weight=700)
        s.text(28, yy + 35, txt, size=12, fill=T3)
        if rid == "run-0142":
            badge(s, LW - 28 - measure("текущие", 11, 700) - 12, yy + 22, "текущие", SEL, size=11)
        yy += 44

    # тайл: данные и период
    y = Y0 + G
    h1 = 228
    body = panel(s, CX, y, CW, h1, "Данные и период", "ds-0007 покрывает 03.01.2019 — 25.09.2026")
    fx = CX + 16
    fy = body + 16
    fw_ = [216, 148, 148, 168]
    field(s, fx, fy, fw_[0], "Датасет", "ds-0007, MOEX ISS", select=True)
    field(s, fx + 224, fy, fw_[1], "Начало", "03.01.2020")
    field(s, fx + 380, fy, fw_[2], "Конец", "30.12.2025")
    field(s, fx + 536, fy, fw_[3], "Капитал", "1 000 000", suffix="₽")
    s.rect(fx + 712, fy, CW - 32 - 712, 44, "none", rx=10, stroke=GRID)
    s.text(fx + 724, fy + 17, "Бары", size=12, fill=T3)
    s.text(fx + 724, fy + 35, "D1, 1 545 дней", size=14, fill=T2)
    # полоса покрытия снапшота с выбранным окном
    a, b = date(2019, 1, 3), date(2026, 9, 25)
    tx0, tw0 = CX + 16, CW - 32
    ty0, th0 = fy + 44 + 24, 92
    s.rect(tx0, ty0, tw0, th0, BASE, rx=6)
    xa, xb = tx_of(date(2020, 1, 3), tx0, tw0, a, b), tx_of(date(2025, 12, 30), tx0, tw0, a, b)
    s.rect(xa, ty0, xb - xa, th0, SEL, opacity=0.08)
    eq = D.EQUITY_IMOEX
    tseries(s, eq, xa, ty0 + 10, xb - xa, th0 - 20, min(eq), max(eq), T2, sw=1.3, step=3,
            a=D.DAYS[0], b=D.DAYS[-1])
    stress_bands(s, tx0, ty0, tw0, th0, labels=False, a=a, b=b)
    s.rect(xa - 1, ty0 - 4, 2, th0 + 8, SEL)
    s.rect(xb - 1, ty0 - 4, 2, th0 + 8, SEL)
    s.rect(xa - 4, ty0 + th0 / 2 - 10, 8, 20, SEL, rx=3)
    s.rect(xb - 4, ty0 + th0 / 2 - 10, 8, 20, SEL, rx=3)
    s.text(xa + 14, ty0 + 18, "IMOEX в выбранном периоде", size=11, fill=T2)
    year_axis(s, tx0, ty0 + th0 + 8, tw0, a=a, b=b)

    # тайл: издержки
    y2 = y + h1 + G
    w2 = 468
    h2 = 412
    body = panel(s, CX, y2, w2, h2, "Издержки и исполнение", "все виды включены")
    fx, fw = CX + 16, w2 - 32
    hw = (fw - 8) / 2
    yy = body + 16
    field(s, fx, yy, hw, "Комиссия брокера", C["commission"])
    field(s, fx + hw + 8, yy, hw, "Биржевой сбор", C["exchange_fee"])
    yy += 52
    field(s, fx, yy, hw, "Спред", C["spread"])
    field(s, fx + hw + 8, yy, hw, "Проскальзывание", "0,10 % + 0,5 × доля")
    yy += 52
    s.rect(fx, yy, fw, 64, SURF, rx=10)
    s.text(fx + 12, yy + 17, "Лимит ликвидности", size=12, fill=T3)
    s.para(fx + 12, yy + 35, C["liquidity"], fw - 24, size=14, lh=20, fill=T1)
    yy += 72
    s.rect(fx, yy, fw, 44, "none", rx=10, stroke=GRID)
    s.icon("lock", fx + 12, yy + 14, T3)
    s.text(fx + 38, yy + 17, "Задержка исполнения", size=12, fill=T3)
    s.text(fx + 38, yy + 35, C["delay"], size=14, fill=T1)
    yy += 52
    s.para(fx, yy + 12, "Проскальзывание растёт с долей заявки в объёме бара: 0,10 % плюс половина этой доли. "
           "Задержку в честном прогоне отключить нельзя.", fw, size=12, lh=18, fill=T3)

    # тайл: стресс-сценарий
    x3 = CX + w2 + G
    w3 = CR - x3
    body = panel(s, x3, y2, w3, h2, "Стресс-сценарий", "накладывается на исторические данные")
    fx, fw = x3 + 16, w3 - 32
    yy = body + 12
    opts = [dict(name="Не применять", desc="Исторические данные как есть", gap=None)] + D.STRESS_PRESETS
    for i, o in enumerate(opts):
        on = i == 0
        custom = o["name"] == "Свой сценарий"
        hh = 44 if o["gap"] is None else (80 if not custom else 112)
        s.rect(fx, yy, fw, hh, SURF2 if on else SURF, rx=10, stroke=Y if on else None)
        if o["gap"] is None:
            radio(s, fx + 12, yy + 22, on)
            tc(s, fx + 40, yy + 22, o["name"], size=13, fill=T1, weight=700)
            tc(s, fx + 40 + measure(o["name"], 13, 700) + 10, yy + 22, o["desc"], size=12, fill=T3)
        else:
            radio(s, fx + 12, yy + 20, on)
            s.text(fx + 40, yy + 25, o["name"], size=13, fill=T1, weight=700)
            s.text(fx + 40, yy + 44, truncate(o["desc"], fw - 52, 12), size=12, fill=T2)
        if o["gap"] and not custom:
            px = fx + 40
            for k, v in (("гэп", o["gap"]), ("волат.", o["vol"]), ("объём", o["volume"]), ("проскальз.", o["slip"])):
                s.text(px, yy + 66, k, size=12, fill=T3)
                s.text(px + measure(k, 12) + 6, yy + 66, v, size=12, fill=T1, weight=700)
                px += measure(k, 12) + 6 + measure(v, 12, 700) + 16
        if custom:
            iw = (fw - 40 - 12 - 18) / 4
            for j, (k, v) in enumerate((("Гэп", o["gap"]), ("Волатильность", o["vol"]), ("Объём", o["volume"]),
                                        ("Проскальз.", o["slip"]))):
                ix = fx + 40 + j * (iw + 6)
                s.rect(ix, yy + 56, iw, 44, BASE, rx=8)
                s.text(ix + 10, yy + 72, truncate(k, iw - 16, 11), size=11, fill=T3)
                s.text(ix + 10, yy + 91, v, size=13, fill=T3)
        yy += hh + 8

    # тайл: режим и остановка
    y4 = y2 + h2 + G
    h4 = H - G - y4
    body = panel(s, CX, y4, CW, h4, "Режим и остановка")
    hx = CX + 16
    colw = 420
    yy = body + 20
    toggle(s, hx, yy + 8, True)
    s.text(hx + 48, yy + 13, "Наивный и честный прогон вместе", size=14, fill=T1, weight=700)
    s.text(hx + 48, yy + 33, "Разница покажет, сколько стоят издержки и задержка", size=12, fill=T2)
    yy += 52
    toggle(s, hx, yy + 8, False)
    s.text(hx + 48, yy + 13, "Walk-forward", size=14, fill=T1, weight=700)
    s.text(hx + 48, yy + 33, C["walk_forward"], size=12, fill=T2)
    rx_ = CX + 16 + colw + 24
    rwid = CR - 16 - rx_
    field(s, rx_, body + 16, rwid, "Правило остановки", C["stop_rule"], select=True)
    field(s, rx_, body + 68, rwid - 52, "Seed", C["seed"])
    s.rect(rx_ + rwid - 44, body + 68, 44, 44, SURF, rx=10)
    s.icon("repeat", rx_ + rwid - 30, body + 82, T2)

    # правая колонка: перед запуском
    right_col(s, H)
    x0 = RX + 16
    rw = RW - 32
    s.text(x0, Y0 + 23, "Перед запуском", size=13, fill=T1, weight=700)
    s.line(RX, Y0 + 36, W, Y0 + 36, GRID)
    yy = Y0 + 52
    checks = [("check", UP, "Стратегия SMA 20/50, версия 4: чтение будущего не найдено"),
              ("check", UP, "Датасет ds-0007 неизменяемый, sha 3f9a…c21e"),
              ("check", UP, "Период внутри снапшота: 1 545 торговых дней"),
              ("check", UP, "Издержки включены: комиссия, сбор, спред, проскальзывание, ликвидность"),
              ("info", SEL, "28.02 — 23.03.2022 торгов не было: дни пропускаются по календарю")]
    for ic, col, txt in checks:
        s.icon(ic, x0, yy, col)
        yy = s.para(x0 + 26, yy + 13, txt, rw - 26, size=13, lh=19, fill=T1) + 12
    s.line(RX, yy, W, yy, GRID)
    yy += 28
    s.text(x0, yy, "Будет создано", size=12, fill=T3)
    s.text(x0, yy + 26, "2 прогона", size=24, fill=T1, weight=700)
    s.text(x0, yy + 48, "наивный и честный, один seed", size=13, fill=T2)
    yy += 76
    kv(s, x0, yy, rw, "Последний такой прогон", "3,8 с", size=13)
    yy += 24
    kv(s, x0, yy, rw, "Движок", "0.3.1", size=13)
    by = H - 16 - 44
    s.para(x0, by - 120, "После запуска параметры не меняются. Чтобы проверить другие настройки, запустите новый прогон.",
           rw, size=12, lh=18, fill=T3)
    button(s, x0, by - 52, "Сохранить как шаблон", kind="ghost", h=44, w=rw)
    button(s, x0, by, "Запустить прогон", kind="primary", h=44, icon="play", w=rw)
    return s


# --- экран B5: Сравнение -------------------------------------------------------------
CMP_COL = {"SMA 20/50": T1, "Моментум 3М": SEL, "RSI-откат": "#C89BF0", "IMOEX": T3}
CMP_EQ = {"SMA 20/50": D.EQUITY_HONEST, "Моментум 3М": D.EQUITY_MOMENTUM, "RSI-откат": D.EQUITY_RSI, "IMOEX": D.EQUITY_IMOEX}


def b5():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 4)
    tape(s, [("", "run-0141 и run-0142", T2), ("Наивный", D.RESULT_NAIVE["total"], T2), ("Честный", D.RESULT_HONEST["total"], UP),
             ("Разница", "−52,6 п.п.", DN), ("Издержки", D.COSTS_TOTAL, DN), ("Съедено", "62 % прибыли", WARN),
             ("Sharpe", "1,12 / 0,41"), ("Просадка", "−18,9 % / −27,4 %")])
    ys = H - SCRUB
    # левая колонка: стратегии в сравнении
    s.rect(0, Y0, LW, ys - Y0, PANEL)
    s.line(LW, Y0, LW, ys, GRID)
    s.text(16, Y0 + 23, "В сравнении", size=13, fill=T1, weight=700)
    s.text(LW - 16, Y0 + 23, "4 из 4", size=12, fill=T3, anchor="end")
    s.line(0, Y0 + 36, LW, Y0 + 36, GRID)
    yy = Y0 + 36
    for c in D.COMPARISON:
        on = c["name"] == "SMA 20/50"
        if on:
            s.rect(0, yy, LW, 56, SURF)
            s.rect(0, yy, 2, 56, SEL)
        checkbox(s, 16, yy + 20, True)
        s.rect(42, yy + 16, 10, 3, CMP_COL[c["name"]], rx=1)
        s.text(58, yy + 24, c["name"], size=13, fill=T1, weight=700)
        s.text(42, yy + 42, "честный", size=11, fill=T3)
        eq = CMP_EQ[c["name"]]
        s.series(eq, 120, yy + 30, 52, 16, min(eq), max(eq), CMP_COL[c["name"]], sw=1.2, step=12)
        s.text(LW - 16, yy + 24, c["honest"], size=13, fill=UP if c["h"] >= 0 else DN, weight=700, anchor="end")
        s.text(LW - 16, yy + 42, c["naive"], size=11, fill=T3, anchor="end")
        yy += 56
    button(s, 16, yy + 16, "Добавить прогон", kind="outline", icon="plus", w=LW - 32)
    yy += 16 + 32 + 24
    s.line(0, yy, LW, yy, GRID)
    s.text(16, yy + 28, "Разложение для", size=12, fill=T3)
    small_select(s, 16, yy + 40, LW - 32, "SMA 20/50", active=True)
    s.para(16, yy + 100, "Разница наивного и честного прогонов раскладывается по видам издержек и задержке. "
           "Сумма вкладов равна разнице.", LW - 32, size=12, lh=18, fill=T2)

    # тайл: водопад
    y = Y0 + G
    h1 = 368
    body = panel(s, CX, y, CW, h1, "Наивный +84,2 % против честного +31,6 %", "SMA 20/50, вклады в разницу 52,6 п.п.")
    s.text(CR - 12, y + 23, "Издержки " + D.COSTS_TOTAL, size=12, fill=T2, anchor="end")
    px0, px1 = CX + 16, CR - 52
    py0, py1 = body + 24, body + h1 - 36 - 76
    vmax = 90.0
    Yv = lambda v: py1 - (py1 - py0) * v / vmax
    for v in (0, 20, 40, 60, 80):
        s.line(px0, Yv(v), px1, Yv(v), GRID if v else LINE)
        s.text(px1 + 8, Yv(v) + 4, f"{v} %", size=11, fill=T3)
    steps = [("Наивный прогон", 84.2, None, "total")] + [(n, v, r, "d") for n, v, r in D.DELTA_BREAKDOWN] + \
            [("Честный прогон", 31.6, None, "end")]
    slot = (px1 - px0) / len(steps)
    bw = slot * 0.56
    level = 0.0
    prev_top = None
    for i, (name, v, rub, kind) in enumerate(steps):
        cx = px0 + slot * i + slot / 2
        if kind == "total":
            top, bot, col = 84.2, 0, T3
            level = 84.2
            val = "+84,2 %"
        elif kind == "end":
            top, bot, col = 31.6, 0, UP
            val = "+31,6 %"
        else:
            top, bot = level, level + v
            level = bot
            col = DN
            val = num(v)
        s.rect(cx - bw / 2, Yv(top), bw, Yv(bot) - Yv(top), col, rx=3, opacity=1 if kind != "d" else 0.85)
        if i < len(steps) - 1:
            nl = level
            s.line(cx + bw / 2, Yv(nl), cx + slot - bw / 2, Yv(nl), T3, dash="3 3")
        vy = Yv(top) - 8
        s.text(cx, vy, val, size=14 if kind != "d" else 13, fill=T1 if kind != "end" else UP, weight=700, anchor="middle")
        main, _, extra = name.partition(": ")
        lines = wrap(main, slot - 12, 12, 700 if kind != "d" else 400)[:2]
        for j, ln in enumerate(lines):
            s.text(cx, py1 + 20 + j * 16, ln, size=12, fill=T1, anchor="middle", weight=700 if kind != "d" else 400)
        sub_ = [rub] if rub else (wrap(extra, slot - 12, 11)[:2] if extra else [])
        for j, ln in enumerate(sub_):
            s.text(cx, py1 + 20 + (len(lines) + j) * 16, ln, size=11 if not rub else 12, fill=T3, anchor="middle")
    # подпись: доля съеденной прибыли
    bx_ = px0 + slot * 4.5
    s.rect(bx_, py0 - 6, 260, 46, BASE, rx=8, stroke=LINE)
    s.text(bx_ + 12, py0 + 13, "Съедено 62 % наивной прибыли", size=13, fill=WARN, weight=700)
    s.text(bx_ + 12, py0 + 31, "больше всего — задержка: −21,4 п.п.", size=12, fill=T2)

    # тайл: таблица стратегий
    y2 = y + h1 + G
    w2 = 540
    h2 = ys - G - y2
    body = panel(s, CX, y2, w2, h2, "Стратегии", "честный и наивный прогон, ds-0007")
    cols = [("Стратегия", 128, "l"), ("Честный", 80, "r"), ("Наивный", 80, "r"), ("Sharpe ч / н", 96, "r"),
            ("Просадка", 76, "r"), ("Оборот", 56, "r")]
    xs = table_head(s, CX, body, w2, cols)
    ry = body + 32
    for c in D.COMPARISON:
        rh = 64 if c["flag"] else 48
        on = c["name"] == "SMA 20/50"
        if on:
            s.rect(CX, ry, w2, rh, SURF)
            s.rect(CX, ry, 2, rh, SEL)
        s.rect(xs[0], ry + 15, 10, 3, CMP_COL[c["name"]], rx=1)
        cell(s, xs[0] + 16, cols[0][1] - 16, "l", ry + 21, c["name"], 13, T1, 700)
        cell(s, xs[1], cols[1][1], "r", ry + 21, c["honest"], 13, UP if c["h"] >= 0 else DN, 700)
        cell(s, xs[2], cols[2][1], "r", ry + 21, c["naive"], 13, T2)
        sh_col = WARN if c["sharpe_naive"] == "3,40" else T2
        s.text(xs[3] + cols[3][1] - 12, ry + 21, c["sharpe_naive"], size=13, fill=sh_col, anchor="end",
               weight=700 if sh_col == WARN else 400)
        s.text(xs[3] + cols[3][1] - 12 - measure(c["sharpe_naive"], 13, 700 if sh_col == WARN else 400) - 4, ry + 21, c["sharpe"] + " /",
               size=13, fill=T1, anchor="end")
        cell(s, xs[4], cols[4][1], "r", ry + 21, c["dd"], 13, T1)
        cell(s, xs[5], cols[5][1], "r", ry + 21, c["turnover"], 13, T1)
        if c["flag"]:
            col = DN if "знак" in c["flag"] else WARN
            s.icon("warn", xs[0] + 14, ry + 34, col, s=14)
            s.text(xs[0] + 34, ry + 46, c["flag"], size=12, fill=col, weight=700)
        s.line(CX, ry + rh, CX + w2, ry + rh, GRID)
        ry += rh
    disclaimer(s, CX + 12, y2 + h2 - 30, w2 - 24)

    # тайл: кривые
    x3 = CX + w2 + G
    w3 = CR - x3
    body = panel(s, x3, y2, w3, h2, "Капитал, честные прогоны")
    cx0, cy0 = x3 + 12, body + 16
    cwid, chh = w3 - 24 - 44, h2 - 36 - 16 - 56
    for v in (0.6, 1.0, 1.4):
        py = cy0 + chh - chh * (v - 0.5) / 1.0
        s.line(cx0, py, cx0 + cwid, py, GRID if v != 1.0 else LINE, dash=None if v != 1.0 else "4 3")
        s.text(cx0 + cwid + 6, py + 4, num(v, 1), size=11, fill=T3)
    stress_bands(s, cx0, cy0, cwid, chh, labels=False)
    for c in reversed(D.COMPARISON):
        tseries(s, CMP_EQ[c["name"]], cx0, cy0, cwid, chh, 0.5, 1.5, CMP_COL[c["name"]],
                sw=2 if c["name"] == "SMA 20/50" else 1.4, step=3)
    year_axis(s, cx0, cy0 + chh + 6, cwid)
    lx = cx0
    ly = cy0 + chh + 34
    for c in D.COMPARISON:
        s.rect(lx, ly - 5, 10, 3, CMP_COL[c["name"]], rx=1)
        s.text(lx + 14, ly, c["name"], size=11, fill=T2)
        lx += 14 + measure(c["name"], 11) + 12
    s.text(cx0, body - 36 + h2 - 8, "", size=11)

    # правая колонка: флаги
    right_col(s, ys)
    x0 = RX + 16
    rw = RW - 32
    s.text(x0, Y0 + 23, "Флаги сравнения", size=13, fill=T1, weight=700)
    s.line(RX, Y0 + 36, W, Y0 + 36, GRID)
    yy = Y0 + 52
    flags = [("Издержки больше 50 % прибыли", WARN, "SMA 20/50", "Съели 52,6 из 84,2 п.п. — 62 % наивной прибыли."),
             ("Издержки меняют знак результата", DN, "RSI-откат", "Наивный +38,5 % стал −6,8 %: оборот 24,7× в год."),
             ("Наивный Sharpe больше 3", WARN, "Моментум 3М", "Sharpe 3,40 без издержек выглядит нереалистично. Честный — 0,58.")]
    for title, col, who, txt in flags:
        top = yy
        s.icon("warn", x0, yy, col)
        s.text(x0 + 26, yy + 13, title, size=13, fill=T1, weight=700)
        s.text(x0 + 26, yy + 33, who, size=12, fill=col, weight=700)
        yy = s.para(x0 + 26, yy + 53, txt, rw - 26, size=12, lh=18, fill=T2) + 16
        s.line(x0, yy - 4, x0 + rw, yy - 4, GRID)
        yy += 12
    yy += 8
    s.text(x0, yy, "Без флагов", size=12, fill=T3)
    s.text(x0, yy + 20, "IMOEX: покупка и удержание, издержек нет", size=13, fill=T2)
    by = ys - 16 - 44
    button(s, x0, by - 52, "Открыть отчёт run-0142", kind="secondary", h=44, w=rw)
    button(s, x0, by, "Экспортировать сравнение", kind="ghost", h=44, icon="download", w=rw)

    scrubber(s, ys, rlabel="Период сравнения", rvalue=D.RUN_CONFIG["period"])
    return s


# --- экран B6: Walk-forward ----------------------------------------------------------
def wf_dates(w):
    a, b = w["train"].split(" — ")
    tr = date(int(a[3:]), int(a[:2]), 1)
    ts = date(int(b[3:]), int(b[:2]), 1)
    m = ts.month + 3
    te = date(ts.year + (m - 1) // 12, (m - 1) % 12 + 1, 1)
    return tr, ts, te


def b6():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 5)
    S = D.WF_SUMMARY
    tape(s, [("", "SMA 20/50, walk-forward", T1), ("Окон", S["windows"]), ("Прибыльных", S["positive"]),
             ("OOS", S["oos_avg"], UP), ("IS", S["is_avg"], T2), ("Деградация", S["degradation"], DN),
             ("OOS итого", S["oos_total"], UP)])
    ys = H - SCRUB
    SELW = 9
    # левая колонка: окна
    s.rect(0, Y0, LW, ys - Y0, PANEL)
    s.line(LW, Y0, LW, ys, GRID)
    s.text(16, Y0 + 23, "Окна", size=13, fill=T1, weight=700)
    s.text(LW - 16, Y0 + 23, "проверка, OOS", size=12, fill=T3, anchor="end")
    s.line(0, Y0 + 36, LW, Y0 + 36, GRID)
    yy = Y0 + 36
    rh = (ys - yy) / 20
    for w in D.WALK_FORWARD:
        on = w["n"] == SELW
        if on:
            s.rect(0, yy, LW, rh, SURF)
            s.rect(0, yy, 2, rh, SEL)
        yc = yy + rh / 2
        tc(s, 16, yc, f"{w['n']:02d}", size=12, fill=T3 if not on else SEL, weight=700)
        tc(s, 44, yc, w["test"], size=13, fill=T1, weight=700 if on else 400)
        tc(s, 112, yc, w["params"], size=12, fill=T2)
        v = w["test_ret"]
        col = UP if v >= 0 else DN
        bwid = 14 * abs(v) / 7
        zx = 166
        s.line(zx, yc - 6, zx, yc + 6, LINE)
        s.rect(zx if v >= 0 else zx - bwid, yc - 3, max(1, bwid), 6, col, rx=1, opacity=0.7)
        s.text(LW - 16, yc + 4.5, fmt_pct(v), size=12, fill=col, weight=700, anchor="end")
        yy += rh

    # тайл: схема окон
    y = Y0 + G
    h1 = 340
    body = panel(s, CX, y, CW, h1, "Схема окон", D.RUN_CONFIG["walk_forward"])
    legend(s, CR - 12, y + 18, [("Подбор параметров", "#4A505E", "box"), ("Проверка: прибыль", UP, "box"),
                                ("убыток", DN, "box")])
    gx0, gx1 = CX + 40, CR - 16
    gw = gx1 - gx0
    gy0 = body + 14
    rp = (h1 - 36 - 14 - 30) / 20
    a, b = date(2020, 1, 1), date(2026, 1, 1)
    for yr in range(2020, 2027):
        px = tx_of(date(yr, 1, 1), gx0, gw, a, b)
        s.line(px, gy0 - 4, px, gy0 + rp * 20, GRID)
        if yr < 2026:
            s.text(px + 4, gy0 + rp * 20 + 16, str(yr), size=11, fill=T3)
    for w in D.WALK_FORWARD:
        tr, ts, te = wf_dates(w)
        ry = gy0 + (w["n"] - 1) * rp
        on = w["n"] == SELW
        if on:
            s.rect(CX + 4, ry - 1, CW - 8, rp, SEL, opacity=0.10)
        s.text(CX + 12, ry + rp / 2 + 4, f"{w['n']:02d}", size=11, fill=SEL if on else T3, weight=700 if on else 400)
        xa, xb, xc = tx_of(tr, gx0, gw, a, b), tx_of(ts, gx0, gw, a, b), tx_of(te, gx0, gw, a, b)
        s.rect(xa, ry + 2, xb - xa - 1, rp - 5, "#4A505E", rx=2)
        s.rect(xb, ry + 2, xc - xb, rp - 5, UP if w["test_ret"] >= 0 else DN, rx=2)
        if on:
            s.text(xc + 8, ry + rp / 2 + 4, f"окно {w['n']:02d}: подбор {w['train']}, проверка {w['test']}, {fmt_pct(w['test_ret'])}",
                   size=11, fill=T1, weight=700)

    # тайл: IS vs OOS
    y2 = y + h1 + G
    w2 = 524
    h2 = ys - G - y2
    body = panel(s, CX, y2, w2, h2, "Доходность по окнам", "% за квартал")
    legend(s, CX + w2 - 12, y2 + 18, [("Подбор, IS", "#4A505E", "box"), ("Проверка, OOS", UP, "box")])
    cx0, cy0 = CX + 12, body + 20
    cwid, chh = w2 - 24 - 36, h2 - 36 - 20 - 36
    vmin, vmax = -8, 14
    Yv = lambda v: cy0 + chh - chh * (v - vmin) / (vmax - vmin)
    for v in (-5, 0, 5, 10):
        s.line(cx0, Yv(v), cx0 + cwid, Yv(v), GRID if v else LINE)
        s.text(cx0 + cwid + 6, Yv(v) + 4, (f"+{v}" if v > 0 else str(v).replace("-", "−")), size=11, fill=T3)
    slot = cwid / 20
    for i, w in enumerate(D.WALK_FORWARD):
        sx = cx0 + slot * i
        bw = slot * 0.36
        on = w["n"] == SELW
        if on:
            s.rect(sx, cy0 - 6, slot, chh + 6, SEL, opacity=0.10)
        s.rect(sx + slot * 0.1, Yv(w["train_ret"]), bw, Yv(0) - Yv(w["train_ret"]), "#4A505E", rx=1.5)
        v = w["test_ret"]
        s.rect(sx + slot * 0.1 + bw + 2, min(Yv(v), Yv(0)), bw, abs(Yv(v) - Yv(0)) or 1, UP if v >= 0 else DN, rx=1.5)
        if (i % 2 == 0) or on:
            s.text(sx + slot / 2, cy0 + chh + 16, f"{w['n']:02d}", size=11, fill=SEL if on else T3, anchor="middle")
    s.line(cx0, Yv(9.0), cx0 + cwid, Yv(9.0), T1, dash="4 3", opacity=0.7)
    s.line(cx0, Yv(0.5), cx0 + cwid, Yv(0.5), UP, dash="4 3", opacity=0.9)
    for lbl, v, col in (("IS в среднем +9,0 %", 9.0, T1), ("OOS в среднем +0,5 %", 0.5, UP)):
        lw_ = measure(lbl, 11, 700) + 12
        s.rect(cx0 + cwid - lw_, Yv(v) - 9, lw_, 18, BASE, rx=4, stroke=col if col == UP else LINE)
        s.text(cx0 + cwid - lw_ + 6, Yv(v) + 4, lbl, size=11, fill=col, weight=700)

    # тайл: параметры по окнам
    x3 = CX + w2 + G
    w3 = CR - x3
    body = panel(s, x3, y2, w3, h2, "Параметры по окнам", "SMA быстрая / медленная")
    cats = ["25/60", "20/60", "20/55", "20/50", "15/45", "15/40"]
    px0, py0 = x3 + 60, body + 20
    pw, ph = w3 - 60 - 16, h2 - 36 - 20 - 76
    rstep = ph / (len(cats) - 1)
    slot = pw / 20
    for j, c in enumerate(cats):
        yv = py0 + j * rstep
        s.line(px0, yv, px0 + pw, yv, GRID)
        s.text(x3 + 12, yv + 4, c, size=12, fill=T1 if c == "20/50" else T2, weight=700 if c == "20/50" else 400)
    pts = []
    for i, w in enumerate(D.WALK_FORWARD):
        pts.append((px0 + slot * i + slot / 2, py0 + cats.index(w["params"]) * rstep))
    s.path("M" + " L".join(f"{a_:.1f} {b_:.1f}" for a_, b_ in pts), stroke=T3, sw=1.2)
    for i, (px, py) in enumerate(pts):
        on = i + 1 == SELW
        s.circle(px, py, 5 if on else 3.5, fill=SEL if on else (T1 if D.WALK_FORWARD[i]["params"] == "20/50" else T2),
                 stroke=PANEL if not on else None, sw=1)
    for i in range(0, 20, 4):
        s.text(px0 + slot * i + slot / 2, py0 + ph + 18, f"{i + 1:02d}", size=11, fill=T3, anchor="middle")
    s.text(px0 + slot * (SELW - 1) + slot / 2, py0 + ph + 18, f"{SELW:02d}", size=11, fill=SEL, anchor="middle", weight=700)
    s.line(x3 + 12, py0 + ph + 32, x3 + w3 - 12, py0 + ph + 32, GRID)
    s.para(x3 + 12, py0 + ph + 54, "Оптимальная пара SMA меняется от окна к окну: подбор подстраивается под шум.", w3 - 24,
           size=12, lh=18, fill=T2)

    # правая колонка: сводка
    right_col(s, ys)
    x0 = RX + 16
    rw = RW - 32
    s.text(x0, Y0 + 23, "Сводка walk-forward", size=13, fill=T1, weight=700)
    s.line(RX, Y0 + 36, W, Y0 + 36, GRID)
    yy = Y0 + 60
    s.text(x0, yy, "Деградация на проверке", size=12, fill=T3)
    s.text(x0, yy + 42, S["degradation"], size=40, fill=DN, weight=700)
    yy = s.para(x0, yy + 68, "На следующем квартале стратегия зарабатывает в среднем +0,5 % против +9,0 % на истории подбора.",
                rw, size=13, lh=19, fill=T2)
    yy += 8
    for k, v, col in (("Прибыльных окон", S["positive"], T1), ("OOS итого", S["oos_total"], UP),
                      ("OOS за квартал", S["oos_avg"], T1), ("IS за квартал", S["is_avg"], T2)):
        yy += 28
        kv(s, x0, yy, rw, k, v, size=13, vcol=col, bold=True)
    yy += 36
    s.text(x0, yy, "Стабильность параметров", size=12, fill=T3)
    yy = s.para(x0, yy + 20, S["stable_param"], rw, size=13, lh=19, fill=T1)
    yy += 8
    s.line(RX, yy, W, yy, GRID)
    w = D.WALK_FORWARD[SELW - 1]
    yy += 28
    s.text(x0, yy, f"Окно {SELW:02d}", size=16, fill=T1, weight=700)
    badge(s, x0 + rw - measure("худшее", 12, 700) - 12, yy - 5, "худшее", DN)
    for k, v, col in (("Подбор", w["train"], T1), ("Проверка", w["test"], T1), ("Параметры", w["params"], T1),
                      ("IS", fmt_pct(w["train_ret"]), T2), ("OOS", fmt_pct(w["test_ret"]), DN)):
        yy += 26
        kv(s, x0, yy, rw, k, v, size=13, vcol=col)
    yy += 20
    button(s, x0, yy, "Открыть отчёт окна", kind="secondary", h=44, w=rw)
    disclaimer(s, x0, ys - 16 - 30, rw)

    tr, ts, te = wf_dates(w)
    scrubber(s, ys, window=(ts, te), train=(tr, ts), rlabel=f"Окно {SELW:02d}", rvalue="проверка " + w["test"])
    return s


# --- экран B7: История прогонов ------------------------------------------------------
def b7():
    H = 900
    s = Svg(W, H, BASE)
    topbar(s, 6)
    cnt = {k: sum(1 for r in D.RUNS if r["status"] == k) for k in ("valid", "warning", "invalid")}
    tape(s, [("Прогонов", str(len(D.RUNS))), ("Валидных", str(cnt["valid"]), UP), ("С пометкой", str(cnt["warning"]), WARN),
             ("Невалидных", str(cnt["invalid"]), DN), ("Стратегий", "4"), ("Датасетов", "2"), ("Авторов", "4"),
             ("Выбрано", "2", SEL)])
    # левая колонка: фильтры
    s.rect(0, Y0, LW, H - Y0, PANEL)
    s.line(LW, Y0, LW, H, GRID)
    s.text(16, Y0 + 23, "Фильтры", size=13, fill=T1, weight=700)
    s.text(LW - 16, Y0 + 23, "Сбросить", size=12, fill=SEL, anchor="end")
    s.line(0, Y0 + 36, LW, Y0 + 36, GRID)
    yy = Y0 + 36 + 16
    s.rect(16, yy, LW - 32, 32, SURF, rx=8)
    s.icon("search", 26, yy + 8, T3)
    tc(s, 48, yy + 16, "Прогон, стратегия, автор", size=13, fill=T3)
    yy += 32 + 24

    def group(title, items, yy):
        s.text(16, yy, title, size=12, fill=T3)
        yy += 8
        for label, n, on, col in items:
            yy += 28
            checkbox(s, 16, yy - 5, on)
            if col:
                s.circle(46, yy - 5, 3.5, fill=col)
            s.text(56 if col else 42, yy, label, size=13, fill=T1 if on else T2)
            s.text(LW - 16, yy, str(n), size=12, fill=T3, anchor="end")
        return yy + 36

    yy = group("Статус", [(D.STATUS_LABEL["valid"], cnt["valid"], True, UP), (D.STATUS_LABEL["warning"], cnt["warning"], True, WARN),
                          (D.STATUS_LABEL["invalid"], cnt["invalid"], True, DN)], yy)
    yy = group("Режим", [("Честный", 6, True, None), ("Наивный", 3, True, None), ("Стресс", 1, True, None)], yy)
    yy = group("Стратегия", [("SMA 20/50", 5, True, None), ("Моментум 3М", 2, True, None), ("RSI-откат", 2, True, None),
                             ("IMOEX", 1, True, None)], yy)
    s.text(16, yy, "Датасет", size=12, fill=T3)
    small_select(s, 16, yy + 10, LW - 32, "Все датасеты")
    yy += 10 + 32 + 24
    s.text(16, yy, "Автор", size=12, fill=T3)
    small_select(s, 16, yy + 10, LW - 32, "Все авторы")

    # тайл: результаты во времени
    y = Y0 + G
    h1 = 204
    body = panel(s, CX, y, CW, h1, "Результаты прогонов", "01.10 — 05.10.2026, по времени запуска")
    legend(s, CR - 12, y + 18, [(D.STATUS_LABEL["valid"], UP, "box"), (D.STATUS_LABEL["warning"], WARN, "box"),
                                (D.STATUS_LABEL["invalid"], DN, "box")])
    runs = list(reversed(D.RUNS))
    cx0, cy0 = CX + 16, body + 34
    cwid, chh = CW - 32 - 44, h1 - 36 - 34 - 28
    vmin, vmax = -20, 104
    Yv = lambda v: cy0 + chh - chh * (v - vmin) / (vmax - vmin)
    for v in (0, 40, 80):
        s.line(cx0, Yv(v), cx0 + cwid, Yv(v), GRID if v else LINE)
        s.text(cx0 + cwid + 8, Yv(v) + 4, f"{v} %" if v else "0", size=11, fill=T3)
    slot = cwid / len(runs)
    bw = slot * 0.42
    for i, r in enumerate(runs):
        bx = cx0 + slot * i + (slot - bw) / 2
        col = STATUS_COL[r["status"]]
        sel = r["id"] in ("run-0142", "run-0141")
        if r["result"] == "—":
            s.rect(bx, Yv(30), bw, Yv(0) - Yv(30), "none", rx=2, stroke=DN, dash="3 2")
            hatch(s, bx, Yv(30), bw, Yv(0) - Yv(30), DN, step=5, opacity=0.5)
            s.text(bx + bw / 2, Yv(30) - 6, "нет", size=11, fill=DN, anchor="middle")
        else:
            v = float(r["result"].replace("+", "").replace("−", "-").replace(" %", "").replace(",", "."))
            s.rect(bx, min(Yv(v), Yv(0)), bw, abs(Yv(v) - Yv(0)), col, rx=2, opacity=0.85 if not sel else 1)
            s.text(bx + bw / 2, min(Yv(v), Yv(0)) - 6, r["result"], size=11, fill=T1 if sel else T2, anchor="middle",
                   weight=700 if sel else 400)
        if sel:
            s.rect(bx - 8, cy0 - 26, bw + 16, chh + 30, "none", rx=4, stroke=SEL)
        s.text(bx + bw / 2, cy0 + chh + 18, r["id"][4:], size=11, fill=SEL if sel else T3, anchor="middle")

    # тайл: таблица
    y2 = y + h1 + G
    h2 = H - G - y2
    s.rect(CX, y2, CW, h2, PANEL)
    # панель действий над таблицей
    s.rect(CX, y2, CW, 52, SURF)
    s.rect(CX + 16, y2 + 18, 16, 16, Y, rx=4)
    s.rect(CX + 20, y2 + 25, 8, 2, INK)
    s.text(CX + 44, y2 + 31, "Выбрано 2 прогона", size=13, fill=T1, weight=700)
    s.text(CX + 44 + measure("Выбрано 2 прогона", 13, 700) + 12, y2 + 31, "run-0142 и run-0141", size=13, fill=T2)
    bx = CR - 12
    w_ = measure("Сравнить выбранные", 13, 700) + 24 + 24
    button(s, bx - w_, y2 + 10, "Сравнить выбранные", kind="secondary", icon="compare", w=w_)
    w2_ = measure("Воспроизвести", 13, 700) + 24 + 24
    button(s, bx - w_ - 8 - w2_, y2 + 10, "Воспроизвести", kind="outline", icon="repeat", w=w2_)
    cols = [("", 32, "l"), ("Прогон", 88, "l"), ("Стратегия", 116, "l"), ("Режим", 132, "l"), ("Датасет", 76, "l"),
            ("Статус", 116, "l"), ("Результат", 84, "r"), ("Запущен", 124, "l")]
    xs = table_head(s, CX, y2 + 52, CW, cols)
    s.text(CR - 12, y2 + 52 + 20, "Автор", size=12, fill=T3, anchor="end")
    ry = y2 + 52 + 32
    for r in D.RUNS:
        inval = r["status"] == "invalid"
        rh = 58 if inval else 44
        sel = r["id"] in ("run-0142", "run-0141")
        if sel:
            s.rect(CX, ry, CW, rh, SEL, opacity=0.08)
        yb = ry + 27 if not inval else ry + 24
        checkbox(s, xs[0] + 2, yb - 5, sel)
        cell(s, xs[1], cols[1][1], "l", yb, r["id"], 13, T1, 700)
        cell(s, xs[2], cols[2][1], "l", yb, r["strategy"], 13, T1)
        cell(s, xs[3], cols[3][1], "l", yb, r["mode"], 13, T2)
        cell(s, xs[4], cols[4][1], "l", yb, r["dataset"], 13, T2)
        badge(s, xs[5], yb - 5, D.STATUS_LABEL[r["status"]], STATUS_COL[r["status"]], size=11)
        res_col = T3 if r["result"] == "—" else (UP if r["result"].startswith("+") else DN)
        if r["mode"] == "наивный" and r["result"] != "—":
            res_col = T2
        cell(s, xs[6], cols[6][1], "r", yb, r["result"], 13, res_col, 700)
        cell(s, xs[7], cols[7][1], "l", yb, r["started"], 13, T2)
        s.text(CR - 12, yb, r["author"], size=13, fill=T2, anchor="end")
        if inval:
            s.text(xs[1], ry + 46, "Причина: " + D.INVALID_REASON.split(": ", 1)[1] + ". Исправьте строку в стратегии и запустите заново.",
                   size=12, fill=DN)
        s.line(CX, ry + rh, CR, ry + rh, GRID)
        ry += rh

    # правая колонка: выбранные и невалидный
    right_col(s, H)
    x0 = RX + 16
    rw = RW - 32
    s.text(x0, Y0 + 23, "Выбранные прогоны", size=13, fill=T1, weight=700)
    s.line(RX, Y0 + 36, W, Y0 + 36, GRID)
    yy = Y0 + 52
    for rid, lbl, val, col in (("run-0142", "честный", "+31,6 %", UP), ("run-0141", "наивный", "+84,2 %", T2)):
        s.rect(x0, yy, rw, 64, SURF, rx=10)
        s.text(x0 + 12, yy + 26, rid, size=13, fill=T1, weight=700)
        s.text(x0 + 12, yy + 46, lbl + ", ds-0007", size=12, fill=T3)
        s.text(x0 + rw - 12, yy + 40, val, size=20, fill=col, weight=700, anchor="end")
        yy += 72
    s.text(x0, yy + 16, "Разница 52,6 п.п.: издержки и задержка", size=12, fill=T2)
    yy += 36
    s.line(RX, yy, W, yy, GRID)
    yy += 28
    s.text(x0, yy, "Почему run-0139 невалиден", size=13, fill=T1, weight=700)
    yy += 16
    s.rect(x0, yy, rw, 30, BASE, rx=6)
    s.text(x0 + 10, yy + 20, truncate("8  when close[+1] > close -> buy…", rw - 20, 12, mono=True), size=12, fill=T1, mono=True)
    s.line(x0 + 10 + measure("8  when ", 12, mono=True), yy + 24, x0 + 10 + measure("8  when close[+1]", 12, mono=True),
           yy + 24, DN, sw=1.5)
    yy += 30
    yy = s.para(x0, yy + 22, "close[+1] читает бар t+1, которого в момент решения ещё нет. Результат такого прогона не "
                "считается и в сравнение не попадает.", rw, size=12, lh=18, fill=T2)
    yy += 8
    button(s, x0, yy, "Открыть строку 8 в стратегии", kind="outline", h=32, icon="code", w=rw)
    disclaimer(s, x0, H - 16 - 30, rw)
    return s


SCREENS = {"B1": b1, "B2": b2, "B3": b3, "B4": b4, "B5": b5, "B6": b6, "B7": b7}


def main(which=None):
    os.makedirs(OUT, exist_ok=True)
    for k, fn in SCREENS.items():
        if which and k not in which:
            continue
        fn().save(os.path.join(OUT, k + ".svg"))
        print("ok", k)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
