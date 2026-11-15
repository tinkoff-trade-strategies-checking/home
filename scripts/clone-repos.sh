#!/usr/bin/env sh
# Клонирует недостающие репозитории проекта рядом с home и подтягивает уже склонированные.
# Запуск из корня home: sh scripts/clone-repos.sh
set -e

ORG=tinkoff-trade-strategies-checking
REPOS="documentation frontend backend core .github"
ROOT=$(cd "$(dirname "$0")/../.." && pwd)

for r in $REPOS; do
  dir="$ROOT/$r"
  if [ -d "$dir/.git" ]; then
    echo "$r: pull"
    git -C "$dir" pull --ff-only || echo "$r: pull не удался, разберись вручную"
  else
    echo "$r: clone"
    git clone "https://github.com/$ORG/$r.git" "$dir"
  fi
done
