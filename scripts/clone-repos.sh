#!/usr/bin/env sh
# Клонирует недостающие репозитории проекта рядом с home и подтягивает уже склонированные.
# Запуск из корня home: sh scripts/clone-repos.sh
set -e

ORG=tinkoff-trade-strategies-checking
REPOS="documentation frontend backend core dsl .github"
# Папка с репозиториями — родитель основного клона home (и при запуске из worktree home).
ROOT=$(dirname "$(dirname "$(git -C "$(dirname "$0")" rev-parse --path-format=absolute --git-common-dir)")")

for r in $REPOS; do
  dir="$ROOT/$r"
  if [ -d "$dir/.git" ] && [ -z "$(git -C "$dir" ls-remote --heads origin 2>/dev/null)" ]; then
    echo "$r: на GitHub пока пусто, подтягивать нечего"
  elif [ -d "$dir/.git" ]; then
    echo "$r: pull"
    git -C "$dir" pull --ff-only || echo "$r: pull не удался, разберись вручную"
  else
    echo "$r: clone"
    git clone "https://github.com/$ORG/$r.git" "$dir"
  fi
done
