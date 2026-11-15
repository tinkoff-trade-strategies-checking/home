"""Мини-библиотека для генерации SVG-экранов, которые импортируются в Figma через figwright.

Ограничения импорта в Figma (проверено):
  * шрифты: только Manrope и JetBrains Mono; serif-шрифты не отрисовываются;
  * начертания: weight 400 -> Regular, 700 -> Bold (500 падает в Regular, 600/800 в Bold);
  * letter-spacing теряется; opacity, fill-opacity, rx, stroke-dasharray, linearGradient,
    clip-path, transform=translate работают; text-anchor start/middle/end работает;
  * многострочный текст: <tspan x dy> -> отдельные текстовые слои.
Текст не переносится сам: ширину меряем через PIL по реальным файлам шрифтов.
"""
import os
from xml.sax.saxutils import escape

from PIL import ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_MANROPE = os.path.join(_HERE, "fonts", "Manrope.ttf")
_MONO = {400: os.path.join(_HERE, "fonts", "JetBrainsMono-Regular.ttf"), 700: os.path.join(_HERE, "fonts", "JetBrainsMono-Bold.ttf")}
_cache = {}

SANS = "Manrope"
MONO = "JetBrains Mono"


def _font(size, weight, mono):
    key = (size, weight, mono)
    if key not in _cache:
        if mono:
            f = ImageFont.truetype(_MONO[700 if weight >= 600 else 400], size=int(round(size * 4)))
        else:
            f = ImageFont.truetype(_MANROPE, size=int(round(size * 4)))
            f.set_variation_by_axes([700 if weight >= 600 else 400])
        _cache[key] = f
    return _cache[key]


def measure(s, size=14, weight=400, mono=False):
    """Ширина строки в px (как отрисует Figma)."""
    if not s:
        return 0.0
    return _font(size, weight, mono).getlength(s) / 4.0


def wrap(s, width, size=14, weight=400, mono=False):
    """Разбить текст на строки не шире width. Учитывает явные \\n."""
    lines = []
    for para in s.split("\n"):
        words, cur = para.split(" "), ""
        for w in words:
            cand = (cur + " " + w).strip()
            if measure(cand, size, weight, mono) <= width or not cur:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def truncate(s, width, size=14, weight=400, mono=False):
    if measure(s, size, weight, mono) <= width:
        return s
    while s and measure(s + "…", size, weight, mono) > width:
        s = s[:-1]
    return s.rstrip() + "…"


def _a(**kw):
    out = []
    for k, v in kw.items():
        if v is None:
            continue
        out.append(f'{k.replace("_", "-")}="{v}"')
    return " ".join(out)


class Svg:
    def __init__(self, w=1440, h=900, bg=None):
        self.w, self.h = w, h
        self.defs, self.body = [], []
        self._gid = 0
        if bg:
            self.rect(0, 0, w, h, bg)

    # --- примитивы ---------------------------------------------------------------
    def raw(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, fill="none", rx=0, stroke=None, sw=1, opacity=None, dash=None, fill_opacity=None):
        self.body.append(f'<rect {_a(x=round(x, 2), y=round(y, 2), width=round(w, 2), height=round(h, 2), rx=rx or None, fill=fill, stroke=stroke, stroke_width=sw if stroke else None, stroke_dasharray=dash, opacity=opacity, fill_opacity=fill_opacity)}/>')

    def line(self, x1, y1, x2, y2, stroke="#000", sw=1, dash=None, opacity=None, cap=None):
        self.body.append(f'<line {_a(x1=round(x1, 2), y1=round(y1, 2), x2=round(x2, 2), y2=round(y2, 2), stroke=stroke, stroke_width=sw, stroke_dasharray=dash, opacity=opacity, stroke_linecap=cap)}/>')

    def circle(self, cx, cy, r, fill="none", stroke=None, sw=1, opacity=None):
        self.body.append(f'<circle {_a(cx=round(cx, 2), cy=round(cy, 2), r=r, fill=fill, stroke=stroke, stroke_width=sw if stroke else None, opacity=opacity)}/>')

    def path(self, d, stroke=None, fill="none", sw=1, opacity=None, dash=None, join="round", cap="round", fill_opacity=None):
        self.body.append(f'<path {_a(d=d, fill=fill, stroke=stroke, stroke_width=sw if stroke else None, stroke_linejoin=join if stroke else None, stroke_linecap=cap if stroke else None, opacity=opacity, stroke_dasharray=dash, fill_opacity=fill_opacity)}/>')

    def text(self, x, y, s, size=14, fill="#000", weight=400, anchor="start", mono=False, opacity=None):
        """y — базовая линия."""
        fam = MONO if mono else SANS
        self.body.append(f'<text {_a(x=round(x, 2), y=round(y, 2), font_family=fam, font_size=size, font_weight=700 if weight >= 600 else 400, fill=fill, text_anchor=anchor if anchor != "start" else None, opacity=opacity)}>{escape(str(s))}</text>')

    def text_top(self, x, top, s, size=14, **kw):
        """То же, но y — верх строки (удобно для раскладки)."""
        self.text(x, top + size * 0.95, s, size=size, **kw)

    def para(self, x, y, s, width, size=14, lh=None, fill="#000", weight=400, mono=False, opacity=None, max_lines=None):
        """Абзац с переносом по ширине. y — базовая линия первой строки. Возвращает y после абзаца."""
        lh = lh or round(size * 1.5)
        lines = wrap(s, width, size, weight, mono)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = truncate(lines[-1] + " …", width, size, weight, mono)
        for i, ln in enumerate(lines):
            self.text(x, y + i * lh, ln, size=size, fill=fill, weight=weight, mono=mono, opacity=opacity)
        return y + len(lines) * lh

    def g(self, x=0, y=0):
        self.body.append(f'<g transform="translate({round(x, 2)},{round(y, 2)})">')

    def end(self):
        self.body.append("</g>")

    def gradient(self, color, top_opacity=0.35, bottom_opacity=0.0):
        self._gid += 1
        gid = f"g{self._gid}"
        self.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{color}" stop-opacity="{top_opacity}"/><stop offset="1" stop-color="{color}" stop-opacity="{bottom_opacity}"/></linearGradient>')
        return f"url(#{gid})"

    def clip(self, x, y, w, h):
        self._gid += 1
        cid = f"c{self._gid}"
        self.defs.append(f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>')
        self.body.append(f'<g clip-path="url(#{cid})">')

    # --- графики -----------------------------------------------------------------
    @staticmethod
    def _pts(values, x, y, w, h, vmin, vmax, step=1):
        n = len(values)
        idx = list(range(0, n, step))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        span = (vmax - vmin) or 1
        return [(x + w * i / (n - 1), y + h - h * (values[i] - vmin) / span) for i in idx]

    def series(self, values, x, y, w, h, vmin, vmax, stroke, sw=2, area=None, step=2, dash=None, opacity=None):
        """Линия ряда в прямоугольнике (x,y,w,h). area — цвет градиентной заливки под линией."""
        pts = self._pts(values, x, y, w, h, vmin, vmax, step)
        d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts)
        if area:
            fill = self.gradient(area)
            self.path(d + f" L{x + w:.1f} {y + h:.1f} L{x:.1f} {y + h:.1f} Z", fill=fill)
        self.path(d, stroke=stroke, sw=sw, dash=dash, opacity=opacity)
        return pts

    def area_down(self, values, x, y, w, h, vmin, color, step=2, opacity=0.35):
        """Просадка (underwater): заливка от нуля вниз. values ≤ 0, vmin < 0."""
        pts = self._pts(values, x, y, w, h, vmin, 0, step)
        d = f"M{x:.1f} {y:.1f} L" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + f" L{x + w:.1f} {y:.1f} Z"
        self.path(d, fill=color, fill_opacity=opacity)
        self.path("M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts), stroke=color, sw=1.2)

    def candles(self, data, x, y, w, h, up, down, wick=None, gap=0.3):
        lo = min(c["l"] for c in data)
        hi = max(c["h"] for c in data)
        span = hi - lo
        bw = w / len(data)
        Y = lambda v: y + h - h * (v - lo) / span
        for i, c in enumerate(data):
            col = up if c["c"] >= c["o"] else down
            cx = x + bw * i + bw / 2
            self.line(cx, Y(c["h"]), cx, Y(c["l"]), stroke=wick or col, sw=1)
            top, bot = Y(max(c["o"], c["c"])), Y(min(c["o"], c["c"]))
            self.rect(cx - bw * (1 - gap) / 2, top, bw * (1 - gap), max(1, bot - top), fill=col)
        return dict(lo=lo, hi=hi, bw=bw, Y=Y, X=lambda i: x + bw * i + bw / 2)

    def bars(self, values, x, y, w, h, vmin, vmax, pos, neg, gap=0.25, rx=2):
        """Столбики вокруг нуля (например, доходности окон walk-forward)."""
        n = len(values)
        bw = w / n
        span = vmax - vmin
        zero = y + h - h * (0 - vmin) / span
        for i, v in enumerate(values):
            top = y + h - h * (v - vmin) / span
            bx = x + bw * i + bw * gap / 2
            self.rect(bx, min(top, zero), bw * (1 - gap), abs(zero - top) or 1, fill=pos if v >= 0 else neg, rx=rx)
        return zero

    # --- иконки (простые пиктограммы 16×16 в точке x,y) --------------------------
    def icon(self, name, x, y, color, s=16, sw=1.6):
        k = s / 16
        P = lambda d: self.path(d, stroke=color, sw=sw)
        self.g(x, y)
        self.body.append(f'<g transform="scale({k})">' if k != 1 else "<g>")
        if name == "play":
            self.path("M4 2.5 L13 8 L4 13.5 Z", fill=color)
        elif name == "check":
            P("M3 8.5 L6.5 12 L13 4.5")
        elif name == "x":
            P("M4 4 L12 12 M12 4 L4 12")
        elif name == "warn":
            P("M8 2 L14.5 13.5 L1.5 13.5 Z")
            P("M8 6.5 L8 9.5")
            self.circle(8, 11.6, 0.9, fill=color)
        elif name == "info":
            self.circle(8, 8, 6.3, stroke=color, sw=sw)
            P("M8 7.5 L8 11.5")
            self.circle(8, 5, 0.9, fill=color)
        elif name == "chevron-right":
            P("M6 3.5 L10.5 8 L6 12.5")
        elif name == "chevron-down":
            P("M3.5 6 L8 10.5 L12.5 6")
        elif name == "search":
            self.circle(7, 7, 4.5, stroke=color, sw=sw)
            P("M10.5 10.5 L14 14")
        elif name == "plus":
            P("M8 3 L8 13 M3 8 L13 8")
        elif name == "download":
            P("M8 2.5 L8 10.5 M4.5 7 L8 10.5 L11.5 7 M3 13.5 L13 13.5")
        elif name == "db":
            self.path("M2.5 4 C2.5 1.8 13.5 1.8 13.5 4 L13.5 12 C13.5 14.2 2.5 14.2 2.5 12 Z", stroke=color, sw=sw)
            P("M2.5 4 C2.5 6.2 13.5 6.2 13.5 4 M2.5 8 C2.5 10.2 13.5 10.2 13.5 8")
        elif name == "code":
            P("M5.5 4 L1.5 8 L5.5 12 M10.5 4 L14.5 8 L10.5 12")
        elif name == "chart":
            P("M2 13.5 L14 13.5 M3 11 L6.5 6.5 L9.5 9 L14 3")
        elif name == "sliders":
            P("M2 4.5 L14 4.5 M2 11.5 L14 11.5")
            self.circle(5.5, 4.5, 1.8, fill=color)
            self.circle(10.5, 11.5, 1.8, fill=color)
        elif name == "compare":
            P("M2.5 13.5 L2.5 6 M6.5 13.5 L6.5 2.5 M10 13.5 L10 8 M13.5 13.5 L13.5 4.5")
        elif name == "steps":
            P("M2 13 L5.5 13 L5.5 9.5 L9 9.5 L9 6 L12.5 6 L12.5 2.5 L14.5 2.5")
        elif name == "history":
            self.circle(8, 8, 6, stroke=color, sw=sw)
            P("M8 4.5 L8 8 L10.5 9.5")
        elif name == "lock":
            self.rect(3, 7, 10, 7, stroke=color, sw=sw, rx=1.5)
            P("M5.5 7 L5.5 5 C5.5 2 10.5 2 10.5 5 L10.5 7")
        elif name == "repeat":
            P("M3 7 C3 4 5 3 8 3 L12.5 3 M10.5 1 L12.5 3 L10.5 5 M13 9 C13 12 11 13 8 13 L3.5 13 M5.5 11 L3.5 13 L5.5 15")
        elif name == "file":
            P("M4 1.5 L10 1.5 L13 4.5 L13 14.5 L4 14.5 Z M10 1.5 L10 4.5 L13 4.5")
        elif name == "folder":
            P("M1.5 4 L6 4 L7.5 5.5 L14.5 5.5 L14.5 13 L1.5 13 Z")
        elif name == "bolt":
            self.path("M9 1.5 L3.5 9 L7.5 9 L7 14.5 L12.5 7 L8.5 7 Z", fill=color)
        elif name == "user":
            self.circle(8, 5.5, 3, stroke=color, sw=sw)
            P("M2.5 14.5 C3 10.5 13 10.5 13.5 14.5")
        elif name == "dot":
            self.circle(8, 8, 4, fill=color)
        self.body.append("</g>")
        self.end()

    # --- вывод -------------------------------------------------------------------
    def tostring(self):
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                + defs + "".join(self.body) + "</svg>")

    def save(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.tostring())
        return path


def fmt_rub(v):
    """1316000 -> '1 316 000 ₽' (неразрывные пробелы не используем: Figma их показывает так же)."""
    return f"{v:,.0f}".replace(",", " ") + " ₽"


def fmt_pct(v, digits=1, sign=True):
    s = f"{abs(v):.{digits}f}".replace(".", ",")
    if not sign:
        return s + " %"
    return ("+" if v > 0 else "−" if v < 0 else "") + s + " %"
