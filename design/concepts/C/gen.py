"""Концепция C. Мастер: светлый, обучающий, пошаговый.

Генерирует out/C1.svg … out/C7.svg. Запуск: python gen.py
"""
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from svg import *  # noqa: E402,F401
import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --- токены ---------------------------------------------------------------------------
BG = "#F4F5F7"
WH = "#FFFFFF"
T1 = "#1B1F3B"
T2 = "#6B6E85"
T3 = "#A3A5B5"
LN = "#E3E4EA"
Y = "#FFDD2D"
YS = "#FFF4C2"
YL = "#FFFAE3"      # очень мягкий жёлтый: колонка перевода, выделенная строка
POS = "#008764"
NEG = "#EB1700"
INFO = "#4C66C3"
POS_BG = "#E2F3ED"
NEG_BG = "#FDEBE8"
INFO_BG = "#ECEFFA"
WARN_TX = "#7A5900"
NEUT = "#ECEDF1"
AMBER = "#C98A00"

W = 1440
X0, CW = 144, 1152
MX, MW = 144, 760
RX, RW = 936, 360
HEAD, STEP_H, FOOT = 64, 76, 72
GAP = 24


def bl(top, lh, size):
    """Базовая линия текста, вертикально центрированного в строке высотой lh."""
    return top + lh / 2 + size * 0.36


def T(s, x, top, txt, size=16, lh=None, fill=T1, weight=400, anchor="start", mono=False, opacity=None):
    lh = lh or round(size * 1.5)
    s.text(x, bl(top, lh, size), txt, size=size, fill=fill, weight=weight, anchor=anchor, mono=mono, opacity=opacity)
    return top + lh


def P(s, x, top, txt, width, size=16, lh=None, fill=T1, weight=400, max_lines=None, mono=False):
    lh = lh or round(size * 1.5)
    lines = wrap(txt, width, size, weight, mono)
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = truncate(lines[-1] + " …", width, size, weight, mono)
    for i, ln in enumerate(lines):
        s.text(x, bl(top + i * lh, lh, size), ln, size=size, fill=fill, weight=weight, mono=mono)
    return top + len(lines) * lh


def nlines(txt, width, size=16, weight=400):
    return len(wrap(txt, width, size, weight))


def behind(s, idx, fn):
    """Нарисовать fn(tmp) и вставить под уже нарисованное содержимое (для фона высотой по контенту)."""
    tmp = Svg()
    fn(tmp)
    s.body[idx:idx] = tmp.body


def island(s, x, y, w, h, fill=WH, stroke=LN, rx=12):
    s.rect(x + 0.5, y + 0.5, w - 1, h - 1, fill, rx=rx, stroke=stroke)


def hatch(s, x, y, w, h, color, step=6, sw=1, opacity=1.0):
    s.clip(round(x, 2), round(y, 2), round(w, 2), round(h, 2))
    k = -h
    while k < w:
        s.line(x + k, y + h, x + k + h, y, stroke=color, sw=sw, opacity=opacity)
        k += step
    s.end()


def chev_left(s, x, y, color, sw=1.6):
    s.g(x, y)
    s.path("M10 3.5 L5.5 8 L10 12.5", stroke=color, sw=sw)
    s.end()


def arrow_right(s, x, y, w, color, sw=2):
    s.line(x, y, x + w, y, stroke=color, sw=sw, cap="round")
    s.path(f"M{x + w - 8} {y - 7} L{x + w} {y} L{x + w - 8} {y + 7}", stroke=color, sw=sw)


# --- компоненты ------------------------------------------------------------------------
def button(s, x, y, label, kind="primary", size="m", icon=None, w=None, anchor="start", left_chev=False):
    h = 44 if size == "m" else 32
    fs = 16 if size == "m" else 14
    pad = 20 if size == "m" else 12
    isz = 20 if size == "m" else 16
    iw = (isz + 8) if (icon or left_chev) else 0
    tw = measure(label, fs, 700)
    bw = w or round(pad * 2 + iw + tw)
    if anchor == "end":
        x = x - bw
    rx = 12 if size == "m" else 8
    tc = T1
    if kind == "primary":
        s.rect(x, y, bw, h, Y, rx=rx)
    elif kind == "secondary":
        s.rect(x, y, bw, h, NEUT, rx=rx)
    elif kind == "outline":
        s.rect(x + 0.5, y + 0.5, bw - 1, h - 1, WH, rx=rx, stroke="#D4D6DF")
    elif kind == "flat":
        tc = INFO
    elif kind == "disabled":
        s.rect(x, y, bw, h, NEUT, rx=rx)
        tc = T3
    cx = x + (bw - (iw + tw)) / 2
    if left_chev:
        s.g(cx, y + (h - isz) / 2)
        s.raw(f'<g transform="scale({isz / 16})">')
        s.path("M10 3.5 L5.5 8 L10 12.5", stroke=tc, sw=1.8)
        s.raw("</g>")
        s.end()
        cx += iw
    elif icon:
        s.icon(icon, cx, y + (h - isz) / 2, tc, s=isz, sw=1.8)
        cx += iw
    s.text(cx, bl(y, h, fs), label, size=fs, fill=tc, weight=700)
    return bw


BADGE = {
    "pos": (POS_BG, POS), "neg": (NEG_BG, NEG), "warn": (YS, WARN_TX), "info": (INFO_BG, INFO),
    "neutral": (NEUT, T2), "yellow": (Y, T1),
}


def badge(s, x, y, label, kind="neutral", anchor="start", icon=None, h=24):
    bg, tx = BADGE[kind]
    fs = 12
    iw = 16 if icon else 0
    bw = round(measure(label, fs, 700) + 16 + iw)
    if anchor == "end":
        x -= bw
    s.rect(x, y, bw, h, bg, rx=6)
    cx = x + 8
    if icon:
        s.icon(icon, cx - 1, y + (h - 12) / 2, tx, s=12, sw=1.8)
        cx += iw
    s.text(cx, bl(y, h, fs), label, size=fs, fill=tx, weight=700)
    return bw


def status_badge(s, x, y, status, anchor="start"):
    kind = {"valid": "pos", "warning": "warn", "invalid": "neg"}[status]
    icon = {"valid": "check", "warning": "warn", "invalid": "x"}[status]
    return badge(s, x, y, D.STATUS_LABEL[status], kind, anchor=anchor, icon=icon)


def radio(s, cx, cy, on, disabled=False):
    if on:
        s.circle(cx, cy, 10, fill=Y)
        s.circle(cx, cy, 4, fill=T1)
    else:
        s.circle(cx, cy, 9.25, fill=NEUT if disabled else WH, stroke="#C5C7D3", sw=1.5)


def checkbox(s, x, y, on):
    if on:
        s.rect(x, y, 20, 20, Y, rx=6)
        s.icon("check", x + 2, y + 2, T1, s=16, sw=2)
    else:
        s.rect(x + 0.75, y + 0.75, 18.5, 18.5, WH, rx=6, stroke="#C5C7D3", sw=1.5)


def toggle(s, x, y, on):
    s.rect(x, y, 40, 24, Y if on else "#D9DBE3", rx=12)
    s.circle(x + (28 if on else 12), y + 12, 9, fill=WH)
    if on:
        s.icon("check", x + 22, y + 6, T1, s=12, sw=2)


def field(s, x, y, w, label, value, h=56, icon=None, lock=False, mono=False, value_fill=T1, hint=None):
    """Поле Taiga с подписью внутри."""
    s.rect(x + 0.5, y + 0.5, w - 1, h - 1, WH, rx=12, stroke="#D4D6DF")
    right = 16 + (24 if (icon or lock) else 0)
    if h >= 52:
        T(s, x + 16, y + 9, truncate(label, w - 16 - right, 12), 12, 16, T2)
        T(s, x + 16, y + 26, truncate(value, w - 16 - right, 16), 16, 20, value_fill, mono=mono)
    else:
        T(s, x + 16, y + (h - 20) / 2, truncate(value, w - 16 - right, 14), 14, 20, value_fill, mono=mono)
    if icon:
        s.icon(icon, x + w - 16 - 16, y + (h - 16) / 2, T2, s=16)
    if lock:
        s.icon("lock", x + w - 16 - 16, y + (h - 16) / 2, T3, s=16)
    if hint:
        T(s, x + 4, y + h + 6, hint, 12, 16, T2)


def tabs(s, x, y, labels, active, w=None, fs=16):
    h = 48
    if w:
        s.line(x, y + h - 0.5, x + w, y + h - 0.5, stroke=LN)
    cx = x
    for i, lab in enumerate(labels):
        on = i == active
        tw = measure(lab, fs, 700 if on else 400)
        T(s, cx, y, lab, fs, h, T1 if on else T2, 700 if on else 400)
        if on:
            s.rect(cx, y + h - 3, tw, 3, Y, rx=1.5)
        cx += tw + 32
    return y + h


def island_title(s, x, top, title, sub=None, w=MW - 48, size=20):
    T(s, x, top, title, size, 28 if size == 20 else 24, T1, 700)
    y = top + (28 if size == 20 else 24)
    if sub:
        y = P(s, x, y + 4, sub, w, 14, 20, T2)
    return y


# --- оболочка --------------------------------------------------------------------------
def new(h=900):
    return Svg(W, h, BG)


def finish(s, h, name):
    s.h = h
    s.body[0] = f'<rect x="0" y="0" width="{W}" height="{h}" fill="{BG}"/>'
    path = os.path.join(OUT, name + ".svg")
    s.save(path)
    return path


def header(s, tab=0):
    s.rect(0, 0, W, HEAD, WH)
    s.line(0, HEAD - 0.5, W, HEAD - 0.5, stroke=LN)
    s.rect(X0, 16, 32, 32, Y, rx=8)
    s.icon("check", X0 + 7, 23, T1, s=18, sw=2.4)
    T(s, X0 + 44, 0, D.PRODUCT, 16, HEAD, T1, 700)
    x = X0 + 44 + measure(D.PRODUCT, 16, 700) + 48
    for i, lab in enumerate(["Новое исследование", "Мои исследования"]):
        on = i == tab
        tw = measure(lab, 16, 700 if on else 400)
        T(s, x, 0, lab, 16, HEAD, T1 if on else T2, 700 if on else 400)
        if on:
            s.rect(x, HEAD - 3, tw, 3, Y, rx=1.5)
        x += tw + 32
    # пользователь
    ax = X0 + CW - 16
    s.circle(ax, 32, 16, fill="#E6E8F2")
    T(s, ax, 16, "ДМ", 12, 32, T1, 700, anchor="middle")
    T(s, ax - 28, 0, D.USER, 14, HEAD, T1, anchor="end")
    hx = ax - 28 - measure(D.USER, 14) - 32
    s.icon("info", hx - 16, 24, T2, s=16)
    T(s, hx - 24, 0, "Справочник", 14, HEAD, T2, anchor="end")


STEPS = ["Данные", "Стратегия", "Издержки и риски", "Проверка", "Результат"]
STEP_SUB = ["ds-0007", "SMA 20/50, версия 4", "6 видов издержек", "без ошибок", "run-0142"]


def stepper(s, cur):
    y = HEAD
    s.rect(0, y, W, STEP_H, WH)
    s.line(0, y + STEP_H - 0.5, W, y + STEP_H - 0.5, stroke=LN)
    cy = y + STEP_H / 2
    sw = CW / 5
    ends = []
    for i, name in enumerate(STEPS):
        n = i + 1
        x = X0 + i * sw
        done, now = n < cur, n == cur
        if done:
            s.circle(x + 16, cy, 16, fill=POS_BG)
            s.icon("check", x + 8, cy - 8, POS, s=16, sw=2.2)
        elif now:
            s.circle(x + 16, cy, 16, fill=Y)
            T(s, x + 16, cy - 10, str(n), 14, 20, T1, 700, anchor="middle")
        else:
            s.circle(x + 16, cy, 15.25, fill=WH, stroke=LN, sw=1.5)
            T(s, x + 16, cy - 10, str(n), 14, 20, T3, 700, anchor="middle")
        sub = STEP_SUB[i] if n <= cur else None
        if cur == 5 and n == 5:
            sub = STEP_SUB[4]
        lc = T1 if (done or now) else T2
        if sub:
            T(s, x + 44, cy - 20, name, 14, 20, lc, 700)
            T(s, x + 44, cy, sub, 12, 16, T2)
            tw = max(measure(name, 14, 700), measure(sub, 12))
        else:
            T(s, x + 44, cy - 10, name, 14, 20, lc, 700 if now else 400)
            tw = measure(name, 14, 700)
        ends.append(x + 44 + tw)
    for i in range(4):
        x1 = ends[i] + 16
        x2 = X0 + (i + 1) * sw - 16
        if x2 > x1:
            s.line(x1, cy, x2, cy, stroke=POS if i + 1 < cur else LN, sw=2, cap="round", opacity=0.5 if i + 1 < cur else None)


def footer(s, h, primary, note=None, back=True, primary_icon=None, secondary=None):
    y = h - FOOT
    s.rect(0, y, W, FOOT, WH)
    s.line(0, y + 0.5, W, y + 0.5, stroke=LN)
    x = X0
    if back:
        bw = button(s, x, y + 14, "Назад", "secondary", left_chev=True)
        x += bw + 24
    if note:
        T(s, x, y, note, 14, FOOT, T2)
    bw = button(s, X0 + CW, y + 14, primary, "primary", icon=primary_icon, anchor="end")
    if secondary:
        button(s, X0 + CW - bw - 12, y + 14, secondary[0], "secondary", icon=secondary[1], anchor="end")


def page_title(s, title, sub=None, top=172, sub_w=MW):
    T(s, X0, top, title, 32, 40, T1, 700)
    y = top + 40
    if sub:
        y = P(s, X0, y + 8, sub, sub_w, 16, 24, T2)
    return y


def why(s, x, y, w, items):
    """Панель «Почему это важно». items: ("p", text) | ("b", text) | ("li", text) | ("gap", px) | ("fn", h, fn)."""
    idx = len(s.body)
    pad = 24
    iw = w - pad * 2
    s.icon("info", x + pad, y + pad + 4, T1, s=20, sw=1.8)
    T(s, x + pad + 30, y + pad, "Почему это важно", 20, 28, T1, 700)
    cy = y + pad + 28 + 12
    for it in items:
        k = it[0]
        if k == "p":
            cy = P(s, x + pad, cy, it[1], iw, 16, 24, T1) + 12
        elif k == "b":
            cy = P(s, x + pad, cy, it[1], iw, 16, 24, T1, 700) + 8
        elif k == "s":
            cy = P(s, x + pad, cy, it[1], iw, 14, 20, T2) + 12
        elif k == "li":
            s.circle(x + pad + 4, cy + 12, 2.5, fill=T1)
            cy = P(s, x + pad + 16, cy, it[1], iw - 16, 16, 24, T1) + 8
        elif k == "gap":
            cy += it[1]
        elif k == "fn":
            r = it[2](s, x + pad, cy, iw)
            cy += (r if isinstance(r, (int, float)) else it[1]) + 12
    h = cy - y + pad - 12
    behind(s, idx, lambda t: t.rect(x, y, w, h, YS, rx=12))
    return y + h


def disclaimer(s, x, top, w=MW):
    s.icon("info", x, top + 2, T3, s=14)
    return P(s, x + 22, top, D.DISCLAIMER, w - 22, 12, 16, T2)


RESULT_TITLE = "Стратегия заработала +31,6 % после всех издержек"


def result_head(s, tab):
    top = 172
    T(s, X0, top, RESULT_TITLE, 32, 40, T1, 700)
    status_badge(s, X0 + measure(RESULT_TITLE, 32, 700) + 16, top + 8, "valid")
    y = P(s, X0, top + 48, "Честный прогон run-0142 на снапшоте ds-0007 за 03.01.2020 — 30.12.2025. "
          "Для сравнения рядом наивный прогон run-0141 — без издержек и задержки.", 900, 16, 24, T2)
    y = tabs(s, X0, y + 16, ["Отчёт", "Сравнение", "Walk-forward"], tab, w=CW)
    return y + 24


# --- графики ---------------------------------------------------------------------------
DD0, DD1 = D.DAYS[0], D.DAYS[-1]


def dx(d, x, w, d0=DD0, d1=DD1):
    return x + w * (d - d0).days / (d1 - d0).days


def ts_path(vals, x, y, w, h, vmin, vmax, step=3):
    n = len(vals)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    pts = [(dx(D.DAYS[i], x, w), y + h - h * (vals[i] - vmin) / (vmax - vmin)) for i in idx]
    return "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts), pts


def year_axis(s, x, y, w):
    for yr in range(2020, 2026):
        d = date(yr, 1, 3) if yr == 2020 else date(yr, 1, 1)
        xx = dx(d, x, w)
        s.line(xx, y, xx, y + 4, stroke=T3)
        T(s, xx + 4, y, str(yr), 12, 16, T2)


def stress_marks(s, x, y, w, h, labels=True):
    x1, x2 = dx(date(2020, 2, 24), x, w), dx(date(2020, 3, 31), x, w)
    s.rect(x1, y, x2 - x1, h, NEG, fill_opacity=0.07)
    g1, g2 = dx(date(2022, 2, 28), x, w), dx(date(2022, 3, 23), x, w)
    hatch(s, g1, y, g2 - g1, h, T3, step=5, sw=1, opacity=0.7)
    xe = dx(date(2022, 2, 24), x, w)
    s.line(xe, y, xe, y + h, stroke=NEG, sw=1.2, dash="3 3")
    if labels:
        T(s, x2 + 6, y + 2, "Март 2020", 12, 16, T2)
        T(s, g2 + 6, y + 2, "24.02.2022 и пауза торгов", 12, 16, T2)


# --- DSL ---------------------------------------------------------------------------------
KW = {"strategy", "universe", "capital", "let", "when", "buy", "sell", "all", "equity", "RUB"}
FN = {"sma", "drawdown", "crosses_above", "crosses_below"}
TOK = re.compile(r'(//.*$)|("[^"]*")|(\d[\d_]*%?)|([A-Za-z_]+)|(\s+)|(.)')


def code_line(s, x, top, src, lh=24, size=15):
    cx = x
    for m in TOK.finditer(src):
        tok = m.group(0)
        if m.group(1):
            col, wt = T3, 400
        elif m.group(2):
            col, wt = POS, 400
        elif m.group(3):
            col, wt = "#B4530A", 400
        elif m.group(4):
            if tok in KW:
                col, wt = INFO, 700
            elif tok in FN:
                col, wt = "#8C3BB8", 400
            else:
                col, wt = T1, 400
        elif m.group(5):
            cx += measure(tok, size)
            continue
        else:
            col, wt = T2, 400
        s.text(cx, bl(top, lh, size), tok, size=size, fill=col, weight=wt)
        cx += measure(tok, size, wt)


DSL_HUMAN = [
    "Название стратегии",
    "Торгуем шестью акциями Мосбиржи",
    "Стартовый капитал — 1 млн рублей",
    None,
    "Быстрая средняя: средняя цена закрытия за 20 дней",
    "Медленная средняя: то же за 50 дней",
    None,
    "Быстрая средняя пересекла медленную снизу вверх — покупаем на 20 % капитала",
    "Пересекла сверху вниз — продаём всю позицию",
    "Позиция упала больше чем на 12 % — продаём всё, чтобы ограничить убыток",
]


# =========================================================================================
# C1. Данные
# =========================================================================================
def screen1():
    s = new(1200)
    header(s, 0)
    stepper(s, 1)
    y0 = page_title(s, "Выберите данные для исследования",
                    "Снапшот — это замороженная копия котировок с биржи. Он не меняется, поэтому ваш прогон "
                    "можно повторить через год и получить тот же результат до копейки.", sub_w=860) + 32

    # --- список снапшотов
    x, y = MX, y0
    idx = len(s.body)
    T(s, x + 24, y + 20, "Снапшоты", 20, 28, T1, 700)
    T(s, x + 24 + measure("Снапшоты", 20, 700) + 8, y + 20, "5", 20, 28, T3, 700)
    button(s, x + MW - 24, y + 18, "Загрузить новый снапшот", "outline", "s", icon="download", anchor="end")
    T(s, x + 24, y + 48, "Новый снапшот — свежие дневные котировки из MOEX ISS, сохраним их с хэшем", 14, 20, T2)
    hy = y + 84
    s.line(x, hy + 0.5, x + MW, hy + 0.5, stroke=LN)
    cols = [(x + 52, "Снапшот"), (x + 164, "Тикеры и период"), (x + 484, "Получен и хэш"), (x + 604, "Статус")]
    for cx, lab in cols:
        T(s, cx, hy + 8, lab, 12, 16, T2)
    ry = hy + 32
    s.line(x, ry - 0.5, x + MW, ry - 0.5, stroke=LN)
    for i, ds in enumerate(D.DATASETS):
        rh = 72
        sel = i == 0
        off = ds["status"] == "после MVP"
        if sel:
            s.rect(x + 1, ry, MW - 2, rh, YL)
            s.rect(x + 1, ry, 3, rh, Y)
        radio(s, x + 28, ry + rh / 2, sel, disabled=off)
        c1 = T3 if off else T1
        c2 = T3 if off else T2
        T(s, x + 52, ry + 14, ds["id"], 16, 24, c1, 700)
        T(s, x + 52, ry + 38, truncate(ds['source'], 104, 14), 14, 20, c2)
        T(s, x + 164, ry + 14, truncate(ds["tickers"], 308, 14), 14, 24, c1)
        T(s, x + 164, ry + 38, truncate(f"{ds['interval']}, " + ds["period"] + (f", {ds['rows']} строк" if ds["rows"] != "—" else ""), 308, 14), 14, 20, c2)
        if off:
            T(s, x + 484, ry + 14, "ещё не создан", 14, 24, c2)
            T(s, x + 484, ry + 38, "—", 14, 20, c2)
        else:
            T(s, x + 484, ry + 14, ds["fetched"], 14, 24, c1)
            T(s, x + 484, ry + 38, f"sha {ds['sha']}", 14, 20, c2)
        st = ds["status"]
        kind = {"актуальный": "pos", "устаревшая схема": "warn", "после MVP": "neutral"}.get(st, "neutral")
        icon = "lock" if off else None
        badge(s, x + 604, ry + 14, st[0].upper() + st[1:], kind, icon=icon)
        used = "не использовался" if not ds["used_in"] else f"схема {ds['schema']}, в {ds['used_in']} прогонах"
        T(s, x + 604, ry + 40, used, 12, 16, c2)
        ry += rh
        if i < len(D.DATASETS) - 1:
            s.line(x + 24, ry - 0.5, x + MW - 24, ry - 0.5, stroke=LN)
    P(s, x + 24, ry + 12, "Генератор синтетических рядов появится после MVP. Пока используйте снапшоты MOEX ISS и ЦБ РФ.",
      MW - 48, 14, 20, T2)
    ry += 12 + 20 + 16
    behind(s, idx, lambda t: island(t, x, y, MW, ry - y))
    y = ry + GAP

    # --- что внутри ds-0007
    idx = len(s.body)
    cy = island_title(s, x + 24, y + 20, "Что внутри ds-0007",
                      "Стратегия видит каждое значение только с того момента, когда оно стало известно на бирже.")
    cy += 16
    tx, tw = x + 24, 420
    T(s, tx, cy, "Поле", 12, 16, T2)
    T(s, tx + 120, cy, "Когда становится известно", 12, 16, T2)
    cy += 24
    for fname, when in D.DATASET_FIELDS:
        s.line(tx, cy - 0.5, tx + tw, cy - 0.5, stroke=LN)
        bad = "запрещено" in when
        T(s, tx, cy, fname, 14, 44, NEG if bad else T1, 700, mono=False)
        if bad:
            T(s, tx + 120, cy, "меняется задним числом", 14, 44, T1)
            badge(s, tx + tw, cy + 10, "Запрещено", "neg", anchor="end", icon="x")
        else:
            T(s, tx + 120, cy, when, 14, 44, T1)
        cy += 44
    # временная шкала дня справа
    gx, gw = x + 484, MW - 484 - 24
    gy = cy - 5 * 44 - 24
    s.rect(gx, gy, gw, 5 * 44 + 24, BG, rx=10)
    T(s, gx + 16, gy + 14, "Торговый день t", 14, 20, T1, 700)
    lx1, lx2 = gx + 28, gx + gw - 28
    ly = gy + 92
    s.line(lx1, ly, lx2, ly, stroke="#C5C7D3", sw=2, cap="round")
    s.circle(lx1, ly, 6, fill=POS)
    s.circle(lx2, ly, 6, fill=T1)
    T(s, lx1, ly - 36, "10:00", 14, 20, T1, 700, anchor="middle")
    T(s, lx1, ly + 12, "open", 14, 20, T2, anchor="middle")
    T(s, lx2, ly - 36, "18:50", 14, 20, T1, 700, anchor="middle")
    T(s, lx2, ly + 12, "close", 14, 20, T2, anchor="middle")
    P(s, gx + 16, ly + 48, "Сигнал по закрытию дня t исполнится по open дня t+1 — раньше купить нельзя.", gw - 32, 14, 20, T1)
    cy += 16
    behind(s, idx, lambda t: island(t, x, y, MW, cy - y))
    main_end = cy

    # --- правая колонка
    ry = why(s, RX, y0, RW, [
        ("p", "Если данные можно тихо поменять, никто не проверит ваш результат — даже вы сами через месяц."),
        ("p", "Поэтому каждый снапшот закреплён хэшем. Совпал sha — значит, данные те же до последней цифры."),
        ("b", "Момент доступности"),
        ("p", "Цена закрытия появляется только в 18:50. Стратегия, которая покупает по ней в тот же день, "
              "подглядывает в будущее."),
    ])
    ry += GAP
    idx = len(s.body)
    cy = island_title(s, RX + 24, ry + 20, "Торговый календарь",
                      "В эти дни биржа не работала. Прогон пропускает их, а не считает нулевыми.", w=RW - 48)
    cy += 16
    T(s, RX + 24, cy, "Февраль — март 2022", 14, 20, T1, 700)
    cy += 28
    cw_ = (RW - 48) / 7
    for j, dn in enumerate(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]):
        T(s, RX + 24 + j * cw_ + cw_ / 2, cy, dn, 12, 16, T2, anchor="middle")
    cy += 24
    days = [(21, 2), (22, 2), (23, 2), (24, 2), (25, 2), (26, 2), (27, 2)]
    weeks = []
    d = date(2022, 2, 21)
    from datetime import timedelta
    for wk in range(5):
        row = []
        for j in range(7):
            row.append(d)
            d += timedelta(days=1)
        weeks.append(row)
    g0, g1 = date(2022, 2, 28), date(2022, 3, 23)
    for row in weeks:
        for j, dd in enumerate(row):
            cx = RX + 24 + j * cw_
            gap = g0 <= dd <= g1 and j < 5
            wkend = j >= 5
            if gap:
                s.rect(cx + 2, cy + 2, cw_ - 4, 32, "#EEEFF3", rx=8)
                hatch(s, cx + 2, cy + 2, cw_ - 4, 32, "#D5D7E0", step=5)
            if dd == date(2022, 2, 24):
                s.rect(cx + 2.75, cy + 2.75, cw_ - 5.5, 30.5, WH, rx=8, stroke=NEG, sw=1.5)
            col = T3 if (wkend or gap) else T1
            T(s, cx + cw_ / 2, cy + 2, str(dd.day), 14, 32, NEG if dd == date(2022, 2, 24) else col,
              700 if dd == date(2022, 2, 24) else 400, anchor="middle")
        cy += 36
    cy += 8
    s.rect(RX + 24, cy + 2, 16, 16, "#EEEFF3", rx=4)
    hatch(s, RX + 24, cy + 2, 16, 16, "#D5D7E0", step=5)
    cy = P(s, RX + 48, cy, f"{D.CALENDAR_GAP[0]} — {D.CALENDAR_GAP[1]}: {D.CALENDAR_GAP[2]}", RW - 72, 14, 20, T1) + 8
    s.rect(RX + 24.75, cy + 2.75, 14.5, 14.5, WH, rx=4, stroke=NEG, sw=1.5)
    cy = P(s, RX + 48, cy, "24.02.2022 — обвал рынка, стресс-событие в отчёте", RW - 72, 14, 20, T1) + 20
    behind(s, idx, lambda t: island(t, RX, ry, RW, cy - ry))

    h = max(main_end, cy) + 32 + FOOT
    footer(s, h, "Далее: Стратегия", note="Шаг 1 из 5. Выбран снапшот ds-0007", back=False)
    return finish(s, h, "C1")


# =========================================================================================
# C2. Стратегия
# =========================================================================================
def code_width(src, size=15):
    return sum(measure(m.group(0), size, 700 if m.group(0) in KW else 400) for m in TOK.finditer(src))


def screen2():
    s = new(1300)
    header(s, 0)
    stepper(s, 2)
    y0 = page_title(s, "Опишите стратегию",
                    "Пишите правила на языке стратегий — справа от каждой строки появится её перевод на обычный язык. "
                    "Перед запуском мы проверим, не подглядывает ли стратегия в будущее.", sub_w=900) + 32
    x, y = MX, y0

    # --- выбор стратегии
    T(s, x, y, "Ваши стратегии", 16, 24, T1, 700)
    button(s, x + MW, y - 4, "Новая стратегия", "flat", "s", icon="plus", anchor="end")
    y += 36
    cw_ = (MW - 3 * 12) / 4
    ch_ = 60
    for i, st in enumerate(D.STRATEGIES):
        cx = x + i * (cw_ + 12)
        sel = i == 0
        if sel:
            s.rect(cx + 1, y + 1, cw_ - 2, ch_ - 2, WH, rx=12, stroke=T1, sw=2)
        else:
            island(s, cx, y, cw_, ch_)
        radio(s, cx + 26, y + ch_ / 2, sel)
        T(s, cx + 46, y + 10, truncate(st["short"], cw_ - 58, 15, 700), 15, 20, T1, 700)
        T(s, cx + 46, y + 30, truncate(f"{st['runs']} прогонов, {st['updated'][:5]}", cw_ - 58, 13), 13, 20, T2)
    y += ch_ + GAP

    # --- редактор
    ex, ew = x, MW
    ey = y
    idx = len(s.body)
    s.icon("code", ex + 24, ey + 22, T1, s=20)
    T(s, ex + 54, ey + 18, "Пересечение SMA 20/50", 20, 28, T1, 700)
    T(s, ex + 54 + measure("Пересечение SMA 20/50", 20, 700) + 12, ey + 22, "версия 4, сохранено в 14:20", 14, 20, T2)
    badge(s, ex + ew - 24, ey + 20, "Без ошибок", "pos", anchor="end", icon="check")
    hy = ey + 64
    code_w = max(code_width(src) for src in D.DSL_MAIN)
    split = ex + 48 + round(code_w) + 20
    s.line(ex, hy + 0.5, ex + ew, hy + 0.5, stroke=LN)
    T(s, ex + 48, hy + 8, "Код", 12, 16, T2)
    T(s, split + 20, hy + 8, "Что это значит", 12, 16, T2)
    ry = hy + 32
    s.line(ex, ry - 0.5, ex + ew, ry - 0.5, stroke=LN)
    trans_w = ex + ew - split - 44
    rows = []
    cy = ry + 8
    for i, src in enumerate(D.DSL_MAIN):
        hum = DSL_HUMAN[i]
        if not src:
            rh = 12
        else:
            nl = nlines(hum, trans_w, 16) if hum else 1
            rh = max(36, nl * 24 + 12)
        rows.append((i, src, hum, cy, rh))
        cy += rh
    code_bottom = cy + 8
    s.rect(split, ry, ex + ew - split - 1, code_bottom - ry - 1, YL)
    s.line(split + 0.5, ry, split + 0.5, code_bottom, stroke="#F1E6B8")
    for i, src, hum, top, rh in rows:
        if i == 7:
            s.rect(ex + 1, top, split - ex - 1, rh, "#F3F5FB")
            s.rect(ex + 1, top, 3, rh, INFO)
    for i, src, hum, top, rh in rows:
        if not src:
            continue
        T(s, ex + 32, top + 6, str(i + 1), 13, 24, T3, anchor="end")
        code_line(s, ex + 48, top + 6, src)
        if hum:
            P(s, split + 20, top + 6, hum, trans_w, 16, 24, T1)
        if i == 7:
            cxx = ex + 48 + code_width(src) + 2
            s.line(cxx, top + 9, cxx, top + 27, stroke=T1, sw=1.5)
    by = code_bottom
    s.line(ex, by + 0.5, ex + ew, by + 0.5, stroke=LN)
    T(s, ex + 24, by + 12, "10 строк. Перевод обновляется, пока вы печатаете.", 14, 20, T2)
    button(s, ex + ew - 24, by + 6, "Проверить ещё раз", "secondary", "s", icon="repeat", anchor="end")
    eb = by + 44
    behind(s, idx, lambda t: island(t, ex, ey, ew, eb - ey))
    y = eb + GAP

    # --- проверка чтения будущего
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, py + 20, "Проверка чтения будущего",
                      "Ищем в коде данные, которых ещё нет в момент решения. У проверки три уровня — "
                      "так они выглядят на примерах из вашей истории.")
    cy += 12
    meta = {
        "ok": ("Всё в порядке", "прогон валиден", POS, POS_BG, "check", "Сейчас в коде"),
        "warning": ("Подозрительно", "прогон получит пометку", WARN_TX, YS, "warn", "Было в прошлой версии, исправлено"),
        "error": ("Ошибка", "прогон невалиден", NEG, NEG_BG, "x", "Из прогона run-0139"),
    }
    for k, chk in enumerate(D.LOOKAHEAD_CHECKS):
        lab, cons, col, bgc, ic, prov = meta[chk["level"]]
        s.line(x + 24, cy + 0.5, x + MW - 24, cy + 0.5, stroke=LN)
        top = cy + 16
        s.circle(x + 24 + 16, top + 16, 16, fill=bgc)
        s.icon(ic, x + 24 + 8, top + 8, col, s=16, sw=2)
        T(s, x + 72, top + 4, lab, 16, 24, col if chk["level"] != "warning" else T1, 700)
        lw_ = measure(lab, 16, 700)
        T(s, x + 72 + lw_ + 8, top + 4, cons, 14, 24, T2)
        code = f"{chk['line']}   {chk['code']}"
        cwid = code_width(code) + 24
        s.rect(x + MW - 24 - cwid, top + 2, cwid, 28, bgc, rx=6)
        code_line(s, x + MW - 24 - cwid + 12, top + 4, code)
        yy = P(s, x + 72, top + 38, chk["msg"], MW - 96, 14, 20, T1)
        T(s, x + 72, yy + 2, prov, 12, 16, T2)
        cy = yy + 2 + 16 + 14
    cy += 6
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    main_end = cy

    # --- правая колонка
    def timeline(t, xx, yy, ww):
        t.rect(xx, yy, ww, 120, WH, rx=10)
        l1, l2 = xx + 72, xx + ww - 72
        ly = yy + 60
        t.line(l1, ly, l2, ly, stroke="#C5C7D3", sw=2)
        mid = (l1 + l2) / 2
        T(t, l1, yy + 16, "День t, 18:50", 12, 16, T2, anchor="middle")
        T(t, l2, yy + 16, "День t+1, 10:00", 12, 16, T2, anchor="middle")
        t.circle(l1, ly, 7, fill=T1)
        t.circle(l2, ly, 7, fill=POS)
        T(t, l1, ly + 14, "close известен", 14, 20, T1, 700, anchor="middle")
        T(t, l1, ly + 34, "решение", 12, 16, T2, anchor="middle")
        T(t, l2, ly + 14, "open", 14, 20, T1, 700, anchor="middle")
        T(t, l2, ly + 34, "сделка", 12, 16, T2, anchor="middle")
        T(t, mid, ly - 22, "ночь", 12, 16, T2, anchor="middle")

    ry = why(s, RX, y0, RW, [
        ("b", "Стратегия не должна знать будущее."),
        ("p", "Вечером вы видите цену закрытия и решаете купить. Купить получится только утром следующего дня."),
        ("fn", 120, timeline),
        ("p", "Если код берёт данные, которых в момент решения ещё нет, результат выйдет слишком хорошим "
              "и в жизни не повторится."),
    ])
    ry += GAP
    idx = len(s.body)
    cy = island_title(s, RX + 24, ry + 20, "Шпаргалка по языку", w=RW - 48)
    cy += 12
    cheat = [
        ("sma(close, 20)", "средняя цена закрытия за 20 дней"),
        ("crosses_above", "пересекла снизу вверх"),
        ("close[1]", "вчерашнее закрытие, можно"),
        ("close[+1]", "завтрашнее закрытие, нельзя"),
        ("adj_close", "пересчитывается задним числом, замените на close"),
    ]
    for code, hum in cheat:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        bad = "нельзя" in hum or "замените" in hum
        T(s, RX + 24, cy + 10, code, 15, 20, NEG if bad else T1, 700)
        yy = P(s, RX + 24, cy + 32, hum, RW - 48, 14, 20, T2)
        cy = yy + 10
    cy += 10
    behind(s, idx, lambda t: island(t, RX, ry, RW, cy - ry))

    h = max(main_end, cy) + 32 + FOOT
    footer(s, h, "Далее: Издержки и риски", note="Шаг 2 из 5. Черновик сохранён в 14:20")
    return finish(s, h, "C2")


# =========================================================================================
# C3. Издержки и риски
# =========================================================================================
def screen3():
    s = new(1500)
    header(s, 0)
    stepper(s, 3)
    C = D.RUN_CONFIG
    y0 = page_title(s, "Настройте издержки и риски",
                    "В жизни каждая сделка стоит денег и исполняется не мгновенно. Чем честнее настройки, "
                    "тем ближе результат к тому, что было бы на самом деле.", sub_w=900) + 32
    x, y = MX, y0

    # --- данные и период
    idx = len(s.body)
    cy = island_title(s, x + 24, y + 20, "Данные и период")
    cy += 16
    fw = (MW - 48 - 2 * 16) / 3
    field(s, x + 24, cy, fw, "Снапшот", C["dataset"] + ", MOEX ISS", icon="chevron-down")
    field(s, x + 24 + fw + 16, cy, fw, "Период, 1 545 торговых дней", C["period"])
    field(s, x + 24 + 2 * (fw + 16), cy, fw, "Стартовый капитал", C["capital"])
    cy += 56 + 24
    behind(s, idx, lambda t: island(t, x, y, MW, cy - y))
    y = cy + GAP

    # --- издержки: сетка 2 × 3
    idx = len(s.body)
    cy = island_title(s, x + 24, y + 20, "Издержки",
                      "Честный прогон учитывает все шесть. Наивный прогон считает сделки бесплатными и мгновенными.")
    cy += 20
    costs = [
        ("Комиссия брокера", "Брокер берёт процент с каждой сделки", C["commission"], None, False),
        ("Биржевой сбор", "Плата бирже за проведение сделки", C["exchange_fee"], None, False),
        ("Спред", "Покупаете дороже середины, продаёте дешевле", C["spread"], None, False),
        ("Проскальзывание", "Крупная заявка сдвигает цену против вас", C["slippage"], None, False),
        ("Лимит ликвидности", "Нельзя купить больше, чем продают", "не больше 5 % объёма бара",
         "Остаток — частичное исполнение или отказ", False),
        ("Задержка исполнения", "Решение вечером, сделка утром", "по open следующего бара", "В честном прогоне всегда включена", True),
    ]
    gw_ = (MW - 48 - 24) / 2
    cell_h = 128
    for k, (name, expl, val, hint, lock) in enumerate(costs):
        cx = x + 24 + (k % 2) * (gw_ + 24)
        top = cy + (k // 2) * cell_h
        if k >= 2:
            s.line(cx, top - 12 + 0.5, cx + gw_, top - 12 + 0.5, stroke=LN)
        T(s, cx, top, name, 16, 24, T1, 700)
        T(s, cx, top + 24, truncate(expl, gw_, 14), 14, 20, T2)
        field(s, cx, top + 52, gw_, "", val, h=44, lock=lock, value_fill=T2 if lock else T1)
        if hint:
            T(s, cx + 4, top + 100, hint, 12, 16, T2)
    cy += 3 * cell_h - 4
    behind(s, idx, lambda t: island(t, x, y, MW, cy - y))
    y = cy + GAP

    # --- стресс-сценарий
    idx = len(s.body)
    T(s, x + 24, y + 20, "Стресс-сценарий", 20, 28, T1, 700)
    toggle(s, x + MW - 24 - 40, y + 22, True)
    T(s, x + MW - 24 - 40 - 12, y + 22, "Добавить стресс-прогон", 14, 24, T1, anchor="end")
    cy = P(s, x + 24, y + 52, "Повторим прогон в условиях кризиса: резкий гэп, высокая волатильность, тонкий рынок.", MW - 48, 14, 20, T2)
    cy += 16
    cw_ = (MW - 48 - 2 * 12) / 3
    card_h = 200
    for i, p in enumerate(D.STRESS_PRESETS):
        cx = x + 24 + i * (cw_ + 12)
        sel = i == 0
        custom = p["name"] == "Свой сценарий"
        if sel:
            s.rect(cx + 1, cy + 1, cw_ - 2, card_h - 2, WH, rx=12, stroke=T1, sw=2)
        else:
            s.rect(cx + 0.5, cy + 0.5, cw_ - 1, card_h - 1, WH, rx=12, stroke=LN)
        radio(s, cx + 26, cy + 26, sel)
        T(s, cx + 44, cy + 14, p["name"], 16, 24, T1, 700)
        P(s, cx + 16, cy + 46, p["desc"], cw_ - 32, 13, 18, T2, max_lines=2)
        pr = [("Гэп", p["gap"]), ("Волатильность", p["vol"]), ("Объём", p["volume"]), ("Проскальзывание", p["slip"])]
        py = cy + 94
        for j, (pl, pv) in enumerate(pr):
            ry = py + j * 24
            T(s, cx + 16, ry, pl, 13, 24, T2)
            if custom:
                s.rect(cx + cw_ - 16 - 60 + 0.5, ry + 2.5, 60, 19, WH, rx=5, stroke="#D4D6DF")
                T(s, cx + cw_ - 16 - 8, ry, pv, 13, 24, T2, anchor="end")
            else:
                T(s, cx + cw_ - 16, ry, pv, 13, 24, T1, 700, anchor="end")
    cy += card_h + 20
    behind(s, idx, lambda t: island(t, x, y, MW, cy - y))
    y = cy + GAP

    # --- как проводить прогон
    idx = len(s.body)
    cy = island_title(s, x + 24, y + 20, "Как проводить прогон")
    cy += 12
    half = (MW - 48 - 24) / 2
    s.line(x + 24, cy + 0.5, x + MW - 24, cy + 0.5, stroke=LN)
    checkbox(s, x + 24, cy + 18, True)
    T(s, x + 56, cy + 14, "Наивный и честный вместе", 16, 24, T1, 700)
    P(s, x + 56, cy + 38, "Покажем оба результата и разложим разницу по видам издержек", half - 32, 14, 20, T2)
    wx = x + 24 + half + 24
    toggle(s, wx, cy + 16, True)
    T(s, wx + 52, cy + 14, "Walk-forward", 16, 24, T1, 700)
    P(s, wx + 52, cy + 38, C["walk_forward"], half - 52, 14, 20, T2)
    cy += 100
    s.line(x + 24, cy + 0.5, x + MW - 24, cy + 0.5, stroke=LN)
    cy += 16
    fw2 = (MW - 48 - 16) / 2
    field(s, x + 24, cy, fw2, "Правило остановки", C["stop_rule"], icon="chevron-down")
    field(s, x + 24 + fw2 + 16, cy, fw2, "Seed случайности", C["seed"], icon="repeat")
    cy += 56 + 8
    T(s, x + 24 + fw2 + 16 + 4, cy - 2, "Тот же seed — тот же результат при повторе", 12, 16, T2)
    cy += 14 + 20
    behind(s, idx, lambda t: island(t, x, y, MW, cy - y))
    main_end = cy

    # --- правая колонка
    def example(t, xx, yy, ww):
        t.rect(xx, yy, ww, 236, WH, rx=10)
        T(t, xx + 16, yy + 14, "Покупка SBER на 200 000 ₽", 14, 20, T1, 700)
        rows = [("Комиссия брокера", "100 ₽"), ("Биржевой сбор", "20 ₽"), ("Спред", "160 ₽"),
                ("Проскальзывание", "от 200 ₽")]
        ry_ = yy + 46
        for a, b in rows:
            T(t, xx + 16, ry_, a, 14, 32, T2)
            T(t, xx + ww - 16, ry_, b, 14, 32, T1, anchor="end")
            ry_ += 32
        t.line(xx + 16, ry_ + 6, xx + ww - 16, ry_ + 6, stroke=LN)
        T(t, xx + 16, ry_ + 14, "Итого за одну сделку", 14, 32, T1, 700)
        T(t, xx + ww - 16, ry_ + 14, "от 480 ₽", 16, 32, T1, 700, anchor="end")

    ry = why(s, RX, y0, RW, [
        ("p", "Наивный прогон считает сделки бесплатными и мгновенными, поэтому почти всегда выглядит лучше реальности."),
        ("fn", 236, example),
        ("p", "Стратегия, которая торгует часто, платит эти деньги сотни раз. Поэтому важен не только процент, но и оборот."),
    ])
    ry += GAP
    idx = len(s.body)
    cy = island_title(s, RX + 24, ry + 20, "Перед запуском проверим", w=RW - 48)
    cy += 8
    checks = [
        ("Данные", "ds-0007, хэш совпадает"),
        ("Стратегия", "чтение будущего не найдено"),
        ("Издержки", "6 из 6 включены"),
        ("Календарь", "18 дней без торгов учтены"),
    ]
    for a, b in checks:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        s.circle(RX + 24 + 10, cy + 24, 10, fill=POS_BG)
        s.icon("check", RX + 24 + 4, cy + 18, POS, s=12, sw=2)
        T(s, RX + 56, cy + 6, a, 14, 20, T1, 700)
        T(s, RX + 56, cy + 26, b, 14, 20, T2)
        cy += 56
    cy += 8
    behind(s, idx, lambda t: island(t, RX, ry, RW, cy - ry))

    h = max(main_end, cy) + 32 + FOOT
    footer(s, h, "Запустить прогон", note="Прогон займёт около 4 секунд, затем откроется проверка", primary_icon="play")
    return finish(s, h, "C3")


# =========================================================================================
# C4. Отчёт прогона (шаг «Результат»)
# =========================================================================================
def hero(s, x, y, w):
    idx = len(s.body)
    pad = 32
    T(s, x + pad, y + 28, "Без издержек и задержки", 16, 24, T2)
    T(s, x + pad, y + 56, D.RESULT_NAIVE["total"], 56, 64, T2, 700)
    nw = measure(D.RESULT_NAIVE["total"], 56, 700)
    ax = x + pad + nw + 32
    arrow_right(s, ax, y + 92, 64, T2, sw=2.5)
    rx_ = ax + 64 + 32
    T(s, rx_, y + 28, "Честно: с издержками и задержкой", 16, 24, T1, 700)
    T(s, rx_, y + 52, D.RESULT_HONEST["total"], 72, 72, POS, 700)
    by = y + 152
    bw = w - pad * 2
    kept = 31.6 / 84.2
    s.rect(x + pad, by, bw, 16, NEG_BG, rx=8)
    hatch(s, x + pad + bw * kept, by, bw * (1 - kept), 16, "#F6B8AE", step=6, sw=1.2)
    s.rect(x + pad, by, bw * kept, 16, POS, rx=8)
    s.rect(x + pad + bw * kept - 8, by, 8, 16, POS)
    T(s, x + pad, by + 24, "Осталось вам: 31,6 п.п.", 14, 20, POS, 700)
    T(s, x + pad + bw, by + 24, "Забрали издержки и задержка: 52,6 п.п.", 14, 20, NEG, 700, anchor="end")
    yy = by + 60
    s.line(x + pad, yy, x + w - pad, yy, stroke=LN)
    yy = P(s, x + pad, yy + 16, "Из каждых 100 ₽ прибыли, которые обещал наивный прогон, до вас доходят 38 ₽.",
           bw, 16, 24, T1, 700)
    yy = P(s, x + pad, yy, "Остальное съели задержка исполнения, спред, проскальзывание, комиссии и лимит ликвидности.",
           bw, 16, 24, T2)
    h = yy + 28 - y
    behind(s, idx, lambda t: island(t, x, y, w, h))
    return y + h


METRICS = [
    [("Доходность", [
        ("Итоговый капитал", "final", "наивный 1 842 000 ₽", "Во что превратился 1 000 000 ₽"),
        ("Доходность после всех затрат", "net", "наивный +84,2 %", "Рост капитала за шесть лет — то, что осталось на самом деле"),
        ("Среднегодовая, CAGR", "cagr", "наивный +10,7 %", "Такой рост каждый год дал бы тот же итог"),
        ("До затрат на сделки", "gross", None, "Уже с задержкой, но без комиссий, сбора и спреда"),
        ("Индекс IMOEX", "benchmark", None, "Стратегия обогнала индекс на 22,2 п.п. за тот же период"),
    ]), ("Портфель", [
        ("Концентрация, HHI", "hhi", None, "0 — деньги поровну во всех бумагах, 1 — всё в одной"),
        ("Крупнейшая позиция", "top_position", None, "Самая большая доля одной акции в портфеле"),
    ])],
    [("Риск", [
        ("Макс. просадка", "max_dd", "наивный −18,9 %", "Самое глубокое падение от пика: 24.02.2022 — 05.01.2023, 214 дней"),
        ("Волатильность", "vol", None, "Насколько сильно капитал колеблется за год"),
        ("Коэффициент Sharpe", "sharpe", "наивный 1,12", "Доходность на единицу риска. Выше 1 — хорошо"),
        ("Коэффициент Sortino", "sortino", "наивный 1,71", "Как Sharpe, но штрафует только за падения"),
    ]), ("Сделки", [
        ("Сделок", "trades", "наивный 436", "Покупки и продажи за весь период"),
        ("Прибыльных сделок", "win_rate", "наивный 51,2 %", "Доля сделок, закрытых в плюс"),
        ("Оборот", "turnover", None, "Сколько раз за год капитал проходит через сделки"),
        ("Частично и отказы", None, None, "Заявки больше 5 % объёма бара: 11 исполнены частично, 6 отклонены"),
    ])],
]


def metrics_table(s, x, y, w):
    idx = len(s.body)
    R = D.RESULT_HONEST
    cy0 = island_title(s, x + 24, y + 20, "Метрики простыми словами",
                       "Рядом с каждым числом — что оно значит и каким было в наивном прогоне.")
    cy0 += 16
    colw = (w - 48 - 32) / 2
    bottoms = []
    for ci, groups in enumerate(METRICS):
        cx = x + 24 + ci * (colw + 32)
        cy = cy0
        for gi, (gname, rows) in enumerate(groups):
            if gi:
                cy += 16
            T(s, cx, cy, gname, 16, 24, T1, 700)
            cy += 32
            for name, key, sub, expl in rows:
                val = R[key] if key else "11 и 6"
                s.line(cx, cy + 0.5, cx + colw, cy + 0.5, stroke=LN)
                vcol = POS if key in ("net", "cagr", "gross") else (NEG if key == "max_dd" else T1)
                T(s, cx, cy + 12, name, 14, 20, T2)
                T(s, cx + colw, cy + 10, val, 16, 24, vcol, 700, anchor="end")
                yy = P(s, cx, cy + 36, expl, colw, 14, 20, T1)
                if sub:
                    yy = T(s, cx, yy + 2, sub, 12, 16, T2)
                cy = yy + 12
        bottoms.append(cy)
    cy = max(bottoms) + 12
    behind(s, idx, lambda t: island(t, x, y, w, cy - y))
    return cy


def screen4():
    s = new(3000)
    header(s, 0)
    stepper(s, 5)
    y0 = result_head(s, 0)
    x = MX
    y = hero(s, x, y0, MW) + GAP

    # --- кривая капитала + просадка
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Как менялся капитал", "Сколько стоил бы ваш 1 000 000 ₽ в каждый день периода.")
    cy += 12
    lx = x + 24
    for lab, col, dash, sw in [("Честный прогон", T1, None, 2.5), ("Наивный прогон", T3, "5 4", 2), ("IMOEX", INFO, None, 1.5)]:
        s.line(lx, cy + 10, lx + 20, cy + 10, stroke=col, sw=sw, dash=dash)
        T(s, lx + 28, cy, lab, 14, 20, T2)
        lx += 28 + measure(lab, 14) + 24
    cy += 32
    gx, gw, gh = x + 72, MW - 72 - 72, 220
    vmin, vmax = 0.5, 1.9
    Yv = lambda v: cy + gh - gh * (v - vmin) / (vmax - vmin)
    for v in (0.6, 1.0, 1.4, 1.8):
        s.line(gx, Yv(v), gx + gw, Yv(v), stroke=LN, dash=None if v == 1.0 else "2 4")
        T(s, gx - 12, Yv(v) - 8, f"{v:.1f}".replace(".", ",") + " млн", 12, 16, T2, anchor="end")
    stress_marks(s, gx, cy, gw, gh)
    for vals, col, dash, sw in [(D.EQUITY_IMOEX, INFO, None, 1.5), (D.EQUITY_NAIVE, T3, "5 4", 2), (D.EQUITY_HONEST, T1, None, 2.5)]:
        d, pts = ts_path(vals, gx, cy, gw, gh, vmin, vmax)
        s.path(d, stroke=col, sw=sw, dash=dash)
    for vals, lab, col in [(D.EQUITY_NAIVE, "+84,2 %", T2), (D.EQUITY_HONEST, "+31,6 %", T1), (D.EQUITY_IMOEX, "+9,4 %", INFO)]:
        yy = Yv(vals[-1])
        s.circle(gx + gw, yy, 3.5, fill=col)
        T(s, gx + gw + 10, yy - 10, lab, 14, 20, col, 700)
    cy += gh + 8
    year_axis(s, gx, cy, gw)
    cy += 32
    # просадка
    T(s, x + 24, cy, "Просадка: насколько капитал ниже своего прошлого максимума", 14, 20, T1, 700)
    cy += 28
    dh = 88
    ddv = D.drawdown(D.EQUITY_HONEST)
    for v in (0, -0.1, -0.2, -0.3):
        yy = cy + dh * (-v) / 0.3
        s.line(gx, yy, gx + gw, yy, stroke=LN, dash=None if v == 0 else "2 4")
        T(s, gx - 12, yy - 8, fmt_pct(v * 100, 0) if v else "0 %", 12, 16, T2, anchor="end")
    stress_marks(s, gx, cy, gw, dh, labels=False)
    n = len(ddv)
    idxs = list(range(0, n, 3)) + [n - 1]
    pts = [(dx(D.DAYS[i], gx, gw), cy + dh * (-ddv[i]) / 0.3) for i in idxs]
    dpath = f"M{gx:.1f} {cy:.1f} L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts) + f" L{gx + gw:.1f} {cy:.1f} Z"
    s.path(dpath, fill=NEG, fill_opacity=0.16)
    s.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts), stroke=NEG, sw=1.2)
    ti = min(range(n), key=lambda k: ddv[k])
    tx_, ty_ = dx(D.DAYS[ti], gx, gw), cy + dh * (-ddv[ti]) / 0.3
    s.circle(tx_, ty_, 4, fill=NEG)
    lab = "−27,4 %, длилась 214 дней"
    s.rect(tx_ - 12 - measure(lab, 12, 700) - 8, ty_ - 12, measure(lab, 12, 700) + 16, 24, WH, rx=6, stroke=LN)
    T(s, tx_ - 12, ty_ - 8, lab, 12, 16, NEG, 700, anchor="end")
    cy += dh + 8
    year_axis(s, gx, cy, gw)
    cy += 36
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- свечи SBER
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Сделки по SBER, сентябрь — декабрь 2025",
                      "Значок — заявка стратегии. Исполняется по цене открытия следующего дня.")
    cy += 20
    data = D.candles()
    cx0, cwid, ch = x + 24, MW - 48 - 64, 200
    lo = min(c["l"] for c in data)
    hi = max(c["h"] for c in data)
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        yy = cy + 16 + ch - ch * k / 4
        s.line(cx0, yy, cx0 + cwid, yy, stroke=LN, dash="2 4")
        T(s, cx0 + cwid + 12, yy - 8, f"{v:.0f}", 12, 16, T2)
    m = s.candles(data, cx0, cy + 16, cwid, ch, POS, NEG, gap=0.35)
    mk = {"buy": (POS, "up"), "partial": (AMBER, "up"), "sell": (NEG, "down"), "rejected": (T2, "x")}
    for num, (i, kind, lab) in enumerate(D.TRADE_MARKERS, 1):
        col, shape = mk[kind]
        mx_ = m["X"](i)
        if shape == "up":
            yy = m["Y"](data[i]["l"]) + 10
            s.path(f"M{mx_} {yy} L{mx_ + 7} {yy + 11} L{mx_ - 7} {yy + 11} Z", fill=col)
            T(s, mx_, yy + 14, str(num), 12, 16, col, 700, anchor="middle")
        elif shape == "down":
            yy = m["Y"](data[i]["h"]) - 10
            s.path(f"M{mx_} {yy} L{mx_ + 7} {yy - 11} L{mx_ - 7} {yy - 11} Z", fill=col)
            T(s, mx_, yy - 30, str(num), 12, 16, col, 700, anchor="middle")
        else:
            yy = m["Y"](data[i]["l"]) + 10
            s.circle(mx_, yy + 7, 8, fill=WH, stroke=col, sw=1.5)
            s.icon("x", mx_ - 5, yy + 2, col, s=10, sw=1.8)
            T(s, mx_, yy + 18, str(num), 12, 16, col, 700, anchor="middle")
    cy += 16 + ch + 28
    T(s, cx0, cy, D.CANDLE_DATES[0], 12, 16, T2)
    T(s, cx0 + cwid, cy, D.CANDLE_DATES[1], 12, 16, T2, anchor="end")
    cy += 32
    colw = (MW - 48 - 24) / 2
    for num, (i, kind, lab) in enumerate(D.TRADE_MARKERS):
        col, shape = mk[kind]
        lx = x + 24 + (num % 2) * (colw + 24)
        ly = cy + (num // 2) * 32
        s.circle(lx + 12, ly + 12, 12, fill={"buy": POS_BG, "partial": YS, "sell": NEG_BG, "rejected": NEUT}[kind])
        T(s, lx + 12, ly + 2, str(num + 1), 12, 20, col if kind != "partial" else WARN_TX, 700, anchor="middle")
        T(s, lx + 34, ly, truncate(lab, colw - 34, 14), 14, 24, T1)
    cy += 64 + 16
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- метрики
    y = metrics_table(s, x, y, MW) + GAP
    y = disclaimer(s, x, y)
    main_end = y

    # --- правая колонка
    ry = why(s, RX, y0, RW, [
        ("p", "Наивный прогон покупает по цене сигнала и ничего не платит. Так не бывает: брокер берёт комиссию, "
              "спред и проскальзывание съедают часть цены, а купить успеваете только утром."),
        ("p", "Показывайте на защите оба числа. Разница между ними — цена реальности."),
    ])
    ry += GAP
    # издержки по видам
    idx = len(s.body)
    py = ry
    T(s, RX + 24, ry + 20, "Сколько стоили сделки", 20, 28, T1, 700)
    T(s, RX + 24, ry + 52, D.COSTS_TOTAL, 32, 40, T1, 700)
    cy = P(s, RX + 24, ry + 96, "комиссии, сбор, спред и проскальзывание за 412 сделок", RW - 48, 14, 20, T2) + 12
    mxv = max(-v for _, v, _ in D.DELTA_BREAKDOWN)
    for name, v, rub in D.DELTA_BREAKDOWN:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        tw_ = RW - 48 - 96
        yy = P(s, RX + 24, cy + 10, name, tw_, 14, 20, T1)
        T(s, RX + RW - 24, cy + 10, fmt_pct(v).replace(" %", " п.п."), 14, 20, NEG, 700, anchor="end")
        if rub:
            T(s, RX + RW - 24, cy + 30, rub, 12, 16, T2, anchor="end")
        bw_ = (RW - 48 - 96) * (-v) / mxv
        s.rect(RX + 24, yy + 6, RW - 48 - 96, 6, NEUT, rx=3)
        s.rect(RX + 24, yy + 6, bw_, 6, NEG, rx=3, opacity=0.75)
        cy = max(yy + 12, cy + 46) + 12
    cy = P(s, RX + 24, cy + 4, "Задержка и лимит ликвидности не стоят денег напрямую — они меняют цену и объём сделок.",
           RW - 48, 12, 16, T2) + 20
    behind(s, idx, lambda t: island(t, RX, py, RW, cy - py))
    ry = cy + GAP
    # предупреждения
    idx = len(s.body)
    py = ry
    cy = island_title(s, RX + 24, ry + 20, "На что обратить внимание", w=RW - 48)
    cy += 8
    for f in D.FLAGS:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        warn = f["level"] == "warning"
        s.circle(RX + 24 + 12, cy + 26, 12, fill=YS if warn else INFO_BG)
        s.icon("warn" if warn else "info", RX + 24 + 5, cy + 19, WARN_TX if warn else INFO, s=14, sw=1.8)
        cy = P(s, RX + 60, cy + 14, f["text"], RW - 84, 14, 20, T1) + 14
    cy += 8
    behind(s, idx, lambda t: island(t, RX, py, RW, cy - py))
    ry = cy + GAP
    # воспроизводимость
    idx = len(s.body)
    py = ry
    cy = island_title(s, RX + 24, ry + 20, "Как повторить этот прогон",
                      "Запустим заново с теми же данными, кодом и seed — результат должен совпасть до копейки.", w=RW - 48)
    cy += 12
    R = D.REPRO
    rows = [("Прогон", R["run"]), ("Снапшот", R["dataset"]), ("Стратегия", R["strategy"]), ("Движок", R["engine"]),
            ("Seed", R["seed"]), ("Запущен", R["started"]), ("Длительность", R["duration"])]
    for a, b in rows:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        T(s, RX + 24, cy + 8, a, 14, 20, T2)
        yy = P(s, RX + 128, cy + 8, b, RW - 24 - 128, 14, 20, T1)
        cy = yy + 8
    cy += 8
    button(s, RX + 24, cy, "Воспроизвести", "outline", icon="repeat", w=RW - 48)
    cy += 44 + 24
    behind(s, idx, lambda t: island(t, RX, py, RW, cy - py))
    ry = cy + GAP
    idx = len(s.body)
    py = ry
    cy = island_title(s, RX + 24, ry + 20, "Что проверить дальше", w=RW - 48)
    cy += 8
    for icon, a, b in [("compare", "Сравнение", "Почему 84,2 % превратились в 31,6 %, по вкладам, и флаги по четырём стратегиям"),
                       ("steps", "Walk-forward", "На новых данных доходность падает с +9,0 % до +0,5 % за квартал")]:
        s.line(RX + 24, cy + 0.5, RX + RW - 24, cy + 0.5, stroke=LN)
        s.rect(RX + 24, cy + 16, 32, 32, NEUT, rx=8)
        s.icon(icon, RX + 32, cy + 24, T1, s=16)
        T(s, RX + 72, cy + 14, a, 16, 24, INFO, 700)
        cy = P(s, RX + 72, cy + 38, b, RW - 96, 14, 20, T2) + 16
    cy += 8
    behind(s, idx, lambda t: island(t, RX, py, RW, cy - py))

    h = max(main_end, cy) + 40 + FOOT
    footer(s, h, "Далее: Сравнение", note="Шаг 5 из 5. Прогон сохранён в «Мои исследования»")
    return finish(s, h, "C4")


# =========================================================================================
# C5. Сравнение
# =========================================================================================
DELTA_HUMAN = {
    "Задержка: исполнение по open t+1": "Покупаем утром следующего дня, а не по цене сигнала",
    "Спред": "Покупаем дороже середины, продаём дешевле",
    "Проскальзывание": "Наши заявки сдвигают цену против нас",
    "Комиссия брокера": "0,05 % с оборота каждой сделки",
    "Лимит ликвидности: 11 частичных, 6 отказов": "Не больше 5 % объёма бара за раз",
    "Биржевой сбор": "0,01 % с оборота каждой сделки",
}


def screen5():
    s = new(2400)
    header(s, 0)
    stepper(s, 5)
    y0 = result_head(s, 1)
    x, y = MX, y0

    # --- водопад
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Куда делись 52,6 п.п. доходности",
                      "Начинаем с наивного прогона и по очереди добавляем то, что бывает в реальной торговле.")
    cy += 20
    lw = 248
    bx0 = x + 24 + lw + 16
    bw_ = MW - 48 - lw - 16 - 96
    sc = lambda v: bx0 + bw_ * v / 90
    # шкала
    for v in (0, 20, 40, 60, 80):
        T(s, sc(v), cy, f"{v} %", 12, 16, T2, anchor="middle")
    cy += 24
    top_scale = cy
    rows = [("Наивный прогон", "Сделки бесплатные и мгновенные", 0, 84.2, "start", None)]
    run = 84.2
    for name, v, rub in D.DELTA_BREAKDOWN:
        rows.append((name, DELTA_HUMAN[name], run + v, run, "delta", (v, rub)))
        run += v
    rows.append(("Честный прогон", "То, что осталось на самом деле", 0, 31.6, "end", None))
    geo = []
    for name, expl, a, b, kind, extra in rows:
        nl = nlines(name, lw, 14, 700) + 0.8 * nlines(expl, lw, 12)
        rh = max(56, round(nl * 20) + 16)
        geo.append((cy, rh))
        cy += rh
    for v in (0, 20, 40, 60, 80):
        s.line(sc(v), top_scale, sc(v), cy, stroke=LN, dash=None if v == 0 else "2 4")
    for k, (name, expl, a, b, kind, extra) in enumerate(rows):
        top, rh = geo[k]
        if k:
            s.line(x + 24, top + 0.5, bx0 - 8, top + 0.5, stroke=LN)
        yy = P(s, x + 24, top + 8, name, lw, 14, 20, T1, 700)
        P(s, x + 24, yy, expl, lw, 12, 16, T2)
        bt = top + (rh - 24) / 2
        if kind == "start":
            s.rect(sc(a), bt, sc(b) - sc(a), 24, T3, rx=4)
            T(s, x + MW - 24, top, "+84,2 %", 16, rh, T2, 700, anchor="end")
        elif kind == "end":
            s.rect(sc(a), bt, sc(b) - sc(a), 24, POS, rx=4)
            T(s, x + MW - 24, top, "+31,6 %", 16, rh, POS, 700, anchor="end")
        else:
            v, rub = extra
            s.rect(sc(a), bt, sc(b) - sc(a), 24, NEG, rx=4, opacity=0.85)
            T(s, x + MW - 24, top + rh / 2 - (20 if rub else 10), fmt_pct(v).replace(" %", " п.п."), 14, 20, NEG, 700, anchor="end")
            if rub:
                T(s, x + MW - 24, top + rh / 2, rub, 12, 16, T2, anchor="end")
        if k < len(rows) - 1:
            nb = rows[k + 1]
            lvl = b if kind == "start" else a
            ntop = geo[k + 1][0] + (geo[k + 1][1] - 24) / 2
            s.line(sc(lvl), bt + 24, sc(lvl), ntop, stroke=T2, sw=1, dash="2 2")
    cy += 16
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- таблица стратегий
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Все стратегии: наивно и честно",
                      "Флаг появляется, когда результат держится на идеальных условиях.")
    cy += 16
    # правые края колонок
    cols = [("Стратегия", x + 24, "start"), ("Честно", x + 300, "end"), ("Наивно", x + 396, "end"),
            ("Sharpe", x + 520, "end"), ("Просадка", x + 624, "end"), ("Оборот", x + MW - 24, "end")]
    s.line(x, cy - 0.5, x + MW, cy - 0.5, stroke=LN)
    for lab, cx, an in cols:
        T(s, cx, cy + 8, lab, 12, 16, T2, anchor=an)
    T(s, x + 520, cy + 24, "честно / наивно", 12, 16, T2, anchor="end")
    cy += 48
    for r in D.COMPARISON:
        s.line(x, cy - 0.5, x + MW, cy - 0.5, stroke=LN)
        rh = 84 if r["flag"] else 56
        if r["name"] == "SMA 20/50":
            s.rect(x + 1, cy, MW - 2, rh, YL)
        top = cy + 8
        T(s, cols[0][1], top, r["name"], 16, 40, T1, 700)
        T(s, cols[1][1], top, r["honest"], 16, 40, POS if r["h"] > 0 else NEG, 700, anchor="end")
        T(s, cols[2][1], top, r["naive"], 16, 40, T2, anchor="end")
        T(s, cols[3][1], top, f"{r['sharpe']} / {r['sharpe_naive']}", 16, 40, T1, anchor="end")
        T(s, cols[4][1], top, r["dd"], 16, 40, T1, anchor="end")
        T(s, cols[5][1], top, r["turnover"], 16, 40, T1, anchor="end")
        if r["flag"]:
            fl = r["flag"][0].upper() + r["flag"][1:]
            badge(s, x + 24, cy + 48, fl, "neg" if "знак" in fl else "warn", icon="warn")
        cy += rh
    cy += 12
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- наложение кривых
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Капитал стратегий в честном режиме", "Все прогоны с издержками и задержкой, рядом индекс IMOEX.")
    cy += 12
    ser = [("SMA 20/50", D.EQUITY_HONEST, T1, None, 2.5), ("Моментум 3М", D.EQUITY_MOMENTUM, INFO, None, 2),
           ("RSI-откат", D.EQUITY_RSI, "#B4530A", None, 2), ("IMOEX", D.EQUITY_IMOEX, T3, "5 4", 2)]
    lx = x + 24
    for lab, _, col, dash, sw in ser:
        s.line(lx, cy + 10, lx + 20, cy + 10, stroke=col, sw=sw, dash=dash)
        T(s, lx + 28, cy, lab, 14, 20, T2)
        lx += 28 + measure(lab, 14) + 24
    cy += 32
    gx, gw, gh = x + 72, MW - 72 - 24 - 156, 220
    vmin, vmax = 0.5, 1.6
    Yv = lambda v: cy + gh - gh * (v - vmin) / (vmax - vmin)
    for v in (0.6, 0.8, 1.0, 1.2, 1.4):
        s.line(gx, Yv(v), gx + gw, Yv(v), stroke=LN, dash=None if v == 1.0 else "2 4")
        T(s, gx - 12, Yv(v) - 8, f"{v:.1f}".replace(".", ",") + " млн", 12, 16, T2, anchor="end")
    stress_marks(s, gx, cy, gw, gh)
    for lab, vals, col, dash, sw in reversed(ser):
        d, _ = ts_path(vals, gx, cy, gw, gh, vmin, vmax)
        s.path(d, stroke=col, sw=sw, dash=dash)
    ends = sorted([(Yv(v[-1]), lab, col, v[-1]) for lab, v, col, _, _ in ser])
    last = -99
    for yy, lab, col, v in ends:
        ly = max(yy, last + 22)
        last = ly
        s.circle(gx + gw, yy, 3.5, fill=col)
        T(s, gx + gw + 10, ly - 10, f"{lab} {fmt_pct((v - 1) * 100)}", 13, 20, col, 700)
    cy += gh + 8
    year_axis(s, gx, cy, gw)
    cy += 36
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP
    y = disclaimer(s, x, y)
    main_end = y

    # --- правая колонка
    ry = why(s, RX, y0, RW, [
        ("p", "Если прибыль держится только на бесплатных и мгновенных сделках, это не стратегия, а ошибка в модели."),
        ("p", "Самый большой вклад — задержка: 21,4\u00a0п.п. Сигнал появляется вечером, а купить можно только утром, "
              "когда цена уже ушла."),
        ("b", "Когда мы ставим флаг"),
        ("li", "Издержки больше половины прибыли — стратегия хрупкая."),
        ("li", "Издержки меняют знак — без них прибыль, с ними убыток."),
        ("li", "Наивный Sharpe больше 3 — слишком хорошо, чтобы быть правдой. Проверьте, не читает ли код будущее."),
    ])
    h = max(main_end, ry) + 40 + FOOT
    footer(s, h, "Далее: Walk-forward", note="Сравнение строится по последним честным и наивным прогонам каждой стратегии")
    return finish(s, h, "C5")


# =========================================================================================
# C6. Walk-forward
# =========================================================================================
def screen6():
    s = new(2400)
    header(s, 0)
    stepper(s, 5)
    y0 = result_head(s, 2)
    x, y = MX, y0
    WF = D.WALK_FORWARD
    S = D.WF_SUMMARY

    # --- сводка
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Работают ли параметры на новых данных",
                      "20 раз подбирали параметры на прошлом году и проверяли их на следующем квартале.")
    cy += 20
    cols = [
        ("Деградация", S["degradation"], NEG, "На проверке +0,5 % за квартал против +9,0 % на подборе"),
        ("Прибыльных окон", S["positive"], T1, "Чуть больше половины проверок закончились в плюсе"),
        ("Итог проверок", S["oos_total"], POS, "Сумма всех 20 кварталов, которых стратегия не видела"),
        ("Самые частые параметры", "20/50", T1, "Выбраны в 9 окнах из 20 — стабильность средняя"),
    ]
    cw_ = (MW - 48) / 4
    hmax = 0
    for i, (lab, val, col, expl) in enumerate(cols):
        cx = x + 24 + i * cw_
        if i:
            s.line(cx - 12 + 0.5, cy, cx - 12 + 0.5, cy + 132, stroke=LN)
        T(s, cx, cy, lab, 14, 20, T2)
        T(s, cx, cy + 24, val, 28, 36, col, 700)
        yy = P(s, cx, cy + 68, expl, cw_ - 24, 14, 20, T1)
        hmax = max(hmax, yy - cy)
    cy += hmax + 24
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- столбики IS vs OOS
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Подбор и проверка по окнам",
                      "Серый — доходность на годе подбора за квартал, цветной — на квартале проверки.")
    cy += 16
    gx, gw, gh = x + 64, MW - 64 - 24, 180
    vmin, vmax = -8, 14
    Yv = lambda v: cy + gh - gh * (v - vmin) / (vmax - vmin)
    for v in (-5, 0, 5, 10):
        s.line(gx, Yv(v), gx + gw, Yv(v), stroke=T3 if v == 0 else LN, dash=None if v == 0 else "2 4")
        T(s, gx - 12, Yv(v) - 8, fmt_pct(v, 0) if v else "0 %", 12, 16, T2, anchor="end")
    slot = gw / 20
    for i, wv in enumerate(WF):
        sx = gx + i * slot
        bw2 = slot * 0.32
        for j, (v, col) in enumerate([(wv["train_ret"], "#C9CCD8"), (wv["test_ret"], POS if wv["test_ret"] >= 0 else NEG)]):
            bx = sx + slot * 0.16 + j * (bw2 + 2)
            top, bot = Yv(max(v, 0)), Yv(min(v, 0))
            s.rect(bx, top, bw2, max(1, bot - top), col, rx=2)
        T(s, sx + slot / 2, cy + gh + 6, f"{wv['n']:02d}", 12, 16, T2, anchor="middle")
    cy += gh + 32
    T(s, gx, cy, "Номер окна", 12, 16, T3)
    cy += 32
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP

    # --- схема окон
    idx = len(s.body)
    py = y
    cy = island_title(s, x + 24, y + 20, "Как устроены окна",
                      "Год подбора, затем три месяца проверки, затем сдвиг на квартал. Нумерация — по порядку.")
    cy += 16
    lx = x + 24
    for lab, col in [("Год подбора", "#DDE1EC"), ("Проверка в плюс", POS), ("Проверка в минус", NEG)]:
        s.rect(lx, cy + 4, 16, 12, col, rx=3)
        T(s, lx + 24, cy, lab, 14, 20, T2)
        lx += 24 + measure(lab, 14) + 24
    cy += 32
    nx = x + 24
    tlx, tlw = x + 64, 392
    px_ = tlx + tlw + 24
    trx = px_ + 72 + 80
    tex = x + MW - 24
    d0, d1 = date(2020, 1, 1), date(2026, 1, 1)
    T(s, nx, cy, "Окно", 12, 16, T2)
    for yr in range(2020, 2027):
        xx = dx(date(yr, 1, 1), tlx, tlw, d0, d1)
        T(s, xx, cy, str(yr)[2:] if False else str(yr), 12, 16, T2, anchor="middle" if 2020 < yr < 2026 else ("start" if yr == 2020 else "end"))
    T(s, px_, cy, "Параметры", 12, 16, T2)
    T(s, trx, cy, "Подбор", 12, 16, T2, anchor="end")
    T(s, tex, cy, "Проверка", 12, 16, T2, anchor="end")
    cy += 24
    s.line(x, cy - 0.5, x + MW, cy - 0.5, stroke=LN)
    grid_top = cy
    rh = 24
    for yr in range(2020, 2027):
        xx = dx(date(yr, 1, 1), tlx, tlw, d0, d1)
        s.line(xx, grid_top, xx, grid_top + 20 * rh + 8, stroke=LN, dash="2 4")
    cy += 4
    for wv in WF:
        mm, yy_ = wv["train"].split(" — ")[0].split(".")
        tr0 = date(int(yy_), int(mm), 1)
        tr1 = date(tr0.year + 1, tr0.month, 1)
        te1 = date(tr1.year + (tr1.month + 2) // 12, (tr1.month + 2) % 12 + 1, 1)
        a, b, c = (dx(d, tlx, tlw, d0, d1) for d in (tr0, tr1, te1))
        T(s, nx, cy, f"{wv['n']:02d}", 12, rh, T2)
        s.rect(a, cy + 6, b - a - 1, 12, "#DDE1EC", rx=3)
        pos = wv["test_ret"] >= 0
        s.rect(b, cy + 6, c - b, 12, POS if pos else NEG, rx=3)
        p = wv["params"]
        if p == "20/50":
            s.rect(px_ - 6, cy + 3, measure(p, 12, 700) + 12, 18, YS, rx=4)
        T(s, px_, cy, p, 12, rh, T1, 700 if p == "20/50" else 400)
        T(s, trx, cy, fmt_pct(wv["train_ret"]), 12, rh, T2, anchor="end")
        T(s, tex, cy, fmt_pct(wv["test_ret"]), 12, rh, POS if pos else NEG, 700, anchor="end")
        cy += rh
    cy += 20
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + GAP
    y = disclaimer(s, x, y)
    main_end = y

    # --- правая колонка
    def mini(t, xx, yy, ww):
        t.rect(xx, yy, ww, 88, WH, rx=10)
        bx, bw3 = xx + 16, ww - 32
        t.rect(bx, yy + 40, bw3 * 0.8, 20, "#DDE1EC", rx=4)
        t.rect(bx + bw3 * 0.8 + 2, yy + 40, bw3 * 0.2 - 2, 20, POS, rx=4)
        T(t, bx, yy + 14, "подбор, 12 мес.", 12, 16, T2)
        T(t, bx + bw3, yy + 14, "проверка, 3 мес.", 12, 16, T2, anchor="end")
        T(t, bx, yy + 64, "выбираем параметры", 12, 16, T1)
        T(t, bx + bw3, yy + 64, "смотрим итог", 12, 16, T1, anchor="end")

    ry = why(s, RX, y0, RW, [
        ("p", "Подобрать параметры, которые идеально работали в прошлом, легко. Важно другое — работают ли они "
              "на данных, которых стратегия не видела."),
        ("fn", 88, mini),
        ("p", "На подборе стратегия зарабатывала +9,0 % за квартал, на проверке — +0,5 %. Такой разрыв значит, "
              "что параметры подогнаны под прошлое."),
        ("p", "Хороший знак — когда одни и те же параметры выбираются в большинстве окон."),
    ])
    h = max(main_end, ry) + 40 + FOOT
    footer(s, h, "Сохранить исследование", note="Отчёт, сравнение и walk-forward сохранятся в «Мои исследования»")
    return finish(s, h, "C6")


# =========================================================================================
# C7. Мои исследования (история прогонов)
# =========================================================================================
def screen7():
    s = new(1200)
    header(s, 1)
    top = 104
    T(s, X0, top, "Мои исследования", 32, 40, T1, 700)
    y0 = P(s, X0, top + 48, "Все прогоны команды. Отметьте два, чтобы сравнить, или повторите любой — "
           "с теми же данными, кодом и seed.", 900, 16, 24, T2) + 32
    x, y = MX, y0

    # фильтры
    chips = [("Все", 10, None), ("Валиден", 7, "valid"), ("С пометкой", 2, "warning"), ("Невалиден", 1, "invalid")]
    cx = x
    for i, (lab, n, st) in enumerate(chips):
        on = i == 0
        txt = f"{lab}  {n}"
        cw2 = measure(lab, 14, 700) + measure(f"  {n}", 14) + 32
        s.rect(cx, y, cw2, 32, Y if on else WH, rx=16, stroke=None if on else "#D4D6DF")
        T(s, cx + 16, y, lab, 14, 32, T1, 700)
        T(s, cx + 16 + measure(lab, 14, 700) + 6, y, str(n), 14, 32, T1 if on else T2)
        cx += cw2 + 8
    y += 32 + 16
    field(s, x, y, 300, "", "Поиск по прогону или стратегии", h=44, icon="search", value_fill=T3)
    field(s, x + 316, y, 214, "", "Стратегия: все", h=44, icon="chevron-down")
    field(s, x + 546, y, 214, "", "Автор: все", h=44, icon="chevron-down")
    y += 44 + 16

    # таблица
    idx = len(s.body)
    py = y
    cols = [(x + 52, "Прогон"), (x + 180, "Стратегия и режим"), (x + 364, "Данные"), (x + 444, "Статус"),
            (x + 640, "Результат")]
    T(s, x + 52, y, "Прогон", 12, 40, T2)
    T(s, x + 172, y, "Стратегия и режим", 12, 40, T2)
    T(s, x + 340, y, "Данные", 12, 40, T2)
    T(s, x + 420, y, "Статус и автор", 12, 40, T2)
    T(s, x + 668, y, "Результат", 12, 40, T2, anchor="end")
    checkbox(s, x + 20, y + 10, False)
    s.rect(x + 21, y + 11, 18, 18, Y, rx=5)
    s.line(x + 25, y + 20, x + 35, y + 20, stroke=T1, sw=2)
    cy = y + 40
    sel_ids = {"run-0142", "run-0141"}
    for r in D.RUNS:
        s.line(x, cy - 0.5, x + MW, cy - 0.5, stroke=LN)
        inv = r["status"] == "invalid"
        rh = 72 if inv else 60
        sel = r["id"] in sel_ids
        if sel:
            s.rect(x + 1, cy, MW - 2, rh, YL)
        checkbox(s, x + 20, cy + (rh - 20) / 2 if not inv else cy + 20, sel)
        mid = cy + (20 if not inv else 26) - 10
        T(s, x + 52, cy + 10, r["id"], 14, 20, T1, 700)
        T(s, x + 52, cy + 30, r["started"], 12, 16, T2)
        T(s, x + 172, cy + 10, r["strategy"], 14, 20, T1)
        T(s, x + 172, cy + 30, r["mode"], 12, 16, T2)
        T(s, x + 340, cy + 10, r["dataset"], 14, 20, T1)
        status_badge(s, x + 420, cy + 8, r["status"])
        if inv:
            T(s, x + 420, cy + 36, "close[+1] в строке 8 читает бар t+1", 12, 16, NEG)
            T(s, x + 420, cy + 52, r["author"], 12, 16, T2)
        else:
            T(s, x + 420, cy + 36, r["author"], 12, 16, T2)
        res = r["result"]
        col = T3 if res == "—" else (NEG if res.startswith("−") else (POS if r["mode"] == "честный" else T2))
        T(s, x + 668, cy, res, 14, rh, col, 700, anchor="end")
        # действие
        s.rect(x + MW - 52, cy + (rh - 32) / 2, 32, 32, NEUT if not inv else WH, rx=8)
        s.icon("repeat", x + MW - 44, cy + (rh - 16) / 2, T1 if not inv else T3, s=16)
        cy += rh
    behind(s, idx, lambda t: island(t, x, py, MW, cy - py))
    y = cy + 16
    y = disclaimer(s, x, y)
    main_end = y

    # правая колонка
    def legend(t, xx, yy, ww):
        rows = [("valid", "Проверки пройдены. Результату можно доверять в рамках модели."),
                ("warning", "Есть подозрительное место, например adj_close. Результат показываем с предупреждением."),
                ("invalid", "Стратегия читает будущее. Результат не считаем — исправьте код и запустите снова.")]
        cy_ = yy
        for st, txt in rows:
            status_badge(t, xx, cy_, st)
            cy_ = P(t, xx, cy_ + 32, txt, ww, 14, 20, T1) + 16
        return cy_ - yy - 16

    ry = why(s, RX, y0, RW, [
        ("p", "Статус показывает, можно ли доверять прогону. Невалидный прогон нельзя показывать на защите."),
        ("fn", 292, legend),
        ("p", "«Воспроизвести» запускает прогон заново с теми же данными, кодом и seed. Числа должны совпасть."),
    ])
    ry += GAP
    idx = len(s.body)
    py = ry
    T(s, RX + 24, ry + 20, "Последнее исследование", 20, 28, T1, 700)
    T(s, RX + 24, ry + 56, "SMA 20/50, 05.10.2026", 14, 20, T2)
    T(s, RX + 24, ry + 80, "+84,2 %", 20, 28, T2, 700)
    arrow_right(s, RX + 24 + measure("+84,2 %", 20, 700) + 12, ry + 94, 28, T2, sw=2)
    T(s, RX + 24 + measure("+84,2 %", 20, 700) + 52, ry + 76, "+31,6 %", 28, 36, POS, 700)
    cy = ry + 124
    button(s, RX + 24, cy, "Открыть отчёт", "outline", "s")
    cy += 32 + 24
    behind(s, idx, lambda t: island(t, RX, py, RW, cy - py))

    h = max(main_end, cy) + 32 + FOOT
    # липкая панель действий
    fy = h - FOOT
    s.rect(0, fy, W, FOOT, WH)
    s.line(0, fy + 0.5, W, fy + 0.5, stroke=LN)
    T(s, X0, fy, "Выбрано 2 прогона: run-0142 и run-0141", 16, FOOT, T1, 700)
    bw = button(s, X0 + CW, fy + 14, "Сравнить выбранные", "primary", icon="compare", anchor="end")
    button(s, X0 + CW - bw - 12, fy + 14, "Воспроизвести", "secondary", icon="repeat", anchor="end")
    return finish(s, h, "C7")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ["1", "2", "3", "4", "5", "6", "7"]
    fns = {"1": screen1, "2": screen2, "3": screen3, "4": screen4, "5": screen5, "6": screen6, "7": screen7}
    for k in which:
        p = fns[k]()
        print(p)
