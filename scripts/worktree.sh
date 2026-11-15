#!/usr/bin/env sh
# Worktree на задачу: отдельная папка и ветка на каждую issue, чтобы несколько агентов
# работали в одном репозитории параллельно. Запуск из корня home.
#
#   sh scripts/worktree.sh start <repo> <тип> <N>   свежий main → ветка <тип>/<N> → ../<repo>/.worktrees/<тип>-<N>
#   sh scripts/worktree.sh list                     все worktree во всех репозиториях
#   sh scripts/worktree.sh clean                    убрать worktree и локальные ветки, чьи ветки уже удалены на GitHub (PR влит)
#
# Типы: feat, fix, docs, chore.
set -e

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
REPOS="documentation frontend backend core dsl .github home"

exclude_worktrees() {
  ex="$1/.git/info/exclude"
  grep -qx '.worktrees/' "$ex" 2>/dev/null || echo '.worktrees/' >> "$ex"
}

case "$1" in
  start)
    repo=$2; type=$3; n=$4
    [ -n "$repo" ] && [ -n "$type" ] && [ -n "$n" ] || { echo "usage: start <repo> <feat|fix|docs|chore> <N>"; exit 1; }
    case "$type" in feat|fix|docs|chore) ;; *) echo "тип: feat, fix, docs или chore"; exit 1;; esac
    dir="$ROOT/$repo"
    [ -d "$dir/.git" ] || { echo "нет репозитория $dir — sh scripts/clone-repos.sh"; exit 1; }
    exclude_worktrees "$dir"
    branch="$type/$n"; wt="$dir/.worktrees/$type-$n"
    if [ -d "$wt" ]; then echo "уже есть: $wt"; exit 0; fi
    git -C "$dir" fetch -q origin
    base=$(git -C "$dir" symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
    if git -C "$dir" show-ref -q --verify "refs/remotes/origin/$branch"; then
      git -C "$dir" worktree add -q "$wt" -B "$branch" "origin/$branch"   # продолжить начатую ветку
    else
      git -C "$dir" worktree add -q "$wt" -b "$branch" "$base"
    fi
    echo "$wt  ($branch)"
    ;;
  list)
    for r in $REPOS; do [ -d "$ROOT/$r/.git" ] && git -C "$ROOT/$r" worktree list | grep '\.worktrees' || true; done
    ;;
  clean)
    for r in $REPOS; do
      dir="$ROOT/$r"; [ -d "$dir/.git" ] || continue
      git -C "$dir" fetch -q --prune origin
      git -C "$dir" worktree list --porcelain | awk '/^worktree /{w=$2} /^branch /{print w" "$2}' | while read -r wt ref; do
        case "$wt" in */.worktrees/*) ;; *) continue;; esac
        b=${ref#refs/heads/}
        # ветка была запушена (есть upstream), а на GitHub её уже нет — PR влит, ветка удалена
        pushed=$(git -C "$dir" config "branch.$b.remote" || true)
        if [ -n "$pushed" ] && ! git -C "$dir" show-ref -q --verify "refs/remotes/origin/$b"; then
          if [ -n "$(git -C "$wt" status --porcelain)" ]; then echo "$r $b: есть незакоммиченное, пропускаю"; continue; fi
          git -C "$dir" worktree remove "$wt" && git -C "$dir" branch -D -q "$b" && echo "$r: убран $b"
        fi
      done
      git -C "$dir" worktree prune
      # локальные ветки без worktree, чьи ветки на GitHub удалены после слияния
      git -C "$dir" for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | while read -r b track; do
        [ "$track" = "[gone]" ] && git -C "$dir" branch -D -q "$b" 2>/dev/null && echo "$r: убрана ветка $b"
      done
    done
    ;;
  *)
    sed -n '2,9p' "$0"; exit 1;;
esac
