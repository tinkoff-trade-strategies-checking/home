"""Барьер на `gh pr create` для Claude Code: была ли в сессии проверка (verify или pr-review).

Режим — файл .claude/verify-gate.mode рядом с этим каталогом: off | observe | enforce (нет файла — observe).
observe пишет в .claude/verify-gate.log, что было бы заблокировано; enforce блокирует.
Пропускает: строку «Проверено: нет — <причина>» в команде и третью попытку в сессии после двух блокировок.
Любая ошибка внутри барьера пропускает команду: барьер не должен ломать работу.
"""
import json
import os
import re
import sys
import time

VERIFY_SKILLS = re.compile(r"^(verify|pr-review|code-review)(-claude)?$")
PR_CREATE = re.compile(r"\bgh\s+pr\s+create\b")
WAIVER = re.compile(r"Проверено:\s*нет\s*[—-]\s*\S")


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command", "")
    if not PR_CREATE.search(command):
        return

    claude_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mode_file = os.path.join(claude_dir, "verify-gate.mode")
    mode = "observe"
    if os.path.exists(mode_file):
        mode = open(mode_file, encoding="utf-8").read().strip() or "observe"
    if mode == "off":
        return

    session = data.get("session_id", "")
    verified = used_verify_skill(data.get("transcript_path", ""))
    body = body_file_text(command, data.get("cwd", ""))
    waived = bool(WAIVER.search(command) or WAIVER.search(body))

    log_path = os.path.join(claude_dir, "verify-gate.log")
    blocks_before = count_blocks(log_path, session)
    would_block = not verified and not waived
    decision = "allow"
    if would_block and mode == "enforce" and blocks_before < 2:
        decision = "deny"

    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps({
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session": session,
            "mode": mode,
            "verified": verified,
            "waived": waived,
            "would_block": would_block,
            "decision": decision,
            "cwd": data.get("cwd", ""),
            "command": command[:200],
        }, ensure_ascii=False) + "\n")

    if decision == "deny":
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Барьер проверки: в этой сессии не было скилла verify или pr-review. "
                "Прогони verify-claude (и pr-review-claude) и добавь в описание PR строку «Проверено: …». "
                "Если проверить нельзя — напиши в описании «Проверено: нет — <причина>»."
            ),
        }}, ensure_ascii=False))


def body_file_text(command, cwd):
    match = re.search(r"--body-file[=\s]+(\"[^\"]+\"|'[^']+'|\S+)", command)
    if not match:
        return ""
    path = match.group(1).strip("\"'")
    if not os.path.isabs(path):
        path = os.path.join(cwd or ".", path)
    try:
        return open(path, encoding="utf-8").read()
    except OSError:
        return ""


def used_verify_skill(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return False
    with open(transcript_path, encoding="utf-8", errors="ignore") as transcript:
        for line in transcript:
            if '"Skill"' not in line:
                continue
            for match in re.finditer(r'"name":\s*"Skill",\s*"input":\s*\{\s*"skill":\s*"([^"]+)"', line):
                if VERIFY_SKILLS.match(match.group(1)):
                    return True
    return False


def count_blocks(log_path, session):
    if not session or not os.path.exists(log_path):
        return 0
    count = 0
    with open(log_path, encoding="utf-8", errors="ignore") as log:
        for line in log:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("session") == session and entry.get("decision") == "deny":
                count += 1
    return count


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001 — барьер не должен ронять работу
        pass
