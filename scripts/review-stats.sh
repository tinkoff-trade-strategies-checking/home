#!/usr/bin/env sh
# Метрики проверки по репозиториям организации за последние DAYS дней (по умолчанию 30):
# влитые PR, отклонённые (закрыты без слияния), откаты, влитые с «Проверено: нет» или без строки «Проверено:»,
# доля влитых PR больше лимита кода (>400 строк без тестов, фикстур, заглушек, сгенерированного и lock-файлов).
# Запуск из корня home: sh scripts/review-stats.sh [DAYS]
set -e

ORG=tinkoff-trade-strategies-checking
REPOS="documentation frontend backend core dsl .github home"
DAYS=${1:-30}
SIZE_LIMIT=400
EXCLUDE_RE='(^|/)(tests?|e2e|__tests__|testdata|fixtures?|__fixtures__|mocks?|__mocks__|stubs?|generated|gen|__generated__)/|(\.spec|\.test|_test|Test|Tests|\.mock|\.stub|\.fixture|_mock|_stub)\.[^/]+$|\.(pb|grpc\.pb|generated|gen)\.|(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|gradle\.lockfile)$|\.lock$'
SINCE=$(date -u -d "-$DAYS days" +%Y-%m-%d 2>/dev/null || python -c "import datetime;print((datetime.date.today()-datetime.timedelta(days=$DAYS)).isoformat())")

printf '%-14s %7s %10s %7s %14s %14s %12s\n' "репозиторий" "влито" "отклонено" "откаты" "проверено:нет" "без отметки" ">${SIZE_LIMIT} строк"
total_merged=0
total_oversized=0
for r in $REPOS; do
  merged_json=$(gh pr list -R "$ORG/$r" --state merged --search "merged:>=$SINCE" --limit 500 --json number,title,body,files 2>/dev/null || echo '[]')
  stats=$(printf '%s' "$merged_json" | python -c "
import json, re, sys
limit = int(sys.argv[1])
excl = re.compile(sys.argv[2])
prs = json.loads(sys.stdin.buffer.read().decode('utf-8'))
merged = len(prs)
reverts = sum(1 for p in prs if re.match(r'^(Revert|Откат)', p.get('title') or '', re.I))
unverified = sum(1 for p in prs if re.search(r'Проверено:\s*нет', p.get('body') or ''))
unstamped = sum(1 for p in prs if 'Проверено:' not in (p.get('body') or ''))
oversized = 0
for p in prs:
    lines = sum((f.get('additions') or 0) + (f.get('deletions') or 0)
                for f in (p.get('files') or []) if not excl.search(f.get('path') or ''))
    if lines > limit:
        oversized += 1
print(merged, reverts, unverified, unstamped, oversized)
" "$SIZE_LIMIT" "$EXCLUDE_RE")
  set -- $stats
  merged=$1; reverts=$2; unverified=$3; unstamped=$4; oversized=$5
  rejected=$(gh pr list -R "$ORG/$r" --state closed --search "closed:>=$SINCE -is:merged" --limit 500 --json number --jq length 2>/dev/null || echo 0)
  total_merged=$((total_merged + merged))
  total_oversized=$((total_oversized + oversized))
  if [ "$merged" -gt 0 ]; then
    pct=$((oversized * 100 / merged))
    over_fmt="${oversized} (${pct}%)"
  else
    over_fmt="0 (0%)"
  fi
  printf '%-14s %7s %10s %7s %14s %14s %12s\n' "$r" "$merged" "$rejected" "$reverts" "$unverified" "$unstamped" "$over_fmt"
done
if [ "$total_merged" -gt 0 ]; then
  total_pct=$((total_oversized * 100 / total_merged))
else
  total_pct=0
fi
echo "с $SINCE. Итого >${SIZE_LIMIT} строк кода: ${total_oversized}/${total_merged} (${total_pct}%)."
echo "Откат — влитый PR с заголовком «Откат…» или «Revert…». Размер >${SIZE_LIMIT} считается по additions+deletions без тестов, фикстур, заглушек, сгенерированного и lock-файлов."
