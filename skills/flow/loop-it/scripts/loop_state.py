#!/usr/bin/env python3
"""为 /loop-it 的 issue 批次排序并做检查点。

依赖解析、破环、拓扑排序、"下一个可执行 issue"的判定以及恢复时的合并都是确定性的。
每次运行都用散文重新推导既慢又不可靠，所以它们放在这里：技能跑一个子命令，读打印出来的
摘要。

子命令（都接受 `--state <path>`，默认 `.loop-state.json`）：

  scan [--issues <path>] [--repo owner/name]
      从文件或 stdin 读取 `gh issue list --state open --json number,title,labels,body`
      的输出，解析依赖边，按最小 issue 编号破环，对这批 issue 做拓扑排序，合并进已有的
      检查点（已记录的状态永不丢失；损坏的检查点是硬错误，永不覆盖），写入检查点，并
      打印顺序、下一个可执行 issue 以及被阻塞/跳过的那些。

  set --issue N --status <pending|in_progress|shipped|failed|skipped|blocked>
      [--error-class X] [--error TEXT] [--branch B] [--phase P] [--waive TEXT]
      记录一次状态转移，打上时间戳，在一次尝试开始时递增 `attempts`，写入检查点，并打印
      下一步该做什么。把 issue 标成 `shipped` 时，若一条 `evidence` 都没有，这次转移会被拒绝——
      背后没有观察的 shipped 记录只说明有事发生过。证据要标层次（`--layer L1..L4`）：只到 L1/L2
      时照样能 shipped，但会打一条告警，因为真实链路（L3）还没验过。
      拿不到观察时可以用 `--waive "原因"` 把原因写进检查点——那是自愿声明，不是豁免
      （已经没有闸门可豁免了），`summary` 里会标出来。
      仍缺 `decisions` / `verification` / `open` 时只告警，不拦——那是判断，不是可核验的事实。

  note --issue N [--progress TEXT] [--decisions TEXT] [--verification TEXT]
       [--open TEXT]
      记录检查点绝不能丢的四件事，逐字追加而非概括：发生了什么、决定了什么以及为什么、
      跑了什么以及它证明了什么、还有什么没结。正是这些让一批做完的工作几个月后仍可审计。

  evidence add --issue N --kind <test|runtime|database|external|human>
               --command TEXT --result <pass|fail|deferred>
               [--layer L1..L4] [--artifact PATH] [--observed-at TIME]
  evidence add --issue N --batch -          # 从 stdin 读 JSON 行，一次写入多条
  evidence list --issue N
      验证的结构化那一半：每条验收标准一条观察，只追加、永不改写。
      `--layer` 标的是这条观察验到哪一层（L1 单元/静态、L2 组件/集成、L3 本地真实链路、
      L4 真实外部系统）；`shipped` 的闸门读它——一条都没标、或只到 L1/L2，都会告警。
      `note --verification` 说的是整次运行证明了什么；这里说的是哪条观察支撑哪个论断，
      连同产生它的命令，好让读者能重跑一遍。`--observed-at` 默认是当前时间。

  followup add --from-issue N --title TEXT [--why TEXT] [--evidence TEXT]
  followup list [--all]
  followup resolve --id ID --status <promoted|dropped> [--issue N] [--why TEXT]
      这轮工作自己的任务队列。评审给出 `follow-up` 判定，意味着 issue 通过了，但
      有件新事不能丢：它记录在这里，随检查点一起版本化，并由 `summary` 打印，绝不留在
      对话里。`promoted` 记录它变成了哪个 issue 编号，下一次 `scan` 会把这个 issue 捡进
      来——一批工作就是这样自我延伸的。

  next
      打印下一个可执行 issue（所有依赖都已 shipped），以及其余的在等什么。

  summary
      打印进度表。

检查点 schema —— 与 heredoc 时代的技能保持一致，好让旧文件能恢复：

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
                     "evidence": [{"kind": "test", "layer": "L3", "command": ...,
                                   "result": "pass", "artifact": ...,
                                   "observed_at": ...}],
                     "evidence_waiver": {"reason": ..., "at": ...}}}
  }

`evidence_waiver` 只在「拿不到观察」时由 `set --status shipped --waive "原因"` 写入：
它是自愿声明，不是豁免（`shipped` 的闸门读 `evidence` 的 `layer`，不读它），
`summary` 会把它标出来。

`title` 与 `deps` 是 `scan` 写入的按 issue 追加字段，好让 `next` 和 `summary` 不必重读
GitHub 就能说明在等什么。`notes`、`evidence` 与 `followups` 同样是追加的——由 `note`、
`evidence` 与 `followup` 子命令写入，没记录之前不存在，重新 `scan` 时逐字保留。缺少其中
任何一项的旧文件仍能恢复；它只是在下次写入之前少了标题、等待原因、notes、evidence 和
follow-up。

排序：反复取编号最小、且批内依赖都已放置的 issue（字典序最小的拓扑序）。这一步卡住时，
剩下的节点构成一个环：编号最小的那个忽略其依赖边，并给出指名该环的告警。

就绪判定：依赖只有状态为 `shipped` 才算满足。状态是 `skipped`、`failed`、`blocked` 或
`in_progress` 的依赖，或根本没被跟踪的依赖（该 issue 已不再 open），都会让依赖它的 issue
继续等待。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

STATUSES = ("pending", "in_progress", "shipped", "failed", "skipped", "blocked")
DONE = ("shipped", "skipped")
RUNNABLE = ("pending", "in_progress")
DEFAULT_STATE = ".loop-state.json"

# 检查点绝不能丢的四件事，逐字保留而非概括。它们是一批做完的工作几个月后仍可审计的
# 原因：状态只说明某件事 shipped 了，说不清决定了什么、什么证明了它、留下了什么没结。
# `progress` 不做强制，因为状态和时间戳已经承载了它；另外三类强制，因为一条缺了它们的
# `shipped` 记录是没有痕迹的断言。
NOTE_CATEGORIES = ("progress", "decisions", "verification", "open")
REQUIRED_NOTES = ("decisions", "verification", "open")

# 验证的结构化那一半：实际观察到了什么，以及产生它的命令。`kind` 是观察的性质，不是它
# 的强度——哪类观察给哪个状态设门禁是工作区自己的决定，不是本脚本的。`result` 刻意是三值
# 的：对一项被跳过的检查，`deferred` 是诚实的答案，它绝不能被伪装成 `pass`。
# 证据层次：证明的**深度**，与 kind（观测的**种类**）正交。层次不自动升级、不互相替代——
# 一条 L1 证据再多也证明不了 L3 的事。典型对应：L1 单测/静态，L2 存储与组件协作，
# L3 本地真实链路（起服务、调真实接口并读回），L4 真实外部系统往返。
LAYERS = ("L1", "L2", "L3", "L4")
# 只到这一层及以下，说明"真实链路"还没验过——shipped 可以，但要留一句话。
SHALLOW_LAYERS = ("L1", "L2")

EVIDENCE_KINDS = ("test", "runtime", "database", "external", "human")
EVIDENCE_RESULTS = ("pass", "fail", "deferred")

# follow-up 是任务，不是笔记：它有生命周期，可以被提升成真正的 issue，一批工作因此在运行
# 中生长，而不是在计划时就冻住。`open` 是唯一的非终态，所以传进来的只有两种解决方式。
FOLLOWUP_OPEN = "open"
FOLLOWUP_RESOLUTIONS = ("promoted", "dropped")

DEP_TRIGGER = re.compile(r"(?:dependencies|depends\s+on|requires)\s*:?", re.IGNORECASE)
REF = re.compile(r"#(\d+)")
SEP = re.compile(r"[ \t]*(?:,|;|\band\b|、)?[ \t]*", re.IGNORECASE)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def warn(message: str) -> None:
    """打一条告警，不改变退出码。"""
    print(f"警告: {message}", file=sys.stderr)


def die(message: str) -> None:
    print(f"loop_state: {message}", file=sys.stderr)
    raise SystemExit(1)


def ref(number: int) -> str:
    return f"#{number}"


# --------------------------------------------------------------------------
# 依赖解析
# --------------------------------------------------------------------------

def parse_deps(body: str, number: int | None = None) -> list[int]:
    """从一个 issue 正文里解析依赖边。

    支持的形式：`Dependencies: #3, #5`、`Depends on: #3`、`depends on #3`、
    `requires #3`，以及用 `and` 连接的列表。第一个非引用 token 之后的引用不再当作依赖。
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
# 图
# --------------------------------------------------------------------------

def cycle_path(start: int, deps: dict[int, set[int]], remaining: set[int]) -> list[int]:
    """从 `start` 出发沿编号最小的边前进，直到某个节点重复出现。"""
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
    """字典序最小的拓扑序，按编号破环。"""
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
            dropped = ", ".join(ref(b) for b in blockers) or "（无）"
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
    """`number` 那些未满足依赖的可读列表。"""
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
# 检查点
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
            die(f"找不到检查点：{path} —— 先跑 `scan` 子命令")
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except json.JSONDecodeError as exc:
        die(f"检查点 {path} 已损坏（JSON 无效：{exc}）—— 修好或删掉它；拒绝覆盖")
    except OSError as exc:
        die(f"检查点 {path} 无法读取：{exc}")
    if not isinstance(raw, dict):
        die(f"检查点 {path} 已损坏（顶层不是对象）—— 修好或删掉它；拒绝覆盖")
    issues = raw.get("issues")
    if not isinstance(issues, dict):
        die(f"检查点 {path} 已损坏（没有 `issues` 对象）—— 修好或删掉它；拒绝覆盖")
    for key, entry in issues.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("status"), str):
            die(f"检查点 {path} 已损坏（issue {key} 没有 status）—— 修好或删掉它；拒绝覆盖")
    if raw.get("version") != 1:
        print(f"⚠️  检查点版本是 {raw.get('version')!r}，期望 1 —— 继续", file=sys.stderr)
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
        die(f"无法从 {path} 读取 issue：{exc}")
    if not text.strip():
        die("没有给出 issue JSON —— 期望 `gh issue list --state open --json number,title,labels,body` 的输出")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        die(f"issue JSON 无效：{exc}")
    if isinstance(data, dict) and isinstance(data.get("issues"), list):
        data = data["issues"]
    if not isinstance(data, list):
        die("issue JSON 必须是 issue 对象的列表")
    return data


def normalize_issue(item: dict) -> tuple[int, str, str, list[str]]:
    if not isinstance(item, dict):
        die(f"issue 条目不是对象：{item!r}")
    try:
        number = int(item.get("number"))
    except (TypeError, ValueError):
        die(f"issue 没有可用的编号：{item!r}")
    title = str(item.get("title") or "").strip() or f"issue #{number}"
    body = item.get("body") or ""
    labels: list[str] = []
    for label in item.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if name:
            labels.append(str(name))
    return number, title, body, labels


# --------------------------------------------------------------------------
# 渲染
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
            detail = entry.get("error_class") or "未知"
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


def labelled(issues: dict, number: int) -> str:
    """`#N[L3]`——把最高证据层次挂在 issue 上，summary 一眼看得出深度。"""
    layer = highest_layer(issues[str(number)])
    return ref(number) + (f"[{layer}]" if layer else "")


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
        f"📊 loop-it: {done}/{total} 完成 ({percent}%)  repo={state.get('repo') or '?'}  "
        f"tracked={state.get('total_issues', total)}",
        "━" * 52,
        f"  ✅ shipped:    {len(buckets.get('shipped', []))}  "
        + ", ".join(labelled(issues, n) for n in buckets.get("shipped", [])),
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
        f"{ref(n)}({issues[str(n)].get('error_class') or '未知'}, "
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
        labels = [
            ref(n) + ("(已声明拿不到观察)" if evidence_waiver(issues[str(n)]) else "") + (f"[{highest_layer(issues[str(n)])}]" if highest_layer(issues[str(n)]) else "")
            for n in no_evidence
        ]
        lines.append(f"  ⚠️  无 evidence 的 shipped: {len(no_evidence)}  " + ", ".join(labels))
    lines.append("━" * 52)
    return "\n".join(lines)


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------

def cmd_scan(args: argparse.Namespace) -> int:
    raw = read_issues(args.issues)
    existing = load_state(args.state)

    fetched: dict[int, dict] = {}
    warnings: list[str] = []
    for item in raw:
        number, title, body, labels = normalize_issue(item)
        if number in fetched:
            warnings.append(f"⚠️  issue {ref(number)} 在输入里出现多次；保留最后一条")
        deps = parse_deps(body, number)
        if number in parse_deps(body):
            warnings.append(f"⚠️  {ref(number)} 依赖自己；该边已丢弃")
        fetched[number] = {"title": title, "deps": deps, "labels": labels}

    if not fetched:
        print("✅ 没有找到 open 的 issue。无事可做。")
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
    print(f"📋 找到 {len(fetched)} 个 open issue（拓扑排序）：")
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
            f"{ref(n)}({issues[str(n)].get('error_class') or '未知'})" for n in failed))
    print(f"\ncheckpoint: {args.state}  (把它加进 .gitignore，然后提交这条规则)")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    issues = state["issues"]
    entry = require_issue(state, args.issue, args.state)
    previous = entry.get("status", "pending")
    stamp = now()

    if args.status == "shipped" and missing_evidence(entry) and not args.waive:
        die(
            f"{ref(args.issue)} 没有记录 evidence —— 背后没有观察的 shipped 记录只说明有事发生过，"
            f"说明不了是什么证明了它。\n"
            f"  先记一条观察：`evidence add --issue {args.issue} --layer <L1|L2|L3|L4> "
            f"--kind <test|runtime|database|external|human> --command '…' --result <pass|fail|deferred>`\n"
            f"  确实拿不到观察时写明原因：`set --issue {args.issue} --status shipped --waive \"…\"`"
        )
    if args.status == "shipped" and not highest_layer(entry):
        # 有 evidence 但一条都没标 layer：这比只到 L1 还弱（读者无从判断它验到哪一层），
        # 所以不能因为"有记录"就放过——闸门判的是层次，不是条数。
        warn(
            f"{ref(args.issue)} 的 evidence 一条都没标 `--layer` —— 无从判断验到哪一层，"
            f"真实链路（L3）是不是验过也看不出来。补上层次再 shipped。"
        )
    elif args.status == "shipped" and highest_layer(entry) in SHALLOW_LAYERS:
        # 「状态与最高层次是否矛盾」——脚本判这个，不判"这条证据是否真的证明了该条验收"（那是人判的）。
        warn(
            f"{ref(args.issue)} 的最高证据只到 {highest_layer(entry)} —— 真实链路（L3）还没验过。"
            f" 跑一遍再 shipped，或者把原因写清楚。"
        )
    if args.status == "shipped" and args.waive and missing_evidence(entry):
        # waiver 是"拿不到观察"的声明，只在真的没有 evidence 时才记：有观察还记一条豁免，
        # 会让 summary 与后来的人以为这条 shipped 背后什么都没有。
        entry["evidence_waiver"] = {"reason": args.waive, "at": stamp}

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
                f"  ! {ref(args.issue)} 没有记录 {', '.join(missing)} —— 缺了这些的 shipped "
                f"记录只说明有事发生过，说明不了是什么证明了它。用 "
                f"`note --issue {args.issue} …` 记录。",
                file=sys.stderr,
            )
        if entry.get("evidence_waiver"):
            print(f"  ℹ️  {ref(args.issue)} 已声明拿不到观察：{entry['evidence_waiver']['reason']}",
                  file=sys.stderr)
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
    """这个 issue 有哪些必填类别一条都没记录。"""
    notes = entry.get("notes") or {}
    return [category for category in REQUIRED_NOTES if not notes.get(category)]


def missing_evidence(entry: dict) -> bool:
    """shipped 的 issue 背后没有任何结构化观察时为真。"""
    return not entry.get("evidence")


def highest_layer(entry: dict) -> str:
    """这条 issue 上最高的一层证据；一条都没有时返回空串。"""
    seen = [r.get("layer") for r in (entry.get("evidence") or []) if r.get("layer") in LAYERS]
    return max(seen, key=LAYERS.index) if seen else ""


def evidence_waiver(entry: dict) -> dict:
    """这条 issue 上自愿声明「拿不到观察」的记录；没有声明时为空 dict。"""
    return entry.get("evidence_waiver") or {}


def require_issue(state: dict, number: int, path: str) -> dict:
    """`number` 的跟踪条目；没有就硬停，并说明如何取得一个。"""
    key = str(number)
    if key not in state["issues"]:
        die(f"{path} 里没有跟踪 {ref(number)} —— 先跑 `scan` 子命令")
    return state["issues"][key]


def open_followups(state: dict) -> list[dict]:
    return [item for item in state.get("followups") or [] if item.get("status") == "open"]


def next_followup_id(state: dict) -> str:
    """单调递增的 `f<n>` id，已解决的 id 绝不会被后续 follow-up 复用。"""
    highest = 0
    for item in state.get("followups") or []:
        match = re.fullmatch(r"f(\d+)", str(item.get("id", "")))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"f{highest + 1}"


def clip(text: str, width: int = 48) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= width else text[: width - 1] + "…"


def read_evidence_batch(source: str) -> list[dict]:
    """读一批 evidence 记录（JSON 行，一行一条）。

    为什么要它：证据是**按验收条件**记的，一条一次调用就是一次工具往返——一张 12 条验收条件的卡
    就是 12 次。观测该合并成一个脚本，记录也该一次写完。批量的只是**写入**，观测本身一条不少。
    """
    text = sys.stdin.read() if source == "-" else open(source, encoding="utf-8").read()
    records: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"evidence batch 第 {lineno} 行不是合法 JSON: {exc}") from exc
        if not isinstance(item, dict):
            raise SystemExit(f"evidence batch 第 {lineno} 行不是对象")
        if item.get("kind") not in EVIDENCE_KINDS:
            raise SystemExit(f"evidence batch 第 {lineno} 行 kind 非法: {item.get('kind')!r}")
        if item.get("result") not in EVIDENCE_RESULTS:
            raise SystemExit(f"evidence batch 第 {lineno} 行 result 非法: {item.get('result')!r}")
        if not item.get("command"):
            raise SystemExit(f"evidence batch 第 {lineno} 行缺 command")
        if item.get("layer") is not None and item["layer"] not in LAYERS:
            raise SystemExit(f"evidence batch 第 {lineno} 行 layer 非法: {item['layer']!r}")
        records.append(item)
    if not records:
        raise SystemExit("evidence batch 是空的")
    return records


def cmd_evidence(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    entry = require_issue(state, args.issue, args.state)

    if args.action == "list":
        records = entry.get("evidence") or []
        if not records:
            print(f"{ref(args.issue)}: 没有记录 evidence")
            return 0
        print(f"{ref(args.issue)}: {len(records)} 条 evidence 记录")
        for record in records:
            artifact = f"   artifact={record['artifact']}" if record.get("artifact") else ""
            print(f"  [{record.get('kind')}] {record.get('result')}  {record.get('observed_at')}{artifact}")
            print(f"    $ {record.get('command')}")
        return 0

    if args.batch:
        records = read_evidence_batch(args.batch)
        for record in records:
            record.setdefault("observed_at", now())
        entry.setdefault("evidence", []).extend(records)
        entry["updated_at"] = now()
        save_state(state, args.state)
        kinds = sorted({r.get("kind", "?") for r in records})
        print(
            f"{ref(args.issue)}: 已记录 {len(records)} 条 evidence（{', '.join(kinds)}）"
            f"（共 {len(entry['evidence'])} 条）"
        )
        return 0

    missing = [n for n in ("kind", "command", "result") if not getattr(args, n)]
    if missing:
        print(f"evidence add: 缺 --{' --'.join(missing)}（或者用 --batch）", file=sys.stderr)
        return 2

    record = {
        "kind": args.kind,
        "command": args.command,
        "result": args.result,
        "observed_at": args.observed_at or now(),
    }
    if args.layer:
        record["layer"] = args.layer
    if args.artifact:
        record["artifact"] = args.artifact
    # 只追加，永不改写。事后发现是错的观察本身也是痕迹的一部分；覆盖它正是这条记录
    # 要防止的丢失。
    entry.setdefault("evidence", []).append(record)
    entry["updated_at"] = now()
    save_state(state, args.state)
    print(
        f"{ref(args.issue)}: 已记录 {args.kind}/{args.result} evidence "
        f"（共 {len(entry['evidence'])} 条）"
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
        print(f"🔀 {item['id']}: 来自 {ref(args.from_issue)} 的 follow-up —— {args.title}")
        print(
            f"  {len(open_followups(state))} 条 open；`summary` 会列出它们，"
            f"`followup resolve --id {item['id']} --status promoted --issue N` 关闭一条。"
        )
        return 0

    if args.action == "list":
        if not followups:
            print("🔀 没有记录 follow-up")
            return 0
        pending = open_followups(state)
        print(f"🔀 follow-ups: {len(pending)} open, {len(followups) - len(pending)} 已解决")
        for item in pending:
            print(f"  {item['id']}  (来自 {ref(item.get('from_issue', 0))})  {item.get('title')}")
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
        die(f"{args.state} 里没有 follow-up {args.id!r} —— 见 `followup list`")
    if item.get("status") != "open":
        die(f"{args.id} 已经是 {item.get('status')}；已解决的 follow-up 不会重新打开")
    if args.status == "promoted" and not args.issue:
        die("--status promoted 需要 --issue N —— 即这个 follow-up 变成了哪个 issue")
    item["status"] = args.status
    item["resolved_at"] = now()
    if args.issue:
        item["promoted_to"] = args.issue
    if args.why:
        item["resolution"] = args.why
    # 同 scope、不阻塞的发现**直接插进本轮**：写一条 pending 条目，`next` 立刻取得到，
    # 不必停下来重跑 `scan`。只在批末 promote 的话，执行中获得的理解决不了正在做的事。
    inserted = False
    if args.status == "promoted" and str(args.issue) not in state["issues"]:
        entry = blank_issue(item.get("title", ""))
        entry["origin"] = item["id"]
        state["issues"][str(args.issue)] = entry
        inserted = True
    if inserted:
        # `total_issues` 只在 `scan` 时算一次。插进来的这一条也要算进去，否则检查点的
        # 计数就永久落后于实际条数——真实运行里出现过 total_issues=6 而实际 7 条。
        state["total_issues"] = len(state["issues"])
    save_state(state, args.state)
    target = f" → {ref(args.issue)}" if args.issue else ""
    print(f"🔀 {args.id}: open → {args.status}{target}  {item.get('title')}")
    if args.status == "promoted":
        if inserted:
            print(f"  已把 {ref(args.issue)} 插进本轮（来自 {args.id}）——"
                  f"`next` 现在就能取到它，不必重跑 `scan`。")
        else:
            print(f"  {ref(args.issue)} 已经在检查点里——重跑 `scan` 会重新排序。")
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
        # 追加而非替换：早期做出的决定恰恰是后续步骤容易覆盖的，丢掉它正是这个字段
        # 要防止的失败。
        notes.setdefault(category, []).append({"at": stamp, "text": text})
        written.append(category)

    if not written:
        die("没有可记录的内容 —— 至少传一个 "
            + ", ".join(f"--{category}" for category in NOTE_CATEGORIES))
    entry["updated_at"] = stamp
    save_state(state, args.state)
    print(f"{ref(args.issue)}: 已记录 {', '.join(written)}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    """按磁盘事实推导「链上走到哪一段」，打印下一个该加载的技能。

    接力失败过一次，值得记：`prd` 落盘之后模型直接开写实现，整条链一步没走，直到用户
    当面追问「为什么不建 issue 不开 loop」才回头。病根不是它没读到「默认继续 /to-issues」
    那句话——它读到了——而是**链上的位置没有任何载体**：那句话在二十多次调用之前读过，
    而「下一步是谁」没有任何东西可查，只能靠回忆。

    所以这条子命令**不发明新状态**（见 `.out-of-scope/no-second-truth-document.md`）：
    它把已经存在的磁盘事实（`documents/`、`issues/`、检查点、工作树的改动）推导成一句话，
    让任何一个决策点都能问「现在该加载谁」，而不是靠正文里的一句嘱咐。
    """
    scope = os.path.abspath(args.scope)
    documents = sorted(glob.glob(os.path.join(scope, "documents", "*.md")))
    cards = sorted(
        path
        for path in glob.glob(os.path.join(scope, "issues", "*.md"))
        if not os.path.basename(path).startswith(".")
    )
    state_path = args.state
    if state_path == DEFAULT_STATE:
        candidate = os.path.join(scope, "issues", ".loop-state.json")
        if os.path.exists(candidate):
            state_path = candidate
    state = load_state(state_path) if os.path.exists(state_path) else None

    tail = "loop-it → review-it → ship-it → 合入归人（/merge-it）"
    if cards and state:
        counts = Counter(entry.get("status") for entry in state["issues"].values())
        open_count = counts["pending"] + counts["in_progress"] + counts["blocked"]
        if open_count == 0 and counts["shipped"] > 0:
            stage, nxt = "batch-end", "review-it"
            tail = "ship-it → 合入归人（/merge-it）"
            why = f"检查点里 {counts['shipped']} 条 shipped、没有未决项"
        else:
            stage, nxt = "implement", "loop-it"
            why = f"检查点里还有 {open_count} 条未决"
    elif cards:
        stage, nxt = "implement", "loop-it"
        why = f"`issues/` 下 {len(cards)} 张卡，还没有检查点"
    elif documents:
        stage, nxt = "plan", "to-issues"
        why = f"`documents/` 下 {len(documents)} 份文档，`issues/` 下还没有卡"
    else:
        stage, nxt = "plan", "prd"
        why = "既没有 `documents/` 也没有 `issues/`"

    # 越序：还在规划阶段，工作树里却已经有实现改动了——那正是踩过的那次（PRD 落盘 → 直接
    # 开写代码）。只在 git 可用时判：**不按文件扩展名猜**，因为仓库自己有基线文件，按扩展名
    # 判会把「什么都没动」误报成越序。
    if stage == "plan" and not cards:
        stray = uncommitted_outside_docs(scope)
        if stray:
            shown = "、".join(stray[:5]) + ("…" if len(stray) > 5 else "")
            # 用 die 而不是 return 1：这个脚本的失败一律走 SystemExit，调用方（包括自测）
            # 只认退出码。越序必须能被机械看见，否则它又变回一句嘱咐。
            die(
                f"越序：还在规划阶段（`documents/` 下有文档、`issues/` 下 0 张卡），"
                f"但工作树里已经有 {len(stray)} 处实现改动：{shown} —— "
                "先把 `/to-issues` 走完再动实现；这些改动若确实属于文档，就挪进 `documents/`"
            )

    print(f"stage: {stage}")
    print(f"next:  用 `skill` 工具加载 {nxt}")
    print(f"then:  {tail}")
    print(f"依据:  {why}")
    return 0


def uncommitted_outside_docs(scope: str) -> list[str]:
    """git 能用时，列出 `documents/` 与 `issues/` 之外的未提交改动；不能判就返回空。"""
    if not os.path.isdir(os.path.join(scope, ".git")):
        return []
    try:
        proc = subprocess.run(
            ["git", "-C", scope, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if proc.returncode != 0:
        return []
    stray: list[str] = []
    for line in proc.stdout.splitlines():
        path = line[3:].strip().strip('"')
        if not path or path.startswith("documents/") or path.startswith("issues/"):
            continue
        stray.append(path)
    return stray


def cmd_summary(args: argparse.Namespace) -> int:
    state = load_state(args.state, required=True)
    print(render_summary(state))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="解析依赖、给这批 issue 排序、写入检查点")
    scan.add_argument("--issues", help="`gh issue list --json ...` 输出的路径（默认：stdin）")
    scan.add_argument("--repo", help="要记录的 owner/name（默认：保留原值，否则用 git origin）")
    scan.add_argument("--state", default=DEFAULT_STATE)
    scan.set_defaults(func=cmd_scan)

    setter = sub.add_parser("set", help="记录一次 issue 状态转移")
    setter.add_argument("--issue", type=int, required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--error-class", dest="error_class")
    setter.add_argument("--error")
    setter.add_argument("--branch")
    setter.add_argument("--phase")
    setter.add_argument("--waive", metavar="原因",
                        help="shipped 但确实拿不到 evidence 时，写明原因（自愿声明，不是豁免）")
    setter.add_argument("--state", default=DEFAULT_STATE)
    setter.set_defaults(func=cmd_set)

    nxt = sub.add_parser("next", help="打印下一个可执行 issue")
    nxt.add_argument("--state", default=DEFAULT_STATE)
    nxt.set_defaults(func=cmd_next)

    note = sub.add_parser("note", help="记录检查点绝不能丢的四件事")
    note.add_argument("--issue", type=int, required=True)
    note.add_argument("--progress", help="发生了什么")
    note.add_argument("--decisions", help="决定了什么，以及为什么")
    note.add_argument("--verification", help="跑了什么，以及它证明了什么")
    note.add_argument("--open", help="还有什么没结")
    note.add_argument("--state", default=DEFAULT_STATE)
    note.set_defaults(func=cmd_note)

    evidence = sub.add_parser("evidence", help="记录或列出结构化的验证 evidence")
    evidence_sub = evidence.add_subparsers(dest="action", required=True)
    evidence_add = evidence_sub.add_parser("add", help="追加一条观察")
    evidence_add.add_argument("--issue", type=int, required=True)
    # 单条形态与批量形态二选一；下面在 cmd_evidence 里校验，不靠 argparse 的 required。
    evidence_add.add_argument("--kind", choices=EVIDENCE_KINDS)
    evidence_add.add_argument("--command", help="产生它的命令")
    evidence_add.add_argument("--result", choices=EVIDENCE_RESULTS)
    evidence_add.add_argument("--batch", metavar="FILE",
                              help="从 JSON 行批量追加（`-` 读 stdin）——一条 issue 的证据一次写完")
    evidence_add.add_argument("--layer", choices=LAYERS,
                              help="这条证据证明到哪一层（L1 单测/静态、L2 组件、L3 真实链路、L4 外部系统）")
    evidence_add.add_argument("--artifact", help="值得留存的输出路径")
    evidence_add.add_argument("--observed-at", help="观察到的时间（默认：当前时间）")
    evidence_add.add_argument("--state", default=DEFAULT_STATE)
    evidence_add.set_defaults(func=cmd_evidence)
    evidence_list = evidence_sub.add_parser("list", help="打印某个 issue 的观察记录")
    evidence_list.add_argument("--issue", type=int, required=True)
    evidence_list.add_argument("--state", default=DEFAULT_STATE)
    evidence_list.set_defaults(func=cmd_evidence)

    followup = sub.add_parser("followup", help="记录、列出或解决 follow-up 任务")
    followup_sub = followup.add_subparsers(dest="action", required=True)
    followup_add = followup_sub.add_parser("add", help="记录评审发现了什么")
    followup_add.add_argument("--from-issue", type=int, required=True)
    followup_add.add_argument("--title", required=True)
    followup_add.add_argument("--why", help="观察到了什么，以及为什么这不是本 issue 的活")
    followup_add.add_argument("--evidence", help="让它暴露出来的 evidence")
    followup_add.add_argument("--state", default=DEFAULT_STATE)
    followup_add.set_defaults(func=cmd_followup)
    followup_list = followup_sub.add_parser("list", help="打印 open 的 follow-up")
    followup_list.add_argument("--all", action="store_true", help="同时显示已解决的")
    followup_list.add_argument("--state", default=DEFAULT_STATE)
    followup_list.set_defaults(func=cmd_followup)
    followup_resolve = followup_sub.add_parser("resolve", help="关闭一条 follow-up")
    followup_resolve.add_argument("--id", required=True)
    followup_resolve.add_argument("--status", required=True, choices=FOLLOWUP_RESOLUTIONS)
    followup_resolve.add_argument("--issue", type=int, help="它变成了哪个 issue（promoted 时必填）")
    followup_resolve.add_argument("--why", help="为什么丢弃它，或者什么变了")
    followup_resolve.add_argument("--state", default=DEFAULT_STATE)
    followup_resolve.set_defaults(func=cmd_followup)

    route = sub.add_parser("route", help="按磁盘事实推导链上走到哪一段、下一个该加载谁")
    route.add_argument("--scope", default=".", help="作用域根（默认当前目录）")
    route.add_argument("--state", default=DEFAULT_STATE)
    route.set_defaults(func=cmd_route)

    summary = sub.add_parser("summary", help="打印进度表")
    summary.add_argument("--state", default=DEFAULT_STATE)
    summary.set_defaults(func=cmd_summary)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
