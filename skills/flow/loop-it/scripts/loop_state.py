#!/usr/bin/env python3
"""Order and checkpoint a /loop-it issue batch.

Dependency parsing, cycle breaking, topological ordering, the "next actionable
issue" decision and the resume merge are deterministic. Deriving them in prose
on every run is slower and less reliable, so they live here: the skill runs a
subcommand and reads the printed summary.

Subcommands (all accept `--state <path>`, default `.loop-state.json`):

  scan [--issues <path>] [--repo owner/name]
      Read `gh issue list --state open --json number,title,labels,body` output
      from a file or stdin, parse dependency edges, break cycles by lowest
      issue number, topologically order the batch, merge into the existing
      checkpoint (a recorded status is never lost; a corrupt checkpoint is a
      hard error and is never overwritten), write the checkpoint, and print the
      order, the next actionable issue and the blocked/skipped ones.

  set --issue N --status <pending|in_progress|shipped|failed|skipped|blocked>
      [--error-class X] [--error TEXT] [--branch B] [--phase P]
      Record one transition, stamp times, increment `attempts` when an attempt
      starts, write the checkpoint, and print what to do next. Marking an issue
      `shipped` warns when it still has no `decisions` / `verification` / `open`
      recorded, and when it has no structured `evidence` — a shipped row without
      them says a thing happened, not what proved it.

  note --issue N [--progress TEXT] [--decisions TEXT] [--verification TEXT]
       [--open TEXT]
      Record the four things a checkpoint must not lose, appended verbatim
      rather than summarized: what happened, what was decided and why, what was
      run and what it proved, and what is still open. These are what make a
      finished batch auditable months later.

  evidence add --issue N --kind <test|runtime|database|external|human>
               --command TEXT --result <pass|fail|deferred>
               [--artifact PATH] [--observed-at TIME]
  evidence list --issue N
      The structured half of verification: one observation per acceptance
      criterion, appended and never rewritten. `note --verification` says what a
      run proved as a whole; this says which observation backs which claim, with
      the command that produced it, so a reader can re-run it. `--observed-at`
      defaults to now.

  followup add --from-issue N --title TEXT [--why TEXT] [--evidence TEXT]
  followup list [--all]
  followup resolve --id ID --status <promoted|dropped> [--issue N] [--why TEXT]
      The campaign's own task queue. A supervisor verdict of `follow-up` means
      the issue passes but something new must not be lost: it is recorded here,
      versioned with the checkpoint and printed by `summary`, never left in the
      conversation. `promoted` records the issue number it became, and the next
      `scan` picks that issue up — which is how a batch extends itself.

  next
      Print the next actionable issue (all deps shipped) and why the others
      are waiting.

  summary
      Print the progress table.

Checkpoint schema — unchanged from the heredoc-era skill so an old file
resumes:

  {
    "version": 1, "started_at": ..., "updated_at": ..., "repo": "owner/repo",
    "total_issues": N,
    "followups": [{"id": "f1", "from_issue": 7, "title": ..., "why": ...,
                   "evidence": ..., "created_at": ..., "status": "open"}],
    "issues": {"3": {"status": ..., "branch": ..., "phase": ...,
                     "error_class": ..., "attempts": 0, "started_at": ...,
                     "updated_at": ..., "completed_at": ..., "last_error": ...
                     "title": ..., "deps": [1, 5],
                     "notes": {"decisions": [{"at": ..., "text": ...}], ...},
                     "evidence": [{"kind": "test", "command": ...,
                                   "result": "pass", "artifact": ...,
                                   "observed_at": ...}]}}
  }

`title` and `deps` are additive per-issue fields written by `scan` so `next`
and `summary` can explain what is waiting without re-reading GitHub. `notes`,
`evidence` and `followups` are additive too — written by the `note`, `evidence`
and `followup` subcommands, absent until something is recorded, and preserved
verbatim by a re-`scan`. An old file that lacks any of them still resumes; it
only loses titles, waiting reasons, notes, evidence and follow-ups until the
next write.

Ordering: repeatedly take the lowest-numbered issue whose in-batch deps are all
placed (lexicographically smallest topological order). When that stalls, the
remaining nodes form a cycle: the lowest-numbered one has its dependency edges
ignored, with a warning naming the cycle.

Readiness: a dependency is satisfied only when its status is `shipped`. A dep
that is `skipped`, `failed`, `blocked` or `in_progress`, or that is not tracked
at all (the issue is no longer open), leaves the dependent waiting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STATUSES = ("pending", "in_progress", "shipped", "failed", "skipped", "blocked")
DONE = ("shipped", "skipped")
RUNNABLE = ("pending", "in_progress")
DEFAULT_STATE = ".loop-state.json"

# The four things a checkpoint must not lose, kept verbatim rather than summarized. They are
# why a finished batch can still be audited months later: a status says a thing shipped, not
# what was decided, what proved it, or what was left open. `progress` is not enforced because
# the status and timestamps already carry it; the other three are, because a `shipped` row
# without them is an assertion with no trail.
NOTE_CATEGORIES = ("progress", "decisions", "verification", "open")
REQUIRED_NOTES = ("decisions", "verification", "open")

# The structured half of verification: what was actually observed, with the command that
# produced it. `kind` is the nature of the observation, not its strength — which kinds gate
# which status is the workspace's call, not this script's. `result` is deliberately
# three-valued: `deferred` is the honest answer for a check that was skipped, and it must
# never be able to masquerade as `pass`.
EVIDENCE_KINDS = ("test", "runtime", "database", "external", "human")
EVIDENCE_RESULTS = ("pass", "fail", "deferred")

# A follow-up is a task, not a note: it has a lifecycle and can be promoted into a real
# issue, which is how a batch grows while it runs instead of being frozen at plan time.
# `open` is the only non-terminal state, so only the two resolutions are ever passed in.
FOLLOWUP_OPEN = "open"
FOLLOWUP_RESOLUTIONS = ("promoted", "dropped")

DEP_TRIGGER = re.compile(r"(?:dependencies|depends\s+on|requires)\s*:?", re.IGNORECASE)
REF = re.compile(r"#(\d+)")
SEP = re.compile(r"[ \t]*(?:,|;|\band\b|、)?[ \t]*", re.IGNORECASE)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def die(message: str) -> None:
    print(f"loop_state: {message}", file=sys.stderr)
    raise SystemExit(1)


def ref(number: int) -> str:
    return f"#{number}"


# --------------------------------------------------------------------------
# dependency parsing
# --------------------------------------------------------------------------

def parse_deps(body: str, number: int | None = None) -> list[int]:
    """Parse dependency edges from one issue body.

    Supported forms: `Dependencies: #3, #5`, `Depends on: #3`, `depends on #3`,
    `requires #3`, plus `and`-joined lists. Refs after the first non-reference
    token are not treated as dependencies.
    """
    deps: set[int] = set()
    if not body:
        return []
    for trigger in DEP_TRIGGER.finditer(body):
        pos = trigger.end()
        while pos <= len(body):
            match = REF.match(body, pos)
            if match is None:
                sep = SEP.match(body, pos)
                if sep is None or sep.end() == pos:
                    break
                pos = sep.end()
                match = REF.match(body, pos)
                if match is None:
                    break
            deps.add(int(match.group(1)))
            pos = match.end()
    if number is not None:
        deps.discard(number)
    return sorted(deps)


# --------------------------------------------------------------------------
# graph
# --------------------------------------------------------------------------

def cycle_path(start: int, deps: dict[int, set[int]], remaining: set[int]) -> list[int]:
    """Walk lowest-numbered edges from `start` until a node repeats."""
    path: list[int] = []
    seen: dict[int, int] = {}
    node = start
    while node not in seen and node in remaining:
        seen[node] = len(path)
        path.append(node)
        following = sorted(d for d in deps.get(node, set()) if d in remaining)
        if not following:
            return []
        node = following[0]
    if node in seen:
        return path[seen[node]:] + [node]
    return []


def topology(numbers: list[int], deps: dict[int, set[int]]) -> tuple[list[int], list[str]]:
    """Lexicographically smallest topological order, breaking cycles by number."""
    remaining = set(numbers)
    edges = {n: {d for d in deps.get(n, set()) if d != n} for n in numbers}
    order: list[int] = []
    warnings: list[str] = []
    while remaining:
        ready = sorted(n for n in remaining if not (edges[n] & remaining))
        if not ready:
            victim = min(remaining)
            blockers = sorted(edges[victim] & remaining)
            cycle = cycle_path(victim, edges, remaining)
            chain = " → ".join(ref(n) for n in cycle) if cycle else ref(victim)
            dropped = ", ".join(ref(b) for b in blockers) or "(none)"
            warnings.append(
                f"⚠️ 循环依赖检测到: {chain}，按编号顺序打破（忽略 {ref(victim)} 的依赖 {dropped}）"
            )
            edges[victim] = set()
            ready = [victim]
        pick = ready[0]
        order.append(pick)
        remaining.discard(pick)
    return order, warnings


def state_edges(state: dict) -> tuple[list[int], dict[int, set[int]]]:
    numbers = sorted(int(key) for key in state.get("issues", {}))
    deps: dict[int, set[int]] = {}
    for number in numbers:
        raw = state["issues"][str(number)].get("deps") or []
        edges: set[int] = set()
        for dep in raw:
            try:
                edges.add(int(dep))
            except (TypeError, ValueError):
                continue
        deps[number] = edges
    return numbers, deps


def order_of(state: dict) -> list[int]:
    numbers, deps = state_edges(state)
    order, _ = topology(numbers, deps)
    return order


def waiting_on(state: dict, number: int) -> list[str]:
    """Human-readable list of the unsatisfied dependencies of `number`."""
    entry = state["issues"].get(str(number)) or {}
    reasons: list[str] = []
    for dep in entry.get("deps") or []:
        try:
            dep = int(dep)
        except (TypeError, ValueError):
            continue
        other = state["issues"].get(str(dep))
        if other is None:
            reasons.append(f"{ref(dep)}(不在本批)")
        elif other.get("status") != "shipped":
            reasons.append(f"{ref(dep)}({other.get('status')})")
    return reasons


def next_actionable(state: dict) -> int | None:
    for number in order_of(state):
        if state["issues"][str(number)].get("status") not in RUNNABLE:
            continue
        if waiting_on(state, number):
            continue
        return number
    return None


# --------------------------------------------------------------------------
# checkpoint
# --------------------------------------------------------------------------

def blank_issue(title: str = "", deps: list[int] | None = None) -> dict:
    entry: dict = {"status": "pending"}
    if title:
        entry["title"] = title
    if deps:
        entry["deps"] = list(deps)
    return entry


def load_state(path: str, required: bool = False) -> dict | None:
    if not os.path.exists(path):
        if required:
            die(f"checkpoint not found: {path} — run the `scan` subcommand first")
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        die(f"checkpoint {path} is corrupt (invalid JSON: {exc}) — fix or delete it; refusing to overwrite")
    except OSError as exc:
        die(f"checkpoint {path} cannot be read: {exc}")
    if not isinstance(raw, dict):
        die(f"checkpoint {path} is corrupt (top level is not an object) — fix or delete it; refusing to overwrite")
    issues = raw.get("issues")
    if not isinstance(issues, dict):
        die(f"checkpoint {path} is corrupt (no `issues` object) — fix or delete it; refusing to overwrite")
    for key, entry in issues.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("status"), str):
            die(f"checkpoint {path} is corrupt (issue {key} has no status) — fix or delete it; refusing to overwrite")
    if raw.get("version") != 1:
        print(f"⚠️  checkpoint version is {raw.get('version')!r}, expected 1 — continuing", file=sys.stderr)
    return raw


def save_state(state: dict, path: str) -> None:
    state["updated_at"] = now()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def detect_repo() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    match = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", result.stdout.strip())
    return match.group(1) if match else ""


def read_issues(path: str | None) -> list:
    try:
        if not path or path == "-":
            text = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
    except OSError as exc:
        die(f"cannot read issues from {path}: {exc}")
    if not text.strip():
        die("no issue JSON given — expected `gh issue list --state open --json number,title,labels,body` output")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        die(f"issue JSON is invalid: {exc}")
    if isinstance(data, dict) and isinstance(data.get("issues"), list):
        data = data["issues"]
    if not isinstance(data, list):
        die("issue JSON must be a list of issue objects")
    return data


def normalize_issue(item: dict) -> tuple[int, str, str, list[str]]:
    if not isinstance(item, dict):
        die(f"issue entry is not an object: {item!r}")
    try:
        number = int(item.get("number"))
    except (TypeError, ValueError):
        die(f"issue without a usable number: {item!r}")
    title = str(item.get("title") or "").strip() or f"issue #{number}"
    body = item.get("body") or ""
    labels: list[str] = []
    for label in item.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            labels.append(str(name))
    return number, title, body, labels


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def dep_note(deps: list[int]) -> str:
    if not deps:
        return "无依赖"
    return "依赖 " + ", ".join(ref(d) for d in deps)


def title_of(state: dict, number: int) -> str:
    return state["issues"].get(str(number), {}).get("title") or ""


def render_order(state: dict, numbers: list[int]) -> str:
    lines = []
    for number in numbers:
        entry = state["issues"][str(number)]
        status = entry.get("status", "pending")
        suffix = "" if status == "pending" else f" [{status}]"
        lines.append(f"  {ref(number)}: {title_of(state, number)} ({dep_note(entry.get('deps') or [])}){suffix}")
    return "\n".join(lines)


def render_next(state: dict) -> str:
    number = next_actionable(state)
    if number is None:
        lines = ["📊 next: (无可执行项)"]
    else:
        entry = state["issues"][str(number)]
        hint = "（恢复 in_progress）" if entry.get("status") == "in_progress" else ""
        lines = [f"📊 next: {ref(number)} {title_of(state, number)}{hint}"]
    waiting = []
    for candidate in order_of(state):
        entry = state["issues"][str(candidate)]
        status = entry.get("status", "pending")
        if status in DONE or candidate == number:
            continue
        if status == "failed":
            detail = entry.get("error_class") or "unknown"
            waiting.append(f"  - {ref(candidate)}: 上次失败（{detail}，{entry.get('attempts', 0)} attempts）— 需决定重试或跳过")
        elif status == "blocked":
            reasons = waiting_on(state, candidate)
            waiting.append(f"  - {ref(candidate)}: 已标记 blocked"
                           + (f"（等待 {', '.join(reasons)}）" if reasons else ""))
        else:
            reasons = waiting_on(state, candidate)
            if reasons:
                waiting.append(f"  - {ref(candidate)}: 等待 {', '.join(reasons)}")
            elif number is not None:
                waiting.append(f"  - {ref(candidate)}: 依赖就绪，排在 {ref(number)} 之后")
    if waiting:
        lines.append("🚧 waiting:")
        lines.extend(waiting)
    return "\n".join(lines)


def render_summary(state: dict) -> str:
    issues = state["issues"]
    order = order_of(state)
    buckets: dict[str, list[int]] = {status: [] for status in STATUSES}
    for number in order:
        status = issues[str(number)].get("status", "pending")
        buckets.setdefault(status, []).append(number)
    total = len(order)
    done = len(buckets.get("shipped", [])) + len(buckets.get("skipped", []))
    percent = int(done * 100 / total) if total else 0
    lines = [
        "━" * 52,
        f"📊 loop-it: {done}/{total} done ({percent}%)  repo={state.get('repo') or '?'}  "
        f"tracked={state.get('total_issues', total)}",
        "━" * 52,
        f"  ✅ shipped:    {len(buckets.get('shipped', []))}  "
        + ", ".join(ref(n) for n in buckets.get("shipped", [])),
        f"  ⏭️  skipped:    {len(buckets.get('skipped', []))}  "
        + ", ".join(ref(n) for n in buckets.get("skipped", [])),
    ]
    blocked = [n for n in buckets.get("blocked", [])] + [
        n for n in buckets.get("pending", []) if waiting_on(state, n)
    ]
    lines.append(f"  🔒 blocked:    {len(blocked)}  " + ", ".join(
        f"{ref(n)}({', '.join(waiting_on(state, n)) or 'blocked'})" for n in blocked))
    failed = buckets.get("failed", [])
    lines.append(f"  ❌ failed:     {len(failed)}  " + ", ".join(
        f"{ref(n)}({issues[str(n)].get('error_class') or 'unknown'}, "
        f"{issues[str(n)].get('attempts', 0)} attempts"
        + (f", {issues[str(n)].get('last_error')}" if issues[str(n)].get("last_error") else "")
        + ")" for n in failed))
    lines.append(f"  ⏳ in_progress: {len(buckets.get('in_progress', []))}  "
                 + ", ".join(ref(n) for n in buckets.get("in_progress", [])))
    remaining = [n for n in buckets.get("pending", []) if not waiting_on(state, n)]
    lines.append(f"  📋 remaining:  {len(remaining)}  "
                 + ", ".join(ref(n) for n in remaining))
    pending = open_followups(state)
    lines.append(f"  🔀 follow-ups: {len(pending)} open  "
                 + ", ".join(f"{item['id']}({clip(item.get('title'))})" for item in pending))
    no_evidence = [n for n in buckets.get("shipped", []) if missing_evidence(issues[str(n)])]
    if no_evidence:
        lines.append(f"  ⚠️  shipped w/o evidence: {len(no_evidence)}  "
                     + ", ".join(ref(n) for n in no_evidence))
    lines.append("━" * 52)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    raw = read_issues(args.issues)
    existing = load_state(args.state)

    fetched: dict[int, dict] = {}
    warnings: list[str] = []
    for item in raw:
        number, title, body, labels = normalize_issue(item)
        if number in fetched:
            warnings.append(f"⚠️  issue {ref(number)} appears more than once in the input; keeping the last one")
        deps = parse_deps(body, number)
        if number in parse_deps(body):
            warnings.append(f"⚠️  {ref(number)} depends on itself; edge dropped")
        fetched[number] = {"title": title, "deps": deps, "labels": labels}

    if not fetched:
        print("✅ No open issues found. Nothing to do.")
        if existing is not None:
            print(render_summary(existing))
        return 0

    state = existing if existing is not None else {
        "version": 1,
        "started_at": now(),
        "updated_at": now(),
        "repo": "",
        "total_issues": 0,
        "issues": {},
    }
    state.setdefault("version", 1)
    state.setdefault("started_at", now())
    issues = state.setdefault("issues", {})
    for number in sorted(fetched):
        entry = issues.setdefault(str(number), blank_issue())
        entry["title"] = fetched[number]["title"]
        entry["deps"] = fetched[number]["deps"]
        entry.setdefault("status", "pending")
    state["total_issues"] = len(issues)
    recorded_repo = state.get("repo")
    repo = args.repo or recorded_repo or detect_repo()
    state["repo"] = repo
    if recorded_repo and repo and recorded_repo != repo:
        warnings.append(
            f"⚠️  状态文件记录的 repo 是 {recorded_repo}，当前是 {repo}；"
            f"若这不是同一批工作，删除 {args.state} 后重跑 scan"
        )

    for number in sorted(fetched):
        for dep in fetched[number]["deps"]:
            if str(dep) not in issues:
                warnings.append(
                    f"⚠️  {ref(number)} 依赖 {ref(dep)}，但 {ref(dep)} 不在本批 open issue 中："
                    f"按未 shipped 处理（可用 `set --issue {dep} --status shipped` 手工补记）"
                )

    save_state(state, args.state)

    order = order_of(state)
    batch_order = [n for n in order if n in fetched]
    print(f"📋 Found {len(fetched)} open issue(s) (topological sort):")
    print(render_order(state, batch_order))
    _, topo_warnings = topology(*state_edges(state))
    for warning in topo_warnings + warnings:
        print(warning)
    print()
    print(render_next(state))
    blocked = [n for n in order if issues[str(n)].get("status") == "blocked"
               or (issues[str(n)].get("status") not in DONE and waiting_on(state, n))]
    skipped = [n for n in order if issues[str(n)].get("status") == "skipped"]
    failed = [n for n in order if issues[str(n)].get("status") == "failed"]
    if blocked:
        print("🔒 blocked: " + ", ".join(
            f"{ref(n)}({', '.join(waiting_on(state, n)) or 'blocked'})" for n in blocked))
    if skipped:
        print("⏭️  skipped: " + ", ".join(ref(n) for n in skipped))
    if failed:
        print("❌ failed:  " + ", ".join(
            f"{ref(n)}({issues[str(n)].get('error_class') or 'unknown'})" for n in failed))
    print(f"\ncheckpoint: {args.state}  (add it to .gitignore, then commit that rule)")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    issues = state["issues"]
    entry = require_issue(state, args.issue, args.state)
    previous = entry.get("status", "pending")
    stamp = now()

    if args.status == "in_progress":
        entry["attempts"] = int(entry.get("attempts", 0)) + 1
        entry.setdefault("started_at", stamp)
    entry["status"] = args.status
    if args.branch:
        entry["branch"] = args.branch
    if args.phase:
        entry["phase"] = args.phase
    elif args.status == "in_progress" and not entry.get("phase"):
        entry["phase"] = "implement"
    if args.error_class:
        entry["error_class"] = args.error_class
    if args.error:
        entry["last_error"] = args.error
    if args.status in DONE:
        entry["completed_at"] = stamp
        entry.pop("error_class", None)
        entry.pop("last_error", None)
    else:
        entry.pop("completed_at", None)
    entry["updated_at"] = stamp
    save_state(state, args.state)

    detail = f" (attempts {entry.get('attempts', 0)})" if args.status == "in_progress" else ""
    print(f"{ref(args.issue)}: {previous} -> {args.status}{detail}")
    if args.status == "shipped":
        missing = missing_notes(entry)
        if missing:
            print(
                f"  ! no {', '.join(missing)} recorded for {ref(args.issue)} — a shipped row "
                f"without them says a thing happened, not what proved it. Record it with "
                f"`note --issue {args.issue} …`.",
                file=sys.stderr,
            )
        if missing_evidence(entry):
            print(
                f"  ! no evidence recorded for {ref(args.issue)} — a shipped row with no "
                f"observation behind it cannot be audited later. Record one with "
                f"`evidence add --issue {args.issue} --kind <test|runtime|database|external|"
                f"human> --command '…' --result <pass|fail|deferred>`.",
                file=sys.stderr,
            )
    print(render_next(state))
    if not any(issues[str(n)].get("status") not in DONE for n in order_of(state)):
        print("\n🎉 全部 issue 处理完毕 — 现在做批末收尾：/review-it 审整批 diff，然后 /ship-it 一次 PR。")
        pending = open_followups(state)
        if pending:
            print(
                f"   还有 {len(pending)} 条 follow-up 没处理（`followup list`）：promote 成新 issue "
                f"再跑一轮，或明确 drop——别让它们只留在会话里。"
            )
    return 0


def cmd_next(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    print(render_next(state))
    return 0


def missing_notes(entry: dict) -> list[str]:
    """Which required category this issue has nothing recorded for."""
    notes = entry.get("notes") or {}
    return [category for category in REQUIRED_NOTES if not notes.get(category)]


def missing_evidence(entry: dict) -> bool:
    """True when a shipped issue has no structured observation behind it."""
    return not entry.get("evidence")


def require_issue(state: dict, number: int, path: str) -> dict:
    """The tracked entry for `number`, or a hard stop explaining how to get one."""
    key = str(number)
    if key not in state["issues"]:
        die(f"{ref(number)} is not tracked in {path} — run the `scan` subcommand first")
    return state["issues"][key]


def open_followups(state: dict) -> list[dict]:
    return [item for item in state.get("followups") or [] if item.get("status") == "open"]


def next_followup_id(state: dict) -> str:
    """Monotonic `f<n>` ids, so a resolved one is never reused by a later follow-up."""
    highest = 0
    for item in state.get("followups") or []:
        match = re.fullmatch(r"f(\d+)", str(item.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"f{highest + 1}"


def clip(text: str, width: int = 48) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def cmd_evidence(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    entry = require_issue(state, args.issue, args.state)

    if args.action == "list":
        records = entry.get("evidence") or []
        if not records:
            print(f"{ref(args.issue)}: no evidence recorded")
            return 0
        print(f"{ref(args.issue)}: {len(records)} evidence record(s)")
        for record in records:
            artifact = f"   artifact={record['artifact']}" if record.get("artifact") else ""
            print(f"  [{record.get('kind')}] {record.get('result')}  {record.get('observed_at')}{artifact}")
            print(f"    $ {record.get('command')}")
        return 0

    record = {
        "kind": args.kind,
        "command": args.command,
        "result": args.result,
        "observed_at": args.observed_at or now(),
    }
    if args.artifact:
        record["artifact"] = args.artifact
    # Append, never rewrite. An observation that later turns out to be wrong is itself part
    # of the trail; overwriting it is exactly the loss this record exists to prevent.
    entry.setdefault("evidence", []).append(record)
    entry["updated_at"] = now()
    save_state(state, args.state)
    print(
        f"{ref(args.issue)}: recorded {args.kind}/{args.result} evidence "
        f"({len(entry['evidence'])} total)"
    )
    return 0


def cmd_followup(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    followups = state.setdefault("followups", [])

    if args.action == "add":
        require_issue(state, args.from_issue, args.state)
        item = {
            "id": next_followup_id(state),
            "from_issue": args.from_issue,
            "title": args.title,
            "created_at": now(),
            "status": "open",
        }
        if args.why:
            item["why"] = args.why
        if args.evidence:
            item["evidence"] = args.evidence
        followups.append(item)
        save_state(state, args.state)
        print(f"🔀 {item['id']}: follow-up from {ref(args.from_issue)} — {args.title}")
        print(
            f"  {len(open_followups(state))} open; `summary` lists them, "
            f"`followup resolve --id {item['id']} --status promoted --issue N` closes one."
        )
        return 0

    if args.action == "list":
        if not followups:
            print("🔀 no follow-ups recorded")
            return 0
        pending = open_followups(state)
        print(f"🔀 follow-ups: {len(pending)} open, {len(followups) - len(pending)} resolved")
        for item in pending:
            print(f"  {item['id']}  (from {ref(item.get('from_issue', 0))})  {item.get('title')}")
            if item.get("why"):
                print(f"      why: {item['why']}")
            if item.get("evidence"):
                print(f"      evidence: {item['evidence']}")
        if args.all:
            for item in followups:
                if item.get("status") == "open":
                    continue
                target = f" → {ref(item['promoted_to'])}" if item.get("promoted_to") else ""
                print(f"  {item['id']}  [{item.get('status')}{target}]  {item.get('title')}")
        return 0

    item = next((candidate for candidate in followups if candidate.get("id") == args.id), None)
    if item is None:
        die(f"no follow-up {args.id!r} in {args.state} — see `followup list`")
    if item.get("status") != "open":
        die(f"{args.id} is already {item.get('status')}; a resolved follow-up is not reopened")
    if args.status == "promoted" and not args.issue:
        die("--status promoted needs --issue N — the issue this follow-up became")
    item["status"] = args.status
    item["resolved_at"] = now()
    if args.issue:
        item["promoted_to"] = args.issue
    if args.why:
        item["resolution"] = args.why
    save_state(state, args.state)
    target = f" → {ref(args.issue)}" if args.issue else ""
    print(f"🔀 {args.id}: open → {args.status}{target}  {item.get('title')}")
    if args.status == "promoted":
        print("  re-run `scan` to pull the new issue into the batch.")
    return 0


def cmd_note(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    entry = require_issue(state, args.issue, args.state)
    notes = entry.setdefault("notes", {})
    stamp = now()

    written = []
    for category in NOTE_CATEGORIES:
        text = getattr(args, category)
        if not text:
            continue
        # Append rather than replace: a decision taken early is exactly what a later step
        # tends to overwrite, and losing it is the failure this field exists to prevent.
        notes.setdefault(category, []).append({"at": stamp, "text": text})
        written.append(category)

    if not written:
        die("nothing to record — pass at least one of "
            + ", ".join(f"--{category}" for category in NOTE_CATEGORIES))
    entry["updated_at"] = stamp
    save_state(state, args.state)
    print(f"{ref(args.issue)}: recorded {', '.join(written)}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    print(render_summary(state))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="parse deps, order the batch, write the checkpoint")
    scan.add_argument("--issues", help="path to `gh issue list --json ...` output (default: stdin)")
    scan.add_argument("--repo", help="owner/name to record (default: keep, else git origin)")
    scan.add_argument("--state", default=DEFAULT_STATE)
    scan.set_defaults(func=cmd_scan)

    setter = sub.add_parser("set", help="record one issue transition")
    setter.add_argument("--issue", type=int, required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--error-class", dest="error_class")
    setter.add_argument("--error")
    setter.add_argument("--branch")
    setter.add_argument("--phase")
    setter.add_argument("--state", default=DEFAULT_STATE)
    setter.set_defaults(func=cmd_set)

    nxt = sub.add_parser("next", help="print the next actionable issue")
    nxt.add_argument("--state", default=DEFAULT_STATE)
    nxt.set_defaults(func=cmd_next)

    note = sub.add_parser("note", help="record the four things the checkpoint must not lose")
    note.add_argument("--issue", type=int, required=True)
    note.add_argument("--progress", help="what happened")
    note.add_argument("--decisions", help="what was decided, and why")
    note.add_argument("--verification", help="what was run, and what it proved")
    note.add_argument("--open", help="what is still open")
    note.add_argument("--state", default=DEFAULT_STATE)
    note.set_defaults(func=cmd_note)

    evidence = sub.add_parser("evidence", help="record or list structured verification evidence")
    evidence_sub = evidence.add_subparsers(dest="action", required=True)
    evidence_add = evidence_sub.add_parser("add", help="append one observation")
    evidence_add.add_argument("--issue", type=int, required=True)
    evidence_add.add_argument("--kind", required=True, choices=EVIDENCE_KINDS)
    evidence_add.add_argument("--command", required=True, help="the command that produced it")
    evidence_add.add_argument("--result", required=True, choices=EVIDENCE_RESULTS)
    evidence_add.add_argument("--artifact", help="path to the output worth keeping")
    evidence_add.add_argument("--observed-at", help="when it was observed (default: now)")
    evidence_add.add_argument("--state", default=DEFAULT_STATE)
    evidence_add.set_defaults(func=cmd_evidence)
    evidence_list = evidence_sub.add_parser("list", help="print one issue's observations")
    evidence_list.add_argument("--issue", type=int, required=True)
    evidence_list.add_argument("--state", default=DEFAULT_STATE)
    evidence_list.set_defaults(func=cmd_evidence)

    followup = sub.add_parser("followup", help="record, list or resolve follow-up tasks")
    followup_sub = followup.add_subparsers(dest="action", required=True)
    followup_add = followup_sub.add_parser("add", help="record what the supervisor found")
    followup_add.add_argument("--from-issue", type=int, required=True)
    followup_add.add_argument("--title", required=True)
    followup_add.add_argument("--why", help="what was observed, and why it is not this issue's job")
    followup_add.add_argument("--evidence", help="the evidence that made it visible")
    followup_add.add_argument("--state", default=DEFAULT_STATE)
    followup_add.set_defaults(func=cmd_followup)
    followup_list = followup_sub.add_parser("list", help="print open follow-ups")
    followup_list.add_argument("--all", action="store_true", help="also show resolved ones")
    followup_list.add_argument("--state", default=DEFAULT_STATE)
    followup_list.set_defaults(func=cmd_followup)
    followup_resolve = followup_sub.add_parser("resolve", help="close one follow-up")
    followup_resolve.add_argument("--id", required=True)
    followup_resolve.add_argument("--status", required=True, choices=FOLLOWUP_RESOLUTIONS)
    followup_resolve.add_argument("--issue", type=int, help="the issue it became (required for promoted)")
    followup_resolve.add_argument("--why", help="why it was dropped, or what changed")
    followup_resolve.add_argument("--state", default=DEFAULT_STATE)
    followup_resolve.set_defaults(func=cmd_followup)

    summary = sub.add_parser("summary", help="print the progress table")
    summary.add_argument("--state", default=DEFAULT_STATE)
    summary.set_defaults(func=cmd_summary)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
