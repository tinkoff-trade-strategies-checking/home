"""Концепция D. Исследование — длинный отчёт-лонгрид. Каждый экран — глава одного документа.

python gen.py            -> out/D1.svg … out/D7.svg
python gen.py 2 4        -> только указанные главы
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

# --- палитра «холодная бумага» -----------------------------------------------------------
BG = "#EDF0F4"
SHEET = "#FFFFFF"
INK = "#14213D"
SEC = "#5C6B80"
TER = "#8A96A8"
LINE = "#D5DAE1"
SOFT = "#F4F6F9"
MARK = "#FFDD2D"
NEG = "#C8372D"
POS = "#0F8A5F"
NEU = "#9AA6B8"
AMBER = "#A86F00"
NEG_BG = "#FBECEA"
AMB_BG = "#FFF5D6"
POS_BG = "#E6F4EE"

# --- сетка ---------------------------------------------------------------------------------
W = 1440
HEAD = 64
SX, SR = 264, 1416          # лист
COL, COLW = 376, 680        # колонка текста (≈ 78 знаков при 17 px)
WIDE = 1000                 # широкие графики: 376…1376
NOTE, NOTEW = 1104, 272     # поля для sidenotes
GUT = 348                   # правый край номеров разделов
NB = "\u00a0"

CHAPTERS = [
    (1, "Данные", "Один снапшот ds-0007 на все прогоны"),
    (2, "Стратегия", "Версия 4 не читает будущее"),
    (3, "Настройка прогона", "Издержки и задержка включены"),
    (4, "Отчёт прогона", "+31,6 % после издержек"),
    (5, "Сравнение", "Издержки съели 62 % прибыли"),
    (6, "Walk-forward", "Вне выборки доходность падает на 95 %"),
    (7, "История прогонов", "Один прогон из 10 невалиден"),
]
TITLES = {
    1: "Все прогоны опираются на один неизменяемый снапшот ds-0007",
    2: "Четвёртая версия стратегии не заглядывает в будущее",
    3: "Честный прогон платит издержки и ждёт открытия следующего дня",
    4: "После издержек стратегия заработала 31,6 % и обогнала IMOEX на 22 п.п.",
    5: "Издержки и задержка съели 62 % наивной прибыли",
    6: "Вне выборки стратегия теряет 95 % доходности, найденной при подборе",
    7: "Из десяти последних прогонов один невалиден: он читал бар t+1",
}

OVERFLOW = []


def nb(s):
    """Склеить числа с единицами, чтобы перенос не рвал «31,6 %» и «1 316 000 ₽»."""
    s = re.sub(r"(\d) (?=\d{3}\b)", "\\1" + NB, s)
    s = re.sub(r"(\d) (%|₽|п\.п\.|дн|шт|×|млн|тыс)", "\\1" + NB + "\\2", s)
    s = re.sub(r"(×) (\d)", "\\1" + NB + "\\2", s)
    s = s.replace(" —", NB + "—")
    s = re.sub(r"\b(I{1,3}|IV) кв\. (\d{4})", "\\1" + NB + "кв." + NB + "\\2", s)
    return s


def fit(s, w, size=14, weight=400, mono=False, tag=""):
    """Обрезать строку по ширине и запомнить переполнение."""
    if measure(s, size, weight, mono) > w:
        OVERFLOW.append(f"{tag}: «{s}» > {w}")
        return truncate(s, w, size, weight, mono)
    return s


# --- богатый абзац с маркером -------------------------------------------------------------
_TOK = re.compile(r"(==.+?==|##.+?##|\*\*.+?\*\*|`.+?`)")


def _segments(src):
    out = []
    for part in _TOK.split(src):
        if not part:
            continue
        if part.startswith("=="):
            out.append((part[2:-2], "mark"))
        elif part.startswith("##"):
            out.append((part[2:-2], "markb"))
        elif part.startswith("**"):
            out.append((part[2:-2], "bold"))
        elif part.startswith("`"):
            out.append((part[1:-1], "mono"))
        else:
            out.append((part, "plain"))
    return out


def _st(style, size):
    weight = 700 if style in ("bold", "markb") else 400
    mono = style == "mono"
    return weight, mono, (size - 1 if mono else size)


def mark_rect(s, x, base, w, size, pad=None):
    pad = 2 if pad is None else pad
    top = base - size * 0.46
    s.rect(x - pad, top, w + pad * 2, size * 0.66, fill=MARK)


def rich(s, x, y, src, width, size=17, lh=28, color=INK, weight=400):
    """Абзац с разметкой ==маркер==, ##маркер+жирный##, **жирный**, `код`. y — базовая линия.
    Возвращает базовую линию после абзаца (y + n*lh)."""
    words = []  # слово = список (кусок, стиль); пробел между словами
    for text, style in _segments(nb(src)):
        if style == "plain" and weight >= 600:
            style = "bold"
        parts = text.split(" ")
        for i, p in enumerate(parts):
            if i == 0 and words and not text.startswith(" ") and words[-1] is not None:
                if p:
                    words[-1].append((p, style))
                continue
            if p:
                words.append([(p, style)])
    words = [w for w in words if w]
    sp = measure(" ", size)

    def wlen(wd):
        tot = 0.0
        for t, st in wd:
            wgt, mono, sz = _st(st, size)
            tot += measure(t, sz, wgt, mono)
        return tot

    lines, cur, cw = [], [], 0.0
    for wd in words:
        wl = wlen(wd)
        if cur and cw + sp + wl > width:
            lines.append(cur)
            cur, cw = [wd], wl
        else:
            cw = cw + (sp if cur else 0) + wl
            cur.append(wd)
    if cur:
        lines.append(cur)

    marks, texts = [], []
    for li, ln in enumerate(lines):
        base = y + li * lh
        runs = []  # [стиль, строка]
        for wi, wd in enumerate(ln):
            for pi, (t, st) in enumerate(wd):
                if wi > 0 and pi == 0:
                    runs[-1][1] += " "
                if runs and runs[-1][0] == st:
                    runs[-1][1] += t
                else:
                    runs.append([st, t])
        cx = x
        prev = None
        for st, t in runs:
            wgt, mono, sz = _st(st, size)
            ism = st in ("mark", "markb")
            if prev is not None and ism != prev and not t[:1] in ",.;:)»!?":
                cx += 3  # воздух между маркером и соседним текстом
            prev = ism
            tw = measure(t.rstrip(" "), sz, wgt, mono)
            if st in ("mark", "markb"):
                marks.append((cx, base, tw))
            texts.append((cx, base, t, sz, wgt, mono, st))
            cx += measure(t, sz, wgt, mono)
    for mx, mb, mw in marks:
        mark_rect(s, mx, mb, mw, size)
    for tx, tb, t, sz, wgt, mono, st in texts:
        col = color
        if st == "mono":
            col = INK
        s.text(tx, tb, t.rstrip(" "), size=sz, fill=col, weight=wgt, mono=mono)
    return y + len(lines) * lh


# --- компоненты ------------------------------------------------------------------------------
def button(s, x, y, label, kind="ghost", icon=None, h=32, size=None, w=None):
    """kind: primary (жёлтая), ink (тёмная), ghost (обводка), flat (текстовая). Возвращает ширину."""
    size = size or (14 if h <= 32 else 16)
    iw = 16 + 8 if icon else 0
    tw = measure(label, size, 700)
    padx = 14 if h <= 32 else 20
    bw = w or (padx * 2 + iw + tw)
    fill, stroke, fg = {"primary": (MARK, None, "#000000"), "ink": (INK, None, "#FFFFFF"),
                        "ghost": (SHEET, LINE, INK), "flat": ("none", None, INK)}[kind]
    s.rect(x, y, bw, h, fill=fill, rx=8 if h <= 32 else 10, stroke=stroke)
    cx = x + (bw - iw - tw) / 2
    if icon:
        s.icon(icon, cx, y + (h - 16) / 2, fg)
        cx += iw
    s.text(cx, y + h / 2 + size * 0.36, label, size=size, fill=fg, weight=700)
    return bw


def badge(s, x, y, label, level, h=24, size=12):
    fg, bg = {"ok": (POS, POS_BG), "valid": (POS, POS_BG), "warning": (AMBER, AMB_BG),
              "error": (NEG, NEG_BG), "invalid": (NEG, NEG_BG), "info": (SEC, SOFT),
              "mvp": (SEC, SOFT)}[level]
    tw = measure(label, size, 700)
    s.rect(x, y, tw + 16, h, fill=bg, rx=6)
    s.text(x + 8, y + h / 2 + size * 0.36, label, size=size, fill=fg, weight=700)
    return tw + 16


def level_icon(s, x, y, level):
    if level in ("ok", "valid"):
        s.circle(x + 8, y + 8, 8, fill=POS_BG)
        s.icon("check", x + 2, y + 2, POS, s=12, sw=2)
    elif level == "warning":
        s.icon("warn", x, y, AMBER)
    elif level in ("error", "invalid"):
        s.circle(x + 8, y + 8, 8, fill=NEG_BG)
        s.icon("x", x + 3, y + 3, NEG, s=10, sw=2)
    else:
        s.icon("info", x, y, SEC)


def field(s, x, y, w, label, value, h=56, mono=False, suffix=None, hint=None):
    """Поле Taiga с подписью внутри (textfield size l)."""
    s.rect(x, y, w, h, fill=SHEET, rx=10, stroke=LINE)
    s.text(x + 16, y + 22, fit(label, w - 32, 12, tag="field"), size=12, fill=SEC)
    vw = w - 32 - (measure(suffix, 15) + 8 if suffix else 0)
    s.text(x + 16, y + 43, fit(value, vw, 15, mono=mono, tag="field"), size=15 if not mono else 14, fill=INK, mono=mono)
    if suffix:
        s.text(x + w - 16, y + 43, suffix, size=15, fill=SEC, anchor="end")
    if hint:
        s.text(x, y + h + 18, hint, size=12, fill=SEC)


def toggle(s, x, y, on=True):
    s.rect(x, y, 40, 24, fill=INK if on else LINE, rx=12)
    s.circle(x + (28 if on else 12), y + 12, 9, fill=SHEET)


def checkbox(s, x, y, on=False):
    if on:
        s.rect(x, y, 18, 18, fill=INK, rx=4)
        s.icon("check", x + 2, y + 2, "#FFFFFF", s=14, sw=2)
    else:
        s.rect(x, y, 18, 18, fill=SHEET, rx=4, stroke="#B4BDCA", sw=1.5)


# --- страница ----------------------------------------------------------------------------------
class Page:
    def __init__(self, n):
        self.n = n
        self.s = Svg(W, 2000)
        self.y = HEAD + 24 + 56
        self.note_bottom = 0
        self.sections = []

    # заголовок главы
    def chapter_head(self, meta, lede):
        s = self.s
        top = self.y
        s.text(GUT, top + 44, str(self.n), size=56, fill=LINE, weight=700, anchor="end")
        lines = wrap(nb(TITLES[self.n]), 900, 44, 700)
        for i, ln in enumerate(lines):
            s.text(COL, top + 42 + i * 52, ln, size=44, fill=INK, weight=700)
        y = top + 42 + (len(lines) - 1) * 52 + 40
        # метастрока: пары «подпись значение», без разделителей-точек
        x = COL
        for k, v in meta:
            s.text(x, y, k, size=13, fill=SEC)
            x += measure(k, 13) + 6
            s.text(x, y, v, size=13, fill=INK, weight=700, mono=False)
            x += measure(v, 13, 700) + 28
        self.lede_top = y + 22
        if lede:
            y = rich(s, COL, y + 44, lede, COLW, size=20, lh=32) - 8
        self.y = y
        return self.lede_top

    def wide(self):
        """Верх широкого блока: ниже и текста, и заметок на полях."""
        return max(self.y, self.note_bottom)

    def repro(self, top):
        """Метаданные воспроизводимости на полях + действие «Воспроизвести»."""
        s = self.s
        top = max(top, self.note_bottom + 20)
        R = D.REPRO
        rows = [("прогон", R["run"]), ("датасет", "ds-0007"), ("sha данных", "3f9a…c21e"),
                ("стратегия", "SMA 20/50, v4"), ("sha кода", "8d10…4ab2"), ("движок", "0.3.1"),
                ("seed", R["seed"]), ("запущен", "05.10.2026 14:22"), ("длительность", R["duration"])]
        s.text(NOTE + 14, top + 16, "Воспроизводимость", size=13, fill=INK, weight=700)
        y = top + 16
        for k, v in rows:
            y += 21
            s.text(NOTE + 14, y, k, size=12, fill=SEC)
            s.text(NOTE + NOTEW, y, v, size=12, fill=INK, mono=True, anchor="end")
        y += 16
        button(s, NOTE + 14, y, "Воспроизвести", "ghost", icon="repeat", w=NOTEW - 14)
        y += 32
        s.line(NOTE, top + 2, NOTE, y, stroke=LINE, sw=2)
        self.note_bottom = y
        return y

    def h2(self, num, title, gap=52):
        s = self.s
        self.y += gap
        s.line(COL, self.y - 32, COL + 48, self.y - 32, stroke=INK, sw=2)
        s.text(GUT, self.y, num, size=15, fill=SEC, weight=700, anchor="end")
        lines = wrap(nb(title), COLW + 40, 24, 700)
        for i, ln in enumerate(lines):
            s.text(COL, self.y + i * 32, ln, size=24, fill=INK, weight=700)
        self.y += (len(lines) - 1) * 32 + 16
        return self.y

    def p(self, src, gap=20, width=COLW, size=17, lh=28, color=INK):
        self.y += gap + 14
        top = self.y - 20
        self.y = rich(self.s, COL, self.y, src, width, size=size, lh=lh, color=color) - 14
        return top

    def note(self, top, label, lines):
        """Sidenote на полях: подпись + строки (текст, моно?). Заметки не налезают друг на друга."""
        s = self.s
        top = max(top, self.note_bottom + 20)
        s.text(NOTE + 14, top + 16, label, size=13, fill=INK, weight=700)
        y = top + 16
        for t, mono in lines:
            if mono:
                y += 20
                s.text(NOTE + 14, y, fit(t, NOTEW - 14, 12, mono=True, tag="note"), size=12, fill=SEC, mono=True)
            else:
                y = s.para(NOTE + 14, y + 20, nb(t), NOTEW - 14, size=13, lh=20, fill=SEC) - 20
        s.line(NOTE, top + 2, NOTE, y + 6, stroke=LINE, sw=2)
        self.note_bottom = y + 6
        return y + 6

    def flag(self, top, level, text):
        """Предупреждение прогона на полях, рядом с местом, к которому оно относится."""
        s = self.s
        top = max(top, self.note_bottom + 20)
        level_icon(s, NOTE - 2, top + 2, level)
        lab = "Предупреждение" if level == "warning" else "К сведению"
        s.text(NOTE + 24, top + 15, lab, size=13, fill=AMBER if level == "warning" else SEC, weight=700)
        y = s.para(NOTE + 24, top + 36, nb(text), NOTEW - 24, size=13, lh=20, fill=INK) - 20
        self.note_bottom = y + 6
        return y + 6

    def caption(self, num, text, x=COL, width=WIDE):
        s = self.s
        self.y += 28
        lab = f"Рис. {num}."
        s.text(x, self.y, lab, size=13, fill=INK, weight=700)
        off = measure(lab, 13, 700) + 6
        lines = wrap(nb(text), width - off, 13)
        s.text(x + off, self.y, lines[0], size=13, fill=SEC)
        rest = " ".join(lines[1:])
        if rest:
            self.y = s.para(x, self.y + 20, rest, width, size=13, lh=20, fill=SEC) - 20
        self.y += 8

    # каркас: фон, лист, шапка, оглавление, подвал
    def finish(self, next_title=None):
        s = self.s
        y = max(self.y, self.note_bottom) + 48
        s.line(COL, y, COL + WIDE, y, stroke=LINE)
        y += 36
        if self.n < 7:
            nn, name, _ = CHAPTERS[self.n]
            s.text(COL, y, f"Следующая глава, {nn}. {name}", size=13, fill=SEC)
            ly = s.para(COL, y + 30, nb(TITLES[nn]), 760, size=20, lh=28, fill=INK, weight=700)
            button(s, COL + WIDE - 180, y + 6, f"Открыть главу {nn}", "ghost", w=180, h=44)
            y = ly - 4
        else:
            s.text(COL, y, "Конец отчёта", size=13, fill=SEC)
            s.text(COL, y + 30, "Экспорт соберёт все семь глав в один документ", size=20, fill=INK, weight=700)
            button(s, COL + WIDE - 180, y + 6, "Экспорт", "ghost", icon="download", w=180, h=44)
            y += 56
        s.para(COL, y + 28, D.DISCLAIMER, WIDE, size=12, lh=16, fill=SEC)
        sheet_bottom = y + 64
        H = sheet_bottom + 32
        s.h = H
        pre = Svg(W, H)
        pre.rect(0, 0, W, H, BG)
        pre.rect(SX, HEAD + 24, SR - SX, sheet_bottom - HEAD - 24, SHEET, rx=4, stroke=LINE)
        s.body[0:0] = pre.body
        self._header()
        self._rail()
        return H

    def _header(self):
        s = self.s
        s.rect(0, 0, W, HEAD, SHEET)
        s.line(0, HEAD, W, HEAD, stroke=LINE)
        s.rect(32, 20, 24, 24, fill=INK, rx=6)
        s.rect(37, 32, 14, 6, fill=MARK)
        s.text(68, 38, D.PRODUCT, size=16, fill=INK, weight=700)
        x = 68 + measure(D.PRODUCT, 16, 700) + 24
        s.line(x, 22, x, 42, stroke=LINE)
        s.text(x + 24, 37, "Исследования", size=14, fill=SEC)
        x2 = x + 24 + measure("Исследования", 14) + 10
        s.icon("chevron-right", x2, 24, TER, s=14)
        s.text(x2 + 22, 37, "Пересечение SMA 20/50", size=14, fill=INK, weight=700)
        # действия
        r = W - 32
        s.circle(r - 16, 32, 16, fill=SOFT, stroke=LINE)
        s.text(r - 16, 37, "ДМ", size=12, fill=INK, weight=700, anchor="middle")
        r -= 32 + 16
        bw = measure("Воспроизвести", 14, 700) + 28 + 24
        button(s, r - bw, 16, "Воспроизвести", "ink", icon="repeat")
        r -= bw + 8
        bw = measure("Экспорт", 14, 700) + 28 + 24
        button(s, r - bw, 16, "Экспорт", "ghost", icon="download")
        r -= bw + 20
        t = "run-0142, ds-0007, seed 20261005"
        s.text(r, 37, t, size=12, fill=SEC, mono=True, anchor="end")

    def _rail(self):
        s = self.s
        x, y = 32, HEAD + 40
        s.text(x, y + 14, "Пересечение SMA 20/50", size=15, fill=INK, weight=700)
        s.text(x, y + 34, "Отчёт исследования, 7 глав", size=13, fill=SEC)
        y += 72
        s.line(x, y, 232, y, stroke=LINE)
        y += 28
        for n, name, concl in CHAPTERS:
            active = n == self.n
            done = n < self.n
            # номер главы
            s.text(x, y, str(n), size=14, fill=INK if (active or done) else TER, weight=700)
            nx = x + 24
            if active:
                mark_rect(s, nx, y, measure(name, 15, 700), 15)
            s.text(nx, y, name, size=15, fill=INK, weight=700 if active else 400)
            ly = s.para(nx, y + 20, concl, 232 - nx, size=12, lh=16, fill=SEC if active else TER, max_lines=2)
            y = ly + 4
            if active and self.sections:
                y += 4
                for num, t in self.sections:
                    s.text(nx, y + 14, num, size=12, fill=SEC, weight=700)
                    s.text(nx + 30, y + 14, fit(t, 232 - nx - 30, 13, tag="rail"), size=13, fill=INK)
                    y += 24
                y += 4
            y += 20
        y += 8
        s.line(x, y, 232, y, stroke=LINE)
        y += 28
        s.text(x, y, "Происхождение", size=13, fill=INK, weight=700)
        rows = [("снапшот", "ds-0007"), ("sha", "3f9a…c21e"), ("стратегия", "версия 4"), ("seed", "20261005"), ("движок", "0.3.1")]
        for i, (k, v) in enumerate(rows):
            s.text(x, y + 26 + i * 22, k, size=12, fill=SEC)
            s.text(232, y + 26 + i * 22, v, size=12, fill=INK, mono=True, anchor="end")

    def save(self):
        return self.s.save(os.path.join(OUT, f"D{self.n}.svg"))


# --- графики -----------------------------------------------------------------------------------
D0, D1 = D.DAYS[0], D.DAYS[-1]


def xdate(d, x, w):
    return x + w * (d - D0).days / (D1 - D0).days


def line_by_date(s, vals, x, y, w, h, vmin, vmax, stroke, sw=2, dash=None, step=3, opacity=None, fill_to=None, fill=None, fill_op=None):
    pts = []
    n = len(vals)
    for i in list(range(0, n, step)) + [n - 1]:
        px = xdate(D.DAYS[i], x, w)
        py = y + h - h * (vals[i] - vmin) / (vmax - vmin)
        pts.append((px, py))
    d = "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
    if fill_to is not None:
        s.path(d + f" L{pts[-1][0]:.1f} {fill_to:.1f} L{pts[0][0]:.1f} {fill_to:.1f} Z", fill=fill, fill_opacity=fill_op)
    s.path(d, stroke=stroke, sw=sw, dash=dash, opacity=opacity)
    return pts


def hatch(s, x, y, w, h, color=NEU, step=6):
    s.clip(x, y, w, h)
    k = -h
    while k < w:
        s.line(x + k, y + h, x + k + h, y, stroke=color, sw=1)
        k += step
    s.end()


def year_axis(s, x, w, y, years=range(2020, 2026)):
    for yr in years:
        px = xdate(date(yr, 1, 1), x, w) if yr > 2020 else x
        s.line(px, y, px, y + 6, stroke=LINE)
        s.text(px + 4, y + 18, str(yr), size=12, fill=SEC)


# ============================================================================================
# Глава 4. Отчёт прогона
# ============================================================================================
def chapter4():
    P = Page(4)
    P.sections = [("4.1", "Капитал и просадка"), ("4.2", "Сделки на SBER"), ("4.3", "Метрики"),
                  ("4.4", "Издержки по видам")]
    s = P.s
    R, N = D.RESULT_HONEST, D.RESULT_NAIVE
    top = P.chapter_head(
        [("Прогон", "run-0142"), ("Режим", "честный"), ("Период", "03.01.2020 — 30.12.2025"), ("Статус", "валиден")],
        None)
    # крупные числа — в колонке текста, поля справа заняты метаданными воспроизводимости
    y = P.y + 20
    P.repro(y + 4)
    s.line(COL, y, COL + COLW, y, stroke=LINE)
    big = [(0, "+31,6 %", "доходность после издержек", "наивный прогон: +84,2 %", True),
           (284, "−27,4 %", "максимальная просадка", "214 дней, 24.02.2022 — 05.01.2023", False),
           (562, "0,41", "коэффициент Шарпа", "наивный: 1,12", False)]
    for i, (dx, num, lab, sub, hl) in enumerate(big):
        bx = COL + dx
        base = y + 76
        if hl:
            mark_rect(s, bx, base, measure(num, 64, 700), 64, pad=4)
        s.text(bx, base, num, size=64, fill=INK, weight=700)
        s.text(bx, base + 32, lab, size=14, fill=INK, weight=700)
        s.text(bx, base + 52, sub, size=13, fill=SEC)
    P.y = y + 160
    s.line(COL, P.y, COL + COLW, P.y, stroke=LINE)
    P.y += 24
    P.p("За шесть лет стратегия «Пересечение SMA 20/50» превратила 1 000 000 ₽ в ==1 316 000 ₽==. "
        "Это почти втрое меньше, чем обещал наивный прогон, но больше, чем дал индекс Мосбиржи.", size=20, lh=32, gap=0)

    # 4.1 капитал + просадка
    P.h2("4.1", "Главный удар по капиталу пришёлся на 24.02.2022")
    t = P.p("Честный прогон отстаёт от наивного с первого месяца. В феврале 2022 обе кривые падают "
            "с рынком, но честная проваливается глубже: ==позиции закрываются только после "
            "возобновления торгов 24 марта==, по цене открытия.")
    P.flag(t, "info", D.FLAGS[2]["text"])

    gx, gy, gw, gh = COL, P.wide() + 40, 840, 220
    vmin, vmax = 0.5, 2.0
    Y = lambda v: gy + gh - gh * (v - vmin) / (vmax - vmin)
    uy, uh = gy + gh + 40, 76
    m0, m1 = xdate(date(2020, 2, 24), gx, gw), xdate(date(2020, 3, 23), gx, gw)
    s.rect(m0, gy, m1 - m0, uy + uh - gy, fill=SOFT)
    g0, g1 = xdate(date(2022, 2, 28), gx, gw), xdate(date(2022, 3, 23), gx, gw)
    hatch(s, g0, gy, g1 - g0, uy + uh - gy, color=NEU, step=4)
    e0 = xdate(date(2022, 2, 24), gx, gw)
    for v in (0.6, 1.0, 1.4, 1.8):
        s.line(gx, Y(v), gx + gw, Y(v), stroke=LINE, dash="2 4" if v != 1.0 else None)
        s.text(gx + gw + 8, Y(v) + 4, f"{v:.1f} млн".replace(".", ","), size=12, fill=SEC)
    line_by_date(s, D.EQUITY_IMOEX, gx, gy, gw, gh, vmin, vmax, NEU, sw=1.5)
    line_by_date(s, D.EQUITY_NAIVE, gx, gy, gw, gh, vmin, vmax, SEC, sw=1.75, dash="5 4")
    line_by_date(s, D.EQUITY_HONEST, gx, gy, gw, gh, vmin, vmax, INK, sw=2.5)
    s.line(e0, gy - 6, e0, uy + uh, stroke=NEG, sw=1.25)
    s.text(m0, gy - 12, "Март 2020", size=12, fill=SEC, weight=700)
    s.text(e0 - 6, gy - 12, "24.02.2022", size=12, fill=NEG, weight=700, anchor="end")
    s.text(g1 + 6, gy - 12, "торгов нет до 23.03", size=12, fill=SEC)
    lx = gx + gw + 64
    for val, lab, sub in [(D.EQUITY_NAIVE[-1], "Наивный", "+84,2 %"), (D.EQUITY_HONEST[-1], "Честный", "+31,6 %"),
                          (D.EQUITY_IMOEX[-1], "IMOEX", "+9,4 %")]:
        py = Y(val)
        hon = lab == "Честный"
        s.circle(gx + gw, py, 3.5, fill=INK if hon else (SEC if lab == "Наивный" else NEU))
        s.text(lx, py + 4, lab, size=13, fill=INK if hon else SEC, weight=700 if hon else 400)
        ox = lx + measure(lab, 13, 700 if hon else 400) + 6
        if hon:
            mark_rect(s, ox, py + 4, measure(sub, 13, 700), 13)
        s.text(ox, py + 4, sub, size=13, fill=INK if hon else SEC, weight=700 if hon else 400)
    s.text(gx, uy - 12, "Просадка честного прогона от предыдущего пика", size=12, fill=SEC, weight=700)
    dd = D.drawdown(D.EQUITY_HONEST)
    line_by_date(s, dd, gx, uy, gw, uh, -0.30, 0.0, NEG, sw=1.25, fill_to=uy, fill=NEG, fill_op=0.16)
    s.line(gx, uy, gx + gw, uy, stroke=INK, sw=1)
    for v in (-0.15, -0.3):
        yy = uy + uh * (-v) / 0.30
        s.line(gx, yy, gx + gw, yy, stroke=LINE, dash="2 4")
        s.text(gx + gw + 8, yy + 4, fmt_pct(v * 100, 0), size=12, fill=SEC)
    s.text(gx + gw + 8, uy + 4, "0 %", size=12, fill=SEC)
    i = dd.index(min(dd))
    tx, ty = xdate(D.DAYS[i], gx, gw), uy + uh * (-dd[i]) / 0.30
    s.circle(tx, ty, 4, fill=NEG)
    s.line(tx + 6, ty, tx + 36, ty, stroke=NEG)
    lab = "−27,4 %"
    mark_rect(s, tx + 42, ty + 5, measure(lab, 14, 700), 14)
    s.text(tx + 42, ty + 5, lab, size=14, fill=INK, weight=700)
    s.text(tx + 42 + measure(lab, 14, 700) + 8, ty + 5, "максимальная просадка", size=13, fill=SEC)
    year_axis(s, gx, gw, uy + uh + 4)
    P.y = uy + uh + 28
    P.caption("4.1", "Капитал прогонов и IMOEX, млн ₽, и просадка честного прогона. Серая зона — март 2020, штриховка — 28.02–23.03.2022.")

    # 4.2 свечи
    P.h2("4.2", "Лимит ликвидности режет крупные заявки на SBER")
    t = P.p("Заявка больше 5 % объёма бара исполняется частично или отклоняется — "
            "на последних четырёх месяцах периода видны оба случая.")
    P.flag(t, "info", D.FLAGS[3]["text"])
    cd = D.candles()
    cx0, cy0, cw, ch = COL, P.wide() + 52, 900, 160
    for k in range(5):
        s.line(cx0, cy0 + ch * k / 4, cx0 + cw, cy0 + ch * k / 4, stroke=LINE, dash="2 4")
    info = s.candles(cd, cx0, cy0, cw, ch, POS, NEG, gap=0.35)
    lo, hi = info["lo"], info["hi"]
    for k in range(5):
        v = hi - (hi - lo) * k / 4
        s.text(cx0 + cw + 10, cy0 + ch * k / 4 + 4, f"{v:.0f} ₽", size=12, fill=SEC)
    lab_y = {"buy": cy0 + ch + 40, "partial": cy0 - 26, "sell": cy0 - 26, "rejected": cy0 + ch + 40}
    for idx, kind, lab in D.TRADE_MARKERS:
        c = cd[idx]
        mx = info["X"](idx)
        if kind in ("buy", "partial"):
            my = info["Y"](c["l"]) + 8
            pth = f"M{mx:.1f} {my:.1f} L{mx + 7:.1f} {my + 11:.1f} L{mx - 7:.1f} {my + 11:.1f} Z"
            if kind == "buy":
                s.path(pth, fill=POS)
            else:
                s.path(pth, fill=SHEET, stroke=POS, sw=1.75)
                s.path(f"M{mx:.1f} {my:.1f} L{mx:.1f} {my + 11:.1f} L{mx - 7:.1f} {my + 11:.1f} Z", fill=POS)
            ay = my + 11
        elif kind == "sell":
            my = info["Y"](c["h"]) - 8
            s.path(f"M{mx:.1f} {my:.1f} L{mx + 7:.1f} {my - 11:.1f} L{mx - 7:.1f} {my - 11:.1f} Z", fill=NEG)
            ay = my - 11
        else:
            my = info["Y"](c["l"]) + 15
            s.circle(mx, my, 7, fill=SHEET, stroke=NEG, sw=1.5)
            s.path(f"M{mx - 3:.1f} {my - 3:.1f} L{mx + 3:.1f} {my + 3:.1f} M{mx + 3:.1f} {my - 3:.1f} L{mx - 3:.1f} {my + 3:.1f}", stroke=NEG, sw=1.5)
            ay = my + 7
        ly = lab_y[kind]
        if ly > ay:
            s.line(mx, ay + 3, mx, ly - 15, stroke=TER, dash="2 2")
        else:
            s.line(mx, ay - 3, mx, ly + 6, stroke=TER, dash="2 2")
        s.text(mx - 6, ly, lab, size=13, fill=INK, weight=700)
    for mi, mname in enumerate(["сентябрь", "октябрь", "ноябрь", "декабрь"]):
        px = cx0 + cw * mi / 4
        s.line(px, cy0 + ch, px, cy0 + ch + 6, stroke=LINE)
        s.text(px + 4, cy0 + ch + 18, mname, size=12, fill=SEC)
    P.y = cy0 + ch + 46
    P.caption("4.2", "Дневные свечи SBER, 01.09–31.12.2025, и сделки стратегии. Цена исполнения — open следующего бара.")

    # 4.3 метрики
    P.h2("4.3", "Издержки снизили доходность и Sharpe почти втрое")
    tx, ty, tw = COL, P.wide() + 36, 470
    s.text(tx, ty, "Метрика", size=13, fill=SEC)
    s.text(tx + 340, ty, "Честный", size=13, fill=INK, weight=700, anchor="end")
    s.text(tx + tw, ty, "Наивный", size=13, fill=SEC, anchor="end")
    s.line(tx, ty + 12, tx + tw, ty + 12, stroke=INK)
    rows = [("Итоговый капитал", R["final"], N["final"]), ("Общая доходность", R["total"], N["total"]),
            ("Среднегодовая, CAGR", R["cagr"], N["cagr"]), ("Макс. просадка", R["max_dd"], N["max_dd"]),
            ("Sharpe", R["sharpe"], N["sharpe"]), ("Sortino", R["sortino"], N["sortino"]),
            ("Сделки", R["trades"], N["trades"]), ("Доля прибыльных", R["win_rate"], N["win_rate"])]
    for i, (k, a, b) in enumerate(rows):
        ry = ty + 38 + i * 32
        s.text(tx, ry, k, size=15, fill=INK)
        if i == 1:
            mark_rect(s, tx + 340 - measure(a, 15, 700), ry, measure(a, 15, 700), 15)
        s.text(tx + 340, ry, a, size=15, fill=INK, weight=700, anchor="end")
        s.text(tx + tw, ry, b, size=15, fill=SEC, anchor="end")
        s.line(tx, ry + 14, tx + tw, ry + 14, stroke=LINE)
    rx, rw = COL + 530, WIDE - 530
    s.text(rx, ty, "Только в честном прогоне", size=13, fill=SEC)
    s.line(rx, ty + 12, rx + rw, ty + 12, stroke=INK)
    rows2 = [("До издержек / после", f"{R['gross']} / {R['net']}"), ("IMOEX за период", R["benchmark"]),
             ("Превышение над IMOEX", R["vs_benchmark"]), ("Волатильность, годовая", R["vol"]),
             ("Оборот", R["turnover"]), ("Частичные / отказы", f"{R['partial']} / {R['rejected']}"),
             ("Концентрация, HHI", R["hhi"]), ("Крупнейшая позиция", R["top_position"])]
    for i, (k, v) in enumerate(rows2):
        ry = ty + 38 + i * 32
        s.text(rx, ry, k, size=15, fill=INK)
        s.text(rx + rw, ry, v, size=15, fill=INK, weight=700, anchor="end")
        s.line(rx, ry + 14, rx + rw, ry + 14, stroke=LINE)
    P.y = ty + 38 + 7 * 32 + 14

    # 4.4 издержки
    P.h2("4.4", "Спред — самая крупная из денежных издержек")
    t = P.p("Прямые издержки за период — ==259 300 ₽==. Задержка и лимит ликвидности денег не списывают, "
            "их вклад разобран в главе 5.")
    P.flag(t, "warning", D.FLAGS[0]["text"])
    P.flag(t, "warning", D.FLAGS[1]["text"])
    by = P.y + 32
    costs = [(name, rub) for name, pp, rub in D.DELTA_BREAKDOWN if rub]
    vals = [int(r.replace(" ", "").replace("₽", "")) for _, r in costs]
    mxv = max(vals)
    for i, ((name, rub), v) in enumerate(zip(costs, vals)):
        ry = by + i * 32
        s.text(COL, ry + 15, name, size=15, fill=INK)
        bx = COL + 200
        bw = 360 * v / mxv
        s.rect(bx, ry + 2, bw, 18, fill=INK if i == 0 else NEU, rx=2)
        s.text(bx + bw + 10, ry + 16, rub, size=15, fill=INK, weight=700)
    ry = by + len(costs) * 32 + 4
    s.line(COL, ry, COL + COLW, ry, stroke=INK)
    s.text(COL, ry + 26, "Всего", size=15, fill=INK, weight=700)
    s.text(COL + 200, ry + 26, D.COSTS_TOTAL, size=15, fill=INK, weight=700)
    P.y = ry + 26

    P.finish()
    return P.save()


# ============================================================================================
# Глава 2. Стратегия
# ============================================================================================
KW = {"strategy", "universe", "capital", "let", "when", "buy", "sell", "all", "equity", "RUB"}
FN = {"sma", "crosses_above", "crosses_below", "drawdown"}


def code_line(s, x, y, line, size=14, hl=None):
    """Подсветка DSL на светлом фоне. hl — подстрока, которую подчеркнуть (код, цвет)."""
    toks = re.findall(r'//.*|"[^"]*"|->|\d[\d_]*%?|[A-Za-z_]+(?:\[\+1\])?|\s+|.', line)
    cx = x
    for t in toks:
        if t.startswith("//"):
            col, w = TER, 400
        elif t.startswith('"'):
            col, w = POS, 400
        elif t == "->":
            col, w = TER, 400
        elif re.match(r"\d", t):
            col, w = "#B4532A", 400
        elif t in KW:
            col, w = "#3346A0", 700
        elif t in FN:
            col, w = INK, 700
        else:
            col, w = INK, 400
        tw = measure(t, size, w, True)
        if hl and t == hl[0]:
            s.rect(cx - 1, y + 4, tw + 2, 2, fill=hl[1])
            s.rect(cx - 2, y - size + 1, tw + 4, size + 6, fill=hl[2], rx=3)
        if t.strip():
            s.text(cx, y, t, size=size, fill=col, weight=w, mono=True)
        cx += tw
    return cx


def chapter2():
    P = Page(2)
    P.sections = [("2.1", "Код стратегии"), ("2.2", "Чтение будущего"), ("2.3", "Список стратегий")]
    s = P.s
    top = P.chapter_head(
        [("Стратегия", "SMA 20/50"), ("Версия", "4"), ("Проверено", "05.10.2026 14:20")],
        "Статический анализ прошёл по всем строкам: каждое решение принимается по данным "
        "до бара t включительно, а сделка исполняется на следующем баре. "
        "==Две предыдущие версии проверка поймала== — их разбор ниже.")
    P.note(top, "Код стратегии", [("SMA 20/50, версия 4", False), ("sha 8d10…4ab2", True)])

    # 2.1 ячейка с кодом
    P.h2("2.1", "Правила умещаются в десять строк")
    t = P.p("Стратегия описана на DSL в стиле Pine: вселенная, капитал, две скользящие средние и три "
            "правила. Поля справа объясняют, какие данные доступны каждой строке.")
    cy = P.y + 32
    cw = 680
    lh = 26
    nlines = len(D.DSL_MAIN)
    chh = 52 + nlines * lh + 24
    s.rect(COL, cy, cw, chh, fill=SOFT, rx=12, stroke=LINE)
    s.line(COL, cy + 44, COL + cw, cy + 44, stroke=LINE)
    s.icon("code", COL + 16, cy + 14, SEC)
    s.text(COL + 40, cy + 27, "sma_20_50.pine", size=13, fill=INK, weight=700, mono=True)
    s.text(COL + 40 + measure("sma_20_50.pine", 13, 700, True) + 12, cy + 27, "версия 4", size=13, fill=SEC)
    badge(s, COL + cw - 16 - measure("Без замечаний", 12, 700) - 16 - 24, cy + 10, "Без замечаний", "ok")
    level_icon(s, COL + cw - 16 - 16, cy + 14, "ok")
    for i, ln in enumerate(D.DSL_MAIN):
        by = cy + 52 + 18 + i * lh
        s.text(COL + 36, by, str(i + 1), size=13, fill=TER, mono=True, anchor="end")
        if ln:
            code_line(s, COL + 56, by, ln, size=14)
    # заметки на полях, привязанные к строкам
    margin = [(2, "Вселенная", "6 акций, бенчмарк IMOEX"), (5, "Строки 5–6", "close доступен после 18:50 дня t; средние считаются по барам до t"),
              (8, "Строки 8–9", "сигнал на закрытии t, исполнение по open t+1"), (10, "Строка 10", "стоп по просадке позиции, проверяется на закрытии")]
    floor = 0
    for ln_no, lab, txt in margin:
        by = cy + 52 + 18 + (ln_no - 1) * lh
        ny = max(by, floor)
        s.path(f"M{COL + cw + 8} {by - 5:.1f} L{NOTE - 24} {by - 5:.1f} L{NOTE - 10} {ny - 5:.1f}", stroke=LINE, sw=1, dash="2 3")
        s.text(NOTE, ny, lab, size=13, fill=INK, weight=700)
        floor = s.para(NOTE, ny + 19, txt, NOTEW, size=13, lh=19, fill=SEC) + 10
    P.y = cy + chh
    bx = COL
    bx += button(s, bx, P.y + 16, "Проверить снова", "ghost", icon="check") + 8
    bx += button(s, bx, P.y + 16, "История версий", "ghost", icon="history") + 8
    s.text(COL + cw, P.y + 37, "проверка заняла 0,2 с", size=12, fill=SEC, anchor="end")
    P.y += 48

    # 2.2 три уровня проверки
    P.h2("2.2", "Проверка различает три уровня риска, и только ошибка делает прогон невалидным")
    t = P.p("Анализатор читает код до запуска и для каждой ссылки на данные определяет момент, когда "
            "значение становится известно. Ниже — по одному примеру каждого уровня из истории этой стратегии.")
    meta = {"ok": ("Без замечаний", "версия 4, текущая", POS, POS_BG),
            "warning": ("Подозрительно: прогон получит пометку", "найдено в run-0140", AMBER, AMB_BG),
            "error": ("Ошибка: прогон невалиден", "найдено в run-0139", NEG, NEG_BG)}
    hlword = {"ok": None, "warning": "adj_close", "error": "close[+1]"}
    yy = P.y + 36
    for chk in D.LOOKAHEAD_CHECKS:
        lv = chk["level"]
        lab, where, col, bgc = meta[lv]
        level_icon(s, COL, yy - 14, lv)
        s.text(COL + 28, yy, lab, size=16, fill=col if lv != "ok" else INK, weight=700)
        s.text(COL + WIDE, yy, where, size=13, fill=SEC, anchor="end")
        # фрагмент кода
        ky = yy + 18
        s.rect(COL + 28, ky, 600, 40, fill=SOFT, rx=8)
        s.text(COL + 44, ky + 26, f"{chk['line']}", size=13, fill=TER, mono=True)
        hw = hlword[lv]
        code_line(s, COL + 72, ky + 26, chk["code"], size=14, hl=(hw, col, bgc) if hw else None)
        ny = s.para(COL + 28 + 600 + 28, ky + 4 + 14, nb(chk["msg"]), WIDE - 656, size=14, lh=20, fill=INK)
        yy = max(ky + 40, ny - 14) + 28
        s.line(COL, yy - 4, COL + WIDE, yy - 4, stroke=LINE)
        yy += 36
    P.y = yy - 36
    t = P.p("Правило простое: **подозрительная** ссылка оставляет прогон в отчёте с пометкой, "
            "**ошибка** блокирует его. Такой прогон виден в истории, но не участвует в сравнении.", gap=28)
    P.note(t, "Причина невалидности", [("run-0139: close[+1] в строке 8", True), ("читает бар t+1", False)])

    # 2.3 стратегии
    P.h2("2.3", "В исследовании четыре стратегии, включая бенчмарк")
    ty = P.y + 40
    cols = [(COL, "Стратегия"), (COL + 260, "Идея"), (COL + 830, "Прогоны"), (COL + WIDE, "Изменена")]
    for x, lab in cols:
        s.text(x, ty, lab, size=13, fill=SEC, anchor="end" if x in (COL + 830, COL + WIDE) else "start")
    s.line(COL, ty + 12, COL + WIDE, ty + 12, stroke=INK)
    for i, st in enumerate(D.STRATEGIES):
        ry = ty + 48 + i * 52
        cur = i == 0
        if cur:
            mark_rect(s, COL, ry, measure(st["name"], 15, 700), 15)
        s.text(COL, ry, fit(st["name"], 240, 15, 700, tag="strat"), size=15, fill=INK, weight=700)
        if cur:
            s.text(COL, ry + 20, "в этом отчёте", size=12, fill=SEC)
        s.text(COL + 260, ry, fit(st["desc"], 480, 15, tag="strat"), size=15, fill=INK)
        s.text(COL + 830, ry, str(st["runs"]), size=15, fill=INK, anchor="end")
        s.text(COL + WIDE, ry, st["updated"], size=15, fill=SEC, anchor="end")
        s.line(COL, ry + 28, COL + WIDE, ry + 28, stroke=LINE)
    P.y = ty + 48 + 3 * 52 + 28
    button(s, COL, P.y + 24, "Новая стратегия", "ghost", icon="plus", h=44)
    P.y += 68
    P.finish()
    return P.save()


def chapter1():
    P = Page(1)
    P.sections = [("1.1", "Снапшоты"), ("1.2", "Момент доступности"), ("1.3", "Торговый календарь")]
    s = P.s
    cur = D.DATASET_CURRENT
    top = P.chapter_head(
        [("Источник", "MOEX ISS"), ("Снапшотов", str(len(D.DATASETS))), ("В отчёте", cur["id"]), ("Строк", cur["rows"])],
        "Прогоны не скачивают данные заново: исследование ссылается на ==снимок с фиксированным хэшем==. "
        "Если биржа поправит историю, старые прогоны всё равно повторятся на тех же строках.")
    P.note(top, "Снапшот ds-0007", [("получен 26.09.2026 18:40", False), ("sha 3f9a…c21e", True), ("схема v2", True)])
    y = P.y + 28
    bw = button(s, COL, y, "Загрузить новый снапшот", "ink", icon="download", h=44)
    s.text(COL + bw + 16, y + 27, "MOEX ISS, дневные бары; старые снапшоты не меняются", size=13, fill=SEC)
    P.y = y + 44

    # 1.1 таблица снапшотов
    P.h2("1.1", "Из пяти снапшотов в работе два, генератор синтетики появится после MVP")
    ty = P.wide() + 40
    cols = [(0, "Снапшот"), (150, "Тикеры"), (410, "Период"), (570, "Получен"), (680, "Хэш и схема"), (800, "Статус"), (WIDE, "Прогоны")]
    for dx, lab in cols:
        s.text(COL + dx, ty, lab, size=13, fill=SEC, anchor="end" if dx == WIDE else "start")
    s.line(COL, ty + 12, COL + WIDE, ty + 12, stroke=INK)
    ry = ty + 12
    for i, ds in enumerate(D.DATASETS):
        mvp = ds["status"] == "после MVP"
        fg = TER if mvp else INK
        tl = wrap(ds["tickers"], 250, 14)
        rh = 28 + max(2, len(tl)) * 20 + 12
        b = ry + 30
        if i == 0:
            s.rect(COL - 16, ry + 1, WIDE + 32, rh - 1, fill="#FFFBE6")
            mark_rect(s, COL, b, measure(ds["id"], 15, 700, True), 15)
        s.text(COL, b, ds["id"], size=15, fill=fg, weight=700, mono=True)
        for k, ln in enumerate(wrap(ds["source"], 136, 13)[:2]):
            s.text(COL, b + 20 + k * 18, ln, size=13, fill=SEC if not mvp else TER)
        for k, ln in enumerate(tl):
            s.text(COL + 150, b + k * 20, ln, size=14, fill=fg)
        pl = ds["period"].split(" — ")
        s.text(COL + 410, b, pl[0] + (" —" if len(pl) > 1 else ""), size=14, fill=fg)
        if len(pl) > 1:
            s.text(COL + 410, b + 20, pl[1], size=14, fill=fg)
        s.text(COL + 410, b + 40, ds["interval"] + ", " + (ds["rows"] + " строк" if ds["rows"] != "—" else "по запросу"), size=12, fill=SEC)
        f = ds["fetched"].split(" ")
        s.text(COL + 570, b, f[0], size=14, fill=fg)
        if len(f) > 1:
            s.text(COL + 570, b + 20, f[1], size=13, fill=SEC)
        s.text(COL + 680, b, ds["sha"], size=13, fill=fg, mono=True)
        s.text(COL + 680, b + 20, "схема " + ds["schema"], size=12, fill=SEC)
        s.text(COL + WIDE, b, str(ds["used_in"]), size=15, fill=fg, weight=700, anchor="end")
        lvl = {"актуальный": "ok", "после MVP": "mvp", "устаревшая схема": "warning"}.get(ds["status"], "info")
        badge(s, COL + 800, b - 17, ds["status"], lvl)
        ry += rh
        s.line(COL, ry, COL + WIDE, ry, stroke=LINE)
    P.y = ry

    # 1.2 момент доступности
    P.h2("1.2", "Стратегия видит close дня t только вечером, а торгует по open следующего утра")
    t = P.p("Для каждого поля снапшот хранит момент, когда значение стало известно рынку. Движок "
            "не отдаёт стратегии поле раньше этого момента, а ==adj_close не отдаёт вовсе==: его "
            "пересчитывают задним числом, когда объявлены дивиденды.")
    P.note(t, "Время биржи", [("Московское время,", False), ("основная сессия акций MOEX", False)])
    # шкала двух дней
    gy = P.wide() + 80
    x0, x1 = COL, COL + WIDE
    s.line(x0, gy, x1, gy, stroke=INK, sw=1.5)
    day_w = (x1 - x0) / 2
    # день t: 10:00 … 18:50, ночь, день t+1: 10:00
    p_open, p_close, p_dec, p_next = x0 + 60, x0 + 400, x0 + 560, x0 + 720
    pts = [(p_open, "10:00", "день t", "open", "открытие торгов"),
           (p_close, "18:50", None, "high, low, close, volume", "после закрытия"),
           (p_next, "10:00", "день t+1", "open t+1", "исполнение заявки")]
    s.rect(p_open, gy - 6, p_close - p_open, 12, fill="#E4E9F0", rx=2)
    s.rect(p_next, gy - 6, x1 - 40 - p_next, 12, fill="#E4E9F0", rx=2)
    s.text((p_open + p_close) / 2, gy - 22, "основная сессия дня t", size=12, fill=SEC, anchor="middle")
    s.text((p_next + x1 - 40) / 2, gy - 22, "основная сессия дня t+1", size=12, fill=SEC, anchor="middle")
    for px, tm, day, fld, what in pts:
        s.circle(px, gy, 6, fill=SHEET, stroke=INK, sw=2)
        s.text(px, gy + 32, tm, size=15, fill=INK, weight=700, anchor="middle")
        s.text(px, gy + 52, fld, size=13, fill=INK, mono=True, anchor="middle")
        s.text(px, gy + 72, what, size=12, fill=SEC, anchor="middle")
        if day:
            s.text(px, gy - 48, day, size=13, fill=INK, weight=700, anchor="middle")
    # момент решения
    dx = p_dec
    s.line(dx, gy - 40, dx, gy + 76, stroke=INK, sw=1, dash="3 3")
    lab = "решение стратегии"
    mark_rect(s, dx + 8, gy - 30, measure(lab, 13, 700), 13)
    s.text(dx + 8, gy - 30, lab, size=13, fill=INK, weight=700)
    # стрелка от решения к исполнению
    ex = p_next
    s.path(f"M{dx:.1f} {gy + 96:.1f} C{dx + 40:.1f} {gy + 120:.1f} {ex - 40:.1f} {gy + 120:.1f} {ex:.1f} {gy + 96:.1f}", stroke=SEC, sw=1.25)
    s.path(f"M{ex - 7:.1f} {gy + 93:.1f} L{ex:.1f} {gy + 96:.1f} L{ex - 3:.1f} {gy + 103:.1f}", stroke=SEC, sw=1.25)
    s.text((dx + ex) / 2, gy + 132, "заявка ждёт следующего открытия", size=12, fill=SEC, anchor="middle")
    P.y = gy + 150
    P.caption("1.1", "Когда поля бара становятся доступны стратегии. Сигнал по close дня t исполняется по open дня t+1.")
    # таблица полей
    ty = P.y + 32
    s.text(COL, ty, "Поле", size=13, fill=SEC)
    s.text(COL + 200, ty, "Когда доступно", size=13, fill=SEC)
    s.line(COL, ty + 12, COL + COLW, ty + 12, stroke=INK)
    for i, (fld, when) in enumerate(D.DATASET_FIELDS):
        ry = ty + 42 + i * 36
        bad = "запрещено" in when
        s.text(COL, ry, fld, size=14, fill=NEG if bad else INK, mono=True, weight=700 if bad else 400)
        txt = when.replace(" — запрещено", "") if bad else when
        s.text(COL + 200, ry, txt, size=15, fill=INK)
        if bad:
            badge(s, COL + 200 + measure(txt, 15) + 12, ry - 17, "запрещено", "error")
        s.line(COL, ry + 14, COL + COLW, ry + 14, stroke=LINE)
    P.y = ty + 42 + 4 * 36 + 14

    # 1.3 календарь
    P.h2("1.3", "Весной 2022 года торговый календарь пропускает 18 дней")
    t = P.p("С 28 февраля по 23 марта 2022 года торги акциями на Мосбирже не проводились. Движок не "
            "заполняет эти дни ценами: ==позиции просто ждут открытия рынка==, а просадка за это время "
            "отражается одним гэпом 24 марта.")
    P.note(t, "Разрыв в календаре", [(f"{D.CALENDAR_GAP[0]} — {D.CALENDAR_GAP[1]}", False), (D.CALENDAR_GAP[2], False)])
    cy = P.wide() + 48
    cell = 40
    months = [("Февраль 2022", 2022, 2), ("Март 2022", 2022, 3)]
    import calendar
    for mi, (mname, yr, mo) in enumerate(months):
        mx = COL + mi * (cell * 7 + 56)
        s.text(mx, cy, mname, size=15, fill=INK, weight=700)
        for k, wd in enumerate(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]):
            s.text(mx + k * cell + cell / 2, cy + 28, wd, size=12, fill=SEC, anchor="middle")
        first, ndays = calendar.monthrange(yr, mo)
        for dday in range(1, ndays + 1):
            pos = first + dday - 1
            col, row = pos % 7, pos // 7
            bx, by = mx + col * cell, cy + 40 + row * cell
            dd_ = date(yr, mo, dday)
            weekend = col >= 5
            gap = date(2022, 2, 28) <= dd_ <= date(2022, 3, 23) and not weekend
            if gap:
                s.rect(bx + 2, by + 2, cell - 4, cell - 4, fill=SHEET, rx=6, stroke=NEU)
                hatch(s, bx + 2, by + 2, cell - 4, cell - 4, color="#C4CCD8", step=5)
            elif not weekend:
                s.rect(bx + 2, by + 2, cell - 4, cell - 4, fill="#E9EDF2", rx=6)
            if dd_ == date(2022, 2, 24):
                s.rect(bx + 2, by + 2, cell - 4, cell - 4, fill=SHEET, rx=6, stroke=NEG, sw=2)
            s.text(bx + cell / 2, by + cell / 2 + 5, str(dday), size=13,
                   fill=TER if weekend else (NEG if dd_ == date(2022, 2, 24) else INK),
                   weight=700 if dd_ == date(2022, 2, 24) else 400, anchor="middle")
    # легенда справа от календаря
    lx = COL + 2 * (cell * 7 + 56) + 16
    leg = [("#E9EDF2", None, "торговый день"), (SHEET, "hatch", "торгов нет, день пропущен"), (SHEET, NEG, "24.02.2022, стресс-событие")]
    for k, (f, st, lab) in enumerate(leg):
        ly = cy + 48 + k * 32
        if st == "hatch":
            s.rect(lx, ly, 20, 20, fill=f, rx=4, stroke=NEU)
            hatch(s, lx, ly, 20, 20, color="#C4CCD8", step=5)
        else:
            s.rect(lx, ly, 20, 20, fill=f, rx=4, stroke=st, sw=2 if st else 1)
        s.text(lx + 32, ly + 15, lab, size=14, fill=INK)
    P.y = cy + 40 + 5 * cell
    P.caption("1.2", "Торговый календарь MOEX за февраль и март 2022 года. В ряду данных 1 545 торговых дней за 2020–2025 годы, разрыв не заполняется.", width=WIDE)
    P.finish()
    return P.save()


def radio(s, x, y, on):
    s.circle(x + 9, y + 9, 9, fill=SHEET, stroke=INK if on else "#B4BDCA", sw=1.5)
    if on:
        s.circle(x + 9, y + 9, 4.5, fill=INK)


def chapter3():
    P = Page(3)
    P.sections = [("3.1", "Данные и капитал"), ("3.2", "Издержки"), ("3.3", "Стресс-сценарий"), ("3.4", "Режим и seed")]
    s = P.s
    C = D.RUN_CONFIG
    top = P.chapter_head(
        [("Стратегия", "SMA 20/50, версия 4"), ("Датасет", C["dataset"]), ("Будет создан", "новый прогон")],
        "Всё, что задано на этой странице, войдёт в отчёт без изменений. Во время прогона параметры "
        "не меняются: ==любая правка — это новый прогон== с новым идентификатором.")
    P.note(top, "Черновик настроек", [("сохранён 05.10.2026 14:21", False), ("автор Денис Муруев", False)])

    # 3.1
    P.h2("3.1", "Прогон охватывает шесть лет и 1 545 торговых дней")
    y = P.y + 32
    fw = (COLW - 16) / 2
    field(s, COL, y, fw, "Датасет", "ds-0007, sha 3f9a…c21e")
    field(s, COL + fw + 16, y, fw, "Период", C["period"])
    field(s, COL, y + 72, fw, "Начальный капитал", "1 000 000", suffix="₽")
    field(s, COL + fw + 16, y + 72, fw, "Бары", C["bars"])
    P.note(y, "Почему 2020–2025", [("Период включает оба стресс-события: март 2020 и 24.02.2022", False)])
    P.y = y + 128

    # 3.2
    P.h2("3.2", "Заявка проходит шесть поправок, до сделки")
    t = P.p("Издержки считаются от оборота и списываются в момент исполнения. Задержку и лимит "
            "ликвидности в честном режиме выключить нельзя: ==именно они отличают честный прогон от наивного==.")
    rows = [("Комиссия брокера", C["commission"], None, False),
            ("Биржевой сбор", C["exchange_fee"], None, False),
            ("Спред", C["spread"], None, False),
            ("Проскальзывание", C["slippage"], None, False),
            ("Лимит ликвидности", "не больше 5 % объёма бара", "остаток — частичное исполнение или отказ", True),
            ("Задержка исполнения", C["delay"], "open t+1, сигнал по close t", True),
            ("Правило остановки", C["stop_rule"], None, False)]
    ry = P.wide() + 28
    P.note(ry + 3 * 56, "Проскальзывание", [("0,10 % плюс половина доли заявки в объёме бара", False)])
    P.note(ry + 4 * 56, "Поля с замком", [("Фиксированы для честного режима; в наивном прогоне отключены", False)])
    s.line(COL, ry, COL + COLW, ry, stroke=INK)
    for i, (k, v, sub, locked) in enumerate(rows):
        rh = 56
        s.text(COL, ry + 33, k, size=15, fill=INK, weight=700)
        fx = COL + 220
        fwid = COLW - 220
        s.rect(fx, ry + 8, fwid, 40, fill=SOFT if locked else SHEET, rx=10, stroke=LINE)
        s.text(fx + 14, ry + 33, fit(nb(v), fwid - 56, 15, tag="cfg"), size=15, fill=INK)
        if locked:
            s.icon("lock", fx + fwid - 30, ry + 20, SEC)
        if sub:
            s.text(fx + 14, ry + 66, sub, size=12, fill=SEC)
            rh += 18
        ry += rh
        s.line(COL, ry, COL + COLW, ry, stroke=LINE)
    P.y = ry

    # 3.3 стресс
    P.h2("3.3", "Стресс-сценарий повторит шок 24 февраля 2022 года")
    t = P.p("Сценарий накладывает шок на исторический ряд: гэп по индексу, рост волатильности, падение "
            "объёмов и рост проскальзывания. Выберите готовый или задайте свой.")
    ty = P.wide() + 36
    hx = [(COL + 520, "Гэп"), (COL + 640, "Волатильность"), (COL + 780, "Объём"), (COL + WIDE, "Проскальзывание")]
    s.text(COL + 36, ty, "Сценарий", size=13, fill=SEC)
    for x, lab in hx:
        s.text(x, ty, lab, size=13, fill=SEC, anchor="end" if x == COL + WIDE else "start")
    s.line(COL, ty + 12, COL + WIDE, ty + 12, stroke=INK)
    ry = ty + 12
    for i, sp in enumerate(D.STRESS_PRESETS):
        on = i == 0
        custom = sp["name"] == "Свой сценарий"
        rh = 72 if not custom else 84
        if on:
            s.rect(COL - 16, ry + 1, WIDE + 32, rh - 1, fill="#FFFBE6")
        radio(s, COL, ry + 18, on)
        if on:
            mark_rect(s, COL + 36, ry + 32, measure(sp["name"], 16, 700), 16)
        s.text(COL + 36, ry + 32, sp["name"], size=16, fill=INK, weight=700)
        s.text(COL + 36, ry + 54, fit(sp["desc"], 460, 13, tag="stress"), size=13, fill=SEC)
        vals = [sp["gap"], sp["vol"], sp["volume"], sp["slip"]]
        if not custom:
            for (x, _), v in zip(hx, vals):
                s.text(x, ry + 32, v, size=15, fill=INK, weight=700, anchor="end" if x == COL + WIDE else "start")
        else:
            for k, ((x, lab), v) in enumerate(zip(hx, vals)):
                fx = x - 8 if x != COL + WIDE else x - 112
                s.rect(fx, ry + 14, 104, 44, fill=SHEET, rx=10, stroke=LINE)
                s.text(fx + 14, ry + 41, v, size=15, fill=TER)
        ry += rh
        s.line(COL, ry, COL + WIDE, ry, stroke=LINE)
    P.y = ry

    # 3.4 режим
    P.h2("3.4", "Наивный и честный прогоны пойдут вместе на одном seed")
    y = P.wide() + 32
    opts = [("Наивный и честный прогон вместе", "Два прогона на одном seed; разница раскладывается по вкладам в главе 5", True),
            ("Проверка walk-forward", C["walk_forward"] + "; результаты в главе 6", True),
            ("Шорты и маржинальная торговля", "Будет доступно после MVP", False)]
    for k, (lab, sub, on) in enumerate(opts):
        oy = y + k * 72
        toggle(s, COL, oy, on)
        s.text(COL + 56, oy + 17, lab, size=16, fill=INK if k < 2 else TER, weight=700)
        s.text(COL + 56, oy + 40, sub, size=13, fill=SEC if k < 2 else TER)
    fy = y + 3 * 72 + 8
    field(s, COL, fy, 300, "Seed генератора", C["seed"], mono=True)
    button(s, COL + 316, fy + 6, "Новый seed", "flat", icon="repeat", h=44)
    P.note(fy, "Зачем seed", [("Фиксирует порядок частичных исполнений и стресс-шоков", False)])
    P.y = fy + 56

    # запуск
    y = P.y + 56
    s.line(COL, y, COL + WIDE, y, stroke=LINE)
    y += 32
    bw = button(s, COL, y, "Запустить прогон", "primary", icon="play", h=56, size=17)
    s.text(COL + bw + 24, y + 24, "Будут созданы два прогона: наивный и честный", size=15, fill=INK, weight=700)
    s.text(COL + bw + 24, y + 44, "ds-0007, 03.01.2020 — 30.12.2025, seed 20261005, стресс 24.02.2022", size=13, fill=SEC)
    button(s, COL + WIDE - 190, y + 6, "Сохранить черновик", "ghost", h=44, w=190)
    P.y = y + 56
    P.finish()
    return P.save()


MOM = "#3F63C9"


def chapter5():
    P = Page(5)
    P.sections = [("5.1", "Разложение разницы"), ("5.2", "Четыре стратегии"), ("5.3", "Кривые капитала")]
    s = P.s
    top = P.chapter_head(
        [("Прогоны", "run-0141 и run-0142"), ("Датасет", "ds-0007"), ("Стратегий в сравнении", "4")],
        "Наивный прогон показал +84,2 %, честный — +31,6 %. Разница в 52,6 п.п. раскладывается на шесть "
        "вкладов, и самый крупный из них — ==не комиссии, а задержка исполнения на один день==.")
    P.note(top, "Пара прогонов", [("одинаковые снапшот, код и seed", False), ("run-0141 наивный", True), ("run-0142 честный", True)])

    # 5.1 водопад
    P.h2("5.1", "Задержка на один день стоит больше, чем все комиссии и сборы вместе")
    t = P.p("Каждая строка — вклад одной поправки честного режима. Вклады складываются без остатка: "
            " от 84,2 % наивного прогона до ==31,6 %== честного.")
    P.flag(t, "warning", D.FLAGS[0]["text"])
    wy = P.wide() + 40
    lx, bx0, bw = COL, COL + 330, 520           # подписи, область столбиков
    sc = bw / 90.0
    X = lambda v: bx0 + v * sc
    rows = [("Наивный прогон", 84.2, None, "start")] + [(n, v, r, "d") for n, v, r in D.DELTA_BREAKDOWN] + [("Честный прогон", 31.6, D.COSTS_TOTAL, "end")]
    rh = 42
    # шкала
    for v in (0, 20, 40, 60, 80):
        s.line(X(v), wy - 8, X(v), wy + rh * len(rows), stroke=LINE, dash="2 4" if v else None)
        s.text(X(v), wy - 16, f"{v} %", size=12, fill=SEC, anchor="middle")
    cum = 84.2
    for i, (name, v, rub, kind) in enumerate(rows):
        ry = wy + i * rh
        b = ry + rh / 2 + 5
        bold = kind != "d"
        s.text(lx, b, fit(nb(name), 320, 15, 700 if bold else 400, tag="wf"), size=15, fill=INK, weight=700 if bold else 400)
        if kind == "start":
            s.rect(X(0), ry + 9, X(v) - X(0), rh - 18, fill=NEU, rx=2)
            s.text(X(v) + 10, b, "+84,2 %", size=15, fill=INK, weight=700)
        elif kind == "end":
            s.rect(X(0), ry + 9, X(v) - X(0), rh - 18, fill=INK, rx=2)
            lab = "+31,6 %"
            mark_rect(s, X(v) + 10, b, measure(lab, 15, 700), 15)
            s.text(X(v) + 10, b, lab, size=15, fill=INK, weight=700)
        else:
            new = cum + v
            s.rect(X(new), ry + 9, X(cum) - X(new), rh - 18, fill=NEG, rx=2, opacity=0.85 if i == 1 else 0.55)
            s.line(X(new), ry + rh - 9, X(new), ry + rh + 9, stroke=NEG, sw=1)
            lab = fmt_pct(v, 1).replace(" %", " п.п.")
            s.text(X(cum) + 10, b, lab, size=15, fill=NEG, weight=700)
            cum = new
        if rub:
            s.text(COL + WIDE, b, rub, size=14, fill=SEC, anchor="end")
        s.line(lx, ry + rh, COL + WIDE, ry + rh, stroke=LINE)
    s.text(COL + WIDE, wy - 16, "в рублях", size=12, fill=SEC, anchor="end")
    P.y = wy + rh * len(rows)
    P.caption("5.1", "Разложение разницы между наивным и честным прогоном SMA 20/50, п.п. доходности за период. "
                     "Денежные издержки за период — 259 300 ₽.")

    # 5.2 таблица стратегий
    P.h2("5.2", "У RSI-отката издержки меняют знак результата: +38,5 % превращаются в −6,8 %")
    t = P.p("Флаги срабатывают автоматически: издержки больше половины прибыли, смена знака результата "
            "и наивный Sharpe выше 3 — признак того, что результат слишком хорош.")
    ty = P.wide() + 40
    cols = [(0, "Стратегия", "start"), (160, "Наивный и честный", "start"), (490, "Честный", "end"), (570, "Sharpe", "end"),
            (660, "Просадка", "end"), (730, "Оборот", "end"), (760, "Флаг", "start")]
    for dx, lab, a in cols:
        s.text(COL + dx, ty, lab, size=13, fill=SEC, anchor=a)
    s.line(COL, ty + 12, COL + WIDE, ty + 12, stroke=INK)
    dx0, dw = COL + 160, 240
    DX = lambda v: dx0 + (v + 10) / 100 * dw
    for i, c in enumerate(D.COMPARISON):
        ry = ty + 12 + i * 60
        b = ry + 36
        s.text(COL, b, c["name"], size=15, fill=INK, weight=700)
        # гантель наивный → честный
        s.line(DX(0), ry + 14, DX(0), ry + 50, stroke=LINE)
        s.line(DX(c["n"]), b - 5, DX(c["h"]), b - 5, stroke=NEU, sw=2)
        s.circle(DX(c["n"]), b - 5, 5, fill=SHEET, stroke=SEC, sw=1.5)
        s.circle(DX(c["h"]), b - 5, 5, fill=INK if c["h"] >= 0 else NEG)
        s.text(COL + 490, b, c["honest"], size=15, fill=NEG if c["h"] < 0 else INK, weight=700, anchor="end")
        s.text(COL + 490, b + 18, "наивный " + c["naive"], size=12, fill=SEC, anchor="end")
        s.text(COL + 570, b, c["sharpe"], size=15, fill=INK, anchor="end")
        s.text(COL + 570, b + 18, c["sharpe_naive"], size=12, fill=SEC, anchor="end")
        s.text(COL + 660, b, c["dd"], size=15, fill=INK, anchor="end")
        s.text(COL + 730, b, c["turnover"], size=15, fill=INK, anchor="end")
        if c["flag"]:
            lvl = "error" if "знак" in c["flag"] else "warning"
            badge(s, COL + 760, b - 17, c["flag"], lvl)
        else:
            s.text(COL + 760, b, "без флагов", size=13, fill=TER)
        s.line(COL, ry + 60, COL + WIDE, ry + 60, stroke=LINE)
    # мини-шкала под гантелями
    sy = ty + 12 + 4 * 60 + 18
    for v in (0, 40, 80):
        s.text(DX(v), sy, f"{v} %", size=11, fill=SEC, anchor="middle")
    s.circle(COL + 760, sy - 4, 4, fill=SHEET, stroke=SEC, sw=1.5)
    s.text(COL + 770, sy, "наивный", size=12, fill=SEC)
    s.circle(COL + 840, sy - 4, 4, fill=INK)
    s.text(COL + 850, sy, "честный", size=12, fill=SEC)
    P.y = sy + 8

    # 5.3 кривые
    P.h2("5.3", "После издержек индекс обгоняют только SMA и моментум")
    gx, gy, gw, gh = COL, P.wide() + 48, 800, 260
    vmin, vmax = 0.5, 1.7
    Y = lambda v: gy + gh - gh * (v - vmin) / (vmax - vmin)
    for v in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6):
        s.line(gx, Y(v), gx + gw, Y(v), stroke=LINE if v != 1.0 else NEU, dash=None if v == 1.0 else "2 4")
        s.text(gx + gw + 8, Y(v) + 4, f"{v:.1f} млн".replace(".", ","), size=12, fill=SEC)
    e0 = xdate(date(2022, 2, 24), gx, gw)
    s.line(e0, gy, e0, gy + gh, stroke=NEG, sw=1, dash="3 3")
    s.text(e0 + 6, gy + 12, "24.02.2022", size=12, fill=NEG, weight=700)
    series = [(D.EQUITY_IMOEX, NEU, 1.5, None, "IMOEX", "+9,4 %"),
              (D.EQUITY_RSI, SEC, 1.5, "5 4", "RSI-откат", "−6,8 %"),
              (D.EQUITY_MOMENTUM, MOM, 2, None, "Моментум 3М", "+44,9 %"),
              (D.EQUITY_HONEST, INK, 2.5, None, "SMA 20/50", "+31,6 %")]
    ends = []
    for vals, col, sw, dash, lab, res in series:
        line_by_date(s, vals, gx, gy, gw, gh, vmin, vmax, col, sw=sw, dash=dash)
        s.circle(gx + gw, Y(vals[-1]), 3.5, fill=col)
        ends.append([Y(vals[-1]), col, lab, res])
    ends.sort()
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 20:
            ends[k][0] = ends[k - 1][0] + 20
    for py, col, lab, res in ends:
        s.text(gx + gw + 70, py + 4, lab, size=13, fill=INK if col in (INK, MOM) else SEC, weight=700 if col == INK else 400)
        s.text(gx + gw + 70 + measure(lab, 13, 700 if col == INK else 400) + 6, py + 4, res, size=13, fill=INK if col == INK else SEC, weight=700 if col == INK else 400)
    year_axis(s, gx, gw, gy + gh + 4)
    P.y = gy + gh + 28
    P.caption("5.3", "Капитал четырёх стратегий в честном режиме, млн ₽, 03.01.2020 — 30.12.2025.")
    y = P.y + 24
    bx = button(s, COL, y, "Добавить стратегию в сравнение", "ghost", icon="plus", h=44) + 8
    button(s, COL + bx, y, "Скачать таблицу", "ghost", icon="download", h=44)
    P.y = y + 44
    P.finish()
    return P.save()


def chapter6():
    P = Page(6)
    P.sections = [("6.1", "Окна и параметры"), ("6.2", "В выборке и вне её"), ("6.3", "Сводка")]
    s = P.s
    WS = D.WF_SUMMARY
    top = P.chapter_head(
        [("Окон", WS["windows"]), ("Подбор", "1 год"), ("Проверка", "3 месяца"), ("Сдвиг", "3 месяца")],
        "На отрезке подбора параметры дают в среднем +9,0 % за квартал, на следующих трёх месяцах — "
        "только ==+0,5 %==. Почти весь результат подбора — подгонка под историю, а не устойчивое правило.")
    P.note(top, "Схема walk-forward", [("1 год подбор, 3 месяца проверка,", False), ("сдвиг 3 месяца; 20 окон", False), ("2021–2025 вне выборки", False)])

    # крупные числа
    y = max(P.y, P.note_bottom) + 36
    s.line(COL, y, COL + WIDE, y, stroke=LINE)
    big = [(0, WS["degradation"], "деградация вне выборки", "с +9,0 % до +0,5 % за квартал", True),
           (300, WS["positive"], "прибыльных окон", "вне выборки", False),
           (600, WS["oos_total"], "итог вне выборки", "сумма 20 кварталов проверки", False)]
    for dx, num, lab, sub, hl in big:
        bx = COL + dx
        base = y + 80
        if hl:
            mark_rect(s, bx, base, measure(num, 64, 700), 64, pad=4)
        s.text(bx, base, num, size=64, fill=INK, weight=700)
        s.text(bx, base + 32, lab, size=14, fill=INK, weight=700)
        s.text(bx, base + 52, sub, size=13, fill=SEC)
    P.y = y + 160
    s.line(COL, P.y, COL + WIDE, P.y, stroke=LINE)

    # 6.1 схема окон
    P.h2("6.1", "Окно сдвигается на квартал, и подбор почти каждый раз выбирает другие параметры")
    t = P.p("Слева — двадцать окон: светлая полоса — год подбора, тёмная — квартал проверки. Справа — "
            "параметры, выбранные на подборе, и результат проверки. ==20/50 выбран в 9 окнах из 20==.")
    gx, gw = COL + 40, 560
    t0, t1 = date(2020, 1, 1), date(2026, 1, 1)
    TX = lambda d: gx + gw * (d - t0).days / (t1 - t0).days
    ty = P.wide() + 40
    s.text(COL, ty, "№", size=13, fill=SEC)
    s.text(gx, ty, "Подбор и проверка", size=13, fill=SEC)
    px, ix, ox = COL + 660, COL + 820, COL + WIDE
    s.text(px, ty, "Параметры", size=13, fill=SEC)
    s.text(ix, ty, "В выборке", size=13, fill=SEC, anchor="end")
    s.text(ox, ty, "Вне выборки", size=13, fill=SEC, anchor="end")
    s.line(COL, ty + 12, COL + WIDE, ty + 12, stroke=INK)
    rh = 22
    for yr in range(2020, 2027):
        xx = TX(date(yr, 1, 1))
        s.line(xx, ty + 16, xx, ty + 16 + rh * 20, stroke=LINE, dash="2 4")
    for w_ in D.WALK_FORWARD:
        i = w_["n"] - 1
        ry = ty + 16 + i * rh
        b = ry + 15
        s.text(COL, b, f"{w_['n']:02d}", size=13, fill=SEC, mono=True)
        m = i * 3
        ts = date(2021 + m // 12, m % 12 + 1, 1)
        tr = date(ts.year - 1, ts.month, 1)
        te_m = m + 3
        te = date(2021 + te_m // 12, te_m % 12 + 1, 1)
        s.rect(TX(tr), ry + 5, TX(ts) - TX(tr), 12, fill="#DCE2EA", rx=2)
        s.rect(TX(ts), ry + 5, TX(te) - TX(ts), 12, fill=INK, rx=2)
        stable = w_["params"] == "20/50"
        s.text(px, b, w_["params"], size=13, fill=INK, mono=True, weight=700 if stable else 400)
        s.text(ix, b, fmt_pct(w_["train_ret"]), size=13, fill=SEC, anchor="end")
        v = w_["test_ret"]
        s.text(ox, b, fmt_pct(v), size=13, fill=POS if v >= 0 else NEG, weight=700, anchor="end")
    by = ty + 16 + 20 * rh
    s.line(COL, by, COL + WIDE, by, stroke=LINE)
    for yr in range(2020, 2026):
        s.text(TX(date(yr, 1, 1)) + 4, by + 18, str(yr), size=12, fill=SEC)
    P.y = by + 30
    P.caption("6.1", "Окна walk-forward: год подбора параметров SMA (быстрая/медленная) и квартал проверки вне выборки.")

    # 6.2 столбики
    P.h2("6.2", "Вне выборки результат ни разу не догнал подбор")
    t = P.p("Серые столбики — доходность на годе подбора, приведённая к кварталу. Цветные — следующий "
            "квартал, который стратегия не видела. Самый тяжёлый квартал — ==I кв. 2023, −6,7 %==.")
    cx, cy, cw, ch = COL, P.wide() + 40, 900, 200
    vmin, vmax = -8, 14
    zero = cy + ch * vmax / (vmax - vmin)
    for v in (-5, 0, 5, 10):
        yy = cy + ch * (vmax - v) / (vmax - vmin)
        s.line(cx, yy, cx + cw, yy, stroke=INK if v == 0 else LINE, dash=None if v == 0 else "2 4")
        s.text(cx + cw + 10, yy + 4, fmt_pct(v, 0) if v else "0 %", size=12, fill=SEC)
    gwid = cw / 20
    for w_ in D.WALK_FORWARD:
        i = w_["n"] - 1
        gx0 = cx + i * gwid
        bw_ = gwid * 0.34
        for k, (v, colr) in enumerate([(w_["train_ret"], "#C9D1DC"), (w_["test_ret"], POS if w_["test_ret"] >= 0 else NEG)]):
            x = gx0 + gwid * 0.14 + k * (bw_ + 2)
            top_ = cy + ch * (vmax - v) / (vmax - vmin)
            s.rect(x, min(top_, zero), bw_, abs(zero - top_) or 1, fill=colr, rx=1.5)
        if i % 4 == 0:
            s.text(gx0 + gwid / 2, cy + ch + 20, w_["test"], size=11, fill=SEC, anchor="start")
    s.rect(cx, cy + ch + 34, 12, 12, fill="#C9D1DC", rx=2)
    s.text(cx + 18, cy + ch + 45, "в выборке, за квартал", size=12, fill=SEC)
    s.rect(cx + 180, cy + ch + 34, 12, 12, fill=POS, rx=2)
    s.rect(cx + 194, cy + ch + 34, 12, 12, fill=NEG, rx=2)
    s.text(cx + 212, cy + ch + 45, "вне выборки: прибыль или убыток", size=12, fill=SEC)
    P.y = cy + ch + 52
    P.caption("6.2", "Доходность за квартал в выборке и вне выборки по 20 окнам, %.")

    # 6.3 сводка
    P.h2("6.3", "Для защиты: правило ловит тренды, но подбор параметров почти ничего не добавляет")
    t = P.p("Прибыльны 12 кварталов из 20 — чуть больше половины. Деградация на 95 % показывает, что "
            "результат подбора на истории нельзя переносить в будущее как есть.")
    rows = [("Окон проверки", WS["windows"]), ("Прибыльных окон", WS["positive"]),
            ("Средняя доходность в выборке", WS["is_avg"]), ("Средняя доходность вне выборки", WS["oos_avg"]),
            ("Деградация", WS["degradation"]), ("Итог вне выборки", WS["oos_total"]),
            ("Стабильность параметров", WS["stable_param"])]
    ry = P.y + 28
    for k, v in rows:
        s.text(COL, ry + 20, k, size=15, fill=INK)
        s.text(COL + COLW, ry + 20, v, size=15, fill=INK, weight=700, anchor="end")
        s.line(COL, ry + 34, COL + COLW, ry + 34, stroke=LINE)
        ry += 36
    P.note(P.y + 28, "Как считается деградация", [("1 − (средняя вне выборки / средняя в выборке)", False)])
    P.y = ry
    P.finish()
    return P.save()


def chip(s, x, y, label, on=False, count=None):
    tw = measure(label, 14, 700 if on else 400)
    cw = measure(count, 13) + 8 if count else 0
    w = tw + cw + 28
    s.rect(x, y, w, 32, fill=MARK if on else SHEET, rx=16, stroke=None if on else LINE)
    s.text(x + 14, y + 21, label, size=14, fill="#000000" if on else INK, weight=700 if on else 400)
    if count:
        s.text(x + 14 + tw + 8, y + 21, count, size=13, fill="#000000" if on else SEC)
    return w


def select(s, x, y, w, label, value):
    s.rect(x, y, w, 44, fill=SHEET, rx=10, stroke=LINE)
    s.text(x + 14, y + 18, label, size=11, fill=SEC)
    s.text(x + 14, y + 35, fit(value, w - 44, 14, tag="sel"), size=14, fill=INK)
    s.icon("chevron-down", x + w - 28, y + 14, SEC)


def chapter7():
    P = Page(7)
    P.sections = [("7.1", "Все прогоны"), ("7.2", "Невалидный прогон"), ("7.3", "Как читать статусы")]
    s = P.s
    runs = D.RUNS
    n_valid = sum(r["status"] == "valid" for r in runs)
    n_warn = sum(r["status"] == "warning" for r in runs)
    n_inv = sum(r["status"] == "invalid" for r in runs)
    top = P.chapter_head(
        [("Прогонов", str(len(runs))), ("Валидных", str(n_valid)), ("С пометкой", str(n_warn)), ("Невалидных", str(n_inv))],
        "История хранит каждый запуск, включая неудачные. ==Невалидный прогон нельзя сравнивать==, "
        "но его можно открыть и увидеть, в какой строке стратегия заглянула в будущее.")
    P.note(top, "Хранение", [("Прогоны не удаляются и не перезаписываются", False)])

    # 7.1 таблица
    P.h2("7.1", "Последние два прогона — наивный и честный запуск SMA 20/50")
    y = P.wide() + 32
    # фильтры
    s.rect(COL, y, 300, 44, fill=SHEET, rx=10, stroke=LINE)
    s.icon("search", COL + 14, y + 14, SEC)
    s.text(COL + 40, y + 27, "Поиск по прогону или стратегии", size=14, fill=TER)
    sw_ = (WIDE - 300 - 16 * 4) / 4
    for k, (lab, val) in enumerate([("Стратегия", "Все стратегии"), ("Режим", "Все режимы"), ("Датасет", "Все датасеты"), ("Автор", "Все авторы")]):
        select(s, COL + 316 + k * (sw_ + 16), y, sw_, lab, val)
    y += 60
    x = COL
    for lab, cnt, on in [("Все", str(len(runs)), True), ("Валиден", str(n_valid), False), ("С пометкой", str(n_warn), False), ("Невалиден", str(n_inv), False)]:
        x += chip(s, x, y, lab, on, cnt) + 8
    y += 56
    cols = [(36, "Прогон"), (150, "Стратегия"), (290, "Режим"), (440, "Датасет"), (540, "Статус"), (740, "Результат"), (764, "Запущен"), (WIDE, "Автор")]
    checkbox(s, COL, y - 13, False)
    for dx, lab in cols:
        s.text(COL + dx, y, lab, size=13, fill=SEC, anchor="end" if dx in (740, WIDE) else "start")
    s.line(COL, y + 12, COL + WIDE, y + 12, stroke=INK)
    ry = y + 12
    for i, r in enumerate(runs):
        sel = r["id"] in ("run-0142", "run-0141")
        inv = r["status"] == "invalid"
        rh = 52 + (22 if inv else 0)
        if sel:
            s.rect(COL - 16, ry + 1, WIDE + 32, rh - 1, fill="#FFFBE6")
        b = ry + 32
        checkbox(s, COL, b - 14, sel)
        s.text(COL + 36, b, r["id"], size=14, fill=INK, mono=True, weight=700)
        s.text(COL + 150, b, r["strategy"], size=15, fill=INK)
        s.text(COL + 290, b, fit(r["mode"], 140, 15, tag="run"), size=15, fill=INK)
        s.text(COL + 440, b, r["dataset"], size=13, fill=SEC, mono=True)
        lvl = r["status"]
        level_icon(s, COL + 540, b - 13, lvl)
        s.text(COL + 564, b, D.STATUS_LABEL[lvl], size=14, fill={"valid": POS, "warning": AMBER, "invalid": NEG}[lvl], weight=700)
        res = r["result"]
        s.text(COL + 740, b, res, size=15, fill=NEG if res.startswith("−") else INK, weight=700, anchor="end")
        s.text(COL + 764, b, r["started"], size=14, fill=SEC)
        s.text(COL + WIDE, b, r["author"], size=14, fill=INK, anchor="end")
        if inv:
            s.text(COL + 564, b + 22, fit(D.INVALID_REASON.split(": ", 1)[1], 400, 13, tag="inv"), size=13, fill=NEG)
        ry += rh
        s.line(COL, ry, COL + WIDE, ry, stroke=LINE)
    # панель действий
    ay = ry + 20
    s.rect(COL - 16, ay, WIDE + 32, 64, fill=INK, rx=12)
    s.text(COL + 8, ay + 38, "Выбрано 2 прогона: run-0142 и run-0141", size=15, fill="#FFFFFF", weight=700)
    bx = COL + WIDE - 8
    w1 = measure("Сравнить выбранные", 14, 700) + 28 + 24
    button(s, bx - w1, ay + 16, "Сравнить выбранные", "primary", icon="compare")
    w2 = measure("Воспроизвести", 14, 700) + 28 + 24
    button(s, bx - w1 - 8 - w2, ay + 16, "Воспроизвести", "ghost", icon="repeat")
    P.y = ay + 64

    # 7.2 невалидный прогон
    P.h2("7.2", "run-0139 остановлен до расчёта: правило покупки читало завтрашнее закрытие")
    t = P.p("Проверка нашла ссылку на бар t+1 ещё до запуска, поэтому результата у прогона нет. "
            "После правки run-0140 получил пометку из-за adj_close, а ==run-0142 прошёл проверку чисто==.")
    P.note(t, "Причина", [(D.INVALID_REASON, False)])
    chk = D.LOOKAHEAD_CHECKS[2]
    ky = P.y + 28
    s.rect(COL, ky, COLW, 48, fill=SOFT, rx=10)
    s.text(COL + 20, ky + 30, str(chk["line"]), size=13, fill=TER, mono=True)
    code_line(s, COL + 52, ky + 30, chk["code"], size=14, hl=("close[+1]", NEG, NEG_BG))
    ny = s.para(COL, ky + 80, nb(chk["msg"]), COLW, size=15, lh=24, fill=INK)
    bx = COL
    bx += button(s, bx, ny, "Открыть главу 2", "ghost", icon="code", h=44) + 8
    button(s, bx, ny, "Открыть прогон", "flat", h=44)
    P.y = ny + 64

    # 7.3 статусы
    P.h2("7.3", "Статус показывает, можно ли опираться на результат")
    defs = [("valid", "Валиден", "Проверка не нашла чтения будущего, результат участвует в сравнении."),
            ("warning", "С пометкой", "Есть подозрительная ссылка на данные, например adj_close. Результат виден, но помечен."),
            ("invalid", "Невалиден", "Стратегия читает бар, который ещё не наступил. Результат не считается.")]
    y = P.y + 28
    for lvl, lab, txt in defs:
        level_icon(s, COL, y - 13, lvl)
        s.text(COL + 28, y, lab, size=15, fill=INK, weight=700)
        y = s.para(COL + 160, y, txt, COLW - 160, size=15, lh=22, fill=INK) + 22
    P.y = y - 30
    P.finish()
    return P.save()


BUILD = {1: chapter1, 2: chapter2, 3: chapter3, 4: chapter4, 5: chapter5, 6: chapter6, 7: chapter7}

if __name__ == "__main__":
    which = [int(a) for a in sys.argv[1:]] or sorted(BUILD)
    for n in which:
        print(BUILD[n]())
    if OVERFLOW:
        print("ПЕРЕПОЛНЕНИЕ:")
        for o in OVERFLOW:
            print("  ", o)
