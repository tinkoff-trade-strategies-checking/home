"""Здоровье проекта: факты о том, чего не хватает и что требует внимания.

Запуск из корня home: python scripts/project-health.py [--json]
Скрипт только читает (git, gh) и ничего не меняет. Решения по фактам принимает скилл `next`.
Каждая находка: уровень (block — мешает работе, gap — пробел, info — к сведению), где, что, что сделать.
"""
import datetime
import json
import os
import re
import subprocess
import sys

ORG = "tinkoff-trade-strategies-checking"
PROJECT = 2
CODE_REPOS = ["frontend", "backend", "core", "dsl"]
ALL_REPOS = ["documentation", "frontend", "backend", "core", "dsl", ".github", "home"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Корень основного клона home (а не worktree, из которого может идти запуск): родитель общего .git.
HOME = os.path.dirname(os.path.abspath(subprocess.run(
    ["git", "-C", SCRIPT_DIR, "rev-parse", "--path-format=absolute", "--git-common-dir"],
    capture_output=True, text=True, encoding="utf-8").stdout.strip()))
ROOT = os.path.dirname(HOME)
TODAY = datetime.date.today()

# Пороги
STALE_IN_PROGRESS_DAYS = 7
OLD_PR_DAYS = 3
EVAL_EVERY_DAYS = 30
MIN_CODE_FILES = 5  # меньше — репозиторий считается «ещё без кода»

findings = []


def add(level, where, what, action):
    findings.append({"level": level, "where": where, "what": what, "action": action})


def run(*args, cwd=None):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{args[0]} завершился с кодом {result.returncode}")
    return result.stdout


def gh_json(*args):
    return json.loads(run("gh", *args) or "null")


def days_since(iso):
    return (TODAY - datetime.date.fromisoformat(iso[:10])).days


def repo_dir(repo):
    return os.path.join(ROOT, repo)


# ---------- Репозитории: слой проверки ----------

def check_repos():
    for repo in ALL_REPOS:
        path = repo_dir(repo)
        if not os.path.isdir(os.path.join(path, ".git")):
            add("block", repo, "нет локального клона", "sh scripts/clone-repos.sh")
            continue
        behind = run("git", "-C", path, "rev-list", "--count", "HEAD..@{upstream}").strip() if has_upstream(path) else "0"
        if behind not in ("", "0"):
            add("info", repo, f"локальная копия отстаёт на {behind} коммит(ов)", "sh scripts/clone-repos.sh")

    for repo in CODE_REPOS:
        path = repo_dir(repo)
        if not os.path.isdir(os.path.join(path, ".git")):
            continue
        files = [f for f in run("git", "-C", path, "ls-files").splitlines()
                 if not re.match(r"(README|AGENTS|LICENSE)[^/]*$|\.github/|\.gitignore$", f)]
        if len(files) < MIN_CODE_FILES:
            continue  # кода ещё нет — слой проверки появится вместе с каркасом
        where = f"{repo} (кода: {len(files)} файлов)"
        agents = os.path.join(path, "AGENTS.md")
        if not os.path.exists(agents):
            add("gap", where, "нет AGENTS.md", "завести AGENTS.md с разделами «Команды» и «Структура»")
        else:
            text = open(agents, encoding="utf-8").read()
            commands = re.search(r"^## Команды\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
            if not commands or "Заполнить" in commands.group(1) or len(commands.group(1).strip()) < 40:
                add("gap", where, "в AGENTS.md нет рабочего раздела «Команды» (сборка, линтер, тесты, запуск)",
                    "заполнить — по нему работает скилл verify")
        workflows = os.path.join(path, ".github", "workflows")
        if not (os.path.isdir(workflows) and os.listdir(workflows)):
            add("gap", where, "нет CI (.github/workflows)", "CI: сборка, линтер, тесты на PR и main")
        elif not required_checks(repo):
            add("gap", where, "CI есть, но его проверки не обязательны в ruleset main",
                "сначала посмотреть стабильность CI, затем добавить проверки в ruleset (workflow.md, «Проверка»)")
        if not os.path.exists(os.path.join(path, ".github", "CODEOWNERS")):
            add("gap", where, "нет .github/CODEOWNERS", "указать владельца тестов и CI")

    for repo in ALL_REPOS:
        try:
            runs = gh_json("run", "list", "-R", f"{ORG}/{repo}", "-b", default_branch(repo), "-L", "1",
                           "--json", "conclusion,status,workflowName,url")
        except RuntimeError:
            continue
        if runs and runs[0]["status"] == "completed" and runs[0]["conclusion"] not in ("success", "skipped", "neutral"):
            add("block", repo, f"CI на основной ветке: {runs[0]['conclusion']} ({runs[0]['workflowName']})",
                f"починить в первую очередь — {runs[0]['url']}")


def has_upstream(path):
    try:
        run("git", "-C", path, "rev-parse", "--abbrev-ref", "@{upstream}")
        return True
    except RuntimeError:
        return False


def default_branch(repo):
    return gh_json("repo", "view", f"{ORG}/{repo}", "--json", "defaultBranchRef")["defaultBranchRef"]["name"]


def required_checks(repo):
    try:
        rules = gh_json("api", f"repos/{ORG}/{repo}/rules/branches/{default_branch(repo)}")
    except RuntimeError:
        return False
    return any(r.get("type") == "required_status_checks" for r in rules or [])


# ---------- Доска и PR ----------

BOARD_QUERY = """
query($org:String!,$num:Int!,$after:String){organization(login:$org){projectV2(number:$num){
 items(first:100,after:$after){pageInfo{hasNextPage endCursor} nodes{
  fieldValues(first:10){nodes{... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}}}
  content{... on Issue{number state title url updatedAt repository{name} assignees(first:3){nodes{login}}
   issueFieldValues(first:5){nodes{... on IssueFieldSingleSelectValue{name field{... on IssueFieldSingleSelect{name}}}}}}}}}}}}
"""


def board_items():
    items, after = [], None
    while True:
        args = ["api", "graphql", "-f", f"query={BOARD_QUERY}", "-f", f"org={ORG}", "-F", f"num={PROJECT}"]
        if after:
            args += ["-f", f"after={after}"]
        page = gh_json(*args)["data"]["organization"]["projectV2"]["items"]
        for node in page["nodes"]:
            content = node.get("content") or {}
            if content.get("state") != "OPEN":
                continue
            fields = {v["field"]["name"]: v["name"] for v in node["fieldValues"]["nodes"] if v.get("name")}
            issue_fields = {v["field"]["name"]: v["name"] for v in content["issueFieldValues"]["nodes"] if v.get("name")}
            items.append({
                "ref": f"{content['repository']['name']}#{content['number']}",
                "title": content["title"], "url": content["url"], "updated": content["updatedAt"],
                "status": fields.get("Status", ""), "size": fields.get("Size", ""),
                "priority": issue_fields.get("Priority", ""),
                "assignees": [a["login"] for a in content["assignees"]["nodes"]],
            })
        if not page["pageInfo"]["hasNextPage"]:
            return items
        after = page["pageInfo"]["endCursor"]


def check_board():
    items = board_items()
    for it in items:
        missing = [name for name, value in (("Priority", it["priority"]), ("Size", it["size"]), ("Status", it["status"])) if not value]
        if missing:
            add("gap", it["ref"], f"на доске нет полей: {', '.join(missing)} — «{it['title']}»",
                "проставить по workflow.md, раздел «Доска»")
        if it["status"] == "In progress" and days_since(it["updated"]) > STALE_IN_PROGRESS_DAYS:
            add("info", it["ref"], f"In progress без движения {days_since(it['updated'])} дн. — «{it['title']}»",
                "спросить исполнителя или оставить в issue комментарий о состоянии")
        if it["status"] == "In progress" and not it["assignees"]:
            add("gap", it["ref"], "In progress без исполнителя", "назначить или вернуть в Ready")
    return items


def check_off_board(items):
    on_board = {it["ref"] for it in items}
    for repo in ALL_REPOS:
        try:
            issues = gh_json("issue", "list", "-R", f"{ORG}/{repo}", "--state", "open", "--limit", "200", "--json", "number,title")
        except RuntimeError:
            continue
        for issue in issues:
            ref = f"{repo}#{issue['number']}"
            if ref not in on_board:
                add("gap", ref, f"открытая issue не на доске — «{issue['title']}»",
                    "добавить на доску с Status, Size, Priority — или закрыть, если неактуальна")


def check_prs():
    for repo in ALL_REPOS:
        try:
            prs = gh_json("pr", "list", "-R", f"{ORG}/{repo}", "--state", "open", "--json", "number,title,createdAt,url,isDraft")
        except RuntimeError:
            continue
        for pr in prs:
            age = days_since(pr["createdAt"])
            if age > OLD_PR_DAYS and not pr["isDraft"]:
                add("info", f"{repo}#{pr['number']}", f"PR открыт {age} дн. — «{pr['title']}»",
                    "довести: ревью pr-review, исправления, слияние — или закрыть")


# ---------- Проверка проверяющего ----------

def check_review_loop():
    results = os.path.join(HOME, "review", "eval", "results")
    dates = sorted(f[:10] for f in os.listdir(results) if re.match(r"\d{4}-\d{2}-\d{2}", f)) if os.path.isdir(results) else []
    if not dates:
        add("gap", "home/review/eval", "оценка ревьюера ни разу не запускалась", "скилл review-eval")
    elif days_since(dates[-1]) > EVAL_EVERY_DAYS:
        add("gap", "home/review/eval", f"последняя оценка ревьюера {dates[-1]} — больше {EVAL_EVERY_DAYS} дн. назад",
            "скилл review-eval и чистка правил (workflow.md, «Проверка»)")
    since = (TODAY - datetime.timedelta(days=30)).isoformat()
    unstamped = 0
    for repo in ALL_REPOS:
        try:
            prs = gh_json("pr", "list", "-R", f"{ORG}/{repo}", "--state", "merged", "--search", f"merged:>={since}",
                          "--limit", "200", "--json", "body")
        except RuntimeError:
            continue
        unstamped += sum(1 for pr in prs if "Проверено:" not in (pr.get("body") or ""))
    if unstamped:
        add("info", "все репозитории", f"влитых за 30 дн. PR без строки «Проверено:»: {unstamped}",
            "scripts/review-stats.sh — где именно; напомнить о скилле verify")


# ---------- Вывод ----------

def main():
    as_json = "--json" in sys.argv
    sections = [("репозитории", check_repos), ("доска", check_board), ("PR", check_prs), ("проверка", check_review_loop)]
    ready = []
    for name, check in sections:
        try:
            value = check()
            if name == "доска":
                ready = [it for it in value if it["status"] == "Ready" and not it["assignees"]]
                check_off_board(value)
        except Exception as error:  # noqa: BLE001 — одна упавшая секция не должна скрывать остальные
            add("info", name, f"проверка не выполнилась: {error}", "проверь доступ gh (read:project) и сеть")

    order = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3, "": 4}
    ready.sort(key=lambda it: (order.get(it["priority"], 4), it["ref"]))
    if as_json:
        print(json.dumps({"findings": findings, "ready": ready}, ensure_ascii=False, indent=2))
        return

    labels = {"block": "Мешает работе", "gap": "Пробелы", "info": "К сведению"}
    for level in ("block", "gap", "info"):
        group = [f for f in findings if f["level"] == level]
        if group:
            print(f"## {labels[level]} ({len(group)})")
            for f in group:
                print(f"- **{f['where']}** — {f['what']}. → {f['action']}")
            print()
    if not findings:
        print("Пробелов не найдено.\n")
    print(f"## Готово к работе, без исполнителя ({len(ready)})")
    for it in ready[:10]:
        print(f"- [{it['priority'] or '—'} · {it['size'] or '—'}] {it['ref']} — {it['title']}")


if __name__ == "__main__":
    main()
