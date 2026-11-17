#!/usr/bin/env sh
# Метрики проверки по репозиториям организации за последние DAYS дней (по умолчанию 30):
# влитые PR, отклонённые (закрыты без слияния), откаты, влитые с «Проверено: нет» или без строки «Проверено:».
# Запуск из корня home: sh scripts/review-stats.sh [DAYS]
set -e

ORG=tinkoff-trade-strategies-checking
REPOS="documentation frontend backend core dsl .github home"
DAYS=${1:-30}
SINCE=$(date -u -d "-$DAYS days" +%Y-%m-%d 2>/dev/null || python -c "import datetime;print((datetime.date.today()-datetime.timedelta(days=$DAYS)).isoformat())")

printf '%-14s %7s %10s %7s %14s %14s\n' "репозиторий" "влито" "отклонено" "откаты" "проверено:нет" "без отметки"
for r in $REPOS; do
  merged=$(gh pr list -R "$ORG/$r" --state merged --search "merged:>=$SINCE" --limit 500 --json number --jq length 2>/dev/null || echo 0)
  rejected=$(gh pr list -R "$ORG/$r" --state closed --search "closed:>=$SINCE -is:merged" --limit 500 --json number --jq length 2>/dev/null || echo 0)
  reverts=$(gh pr list -R "$ORG/$r" --state merged --search "merged:>=$SINCE" --limit 500 --json title \
    --jq '[.[] | select(.title | test("^(Revert|Откат)"; "i"))] | length' 2>/dev/null || echo 0)
  unverified=$(gh pr list -R "$ORG/$r" --state merged --search "merged:>=$SINCE" --limit 500 --json body \
    --jq '[.[] | select(.body // "" | test("Проверено:\\s*нет"))] | length' 2>/dev/null || echo 0)
  unstamped=$(gh pr list -R "$ORG/$r" --state merged --search "merged:>=$SINCE" --limit 500 --json body \
    --jq '[.[] | select(.body // "" | test("Проверено:") | not)] | length' 2>/dev/null || echo 0)
  printf '%-14s %7s %10s %7s %14s %14s\n' "$r" "$merged" "$rejected" "$reverts" "$unverified" "$unstamped"
done
echo "с $SINCE. Откат — влитый PR с заголовком «Откат…» или «Revert…»."
