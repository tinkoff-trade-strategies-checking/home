"""Единый источник фейковых данных для всех пяти концепций.

Все концепции показывают ОДНО и то же исследование, чтобы команда сравнивала UX, а не цифры.
Числа согласованы между собой (наивный → честный = сумма вкладов издержек и задержки).
"""
import math
import random
from datetime import date, timedelta

PRODUCT = "Честная проверка стратегий"
USER = "Денис Муруев"
DISCLAIMER = "Учебное моделирование на исторических данных. Не является инвестиционной рекомендацией."

# --- Датасеты (неизменяемые снапшоты) ---------------------------------------------------
DATASETS = [
    dict(id="ds-0007", source="MOEX ISS", interval="D1", tickers="SBER, GAZP, LKOH, GMKN, YDEX, MOEX + IMOEX",
         period="03.01.2019 — 25.09.2026", fetched="26.09.2026 18:40", sha="3f9a…c21e", schema="v2",
         rows="13 482", status="актуальный", used_in=9),
    dict(id="ds-0006", source="MOEX ISS", interval="D1", tickers="SBER, GAZP, LKOH, GMKN, YDEX, MOEX + IMOEX",
         period="03.01.2019 — 30.06.2026", fetched="01.07.2026 10:12", sha="b41d…07fa", schema="v2",
         rows="12 908", status="заменён ds-0007", used_in=14),
    dict(id="ds-0005", source="MOEX ISS", interval="D1", tickers="SBER, GAZP, LKOH",
         period="03.01.2020 — 29.12.2023", fetched="12.03.2026 21:03", sha="9e02…5b3d", schema="v1",
         rows="3 012", status="устаревшая схема", used_in=3),
    dict(id="cbr-0002", source="ЦБ РФ", interval="D1", tickers="USD/RUB, CNY/RUB",
         period="03.01.2019 — 25.09.2026", fetched="26.09.2026 18:41", sha="71cc…e980", schema="v2",
         rows="3 860", status="актуальный", used_in=2),
    dict(id="syn-0001", source="Генератор GBM + скачки", interval="D1", tickers="SYN1…SYN5",
         period="seed 42, 1 500 баров", fetched="—", sha="—", schema="v2",
         rows="—", status="после MVP", used_in=0),
]
DATASET_CURRENT = DATASETS[0]
# Колонки снапшота и момент доступности значения
DATASET_FIELDS = [
    ("open", "доступно в 10:00 дня t"),
    ("high / low", "после закрытия дня t (18:50)"),
    ("close", "после закрытия дня t (18:50)"),
    ("volume", "после закрытия дня t (18:50)"),
    ("adj_close", "пересчитывается задним числом — запрещено"),
]
CALENDAR_GAP = ("28.02.2022", "23.03.2022", "торги акциями на MOEX не проводились")

# --- Стратегия (DSL в стиле Pine) ------------------------------------------------------
DSL_MAIN = [
    'strategy "Пересечение SMA 20/50"',
    "universe SBER, GAZP, LKOH, GMKN, YDEX, MOEX",
    "capital 1_000_000 RUB",
    "",
    "let fast = sma(close, 20)",
    "let slow = sma(close, 50)",
    "",
    "when fast crosses_above slow -> buy 20% equity",
    "when fast crosses_below slow -> sell all",
    "when drawdown(position) < -12% -> sell all  // стоп",
]
# Три уровня проверки «чтения будущего» (HANDOFF §4.6)
LOOKAHEAD_CHECKS = [
    dict(level="ok", line=5, code="let fast = sma(close, 20)",
         msg="Использует бары до t включительно. Сделка исполнится по open t+1."),
    dict(level="warning", line=6, code="let slow = sma(adj_close, 50)",
         msg="adj_close пересчитывается задним числом по дивидендам, объявленным позже. Замените на close. Прогон получит пометку."),
    dict(level="error", line=8, code="when close[+1] > close -> buy 20% equity",
         msg="close[+1] — это бар t+1, на момент решения он ещё не наступил. Прогон невалиден."),
]
STRATEGIES = [
    dict(name="Пересечение SMA 20/50", short="SMA 20/50", desc="Тренд: покупка при пересечении быстрой средней снизу вверх", runs=12, updated="04.10.2026"),
    dict(name="Моментум 3 мес.", short="Моментум 3М", desc="Ежемесячно держим 2 бумаги с лучшей доходностью за 3 месяца", runs=7, updated="02.10.2026"),
    dict(name="Откат по RSI", short="RSI-откат", desc="Покупка при RSI(14) < 30, продажа при RSI > 55", runs=5, updated="29.09.2026"),
    dict(name="Покупка и удержание IMOEX", short="IMOEX", desc="Бенчмарк: индекс Мосбиржи без ребалансировки", runs=3, updated="26.09.2026"),
]

# --- Настройки прогона -------------------------------------------------------------------
RUN_CONFIG = dict(
    dataset="ds-0007", period="03.01.2020 — 30.12.2025", capital="1 000 000 ₽", bars="D1, 1 545 торговых дней",
    commission="0,05 % от оборота", exchange_fee="0,01 % от оборота", spread="половина спреда, 0,08 %",
    slippage="0,10 % + 0,5 × доля в объёме бара", liquidity="не больше 5 % объёма бара; остаток — частичное исполнение или отказ",
    delay="исполнение по open следующего бара", stop_rule="конец периода или капитал ≤ 0",
    walk_forward="1 год подбор / 3 месяца проверка / сдвиг 3 месяца", mode="наивный и честный прогон вместе",
    seed="20261005",
)
STRESS_PRESETS = [
    dict(name="24.02.2022", desc="Гэп −33 % по индексу, затем закрытие торгов на 18 дней", gap="−33 %", vol="× 3,0", volume="× 0,4", slip="× 4"),
    dict(name="Март 2020", desc="Падение на 30 % за 4 недели, волатильность × 2,5", gap="−8 %", vol="× 2,5", volume="× 1,6", slip="× 2"),
    dict(name="Свой сценарий", desc="Задайте параметры вручную", gap="−X %", vol="× k", volume="× q", slip="× s"),
]

# --- Результаты: честный и наивный прогоны SMA 20/50 -----------------------------------
RUN_ID = "run-0142"
RESULT_HONEST = dict(
    final="1 316 000 ₽", total="+31,6 %", cagr="+4,7 %", gross="+57,5 %", net="+31,6 %",
    max_dd="−27,4 %", dd_days="214 дней", dd_period="24.02.2022 — 05.01.2023", vol="17,8 %",
    sharpe="0,41", sortino="0,58", turnover="13,9× в год", trades="412", win_rate="44,6 %",
    partial="11", rejected="6", hhi="0,23", top_position="SBER, 29,8 %",
    benchmark="+9,4 %", vs_benchmark="+22,2 п.п.",
)
RESULT_NAIVE = dict(
    final="1 842 000 ₽", total="+84,2 %", cagr="+10,7 %", max_dd="−18,9 %", sharpe="1,12", sortino="1,71",
    trades="436", win_rate="51,2 %",
)
# Разложение разницы наивный → честный, в п.п. (сумма = 52,6)
DELTA_BREAKDOWN = [
    ("Задержка: исполнение по open t+1", -21.4, None),
    ("Спред", -9.8, "97 900 ₽"),
    ("Проскальзывание", -8.7, "86 600 ₽"),
    ("Комиссия брокера", -6.2, "62 300 ₽"),
    ("Лимит ликвидности: 11 частичных, 6 отказов", -5.2, None),
    ("Биржевой сбор", -1.3, "12 500 ₽"),
]
COSTS_TOTAL = "259 300 ₽"
FLAGS = [
    dict(level="warning", text="Издержки и задержка съели 62 % наивной прибыли (порог 50 %)"),
    dict(level="warning", text="adj_close в строке 6 заменён на close: пометка «подозрительно» снята после правки"),
    dict(level="info", text="28.02 — 23.03.2022 торги не проводились: 18 дней пропущены по торговому календарю"),
    dict(level="info", text="11 заявок исполнены частично, 6 отклонены: объём больше 5 % бара"),
]
REPRO = dict(run=RUN_ID, dataset="ds-0007, sha 3f9a…c21e", strategy="SMA 20/50, версия 4, sha 8d10…4ab2",
             engine="движок 0.3.1", seed="20261005", started="05.10.2026 14:22", duration="3,8 с")

# --- Сравнение нескольких стратегий ----------------------------------------------------
COMPARISON = [
    dict(name="SMA 20/50", honest="+31,6 %", naive="+84,2 %", h=31.6, n=84.2, sharpe="0,41", sharpe_naive="1,12", dd="−27,4 %", turnover="13,9×", flag="издержки > 50 % прибыли"),
    dict(name="Моментум 3М", honest="+44,9 %", naive="+71,3 %", h=44.9, n=71.3, sharpe="0,58", sharpe_naive="3,40", dd="−31,2 %", turnover="6,1×", flag="наивный Sharpe > 3"),
    dict(name="RSI-откат", honest="−6,8 %", naive="+38,5 %", h=-6.8, n=38.5, sharpe="−0,12", sharpe_naive="1,90", dd="−22,9 %", turnover="24,7×", flag="издержки меняют знак результата"),
    dict(name="IMOEX", honest="+9,4 %", naive="+9,4 %", h=9.4, n=9.4, sharpe="0,11", sharpe_naive="0,11", dd="−43,1 %", turnover="0", flag=None),
]

# --- Walk-forward: 1 год подбор / 3 мес. проверка / сдвиг 3 мес. -------------------------
_WF_TEST = [2.1, -3.4, 4.8, 1.2, -1.9, 0.6, 3.3, -0.8, -6.7, -2.2, 5.9, 1.4, 0.3, -1.1, 2.7, 3.9, -2.6, 1.8, 0.9, -0.4]
_WF_TRAIN = [9.8, 11.2, 7.5, 12.6, 8.1, 10.4, 6.9, 13.3, 9.0, 4.2, 7.7, 10.9, 8.8, 6.1, 11.7, 9.5, 7.2, 8.4, 10.1, 6.6]
_WF_PARAMS = ["20/50", "20/50", "15/45", "15/45", "20/60", "20/50", "25/60", "20/50", "15/40", "15/40",
              "20/50", "20/55", "20/55", "25/60", "20/50", "20/50", "15/45", "20/50", "20/55", "20/50"]


def _q(d):
    return f"{('I', 'II', 'III', 'IV')[(d.month - 1) // 3]} кв. {d.year}"


WALK_FORWARD = []
for _i in range(20):
    _start = date(2021, 1, 1)
    _m = _i * 3
    _ts = date(_start.year + (_start.month - 1 + _m) // 12, (_start.month - 1 + _m) % 12 + 1, 1)
    _tr = date(_ts.year - 1, _ts.month, 1)
    WALK_FORWARD.append(dict(n=_i + 1, train=f"{_tr.strftime('%m.%Y')} — {_ts.strftime('%m.%Y')}",
                             test=_q(_ts), test_ret=_WF_TEST[_i], train_ret=_WF_TRAIN[_i], params=_WF_PARAMS[_i]))
WF_SUMMARY = dict(windows="20", positive="12 из 20", oos_avg="+0,5 % за квартал", is_avg="+9,0 % за квартал",
                  degradation="−95 %", oos_total="+9,3 %", stable_param="20/50 выбран в 9 окнах из 20")

# --- История прогонов -----------------------------------------------------------------
RUNS = [
    dict(id="run-0142", strategy="SMA 20/50", mode="честный", dataset="ds-0007", status="valid", result="+31,6 %", started="05.10.2026 14:22", author="Денис М."),
    dict(id="run-0141", strategy="SMA 20/50", mode="наивный", dataset="ds-0007", status="valid", result="+84,2 %", started="05.10.2026 14:22", author="Денис М."),
    dict(id="run-0140", strategy="SMA 20/50", mode="честный", dataset="ds-0007", status="warning", result="+36,0 %", started="05.10.2026 13:58", author="Денис М."),
    dict(id="run-0139", strategy="SMA 20/50", mode="честный", dataset="ds-0007", status="invalid", result="—", started="05.10.2026 13:41", author="Денис М."),
    dict(id="run-0138", strategy="Моментум 3М", mode="честный", dataset="ds-0007", status="valid", result="+44,9 %", started="04.10.2026 19:05", author="Максим Т."),
    dict(id="run-0137", strategy="Моментум 3М", mode="наивный", dataset="ds-0007", status="warning", result="+71,3 %", started="04.10.2026 19:05", author="Максим Т."),
    dict(id="run-0136", strategy="RSI-откат", mode="честный", dataset="ds-0006", status="valid", result="−6,8 %", started="03.10.2026 16:47", author="Владислав Г."),
    dict(id="run-0135", strategy="RSI-откат", mode="наивный", dataset="ds-0006", status="valid", result="+38,5 %", started="03.10.2026 16:47", author="Владислав Г."),
    dict(id="run-0134", strategy="SMA 20/50", mode="стресс 24.02.2022", dataset="ds-0007", status="valid", result="−12,3 %", started="02.10.2026 12:10", author="Настя"),
    dict(id="run-0133", strategy="IMOEX", mode="честный", dataset="ds-0006", status="valid", result="+9,4 %", started="01.10.2026 11:30", author="Настя"),
]
STATUS_LABEL = {"valid": "Валиден", "warning": "С пометкой", "invalid": "Невалиден"}
INVALID_REASON = "run-0139: close[+1] в строке 8 читает бар t+1"


# --- Временные ряды (детерминированно) -----------------------------------------------
def trading_days(start=date(2020, 1, 3), end=date(2025, 12, 30)):
    d, out = start, []
    gap0, gap1 = date(2022, 2, 28), date(2022, 3, 23)
    while d <= end:
        if d.weekday() < 5 and not (gap0 <= d <= gap1):
            out.append(d)
        d += timedelta(days=1)
    return out


DAYS = trading_days()


def _series(seed, total_ret, vol, shocks):
    """Случайное блуждание, притянутое к нужной итоговой доходности, с шоками в датах."""
    rnd = random.Random(seed)
    n = len(DAYS)
    steps = [rnd.gauss(0, vol / math.sqrt(252)) for _ in range(n)]
    for i, d in enumerate(DAYS):
        for sd, size, span in shocks:
            if sd <= d < sd + timedelta(days=span):
                steps[i] += size / max(1, span * 5 / 7)
    cum, s = [], 0.0
    for x in steps:
        s += x
        cum.append(s)
    drift = (math.log(1 + total_ret) - cum[-1]) / n
    return [math.exp(c + drift * (i + 1)) for i, c in enumerate(cum)]


def _shock(c):
    return [(date(2020, 2, 24), -c * 0.7, 26), (date(2022, 2, 21), -c, 6)]


# Множители капитала (1.0 = 1 000 000 ₽). Seed подобраны так, чтобы макс. просадка совпадала с метриками.
EQUITY_HONEST = _series(55, 0.316, 0.10, _shock(0.26))     # макс. просадка −27,4 %
EQUITY_NAIVE = _series(147, 0.842, 0.08, _shock(0.18))     # −18,9 %
EQUITY_IMOEX = _series(126, 0.094, 0.12, _shock(0.26))     # −43,1 %
EQUITY_MOMENTUM = _series(83, 0.449, 0.11, _shock(0.30))   # −31,2 %
EQUITY_RSI = _series(290, -0.068, 0.08, _shock(0.18))      # −22,9 %


def drawdown(eq):
    peak, out = eq[0], []
    for v in eq:
        peak = max(peak, v)
        out.append(v / peak - 1)
    return out


def candles(seed=7, n=90, start_price=268.0):
    """Свечи SBER (D1) для фрагмента графика + маркеры сделок."""
    rnd = random.Random(seed)
    out, p = [], start_price
    for i in range(n):
        o = p * (1 + rnd.gauss(0, 0.004))
        c = o * (1 + rnd.gauss(0.0006 if i < 55 else -0.0012, 0.014))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.006)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.006)))
        v = rnd.uniform(0.6, 1.6)
        out.append(dict(o=o, h=h, l=l, c=c, v=v))
        p = c
    return out


CANDLE_DATES = ("01.09.2025", "31.12.2025")
TRADE_MARKERS = [  # индекс свечи, тип, подпись
    (14, "buy", "Покупка 210 шт. по 271,40 (open t+1)"),
    (41, "partial", "Частично: 120 из 210 шт."),
    (58, "sell", "Продажа всё по 284,95"),
    (72, "rejected", "Отказ: объём > 5 % бара"),
]


# =========================================================================================
# Продукт v2: тренажёр трейдера и лаборатория стратегий (кликабельный прототип E)
# =========================================================================================
# Демо-данные синтетические (seed), по форме повторяют весну 2020: обвал в марте, отскок в апреле — мае.
V2_CAPITAL = 1_000_000
V2_WARMUP = 50          # свечей истории до старта сессии (нужны алгоритмам для SMA 50)
V2_DAYS = 60            # длительность сессии в свечах D1
V2_START = date(2020, 2, 26)
V2_HOLIDAYS = {date(2019, 12, 31), date(2020, 1, 1), date(2020, 1, 2), date(2020, 1, 7), date(2020, 2, 24),
               date(2020, 3, 9), date(2020, 5, 1), date(2020, 5, 11)}
V2_COSTS = dict(commission=0.0005, fee=0.0001, spread=0.0008, slippage=0.001, slip_k=0.5, liquidity=0.05)


def _v2_dates():
    fwd, d = [], V2_START
    while len(fwd) < V2_DAYS:
        if d.weekday() < 5 and d not in V2_HOLIDAYS:
            fwd.append(d)
        d += timedelta(days=1)
    back, d = [], V2_START - timedelta(days=1)
    while len(back) < V2_WARMUP:
        if d.weekday() < 5 and d not in V2_HOLIDAYS:
            back.append(d)
        d -= timedelta(days=1)
    return list(reversed(back)) + fwd


V2_DATES = _v2_dates()


def _v2_candles(seed, segments, gaps, vol, base_volume):
    """Свечи по сегментам (свечей, итоговая доходность) с гэпами на открытии {индекс: доля}."""
    rnd = random.Random(seed)
    rets = []
    for n, total in segments:
        noise = [rnd.gauss(0, vol) for _ in range(n)]
        i0 = len(rets)
        gsum = sum(math.log(1 + g) for k, g in gaps.items() if i0 <= k < i0 + n)
        drift = (math.log(1 + total) - gsum - sum(noise)) / n
        rets += [x + drift for x in noise]
    out, p = [], 100.0
    for i, r in enumerate(rets):
        g = gaps.get(i, 0.0)
        o = p * (1 + g) * (1 + rnd.gauss(0, vol * 0.25))
        c = p * math.exp(r + math.log(1 + g))
        h = max(o, c) * (1 + abs(rnd.gauss(0, vol * 0.45)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, vol * 0.45)))
        v = base_volume * (0.7 + 0.6 * rnd.random()) * (1 + 18 * abs(c / p - 1))
        out.append([o, h, l, c, v])
        p = c
    k = 100.0 / out[0][0]          # слепой режим: первая свеча = 100
    return [dict(o=round(o * k, 2), h=round(h * k, 2), l=round(l * k, 2), c=round(c * k, 2), v=int(v))
            for o, h, l, c, v in out]


# Индексы: 0..49 — история до старта, 50..109 — дни сессии 1..60
V2_PAPERS = [
    dict(id="A", sector="Банки", ticker="SBER", name="Сбербанк", real_start=253.8,
         candles=_v2_candles(2020, [(50, 0.07), (17, -0.38), (18, 0.17), (25, 0.09)], {58: -0.06, 67: 0.05}, 0.016, 42000)),
    dict(id="B", sector="Газ", ticker="GAZP", name="Газпром", real_start=245.1,
         candles=_v2_candles(2021, [(50, 0.04), (17, -0.24), (18, 0.05), (25, -0.04)], {58: -0.07}, 0.014, 48000)),
    dict(id="C", sector="Нефть", ticker="LKOH", name="Лукойл", real_start=6290.0,
         candles=_v2_candles(2022, [(50, 0.05), (17, -0.41), (18, 0.24), (25, 0.11)], {58: -0.15, 82: 0.07}, 0.018, 26000)),
]


def _v2_day(d):
    """Индекс свечи, вместе с которой новость становится видна (первый торговый день не раньше d)."""
    return next(i for i, x in enumerate(V2_DATES) if x >= d)


# Обезличенные новости (только для людей): без компаний, людей, дат, сумм и примет эпохи
_V2_NEWS = [
    (date(2020, 2, 27), "10:40", None, "Число заражений новым вирусом за пределами страны-источника впервые превысило число новых случаев внутри неё.",
     "ВОЗ: число новых случаев COVID-19 за пределами Китая впервые превысило число случаев в Китае"),
    (date(2020, 3, 6), "17:20", "Нефть", "Переговоры крупнейших стран-экспортёров нефти о продлении сокращения добычи завершились без соглашения.",
     "Переговоры ОПЕК+ в Вене о продлении сделки провалились"),
    (date(2020, 3, 10), "09:30", "Нефть", "Цены на нефть за выходные упали на четверть: крупнейшее падение за несколько десятилетий.",
     "Brent упала на 25 %: крупнейшее падение с 1991 года"),
    (date(2020, 3, 10), "11:15", None, "Национальная валюта ослабла до многолетних минимумов вслед за сырьём.",
     "Рубль упал до минимума с 2016 года, доллар выше 75 ₽"),
    (date(2020, 3, 16), "19:00", None, "Регулятор крупнейшей экономики мира экстренно снизил ставку почти до нуля.",
     "ФРС экстренно снизила ставку до 0–0,25 %"),
    (date(2020, 3, 20), "13:30", "Банки", "Центральный банк сохранил ключевую ставку и допустил её снижение на ближайших заседаниях.",
     "Банк России сохранил ключевую ставку на уровне 6 %"),
    (date(2020, 3, 25), "19:10", None, "Власти объявили нерабочую неделю по всей стране с сохранением зарплат.",
     "Объявлена нерабочая неделя с 28 марта по 5 апреля"),
    (date(2020, 4, 13), "08:45", "Нефть", "Страны-экспортёры договорились о рекордном сокращении добычи нефти.",
     "ОПЕК+ договорилась сократить добычу на 9,7 млн баррелей в сутки"),
    (date(2020, 4, 21), "09:05", "Нефть", "Один из мировых нефтяных фьючерсов впервые в истории торговался по отрицательной цене.",
     "Майский фьючерс на WTI ушёл в минус: −37 $ за баррель"),
    (date(2020, 4, 24), "13:30", "Банки", "Центральный банк снизил ключевую ставку на 0,5 п.п. и пообещал продолжить снижение.",
     "Банк России снизил ключевую ставку до 5,5 %"),
    (date(2020, 4, 29), "16:20", "Газ", "Экспортная выручка крупного газового экспортёра за квартал сократилась почти вдвое.",
     "Экспортная выручка Газпрома в I квартале снизилась на 44 %"),
    (date(2020, 5, 12), "12:00", None, "Объявлено поэтапное снятие ограничений, введённых из-за эпидемии.",
     "Объявлено завершение периода нерабочих дней с 12 мая"),
    (date(2020, 5, 19), "07:50", "Банки", "Крупнейший банк страны сообщил о падении квартальной прибыли почти наполовину из-за резервов.",
     "Сбербанк: чистая прибыль по МСФО в I квартале снизилась на 47 %"),
]
V2_NEWS = [dict(t=_v2_day(d), time=tm, sector=sec, text=txt, original=orig, date=d.strftime("%d.%m.%Y"))
           for d, tm, sec, txt, orig in _V2_NEWS]

# Алгоритмы открытой мастерской. impl — как их исполняет прототип (те же правила, что в DSL).
V2_ALGOS = [
    dict(id="sma", name="Пересечение SMA", author="Денис Муруев", version=4, updated="04.10.2026",
         desc="Тренд: покупка при пересечении быстрой средней снизу вверх", forks=3, runs=214,
         impl=dict(kind="sma", fast=20, slow=50, size=0.2),
         buy_because="тренд вверх: SMA{fast} = {a} выше SMA{slow} = {b}",
         sell_because="тренд сломан: SMA{fast} = {a} ниже SMA{slow} = {b}",
         dsl=['algorithm "Пересечение SMA"', "param fast = 20", "param slow = 50", "param size = 20%", "",
              "let f = sma(close, fast)", "let s = sma(close, slow)", "",
              "when f crosses_above s -> buy size equity",
              '  because "тренд вверх: SMA{fast} = {f} выше SMA{slow} = {s}"',
              "when f crosses_below s -> sell all",
              '  because "тренд сломан: SMA{fast} = {f} ниже SMA{slow} = {s}"'],
         lint=[], rating=dict(score=71, windows=200, median="+2,4 %", profitable="58 %", dd="−9,8 %",
                              regimes=dict(up=5.1, down=-3.9, flat=-0.8))),
    dict(id="rsi", name="Откат по RSI", author="Владислав Гаев", version=3, updated="29.09.2026",
         desc="Покупка на перепроданности, продажа, когда RSI вернулся к середине", forks=1, runs=96,
         impl=dict(kind="rsi", period=14, low=30, high=55, size=0.2),
         buy_because="перепроданность, RSI = {a}", sell_because="RSI вернулся к середине, RSI = {a}",
         dsl=['algorithm "Откат по RSI"', "param period = 14", "param low = 30", "param high = 55", "param size = 20%", "",
              "let r = rsi(close, period)", "",
              "when r < low and position = 0 -> buy size equity",
              '  because "перепроданность, RSI = {r}"',
              "when r > high -> sell all",
              '  because "RSI вернулся к середине, RSI = {r}"'],
         lint=[], rating=dict(score=54, windows=200, median="+0,6 %", profitable="51 %", dd="−12,6 %",
                              regimes=dict(up=1.2, down=-1.4, flat=2.3))),
    dict(id="mom", name="Моментум 20 дней", author="Максим Токарев", version=2, updated="02.10.2026",
         desc="Держим бумагу, пока её доходность за 20 дней выше порога", forks=2, runs=131,
         impl=dict(kind="mom", lookback=20, enter=0.05, exit=0.0, size=0.2),
         buy_because="рост за {lookback} дней = {a} %, выше порога {enter} %",
         sell_because="рост за {lookback} дней = {a} %, ниже нуля",
         dsl=['algorithm "Моментум 20 дней"', "param lookback = 20", "param enter = 5%", "param exit = 0%", "param size = 20%", "",
              "let m = close / close[lookback] - 1", "",
              "when m > enter and position = 0 -> buy size equity",
              '  because "рост за {lookback} дней = {m}, выше порога {enter}"',
              "when m < exit -> sell all",
              '  because "рост за {lookback} дней = {m}, ниже нуля"'],
         lint=[], rating=dict(score=63, windows=200, median="+1,7 %", profitable="55 %", dd="−11,2 %",
                              regimes=dict(up=6.3, down=-5.2, flat=-1.9))),
    dict(id="brk", name="Пробой канала", author="Настя", version=1, updated="30.09.2026",
         desc="Покупка на пробое 20-дневного максимума, выход ниже 10-дневного минимума", forks=0, runs=58,
         impl=dict(kind="brk", enter=20, exit=10, size=0.2),
         buy_because="пробой максимума {enter} дней: close = {a} выше {b}",
         sell_because="пробой минимума {exit} дней: close = {a} ниже {b}",
         dsl=['algorithm "Пробой канала"', "param enter = 20", "param exit = 10", "param size = 20%", "",
              "let top = highest(high[1], enter)", "let bottom = lowest(low[1], exit)", "",
              "when close > top and position = 0 -> buy size equity",
              '  because "пробой максимума {enter} дней: close = {close} выше {top}"',
              "when close < bottom -> sell all",
              '  because "пробой минимума {exit} дней: close = {close} ниже {bottom}"'],
         lint=[], rating=dict(score=58, windows=200, median="+1,1 %", profitable="47 %", dd="−8,4 %",
                              regimes=dict(up=4.4, down=-2.1, flat=-2.6))),
    dict(id="smavol", name="SMA с фильтром волатильности", author="Максим Токарев", version=1, updated="06.10.2026",
         desc="Форк «Пересечение SMA»: не входит, когда рынок слишком нервный", forks=0, runs=17,
         forked_from=["sma", 4, "Денис Муруев"],
         impl=dict(kind="sma", fast=20, slow=50, size=0.2, atr=14, atr_max=0.035),
         buy_because="тренд вверх и рынок спокоен: SMA{fast} = {a} выше SMA{slow} = {b}",
         sell_because="тренд сломан: SMA{fast} = {a} ниже SMA{slow} = {b}",
         dsl=['algorithm "SMA с фильтром волатильности"', 'fork of "Пересечение SMA" v4 by "Денис Муруев"',
              "param fast = 20", "param slow = 50", "param size = 20%", "",
              "let f = sma(close, fast)", "let s = sma(close, slow)", "let calm = atr(14) / close < 0.035", "",
              "when f crosses_above s and calm -> buy size equity",
              '  because "тренд вверх и рынок спокоен: SMA{fast} = {f} выше SMA{slow} = {s}"',
              "when f crosses_below s -> sell all",
              '  because "тренд сломан: SMA{fast} = {f} ниже SMA{slow} = {s}"'],
         lint=[dict(line=9, const="14", name="atr_period"), dict(line=9, const="0.035", name="calm_max")],
         rating=dict(score=66, windows=200, median="+2,0 %", profitable="56 %", dd="−7,9 %",
                     regimes=dict(up=3.8, down=-1.6, flat=-0.4))),
]
V2_ALGO_VERSIONS = {  # версии неизменяемы: правка = новая версия
    "sma": [(4, "04.10.2026", "8d10…4ab2", "Размер позиции вынесен в параметр size"),
            (3, "27.09.2026", "51c7…e019", "Добавлены причины because"),
            (2, "20.09.2026", "0b3e…77d4", "Окна 20/50 вместо 15/45 по итогам walk-forward"),
            (1, "12.09.2026", "e4a2…1c90", "Первая публикация")],
}
V2_FORKS = {"sma": [("SMA с фильтром волатильности", "Максим Токарев", "v1"), ("SMA 10/30 быстрая", "Настя", "v2"),
                    ("SMA на недельных свечах", "Владислав Гаев", "v1")]}

# Журнал демо-сессии: (день, бумага, сторона, тип, штук, параметры).
# День d — человек видел свечи по день d включительно; исполнение начинается с открытия дня d+1.
V2_DEMO_JOURNAL = [
    (0, "A", "buy", "market", 1500, {}),
    (0, "C", "buy", "limit", 1800, dict(limit=99.0, tif="gtc")),
    (5, "A", "buy", "market", 800, {}),
    (8, "C", "sell", "market", 1800, {}),
    (9, "B", "buy", "stop_limit", 1200, dict(stop=101.0, limit=102.0)),
    (12, "A", "sell", "stop", 2300, dict(stop=74.0)),
    (17, "C", "buy", "market", 2600, {}),
    (17, "C", "sell", "oco", 2600, dict(tp=78.0, stop=52.0)),
    (24, "A", "buy", "limit", 2000, dict(limit=71.0, tif="gtc")),
    (32, "B", "buy", "market", 1500, {}),
    (37, "B", "sell", "trailing", 1500, dict(trail=4.0)),
    (44, "A", "buy", "market", 1200, {}),
    (55, "A", "sell", "take_profit", 3200, dict(tp=84.0)),
]

V2_SESSIONS = [  # у сессий без журнала прототип строит журнал по seed
    dict(id="s-0031", who="human", author="Настя", blind=True, papers="ABC", started="21.10.2026 19:40", seed=31),
    dict(id="s-0030", who="algo", algo="mom", author="Максим Т.", blind=True, papers="ABC", started="21.10.2026 15:02"),
    dict(id="s-0029", who="human", author="Владислав Г.", blind=False, papers="AC", started="20.10.2026 21:17", seed=29),
    dict(id="s-0028", who="algo", algo="sma", author="Денис М.", blind=True, papers="ABC", started="20.10.2026 12:30"),
    dict(id="s-0027", who="human", author="Денис М.", blind=True, papers="ABC", started="19.10.2026 18:05", demo=True),
    dict(id="s-0026", who="human", author="Настя", blind=True, papers="A", started="18.10.2026 11:44", seed=26),
    dict(id="s-0025", who="algo", algo="rsi", author="Владислав Г.", blind=True, papers="ABC", started="17.10.2026 16:20"),
    dict(id="s-0024", who="human", author="Максим Т.", blind=True, papers="ABC", started="16.10.2026 20:08", seed=24),
]
