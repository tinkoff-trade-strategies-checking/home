"""Концепция E. Дашборд: сайдбар, таблицы, плотная операционная консоль команды.

Запуск: python gen.py  ->  out/E1.svg … out/E7.svg
Запоминающаяся деталь: «светофор честности» — сегменты Данные / Будущее / Издержки у каждого прогона.
"""
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from svg import *  # noqa: E402,F403
import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --- токены (rgba заранее смешаны в hex) ----------------------------------------------
BG = "#F2F3F5"
SURF = "#FFFFFF"
ALT = "#F6F6F7"
BORDER = "#E1E2E6"      # rgba(0,0,0,.1) поверх белого/фона
DIV = "#ECEDF0"
FIELD = "#D5D7DD"
TEXT = "#1B1F3B"
TEXT2 = "#6B6D80"       # rgba(27,31,59,.65)
TEXT3 = "#A4A5B1"       # rgba(27,31,59,.4)
ACCENT = "#526ED3"
ACTION = "#4C66C3"
ACC_BG = "#EEF1FB"      # accent 10 %
SEL_BG = "#F3F5FD"
POS = "#008764"
NEG = "#EB1700"
YELLOW = "#FFDD2D"
OK_C = "#4AC99B"
WARN_C = "#FFC700"
BAD_C = "#FF291A"
SB_BG = "#1B1F3B"
SB_T2 = "#A4A5B1"
SB_ACT = "#2E3354"
SB_LINE = "#2C3152"
SB_FIELD = "#252A4A"
UP = "#2FA57D"
DOWN = "#E5483A"
NAIVE = "#7A7D93"
IMOEX_C = "#B8BBC8"
MOM_C = "#8E5BD0"
RSI_C = "#E07B39"

W = 1440
SB = 248
TOPH = 56
X0 = SB + 24
X1 = W - 24
CW = X1 - X0  # 1144

OVERFLOWS = []


def fit(s, maxw, size=14, weight=400, mono=False, where=""):
    """Обрезает строку по реальной ширине и логирует обрезку."""
    s = str(s)
    if measure(s, size, weight, mono) <= maxw:
        return s
    OVERFLOWS.append(f"{where}: «{s}» {measure(s, size, weight, mono):.0f}/{maxw:.0f}")
    return truncate(s, maxw, size, weight, mono)


def T(s, x, cy, txt, size=14, fill=TEXT, weight=400, anchor="start", mono=False, maxw=None, opacity=None):
    """Текст, выровненный по вертикальному центру строки cy."""
    if maxw:
        txt = fit(txt, maxw, size, weight, mono, where=f"T@{int(x)},{int(cy)}")
    s.text(x, cy + size * 0.36, txt, size=size, fill=fill, weight=weight, anchor=anchor, mono=mono, opacity=opacity)
    return measure(txt, size, weight, mono)


def P(s, x, top, txt, width, size=13, lh=None, fill=TEXT, weight=400, mono=False, max_lines=None):
    """Абзац: top — верх первой строки. Возвращает низ абзаца."""
    lh = lh or round(size * 1.45)
    lines = wrap(txt, width, size, weight, mono)
    if max_lines and len(lines) > max_lines:
        OVERFLOWS.append(f"para cut: «{txt[:40]}…»")
        lines = lines[:max_lines]
        lines[-1] = truncate(lines[-1] + " …", width, size, weight, mono)
    for i, ln in enumerate(lines):
        T(s, x, top + lh / 2 + i * lh, ln, size, fill, weight, mono=mono)
    return top + len(lines) * lh


def nlines(txt, width, size=13, weight=400, mono=False):
    return len(wrap(txt, width, size, weight, mono))


# --- компоненты -------------------------------------------------------------------------
def panel(s, x, y, w, h, title=None, count=None, rx=12):
    s.rect(x, y, w, h, SURF, rx=rx, stroke=BORDER)
    if title:
        tw = T(s, x + 16, y + 26, title, 16, TEXT, 700)
        if count is not None:
            counter(s, x + 16 + tw + 8, y + 26, str(count))
    return y + 52


def insert_panel(s, idx, x, y, w, h):
    """Подложка панели, высота которой стала известна после отрисовки содержимого."""
    tmp = Svg(10, 10)
    tmp.rect(x, y, w, h, SURF, rx=12, stroke=BORDER)
    s.body.insert(idx, tmp.body[0])


def counter(s, x, cy, label):
    w = measure(label, 12, 700) + 12
    s.rect(x, cy - 10, w, 20, ALT, rx=6, stroke=DIV)
    T(s, x + w / 2, cy, label, 12, TEXT2, 700, anchor="middle")
    return w


def btn_w(label, h=32, icon=None):
    size = 14 if h <= 32 else 16
    pad = 12 if h <= 32 else 20
    return measure(label, size, 700) + 2 * pad + (24 if icon else 0)


def button(s, x, y, label, kind="secondary", h=32, icon=None, w=None, align="start"):
    size = 14 if h <= 32 else 16
    W_ = w or btn_w(label, h, icon)
    if align == "end":
        x -= W_
    fills = {
        "primary": (YELLOW, "#000000", None),
        "accent": (ACCENT, "#FFFFFF", None),
        "secondary": (ACC_BG, ACTION, None),
        "outline": (SURF, TEXT, FIELD),
        "flat": ("none", ACTION, None),
        "disabled": (ALT, TEXT3, None),
    }
    bg, fg, st = fills[kind]
    s.rect(x, y, W_, h, bg, rx=10, stroke=st)
    cw = measure(label, size, 700) + (24 if icon else 0)
    cx = x + (W_ - cw) / 2
    if icon:
        s.icon(icon, cx, y + h / 2 - 8, fg)
        cx += 24
    T(s, cx, y + h / 2, label, size, fg, 700)
    return W_


def icon_btn(s, x, y, icon, size=32, kind="outline"):
    bg, st = (SURF, FIELD) if kind == "outline" else (ACC_BG, None)
    s.rect(x, y, size, size, bg, rx=10, stroke=st)
    s.icon(icon, x + size / 2 - 8, y + size / 2 - 8, TEXT2 if kind == "outline" else ACTION)


BADGE = {
    "valid": (OK_C, "#0B7A55"),
    "warning": (WARN_C, "#7A5800"),
    "invalid": (BAD_C, "#C8160A"),
    "info": ("#70B6F6", "#1D5F9E"),
    "accent": (ACCENT, ACTION),
    "neutral": ("#1B1F3B", TEXT2),
}


def badge(s, x, cy, label, kind="neutral", dot=False, h=22, align="start"):
    base, fg = BADGE[kind]
    w = measure(label, 12, 700) + 16 + (12 if dot else 0)
    if align == "end":
        x -= w
    s.rect(x, cy - h / 2, w, h, base, rx=8, fill_opacity=0.08 if kind == "neutral" else 0.16)
    tx = x + 8
    if dot:
        s.circle(tx + 3, cy, 3, fill=base if kind != "neutral" else TEXT3)
        tx += 12
    T(s, tx, cy, label, 12, fg, 700)
    return w


def status_badge(s, x, cy, status, align="start"):
    return badge(s, x, cy, D.STATUS_LABEL[status], status, dot=True, align=align)


def field(s, x, y, w, label, value, h=44, select=False, readonly=False, suffix=None, icon=None, mono=False, hint=None, placeholder=False):
    """Поле Taiga с подписью внутри."""
    if readonly:
        s.rect(x, y, w, h, ALT, rx=10)
    else:
        s.rect(x, y, w, h, SURF, rx=10, stroke=FIELD)
    right = 12
    if select:
        s.icon("chevron-down", x + w - 28, y + h / 2 - 8, TEXT2)
        right = 36
    if icon:
        s.icon(icon, x + w - 28, y + h / 2 - 8, TEXT3)
        right = 36
    if suffix:
        sw_ = measure(suffix, 13) + 12
        T(s, x + w - right - sw_ + 12, y + h / 2 + 7, suffix, 13, TEXT3)
        right += sw_
    T(s, x + 12, y + 14, label, 12, TEXT2, maxw=w - 24)
    T(s, x + 12, y + 31, value, 14, TEXT3 if placeholder else TEXT, mono=mono, maxw=w - 12 - right)
    if hint:
        return P(s, x + 2, y + h + 4, hint, w - 4, 12, 16, TEXT2)
    return y + h


def toggle(s, x, cy, on=True):
    s.rect(x, cy - 10, 36, 20, ACCENT if on else "#D5D7DD", rx=10)
    s.circle(x + (26 if on else 10), cy, 8, fill="#FFFFFF")


def checkbox(s, x, cy, on=False):
    if on:
        s.rect(x, cy - 8, 16, 16, ACCENT, rx=4)
        s.icon("check", x + 1, cy - 7, "#FFFFFF", s=14, sw=2)
    else:
        s.rect(x + 0.5, cy - 7.5, 15, 15, SURF, rx=4, stroke=FIELD)


def tabs(s, x, y, items, active=0, h=48, size=14):
    cx = x
    for i, it in enumerate(items):
        w = measure(it, size, 700)
        T(s, cx, y + h / 2, it, size, TEXT if i == active else TEXT2, 700 if i == active else 400)
        if i == active:
            s.rect(cx, y + h - 2, w, 2, ACCENT)
        cx += w + 24
    return cx


def segmented(s, x, y, items, active=0, h=32):
    widths = [measure(it, 13, 700) + 24 for it in items]
    total = sum(widths) + 4
    s.rect(x, y, total, h, "#E9EAEE", rx=10)
    cx = x + 2
    for i, (it, w) in enumerate(zip(items, widths)):
        if i == active:
            s.rect(cx, y + 2, w, h - 4, SURF, rx=8, stroke=BORDER)
        T(s, cx + w / 2, y + h / 2, it, 13, TEXT if i == active else TEXT2, 700 if i == active else 400, anchor="middle")
        cx += w
    return total


def kv(s, x, cy, w, label, value, vfill=TEXT, vweight=400, mono=False, vsize=13, line=True):
    lw = T(s, x, cy, label, 13, TEXT2)
    T(s, x + w, cy, value, vsize, vfill, vweight, anchor="end", mono=mono, maxw=w - lw - 12)
    if line:
        s.line(x, cy + 15, x + w, cy + 15, DIV)


# --- светофор честности ------------------------------------------------------------------
LIGHT = {"ok": OK_C, "warn": WARN_C, "fail": BAD_C}
LIGHT_WORD = {"ok": "в порядке", "warn": "есть пометка", "fail": "ошибка", "off": "не учтены"}


def honesty(run_id):
    """(Данные, Будущее, Издержки) для прогона — выводится из data.py."""
    r = next(x for x in D.RUNS if x["id"] == run_id)
    data_s = "ok" if r["dataset"] == "ds-0007" else "warn"        # ds-0006 заменён ds-0007
    fut = {"valid": "ok", "warning": "warn", "invalid": "fail"}[r["status"]]
    if r["mode"] == "наивный" or r["status"] == "invalid":
        cost = "off"
    elif r["strategy"] == "RSI-откат":
        cost = "fail"                                              # издержки меняют знак
    elif r["strategy"] == "SMA 20/50":
        cost = "warn"                                              # издержки > 50 % прибыли
    else:
        cost = "ok"
    return (data_s, fut, cost)


def light(s, x, cy, states, seg=20, h=8, gap=3):
    for i, st in enumerate(states):
        sx = x + i * (seg + gap)
        if st == "off":
            s.rect(sx + 0.5, cy - h / 2 + 0.5, seg - 1, h - 1, SURF, rx=2, stroke="#AEB1BF", dash="2 2")
        else:
            s.rect(sx, cy - h / 2, seg, h, LIGHT[st], rx=2)
    return 3 * seg + 2 * gap


def light_legend(s, x, cy, size=12, compact=False):
    """Подпись к светофору: что значит каждый сегмент."""
    cx = x
    if compact:
        light(s, cx, cy - 10, ("ok", "warn", "fail"), seg=10, h=6, gap=2)
        T(s, cx + 44, cy - 10, "Сегменты светофора: данные, будущее, издержки", size, TEXT2)
        cy += 10
    else:
        cx += light(s, cx, cy, ("ok", "warn", "fail"), seg=10, h=6, gap=2) + 8
        cx += T(s, cx, cy, "Данные, Будущее, Издержки", size, TEXT2) + 20
    for st, word in (("ok", "в порядке"), ("warn", "пометка"), ("fail", "ошибка"), ("off", "не учтено")):
        if st == "off":
            s.rect(cx + 0.5, cy - 2.5, 9, 5, SURF, rx=1.5, stroke="#AEB1BF", dash="2 2")
        else:
            s.rect(cx, cy - 3, 10, 6, LIGHT[st], rx=1.5)
        cx += 16
        cx += T(s, cx, cy, word, size, TEXT2) + 16
    return cx - x


# --- оболочка ----------------------------------------------------------------------------
NAV = [("db", "Датасеты", "5"), ("code", "Стратегии", "4"), ("sliders", "Настройка прогона", ""),
       ("chart", "Отчёты", ""), ("compare", "Сравнение", ""), ("steps", "Walk-forward", ""),
       ("history", "История прогонов", "142")]


def shell(s, active, crumbs, new_run=True):
    H = s.h
    s.rect(0, 0, W, H, BG)
    # сайдбар
    s.rect(0, 0, SB, H, SB_BG)
    s.rect(20, 18, 32, 32, SB_ACT, rx=8)
    for i, col in enumerate((OK_C, WARN_C, BAD_C)):
        s.rect(26 + i * 7, 30, 6, 8, col, rx=1.5)
    T(s, 64, 25, "Честная проверка", 14, "#FFFFFF", 700)
    T(s, 64, 43, "стратегий", 14, "#FFFFFF", 700)
    s.rect(16, 68, SB - 32, 48, SB_FIELD, rx=10)
    T(s, 28, 82, "Проект", 12, SB_T2)
    T(s, 28, 101, "ПАК, учебная команда", 14, "#FFFFFF", 700)
    s.icon("chevron-down", SB - 44, 84, SB_T2)
    y = 136
    for i, (ic, label, cnt) in enumerate(NAV):
        on = i == active
        if on:
            s.rect(12, y, SB - 24, 36, SB_ACT, rx=10)
            s.rect(12, y + 8, 3, 20, YELLOW if False else "#FFFFFF", rx=1.5)
        s.icon(ic, 28, y + 10, "#FFFFFF" if on else SB_T2)
        T(s, 56, y + 18, label, 14, "#FFFFFF" if on else "#D7D8E0", 700 if on else 400)
        if cnt:
            T(s, SB - 28, y + 18, cnt, 12, SB_T2, anchor="end")
        y += 40
    y += 12
    s.line(16, y, SB - 16, y, SB_LINE)
    T(s, 28, y + 24, "Последние прогоны", 12, SB_T2)
    y += 40
    for rid in ("run-0142", "run-0141", "run-0140", "run-0139"):
        r = next(x for x in D.RUNS if x["id"] == rid)
        T(s, 28, y + 12, rid, 13, "#FFFFFF", mono=True)
        T(s, 28, y + 30, f'{r["strategy"]}, {r["mode"]}', 12, SB_T2, maxw=140)
        light(s, SB - 28 - 46, y + 12, honesty(rid), seg=14, h=6, gap=2)
        y += 44
    # низ сайдбара
    s.line(16, H - 104, SB - 16, H - 104, SB_LINE)
    s.circle(32, H - 82, 4, fill=OK_C)
    T(s, 44, H - 82, "Движок 0.3.1, очередь пуста", 12, SB_T2)
    s.circle(36, H - 40, 16, fill=ACCENT)
    T(s, 36, H - 40, "ДМ", 12, "#FFFFFF", 700, anchor="middle")
    T(s, 62, H - 49, D.USER, 14, "#FFFFFF", 700)
    T(s, 62, H - 31, "Исследователь", 12, SB_T2)
    # верхняя панель
    s.rect(SB, 0, W - SB, TOPH, SURF)
    s.line(SB, TOPH - 0.5, W, TOPH - 0.5, BORDER)
    cx = X0
    for i, c in enumerate(crumbs):
        last = i == len(crumbs) - 1
        cx += T(s, cx, 28, c, 14, TEXT if last else TEXT2, 700 if last else 400, mono=c.startswith("run-"))
        if not last:
            s.icon("chevron-right", cx + 6, 22, TEXT3, s=12)
            cx += 24
    bx = X1
    if new_run:
        bx -= button(s, X1, 12, "Новый прогон", "primary", icon="plus", align="end") + 12
    sw_ = 300
    s.rect(bx - sw_, 12, sw_, 32, BG, rx=10)
    s.icon("search", bx - sw_ + 12, 20, TEXT3)
    T(s, bx - sw_ + 36, 28, "Найти прогон, стратегию, хэш", 13, TEXT3)
    s.rect(bx - 52, 18, 40, 20, SURF, rx=6, stroke=BORDER)
    T(s, bx - 32, 28, "Ctrl K", 11, TEXT2, anchor="middle")


def page_header(s, title, meta=(), title_extra=None, buttons=(), y=80):
    """Заголовок страницы 24/28 + строка метаданных «подпись значение»."""
    tw = T(s, X0, y + 16, title, 24, TEXT, 700)
    cx = X0 + tw + 12
    if title_extra:
        for kind, payload in title_extra:
            if kind == "mono":
                cx += T(s, cx, y + 17, payload, 14, TEXT2, mono=True) + 12
            else:
                cx += badge(s, cx, y + 17, payload[0], payload[1], dot=payload[2] if len(payload) > 2 else False) + 8
    mx = X0
    for lab, val in meta:
        mx += T(s, mx, y + 48, lab, 13, TEXT2) + 6
        mx += T(s, mx, y + 48, val, 13, TEXT, mono=val.startswith(("ds-", "run-"))) + 24
    bx = X1
    for label, kind, icon in buttons:
        bx -= button(s, bx, y, label, kind, icon=icon, align="end") + 8


def disclaimer(s, y):
    s.icon("info", X0, y - 8, TEXT3, s=14, sw=1.4)
    T(s, X0 + 20, y - 1, D.DISCLAIMER, 12, TEXT2)


# --- графики по датам ---------------------------------------------------------------------
D0, D1 = D.DAYS[0], D.DAYS[-1]
SPAN = (D1 - D0).days


def dx(d, x, w):
    return x + w * (d - D0).days / SPAN


def date_series(s, values, x, y, w, h, vmin, vmax, stroke, sw=2, dash=None, opacity=None, step=3, area=None):
    n = len(values)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    pts = [(dx(D.DAYS[i], x, w), y + h - h * (values[i] - vmin) / (vmax - vmin)) for i in idx]
    d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
    if area:
        s.path(d + f" L{pts[-1][0]:.1f} {y + h:.1f} L{x:.1f} {y + h:.1f} Z", fill=area, fill_opacity=0.08)
    s.path(d, stroke=stroke, sw=sw, dash=dash, opacity=opacity)
    return pts


def hatch(s, x, y, w, h, color="#9EA1B2", step=4, bg=ALT):
    s.rect(x, y, w, h, bg)
    s.clip(x, y, w, h)
    k = -h
    while k < w:
        s.line(x + k, y + h, x + k + h, y, color, sw=0.8)
        k += step
    s.end()


def stress_marks(s, x, y, w, h, labels=True):
    """Март 2020, 24.02.2022 и разрыв торгов 28.02 — 23.03.2022."""
    a, b = dx(date(2020, 2, 24), x, w), dx(date(2020, 3, 23), x, w)
    s.rect(a, y, b - a, h, WARN_C, fill_opacity=0.18)
    g0, g1 = dx(date(2022, 2, 28), x, w), dx(date(2022, 3, 23), x, w)
    hatch(s, g0, y, g1 - g0, h)
    l = dx(date(2022, 2, 24), x, w)
    s.line(l, y, l, y + h, NEG, sw=1, dash="3 3")
    if labels:
        for lx, txt in ((b + 6, "Март 2020"), (g1 + 6, "24.02.2022, торги закрыты 28.02 — 23.03")):
            tw = measure(txt, 12, 700) + 10
            s.rect(lx - 2, y + 6, tw, 20, SURF, rx=6, opacity=0.92)
            T(s, lx + 3, y + 16, txt, 12, TEXT2, 700)


def year_axis(s, x, w, cy, years=range(2020, 2026)):
    for yr in years:
        d = max(date(yr, 1, 1), D0)
        px = dx(d, x, w)
        T(s, px, cy, str(yr), 12, TEXT3, anchor="start" if yr == 2020 else "middle")


def ru(v, digits=1):
    return f"{v:.{digits}f}".replace(".", ",")


# =========================================================================================
# E4 — Отчёт прогона
# =========================================================================================
def e4(H=1400):
    s = Svg(W, H)
    shell(s, 3, ["Прогоны", "Пересечение SMA 20/50", "run-0142"])
    R = D.RESULT_HONEST
    page_header(s, "Пересечение SMA 20/50",
                meta=[("Режим", "честный"), ("Датасет", "ds-0007"), ("Период", D.RUN_CONFIG["period"]),
                      ("Капитал", D.RUN_CONFIG["capital"]), ("Запущен", "05.10.2026 14:22, Денис М.")],
                title_extra=[("mono", "run-0142"), ("badge", ("Валиден", "valid", True))],
                buttons=[("Скачать отчёт", "outline", "download"), ("Сравнить с наивным", "secondary", "compare")])

    # --- полоса: светофор + KPI ---
    y = 148
    s.rect(X0, y, CW, 108, SURF, rx=12, stroke=BORDER)
    LW = 440
    T(s, X0 + 20, y + 26, "Честность прогона", 14, TEXT, 700)
    T(s, X0 + LW - 20, y + 26, "проверено движком при запуске", 12, TEXT3, anchor="end")
    seg_w, gap = 132, 8
    items = [("Данные", "ok", "ds-0007, хэш совпал"), ("Будущее", "ok", "0 ошибок, 0 пометок"),
             ("Издержки", "warn", "съели 62 % прибыли")]
    for i, (lab, st, verdict) in enumerate(items):
        sx = X0 + 20 + i * (seg_w + gap)
        s.rect(sx, y + 46, seg_w, 10, LIGHT[st], rx=3)
        T(s, sx, y + 72, lab, 13, TEXT, 700)
        T(s, sx, y + 90, verdict, 12, TEXT2, maxw=seg_w)
    s.line(X0 + LW, y + 16, X0 + LW, y + 92, DIV)
    kpis = [("Доходность за период", R["total"], POS, "1 316 000 ₽ на конец"),
            ("Без издержек", D.RESULT_NAIVE["total"], TEXT, "наивный, run-0141"),
            ("Макс. просадка", R["max_dd"], NEG, R["dd_days"] + " под водой"),
            ("Sharpe", R["sharpe"], TEXT, "Sortino " + R["sortino"])]
    kw = (CW - LW) / 4
    for i, (lab, val, col, sub) in enumerate(kpis):
        kx = X0 + LW + i * kw + 20
        if i:
            s.line(X0 + LW + i * kw, y + 16, X0 + LW + i * kw, y + 92, DIV)
        T(s, kx, y + 26, lab, 13, TEXT2, maxw=kw - 28)
        T(s, kx, y + 58, val, 28, col, 700)
        T(s, kx, y + 88, sub, 12, TEXT2, maxw=kw - 28)

    LX, LWc = X0, 752
    RX, RWc = X0 + 752 + 16, CW - 752 - 16

    # --- левая колонка: предупреждения ---
    y = 272
    fh = 52 + 2 * 48 + 8
    panel(s, LX, y, LWc, fh, "Предупреждения", len(D.FLAGS))
    T(s, LX + LWc - 16, y + 26, "Прогон валиден, пометки не блокируют сравнение", 12, TEXT3, anchor="end")
    colw = (LWc - 48) / 2
    for i, f in enumerate(D.FLAGS):
        fx = LX + 16 + (i % 2) * (colw + 16)
        fy = y + 52 + (i // 2) * 48
        col = WARN_C if f["level"] == "warning" else "#70B6F6"
        icn = "warn" if f["level"] == "warning" else "info"
        s.icon(icn, fx, fy + 2, "#C79A00" if f["level"] == "warning" else "#3D8FD9")
        P(s, fx + 26, fy, f["text"], colw - 28, 13, 18, TEXT, max_lines=2)
    y += fh + 16

    # --- капитал и просадка ---
    _bg1 = len(s.body)
    T(s, LX + 16, y + 26, "Капитал и просадка", 16, TEXT, 700)
    lx = LX + LWc - 16
    for label, col, dash in (("IMOEX", IMOEX_C, None), ("Наивный, без издержек", NAIVE, "4 3"), ("Честный", ACCENT, None)):
        tw = measure(label, 13)
        T(s, lx, y + 26, label, 13, TEXT2, anchor="end")
        s.line(lx - tw - 28, y + 26, lx - tw - 8, y + 26, col, sw=2, dash=dash)
        lx -= tw + 44
    px, pw = LX + 64, LWc - 64 - 72
    ptop, ph = y + 64, 284
    vmin, vmax = 0.6, 2.0
    for k in range(8):
        v = 0.6 + 0.2 * k
        gy = ptop + ph - ph * (v - vmin) / (vmax - vmin)
        s.line(px, gy, px + pw, gy, DIV)
        T(s, px - 10, gy, ru(v) + " млн", 12, TEXT3, anchor="end")
    stress_marks(s, px, ptop, pw, ph)
    s.line(px, ptop + ph - ph * (1 - vmin) / (vmax - vmin), px + pw, ptop + ph - ph * (1 - vmin) / (vmax - vmin), "#C9CBD3", dash="2 3")
    date_series(s, D.EQUITY_IMOEX, px, ptop, pw, ph, vmin, vmax, IMOEX_C, sw=1.4)
    date_series(s, D.EQUITY_NAIVE, px, ptop, pw, ph, vmin, vmax, NAIVE, sw=1.4, dash="4 3")
    pts = date_series(s, D.EQUITY_HONEST, px, ptop, pw, ph, vmin, vmax, ACCENT, sw=2, area=ACCENT)
    ex, ey = pts[-1]
    s.circle(ex, ey, 3.5, fill=ACCENT, stroke=SURF, sw=1.5)
    # подписи концов
    for ser, txt, col in ((D.EQUITY_NAIVE, "+84,2 %", NAIVE), (D.EQUITY_HONEST, "+31,6 %", ACCENT), (D.EQUITY_IMOEX, "+9,4 %", "#8C8FA3")):
        yy = ptop + ph - ph * (ser[-1] - vmin) / (vmax - vmin)
        T(s, px + pw + 10, yy, txt, 12, col, 700)
    # просадка
    utop, uh = ptop + ph + 36, 96
    T(s, px, utop - 14, "Просадка честного прогона от предыдущего максимума", 12, TEXT2)
    s.line(px, utop, px + pw, utop, "#C9CBD3")
    for v in (-0.15, -0.30):
        gy = utop + uh * (v / -0.30)
        s.line(px, gy, px + pw, gy, DIV)
        T(s, px - 10, gy, ru(v * 100, 0).replace("-", "−") + " %", 12, TEXT3, anchor="end")
    T(s, px - 10, utop, "0 %", 12, TEXT3, anchor="end")
    stress_marks(s, px, utop, pw, uh, labels=False)
    dd = D.drawdown(D.EQUITY_HONEST)
    n = len(dd)
    idx = list(range(0, n, 3)) + [n - 1]
    pp = [(dx(D.DAYS[i], px, pw), utop + uh * (dd[i] / -0.30)) for i in idx]
    s.path(f"M{px:.1f} {utop:.1f} L" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pp) + f" L{px + pw:.1f} {utop:.1f} Z", fill=NEG, fill_opacity=0.12)
    s.path("M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pp), stroke=NEG, sw=1.2)
    imin = dd.index(min(dd))
    mx, my = dx(D.DAYS[imin], px, pw), utop + uh * (dd[imin] / -0.30)
    s.circle(mx, my, 3, fill=NEG)
    T(s, mx + 8, my - 2, "−27,4 %, 214 дней под водой", 12, NEG, 700)
    year_axis(s, px, pw, utop + uh + 18)
    eh = utop + uh + 44 - y
    insert_panel(s, _bg1, LX, y, LWc, eh)
    y += eh + 16

    # --- свечи SBER ---
    data = D.candles()
    sub = [d for d in D.DAYS if d >= date(2025, 9, 1)]
    _bg2 = len(s.body)
    T(s, LX + 16, y + 26, "SBER: сделки стратегии", 16, TEXT, 700)
    T(s, LX + LWc - 16, y + 26, "01.09.2025 — 31.12.2025, дневные бары", 13, TEXT2, anchor="end")
    cx0, cwid = LX + 20, LWc - 20 - 64
    ctop, chh = y + 64, 200
    lo = min(c["l"] for c in data)
    hi = max(c["h"] for c in data)
    for k in range(5):
        v = 265 + k * 10
        if lo - 2 <= v <= hi + 2:
            gy = ctop + chh - chh * (v - lo) / (hi - lo)
            s.line(cx0, gy, cx0 + cwid, gy, DIV)
            T(s, cx0 + cwid + 10, gy, f"{v},00", 12, TEXT3)
    geo = s.candles(data, cx0, ctop, cwid, chh, UP, DOWN, gap=0.35)
    vtop, vh = ctop + chh + 12, 36
    for i, c in enumerate(data):
        bh = vh * c["v"] / 1.6
        s.rect(geo["X"](i) - geo["bw"] * 0.32, vtop + vh - bh, geo["bw"] * 0.64, bh, "#DADCE3" if i != 72 else "#F3B0A8")
    T(s, cx0 + cwid + 10, vtop + vh / 2, "Объём", 12, TEXT3)
    months = [("сен", 9), ("окт", 10), ("ноя", 11), ("дек", 12)]
    for name, m in months:
        i0 = next(i for i, d in enumerate(sub) if d.month == m)
        T(s, geo["X"](round(i0 * 89 / 86)), vtop + vh + 16, name, 12, TEXT3, anchor="middle")

    def tdate(i):
        return sub[min(len(sub) - 1, round(i * 86 / 89))].strftime("%d.%m.%Y")

    def glyph(kind, gx, gy):
        if kind == "buy":
            s.path(f"M{gx - 6} {gy + 5} L{gx + 6} {gy + 5} L{gx} {gy - 5} Z", fill=POS)
        elif kind == "partial":
            s.path(f"M{gx - 6} {gy + 5} L{gx + 6} {gy + 5} L{gx} {gy - 5} Z", fill=SURF, stroke=POS, sw=1.6)
        elif kind == "sell":
            s.path(f"M{gx - 6} {gy - 5} L{gx + 6} {gy - 5} L{gx} {gy + 5} Z", fill=NEG)
        else:
            s.circle(gx, gy, 6, fill=SURF, stroke=TEXT2, sw=1.4)
            s.path(f"M{gx - 2.5} {gy - 2.5} L{gx + 2.5} {gy + 2.5} M{gx + 2.5} {gy - 2.5} L{gx - 2.5} {gy + 2.5}", stroke=TEXT2, sw=1.4)

    short = {"buy": "Покупка", "partial": "Частично", "sell": "Продажа", "rejected": "Отказ"}

    def chip(cx_, cy_, txt, col):
        tw = measure(txt, 12, 700) + 12
        s.rect(cx_ - tw / 2, cy_ - 10, tw, 20, SURF, rx=6, stroke=BORDER)
        T(s, cx_, cy_, txt, 12, col, 700, anchor="middle")
    for i, kind, label in D.TRADE_MARKERS:
        c = data[i]
        gx = geo["X"](i)
        if kind in ("buy", "partial"):
            gy = geo["Y"](c["l"]) + 12
            glyph(kind, gx, gy)
            chip(gx, gy + 20, short[kind], POS)
        else:
            gy = geo["Y"](c["h"]) - 12
            glyph(kind, gx, gy)
            chip(gx, gy - 20, short[kind], NEG if kind == "sell" else TEXT2)
    ly = vtop + vh + 36
    s.line(LX + 16, ly, LX + LWc - 16, ly, DIV)
    T(s, LX + 48, ly + 18, "Дата", 12, TEXT2)
    T(s, LX + 160, ly + 18, "Заявка", 12, TEXT2)
    T(s, LX + LWc - 16, ly + 18, "Исполнение", 12, TEXT2, anchor="end")
    ly += 36
    exec_note = {"buy": "полностью", "partial": "57 % объёма", "sell": "полностью", "rejected": "не исполнена"}
    for i, kind, label in D.TRADE_MARKERS:
        s.line(LX + 16, ly, LX + LWc - 16, ly, DIV)
        glyph(kind, LX + 28, ly + 18)
        T(s, LX + 48, ly + 18, tdate(i), 13, TEXT2, mono=True)
        T(s, LX + 160, ly + 18, label, 14, TEXT, maxw=420)
        T(s, LX + LWc - 16, ly + 18, exec_note[kind], 13, TEXT2 if kind != "rejected" else NEG, anchor="end")
        ly += 36
    ch = ly + 4 - y
    insert_panel(s, _bg2, LX, y, LWc, ch)
    left_bottom = y + ch

    # --- правая колонка: метрики ---
    y = 272
    rows = [("Итоговый капитал", R["final"], True), ("Доходность до / после издержек", f'{R["gross"]} / {R["net"]}', True),
            ("CAGR", R["cagr"], False), ("Макс. просадка", f'{R["max_dd"]}, {R["dd_days"]}', False),
            ("Период просадки", R["dd_period"], False), ("Волатильность, годовая", R["vol"], False),
            ("Sharpe / Sortino", f'{R["sharpe"]} / {R["sortino"]}', False), ("Оборот", R["turnover"], False),
            ("Сделки, win rate", f'{R["trades"]}, {R["win_rate"]}', False), ("Частичные / отказы", f'{R["partial"]} / {R["rejected"]}', False),
            ("Концентрация HHI", R["hhi"], False), ("Крупнейшая позиция", R["top_position"], False),
            ("IMOEX за период", R["benchmark"], False), ("Против IMOEX", R["vs_benchmark"], True)]
    mh = 52 + len(rows) * 28 + 6
    panel(s, RX, y, RWc, mh, "Метрики")
    for i, (lab, val, strong) in enumerate(rows):
        kv(s, RX + 16, y + 52 + i * 28 + 13, RWc - 32, lab, val, TEXT, 700 if strong else 400, line=i < len(rows) - 1)
    y += mh + 16

    # --- издержки ---
    rows_h = []
    lab_w = RWc - 32 - 84
    for lab, pp_, rub in D.DELTA_BREAKDOWN:
        rows_h.append(nlines(lab, lab_w, 13) * 18 + 22)
    ch2 = 52 + sum(rows_h) + 92
    panel(s, RX, y, RWc, ch2, "Издержки и задержка")
    T(s, RX + RWc - 16, y + 26, "−52,6 п.п.", 14, NEG, 700, anchor="end")
    cy = y + 52
    for (lab, pp_, rub), rh in zip(D.DELTA_BREAKDOWN, rows_h):
        bot = P(s, RX + 16, cy, lab, lab_w, 13, 18, TEXT)
        T(s, RX + RWc - 16, cy + 9, ru(pp_).replace("-", "−") + " п.п.", 13, TEXT, 700, anchor="end")
        bw_ = (RWc - 32 - 84) * abs(pp_) / 21.4
        s.rect(RX + 16, bot + 4, RWc - 32 - 84, 4, DIV, rx=2)
        s.rect(RX + 16, bot + 4, bw_, 4, NEG if rub else ACCENT, rx=2)
        T(s, RX + RWc - 16, bot + 6, rub or "без денег", 12, TEXT2 if rub else TEXT3, anchor="end")
        cy += rh
    s.line(RX + 16, cy + 4, RX + RWc - 16, cy + 4, DIV)
    T(s, RX + 16, cy + 24, "Издержки в деньгах", 13, TEXT2)
    T(s, RX + RWc - 16, cy + 24, D.COSTS_TOTAL, 14, TEXT, 700, anchor="end")
    P(s, RX + 16, cy + 40, "Задержка и лимит ликвидности не списывают деньги, но ухудшают цену и объём сделок.", RWc - 32, 12, 16, TEXT2)
    y += ch2 + 16

    # --- воспроизводимость ---
    rp = D.REPRO
    rrows = [("Прогон", rp["run"]), ("Датасет", rp["dataset"]), ("Стратегия", rp["strategy"]),
             ("Движок", rp["engine"].replace("движок ", "")), ("Seed", rp["seed"]), ("Запущен", rp["started"]), ("Длительность", rp["duration"])]
    rh_ = left_bottom - y
    panel(s, RX, y, RWc, rh_, "Воспроизводимость")
    s.icon("lock", RX + RWc - 32, y + 18, TEXT3)
    for i, (lab, val) in enumerate(rrows):
        kv(s, RX + 16, y + 52 + i * 28 + 13, RWc - 32, lab, val, mono=True, vsize=12, line=i < len(rrows) - 1)
    hy = y + 52 + len(rrows) * 28 + 8
    hy = P(s, RX + 16, hy, "Повтор с теми же данными, кодом и seed должен дать тот же результат до копейки.", RWc - 32, 12, 16, TEXT2)
    button(s, RX + 16, y + rh_ - 48, "Воспроизвести", "secondary", icon="repeat", w=RWc - 32)
    if hy > y + rh_ - 56:
        OVERFLOWS.append(f"E4 repro panel too short: {hy} > {y + rh_ - 56}")
    print("E4 left bottom", left_bottom, "right needs", hy + 56)
    disclaimer(s, left_bottom + 32)
    if H != left_bottom + 56:
        return e4(left_bottom + 56)
    return s


# =========================================================================================
# E2 — Стратегия
# =========================================================================================
KW = {"strategy", "universe", "capital", "let", "when", "buy", "sell", "all", "equity", "RUB"}
FN = {"sma", "drawdown", "crosses_above", "crosses_below"}


def code_line(s, x, cy, line, size=13):
    cw = measure("M", size, mono=True)
    toks = re.findall(r'//.*|"[^"]*"|\d[\d_]*%?|[A-Za-z_]\w*|->|\s+|.', line)
    col = 0
    for t in toks:
        if not t.strip():
            col += len(t)
            continue
        if t.startswith("//"):
            c, w = TEXT3, 400
        elif t.startswith('"'):
            c, w = "#0F8A5F", 400
        elif t[0].isdigit() or (t.startswith("-") and len(t) > 1):
            c, w = "#C2410C", 400
        elif t in KW:
            c, w = ACTION, 700
        elif t in FN:
            c, w = MOM_C, 400
        elif t == "->":
            c, w = TEXT3, 400
        else:
            c, w = TEXT, 400
        T(s, x + col * cw, cy, t, size, c, w, mono=True)
        col += len(t)


def e2():
    H = 924
    s = Svg(W, H)
    shell(s, 1, ["Стратегии", "Пересечение SMA 20/50"])
    page_header(s, "Пересечение SMA 20/50",
                meta=[("Версия", "4 из 4"), ("Изменена", "04.10.2026, Денис М."), ("Прогонов", "12"), ("Вселенная", "6 акций MOEX")],
                title_extra=[("badge", ("Проверка пройдена", "valid", True))],
                buttons=[("Сохранить версию", "secondary", None), ("Проверить код", "outline", "check")])
    top, bottom = 148, H - 48
    disclaimer(s, H - 18)
    # --- список стратегий ---
    x, w = X0, 272
    lh = 52 + 44 + len(D.STRATEGIES) * 76 + 4
    panel(s, x, top, w, lh, "Стратегии", len(D.STRATEGIES))
    icon_btn(s, x + w - 48, top + 10, "plus")
    s.rect(x + 16, top + 52, w - 32, 32, BG, rx=10)
    s.icon("search", x + 28, top + 60, TEXT3)
    T(s, x + 52, top + 68, "Найти стратегию", 13, TEXT3)
    ry = top + 96
    for i, st in enumerate(D.STRATEGIES):
        if i == 0:
            s.rect(x + 8, ry, w - 16, 72, SEL_BG, rx=10)
            s.rect(x + 8, ry + 16, 3, 40, ACCENT, rx=1.5)
        T(s, x + 20, ry + 20, st["name"], 14, TEXT, 700, maxw=w - 64)
        T(s, x + w - 20, ry + 20, str(st["runs"]), 12, TEXT3, anchor="end")
        P(s, x + 20, ry + 30, st["desc"], w - 40, 12, 16, TEXT2, max_lines=2)
        if 0 < i < len(D.STRATEGIES) - 1:
            s.line(x + 20, ry + 74, x + w - 20, ry + 74, DIV)
        ry += 76
    # справочник DSL
    ref = [("sma(x, n)", "простая средняя за n баров", TEXT2),
           ("a crosses_above b", "пересечение снизу вверх", TEXT2),
           ("drawdown(position)", "просадка открытой позиции", TEXT2),
           ("buy 20% equity", "заявка на долю капитала", TEXT2),
           ("close[1]", "закрытие предыдущего бара", TEXT2),
           ("close[+1]", "запрещено: бар ещё не наступил", NEG)]
    ry = top + lh + 16
    panel(s, x, ry, w, bottom - ry, "Справочник DSL")
    cy = ry + 52
    for tok, desc, col in ref:
        code_line(s, x + 16, cy + 8, tok, 12)
        T(s, x + 16, cy + 27, desc, 12, col, maxw=w - 32)
        cy += 42

    # --- редактор ---
    ex, ew = X0 + 272 + 16, 496
    eh = 48 + 12 + len(D.DSL_MAIN) * 24 + 12 + 44
    s.rect(ex, top, ew, eh, SURF, rx=12, stroke=BORDER)
    tabs(s, ex + 16, top, ["Код", "Параметры", "Версии"], 0)
    T(s, ex + ew - 16, top + 24, f"Строка 8, столбец {len(D.DSL_MAIN[7]) + 1}", 12, TEXT3, anchor="end")
    s.line(ex, top + 48, ex + ew, top + 48, DIV)
    cy0 = top + 48
    s.rect(ex + 1, cy0 + 0.5, 44, 12 + len(D.DSL_MAIN) * 24 + 12, "#FAFAFB")
    s.line(ex + 45, cy0, ex + 45, cy0 + 24 + len(D.DSL_MAIN) * 24, DIV)
    for i, ln in enumerate(D.DSL_MAIN):
        ly = cy0 + 12 + i * 24 + 12
        if i == 7:
            s.rect(ex + 46, ly - 12, ew - 47, 24, "#F7F8FC")
        T(s, ex + 34, ly, str(i + 1), 12, TEXT3 if i != 7 else TEXT, mono=True, anchor="end")
        code_line(s, ex + 60, ly, ln, 13)
    cw_ = measure("M", 13, mono=True)
    s.rect(ex + 60 + len(D.DSL_MAIN[7]) * cw_ + 1, cy0 + 12 + 7 * 24 + 4, 1.5, 16, ACCENT)
    sy = cy0 + 24 + len(D.DSL_MAIN) * 24
    s.line(ex, sy, ex + ew, sy, DIV)
    s.icon("check", ex + 16, sy + 14, POS)
    T(s, ex + 40, sy + 22, "Чтения будущего нет: 10 строк, 0 ошибок, 0 пометок", 13, TEXT, maxw=ew - 56)
    # прогоны стратегии
    py = top + eh + 16
    panel(s, ex, py, ew, bottom - py, "Прогоны этой стратегии")
    T(s, ex + ew - 16, py + 26, "Все 12 прогонов", 13, ACTION, 700, anchor="end")
    cols = [("Прогон", 0), ("Режим", 92), ("Честность", 214), ("Статус", 300), ("Результат", ew - 32)]
    hy = py + 52
    for name, off in cols:
        T(s, ex + 16 + off, hy + 14, name, 12, TEXT2, anchor="end" if name == "Результат" else "start")
    s.line(ex + 16, hy + 28, ex + ew - 16, hy + 28, DIV)
    ry = hy + 28
    for r in [x for x in D.RUNS if x["strategy"] == "SMA 20/50"]:
        cy = ry + 20
        T(s, ex + 16, cy, r["id"], 13, ACTION, mono=True)
        T(s, ex + 16 + 92, cy, r["mode"], 13, TEXT, maxw=116)
        light(s, ex + 16 + 214, cy, honesty(r["id"]), seg=18, h=8, gap=3)
        status_badge(s, ex + 16 + 300, cy, r["status"])
        res = r["result"]
        rc = TEXT2 if r["mode"] == "наивный" else POS if res.startswith("+") else NEG if res.startswith("−") else TEXT3
        T(s, ex + ew - 16, cy, res, 14, rc, 700, anchor="end")
        s.line(ex + 16, ry + 40, ex + ew - 16, ry + 40, DIV)
        ry += 40
    light_legend(s, ex + 16, bottom - 30, 12, compact=True)

    # --- проверка чтения будущего ---
    cx, cwp = ex + ew + 16, X1 - (ex + ew + 16)
    panel(s, cx, top, cwp, bottom - top, "Проверка чтения будущего")
    iy = P(s, cx + 16, top + 44, "Анализатор смотрит на каждую строку: известны ли эти данные в момент решения.", cwp - 32, 13, 18, TEXT2)
    levels = [("ok", "OK", "данные известны на момент решения"),
              ("warning", "Подозрительно", "прогон получит пометку"),
              ("error", "Ошибка", "прогон невалиден")]
    lvl_c = {"ok": OK_C, "warning": WARN_C, "error": BAD_C}
    lvl_kind = {"ok": "valid", "warning": "warning", "error": "invalid"}
    iy += 8
    s.rect(cx + 16, iy, cwp - 32, 3 * 26 + 12, ALT, rx=10)
    for i, (lv, name, mean) in enumerate(levels):
        ly = iy + 6 + i * 26 + 13
        s.rect(cx + 28, ly - 4, 14, 8, lvl_c[lv], rx=2)
        nw = T(s, cx + 52, ly, name, 13, TEXT, 700)
        T(s, cx + 52 + nw + 8, ly, mean, 12, TEXT2, maxw=cwp - 32 - 52 - nw - 16)
    iy += 3 * 26 + 12 + 20
    T(s, cx + 16, iy, "Находки по версиям", 14, TEXT, 700)
    iy += 16
    notes = {"ok": None,
             "warning": ("Исправлено в версии 4: adj_close заменён на close", "run-0140 получил пометку"),
             "error": ("Исправлено в версии 3", "run-0139 признан невалидным")}
    vers = {"ok": "версия 4, текущая", "warning": "версия 3", "error": "версия 2"}
    names = {"ok": "OK", "warning": "Подозрительно", "error": "Ошибка"}
    inner = cwp - 32 - 24
    for chk in D.LOOKAHEAD_CHECKS:
        lv = chk["level"]
        msg_l = nlines(chk["msg"], inner, 13, 400)
        note_l = nlines(notes[lv][0], inner - 18, 12, 700) if notes[lv] else 0
        hh = 12 + 22 + 8 + 28 + 8 + msg_l * 18 + (note_l * 16 + 8 if notes[lv] else 0) + 12
        s.rect(cx + 16, iy, cwp - 32, hh, SURF, rx=10, stroke=BORDER)
        s.rect(cx + 16, iy + 12, 3, hh - 24, lvl_c[lv], rx=1.5)
        by = iy + 12 + 11
        bw_ = badge(s, cx + 28, by, names[lv], lvl_kind[lv], dot=True)
        T(s, cx + 28 + bw_ + 8, by, f'Строка {chk["line"]}, {vers[lv]}', 12, TEXT2)
        sy_ = iy + 12 + 22 + 8
        s.rect(cx + 28, sy_, inner, 28, ALT, rx=6)
        code_line(s, cx + 36, sy_ + 14, fit(chk["code"], inner - 16, 11, mono=True, where="E2 snippet"), 11)
        my = P(s, cx + 28, sy_ + 28 + 8, chk["msg"], inner, 13, 18, TEXT)
        if notes[lv]:
            s.icon("check", cx + 28, my + 4, POS, s=14, sw=1.8)
            P(s, cx + 46, my + 4, notes[lv][0], inner - 18, 12, 16, POS, 700)
        iy += hh + 8
    if iy > bottom:
        OVERFLOWS.append(f"E2 check panel overflow {iy} > {bottom}")
    return s


# =========================================================================================
# E1 — Датасеты
# =========================================================================================
DS_STATUS = {"актуальный": "valid", "заменён ds-0007": "neutral", "устаревшая схема": "warning", "после MVP": "info"}


def e1():
    H = 968
    s = Svg(W, H)
    shell(s, 0, ["Датасеты"])
    page_header(s, "Датасеты",
                meta=[("Снапшотов", "5"), ("Источники", "MOEX ISS, ЦБ РФ"), ("Правило", "снапшот не меняется, прогон ссылается на хэш")],
                buttons=[("Загрузить новый снапшот", "accent", "download")])
    y = 148
    rows_n = len(D.DATASETS)
    th = 52 + 36 + rows_n * 56 + 4
    panel(s, X0, y, CW, th, "Снапшоты", rows_n)
    segmented(s, X1 - 16 - 300, y + 10, ["Все источники", "MOEX ISS", "ЦБ РФ"], 0)
    cols = [("Снапшот", 144), ("Тикеры", 176), ("Интервал", 72), ("Период", 156), ("Получен", 120), ("Хэш", 92),
            ("Схема", 48), ("Строк", 64), ("Используется", 100), ("Статус", 140)]
    xs, cx = [], X0 + 16
    for name, w in cols:
        xs.append(cx)
        cx += w
    hy = y + 52
    for (name, w), x in zip(cols, xs):
        if name == "Строк":
            T(s, x + w - 16, hy + 18, name, 12, TEXT2, anchor="end")
        else:
            T(s, x, hy + 18, name, 12, TEXT2)
            if name == "Получен":
                s.icon("chevron-down", x + measure(name, 12) + 4, hy + 12, TEXT2, s=12)
    s.line(X0 + 16, hy + 36, X1 - 16, hy + 36, DIV)
    ry = hy + 36
    for i, d in enumerate(D.DATASETS):
        mvp = d["status"] == "после MVP"
        if i == 0:
            s.rect(X0 + 8, ry + 2, CW - 16, 52, SEL_BG, rx=8)
        c1 = TEXT3 if mvp else TEXT
        c2 = TEXT3 if mvp else TEXT2
        T(s, xs[0], ry + 19, d["id"], 13, TEXT3 if mvp else ACTION, 700, mono=True)
        T(s, xs[0], ry + 38, d["source"], 12, c2, maxw=cols[0][1] - 4)
        P(s, xs[1], ry + 10, d["tickers"], cols[1][1] - 16, 13, 18, c1, max_lines=2)
        T(s, xs[2], ry + 28, d["interval"], 13, c1)
        T(s, xs[3], ry + 28, d["period"], 13, c1, maxw=cols[3][1] - 6)
        T(s, xs[4], ry + 28, d["fetched"], 13, c1)
        T(s, xs[5], ry + 28, d["sha"], 12, c2, mono=True)
        T(s, xs[6], ry + 28, d["schema"], 13, c1)
        T(s, xs[7] + cols[7][1] - 16, ry + 28, d["rows"], 13, c1, anchor="end")
        T(s, xs[8], ry + 28, f'{d["used_in"]} прогонов' if d["used_in"] else "—", 13, ACTION if d["used_in"] else TEXT3)
        badge(s, xs[9], ry + 28, d["status"], DS_STATUS[d["status"]], dot=not mvp)
        if i < rows_n - 1:
            s.line(X0 + 16, ry + 56, X1 - 16, ry + 56, DIV)
        ry += 56
    # --- карточка выбранного снапшота ---
    y += th + 16
    bh = H - 24 - y
    lw = 600
    ds = D.DATASET_CURRENT
    panel(s, X0, y, lw, bh)
    tw = T(s, X0 + 16, y + 26, ds["id"], 16, TEXT, 700, mono=True)
    badge(s, X0 + 16 + tw + 10, y + 26, "актуальный", "valid", dot=True)
    T(s, X0 + lw - 16, y + 26, "Используется в 9 прогонах", 13, ACTION, 700, anchor="end")
    grid = [("Источник", ds["source"]), ("Интервал", "D1, дневные бары"), ("Период", ds["period"]), ("Получен", ds["fetched"]),
            ("Хэш", "sha " + ds["sha"]), ("Версия схемы", ds["schema"]), ("Строк", ds["rows"]), ("Тикеры", "6 акций + IMOEX")]
    gw = (lw - 32 - 24) / 2
    for i, (lab, val) in enumerate(grid):
        gx = X0 + 16 + (i % 2) * (gw + 24)
        gy = y + 52 + (i // 2) * 28 + 12
        kv(s, gx, gy, gw, lab, val, mono=lab == "Хэш", vsize=12 if lab == "Хэш" else 13)
    fy = y + 52 + 4 * 28 + 16
    T(s, X0 + 16, fy + 10, "Поля и момент доступности", 14, TEXT, 700)
    fy += 28
    T(s, X0 + 16, fy + 12, "Поле", 12, TEXT2)
    T(s, X0 + 124, fy + 12, "Когда значение известно", 12, TEXT2)
    T(s, X0 + lw - 16, fy + 12, "Можно использовать", 12, TEXT2, anchor="end")
    s.line(X0 + 16, fy + 26, X0 + lw - 16, fy + 26, DIV)
    fy += 26
    use = {"open": ("в решении дня t", "valid"), "adj_close": ("запрещено", "invalid")}
    for fld, when in D.DATASET_FIELDS:
        lab, kind = use.get(fld, ("для заявок на t+1", "accent"))
        T(s, X0 + 16, fy + 16, fld, 13, NEG if kind == "invalid" else TEXT, mono=True)
        T(s, X0 + 124, fy + 16, when, 13, TEXT if kind != "invalid" else NEG, maxw=lw - 124 - 152)
        badge(s, X0 + lw - 16, fy + 16, lab, kind, align="end")
        fy += 32
        if fld != "adj_close":
            s.line(X0 + 16, fy, X0 + lw - 16, fy, DIV)
    if fy > y + bh - 8:
        OVERFLOWS.append(f"E1 detail overflow {fy} > {y + bh}")
    # --- торговый календарь ---
    cx0, cw0 = X0 + lw + 16, CW - lw - 16
    panel(s, cx0, y, cw0, bh, "Торговый календарь")
    segmented(s, cx0 + cw0 - 16 - 236, y + 10, ["2020", "2021", "2022", "2023"], 2)
    months = [(2, "Февраль 2022"), (3, "Март 2022"), (4, "Апрель 2022")]
    mw = (cw0 - 32 - 32) / 3
    cell = mw / 7
    g0, g1 = date(2022, 2, 28), date(2022, 3, 23)
    import calendar
    for k, (m, name) in enumerate(months):
        mx = cx0 + 16 + k * (mw + 16)
        my = y + 52
        T(s, mx, my + 8, name, 13, TEXT, 700)
        for j, dname in enumerate(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]):
            T(s, mx + j * cell + cell / 2, my + 30, dname, 11, TEXT3, anchor="middle")
        first_wd, ndays = calendar.monthrange(2022, m)
        for dday in range(1, ndays + 1):
            pos = first_wd + dday - 1
            col, row = pos % 7, pos // 7
            ccx, ccy = mx + col * cell, my + 42 + row * 26
            dt = date(2022, m, dday)
            weekend = col >= 5
            gap = g0 <= dt <= g1 and not weekend
            if gap:
                s.rect(ccx + 1, ccy + 1, cell - 2, 22, BAD_C, rx=6, fill_opacity=0.14)
                fc, fw = "#C8160A", 700
            elif weekend:
                fc, fw = TEXT3, 400
            else:
                s.rect(ccx + 1, ccy + 1, cell - 2, 22, "#EEF0F3", rx=6)
                fc, fw = TEXT, 400
            if dt == date(2022, 2, 24):
                s.rect(ccx + 1.5, ccy + 1.5, cell - 3, 21, "none", rx=6, stroke=NEG, sw=1.5)
            T(s, ccx + cell / 2, ccy + 12, str(dday), 12, fc, fw, anchor="middle")
    ly = y + 52 + 42 + 6 * 26 + 12
    lx = cx0 + 16
    for kind, label in (("trade", "торги шли"), ("gap", "торгов не было"), ("stress", "24.02, стресс-событие"), ("we", "выходной")):
        if kind == "trade":
            s.rect(lx, ly - 7, 14, 14, "#EEF0F3", rx=4)
        elif kind == "gap":
            s.rect(lx, ly - 7, 14, 14, BAD_C, rx=4, fill_opacity=0.14)
        elif kind == "stress":
            s.rect(lx + 0.75, ly - 6.25, 12.5, 12.5, "none", rx=4, stroke=NEG, sw=1.5)
        else:
            s.rect(lx + 0.5, ly - 6.5, 13, 13, SURF, rx=4, stroke=FIELD)
        lx += 20 + T(s, lx + 20, ly, label, 12, TEXT2) + 20
    ny = ly + 20
    s.rect(cx0 + 16, ny, cw0 - 32, 52, BAD_C, rx=10, fill_opacity=0.06)
    s.icon("info", cx0 + 28, ny + 10, "#C8160A")
    P(s, cx0 + 52, ny + 8, f"{D.CALENDAR_GAP[0]} — {D.CALENDAR_GAP[1]} {D.CALENDAR_GAP[2]}. Прогоны пропускают 18 дней: заявки не исполняются, позиции не переоцениваются.",
      cw0 - 32 - 48, 12, 17, TEXT, max_lines=2)
    if ny + 52 > y + bh - 8:
        OVERFLOWS.append(f"E1 calendar overflow {ny + 52} > {y + bh}")
    return s


# =========================================================================================
# E3 — Настройка прогона
# =========================================================================================
def e3():
    H = 1176
    s = Svg(W, H)
    shell(s, 2, ["Прогоны", "Новый прогон"], new_run=False)
    page_header(s, "Новый прогон",
                meta=[("Стратегия", "Пересечение SMA 20/50, версия 4"), ("Код", "проверен, чтения будущего нет")],
                buttons=[("Сохранить как шаблон", "outline", None)])
    C = D.RUN_CONFIG
    LWc = 744
    RX, RWc = X0 + LWc + 16, CW - LWc - 16
    y = 148
    # 1. данные
    h1 = 52 + 44 + 12 + 44 + 20
    panel(s, X0, y, LWc, h1, "Данные и капитал")
    fw3 = (LWc - 32 - 24) / 3
    f = [("Стратегия", "SMA 20/50, версия 4", True, False, 1), ("Датасет", "ds-0007, MOEX ISS, D1", True, False, 1),
         ("Период", C["period"], True, False, 1), ("Капитал", C["capital"], False, False, 1),
         ("Бары в периоде", C["bars"], False, True, 2)]
    for i, (lab, val, sel, ro, span) in enumerate(f):
        fx = X0 + 16 + (i % 3) * (fw3 + 12)
        fy = y + 52 + (i // 3) * 56
        field(s, fx, fy, fw3 * span + 12 * (span - 1), lab, val, select=sel, readonly=ro)
    y += h1 + 16
    # 2. издержки
    h2 = 52 + 3 * 44 + 2 * 12 + 40 + 12
    panel(s, X0, y, LWc, h2, "Издержки и исполнение")
    T(s, X0 + LWc - 16, y + 26, "Честный прогон учитывает всё; наивный считается без этого блока", 12, TEXT3, anchor="end")
    fw2 = (LWc - 32 - 16) / 2
    cost = [("Комиссия брокера", "0,05", "% от оборота", None, False),
            ("Биржевой сбор", "0,01", "% от оборота", None, False),
            ("Спред", C["spread"], None, None, False),
            ("Проскальзывание", C["slippage"], None, None, False),
            ("Лимит ликвидности", "не больше 5 % объёма бара", None, "Остаток заявки исполняется частично или отклоняется", False),
            ("Задержка исполнения", "по open следующего бара, t+1", None, "В честном режиме задержку убрать нельзя", True)]
    for i, (lab, val, suf, hint, ro) in enumerate(cost):
        fx = X0 + 16 + (i % 2) * (fw2 + 16)
        fy = y + 52 + (i // 2) * 56
        field(s, fx, fy, fw2, lab, val, suffix=suf, hint=hint, readonly=ro, icon="lock" if ro else None)
    y += h2 + 16
    # 3. стресс
    cards_h = 196
    h3 = 52 + cards_h + 16
    panel(s, X0, y, LWc, h3, "Стресс-сценарий")
    tw = measure("Добавить стресс-прогон", 13)
    T(s, X0 + LWc - 16 - 44, y + 26, "Добавить стресс-прогон", 13, TEXT, anchor="end")
    toggle(s, X0 + LWc - 16 - 36, y + 26, True)
    cw3 = (LWc - 32 - 24) / 3
    for i, p in enumerate(D.STRESS_PRESETS):
        cx = X0 + 16 + i * (cw3 + 12)
        cy = y + 52
        sel = i == 0
        custom = p["name"] == "Свой сценарий"
        if sel:
            s.rect(cx + 1, cy + 1, cw3 - 2, cards_h - 2, SEL_BG, rx=10, stroke=ACCENT, sw=2)
        else:
            s.rect(cx + 0.5, cy + 0.5, cw3 - 1, cards_h - 1, SURF, rx=10, stroke=FIELD)
        s.circle(cx + 22, cy + 24, 7.5, fill=SURF, stroke=ACCENT if sel else FIELD, sw=1.5)
        if sel:
            s.circle(cx + 22, cy + 24, 4, fill=ACCENT)
        T(s, cx + 38, cy + 24, p["name"], 14, TEXT, 700)
        P(s, cx + 14, cy + 40, p["desc"], cw3 - 28, 12, 16, TEXT2, max_lines=2)
        params = [("Гэп по индексу", p["gap"]), ("Волатильность", p["vol"]), ("Объём торгов", p["volume"]), ("Проскальзывание", p["slip"])]
        for j, (lab, val) in enumerate(params):
            ry_ = cy + 92 + j * 26
            T(s, cx + 14, ry_, lab, 13, TEXT2)
            if custom:
                s.rect(cx + cw3 - 14 - 72, ry_ - 11, 72, 22, SURF, rx=6, stroke=FIELD)
                T(s, cx + cw3 - 14 - 64, ry_, val, 13, TEXT3)
            else:
                T(s, cx + cw3 - 14, ry_, val, 13, TEXT, 700, anchor="end")
            if j < 3:
                s.line(cx + 14, ry_ + 13, cx + cw3 - 14, ry_ + 13, DIV if not sel else "#DDE3F6")
    y += h3 + 16
    # 4. режим
    h4 = 52 + 64 + 64 + 12 + 44 + 24
    panel(s, X0, y, LWc, h4, "Режим и воспроизводимость")
    modes = [(True, "Наивный и честный прогон вместе", "Отчёт сразу покажет, сколько доходности съели издержки и задержка"),
             (False, "Walk-forward", C["walk_forward"] + ". Проверяет, держатся ли параметры на новых данных: 20 окон")]
    my = y + 52
    for on, name, hint in modes:
        toggle(s, X0 + 16, my + 20, on)
        T(s, X0 + 68, my + 18, name, 14, TEXT, 700)
        T(s, X0 + 68, my + 38, hint, 12, TEXT2, maxw=LWc - 68 - 16)
        my += 64
        s.line(X0 + 16, my - 6, X0 + LWc - 16, my - 6, DIV)
    field(s, X0 + 16, my + 6, fw2, "Seed генератора случайностей", C["seed"], icon="repeat", mono=True,
          hint="Одинаковые seed, датасет и код дают тот же результат")
    field(s, X0 + 16 + fw2 + 16, my + 6, fw2, "Правило остановки", C["stop_rule"], select=True)
    left_bottom = y + h4
    # --- сводка ---
    y = 148
    sh = 572
    panel(s, RX, y, RWc, sh, "Сводка запуска")
    iy = y + 52
    T(s, RX + 16, iy + 8, "Будет создано 3 прогона", 13, TEXT2)
    iy += 24
    runs = [("Наивный", "без издержек и задержки", NAIVE), ("Честный", "издержки, лимит ликвидности, open t+1", ACCENT),
            ("Стресс 24.02.2022", "честный прогон со сценарием", WARN_C)]
    for name, hint, col in runs:
        s.rect(RX + 16, iy + 6, 4, 32, col, rx=2)
        T(s, RX + 32, iy + 14, name, 14, TEXT, 700)
        T(s, RX + 32, iy + 32, hint, 12, TEXT2, maxw=RWc - 48)
        iy += 44
    iy += 8
    s.line(RX + 16, iy, RX + RWc - 16, iy, DIV)
    iy += 20
    T(s, RX + 16, iy, "Честность до запуска", 14, TEXT, 700)
    iy += 18
    segw = (RWc - 32 - 16) / 3
    for i, (lab, st, verdict) in enumerate((("Данные", "ok", "хэш 3f9a…c21e"), ("Будущее", "ok", "версия 4 чистая"), ("Издержки", "ok", "5 видов + t+1"))):
        sx = RX + 16 + i * (segw + 8)
        s.rect(sx, iy, segw, 8, LIGHT[st], rx=3)
        T(s, sx, iy + 24, lab, 13, TEXT, 700)
        T(s, sx, iy + 42, verdict, 12, TEXT2, maxw=segw)
    iy += 60
    s.line(RX + 16, iy, RX + RWc - 16, iy, DIV)
    iy += 6
    for i, (lab, val) in enumerate((("Датасет", "ds-0007"), ("Торговых дней", "1 545"), ("Движок", "0.3.1"), ("Seed", C["seed"]))):
        kv(s, RX + 16, iy + 14 + i * 28, RWc - 32, lab, val, mono=lab in ("Датасет", "Seed"), line=i < 3)
    iy += 4 * 28 + 16
    button(s, RX + 16, y + sh - 16 - 44 - 40, "Запустить прогон", "primary", h=44, icon="play", w=RWc - 32)
    P(s, RX + 16, y + sh - 16 - 32, "Параметры фиксируются в прогоне. Чтобы изменить их, запустите новый.", RWc - 32, 12, 16, TEXT2)
    if iy > y + sh - 16 - 44 - 48:
        OVERFLOWS.append(f"E3 summary overflow {iy}")
    # отличия от прошлого запуска
    y += sh + 16
    diffs = [("Стресс-сценарий", "добавлен 24.02.2022", True), ("Датасет и код", "без изменений", False),
             ("Издержки и исполнение", "без изменений", False), ("Seed", "тот же", False)]
    ph_ = 52 + 36 + len(diffs) * 28 + 40
    panel(s, RX, y, RWc, ph_, "Отличия от прошлого запуска")
    s.rect(RX + 16, y + 52, RWc - 32, 36, ALT, rx=8)
    T(s, RX + 28, y + 70, "run-0142", 13, ACTION, 700, mono=True)
    light(s, RX + 112, y + 70, honesty("run-0142"), seg=18)
    T(s, RX + RWc - 28, y + 70, "+31,6 %", 14, POS, 700, anchor="end")
    for i, (lab, val, strong) in enumerate(diffs):
        kv(s, RX + 16, y + 52 + 36 + 8 + i * 28 + 10, RWc - 32, lab, val, ACTION if strong else TEXT2, 700 if strong else 400, line=i < len(diffs) - 1)
    T(s, RX + 16, y + ph_ - 22, "Открыть отчёт run-0142", 13, ACTION, 700)
    print("E3 left", left_bottom, "right", y + ph_)
    return s


# =========================================================================================
# E5 — Сравнение
# =========================================================================================
HONEST_RUN = {"SMA 20/50": "run-0142", "Моментум 3М": "run-0138", "RSI-откат": "run-0136", "IMOEX": "run-0133"}
STRAT_C = {"SMA 20/50": ACCENT, "Моментум 3М": MOM_C, "RSI-откат": RSI_C, "IMOEX": IMOEX_C}


def e5():
    H = 1260
    s = Svg(W, H)
    shell(s, 4, ["Сравнение", "SMA 20/50: наивный и честный"])
    page_header(s, "Наивный и честный прогон",
                meta=[("Стратегия", "Пересечение SMA 20/50"), ("Прогоны", "run-0141 и run-0142"), ("Датасет", "ds-0007"), ("Период", D.RUN_CONFIG["period"])],
                buttons=[("Скачать сравнение", "outline", "download"), ("Добавить прогон", "outline", "plus")])
    LWc = 744
    RX, RWc = X0 + LWc + 16, CW - LWc - 16
    y = 148
    rh = 34
    wh = 52 + 28 + 8 * rh + 16 + 24
    panel(s, X0, y, LWc, wh, "Из чего складывается разница 52,6 п.п.")
    labw = 292
    bx0, bw = X0 + 16 + labw, LWc - 32 - labw - 132
    sc = lambda v: bx0 + bw * v / 90
    ay = y + 52 + 14
    for v in (0, 20, 40, 60, 80):
        T(s, sc(v), ay, f"{v} %", 11, TEXT3, anchor="middle")
        s.line(sc(v), ay + 12, sc(v), ay + 20 + 8 * rh, DIV)
    T(s, X0 + LWc - 16 - 60, ay, "п.п.", 11, TEXT3, anchor="end")
    T(s, X0 + LWc - 16, ay, "доля", 11, TEXT3, anchor="end")
    ry = y + 52 + 28
    rows = [("Наивный прогон", 84.2, 0, None, "base")]
    cum = 84.2
    for lab, d, rub in D.DELTA_BREAKDOWN:
        rows.append((lab, d, cum, rub, "step"))
        cum += d
    rows.append(("Честный прогон", 31.6, 0, None, "end"))
    prev_x = None
    for lab, v, start, rub, kind in rows:
        cy = ry + rh / 2
        strong = kind != "step"
        T(s, X0 + 16, cy, lab, 13, TEXT, 700 if strong else 400, maxw=labw - 12)
        if kind == "base":
            s.rect(sc(0), cy - 9, sc(84.2) - sc(0), 18, NAIVE, rx=4, fill_opacity=0.35)
            T(s, X0 + LWc - 16 - 60, cy, "+84,2 %", 13, TEXT, 700, anchor="end")
            prev_x = sc(84.2)
        elif kind == "end":
            s.rect(sc(0), cy - 9, sc(31.6) - sc(0), 18, ACCENT, rx=4)
            T(s, X0 + LWc - 16 - 60, cy, "+31,6 %", 13, POS, 700, anchor="end")
            s.line(prev_x, cy - rh + 9, prev_x, cy - 9, TEXT3, dash="2 2")
        else:
            a, b = sc(start + v), sc(start)
            s.line(prev_x, cy - rh + 9, prev_x, cy - 6, TEXT3, dash="2 2")
            s.rect(a, cy - 6, b - a, 12, NEG if rub else ACCENT, rx=3, fill_opacity=0.85 if rub else 0.55)
            prev_x = a
            T(s, X0 + LWc - 16 - 60, cy, ru(v).replace("-", "−"), 13, TEXT, 700, anchor="end")
            T(s, X0 + LWc - 16, cy, f"{round(abs(v) / 52.6 * 100)} %", 13, TEXT2, anchor="end")
        if kind == "step" or kind == "base":
            s.line(X0 + 16, ry + rh, X0 + LWc - 16, ry + rh, DIV)
        ry += rh
    ly = ry + 20
    lx = X0 + 16
    for col, op, lab in ((NEG, 0.85, "издержки в деньгах, всего " + D.COSTS_TOTAL), (ACCENT, 0.55, "исполнение: задержка и лимит ликвидности")):
        s.rect(lx, ly - 5, 14, 10, col, rx=2, fill_opacity=op)
        lx += 22 + T(s, lx + 22, ly, lab, 12, TEXT2) + 24
    # --- правая: два прогона ---
    panel(s, RX, y, RWc, wh, "Светофор и итог")
    colw = (RWc - 32 - 16) / 2
    runs = [("Наивный", "run-0141", D.RESULT_NAIVE, TEXT), ("Честный", "run-0142", D.RESULT_HONEST, POS)]
    for k, (name, rid, R, col) in enumerate(runs):
        cx = RX + 16 + k * (colw + 16)
        cy = y + 52
        nw = T(s, cx, cy + 8, name, 13, TEXT2)
        T(s, cx + nw + 6, cy + 8, rid, 12, TEXT3, mono=True)
        T(s, cx, cy + 40, R["total"], 28, col, 700)
        st = honesty(rid)
        sw_ = (colw - 8) / 3
        for i, (lab, ss) in enumerate(zip(("Данные", "Будущее", "Издержки"), st)):
            sx = cx + i * (sw_ + 4)
            if ss == "off":
                s.rect(sx + 0.5, cy + 66.5, sw_ - 1, 7, SURF, rx=2, stroke="#AEB1BF", dash="2 2")
            else:
                s.rect(sx, cy + 66, sw_, 8, LIGHT[ss], rx=2)
            T(s, sx, cy + 88, lab, 11, TEXT2, maxw=sw_)
        T(s, cx, cy + 108, "издержки не учтены" if k == 0 else "издержки > 50 % прибыли", 12, TEXT2 if k == 0 else "#7A5800", 700 if k else 400, maxw=colw)
        rows_ = [("Sharpe", R["sharpe"]), ("Sortino", R["sortino"]), ("Макс. просадка", R["max_dd"]), ("Сделки", R["trades"]), ("Win rate", R["win_rate"])]
        for i, (lab, val) in enumerate(rows_):
            kv(s, cx, cy + 136 + i * 28, colw, lab, val, line=i < len(rows_) - 1)
    s.line(RX + 16 + colw + 8, y + 60, RX + 16 + colw + 8, y + 52 + 136 + 4 * 28 + 12, DIV)
    fy = y + wh - 16 - 52
    s.rect(RX + 16, fy, RWc - 32, 52, WARN_C, rx=10, fill_opacity=0.14)
    s.icon("warn", RX + 28, fy + 10, "#C79A00")
    P(s, RX + 52, fy + 8, D.FLAGS[0]["text"], RWc - 32 - 48, 12, 17, TEXT, max_lines=2)
    y += wh + 16

    # --- таблица стратегий ---
    th = 52 + 36 + 4 * 52 + 8
    panel(s, X0, y, CW, th, "Стратегии на ds-0007, честные и наивные прогоны")
    T(s, X1 - 16, y + 26, "Флаги: издержки > 50 % прибыли, смена знака результата, наивный Sharpe > 3", 12, TEXT3, anchor="end")
    cols = [("Стратегия", 136), ("Честность", 92), ("Честный", 84), ("Наивный", 84), ("Наивный и честный", 172),
            ("Sharpe честн. / наивн.", 140), ("Макс. просадка", 104), ("Оборот", 64), ("Флаг", 236)]
    xs, cx = [], X0 + 16
    for _, w in cols:
        xs.append(cx)
        cx += w
    hy = y + 52
    for (name, w), x in zip(cols, xs):
        right = name in ("Честный", "Наивный")
        T(s, x + w - 16 if right else x, hy + 18, name, 12, TEXT2, anchor="end" if right else "start")
    s.line(X0 + 16, hy + 36, X1 - 16, hy + 36, DIV)
    ry = hy + 36
    for i, c in enumerate(D.COMPARISON):
        cy = ry + 26
        if i == 0:
            s.rect(X0 + 8, ry + 2, CW - 16, 48, SEL_BG, rx=8)
        s.rect(xs[0], cy - 5, 10, 10, STRAT_C[c["name"]], rx=3)
        T(s, xs[0] + 18, cy, c["name"], 14, TEXT, 700)
        light(s, xs[1], cy, honesty(HONEST_RUN[c["name"]]), seg=18)
        T(s, xs[2] + cols[2][1] - 16, cy, c["honest"], 14, POS if c["h"] > 0 else NEG, 700, anchor="end")
        T(s, xs[3] + cols[3][1] - 16, cy, c["naive"], 14, TEXT2, anchor="end")
        ax, aw = xs[4], cols[4][1] - 24
        X = lambda v: ax + aw * (v + 10) / 100
        s.line(ax, cy, ax + aw, cy, DIV, sw=2)
        s.line(X(0), cy - 6, X(0), cy + 6, TEXT3)
        s.line(X(c["h"]), cy, X(c["n"]), cy, NEG if c["h"] < c["n"] else TEXT3, sw=2, opacity=0.5)
        s.circle(X(c["n"]), cy, 5, fill=SURF, stroke=NAIVE, sw=2)
        s.circle(X(c["h"]), cy, 5, fill=POS if c["h"] > 0 else NEG)
        sw1 = T(s, xs[5], cy, f'{c["sharpe"]} / ', 14, TEXT)
        hot = float(c["sharpe_naive"].replace(",", ".").replace("−", "-")) > 3
        T(s, xs[5] + sw1, cy, c["sharpe_naive"], 14, "#7A5800" if hot else TEXT2, 700 if hot else 400)
        T(s, xs[6], cy, c["dd"], 14, TEXT)
        T(s, xs[7], cy, c["turnover"], 14, TEXT)
        if c["flag"]:
            badge(s, xs[8], cy, c["flag"], "invalid" if "знак" in c["flag"] else "warning", dot=True)
        else:
            T(s, xs[8], cy, "нет", 13, TEXT3)
        if i < 3:
            s.line(X0 + 16, ry + 52, X1 - 16, ry + 52, DIV)
        ry += 52
    ly = ry + 0
    y += th + 16

    # --- наложение кривых ---
    ch = H - 56 - y
    panel(s, X0, y, CW, ch, "Кривые капитала честных прогонов")
    lx = X1 - 16
    for name in ("IMOEX", "RSI-откат", "Моментум 3М", "SMA 20/50"):
        tw = measure(name, 13)
        T(s, lx, y + 26, name, 13, TEXT2, anchor="end")
        s.line(lx - tw - 28, y + 26, lx - tw - 8, y + 26, STRAT_C[name], sw=2)
        lx -= tw + 44
    px, pw = X0 + 64, CW - 64 - 80
    ptop, ph = y + 60, ch - 60 - 44
    vmin, vmax = 0.5, 1.7
    for k in range(7):
        v = 0.5 + 0.2 * k
        gy = ptop + ph - ph * (v - vmin) / (vmax - vmin)
        s.line(px, gy, px + pw, gy, DIV)
        T(s, px - 10, gy, ru(v) + " млн", 12, TEXT3, anchor="end")
    stress_marks(s, px, ptop, pw, ph)
    series = [("IMOEX", D.EQUITY_IMOEX, "+9,4 %"), ("RSI-откат", D.EQUITY_RSI, "−6,8 %"), ("Моментум 3М", D.EQUITY_MOMENTUM, "+44,9 %"), ("SMA 20/50", D.EQUITY_HONEST, "+31,6 %")]
    for name, ser, lab in series:
        date_series(s, ser, px, ptop, pw, ph, vmin, vmax, STRAT_C[name], sw=2 if name == "SMA 20/50" else 1.5)
    ends = sorted([(ptop + ph - ph * (ser[-1] - vmin) / (vmax - vmin), name, lab) for name, ser, lab in series])
    last = -99
    for yy, name, lab in ends:
        yy = max(yy, last + 16)
        T(s, px + pw + 10, yy, lab, 12, STRAT_C[name] if name != "IMOEX" else "#8C8FA3", 700)
        last = yy
    year_axis(s, px, pw, ptop + ph + 18)
    disclaimer(s, H - 24)
    return s


# =========================================================================================
# E6 — Walk-forward
# =========================================================================================
def e6():
    H = 1304
    s = Svg(W, H)
    shell(s, 5, ["Walk-forward", "Пересечение SMA 20/50"])
    S = D.WF_SUMMARY
    page_header(s, "Walk-forward: Пересечение SMA 20/50",
                meta=[("Схема", D.RUN_CONFIG["walk_forward"]), ("Окон", S["windows"]), ("Датасет", "ds-0007")],
                buttons=[("Скачать окна", "outline", "download")])
    y = 148
    kh = 104
    s.rect(X0, y, CW, kh, SURF, rx=12, stroke=BORDER)
    kp = [("Прибыльных окон", S["positive"], TEXT, "на проверке"),
          ("Средняя на проверке", S["oos_avg"].split(" за")[0], TEXT, "за квартал"),
          ("Средняя на подборе", S["is_avg"].split(" за")[0], TEXT2, "за квартал"),
          ("Деградация", S["degradation"], NEG, "проверка против подбора"),
          ("Итого на проверке", S["oos_total"], POS, "20 кварталов подряд"),
          ("Самый частый набор", "20/50", TEXT, S["stable_param"].replace("20/50 выбран", "выбран"))]
    kw = CW / len(kp)
    for i, (lab, val, col, sub) in enumerate(kp):
        kx = X0 + i * kw + 20
        if i:
            s.line(X0 + i * kw, y + 16, X0 + i * kw, y + kh - 16, DIV)
        T(s, kx, y + 26, lab, 13, TEXT2, maxw=kw - 28)
        T(s, kx, y + 58, val, 28, col, 700, maxw=kw - 28)
        T(s, kx, y + 88, sub, 12, TEXT2, maxw=kw - 28)
    y += kh + 16
    # --- доходность по окнам ---
    LWc = 744
    RX, RWc = X0 + LWc + 16, CW - LWc - 16
    bh = 348
    panel(s, X0, y, LWc, bh, "Доходность по окнам")
    lx = X0 + LWc - 16
    for lab, col in (("Проверка, out-of-sample", POS), ("Подбор, in-sample", "#C3CDF0")):
        tw = measure(lab, 13)
        T(s, lx, y + 26, lab, 13, TEXT2, anchor="end")
        s.rect(lx - tw - 22, y + 21, 12, 10, col, rx=2)
        lx -= tw + 40
    px, pw = X0 + 56, LWc - 56 - 20
    ptop, ph = y + 64, bh - 64 - 48
    vmin, vmax = -8, 14
    Y = lambda v: ptop + ph - ph * (v - vmin) / (vmax - vmin)
    for v in (-8, -4, 0, 4, 8, 12):
        s.line(px, Y(v), px + pw, Y(v), "#C9CBD3" if v == 0 else DIV)
        T(s, px - 10, Y(v), (("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v)} %"), 12, TEXT3, anchor="end")
    gw = pw / 20
    for i, wnd in enumerate(D.WALK_FORWARD):
        gx = px + i * gw
        b = gw * 0.34
        tr, te = wnd["train_ret"], wnd["test_ret"]
        s.rect(gx + gw * 0.14, Y(tr), b, Y(0) - Y(tr), "#C3CDF0", rx=2)
        s.rect(gx + gw * 0.14 + b + 2, min(Y(te), Y(0)), b, abs(Y(te) - Y(0)) or 1, POS if te >= 0 else NEG, rx=2)
        T(s, gx + gw / 2, ptop + ph + 18, f"{wnd['n']:02d}", 11, TEXT3, anchor="middle")
    T(s, px, ptop + ph + 38, "Окно", 12, TEXT2)
    T(s, px + pw, ptop + ph + 38, "Подбор в среднем +9,0 %, проверка +0,5 % за квартал", 12, TEXT2, anchor="end")
    # --- параметры по окнам ---
    panel(s, RX, y, RWc, bh, "Параметры по окнам")
    sets = sorted(set(D._WF_PARAMS), key=lambda p: (int(p.split("/")[0]), int(p.split("/")[1])))
    mx0 = RX + 16 + 52
    mw = RWc - 32 - 52
    cw_ = mw / 20
    rr = 30
    my0 = y + 60
    for j, p in enumerate(sets):
        cy = my0 + j * rr + rr / 2
        T(s, RX + 16, cy, p, 13, TEXT, 700 if p == "20/50" else 400, mono=True)
        s.line(mx0, cy, mx0 + mw, cy, DIV)
        for i, wnd in enumerate(D.WALK_FORWARD):
            if wnd["params"] == p:
                s.circle(mx0 + i * cw_ + cw_ / 2, cy, 5, fill=ACCENT if p == "20/50" else "#8FA2E4")
    ay = my0 + len(sets) * rr + 14
    for i in (0, 4, 9, 14, 19):
        T(s, mx0 + i * cw_ + cw_ / 2, ay, f"{i + 1:02d}", 11, TEXT3, anchor="middle")
    changes = sum(1 for a, b in zip(D._WF_PARAMS, D._WF_PARAMS[1:]) if a != b)
    ny = ay + 20
    s.rect(RX + 16, ny, RWc - 32, y + bh - 16 - ny, WARN_C, rx=10, fill_opacity=0.14)
    P(s, RX + 28, ny + 8, f"Набор меняется в {changes} переходах из 19: подбор плохо переносится на новые данные.", RWc - 56, 12, 17, TEXT, max_lines=3)
    y += bh + 16
    # --- таблица окон с диаграммой ---
    rows_h = 26
    th = 52 + 36 + 20 * rows_h + 8
    panel(s, X0, y, CW, th, "Окна", 20)
    T(s, X1 - 16, y + 26, "Подбор 1 год, проверка 3 месяца, окна сдвигаются на 3 месяца", 12, TEXT3, anchor="end")
    cols = [("№", 40), ("Подбор", 152), ("Проверка", 104), ("Шкала 2020 — 2025", 552), ("Параметры", 92), ("Подбор", 84), ("Проверка", 88)]
    xs, cx = [], X0 + 16
    for _, w in cols:
        xs.append(cx)
        cx += w
    hy = y + 52
    for k, ((name, w), x) in enumerate(zip(cols, xs)):
        right = k >= 5
        if k != 3:
            T(s, x + w - 16 if right else x, hy + 18, name, 12, TEXT2, anchor="end" if right else "start")
    gx0, gw0 = xs[3], cols[3][1] - 24
    m0 = date(2020, 1, 1)
    MX = lambda d: gx0 + gw0 * ((d.year - m0.year) * 12 + d.month - 1) / 72
    for yr in range(2020, 2027):
        xx = MX(date(yr, 1, 1))
        T(s, xx, hy + 18, str(yr), 11, TEXT3, anchor="middle" if yr > 2020 else "start")
    s.line(X0 + 16, hy + 36, X1 - 16, hy + 36, DIV)
    ry = hy + 36
    for yr in range(2020, 2027):
        xx = MX(date(yr, 1, 1))
        s.line(xx, ry, xx, ry + 20 * rows_h, DIV)
    for i, wnd in enumerate(D.WALK_FORWARD):
        cy = ry + rows_h / 2
        T(s, xs[0], cy, f"{wnd['n']:02d}", 12, TEXT3, mono=True)
        T(s, xs[1], cy, wnd["train"], 13, TEXT)
        T(s, xs[2], cy, wnd["test"], 13, TEXT)
        a, b = wnd["train"].split(" — ")
        da = date(int(a[3:]), int(a[:2]), 1)
        db = date(int(b[3:]), int(b[:2]), 1)
        de = date(db.year + (db.month + 2) // 12, (db.month + 2) % 12 + 1, 1)
        s.rect(MX(da), cy - 5, MX(db) - MX(da) - 1, 10, "#DCE2F7", rx=2)
        te = wnd["test_ret"]
        s.rect(MX(db), cy - 5, MX(de) - MX(db), 10, POS if te >= 0 else NEG, rx=2)
        T(s, xs[4], cy, wnd["params"], 13, TEXT, 700 if wnd["params"] == "20/50" else 400, mono=True)
        T(s, xs[5] + cols[5][1] - 16, cy, fmt_pct(wnd["train_ret"]), 13, TEXT2, anchor="end")
        T(s, xs[6] + cols[6][1] - 16, cy, fmt_pct(te), 13, POS if te >= 0 else NEG, 700, anchor="end")
        if i < 19:
            s.line(X0 + 16, ry + rows_h, X1 - 16, ry + rows_h, DIV)
        ry += rows_h
    y += th
    disclaimer(s, y + 32)
    if y + 56 != H:
        print("E6 height should be", y + 56)
    return s


# =========================================================================================
# E7 — История прогонов
# =========================================================================================
WARN_REASON = {"run-0140": "adj_close в строке 6", "run-0137": "наивный Sharpe 3,40 > 3"}


def e7():
    H = 948
    s = Svg(W, H)
    shell(s, 6, ["История прогонов"])
    page_header(s, "История прогонов",
                meta=[("Период", "28.09 — 05.10.2026"), ("Прогонов", str(len(D.RUNS))), ("Авторов", "4"), ("Датасетов", "2")],
                buttons=[("Выгрузить CSV", "outline", "download")])
    y = 148
    sel = {"run-0142", "run-0141"}
    cnt = {k: sum(1 for r in D.RUNS if r["status"] == k) for k in ("valid", "warning", "invalid")}
    # строки
    row_h = {}
    for r in D.RUNS:
        row_h[r["id"]] = 56 if r["id"] in WARN_REASON else (44 + 52 if r["status"] == "invalid" else 44)
    th = 64 + 36 + sum(row_h.values()) + 52
    panel(s, X0, y, CW, th)
    sx = X0 + 16
    sx += segmented(s, sx, y + 16, [f"Все {len(D.RUNS)}", f"Валиден {cnt['valid']}", f"С пометкой {cnt['warning']}", f"Невалиден {cnt['invalid']}"], 0) + 16
    for lab, val in (("Стратегия", "все"), ("Режим", "все"), ("Датасет", "все"), ("Автор", "все")):
        w_ = measure(lab + ": " + val, 13) + 44
        s.rect(sx, y + 16, w_, 32, SURF, rx=10, stroke=FIELD)
        lw_ = T(s, sx + 12, y + 32, lab + ":", 13, TEXT2)
        T(s, sx + 12 + lw_ + 4, y + 32, val, 13, TEXT, 700)
        s.icon("chevron-down", sx + w_ - 26, y + 24, TEXT2)
        sx += w_ + 8
    T(s, X1 - 16, y + 32, "Сбросить фильтры", 13, TEXT3, 700, anchor="end")
    cols = [("", 32), ("Прогон", 96), ("Стратегия", 120), ("Режим", 140), ("Датасет", 84), ("Честность", 96), ("Статус", 176),
            ("Результат", 88), ("Запущен", 140), ("Автор", 104), ("", 36)]
    xs, cx = [], X0 + 16
    for _, w in cols:
        xs.append(cx)
        cx += w
    hy = y + 64
    checkbox(s, xs[0], hy + 18, False)
    s.rect(xs[0] + 4, hy + 17, 8, 2, ACCENT)  # частичный выбор
    s.rect(xs[0], hy + 10, 16, 16, ACCENT, rx=4)
    s.rect(xs[0] + 4, hy + 17, 8, 2, "#FFFFFF")
    for (name, w), x in zip(cols, xs):
        if not name:
            continue
        if name == "Результат":
            T(s, x + w - 16, hy + 18, name, 12, TEXT2, anchor="end")
        else:
            nw = T(s, x, hy + 18, name, 12, TEXT if name == "Запущен" else TEXT2, 700 if name == "Запущен" else 400)
            if name == "Запущен":
                s.icon("chevron-down", x + nw + 4, hy + 12, TEXT, s=12)
    s.line(X0 + 16, hy + 36, X1 - 16, hy + 36, DIV)
    ry = hy + 36
    for i, r in enumerate(D.RUNS):
        h_ = row_h[r["id"]]
        base_h = 56 if r["id"] in WARN_REASON else 44
        cy = ry + base_h / 2
        on = r["id"] in sel
        if on:
            s.rect(X0 + 8, ry + 2, CW - 16, base_h - 4, SEL_BG, rx=8)
        checkbox(s, xs[0], cy, on)
        T(s, xs[1], cy, r["id"], 13, ACTION, 700, mono=True)
        T(s, xs[2], cy, r["strategy"], 14, TEXT, maxw=cols[2][1] - 12)
        T(s, xs[3], cy, r["mode"], 14, TEXT, maxw=cols[3][1] - 12)
        T(s, xs[4], cy, r["dataset"], 13, TEXT2, mono=True)
        light(s, xs[5], cy, honesty(r["id"]), seg=20)
        if r["id"] in WARN_REASON:
            status_badge(s, xs[6], cy - 9, r["status"])
            T(s, xs[6], cy + 13, WARN_REASON[r["id"]], 12, TEXT2, maxw=cols[6][1] - 12)
        else:
            status_badge(s, xs[6], cy, r["status"])
        res = r["result"]
        rc = TEXT2 if r["mode"] == "наивный" else POS if res.startswith("+") else NEG if res.startswith("−") else TEXT3
        T(s, xs[7] + cols[7][1] - 16, cy, res, 14, rc, 700, anchor="end")
        T(s, xs[8], cy, r["started"], 13, TEXT2)
        T(s, xs[9], cy, r["author"], 14, TEXT, maxw=cols[9][1] - 8)
        s.icon("repeat", xs[10] + 10, cy - 8, TEXT2)
        if r["status"] == "invalid":
            by = ry + 44
            bw = CW - 32 - 32
            s.rect(xs[1], by, X1 - 16 - xs[1], 44, BAD_C, rx=10, fill_opacity=0.07)
            s.icon("x", xs[1] + 12, by + 14, "#C8160A")
            reason = D.INVALID_REASON.split(": ", 1)[1]
            tw = T(s, xs[1] + 36, by + 22, "Прогон невалиден: " + reason + ".", 13, "#C8160A", 700)
            T(s, xs[1] + 36 + tw + 8, by + 22, "Замените на close или close[1] и запустите заново.", 13, TEXT, maxw=X1 - 32 - 160 - (xs[1] + 44 + tw))
            T(s, X1 - 32, by + 22, "Открыть строку 8", 13, ACTION, 700, anchor="end")
        if i < len(D.RUNS) - 1:
            s.line(X0 + 16, ry + h_, X1 - 16, ry + h_, DIV)
        ry += h_
    fy = ry + 26
    s.line(X0 + 16, ry, X1 - 16, ry, DIV)
    light_legend(s, X0 + 16, fy)
    T(s, X1 - 16 - 88, fy, f"Показаны 1–{len(D.RUNS)} из {len(D.RUNS)}", 13, TEXT2, anchor="end")
    icon_btn(s, X1 - 16 - 72, fy - 16, "chevron-right", 32)
    s.rect(X1 - 16 - 72, fy - 16, 32, 32, ALT, rx=10)
    s.path(f"M{X1 - 16 - 52} {fy - 4.5} L{X1 - 16 - 56.5} {fy} L{X1 - 16 - 52} {fy + 4.5}", stroke=TEXT3, sw=1.6)
    icon_btn(s, X1 - 16 - 32, fy - 16, "chevron-right", 32)
    y += th
    disclaimer(s, y + 28)
    # --- плавающая панель выбора ---
    bw = 760
    bx = X0 + (CW - bw) / 2
    by = H - 24 - 56
    s.rect(bx, by, bw, 56, SB_BG, rx=12)
    T(s, bx + 20, by + 28, "Выбрано 2", 14, "#FFFFFF", 700)
    T(s, bx + 104, by + 28, "run-0142, run-0141", 13, SB_T2, mono=True)
    rx_ = bx + bw - 12
    s.icon("x", rx_ - 24, by + 20, SB_T2)
    rx_ -= 40
    rx_ -= button(s, rx_, by + 12, "Сравнить выбранные", "accent", icon="compare", align="end") + 8
    rx_ -= button(s, rx_, by + 12, "Воспроизвести", "outline", icon="repeat", align="end") + 8
    if y + 40 > by:
        OVERFLOWS.append(f"E7 bar overlaps content {y + 40} > {by}")
    return s


SCREENS = {"E1": e1, "E2": e2, "E3": e3, "E4": e4, "E5": e5, "E6": e6, "E7": e7}


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in SCREENS.items():
        s = fn()
        assert s.w == 1440
        s.save(os.path.join(OUT, f"{name}.svg"))
        print(name, s.w, "x", s.h)
    if OVERFLOWS:
        print("OVERFLOWS:")
        for o in OVERFLOWS:
            print("  ", o)


if __name__ == "__main__":
    only = sys.argv[1:]
    if only:
        SCREENS = {k: v for k, v in SCREENS.items() if k in only}
    main()
