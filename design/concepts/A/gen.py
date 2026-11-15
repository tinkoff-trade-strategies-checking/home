"""Концепция A «Лаборатория»: IDE, код в центре. Генерирует out/A1.svg … out/A7.svg."""
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "shared"))
from svg import *  # noqa: E402,F401
import data as D  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# --- палитра -------------------------------------------------------------------------------
BG, PN, SF, LN = "#0E1726", "#132036", "#1A2A44", "#24365A"
T1, T2, T3 = "#E6ECF5", "#8DA0BC", "#5D7091"
KW, FN, NUM, STR, CM = "#7FB4FF", "#E6C07B", "#F08D6E", "#9AD4A0", "#5D7091"
POS, NEG, WARN, Y, INK = "#44C596", "#FF4D4D", "#FFC700", "#FFDD2D", "#11141C"
ACC = KW
LEVEL_COL = {"ok": POS, "warning": WARN, "error": NEG, "info": KW, "valid": POS, "invalid": NEG}

# --- геометрия оболочки --------------------------------------------------------------------
W, TB, AB, EXW, INSW, PNH, SBH, TABH, CRH = 1440, 40, 48, 260, 320, 208, 24, 36, 28
XE, XC, XI = AB, AB + EXW, W - INSW
CW = XI - XC
MW = 7.25  # ширина символа JetBrains Mono 12


def cy(y, h, size):
    """Базовая линия текста, отцентрованного в полосе (y, h)."""
    return y + h / 2 + size * 0.36


# --- компоненты ----------------------------------------------------------------------------
def btn(s, x, y, label, kind="secondary", icon=None, h=32, size=13, w=None, anchor="start"):
    pad = 12 if h <= 32 else 20
    iw = 22 if icon else 0
    tw = measure(label, size, 700)
    bw = w or (pad * 2 + iw + tw)
    if anchor == "end":
        x -= bw
    fill, col, stroke = {
        "primary": (Y, INK, None),
        "secondary": (SF, T1, None),
        "outline": ("none", T1, LN),
        "ghost": ("none", ACC, None),
        "accent": (ACC, BG, None),
    }[kind]
    s.rect(x, y, bw, h, fill, rx=8, stroke=stroke)
    x0 = x + (bw - iw - tw) / 2
    if icon:
        s.icon(icon, x0, y + (h - 16) / 2, col)
        x0 += iw
    s.text(x0, cy(y, h, size), label, size, col, 700)
    return bw


def badge(s, x, y, label, color, h=20, size=12, mono=False, anchor="start", bold=True):
    tw = measure(label, size, 700 if bold else 400, mono)
    bw = tw + 12
    if anchor == "end":
        x -= bw
    s.rect(x, y, bw, h, color, rx=4, fill_opacity=0.16)
    s.text(x + 6, cy(y, h, size), label, size, color, 700 if bold else 400, mono=mono)
    return bw


def chip(s, x, y, label, color, anchor="middle", h=18):
    """Чип момента доступности данных (t, t+1 …)."""
    tw = measure(label, 11, 700, True)
    bw = max(24, tw + 10)
    x0 = x - bw / 2 if anchor == "middle" else x
    s.rect(x0, y, bw, h, color, rx=4, fill_opacity=0.18)
    s.rect(x0, y, bw, h, "none", rx=4, stroke=color, sw=1, opacity=0.45)
    s.text(x0 + bw / 2, cy(y, h, 11), label, 11, color, 700, anchor="middle", mono=True)
    return bw


def dot(s, x, y, color, r=4):
    s.circle(x, y, r, fill=color)


def kv(s, x, y, w, label, value, vcol=T1, lsize=13, vsize=12, lcol=T2):
    s.text(x, y, label, lsize, lcol)
    s.text(x + w, y, value, vsize, vcol, anchor="end", mono=True)


def hline(s, x, y, w, col=LN):
    s.line(x, y, x + w, y, col)


def wave(s, x1, x2, y, color, amp=2.0, step=3.0):
    d, x, up = f"M{x1:.1f} {y:.1f}", x1, True
    while x < x2 - 0.5:
        d += f" Q{x + step / 2:.1f} {y - amp if up else y + amp:.1f} {x + step:.1f} {y:.1f}"
        x += step
        up = not up
    s.path(d, stroke=color, sw=1.3)


def field(s, x, y, w, label, value, h=44, mono=True, icon=None, suffix=None, state=None):
    """Поле Taiga: подпись внутри сверху, значение снизу."""
    stroke = {"focus": ACC, "error": NEG}.get(state, LN)
    s.rect(x, y, w, h, SF, rx=8, stroke=stroke, sw=1.5 if state else 1)
    s.text(x + 12, y + 17, label, 11, T2)
    vw = w - 24 - (20 if icon else 0) - (measure(suffix, 12) + 8 if suffix else 0)
    s.text(x + 12, y + 35, truncate(value, vw, 13, 400, mono), 13, T1, mono=mono)
    if suffix:
        s.text(x + w - 12 - (20 if icon else 0), y + 35, suffix, 12, T2, anchor="end")
    if icon:
        s.icon(icon, x + w - 28, y + (h - 16) / 2, T2)


def toggle(s, x, y, on=True):
    s.rect(x, y, 32, 18, ACC if on else LN, rx=9)
    s.circle(x + (23 if on else 9), y + 9, 7, fill=T1 if on else T2)


def radio(s, x, y, on):
    s.circle(x + 8, y + 8, 7.5, stroke=ACC if on else T3, sw=1.5)
    if on:
        s.circle(x + 8, y + 8, 4, fill=ACC)


# --- оболочка IDE --------------------------------------------------------------------------
SECTIONS = [("db", "Датасеты"), ("code", "Стратегия"), ("sliders", "Настройка"), ("chart", "Отчёт"),
            ("compare", "Сравнение"), ("steps", "Walk-forward"), ("history", "История")]
DS_META = {"актуальный": "актуальный", "заменён ds-0007": "заменён", "устаревшая схема": "схема v1", "после MVP": "после MVP"}
STATUS_COL = {"valid": POS, "warning": WARN, "invalid": NEG}


def tree_row(s, y, label, meta=None, indent=0, icon=None, sel=False, dotc=None, mono=False, folder=False, meta_col=T3):
    x = XE + 12 + indent
    if sel:
        s.rect(XE, y, EXW - 1, 24, SF)
        s.rect(XE, y, 2, 24, ACC)
    if folder:
        s.icon("chevron-down", x, y + 6, T2, s=12, sw=2)
        s.text(x + 18, cy(y, 24, 12), label, 12, T1, 700)
        if meta:
            s.text(XE + EXW - 14, cy(y, 24, 11), meta, 11, T3, anchor="end")
        return
    tx = x
    if dotc:
        dot(s, x + 4, y + 12, dotc, 3.5)
        tx = x + 14
    elif icon:
        s.icon(icon, x, y + 5, T2 if not sel else T1, s=14, sw=1.8)
        tx = x + 22
    mw = measure(meta, 11, 400, mono) + 10 if meta else 0
    s.text(tx, cy(y, 24, 12 if mono else 13), truncate(label, XE + EXW - 14 - mw - tx, 12 if mono else 13, 400, mono),
           12 if mono else 13, T1 if sel else T2 if not mono else T1, mono=mono)
    if meta:
        s.text(XE + EXW - 14, cy(y, 24, 11), meta, 11, meta_col, anchor="end", mono=mono)


def shell(s, H, sec, tabs, crumbs, crumb_right, ins_title, panel_tab, panel_counts, tree_sel, check, status_right):
    s.rect(0, 0, W, H, BG)
    # заголовок окна
    s.rect(0, 0, W, TB, PN)
    hline(s, 0, TB - 0.5, W)
    s.rect(12, 8, 24, 24, SF, rx=6)
    s.icon("code", 16, 12, Y, s=16, sw=2)
    s.text(AB + 12, cy(0, TB, 14), D.PRODUCT, 14, T1, 700)
    mx = AB + 12 + measure(D.PRODUCT, 14, 700) + 28
    for m in ["Файл", "Правка", "Вид", "Прогон", "Справка"]:
        s.text(mx, cy(0, TB, 13), m, 13, T2)
        mx += measure(m, 13) + 20
    s.circle(W - 26, 20, 14, fill=SF)
    s.text(W - 26, cy(6, 28, 11), "ДМ", 11, T1, 700, anchor="middle")
    rx = W - 52
    bw = btn(s, rx, 4, "Запустить прогон", "primary", icon="play", anchor="end")
    rx -= bw + 8
    cfg = "SMA 20/50 на ds-0007"
    cw_ = measure(cfg, 13) + 32 + 36
    s.rect(rx - cw_, 4, cw_, 32, SF, rx=8)
    s.icon("code", rx - cw_ + 10, 12, T2, s=16)
    s.text(rx - cw_ + 32, cy(4, 32, 13), cfg, 13, T1)
    s.icon("chevron-down", rx - 22, 12, T2)
    # activity bar
    s.rect(0, TB, AB, H - TB - SBH, PN)
    s.line(AB - 0.5, TB, AB - 0.5, H - SBH, LN)
    for i, (ic, _name) in enumerate(SECTIONS):
        y = TB + 8 + i * 44
        if i == sec:
            s.rect(6, y, 36, 36, SF, rx=8)
            s.rect(0, y + 8, 2, 20, Y)
        s.icon(ic, 14, y + 10, T1 if i == sec else T2, s=20 if False else 16, sw=1.7)
    s.icon("user", 16, H - SBH - 40, T2)
    # explorer
    s.rect(XE, TB, EXW, H - TB - SBH, PN)
    s.line(XE + EXW - 0.5, TB, XE + EXW - 0.5, H - SBH, LN)
    s.text(XE + 16, cy(TB, 36, 12), "Исследование", 12, T2, 700)
    s.icon("plus", XE + EXW - 50, TB + 10, T2)
    s.icon("search", XE + EXW - 28, TB + 10, T2)
    y = TB + 36
    tree_row(s, y, "Датасеты", str(len(D.DATASETS)), folder=True)
    y += 24
    for ds in D.DATASETS:
        tree_row(s, y, ds["id"], DS_META.get(ds["status"], ds["source"]), indent=16, icon="db", sel=tree_sel == ds["id"],
                 mono=True, meta_col=T3)
        y += 24
    y += 4
    tree_row(s, y, "Стратегии", str(len(D.STRATEGIES)), folder=True)
    y += 24
    for st in D.STRATEGIES:
        tree_row(s, y, st["short"], f"{st['runs']} прогонов" if st["runs"] >= 5 else f"{st['runs']} прогона", indent=16,
                 icon="file", sel=tree_sel == st["short"])
        y += 24
    y += 4
    tree_row(s, y, "Прогоны", "последние 10", folder=True)
    y += 24
    for r in D.RUNS:
        tree_row(s, y, r["id"], r["result"], indent=16, dotc=STATUS_COL[r["status"]], sel=tree_sel == r["id"], mono=True,
                 meta_col=T2)
        y += 24
    # инспектор
    s.rect(XI, TB, INSW, H - TB - SBH, PN)
    s.line(XI + 0.5, TB, XI + 0.5, H - SBH, LN)
    s.text(XI + 16, cy(TB, 36, 12), ins_title, 12, T2, 700)
    hline(s, XI, TB + 36 - 0.5, INSW)
    # вкладки редактора
    s.rect(XC, TB, CW, TABH, PN)
    hline(s, XC, TB + TABH - 0.5, CW)
    tx = XC
    for ic, label, active, modified in tabs:
        tw = 12 + 16 + 8 + measure(label, 13) + 12 + 12 + 12
        if active:
            s.rect(tx, TB, tw, TABH, BG)
            s.rect(tx, TB, tw, 2, ACC)
        s.icon(ic, tx + 12, TB + 10, ACC if active else T3, s=16)
        s.text(tx + 36, cy(TB, TABH, 13), label, 13, T1 if active else T2)
        if modified:
            s.circle(tx + tw - 18, TB + 18, 4, fill=T2)
        else:
            s.icon("x", tx + tw - 24, TB + 12, T3 if not active else T2, s=12, sw=2)
        s.line(tx + tw - 0.5, TB, tx + tw - 0.5, TB + TABH, LN)
        tx += tw
    # хлебные крошки
    cy0 = TB + TABH
    bx = XC + 16
    for i, c in enumerate(crumbs):
        last = i == len(crumbs) - 1
        s.text(bx, cy(cy0, CRH, 12), c, 12, T1 if last else T2)
        bx += measure(c, 12)
        if not last:
            s.icon("chevron-right", bx + 4, cy0 + 8, T3, s=12, sw=2)
            bx += 20
    if crumb_right:
        s.text(XC + CW - 16, cy(cy0, CRH, 12), crumb_right, 12, T2, anchor="end")
    hline(s, XC, cy0 + CRH - 0.5, CW)
    # нижняя панель
    py = H - SBH - PNH
    s.rect(XC, py, CW, PNH, PN)
    hline(s, XC, py + 0.5, CW)
    px = XC + 16
    for name in ["Проблемы", "Консоль", "Сделки"]:
        active = name == panel_tab
        tw = measure(name, 13, 700 if active else 400)
        s.text(px, cy(py, 32, 13), name, 13, T1 if active else T2, 700 if active else 400)
        cnt = panel_counts.get(name)
        w2 = tw
        if cnt:
            col = cnt[1]
            w2 += 6 + badge(s, px + tw + 6, py + 7, cnt[0], col, h=18, size=11, mono=True)
        if active:
            s.rect(px, py + 30, w2, 2, ACC)
        px += w2 + 24
    s.icon("chevron-down", XC + CW - 30, py + 8, T3)
    hline(s, XC, py + 32 - 0.5, CW)
    # статус-бар
    sy = H - SBH
    s.rect(0, sy, W, SBH, PN)
    hline(s, 0, sy + 0.5, W)
    x = 12
    items = [("db", f"{D.DATASET_CURRENT['id']}  sha {D.DATASET_CURRENT['sha']}", T2),
             (None, f"seed {D.RUN_CONFIG['seed']}", T2),
             (None, D.REPRO["engine"], T2)]
    for ic, label, col in items:
        if ic:
            s.icon(ic, x, sy + 6, T2, s=12, sw=2)
            x += 18
        s.text(x, cy(sy, SBH, 11), label, 11, col, mono=True)
        x += measure(label, 11, mono=True) + 12
        s.line(x, sy + 6, x, sy + 18, LN)
        x += 12
    lvl, text = check
    s.icon({"ok": "check", "warning": "warn", "error": "x"}[lvl], x, sy + 6, LEVEL_COL[lvl], s=12, sw=2.2)
    s.text(x + 18, cy(sy, SBH, 12), text, 12, LEVEL_COL[lvl] if lvl != "ok" else T2)
    rx = W - 12
    for label in status_right:
        s.text(rx, cy(sy, SBH, 11), label, 11, T2, anchor="end", mono=True)
        rx -= measure(label, 11, mono=True) + 12
        s.line(rx, sy + 6, rx, sy + 18, LN)
        rx -= 12
    return dict(x=XC, y=cy0 + CRH, w=CW, h=py - cy0 - CRH, py=py + 32, ph=PNH - 32, ix=XI, iy=TB + 36, iw=INSW,
                ih=H - SBH - TB - 36, H=H)


# --- ряды по датам -------------------------------------------------------------------------
D0, D1 = D.DAYS[0], D.DAYS[-1]
GAP0, GAP1 = date(2022, 2, 28), date(2022, 3, 23)


def dx(d, x, w):
    return x + w * (d - D0).days / (D1 - D0).days


def date_paths(vals, x, y, w, h, vmin, vmax, step=3):
    segs, n = [[], []], len(vals)
    for i, (d, v) in enumerate(zip(D.DAYS, vals)):
        edge = (i + 1 < n and d < GAP0 <= D.DAYS[i + 1]) or (i > 0 and D.DAYS[i - 1] < GAP0 <= d)
        if i % step and i != n - 1 and not edge:
            continue
        segs[0 if d < GAP0 else 1].append((dx(d, x, w), y + h - h * (v - vmin) / (vmax - vmin)))
    return segs


def pts_d(seg):
    return "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in seg)


def hatch(s, x, y, w, h, color, gap=4, opacity=0.6):
    s.clip(x, y, w, h)
    k = -h
    while k < w:
        s.line(x + k, y + h, x + k + h, y, color, sw=1, opacity=opacity)
        k += gap
    s.end()


# --- DSL -----------------------------------------------------------------------------------
KEYWORDS = {"strategy", "universe", "capital", "let", "when", "crosses_above", "crosses_below", "buy", "sell", "all", "equity"}
TOK = re.compile(r'(//.*$)|("[^"]*")|(\d[\d_]*%?)|([A-Za-z_][A-Za-z_0-9]*)|(\s+)|(.)')


def code_tokens(line):
    out = []
    for m in TOK.finditer(line):
        cm, st, nm, idf, ws, _p = m.groups()
        if ws:
            continue
        if cm:
            col = CM
        elif st:
            col = STR
        elif nm:
            col = NUM
        elif idf:
            nxt = line[m.end():m.end() + 1]
            col = KW if idf in KEYWORDS else FN if nxt == "(" else T2 if idf == "RUB" else T1
        else:
            col = T2
        out.append((m.start(), m.group(), col))
    return out


def draw_code(s, x, base, line, size=14):
    for start, tok, col in code_tokens(line):
        s.text(x + measure(line[:start], size, mono=True), base, tok, size, col, mono=True)


def draft_code():
    lines = list(D.DSL_MAIN)
    for c in D.LOOKAHEAD_CHECKS:
        lines[c["line"] - 1] = c["code"]
    return lines


def disclaimer(s, x, y, w=None):
    s.icon("info", x, y - 12, T3, s=14, sw=1.6)
    s.text(x + 20, y, D.DISCLAIMER, 12, T2)


# ==========================================================================================
# A2 Стратегия
# ==========================================================================================
def screen_a2():
    H = 900
    s = Svg(W, H)
    R = shell(s, H, 1,
              tabs=[("code", "sma_20_50.strat", True, True), ("chart", "run-0142", False, False),
                    ("db", "ds-0007", False, False)],
              crumbs=["Стратегии", "SMA 20/50", "sma_20_50.strat"], crumb_right="Версия 4, есть несохранённые правки",
              ins_title="Стратегия", panel_tab="Проблемы", panel_counts={"Проблемы": ("2", NEG)},
              tree_sel="SMA 20/50", check=("error", "Чтение будущего: 1 ошибка, 1 подозрение"),
              status_right=["DSL", "Строка 8, столбец 15"])
    code = draft_code()
    ex, ey = R["x"], R["y"]
    x_num, lane_ok, x_hz, lane_fut, x_code = ex + 40, ex + 70, ex + 96, ex + 122, ex + 156
    LH = 24
    chk = D.LOOKAHEAD_CHECKS[2]
    diag_w = 256
    tw_ = R["w"] - 64 - 40 - diag_w - 32
    HINT = "Сравнивайте только известные бары: close и close[1]."
    n1 = len(wrap(chk["msg"], tw_, 13))
    n2 = len(wrap(HINT, tw_, 12))
    ph = max(168, 54 + n1 * 20 + n2 * 18 + 12 + 32 + 14)
    PEEK = ph + 24
    top = ey + 44
    bottom = R["py"] - 32

    def base_of(i):  # i — 1-based
        return top + (i - 1) * LH + (PEEK if i > 8 else 0)

    avail = {5: ("t", POS, "ok"), 6: ("t?", WARN, "hz"), 8: ("t+1", NEG, "fut"), 9: ("t", POS, "ok"), 10: ("t", POS, "ok")}
    # подсветка строк с проблемами
    for i, col, op in [(8, NEG, 0.10), (6, WARN, 0.07)]:
        b = base_of(i)
        s.rect(ex, b - 17, R["w"], LH, col, fill_opacity=op)
        s.rect(ex, b - 17, 2, LH, col)
    # горизонт знания: жёлтая линия через гаттер
    s.line(x_hz, ey + 30, x_hz, bottom, Y, sw=1.5, opacity=0.9)
    pw = measure("горизонт t", 11, 700) + 12
    s.rect(x_hz - pw / 2, ey + 10, pw, 18, Y, rx=4)
    s.text(x_hz, cy(ey + 10, 18, 11), "горизонт t", 11, INK, 700, anchor="middle")
    s.text(lane_ok, cy(ey + 10, 18, 11), "", 11, T3)
    for i, line in enumerate(code, start=1):
        b = base_of(i)
        s.text(x_num, b, str(i), 12, T1 if i == 8 else T3, anchor="end", mono=True)
        if i in avail:
            lab, col, lane = avail[i]
            xx = {"ok": lane_ok, "hz": x_hz, "fut": lane_fut}[lane]
            chip(s, xx, b - 13, lab, col)
        draw_code(s, x_code, b, line)
    cw14 = measure("a", 14, mono=True)
    # волны и inline-сообщения
    l8 = code[7]
    a = l8.index("close[+1]")
    wave(s, x_code + a * cw14, x_code + (a + 9) * cw14, base_of(8) + 5, NEG)
    s.rect(x_code + (a + 9) * cw14, base_of(8) - 15, 2, 20, T1)  # курсор
    l6 = code[5]
    a6 = l6.index("adj_close")
    wave(s, x_code + a6 * cw14, x_code + (a6 + 9) * cw14, base_of(6) + 5, WARN)
    for i, msg, col in [(8, "Бар t+1 ещё не наступил: прогон невалиден", NEG),
                        (6, "adj_close пересчитывается задним числом", WARN)]:
        mx = x_code + len(code[i - 1]) * cw14 + 32
        s.text(mx, base_of(i), truncate(msg, ex + R["w"] - 20 - mx, 12), 12, col)
    # peek-виджет ошибки под строкой 8
    px, py, pw_ = ex + 48, base_of(8) + 12, R["w"] - 64
    s.rect(px, py, pw_, ph, PN, rx=8, stroke=LN)
    s.rect(px, py, pw_, 3, NEG)
    s.icon("x", px + 16, py + 16, NEG, sw=2)
    s.text(px + 40, py + 29, "Чтение будущего", 13, T1, 700)
    s.text(px + 40 + measure("Чтение будущего", 13, 700) + 10, py + 29, "строка 8, столбец 6", 12, T2)
    s.icon("x", px + pw_ - 28, py + 16, T3, s=12, sw=2)
    yy = s.para(px + 40, py + 54, chk["msg"], tw_, 13, 20, T1)
    yy = s.para(px + 40, yy + 2, HINT, tw_, 12, 18, T2)
    bw1 = btn(s, px + 40, py + ph - 46, "Заменить на close[1]", "secondary", icon="code")
    btn(s, px + 40 + bw1 + 8, py + ph - 46, "Как устроен горизонт", "ghost")
    # мини-схема t-2 … t+1
    gx, gy = px + pw_ - diag_w - 20, py + 40
    s.rect(gx, gy, diag_w, ph - 56, BG, rx=8)
    cols = [("t−2", 0.55, 0.30, POS), ("t−1", 0.40, 0.62, NEG), ("t", 0.62, 0.30, POS), ("t+1", 0.28, 0.70, NEG)]
    slot = (diag_w - 32) / 4
    hzx = gx + 16 + slot * 3
    for k, (lab, o, c, col) in enumerate(cols):
        cx_ = gx + 16 + slot * k + slot / 2
        top_, bot_ = gy + 14, gy + 56
        yo, yc = bot_ - (bot_ - top_) * o, bot_ - (bot_ - top_) * c
        fut = k == 3
        s.line(cx_, top_ - 4, cx_, bot_ + 4, col if not fut else T3, sw=1.2, dash="2 2" if fut else None)
        s.rect(cx_ - 7, min(yo, yc), 14, abs(yo - yc), "none" if fut else col, stroke=T3 if fut else None, dash="2 2" if fut else None)
        s.text(cx_, gy + 78, lab, 11, NEG if fut else T2, 700 if fut else 400, anchor="middle", mono=True)
    s.line(hzx, gy + 6, hzx, gy + 84, Y, sw=1.5)
    s.text(hzx - 6, gy + 100, "решение", 11, T2, anchor="end")
    s.text(hzx + 6, gy + 100, "исполнение", 11, T2)
    # нижняя панель: проблемы
    rows = sorted(D.LOOKAHEAD_CHECKS, key=lambda c: {"error": 0, "warning": 1, "ok": 2}[c["level"]])
    names = {"error": "Ошибка", "warning": "Подозрительно", "ok": "OK"}
    icons = {"error": "x", "warning": "warn", "ok": "check"}
    ry = R["py"] + 4
    for k, c in enumerate(rows):
        col = LEVEL_COL[c["level"]]
        if k == 0:
            s.rect(ex, ry, R["w"], 44, SF)
        s.icon(icons[c["level"]], ex + 16, ry + 8, col, sw=2)
        s.text(ex + 40, ry + 20, names[c["level"]], 13, col, 700)
        for start, tok, _col in code_tokens(c["code"]):
            s.text(ex + 40 + 128 + measure(c["code"][:start], 12, mono=True), ry + 20, tok, 12, T2, mono=True)
        s.text(ex + R["w"] - 16, ry + 20, f"строка {c['line']}", 11, T2, anchor="end", mono=True)
        s.text(ex + 40, ry + 37, truncate(c["msg"], R["w"] - 72, 12), 12, T2 if k else T1)
        ry += 48
    # инспектор
    ix, iy, iw = R["ix"] + 16, R["iy"], R["iw"] - 32
    st = D.STRATEGIES[0]
    s.text(ix, iy + 32, st["name"], 16, T1, 700)
    y = s.para(ix, iy + 54, st["desc"], iw, 13, 20, T2)
    s.text(ix, y + 4, "версия 4, sha 8d10…4ab2", 12, T2, mono=True)
    s.text(ix, y + 24, f"{st['runs']} прогонов, изменена {st['updated']}", 12, T2)
    y += 44
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Проверка чтения будущего", 14, T1, 700)
    y += 16
    bh = 112
    s.rect(ix, y, iw, bh, NEG, rx=8, fill_opacity=0.10)
    s.rect(ix, y, iw, bh, "none", rx=8, stroke=NEG, opacity=0.4)
    s.icon("x", ix + 12, y + 14, NEG, sw=2)
    s.text(ix + 36, y + 27, "Прогон будет невалиден", 13, T1, 700)
    s.para(ix + 36, y + 48, "Его можно запустить, но результат не засчитается, пока в строке 8 есть close[+1].",
           iw - 48, 12, 18, T2)
    y += bh + 16
    expl = [("error", "Ошибка", "прогон невалиден", 8), ("warning", "Подозрительно", "прогон с пометкой", 6),
            ("ok", "OK", "данные известны к моменту решения", 5)]
    for lvl, nm, what, ln in expl:
        col = LEVEL_COL[lvl]
        s.icon(icons[lvl], ix, y - 2, col, s=14, sw=2)
        s.text(ix + 22, y + 10, nm, 13, T1, 700)
        s.text(ix + iw, y + 10, f"стр. {ln}", 11, T2, anchor="end", mono=True)
        s.text(ix + 22, y + 28, what, 12, T2)
        y += 44
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Параметры", 14, T1, 700)
    y += 26
    for lab, val in [("fast", "sma(close, 20)"), ("slow", "sma(adj_close, 50)"), ("Вселенная", "6 бумаг"),
                     ("Капитал", "1 000 000 RUB"), ("Исполнение", "open t+1"), ("Стоп", "−12 % по позиции")]:
        kv(s, ix, y, iw, lab, val, vcol=WARN if "adj" in val else T1)
        y += 24
    return s


# ==========================================================================================
# A4 Отчёт прогона
# ==========================================================================================
def screen_a4():
    H = 1232
    s = Svg(W, H)
    res, nv = D.RESULT_HONEST, D.RESULT_NAIVE
    R = shell(s, H, 3,
              tabs=[("chart", "run-0142 отчёт", True, False), ("code", "sma_20_50.strat", False, False),
                    ("compare", "Сравнение", False, False)],
              crumbs=["Прогоны", "run-0142", "Отчёт"], crumb_right=f"Запущен {D.REPRO['started']}, {D.REPRO['duration']}",
              ins_title="Метрики прогона", panel_tab="Проблемы", panel_counts={"Проблемы": ("4", WARN)},
              tree_sel="run-0142", check=("ok", "Чтение будущего не найдено"),
              status_right=["run-0142", "честный режим"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    # заголовок отчёта
    title = "SMA 20/50, честный прогон"
    s.text(x0, y + 20, title, 20, T1, 700)
    badge(s, x0 + measure(title, 20, 700) + 12, y + 4, "Валиден", POS)
    s.text(x0, y + 44, "ds-0007, 03.01.2020 — 30.12.2025, капитал 1 000 000 ₽, издержки и задержка учтены", 13, T2)
    btn(s, x0 + w, y, "Сравнить с наивным", "outline", icon="compare", anchor="end")
    y += 64
    # KPI-полоса
    kpis = [("Итог честного", res["total"], POS, res["final"]),
            ("Итог наивного", nv["total"], T1, "без издержек"),
            ("IMOEX", res["benchmark"], T1, "бенчмарк"),
            ("Макс. просадка", res["max_dd"], NEG, res["dd_days"]),
            ("Sharpe", res["sharpe"], T1, f"у наивного {nv['sharpe']}")]
    hline(s, x0, y, w)
    hline(s, x0, y + 76, w)
    cwk = w / len(kpis)
    for k, (lab, val, col, sub) in enumerate(kpis):
        kx = x0 + k * cwk + (16 if k else 0)
        if k:
            s.line(x0 + k * cwk, y + 12, x0 + k * cwk, y + 64, LN)
        s.text(kx, y + 22, lab, 12, T2)
        s.text(kx, y + 48, val, 22, col, 700, mono=True)
        s.text(kx, y + 66, truncate(sub, cwk - 24, 12), 12, T2)
    y += 76 + 28
    # капитал
    s.text(x0, y, "Капитал", 14, T1, 700)
    lx = x0 + w
    for lab, col, dash in [("IMOEX", T3, None), ("Наивный", T2, "5 4"), ("Честный", ACC, None)]:
        tw = measure(lab, 12)
        s.text(lx, y, lab, 12, T2, anchor="end")
        s.line(lx - tw - 28, y - 4, lx - tw - 8, y - 4, col, sw=2, dash=dash)
        lx -= tw + 28 + 20
    ax_w, lab_w = 52, 64
    gx, gw = x0 + ax_w, w - ax_w - lab_w
    ct, chh = y + 32, 196
    vmin, vmax = 0.5, 2.0
    # стресс-события (полосы + подписи над графиком)
    m0, m1 = dx(date(2020, 2, 24), gx, gw), dx(date(2020, 3, 23), gx, gw)
    g0, g1 = dx(GAP0, gx, gw), dx(GAP1, gx, gw)
    f24 = dx(date(2022, 2, 24), gx, gw)
    uw_t, uw_h = ct + chh + 24, 72
    s.rect(m0, ct, m1 - m0, uw_t + uw_h - ct, NEG, fill_opacity=0.10)
    hatch(s, g0, ct, g1 - g0, uw_t + uw_h - ct, T2, gap=3, opacity=0.5)
    s.line(f24, ct - 4, f24, uw_t + uw_h, NEG, sw=1, dash="3 3")
    s.text(m0, y + 22, "Март 2020", 11, T2)
    lab24 = "24.02.2022, затем торги закрыты до 23.03"
    s.text(f24 + 6, y + 22, lab24, 11, T2)
    for v in [0.5, 1.0, 1.5, 2.0]:
        yy = ct + chh - chh * (v - vmin) / (vmax - vmin)
        s.line(gx, yy, gx + gw, yy, LN if v != 1.0 else T3, sw=1, dash=None if v != 1.0 else "2 3")
        s.text(gx - 8, yy + 4, f"{v:.1f} млн".replace(".", ","), 11, T3, anchor="end", mono=True)
    for vals, col, sw, dash, lab in [(D.EQUITY_IMOEX, T3, 1.3, None, res["benchmark"]),
                                      (D.EQUITY_NAIVE, T2, 1.5, "5 4", nv["total"]),
                                      (D.EQUITY_HONEST, ACC, 2.2, None, res["total"])]:
        for seg in date_paths(vals, gx, ct, gw, chh, vmin, vmax):
            s.path(pts_d(seg), stroke=col, sw=sw, dash=dash)
        ey_ = ct + chh - chh * (vals[-1] - vmin) / (vmax - vmin)
        s.circle(gx + gw, ey_, 3, fill=col)
        s.text(gx + gw + 10, ey_ + 4, lab, 12, col if col != T3 else T2, 700, mono=True)
    # underwater
    dd = D.drawdown(D.EQUITY_HONEST)
    s.line(gx, uw_t, gx + gw, uw_t, LN)
    for seg in date_paths(dd, gx, uw_t, gw, uw_h, -0.30, 0.0):
        d_ = pts_d(seg) + f" L{seg[-1][0]:.1f} {uw_t:.1f} L{seg[0][0]:.1f} {uw_t:.1f} Z"
        s.path(d_, fill=NEG, fill_opacity=0.22)
        s.path(pts_d(seg), stroke=NEG, sw=1.2)
    s.text(gx - 8, uw_t + 4, "0 %", 11, T3, anchor="end", mono=True)
    s.text(gx - 8, uw_t + uw_h, "−30 %", 11, T3, anchor="end", mono=True)
    imin = min(range(len(dd)), key=lambda i: dd[i])
    mx_ = dx(D.DAYS[imin], gx, gw)
    my_ = uw_t + uw_h * dd[imin] / -0.30
    s.circle(mx_, my_, 3, fill=NEG)
    ddl = f"{res['max_dd']}, {res['dd_days']}"
    s.rect(mx_ + 8, my_ - 8, measure(ddl, 11, 700) + 8, 16, BG, rx=3, opacity=0.9)
    s.text(mx_ + 12, my_ + 4, ddl, 11, NEG, 700)
    s.text(gx + gw + 10, uw_t + 16, "Просадка", 11, T2)
    for yr in range(2020, 2026):
        xx = dx(date(yr, 1, 1), gx, gw) if yr > 2020 else gx
        if yr > 2020:
            s.line(xx, uw_t + uw_h, xx, uw_t + uw_h + 4, T3)
        s.text(xx + (0 if yr == 2020 else 0), uw_t + uw_h + 18, str(yr), 11, T3, anchor="start" if yr == 2020 else "middle", mono=True)
    y = uw_t + uw_h + 52
    # свечи SBER
    s.text(x0, y, "SBER, сделки стратегии", 14, T1, 700)
    s.text(x0 + measure("SBER, сделки стратегии", 14, 700) + 10, y, f"D1, {D.CANDLE_DATES[0]} — {D.CANDLE_DATES[1]}", 12, T2)
    legend = [("buy", "покупка"), ("partial", "частичное"), ("sell", "продажа"), ("rejected", "отказ")]
    lx = x0 + w
    for kind, lab in reversed(legend):
        tw = measure(lab, 12)
        s.text(lx, y, lab, 12, T2, anchor="end")
        marker(s, kind, lx - tw - 12, y - 4)
        lx -= tw + 36
    ct2, ch2 = y + 16, 200
    cgw = w - 52
    cd = D.candles()
    s.rect(x0, ct2, cgw, ch2, BG)
    info = s.candles(cd, x0, ct2 + 30, cgw, ch2 - 60, POS, NEG)
    lo, hi = info["lo"], info["hi"]
    for v in range(int(lo // 10 * 10) + 10, int(hi) + 1, 10):
        yy = info["Y"](v)
        s.line(x0, yy, x0 + cgw, yy, LN, opacity=0.6)
        s.text(x0 + cgw + 8, yy + 4, str(v), 11, T3, mono=True)
    # объём
    vt, vh = ct2 + ch2 + 6, 34
    vmax_ = max(c["v"] for c in cd)
    for i, c in enumerate(cd):
        bh_ = vh * c["v"] / vmax_
        s.rect(info["X"](i) - info["bw"] * 0.35, vt + vh - bh_, info["bw"] * 0.7, bh_, NEG if i == 72 else LN,
               fill_opacity=0.8 if i == 72 else None)
    s.text(x0 + cgw + 8, vt + vh, "объём", 11, T3)
    for i, mname in [(0, "сентябрь"), (22, "октябрь"), (44, "ноябрь"), (66, "декабрь")]:
        s.text(info["X"](i), vt + vh + 18, mname, 11, T3)
    place = {"buy": "below", "partial": "below", "sell": "above", "rejected": "above"}
    for i, kind, lab in D.TRADE_MARKERS:
        c = cd[i]
        mx_ = info["X"](i)
        tw = measure(lab, 11)
        tx = min(mx_ - 6, x0 + cgw - tw - 4)
        if kind == "sell":
            tx = mx_ + 6 - tw
        if place[kind] == "below":
            my_ = info["Y"](c["l"]) + 10
            ly = ct2 + ch2 - 8
            s.line(mx_, my_ + 7, mx_, ly - 12, T3, dash="2 2")
        else:
            my_ = info["Y"](c["h"]) - 10
            ly = ct2 + 16
            s.line(mx_, my_ - 7, mx_, ly + 4, T3, dash="2 2")
        marker(s, kind, mx_, my_)
        s.text(tx, ly, lab, 11, T1)
    disclaimer(s, x0, R["py"] - 32 - 18)
    # нижняя панель — флаги
    tags = ["издержки", "стр. 6", "календарь", "ликвидность"]
    ry = R["py"] + 4
    for k, f in enumerate(D.FLAGS):
        col = LEVEL_COL[f["level"]]
        s.icon("warn" if f["level"] == "warning" else "info", R["x"] + 16, ry + 8, col, sw=1.8)
        s.text(R["x"] + 40, ry + 20, truncate(f["text"], R["w"] - 160, 13), 13, T1)
        s.text(R["x"] + R["w"] - 16, ry + 20, tags[k], 11, T2, anchor="end")
        ry += 32
    # инспектор
    ix, iw = R["ix"] + 16, R["iw"] - 32
    y = R["iy"] + 30
    groups = [("Доходность", [("Итог, net", res["net"], POS), ("Gross, до издержек", res["gross"], T1), ("CAGR", res["cagr"], T1),
                              ("Капитал на конец", res["final"], T1), ("IMOEX за период", res["benchmark"], T1),
                              ("Относительно IMOEX", res["vs_benchmark"], POS)]),
              ("Риск", [("Макс. просадка", res["max_dd"], NEG), ("Длительность", res["dd_days"], T1),
                        ("Период", res["dd_period"], T1), ("Волатильность", res["vol"], T1), ("Sharpe", res["sharpe"], T1),
                        ("Sortino", res["sortino"], T1)]),
              ("Торговля", [("Оборот", res["turnover"], T1), ("Сделки", res["trades"], T1), ("Win rate", res["win_rate"], T1),
                            ("Частичные / отказы", f"{res['partial']} / {res['rejected']}", WARN)]),
              ("Концентрация", [("HHI", res["hhi"], T1), ("Крупнейшая позиция", res["top_position"], T1)])]
    for gname, rows in groups:
        s.text(ix, y, gname, 13, T1, 700)
        y += 22
        for lab, val, col in rows:
            kv(s, ix, y, iw, lab, val, vcol=col, lsize=12)
            y += 20
        y += 14
    hline(s, R["ix"], y - 4, R["iw"])
    y += 22
    s.text(ix, y, "Издержки и задержка", 13, T1, 700)
    s.text(ix + iw, y, "−52,6 п.п.", 12, NEG, 700, mono=True, anchor="end")
    y += 18
    s.text(ix, y, f"Разница наивного {nv['total']} и честного {res['total']}", 12, T2)
    y += 22
    mx = max(abs(v) for _, v, _ in D.DELTA_BREAKDOWN)
    for lab, v, rub in D.DELTA_BREAKDOWN:
        right = fmt_pct(v, 1).replace(" %", " п.п.")
        s.text(ix, y, truncate(lab, iw - 80, 12), 12, T1)
        s.text(ix + iw, y, right, 12, T1, mono=True, anchor="end")
        bw_ = (iw - 80) * abs(v) / mx
        s.rect(ix, y + 10, iw - 80, 4, SF, rx=2)
        s.rect(ix, y + 10, bw_, 4, NEG, rx=2, opacity=0.85)
        if rub:
            s.text(ix + iw, y + 17, rub, 11, T2, mono=True, anchor="end")
        y += 34
    kv(s, ix, y, iw, "Издержки всего", D.COSTS_TOTAL, lsize=12, vcol=T1)
    y += 22
    hline(s, R["ix"], y, R["iw"])
    y += 26
    s.text(ix, y, "Воспроизводимость", 13, T1, 700)
    y += 22
    rp = D.REPRO
    for lab, val in [("Прогон", rp["run"]), ("Датасет", rp["dataset"]), ("Стратегия", rp["strategy"]),
                     ("Движок", rp["engine"].replace("движок ", "")), ("Seed", rp["seed"]), ("Запущен", rp["started"])]:
        s.text(ix, y, lab, 12, T2)
        lines = wrap(val, iw - 84, 12, mono=True)
        for k, ln in enumerate(lines):
            s.text(ix + iw, y + k * 18, ln, 12, T1, mono=True, anchor="end")
        y += 18 * len(lines) + 2
    y += 8
    btn(s, ix, y, "Воспроизвести", "secondary", icon="repeat", w=iw)
    y += 32 + 18
    s.para(ix, y, "Создаст новый прогон с теми же данными, кодом и seed. Итог должен совпасть до рубля.", iw, 12, 18, T2)
    return s


def marker(s, kind, x, y):
    if kind == "buy":
        s.path(f"M{x - 5:.1f} {y + 4:.1f} L{x + 5:.1f} {y + 4:.1f} L{x:.1f} {y - 5:.1f} Z", fill=POS)
    elif kind == "partial":
        s.path(f"M{x - 5:.1f} {y + 4:.1f} L{x + 5:.1f} {y + 4:.1f} L{x:.1f} {y - 5:.1f} Z", fill=BG, stroke=POS, sw=1.5)
        s.path(f"M{x - 5:.1f} {y + 4:.1f} L{x:.1f} {y + 4:.1f} L{x:.1f} {y - 5:.1f} Z", fill=POS)
    elif kind == "sell":
        s.path(f"M{x - 5:.1f} {y - 4:.1f} L{x + 5:.1f} {y - 4:.1f} L{x:.1f} {y + 5:.1f} Z", fill=NEG)
    elif kind == "rejected":
        s.circle(x, y, 5.5, fill=BG, stroke=T2, sw=1.3)
        s.path(f"M{x - 2.5:.1f} {y - 2.5:.1f} L{x + 2.5:.1f} {y + 2.5:.1f} M{x + 2.5:.1f} {y - 2.5:.1f} L{x - 2.5:.1f} {y + 2.5:.1f}",
               stroke=T2, sw=1.3)


def checkbox(s, x, y, on):
    if on:
        s.rect(x, y, 16, 16, ACC, rx=4)
        s.icon("check", x + 2, y + 2, BG, s=12, sw=2.4)
    else:
        s.rect(x, y, 16, 16, "none", rx=4, stroke=T3, sw=1.5)


def th(s, x, y, label, anchor="start"):
    s.text(x, y, label, 12, T2, anchor=anchor)


def section_title(s, x, y, label, note=None):
    s.text(x, y, label, 14, T1, 700)
    if note:
        s.text(x + measure(label, 14, 700) + 10, y, note, 12, T2)


def header(s, x, y, w, title, sub, right_w=0):
    s.text(x, y + 20, title, 20, T1, 700)
    for k, ln in enumerate(wrap(sub, w - right_w - 24, 13)[:2]):
        s.text(x, y + 44 + k * 18, ln, 13, T2)


def console(s, R, lines):
    y = R["py"] + 22
    for t, msg, col in lines:
        s.text(R["x"] + 16, y, t, 12, T3, mono=True)
        s.text(R["x"] + 16 + measure(t, 12, mono=True) + 16, y,
               truncate(msg, R["w"] - 48 - measure(t, 12, mono=True), 12, mono=True), 12, col, mono=True)
        y += 22


def problems(s, R, rows):
    ry = R["py"] + 4
    for lvl, text, tag in rows:
        col = LEVEL_COL[lvl]
        s.icon({"error": "x", "warning": "warn", "info": "info", "ok": "check"}[lvl], R["x"] + 16, ry + 8, col, sw=1.9)
        s.text(R["x"] + 40, ry + 20, truncate(text, R["w"] - 170, 13), 13, T1)
        s.text(R["x"] + R["w"] - 16, ry + 20, tag, 11, T2, anchor="end", mono=True)
        ry += 32


# ==========================================================================================
# A1 Датасеты
# ==========================================================================================
def screen_a1():
    H = 960
    s = Svg(W, H)
    R = shell(s, H, 0,
              tabs=[("db", "Датасеты", True, False), ("code", "sma_20_50.strat", False, False)],
              crumbs=["Датасеты"], crumb_right="Снапшоты неизменяемы: правка создаёт новый",
              ins_title="Снапшот", panel_tab="Консоль", panel_counts={},
              tree_sel="ds-0007", check=("ok", "Чтение будущего не найдено"),
              status_right=["MOEX ISS", "5 снапшотов"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    bw = btn(s, x0 + w, y + 4, "Загрузить новый снапшот", "accent", icon="download", anchor="end")
    src = "Источник: MOEX ISS"
    sw_ = measure(src, 13) + 44
    s.rect(x0 + w - bw - 8 - sw_, y + 4, sw_, 32, "none", rx=8, stroke=LN)
    s.text(x0 + w - bw - 8 - sw_ + 12, cy(y + 4, 32, 13), src, 13, T1)
    s.icon("chevron-down", x0 + w - bw - 8 - 26, y + 12, T2)
    header(s, x0, y, w, "Снапшоты данных", "Прогон ссылается на хэш снапшота, поэтому его можно повторить и через год.",
           right_w=bw + sw_ + 8)
    y += 72
    cols = [0, 150, 372, 548, 700]
    hy = y + 18
    for cx_, lab in zip(cols, ["Снапшот", "Источник и тикеры", "Период и интервал", "Получен и хэш"]):
        th(s, x0 + cx_ + (12 if cx_ == 0 else 0), hy, lab)
    th(s, x0 + w - 12, hy, "Прогонов", "end")
    hline(s, x0, y + 28, w)
    y += 28
    st_col = {"актуальный": POS, "заменён ds-0007": T2, "устаревшая схема": WARN, "после MVP": T2}
    for ds in D.DATASETS:
        rh = 48
        sel = ds["id"] == "ds-0007"
        mvp = ds["status"] == "после MVP"
        if sel:
            s.rect(x0, y, w, rh, SF)
            s.rect(x0, y, 2, rh, ACC)
        op = 0.55 if mvp else None
        s.text(x0 + 12, y + 20, ds["id"], 13, T1, 700, mono=True, opacity=op)
        bx = x0 + 12
        if mvp:
            s.icon("lock", bx, y + 26, T2, s=14)
            bx += 18
        badge(s, bx, y + 25, ds["status"], st_col[ds["status"]], h=18, size=11)
        s.text(x0 + cols[1], y + 20, ds["source"], 13, T1, opacity=op)
        s.text(x0 + cols[1], y + 38, truncate(ds["tickers"], cols[2] - cols[1] - 16, 12), 12, T2, opacity=op)
        s.text(x0 + cols[2], y + 20, ds["period"], 12, T1, mono=True, opacity=op)
        rows = f"{ds['interval']}, строк: {ds['rows']}" if ds["rows"] != "—" else f"{ds['interval']}, по запросу"
        s.text(x0 + cols[2], y + 38, rows, 12, T2, opacity=op)
        s.text(x0 + cols[3], y + 20, ds["fetched"], 12, T1, mono=True, opacity=op)
        s.text(x0 + cols[3], y + 38, f"{ds['sha']}  схема {ds['schema']}", 12, T2, mono=True, opacity=op)
        s.text(x0 + w - 12, y + 20, str(ds["used_in"]) if ds["used_in"] else "—", 13, T1, mono=True, anchor="end", opacity=op)
        hline(s, x0, y + rh, w)
        y += rh
    # торговый календарь
    y += 32
    section_title(s, x0, y, "Торговый календарь", "ds-0007, февраль — апрель 2022")
    lx = x0 + w
    for lab, kind in [("торги не проводились", "gap"), ("выходной", "off"), ("торговый день", "on")]:
        tw = measure(lab, 12)
        s.text(lx, y, lab, 12, T2, anchor="end")
        bx_ = lx - tw - 20
        if kind == "on":
            s.rect(bx_, y - 11, 12, 12, SF, rx=3, stroke=LN)
        elif kind == "off":
            s.rect(bx_, y - 11, 12, 12, "none", rx=3, stroke=LN, dash="2 2")
        else:
            s.rect(bx_, y - 11, 12, 12, NEG, rx=3, fill_opacity=0.18, stroke=NEG)
        lx = bx_ - 20
    y += 16
    cell, gap = 22, 3
    gx = x0
    gap0, gap1 = date(2022, 2, 28), date(2022, 3, 23)
    for (yr, mo, name) in [(2022, 2, "Февраль"), (2022, 3, "Март"), (2022, 4, "Апрель")]:
        s.text(gx, y + 14, name, 12, T1, 700)
        for k, wd in enumerate(["пн", "вт", "ср", "чт", "пт", "сб", "вс"]):
            s.text(gx + k * (cell + gap) + cell / 2, y + 32, wd, 10, T3, anchor="middle")
        d = date(yr, mo, 1)
        row = 0
        while d.month == mo:
            c = d.weekday()
            cx_, cy_ = gx + c * (cell + gap), y + 40 + row * (cell + gap)
            in_gap = gap0 <= d <= gap1 and c < 5
            if c >= 5:
                s.rect(cx_, cy_, cell, cell, "none", rx=4, stroke=LN, dash="2 2")
                col = T3
            elif in_gap:
                s.rect(cx_, cy_, cell, cell, NEG, rx=4, fill_opacity=0.16, stroke=NEG, sw=1)
                col = NEG
            else:
                s.rect(cx_, cy_, cell, cell, SF, rx=4)
                col = T2
            if d == date(2022, 2, 24):
                s.rect(cx_, cy_, cell, cell, "none", rx=4, stroke=WARN, sw=1.5)
                col = WARN
            s.text(cx_ + cell / 2, cy_ + 15, str(d.day), 10, col, 700 if in_gap else 400, anchor="middle", mono=True)
            if c == 6:
                row += 1
            d += timedelta(days=1)
        gx += 7 * (cell + gap) + 20
    nx = gx + 4
    nw = x0 + w - nx
    yy = s.para(nx, y + 14, f"{D.CALENDAR_GAP[0]} — {D.CALENDAR_GAP[1]}", nw, 13, 20, T1, 700)
    yy = s.para(nx, yy, f"{D.CALENDAR_GAP[2][0].upper() + D.CALENDAR_GAP[2][1:]}. Движок пропускает эти 18 дней, а не заполняет их ценами: "
                "индикаторы считаются только по торговым дням.", nw, 12, 18, T2)
    s.rect(nx, yy + 4, 12, 12, "none", rx=3, stroke=WARN, sw=1.5)
    s.para(nx + 20, yy + 14, "24.02.2022 — гэп −33 % по индексу, стресс-событие", nw - 20, 12, 18, T2)
    # консоль
    console(s, R, [
        ("26.09.2026 18:40", "Загрузка MOEX ISS: SBER, GAZP, LKOH, GMKN, YDEX, MOEX + IMOEX, D1", T1),
        ("26.09.2026 18:40", "Получено 13 482 строки за 03.01.2019 — 25.09.2026", T1),
        ("26.09.2026 18:40", "Календарь: 28.02 — 23.03.2022 торги не проводились, пропуск ожидаемый", T2),
        ("26.09.2026 18:40", "adj_close не сохраняется: значение пересчитывается задним числом", WARN),
        ("26.09.2026 18:40", "Снапшот ds-0007 зафиксирован: sha 3f9a…c21e, схема v2", POS),
        ("26.09.2026 18:41", "ds-0006 помечен как заменённый, его прогоны остаются воспроизводимыми", T2),
    ])
    # инспектор
    ix, iw = R["ix"] + 16, R["iw"] - 32
    ds = D.DATASET_CURRENT
    y = R["iy"] + 32
    s.text(ix, y, ds["id"], 16, T1, 700, mono=True)
    badge(s, ix + measure(ds["id"], 16, 700, True) + 10, y - 15, ds["status"], POS, h=20, size=11)
    y += 22
    s.text(ix, y, f"{ds['source']}, интервал {ds['interval']}", 13, T2)
    y += 28
    for lab, val in [("Тикеры", ds["tickers"]), ("Период", ds["period"]), ("Получен", ds["fetched"]), ("Хэш", ds["sha"]),
                     ("Схема", ds["schema"]), ("Строк", ds["rows"]), ("Прогонов", f"{ds['used_in']}")]:
        s.text(ix, y, lab, 12, T2)
        lines = wrap(val, iw - 80, 12, mono=True)
        for k, ln in enumerate(lines):
            s.text(ix + iw, y + k * 18, ln, 12, T1, mono=True, anchor="end")
        y += 18 * len(lines) + 4
    y += 6
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Поля и момент доступности", 13, T1, 700)
    y += 24
    chips = {"open": ("t 10:00", POS), "adj_close": ("запрещено", NEG)}
    for fld, desc in D.DATASET_FIELDS:
        lab, col = chips.get(fld, ("t 18:50", POS))
        s.text(ix, y + 4, fld, 13, NEG if fld == "adj_close" else T1, mono=True)
        bw_ = measure(lab, 11, 700, True) + 10
        chip(s, ix + iw - bw_, y - 9, lab, col, anchor="start")
        s.text(ix, y + 22, truncate(desc, iw, 12), 12, T2)
        y += 42
    y += 2
    y = s.para(ix, y, "Стратегия получает значение только после этого момента. Решение по close дня t исполняется по open t+1.",
               iw, 12, 18, T2)
    y += 8
    hline(s, R["ix"], y, R["iw"])
    y += 28
    syn = D.DATASETS[4]
    s.text(ix, y, "Генератор синтетики", 13, T1, 700)
    badge(s, ix + iw, y - 14, "после MVP", T2, h=20, size=11, anchor="end")
    y += 20
    s.para(ix, y, f"{syn['source']}, {syn['period']}. Появится после MVP: сейчас доступны только снапшоты MOEX ISS и ЦБ РФ.",
           iw, 12, 18, T2)
    return s


def _valid(y, m, d):
    try:
        date(y, m, d)
        return True
    except ValueError:
        return False


# ==========================================================================================
# A3 Настройка прогона
# ==========================================================================================
def screen_a3():
    H = 952
    s = Svg(W, H)
    rc = D.RUN_CONFIG
    R = shell(s, H, 2,
              tabs=[("sliders", "Новый прогон", True, True), ("code", "sma_20_50.strat", False, False)],
              crumbs=["Прогоны", "Новый прогон"], crumb_right="SMA 20/50, версия 4",
              ins_title="Режим и запуск", panel_tab="Консоль", panel_counts={},
              tree_sel="SMA 20/50", check=("ok", "Чтение будущего не найдено"),
              status_right=["конфигурация не сохранена"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    header(s, x0, y, w, "Настройка прогона",
           "Во время прогона параметры зафиксированы. Чтобы что-то поменять, запустите новый прогон.")
    y += 84
    section_title(s, x0, y, "Данные")
    y += 14
    fw3 = (w - 24) / 3
    field(s, x0, y, fw3, "Датасет", f"{rc['dataset']}, sha 3f9a…c21e", icon="chevron-down")
    field(s, x0 + fw3 + 12, y, fw3, "Период", rc["period"], state="focus")
    field(s, x0 + 2 * (fw3 + 12), y, fw3, "Начальный капитал", rc["capital"])
    s.text(x0 + fw3 + 12, y + 62, rc["bars"], 12, T2)
    y += 64 + 36
    section_title(s, x0, y, "Издержки и исполнение", "применяются к честному прогону")
    y += 14
    fw2 = (w - 12) / 2
    rows = [
        [("Комиссия брокера", "0,05 %", "от оборота", None, None), ("Биржевой сбор", "0,01 %", "от оборота", None, None)],
        [("Спред", "0,08 %", "половина спреда", None, None), ("Проскальзывание", "0,10 % + 0,5 × доля в объёме бара", None, None, None)],
        [("Лимит ликвидности", "не больше 5 % объёма бара", None, None, "Остаток — частичное исполнение или отказ"),
         ("Задержка исполнения", "open следующего бара, t+1", None, "lock", "В честном режиме задержку отключить нельзя")],
    ]
    for row in rows:
        hint = False
        for k, (lab, val, suf, ic, h_) in enumerate(row):
            fx = x0 + k * (fw2 + 12)
            field(s, fx, y, fw2, lab, val, suffix=suf, icon=ic)
            if h_:
                s.text(fx, y + 62, h_, 12, T2)
                hint = True
        y += 44 + (30 if hint else 12)
    y += 24
    section_title(s, x0, y, "Стресс-сценарий", "накладывается на исторические данные")
    y += 14
    cw3 = (w - 24) / 3
    sel = 0
    for k, p in enumerate(D.STRESS_PRESETS):
        cx_ = x0 + k * (cw3 + 12)
        on = k == sel
        s.rect(cx_, y, cw3, 72, SF if on else "none", rx=10, stroke=ACC if on else LN, sw=1.5 if on else 1)
        radio(s, cx_ + 12, y + 12, on)
        s.text(cx_ + 36, y + 25, p["name"], 13, T1, 700)
        s.para(cx_ + 36, y + 44, p["desc"], cw3 - 48, 12, 16, T2, max_lines=2)
    y += 72 + 14
    fw4 = (w - 36) / 4
    p = D.STRESS_PRESETS[sel]
    for k, (lab, val) in enumerate([("Гэп по индексу", p["gap"]), ("Волатильность", p["vol"]), ("Объём торгов", p["volume"]),
                                    ("Проскальзывание", p["slip"])]):
        field(s, x0 + k * (fw4 + 12), y, fw4, lab, val)
    s.text(x0, y + 62, "Измените любое значение, и сценарий станет «Свой сценарий».", 12, T2)
    # консоль
    console(s, R, [
        ("14:21:40", f"Датасет {rc['dataset']}, sha 3f9a…c21e: снапшот найден, схема v2", T1),
        ("14:21:40", f"Период {rc['period']}: {rc['bars'].split(', ')[1]}", T1),
        ("14:21:40", "Пропуск 28.02 — 23.03.2022 учтён по торговому календарю", T2),
        ("14:21:41", "Сценарий 24.02.2022: гэп −33 %, волатильность × 3,0, объём × 0,4, проскальзывание × 4", T2),
        ("14:21:41", f"Готово к запуску: наивный и честный прогон, seed {rc['seed']}", POS),
    ])
    # инспектор
    ix, iw = R["ix"] + 16, R["iw"] - 32
    y = R["iy"] + 28
    s.text(ix, y, "Режим", 13, T1, 700)
    y += 20
    for title, sub, on in [("Наивный и честный вместе", "Покажет, сколько съели издержки и задержка", True),
                           ("Walk-forward", rc["walk_forward"], False)]:
        s.text(ix, y + 14, title, 13, T1)
        toggle(s, ix + iw - 32, y + 2, on)
        yy = s.para(ix, y + 34, sub, iw - 48, 12, 18, T2)
        y = yy + 12
    y += 4
    field(s, ix, y, iw, "Правило остановки", rc["stop_rule"], mono=False)
    y += 56
    field(s, ix, y, iw, "Seed", rc["seed"], icon="repeat")
    y += 52
    s.text(ix, y + 10, "Одинаковый seed даёт одинаковый результат", 12, T2)
    y += 32
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Будет запущено", 13, T1, 700)
    y += 24
    for lab, val, col in [("Прогонов", "2", T1), ("Стратегия", "SMA 20/50, v4", T1), ("Торговых дней", "1 545", T1),
                          ("Стресс", "24.02.2022", WARN), ("Чтение будущего", "не найдено", POS)]:
        kv(s, ix, y, iw, lab, val, vcol=col, lsize=12)
        y += 22
    y += 14
    s.rect(ix, y, iw, 56, BG, rx=8, stroke=LN)
    s.icon("play", ix + 12, y + 20, Y)
    s.para(ix + 36, y + 23, "Запустите прогон кнопкой в шапке или сочетанием Ctrl + Enter", iw - 48, 12, 18, T2)
    return s


# ==========================================================================================
# A5 Сравнение
# ==========================================================================================
def screen_a5():
    H = 1000
    s = Svg(W, H)
    res, nv = D.RESULT_HONEST, D.RESULT_NAIVE
    R = shell(s, H, 4,
              tabs=[("compare", "Сравнение", True, False), ("chart", "run-0142 отчёт", False, False)],
              crumbs=["Прогоны", "Сравнение"], crumb_right="run-0141 и run-0142, seed 20261005",
              ins_title="Кривые капитала", panel_tab="Проблемы", panel_counts={"Проблемы": ("3", WARN)},
              tree_sel="run-0142", check=("ok", "Чтение будущего не найдено"),
              status_right=["4 стратегии", "честный режим"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    btn(s, x0 + w, y + 4, "Открыть отчёт run-0142", "outline", icon="chart", anchor="end")
    header(s, x0, y, w, "SMA 20/50: наивный и честный прогон",
           "Те же данные, код и seed. Разница — только издержки, задержка исполнения и лимит ликвидности.", right_w=220)
    y += 92
    section_title(s, x0, y, "Куда ушли 52,6 п.п.", f"от {nv['total']} к {res['total']}")
    y += 20
    ax = 44
    gx, gw, gh = x0 + ax, w - ax, 180
    top = y + 16
    vmax = 90.0
    Yv = lambda v: top + gh - gh * v / vmax
    for v in [0, 20, 40, 60, 80]:
        s.line(gx, Yv(v), gx + gw, Yv(v), LN if v else T3, sw=1)
        s.text(gx - 8, Yv(v) + 4, f"{v} %", 11, T3, anchor="end", mono=True)
    steps = [("Наивный", 84.2, None, "naive")] + [(l, v, r, "d") for l, v, r in D.DELTA_BREAKDOWN] + [("Честный", 31.6, None, "honest")]
    slot = gw / len(steps)
    bw = slot - 28
    level = 84.2
    prev_top = None
    for k, (lab, v, rub, kind) in enumerate(steps):
        bx = gx + k * slot + 14
        if kind == "naive":
            a, b, col = 0, 84.2, T2
            val = nv["total"]
        elif kind == "honest":
            a, b, col = 0, 31.6, ACC
            val = res["total"]
        else:
            a, b, col = level + v, level, NEG
            level += v
            val = fmt_pct(v, 1).replace(" %", "")
        s.rect(bx, Yv(b), bw, Yv(a) - Yv(b), col, rx=3, opacity=0.9 if kind != "d" else 0.75)
        if prev_top is not None:
            s.line(bx - 28, Yv(prev_top), bx, Yv(prev_top), T3, dash="2 2")
        prev_top = a if kind == "d" else b
        s.text(bx + bw / 2, Yv(b) - 8, val, 12, col if kind != "naive" else T1, 700, anchor="middle", mono=True)
        # подписи
        name, _, rest = lab.partition(": ")
        ly = top + gh + 18
        for ln in wrap(name, slot - 6, 11, 700)[:2]:
            s.text(bx + bw / 2, ly, ln, 11, T1, 700, anchor="middle")
            ly += 14
        for ln in wrap(rest, slot - 6, 11)[:2] if rest else []:
            s.text(bx + bw / 2, ly, ln, 11, T2, anchor="middle")
            ly += 14
        if rub:
            s.text(bx + bw / 2, ly, rub, 11, T2, anchor="middle", mono=True)
    y = top + gh + 92
    # таблица стратегий
    section_title(s, x0, y, "Стратегии на ds-0007", "честный режим, флаги считаются автоматически")
    y += 14
    cols = [12, 214, 292, 392, 466, 526]  # правые края числовых колонок
    heads = ["Стратегия", "Честный", "Наивный", "Sharpe ч / н", "Просадка", "Оборот"]
    for k, (cx_, lab) in enumerate(zip(cols, heads)):
        th(s, x0 + cx_, y + 18, lab, "end" if k else "start")
    FX = 550
    th(s, x0 + FX, y + 18, "Флаг")
    hline(s, x0, y + 28, w)
    y += 28
    colors = {"SMA 20/50": ACC, "Моментум 3М": FN, "RSI-откат": NUM, "IMOEX": T2}
    for r in D.COMPARISON:
        rh = 40
        if r["name"] == "SMA 20/50":
            s.rect(x0, y, w, rh, SF)
        s.rect(x0 + 12, y + 17, 10, 3, colors[r["name"]], rx=1)
        s.text(x0 + 30, y + 25, r["name"], 13, T1, 700)
        vals = [(r["honest"], NEG if r["h"] < 0 else T1), (r["naive"], T2),
                (f"{r['sharpe']} / {r['sharpe_naive']}", WARN if r["flag"] and "Sharpe" in r["flag"] else T1),
                (r["dd"], T1), (r["turnover"], T1)]
        for k, (v, col) in enumerate(vals):
            s.text(x0 + cols[k + 1], y + 25, v, 12, col, mono=True, anchor="end")
        if r["flag"]:
            col = NEG if "знак" in r["flag"] else WARN
            badge(s, x0 + FX, y + 10, r["flag"], col, h=20, size=11)
        else:
            s.text(x0 + FX, y + 25, "нет", 12, T2)
        hline(s, x0, y + rh, w)
        y += rh
    disclaimer(s, x0, R["py"] - 32 - 18)
    problems(s, R, [
        ("warning", "SMA 20/50: издержки и задержка съели 62 % наивной прибыли, порог 50 %", "издержки"),
        ("warning", "Моментум 3М: наивный Sharpe 3,40 больше 3. Проверьте стратегию на чтение будущего", "Sharpe"),
        ("error", "RSI-откат: издержки меняют знак результата, с +38,5 % до −6,8 %", "знак"),
    ])
    # инспектор: наложение кривых
    ix, iw = R["ix"] + 16, R["iw"] - 32
    y = R["iy"] + 28
    s.text(ix, y, "Честный режим, 2020 — 2025", 13, T1, 700)
    y += 16
    ct, chh = y + 8, 180
    vmin, vmax = 0.5, 1.6
    cx0, cw0 = ix + 36, iw - 36
    for v in [0.5, 1.0, 1.5]:
        yy = ct + chh - chh * (v - vmin) / (vmax - vmin)
        s.line(cx0, yy, cx0 + cw0, yy, LN if v != 1.0 else T3, dash=None if v != 1.0 else "2 3")
        s.text(cx0 - 6, yy + 4, f"{v:.1f}".replace(".", ","), 10, T3, mono=True, anchor="end")
    s.text(cx0 - 6, ct - 6, "млн ₽", 10, T3, anchor="end")
    series = [(D.EQUITY_IMOEX, T2, "IMOEX", 1.2, "4 3"), (D.EQUITY_RSI, NUM, "RSI-откат", 1.4, None),
              (D.EQUITY_MOMENTUM, FN, "Моментум 3М", 1.4, None), (D.EQUITY_HONEST, ACC, "SMA 20/50", 2.0, None)]
    g0 = dx(GAP0, cx0, cw0)
    hatch(s, g0, ct, max(3, dx(GAP1, cx0, cw0) - g0), chh, T2, gap=3, opacity=0.5)
    for vals, col, _n, sw, dash in series:
        for seg in date_paths(vals, cx0, ct, cw0, chh, vmin, vmax, step=6):
            s.path(pts_d(seg), stroke=col, sw=sw, dash=dash)
    for yr, anc in [(2020, "start"), (2023, "middle"), (2025, "end")]:
        xx = dx(date(yr, 1, 1), cx0, cw0) if yr != 2020 else cx0
        if yr == 2025:
            xx = cx0 + cw0
        s.text(xx, ct + chh + 16, str(yr) if yr != 2025 else "2025", 10, T3, anchor=anc, mono=True)
    y = ct + chh + 40
    for r in D.COMPARISON:
        on = True
        checkbox(s, ix, y - 12, on)
        s.rect(ix + 26, y - 6, 14, 3, colors[r["name"]], rx=1)
        s.text(ix + 48, y, r["name"], 13, T1)
        s.text(ix + iw, y, r["honest"], 12, NEG if r["h"] < 0 else T1, mono=True, anchor="end")
        y += 28
    y += 4
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Когда ставится флаг", 13, T1, 700)
    y += 22
    for lab, desc, col in [("Издержки > 50 % прибыли", "Стратегия зарабатывает в основном для брокера", WARN),
                           ("Издержки меняют знак", "Без издержек плюс, с издержками минус", NEG),
                           ("Наивный Sharpe > 3", "Слишком хорошо для дневных данных: ищите утечку будущего", WARN)]:
        s.circle(ix + 4, y - 4, 3.5, fill=col)
        s.text(ix + 16, y, lab, 12, T1, 700)
        y = s.para(ix + 16, y + 18, desc, iw - 16, 12, 18, T2) + 10
    return s


# ==========================================================================================
# A6 Walk-forward
# ==========================================================================================
def screen_a6():
    H = 1168
    s = Svg(W, H)
    wf, sm = D.WALK_FORWARD, D.WF_SUMMARY
    R = shell(s, H, 5,
              tabs=[("steps", "Walk-forward", True, False), ("chart", "run-0142 отчёт", False, False)],
              crumbs=["Прогоны", "Walk-forward"], crumb_right="20 окон, параметры подбираются заново в каждом",
              ins_title="Сводка walk-forward", panel_tab="Консоль", panel_counts={},
              tree_sel="SMA 20/50", check=("ok", "Чтение будущего не найдено"),
              status_right=["20 окон", "SMA 20/50"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    header(s, x0, y, w, "Walk-forward: SMA 20/50",
           "Год подбора параметров, затем квартал проверки на данных, которых подбор не видел. Окно сдвигается на 3 месяца.")
    y += 92
    # IS vs OOS
    section_title(s, x0, y, "Доходность по окнам", "за квартал, %")
    lx = x0 + w
    for lab, col in [("проверка (out-of-sample)", POS), ("подбор (in-sample)", T3)]:
        tw = measure(lab, 12)
        s.text(lx, y, lab, 12, T2, anchor="end")
        s.rect(lx - tw - 18, y - 10, 10, 10, col, rx=2)
        lx -= tw + 36
    ax = 40
    gx, gw, gh = x0 + ax, w - ax, 150
    top = y + 20
    vmin, vmax = -8.0, 14.0
    Yv = lambda v: top + gh - gh * (v - vmin) / (vmax - vmin)
    for v in [-5, 0, 5, 10]:
        s.line(gx, Yv(v), gx + gw, Yv(v), T3 if v == 0 else LN)
        s.text(gx - 8, Yv(v) + 4, f"{v:+d}".replace("-", "−") if v else "0", 11, T3, anchor="end", mono=True)
    slot = gw / 20
    for k, r in enumerate(wf):
        bx = gx + k * slot
        bw = (slot - 10) / 2
        for j, (v, col) in enumerate([(r["train_ret"], T3), (r["test_ret"], POS if r["test_ret"] >= 0 else NEG)]):
            x_ = bx + 5 + j * bw
            s.rect(x_, min(Yv(v), Yv(0)), bw - 1, abs(Yv(v) - Yv(0)) or 1, col, rx=1.5,
                   opacity=0.55 if j == 0 else 0.95)
        s.text(bx + slot / 2, top + gh + 16, f"{r['n']:02d}", 10, T1 if r["n"] == 9 else T3, anchor="middle", mono=True)
    y = top + gh + 48
    # схема окон
    section_title(s, x0, y, "Схема окон", "подбор 1 год, проверка 3 месяца, сдвиг 3 месяца")
    y += 14
    c_n, c_tl, c_is, c_oos, c_par = 0, 40, 492, 572, 652
    tl_w = c_is - c_tl - 28
    th(s, x0 + c_n, y + 18, "Окно")
    th(s, x0 + c_is + 52, y + 18, "Подбор", "end")
    th(s, x0 + c_oos + 52, y + 18, "Проверка", "end")
    th(s, x0 + c_par, y + 18, "Параметры")
    T0, T1d = date(2020, 1, 1), date(2026, 1, 1)
    TX = lambda d: x0 + c_tl + tl_w * (d - T0).days / (T1d - T0).days
    for yr in range(2020, 2027):
        xx = TX(date(yr, 1, 1))
        s.text(xx, y + 18, str(yr), 11, T3, anchor="middle" if 2020 < yr < 2026 else ("start" if yr == 2020 else "end"), mono=True)
    hline(s, x0, y + 28, w)
    y += 28
    rh = 20
    tl_top = y
    for yr in range(2021, 2026):
        xx = TX(date(yr, 1, 1))
        s.line(xx, y, xx, y + rh * 20, LN, dash="2 3")

    def mdate(sv):
        mm, yy = sv.split(".")
        return date(int(yy), int(mm), 1)
    for r in wf:
        tr0, tr1 = [mdate(p.strip()) for p in r["train"].split("—")]
        te1 = date(tr1.year + (tr1.month + 2) // 12, (tr1.month + 2) % 12 + 1, 1)
        if r["n"] == 9:
            s.rect(x0, y, w, rh, NEG, fill_opacity=0.08)
        s.text(x0 + 4, y + 14, f"{r['n']:02d}", 11, T2, mono=True)
        s.rect(TX(tr0), y + 5, TX(tr1) - TX(tr0) - 1, 10, LN, rx=2)
        col = POS if r["test_ret"] >= 0 else NEG
        s.rect(TX(tr1), y + 5, TX(te1) - TX(tr1), 10, col, rx=2, opacity=0.9)
        s.text(x0 + c_is + 52, y + 14, fmt_pct(r["train_ret"], 1), 11, T2, mono=True, anchor="end")
        s.text(x0 + c_oos + 52, y + 14, fmt_pct(r["test_ret"], 1), 11, col, 700, mono=True, anchor="end")
        s.text(x0 + c_par, y + 14, r["params"], 11, T1, mono=True)
        y += rh
    s.text(x0 + c_par + 58, tl_top - 10 - 0, "", 11, T2)
    y += 16
    s.rect(x0 + c_tl, y - 9, 18, 8, LN, rx=2)
    s.text(x0 + c_tl + 24, y, "подбор", 11, T2)
    s.rect(x0 + c_tl + 84, y - 9, 18, 8, POS, rx=2)
    s.text(x0 + c_tl + 108, y, "проверка", 11, T2)
    disclaimer(s, x0, R["py"] - 32 - 18)
    console(s, R, [(f"окно {r['n']:02d}", f"подбор {r['train']}: выбрано {r['params']}, проверка {r['test']}: {fmt_pct(r['test_ret'], 1)}",
                    NEG if r["test_ret"] < -5 else T1) for r in wf[5:10]] +
            [("готово", "20 окон: прибыльных 12, итог проверки +9,3 %", POS)])
    # инспектор
    ix, iw = R["ix"] + 16, R["iw"] - 32
    y = R["iy"] + 32
    s.text(ix, y, "Деградация", 12, T2)
    s.text(ix, y + 32, sm["degradation"], 28, NEG, 700, mono=True)
    s.para(ix + 120, y + 18, "out-of-sample относительно in-sample", iw - 120, 12, 18, T2)
    y += 56
    hline(s, R["ix"], y, R["iw"])
    y += 26
    for lab, val, col in [("Окон", sm["windows"], T1), ("Прибыльных окон", sm["positive"], T1),
                          ("Проверка в среднем", sm["oos_avg"], T1), ("Подбор в среднем", sm["is_avg"], T2),
                          ("Итог проверки", sm["oos_total"], POS)]:
        kv(s, ix, y, iw, lab, val, vcol=col, lsize=12)
        y += 22
    y += 10
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Стабильность параметров", 13, T1, 700)
    y += 18
    s.text(ix, y, sm["stable_param"], 12, T2)
    y += 22
    sets = []
    for r in wf:
        if r["params"] not in sets:
            sets.append(r["params"])
    s.text(ix, y + 4, f"За 20 окон подбор выбрал {len(sets)} разных наборов SMA:", 12, T2)
    y += 18
    px_ = ix
    for p_ in sorted(sets):
        cw_ = measure(p_, 12, 700, True) + 14
        if px_ + cw_ > ix + iw:
            px_ = ix
            y += 28
        s.rect(px_, y, cw_, 22, ACC if p_ == "20/50" else SF, rx=4, fill_opacity=0.18 if p_ == "20/50" else None)
        s.text(px_ + 7, y + 15, p_, 12, ACC if p_ == "20/50" else T1, 700, mono=True)
        px_ += cw_ + 6
    y += 34
    y += 12
    hline(s, R["ix"], y, R["iw"])
    y += 20
    s.rect(ix, y, iw, 96, WARN, rx=8, fill_opacity=0.08)
    s.rect(ix, y, iw, 96, "none", rx=8, stroke=WARN, opacity=0.35)
    s.icon("warn", ix + 12, y + 14, WARN)
    s.text(ix + 36, y + 27, "Подбор переоценивает стратегию", 13, T1, 700)
    s.para(ix + 36, y + 48, "Оценивайте её по окнам проверки: +0,5 % за квартал вместо +9,0 % на подборе.", iw - 48, 12, 18, T2)
    return s


# ==========================================================================================
# A7 История прогонов
# ==========================================================================================
def screen_a7():
    H = 900
    s = Svg(W, H)
    R = shell(s, H, 6,
              tabs=[("history", "История прогонов", True, False), ("compare", "Сравнение", False, False)],
              crumbs=["Прогоны", "История"], crumb_right="Прогоны неизменяемы и хранятся с хэшами",
              ins_title="Прогон", panel_tab="Проблемы", panel_counts={"Проблемы": ("3", NEG)},
              tree_sel="run-0139", check=("error", "run-0139 невалиден"),
              status_right=["выбрано 2", "10 прогонов"])
    x0, w = R["x"] + 24, R["w"] - 48
    y = R["y"] + 20
    bw = btn(s, x0 + w, y + 4, "Сравнить выбранные", "accent", icon="compare", anchor="end")
    btn(s, x0 + w - bw - 8, y + 4, "Воспроизвести", "outline", icon="repeat", anchor="end")
    header(s, x0, y, w, "История прогонов", "Чтобы поменять параметры, запустите новый прогон. Старые остаются здесь.",
           right_w=bw + 150)
    y += 72
    # фильтры
    cnt = {k: sum(1 for r in D.RUNS if r["status"] == k) for k in D.STATUS_LABEL}
    seg = [("Все", len(D.RUNS))] + [(D.STATUS_LABEL[k], cnt[k]) for k in ["valid", "warning", "invalid"]]
    sx = x0
    segw = [measure(a, 13, 700 if k == 0 else 400) + measure(str(b), 12, mono=True) + 28 for k, (a, b) in enumerate(seg)]
    s.rect(sx, y, sum(segw) + 4, 32, SF, rx=8)
    xx = sx + 2
    for k, ((a, b), ww) in enumerate(zip(seg, segw)):
        if k == 0:
            s.rect(xx, y + 2, ww, 28, BG, rx=6)
        s.text(xx + 10, cy(y, 32, 13), a, 13, T1 if k == 0 else T2, 700 if k == 0 else 400)
        s.text(xx + ww - 10, cy(y, 32, 12), str(b), 12, LEVEL_COL.get(["", "valid", "warning", "invalid"][k], T2) if k else T2,
               mono=True, anchor="end")
        xx += ww
    fx = sx + sum(segw) + 12
    for lab in ["Стратегия: все", "Автор: все"]:
        fw_ = measure(lab, 13) + 36
        s.rect(fx, y, fw_, 32, "none", rx=8, stroke=LN)
        s.text(fx + 12, cy(y, 32, 13), lab, 13, T1)
        s.icon("chevron-down", fx + fw_ - 22, y + 9, T2, s=14)
        fx += fw_ + 8
    sw_ = x0 + w - fx
    s.rect(fx, y, sw_, 32, SF, rx=8, stroke=LN)
    s.icon("search", fx + 10, y + 8, T2)
    s.text(fx + 34, cy(y, 32, 13), truncate("Поиск", sw_ - 44, 13), 13, T3)
    y += 48
    cols = dict(chk=12, id=40, strat=124, mode=244, status=404, res=588, start=604)
    th(s, x0 + cols["id"], y + 18, "ID")
    th(s, x0 + cols["strat"], y + 18, "Стратегия")
    th(s, x0 + cols["mode"], y + 18, "Режим и датасет")
    th(s, x0 + cols["status"], y + 18, "Статус")
    th(s, x0 + cols["res"], y + 18, "Итог", "end")
    th(s, x0 + cols["start"], y + 18, "Запуск и автор")
    checkbox(s, x0 + cols["chk"], y + 6, False)
    s.rect(x0 + cols["chk"] + 4, y + 13, 8, 2, T3)
    hline(s, x0, y + 28, w)
    y += 28
    picked = {"run-0142", "run-0141"}
    for r in D.RUNS:
        rh = 36
        focus = r["id"] == "run-0139"
        if focus:
            s.rect(x0, y, w, rh, SF)
            s.rect(x0, y, 2, rh, ACC)
        checkbox(s, x0 + cols["chk"], y + 10, r["id"] in picked)
        stc = STATUS_COL[r["status"]]
        s.text(x0 + cols["id"], y + 23, r["id"], 12, T1, 700, mono=True)
        s.text(x0 + cols["strat"], y + 23, r["strategy"], 13, T1)
        s.text(x0 + cols["mode"], y + 16, r["mode"], 12, T1)
        s.text(x0 + cols["mode"], y + 30, r["dataset"], 11, T2, mono=True)
        badge(s, x0 + cols["status"], y + 8, D.STATUS_LABEL[r["status"]], stc, h=20, size=11)
        if r["status"] == "invalid":
            s.text(x0 + cols["status"] + measure(D.STATUS_LABEL[r["status"]], 11, 700) + 20, y + 23, "строка 8", 11, NEG, mono=True)
        rcol = T3 if r["result"] == "—" else (NEG if r["result"].startswith("−") else T1)
        s.text(x0 + cols["res"], y + 23, r["result"], 12, rcol, mono=True, anchor="end")
        s.text(x0 + cols["start"], y + 16, r["started"], 11, T1, mono=True)
        s.text(x0 + cols["start"], y + 30, r["author"], 12, T2)
        hline(s, x0, y + rh, w)
        y += rh
    disclaimer(s, x0, R["py"] - 32 - 14)
    problems(s, R, [
        ("error", D.INVALID_REASON + ". Прогон невалиден, исправьте строку и запустите заново", "run-0139"),
        ("warning", "adj_close в строке 6 пересчитывается задним числом. Прогон получил пометку", "run-0140"),
        ("warning", "Наивный Sharpe 3,40 больше 3: проверьте стратегию на чтение будущего", "run-0137"),
    ])
    # инспектор
    ix, iw = R["ix"] + 16, R["iw"] - 32
    run = D.RUNS[3]
    y = R["iy"] + 32
    s.text(ix, y, run["id"], 16, T1, 700, mono=True)
    badge(s, ix + measure(run["id"], 16, 700, True) + 10, y - 15, D.STATUS_LABEL[run["status"]], NEG, h=20, size=11)
    y += 28
    for lab, val in [("Стратегия", f"{run['strategy']}, черновик"), ("Режим", run["mode"]), ("Датасет", run["dataset"]),
                     ("Запущен", run["started"]), ("Автор", run["author"]), ("Итог", "не засчитан")]:
        kv(s, ix, y, iw, lab, val, lsize=12, vcol=T1 if lab != "Итог" else T2)
        y += 22
    y += 8
    hline(s, R["ix"], y, R["iw"])
    y += 28
    s.text(ix, y, "Почему невалиден", 13, T1, 700)
    y += 16
    # строка кода с волной — та же деталь, что в редакторе
    s.rect(ix, y, iw, 40, BG, rx=8, stroke=LN)
    s.rect(ix, y, 2, 40, NEG)
    s.text(ix + 22, y + 25, "8", 12, T3, anchor="end", mono=True)
    chip(s, ix + 46, y + 11, "t+1", NEG)
    code = D.LOOKAHEAD_CHECKS[2]["code"]
    short = code.split(" -> ")[0]
    cx0 = ix + 68
    for start, tok, col in code_tokens(short):
        s.text(cx0 + measure(short[:start], 12, mono=True), y + 25, tok, 12, col, mono=True)
    a = short.index("close[+1]")
    wave(s, cx0 + measure(short[:a], 12, mono=True), cx0 + measure(short[:a + 9], 12, mono=True), y + 30, NEG, amp=1.6, step=2.6)
    y += 56
    y = s.para(ix, y, D.LOOKAHEAD_CHECKS[2]["msg"], iw, 12, 18, T2)
    y += 8
    y = s.para(ix, y, "Исправьте строку 8 и запустите новый прогон: этот останется в истории как невалидный.", iw, 12, 18, T2)
    y += 10
    btn(s, ix, y, "Открыть строку 8", "secondary", icon="code", w=iw)
    return s


SCREENS = {1: screen_a1, 2: screen_a2, 3: screen_a3, 4: screen_a4, 5: screen_a5, 6: screen_a6, 7: screen_a7}


def main(which=None):
    for n, fn in sorted(SCREENS.items()):
        if which and n not in which:
            continue
        fn().save(os.path.join(OUT, f"A{n}.svg"))
        print("wrote", f"A{n}.svg")


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or None)
