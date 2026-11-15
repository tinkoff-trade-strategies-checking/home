# home

Точка входа для ИИ-агентов проекта «Т-Инвестиции: тренажёр и лаборатория стратегий»: указатели на репозитории, общие правила работы, скиллы, дизайн-макеты и исходные материалы. Подробно — [AGENTS.md](AGENTS.md), процесс — [workflow.md](workflow.md).

## Настройка

```sh
mkdir tinkoff && cd tinkoff
git clone https://github.com/tinkoff-trade-strategies-checking/home.git
cd home && sh scripts/clone-repos.sh
```

Получится:

```
tinkoff/
  home/            ← отсюда запускаются агенты
  documentation/
  frontend/
  backend/
  core/
  .github/         ← общие шаблоны issue и PR
```

## Запуск агентов

| Агент | Команда из `home` |
|---|---|
| Claude Code | `claude` — соседние папки подключаются из `.claude/settings.json` после доверия папке |
| Codex | `codex --add-dir ../documentation --add-dir ../frontend --add-dir ../backend --add-dir ../core --add-dir ../.github` |
| opencode | `opencode` |

Работа над одним репозиторием без кросс-репозиторного контекста — можно запускать агента и прямо в нём: его `AGENTS.md` подгрузится сам.
