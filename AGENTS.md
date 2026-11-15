# home — точка входа для ИИ-агентов

Home-репозиторий проекта «Т-Инвестиции: тренажёр и лаборатория стратегий» (паттерн [Home Repo](https://www.aihero.dev/the-home-repo-pattern)). Агенты запускаются отсюда; код и документация лежат в соседних репозиториях, здесь — указатели на них, общие правила, скиллы и материалы, не принадлежащие одному репозиторию.

## Репозитории

Все лежат рядом с `home` в одной папке. Нет локально — склонируй: `scripts/clone-repos.sh` (или `git clone` из ссылки). Перед работой в репозитории: `git -C ../<repo> pull`, затем прочитай его `AGENTS.md`, если он есть.

- **documentation** (требования, инварианты, юзкейсы, DSL, архитектура, ADR, статус, план реализации): `../documentation`. Клонировать из https://github.com/tinkoff-trade-strategies-checking/documentation. Источник правды по продукту; карта документов — `../documentation/AGENTS.md`.
- **frontend** (Angular + Taiga UI): `../frontend`. Клонировать из https://github.com/tinkoff-trade-strategies-checking/frontend. Пока пустой.
- **backend** (Java, Spring Boot + Spring Modulith; источник OpenAPI и инфраструктуры `deploy/`): `../backend`. Клонировать из https://github.com/tinkoff-trade-strategies-checking/backend. Пока только README.
- **core** (C++20 ядро симуляции рынка; источник `.proto`): `../core`. Клонировать из https://github.com/tinkoff-trade-strategies-checking/core.

`frontend-ai`, `backend-ai`, `core-ai` — приватный архив ранней версии, сгенерированной ИИ. Неактуальны: не клонировать, не брать оттуда код и решения без явной просьбы.

## Как работать

- Задачи — только по issue с [доски](https://github.com/orgs/tinkoff-trade-strategies-checking/projects/2). Процесс, ветки, коммиты, PR, когда обновлять документы — `workflow.md`.
- Перед фичей найди её ФТ, INV и UC в `../documentation` поиском по ID, не читай документы целиком.
- Изменение в нескольких репозиториях — по одному PR в каждом, в порядке контракта (ADR-0007): `core` (`.proto`) → `backend` (копия `.proto`, `api/openapi.yaml`) → `frontend` (копия OpenAPI).
- Коммить и пушь только в тот репозиторий, где изменение. В `home` — только то, что общее для всех репозиториев.
- Если документация противоречит существующему коду, следуй соглашениям, принятым в самом коде, а в финальном ответе укажи каждое найденное несоответствие между документацией и кодом и предложи исправления. Исключение — инварианты из `../documentation/invariants.md`: их нарушение в коде считается багом, его не повторяют, а сообщают о нём.
- Пишем по-русски, коротко. Команда скептически относится к сгенерированному тексту: каждое утверждение — по решению команды, не по догадке.

## Что лежит в home

| Путь | Что |
|---|---|
| `workflow.md` | доска, Status / Size / Priority, задача от начала до конца, коммиты и PR, когда обновлять документы |
| `.agents/skills/` | общие скиллы (Codex, opencode); `.claude/skills/` — переходники для Claude Code |
| `scripts/clone-repos.sh` | клонирует недостающие репозитории рядом с `home` |
| `design/` | генераторы hi-fi макетов для Figma (свой `AGENTS.md`) |
| `context/` | исходники: ТЗ, презентация требований, схема стека |

Скиллы: `miro-board` — чтение и правка Miro-доски.

## Доступ к соседним репозиториям

Агент запущен в `home`, а пишет в `../<repo>`:
- Claude Code — `.claude/settings.json` добавляет соседние папки в `additionalDirectories` (после доверия папке);
- Codex — запускать с `--add-dir ../documentation --add-dir ../frontend --add-dir ../backend --add-dir ../core`;
- opencode — доступ к внешним папкам разрешён по умолчанию.

`AGENTS.md` соседнего репозитория не подгружается сам — открой его перед изменениями.

## Внешние артефакты
- Доска задач: https://github.com/orgs/tinkoff-trade-strategies-checking/projects/2
- Miro-доска «Т-Инвестиции»: https://miro.com/app/board/uXjVEe4xbpg=/ (скилл `miro-board`)
- Figma-файл «ПАК», страница «Концепции» — `design/AGENTS.md`
