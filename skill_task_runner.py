#!/usr/bin/env python3
"""
skill_task_runner.py
Load skills.md and execute the tasks described in each skill section.

Usage:
  python skill_task_runner.py                               # interactive menu
  python skill_task_runner.py --list                        # list all skills
  python skill_task_runner.py --skill "Python Basics"       # run all tasks in a skill
  python skill_task_runner.py --skill "Python Basics" --task "Hello World"
  python skill_task_runner.py --run-all                     # run every task
  python skill_task_runner.py --file my_skills.md --list    # custom file
"""

import re
import sys
import os
import subprocess
import textwrap
import argparse
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_skills_md(filepath: str) -> dict:
    """
    Parse a skills.md file into a dict:
      {
        "Skill Name": {
          "description": str,
          "tasks": {
            "Task Name": {
              "description": str,
              "language": str,   # "python" | "bash" | ...
              "code": str
            }
          }
        }
      }
    Skill sections start at ## headings; task sections at ### headings.
    Code blocks (```lang ... ```) are extracted per task.
    """
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Stash fenced code blocks so their interior headings are not mis-parsed.
    _stash: list[str] = []

    def _hide(m: re.Match) -> str:
        _stash.append(m.group(0))
        return f"\x00BLOCK{len(_stash) - 1}\x00"

    def _restore(text: str) -> str:
        for i, blk in enumerate(_stash):
            text = text.replace(f"\x00BLOCK{i}\x00", blk)
        return text

    safe = re.sub(r"```.*?```", _hide, content, flags=re.DOTALL)

    skills = {}

    # Split on lines that begin a ## heading (skill boundary)
    skill_chunks = re.split(r"\n(?=##\s)", "\n" + safe)

    for chunk in skill_chunks:
        skill_m = re.match(r"^##\s+(?:Skill:\s*)?(.+)", chunk, re.MULTILINE)
        if not skill_m:
            continue

        skill_name = skill_m.group(1).strip()
        after_skill_heading = chunk[skill_m.end():]

        # Description: text before first ### heading
        desc_m = re.match(r"^(.*?)(?=\n###|\Z)", after_skill_heading, re.DOTALL)
        description = _restore(desc_m.group(1).strip()) if desc_m else ""

        tasks = {}

        # Split on lines that begin a ### heading (task boundary)
        task_chunks = re.split(r"\n(?=###\s)", "\n" + after_skill_heading)
        for tc in task_chunks:
            task_m = re.match(r"^###\s+(?:Task:\s*)?(.+)", tc, re.MULTILINE)
            if not task_m:
                continue

            task_name = task_m.group(1).strip()
            after_task_heading = _restore(tc[task_m.end():])

            # Extract first fenced code block
            code_m = re.search(r"```(\w*)\n(.*?)```", after_task_heading, re.DOTALL)
            if code_m:
                language = code_m.group(1).strip() or "python"
                code = code_m.group(2)
                task_desc = after_task_heading[: code_m.start()].strip()
            else:
                language = None
                code = None
                task_desc = after_task_heading.strip()

            tasks[task_name] = {
                "description": task_desc,
                "language": language,
                "code": code,
            }

        # Only register skills that actually contain tasks
        if tasks:
            skills[skill_name] = {"description": description, "tasks": tasks}

    return skills


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
DIM    = "\033[2m"

def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def c(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if _supports_color() else text


def print_header(title: str) -> None:
    width = 60
    print()
    print(c("=" * width, CYAN))
    print(c(f"  {title}", BOLD))
    print(c("=" * width, CYAN))


def list_skills(skills: dict) -> None:
    print_header("Available Skills")
    for i, (name, data) in enumerate(skills.items(), 1):
        task_count = len(data["tasks"])
        desc = data["description"].replace("\n", " ")
        if len(desc) > 65:
            desc = desc[:62] + "..."
        print(f"\n  {c(str(i) + '.', BOLD)} {c(name, CYAN)}")
        if desc:
            print(f"     {c(desc, DIM)}")
        print(f"     Tasks: {task_count}")
    print()


def list_tasks(skills: dict, skill_name: str) -> None:
    skill_data = skills.get(skill_name)
    if not skill_data:
        print(c(f"\n  Skill '{skill_name}' not found.", RED))
        return
    print_header(f"Tasks — {skill_name}")
    for i, (name, data) in enumerate(skill_data["tasks"].items(), 1):
        lang = data.get("language") or "—"
        desc = data.get("description", "").replace("\n", " ")
        if len(desc) > 65:
            desc = desc[:62] + "..."
        print(f"\n  {c(str(i) + '.', BOLD)} {c(name, CYAN)}  {c('[' + lang + ']', DIM)}")
        if desc:
            print(f"     {c(desc, DIM)}")
    print()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TaskResult:
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.status = "skipped"   # ok | failed | skipped
        self.output = ""
        self.error = ""
        self.elapsed = 0.0


def execute_task(task_name: str, task_data: dict) -> TaskResult:
    result = TaskResult(task_name)
    lang = (task_data.get("language") or "").lower()
    code = task_data.get("code") or ""

    print(f"\n  {c('▶ Running:', BOLD)} {c(task_name, CYAN)}  {c('[' + lang + ']', DIM)}")
    print(c("  " + "-" * 56, DIM))

    if not code.strip():
        print(c("  (no code found — skipping)", YELLOW))
        result.status = "skipped"
        return result

    start = datetime.now()

    if lang in ("python", "python3", "py", ""):
        buf = StringIO()
        try:
            cleaned = textwrap.dedent(code)
            with redirect_stdout(buf):
                exec(cleaned, {"__name__": "__main__"})   # noqa: S102
            result.output = buf.getvalue()
            result.status = "ok"
        except Exception as exc:
            result.output = buf.getvalue()
            result.error = f"{type(exc).__name__}: {exc}"
            result.status = "failed"

        for line in result.output.splitlines():
            print(f"  {line}")
        if result.error:
            print(c(f"\n  ERROR: {result.error}", RED))

    elif lang in ("bash", "sh", "shell"):
        try:
            proc = subprocess.run(
                code, shell=True, capture_output=True, text=True, timeout=30
            )
            result.output = proc.stdout
            result.error = proc.stderr
            result.status = "ok" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            result.error = "Command timed out (30s)"
            result.status = "failed"
        except Exception as exc:
            result.error = str(exc)
            result.status = "failed"

        for line in result.output.splitlines():
            print(f"  {line}")
        if result.error:
            print(c(f"\n  STDERR: {result.error}", YELLOW))
        if result.status == "failed":
            print(c(f"  Exit code indicated failure.", RED))

    else:
        print(c(f"  Unsupported language '{lang}' — skipping.", YELLOW))
        result.status = "skipped"

    result.elapsed = (datetime.now() - start).total_seconds()
    status_str = {"ok": c("OK", GREEN), "failed": c("FAILED", RED),
                  "skipped": c("SKIPPED", YELLOW)}.get(result.status, result.status)
    print(c("  " + "-" * 56, DIM))
    print(f"  {status_str}  {c(f'({result.elapsed:.3f}s)', DIM)}")

    return result


def run_skill(skills: dict, skill_name: str) -> list:
    skill_data = skills.get(skill_name)
    if not skill_data:
        print(c(f"\n  Skill '{skill_name}' not found.", RED))
        return []

    print_header(f"Skill: {skill_name}")
    results = []
    for task_name, task_data in skill_data["tasks"].items():
        results.append(execute_task(task_name, task_data))

    _print_summary(skill_name, results)
    return results


def _print_summary(label: str, results: list) -> None:
    print(f"\n  {c('Summary — ' + label, BOLD)}")
    ok      = sum(1 for r in results if r.status == "ok")
    failed  = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status == "skipped")
    for r in results:
        icon = {"ok": c("✓", GREEN), "failed": c("✗", RED),
                "skipped": c("—", YELLOW)}.get(r.status, "?")
        print(f"    {icon}  {r.task_name}  {c(f'({r.elapsed:.3f}s)', DIM)}")
    total_time = sum(r.elapsed for r in results)
    print(f"\n    {c(str(ok), GREEN)} ok  "
          f"{c(str(failed), RED)} failed  "
          f"{c(str(skipped), YELLOW)} skipped  "
          f"{c(f'({total_time:.3f}s total)', DIM)}")
    print()


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def _pick(prompt: str, names: list) -> str | None:
    """Ask user to pick by number or exact name; return name or None."""
    raw = input(prompt).strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(names):
            return names[idx]
        print(c("  Invalid number.", RED))
        return None
    if raw in names:
        return raw
    print(c(f"  '{raw}' not found.", RED))
    return None


def interactive_mode(skills: dict) -> None:
    skill_names = list(skills.keys())
    print_header("Skill Task Runner — Interactive")

    while True:
        print(f"\n  {c('Menu', BOLD)}")
        print("    1  List skills")
        print("    2  Run all tasks for a skill")
        print("    3  Run one specific task")
        print("    4  Run ALL skills")
        print("    0  Exit")

        choice = input(f"\n  {c('Choice:', BOLD)} ").strip()

        if choice == "0":
            print(c("\n  Goodbye!", GREEN))
            break

        elif choice == "1":
            list_skills(skills)

        elif choice == "2":
            list_skills(skills)
            name = _pick("  Pick skill (name or number): ", skill_names)
            if name:
                run_skill(skills, name)

        elif choice == "3":
            list_skills(skills)
            sname = _pick("  Pick skill (name or number): ", skill_names)
            if not sname:
                continue
            list_tasks(skills, sname)
            task_names = list(skills[sname]["tasks"].keys())
            tname = _pick("  Pick task (name or number): ", task_names)
            if tname:
                execute_task(tname, skills[sname]["tasks"][tname])

        elif choice == "4":
            all_results = []
            for sname in skill_names:
                all_results.extend(run_skill(skills, sname))
            print_header("Grand Summary")
            _print_summary("All Skills", all_results)

        else:
            print(c("  Unknown option — try 0-4.", YELLOW))


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="skill_task_runner.py",
        description="Load skills.md and execute the tasks described in each skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--file", "-f", default="skills.md",
        metavar="PATH",
        help="Path to the skills markdown file (default: skills.md)",
    )
    p.add_argument("--list", "-l", action="store_true", help="List all skills and exit")
    p.add_argument("--list-tasks", action="store_true",
                   help="List tasks for --skill and exit (no execution)")
    p.add_argument("--skill", "-s", metavar="NAME", help="Skill to run (or inspect)")
    p.add_argument("--task", "-t", metavar="NAME",
                   help="Specific task to run (requires --skill)")
    p.add_argument("--run-all", action="store_true", help="Run every skill and task")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Resolve file path
    md_path = args.file
    if not os.path.isabs(md_path):
        md_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), md_path)

    if not os.path.exists(md_path):
        print(c(f"Error: '{md_path}' not found.", RED))
        print("  Create skills.md next to this script, or pass --file <path>.")
        sys.exit(1)

    print(c(f"Loading: {md_path}", DIM))
    skills = parse_skills_md(md_path)

    if not skills:
        print(c("No skills parsed. Check the file format.", RED))
        sys.exit(1)

    total_tasks = sum(len(s["tasks"]) for s in skills.values())
    print(c(f"Loaded {len(skills)} skill(s), {total_tasks} task(s).", DIM))

    # --list
    if args.list:
        list_skills(skills)
        return

    # --run-all
    if args.run_all:
        all_results = []
        for name in skills:
            all_results.extend(run_skill(skills, name))
        print_header("Grand Summary")
        _print_summary("All Skills", all_results)
        return

    # --skill + --task
    if args.skill and args.task:
        if args.skill not in skills:
            print(c(f"Skill '{args.skill}' not found.", RED))
            sys.exit(1)
        if args.task not in skills[args.skill]["tasks"]:
            print(c(f"Task '{args.task}' not found in skill '{args.skill}'.", RED))
            sys.exit(1)
        execute_task(args.task, skills[args.skill]["tasks"][args.task])
        return

    # --skill (optionally with --list-tasks)
    if args.skill:
        if args.skill not in skills:
            print(c(f"Skill '{args.skill}' not found.", RED))
            sys.exit(1)
        if args.list_tasks:
            list_tasks(skills, args.skill)
        else:
            run_skill(skills, args.skill)
        return

    # No flags → interactive
    interactive_mode(skills)


if __name__ == "__main__":
    main()
