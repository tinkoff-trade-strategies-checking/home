"""Сборка кликабельного прототипа E (продукт v2) в один файл site/index.html.

Данные берутся из design/shared/data.py, код — из src/. Запуск: python design/prototype/E/build.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shared"))
import data as D  # noqa: E402

ROOT = Path(__file__).parent
SRC = ROOT / "src"
SITE = ROOT / "site"

ORDER_KEYS = ("limit", "stop", "tp", "trail", "tif")


def journal(entries):
    out = []
    for day, paper, side, typ, qty, extra in entries:
        j = dict(t=D.V2_WARMUP - 1 + day, paper=paper, side=side, type=typ, qty=qty)
        j.update({k: v for k, v in extra.items() if k in ORDER_KEYS})
        out.append(j)
    return out


def payload():
    v2 = dict(
        capital=D.V2_CAPITAL, warmup=D.V2_WARMUP, days=D.V2_DAYS, costs=D.V2_COSTS,
        dates=[d.strftime("%d.%m.%Y") for d in D.V2_DATES],
        papers=D.V2_PAPERS, news=D.V2_NEWS, algos=D.V2_ALGOS, versions=D.V2_ALGO_VERSIONS, forks=D.V2_FORKS,
        demo_journal=journal(D.V2_DEMO_JOURNAL), sessions=D.V2_SESSIONS,
    )
    v1 = dict(
        datasets=D.DATASETS, fields=D.DATASET_FIELDS, calendar_gap=D.CALENDAR_GAP, run_config=D.RUN_CONFIG,
        lookahead=D.LOOKAHEAD_CHECKS, result_honest=D.RESULT_HONEST, result_naive=D.RESULT_NAIVE,
        delta=D.DELTA_BREAKDOWN, costs_total=D.COSTS_TOTAL, flags=D.FLAGS, repro=D.REPRO,
        walk_forward=D.WALK_FORWARD, wf_summary=D.WF_SUMMARY, comparison=D.COMPARISON,
    )
    return dict(product=D.PRODUCT, user=D.USER, disclaimer=D.DISCLAIMER, v1=v1, v2=v2)


def main():
    data = json.dumps(payload(), ensure_ascii=False, separators=(",", ":"))
    (ROOT / "build").mkdir(exist_ok=True)
    (ROOT / "build" / "data.json").write_text(data, encoding="utf-8")
    html = (SRC / "index.html").read_text(encoding="utf-8")
    css = (SRC / "style.css").read_text(encoding="utf-8")
    js = "\n".join((SRC / f).read_text(encoding="utf-8") for f in ("engine.js", "charts.js", "app.js"))
    html = html.replace("/*STYLE*/", css).replace("/*DATA*/", "const DATA = " + data + ";").replace("/*APP*/", js)
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(html, encoding="utf-8")
    print(f"site/index.html: {len(html) // 1024} КБ")


if __name__ == "__main__":
    main()
