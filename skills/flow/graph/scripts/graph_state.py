#!/usr/bin/env python3
"""为 /graph 任务图做规划与检查点。

依赖环、悬空边、作用域冲突、波分层以及检查点的状态流转都是确定性的。
每一波都用散文重新推导它们更慢也更不可靠，所以它们放在这里，
技能只需要说“跑这个，读摘要”。

子命令：

  plan [--nodes <file>] [--state .graph_state.json] [--max-parallel N] [--keep-shipped] [--only-pending]
      读取 nodes 文件，校验它，分层成波，写检查点，并打印计划
      （人类可读摘要 + Mermaid + 第 0 波派发清单）。
      不给 --nodes 时，图从检查点本身重建——检查点持有 plan 会读的每个声明式字段；
      于是只有在图发生变化（新增节点、移动依赖）时才需要 nodes 文件。
      一张图的首次 plan 仍然需要 --nodes，因为此时还没有检查点可供重新分层。
      带 --keep-shipped 时，现有检查点里每个存活 id 的节点结果会被沿用，
      重新规划不会重置已交付的内容。
      带 --only-pending 时，上一个检查点已经结算（已交付或已跳过）的节点不再占用
      其作用域，于是剩余工作可以和它们共享同一波。它们的文件已经在分支上；
      只有仍在运行的节点才可能与它们冲突。检查点里处于 in_progress 的节点保留
      其作用域，并被排在共享该作用域的待办工作之前，所以重新规划绝不会把子节点
      派发到另一个子节点此刻正在编辑的文件里。把它和 --keep-shipped 配对使用，
      后者才会把已结算的结果放进检查点供读取。
      上限会被持久化：后续 plan 省略 --max-parallel 时会复用记录下来的值，
      而不是悄悄重新分层。

  set --state .graph_state.json --node N --status <s> [--commit SHA] [--branch NAME] [--error TEXT]
      记录一个节点的结果，以及它实际所在的分支（可选）。
      传 --status pending 可清除一次重试。打印编排者接下来该做什么。

  show --state .graph_state.json [--json]
      打印当前计划与每个节点的状态。

  prompt --node N [--state .graph_state.json] [--worktrees DIR]
      按 references/node-prompt.md 渲染一个节点的提示词，其中的 worktree 路径、
      分支、标题、类型、作用域和验收条件都从检查点填入。`plan` 或 `set` 记录过的
      `branch` 会原样使用；只有未记录的节点才会得到一个由标题推导出来的名字，
      此时头部会说明这一点。最先打印的 worktree 命令与提示词中关于分支的说法一致
      ——包括该分支是否存在。依赖摘要是留出的标记缺口——只有编排者知道它们。

nodes 文件格式：

  {
    "task": "Add user auth",
    "repo": "owner/repo",
    "max_parallel": 4,
    "nodes": [
      {"id": 1, "title": "db schema", "deps": [], "scope": "internal/db",
       "criteria": ["migration applies on a fresh database"]},
      {"id": 2, "title": "API handler", "deps": [1], "scope": "internal/api",
       "hot_files": "internal/api/router.go", "branch": "feat/issue-42-api",
       "context": "#1 landed migration 012; the table already exists."}
    ]
  }

`criteria` 是节点的验收清单，会原样复制进子节点的提示词。`context` 是编排者给
子节点的简报：每个依赖一到两行——它新增了什么、加在哪里，以及该节点必须知道的
任何事。两者也可以直接写进检查点。重新规划时，只有 nodes 文件未提及的字段才
保留检查点的值；nodes 文件里显式的空列表/空字符串会清空它（由字段是否存在决定，
而非真假值）。

`scope` 是节点预计会改动的文件/目录的逗号分隔列表。两个没有依赖边但作用域重叠的
节点并不独立：规划器会把 id 较大的那个串行到更晚的波。

`hot_files` 是相反的列表：共享接线文件（一个 router、一个 `main`、一张路由表、
一个 DI 容器、一个类型联合），节点*会*改动它们，但它们必须留在 `scope` 之外，
因为把它们列进去会把整张图串行成一条链。规划器不会因它们串行——它只会在同一波的
两个节点声明了同一个 hot file 时告警，因为那正是会冲突的形状：“只追加的编辑能
干净合并”只在每个节点各自编辑自己的区域时成立。两个节点往同一个 import 块里追加，
或者写同一张路由表，就不是只追加，集成时必然冲突。

`branch`（可选，按节点）是节点实际所在的分支。缺省时检查点不记录任何分支，
`prompt` 会从标题推导一个名字并说明它是推导出来的；实际分支与推导名不同的节点
应当把分支记录下来，否则 `prompt` 会把一个并不存在的名字交给子节点。

状态：pending | in_progress | shipped | failed | blocked | skipped
（`shipped` 和 `skipped` 是完成；`failed` 和 `blocked` 会拖住它们的下游，
但不会永远占住一波——由编排者决定。）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STATUSES = ("pending", "in_progress", "shipped", "failed", "blocked", "skipped")
WAVE_DONE = {"shipped", "skipped", "failed", "blocked"}

# 检查点以前叫 `.graph_state`（没有扩展名），后来为了和同级的 `.loop-state.json`
# 保持一致而改名。旧名字仍然会被读取，好让已经在运行的图不丢进度；但绝不写它。
STATE_DEFAULT = ".graph_state.json"
LEGACY_STATE = ".graph_state"
# 渲染出来的看板与检查点放在一起，每次写入都会刷新它。
BOARD_NAME = "graph.html"


def die(message: str) -> None:
    print(f"graph_state: {message}", file=sys.stderr)
    raise SystemExit(1)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str, what: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        die(f"{what}不存在：{path}")
    except json.JSONDecodeError as exc:
        die(f"{what}不是合法 JSON（{path}）：{exc}")


def legacy_path_for(requested: str) -> str:
    """`requested` 旁边那个改名前的检查点。

    从请求的路径解析，而不是从进程的 cwd，这样
    `--state /work/repo/.graph_state.json` 能找到 `/work/repo/.graph_state`。
    """
    directory = os.path.dirname(requested)
    return os.path.join(directory, LEGACY_STATE) if directory else LEGACY_STATE


def read_state(requested: str) -> tuple[dict, str | None]:
    """加载检查点，并回退到改名前的名字。

    只有默认文件名才回退：显式的 `--state foo.json` 意味着调用者指明了它要的
    文件，悄悄去读另一个文件比直接说它不存在更糟。
    """
    legacy = legacy_path_for(requested)
    if (not os.path.exists(requested) and os.path.basename(requested) == STATE_DEFAULT
            and os.path.exists(legacy)):
        return (load_json(legacy, "状态文件"),
                f"读取了改名前的检查点 {legacy}；下一次写入会落到 {requested}")
    return load_json(requested, "状态文件"), None


def read_previous(requested: str) -> tuple[dict | None, str | None]:
    """与 read_state 相同的回退，但检查点缺失不算错误。"""
    if os.path.exists(requested):
        return load_json(requested, "状态文件"), None
    legacy = legacy_path_for(requested)
    if os.path.basename(requested) == STATE_DEFAULT and os.path.exists(legacy):
        return (load_json(legacy, "状态文件"),
                f"读取了改名前的检查点 {legacy}；下一次写入会落到 {requested}")
    return None, None


def save_state(state: dict, path: str) -> str:
    """写检查点，并刷新它旁边的看板。

    看板是快照——它把检查点内联进去——所以跳过刷新的一次写入会留下一张与状态
    悄悄不符的页面。这不是假设：看板曾经过期了八个小时，而期间节点在被新增和
    交付，因为“重新渲染”是挂在“收尾一波”上的义务，而之后的工作不算一波。把刷新
    放进写入本身，就免掉了某个必须有人记得的步骤。它是尽力而为：已经保存成功的
    检查点不能因为一个展示文件而被报成失败。
    """
    state["updated_at"] = now()
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)
    return render_board(path)


def render_board(path: str) -> str:
    """刷新 `path` 旁边的 BOARD_NAME。返回一条要打印的提示，或 ""。"""
    board = os.path.join(os.path.dirname(os.path.abspath(path)) or ".", BOARD_NAME)
    renderer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_graph_html.py")
    if not os.path.exists(renderer):
        return f"提示: {os.path.basename(renderer)} 不存在，因此 {BOARD_NAME} 没有被刷新"
    result = subprocess.run([sys.executable, renderer, path, board],
                            capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return (f"提示: {BOARD_NAME} 没有被刷新 "
                f"({detail[-1] if detail else '未知错误'})；检查点本身已保存")
    return ""


def scope_set(node: dict) -> set[str]:
    raw = node.get("scope") or ""
    if isinstance(raw, list):
        parts = raw
    else:
        parts = raw.split(",")
    return {p.strip().rstrip("/") for p in parts if p and p.strip()}


def hot_set(node: dict) -> set[str]:
    """节点预计会改动、但留在 `scope` 之外的共享接线文件。"""
    raw = node.get("hot_files") or ""
    if isinstance(raw, list):
        parts = raw
    else:
        parts = raw.split(",")
    return {p.strip().rstrip("/") for p in parts if p and p.strip()}


def validate(nodes: list[dict]) -> tuple[dict[int, dict], list[str]]:
    warnings: list[str] = []
    by_id: dict[int, dict] = {}
    for node in nodes:
        try:
            node_id = int(node["id"])
        except (KeyError, TypeError, ValueError):
            die(f"节点没有可用的整数 id: {node!r}")
        if node_id in by_id:
            die(f"重复的节点 id {node_id}")
        if not str(node.get("title", "")).strip():
            warnings.append(f"节点 {node_id} 没有标题")
        by_id[node_id] = node

    for node_id, node in by_id.items():
        kept = []
        for dep in node.get("deps") or []:
            dep = int(dep)
            if dep not in by_id:
                warnings.append(f"节点 {node_id} 依赖不存在的节点 {dep}；该边已丢弃")
            elif dep == node_id:
                warnings.append(f"节点 {node_id} 依赖自身；该边已丢弃")
            else:
                kept.append(dep)
        node["deps"] = sorted(set(kept))
    return by_id, warnings


def scopes_overlap(a: str, b: str) -> bool:
    """两个作用域条目是否指向同一路径，或一个包含另一个。

    作用域条目是目录和文件一样常见，两个节点写进同一个目录就会冲突——无论它们
    是整体拥有这个目录，还是在里面各写不同的文件。用 `==` 比较看不到这一点，
    于是作用域为 `internal/config` 的节点会和作用域为
    `internal/config/config.go` 的节点共享一波——那正是两个 agent 会同时编辑的
    一对。
    """
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def scope_clash(scope: set[str], used: set[str]) -> list[str]:
    """`scope` 中与 `used` 里任何条目冲突的那些条目。"""
    return sorted({entry for entry in scope for other in used if scopes_overlap(entry, other)})


def layer(by_id: dict[int, dict], settled: set[int] | None = None,
          inflight: set[int] | None = None) -> tuple[list[list[int]], list[str]]:
    """把节点分层成波：先依赖，再互不重叠的作用域。

    单趟贪心，因为这两个约束相互影响——因作用域冲突被拦下的节点不能越过它自己的
    依赖，而它的下游也不能和它落在同一波。只有依赖已经就位的节点才是候选，
    所以顺序由构造保证；在作用域上冲突的候选只需等更晚的一波。

    `settled` 指出已经完成的节点（已交付或已跳过）。它们仍会被放置，好让布局
    保留它们的位置、让它们的下游保持顺序，但它们不占用作用域：作用域冲突只在
    两个可能同时运行的节点之间才有意义，而已结算的节点已经落到分支上了。没有
    这一点，运行中重新规划会让早就完成的节点把文件占住，对抗真正剩下的工作，
    从而悄悄把图的尾巴串行成每波一个节点。

    `inflight` 指出此刻正在运行的节点。它们被排在同样就绪的待办节点之前，因为
    这个平局过去只按 id 决定——而 id 顺序在这里是反的。一个正在运行的节点通常
    就是共享其文件的那些节点仍待办的原因，而那些节点大约有一半 id 更小，于是
    它们会被排在它们所等待的工作*之前*，被派发到另一个子节点此刻正在编辑的
    文件里。

    这个冲突被记成一条边，而不是在波循环里过滤掉。过滤会死锁：待办节点等待一个
    自身依赖尚未就位的运行中节点，没有候选能存活，图就被报成有环。作为一条边，
    分层会在依赖允许时把运行中节点排在最前，与之冲突的下游随后跟上——这就是
    同一句“等它跑完”，只是交给排序求解器去做。
    """
    settled = settled or set()
    inflight = inflight or set()
    deps = {nid: set(node["deps"]) for nid, node in by_id.items()}
    for runner in sorted(inflight):
        if runner not in by_id:
            continue
        runner_scope = scope_set(by_id[runner])
        for nid in by_id:
            # 只有还能跑的工作才需要这道屏障。把它接到已结算的节点上会凭空造出一条
            # 跨越历史的边，并可能经由真实依赖闭合出一个环——#135 和 #140 都改
            # protocol.go，而 #144 依赖 #140，于是“等 #144”变成了
            # #135 -> #144 -> #140 -> #135。
            if nid == runner or nid in inflight or nid in settled:
                continue
            if scope_set(by_id[nid]) & runner_scope:
                deps[nid].add(runner)
    notes: list[str] = []
    # 已结算的工作已经做完，所以它既不占作用域也不占一波：唯一未完成依赖已结算的
    # 待办节点*现在*就绪，而不是等布局走完已结算节点自己的依赖链之后。没有这一点，
    # 即使作用域已被释放，尾巴仍会串行——#144 位于一条深链的末端，所以依赖它、
    # 且不依赖任何未完成工作的 #146 仍被推到很晚的一波，而一个无关的 #217 却排在
    # 它前面。因此布局描述的是剩下的工作；已结算的节点连同其状态留在节点表里，
    # 看板的计数和之后任何一次 `set` 读的就是它。
    remaining = set(by_id) - settled
    placed: set[int] = set(settled)
    waves: list[list[int]] = []
    while remaining:
        ready = sorted(nid for nid in remaining if deps[nid] <= placed)
        if not ready:
            cycle = ", ".join(f"#{nid}" for nid in sorted(remaining))
            die(f"{cycle} 之间存在依赖环——断开它并重新规划")
        wave: list[int] = []
        used: set[str] = set()
        for nid in ready:
            scope = scope_set(by_id[nid])
            clash = scope_clash(scope, used)
            if clash:
                notes.append(
                    f"#{nid} 等待一波：作用域 {sorted(clash)} "
                    f"与已在第 {len(waves)} 波的节点重叠"
                )
                continue
            wave.append(nid)
            if nid not in settled:
                used |= scope
        if not wave:  # 所有就绪节点都冲突；只取最小的 id 独占一波
            wave = [ready[0]]
            notes.append(f"#{ready[0]} 独占一波：所有就绪节点都共享它的作用域")
        waves.append(wave)
        remaining.difference_update(wave)
        placed.update(wave)

        # hot 文件被有意放在 `scope` 之外，所以上面的作用域检查看不到这种冲突——
        # 而且把 hot 列表互相比较也不够。危险的形状是*拥有*某个文件的节点（`scope`）
        # 与*编辑*它的节点（`hot_files`）共享一波：那正是“一个节点拥有路由表，
        # 另外三个往里面追加”，一波因此把同一个 import 块解了三次。
        # 告警而不是串行：把这些文件排除在作用域之外，才让一波还能并行。
        for path in sorted({p for nid in wave if nid not in settled for p in hot_set(by_id[nid])}):
            hot = sorted({nid for nid in wave if nid not in settled and path in hot_set(by_id[nid])})
            # 作用域条目可能是目录（`internal/config`），而 hot 文件是它里面的一个
            # 文件，所以这里按包含关系比较而非相等——相等的形式恰好漏掉了这一对。
            owners = sorted({nid for nid in wave if nid not in settled
                             and any(scopes_overlap(entry, path) for entry in scope_set(by_id[nid]))})
            interested = sorted(set(hot) | set(owners))
            if len(interested) < 2:
                continue  # 只有一个节点关心这个文件
            who = ", ".join(f"#{nid}" for nid in interested)
            shape = (f"{who} 都改动 {path}，且 {', '.join(f'#{nid}' for nid in owners)} "
                     f"把它放在作用域里" if owners else f"{who} 都把 {path} 声明为 hot 文件")
            notes.append(
                f"第 {len(waves) - 1} 波: {shape} —— 只有各自编辑自己的区域才能干净合并；"
                f"把它们串行，或者把所有权交给其中一个节点"
            )
    return waves, notes


def wave_of(state: dict) -> dict[int, int]:
    return {nid: index for index, wave in enumerate(state["waves"]) for nid in wave}


def current_wave(state: dict) -> int:
    for index, wave in enumerate(state["waves"]):
        if any(state["nodes"][str(nid)]["status"] not in WAVE_DONE for nid in wave):
            return index
    return len(state["waves"])


def render(state: dict) -> str:
    index_of = wave_of(state)
    done = sum(1 for node in state["nodes"].values() if node["status"] in {"shipped", "skipped"})
    total = len(state["nodes"])
    cap = int(state.get("max_parallel") or 0)
    lines = [f"graph: {state.get('task', '(未命名)')} — {total} 个节点，"
             f"{len(state['waves'])} 波，{done} 个已交付" + (f"，上限 {cap}" if cap else "")]
    for index, wave in enumerate(state["waves"]):
        parts = []
        for nid in wave:
            node = state["nodes"][str(nid)]
            mark = {"shipped": "已交付", "failed": "失败", "blocked": "阻塞", "skipped": "已跳过",
                    "in_progress": "进行中"}.get(node["status"], "待处理")
            ref = f" [{node['commit']}]" if node.get("commit") else ""
            parts.append(f"#{nid} {node['title']} ({mark}){ref}")
        marker = "  <-- 当前" if index == current_wave(state) and index < len(state["waves"]) else ""
        lines.append(f"  第 {index} 波 (x{len(wave)}): " + "; ".join(parts) + marker)
    blocked = [nid for nid, node in state["nodes"].items() if node["status"] == "blocked"]
    if blocked:
        lines.append("  阻塞: " + ", ".join(f"#{nid}" for nid in sorted(blocked, key=int)))
    # 布局不再承载的已结算工作。它仍然是这次运行的一部分，
    # 所以 CLI 摘要要点出它，而不是让上面的波暗示图里只剩这些。
    scheduled = {nid for wave in state["waves"] for nid in wave}
    off_layout = sorted((nid for nid in state["nodes"] if int(nid) not in scheduled), key=int)
    if off_layout:
        marks = {"shipped": "已交付", "skipped": "已跳过", "failed": "失败",
                 "blocked": "阻塞", "in_progress": "进行中"}
        shown = ", ".join(
            f"#{nid} ({marks.get(state['nodes'][nid]['status'], state['nodes'][nid]['status'])})"
            for nid in off_layout)
        lines.append(f"  已结算，不在布局中: {shown}")
    return "\n".join(lines)


def mermaid(state: dict) -> str:
    index_of = wave_of(state)
    lines = ["```mermaid", "graph LR"]
    for nid, node in sorted(state["nodes"].items(), key=lambda kv: int(kv[0])):
        label = str(node["title"]).replace('"', "'")
        lines.append(f'  n{nid}["#{nid} {label}"]')
        for dep in node.get("deps") or []:
            lines.append(f"  n{dep} --> n{nid}")
    lines.append("```")
    return "\n".join(lines)


def dispatch_list(state: dict, index: int) -> list[str]:
    wave = state["waves"][index]
    out = []
    for nid in wave:
        node = state["nodes"][str(nid)]
        deps = ", ".join(f"#{d}" for d in node.get("deps") or []) or "无"
        hot = node.get("hot_files") or []
        hot_note = f" — hot: {', '.join(hot)}" if hot else ""
        out.append(f"  #{nid} [{node.get('type', 'task')}] {node['title']} — 依赖: {deps} "
                   f"— 作用域: {', '.join(sorted(scope_set(node))) or '(无作用域)'}{hot_note}")
    return out


def carry_over(state: dict, previous: dict | None, path: str) -> list[str]:
    """把上一个检查点里每个节点的结果沿用到刚分好层的计划上。

    运行中重新规划很正常：一个节点发现已经满足了，另一个得挪位置。重新分层时把
    每个节点都重置成 `pending`，会逼着编排者手工重新记录已交付的内容，而手工维护
    的账目正是漂移的起点。存活下来的 id 保留其结果；新增的 id 从 pending 开始；
    消失的 id 会被报出来，而不是悄悄留着。
    """
    if previous is None:
        return ["--keep-shipped: 没有可沿用的现有检查点"]
    old_nodes = previous.get("nodes") or {}
    notes: list[str] = []
    carried = 0
    for key, node in state["nodes"].items():
        old = old_nodes.get(key)
        if not isinstance(old, dict):
            continue
        for field in ("status", "branch", "commit", "attempts", "error", "error_class"):
            if field in old:
                node[field] = old[field]
        carried += 1
    if carried:
        notes.append(f"--keep-shipped: 从 {path} 沿用了 {carried} 个节点的结果")
    dropped = sorted(set(old_nodes) - set(state["nodes"]), key=lambda k: (len(str(k)), str(k)))
    if dropped:
        notes.append("--keep-shipped: 丢弃 " + ", ".join(f"#{key}" for key in dropped)
                     + "（已不在 nodes 文件中）")
    return notes


def nodes_from_state(state: dict) -> list[dict]:
    """从检查点重建规划器的输入。

    检查点是 nodes 文件的严格超集：plan 会读的每个声明式字段——title、deps、
    scope、hot_files、type、criteria、context，以及一个已知的 branch——都在节点
    记录上，而 `set` 拥有的结果字段与它们不相交。所以检查点可以在没有当初构建它
    的 nodes 文件的情况下重新分层。

    这很重要，因为 nodes 文件是一次性输入：被 gitignore、容易丢，而且直到现在
    都是那个一旦缺失就让重新规划无法进行的东西——而那恰恰是 `--only-pending`
    最有价值的时候。
    """
    return [
        {
            "id": int(key),
            "title": node.get("title", ""),
            "deps": node.get("deps") or [],
            "scope": node.get("scope") or [],
            "hot_files": node.get("hot_files") or [],
            "type": node.get("type", "task"),
            "criteria": node.get("criteria") or [],
            "context": node.get("context", ""),
            # 只沿用，绝不合成：检查点只在分支存在之后才持有它，
            # 而且下面的 state 构建本来就会丢掉空值。
            "branch": node.get("branch"),
        }
        for key, node in state["nodes"].items()
    ]


def cmd_plan(args: argparse.Namespace) -> int:
    # 无论哪条路径都先读上一个检查点：`--only-pending` 需要它的结果，分层才能
    # 判断谁的作用域还算数；而没有 nodes 文件时，图本身也来自它。
    previous, legacy_note = read_previous(args.state)
    from_state_note = ""
    if args.nodes:
        spec = load_json(args.nodes, "nodes 文件")
        nodes = spec.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            die("nodes 文件必须包含一个非空的 'nodes' 数组")
    else:
        if not previous:
            die(f"无可分层的内容：没有给 nodes 文件，{args.state} 处也没有检查点——"
                f"一张图的首次 plan 请传 --nodes")
        spec = {"task": previous.get("task", "(未命名)"),
                "repo": previous.get("repo", ""),
                "max_parallel": previous.get("max_parallel")}
        nodes = nodes_from_state(previous)
        from_state_note = (f"没有 --nodes：重新分层了记录在 {args.state} 中的 "
                           f"{len(nodes)} 个节点")

    by_id, warnings = validate(nodes)

    checkout_nodes = (previous or {}).get("nodes") or {}
    settled: set[int] = set()
    inflight: set[int] = set()
    if args.only_pending:
        for key, old in checkout_nodes.items():
            if not isinstance(old, dict):
                continue
            if old.get("status") in {"shipped", "skipped"}:
                settled.add(int(key))
            elif old.get("status") == "in_progress":
                inflight.add(int(key))
        settled &= set(by_id)
        inflight &= set(by_id)
        if previous is None:
            notes_later = "--only-pending: 没有现有检查点，因此没有已结算的节点"
        elif not settled:
            notes_later = "--only-pending: 检查点里没有已交付或已跳过的节点"
        else:
            notes_later = (f"--only-pending: {len(settled)} 个已结算节点不再"
                           f"占用其作用域")
            if inflight:
                notes_later += (f"；{len(inflight)} 个运行中的节点"
                                f"（{', '.join(f'#{nid}' for nid in sorted(inflight))}）仍然占用")
    else:
        notes_later = ""
    waves, notes = layer(by_id, settled, inflight)
    if notes_later:
        notes.append(notes_later)

    # 并发上限会塑造布局，所以它属于检查点：不带它重新规划会悄悄重新分层，
    # 而没人会看到变化，因为无论哪种方式每个节点的状态都被保留。
    # 检查点有时是验收条件唯一的存放处（issue 提出来之后，criteria 被直接粘进去）。
    # 重新规划绝不能是破坏性的。
    previous_criteria = {k: v.get("criteria") for k, v in checkout_nodes.items() if v.get("criteria")}
    previous_context = {k: v.get("context") for k, v in checkout_nodes.items() if v.get("context")}
    if legacy_note:
        notes.append(legacy_note)
    if from_state_note:
        notes.append(from_state_note)
    recorded = int((previous or {}).get("max_parallel") or 0)
    if args.max_parallel is not None:
        limit = args.max_parallel
        if recorded and limit != recorded:
            notes.append(f"--max-parallel {limit} 与记录的 {recorded} 不同"
                         f"（{args.state}）——波布局会改变")
    else:
        limit = int(spec.get("max_parallel") or 0)
        if not limit and recorded:
            limit = recorded
            notes.append(f"--max-parallel 未给出：复用记录的 {recorded}（{args.state}）")
    if limit > 0:
        limited: list[list[int]] = []
        for wave in waves:
            for start in range(0, len(wave), limit):
                limited.append(wave[start:start + limit])
        if len(limited) != len(waves):
            notes.append(f"为遵守 --max-parallel {limit}，波被拆分")
        waves = limited

    state = {
        "version": 1,
        "updated_at": now(),
        "task": spec.get("task", "(未命名)"),
        "repo": spec.get("repo", ""),
        "max_parallel": limit,
        "waves": waves,
        "current_wave": 0,
        "nodes": {
            str(nid): {
                "title": node.get("title", ""),
                "deps": node.get("deps") or [],
                "type": node.get("type", "task"),
                "scope": sorted(scope_set(node)),
                "hot_files": sorted(hot_set(node)),
                # 重新规划会从 nodes 文件重建每个节点，所以只记在检查点里的东西会
                # 被悄悄丢掉。验收条件正是会咬人的那种：它们通常在建 issue 时被
                # 直接写进检查点，而之后的一次重新规划过去会把它们抹掉
                # （子节点提示词于是说“从 issue 里把它们写出来”）。
                # 回退到检查点，好让重新规划不是破坏性的。
                # 由字段是否存在决定，而非真假值：nodes 文件里显式的
                # `"criteria": []` 是有意的清空，把它当成“未提供”
                # 会让检查点的值复活。
                "criteria": (node["criteria"] if "criteria" in node
                             else previous_criteria.get(str(nid))) or [],
                "context": (node["context"] if "context" in node
                            else previous_context.get(str(nid))) or "",
                # 分支只在已知时才记录。在 plan 时合成一个会把一个
                # 还没有任何东西创建过的名字放进检查点，`prompt`
                # 随后会把它当作事实呈现。
                **({"branch": str(node["branch"])} if node.get("branch") else {}),
                "status": "pending",
            }
            for nid, node in sorted(by_id.items())
        },
    }

    if args.keep_shipped:
        notes.extend(carry_over(state, previous, args.state))

    state["current_wave"] = current_wave(state)
    board_note = save_state(state, args.state)

    max_par = max(len(wave) for wave in waves)
    print(render(state))
    print(f"\n最大并行度: 一波 {max_par} 个子 agent")
    print(f"检查点: {args.state}")
    for warning in warnings:
        print(f"警告: {warning}")
    for note in notes:
        print(f"提示: {note}")
    if board_note:
        print(board_note)
    print("\n" + mermaid(state))
    index = current_wave(state)
    if index < len(state["waves"]):
        print(f"\n第 {index} 波 —— 一起派发，每个子节点一个:")
        for line in dispatch_list(state, index):
            print(line)
        print("\n下一步: 用 render_graph_html.py 渲染追踪板，然后派发这一波。")
    else:
        print("\n每一波都已关闭——没有可派发的。")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    if args.status not in STATUSES:
        die(f"未知状态 {args.status!r}（应为以下之一: {', '.join(STATUSES)}）")
    state, legacy_note = read_state(args.state)
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"节点 {key} 不在 {args.state} 中")
    node = state["nodes"][key]
    previous = node["status"]
    node["status"] = args.status
    if args.branch:
        node["branch"] = args.branch
    if args.commit:
        node["commit"] = args.commit
    # 节点的结构化报告是它的证据在那一波 workflow 调用返回后唯一存在的地方，
    # 所以要写进检查点，而不是留在对话记录里。`files` 是 fan-in diffstat 拿来
    # 比对的依据——最便宜的一次抓错，而它只有在两边都写下来时才管用。
    #
    # 带默认值读取：CLI 解析器总会提供全部四个，而只想改一个状态的调用方
    # （测试夹具、重新规划脚本）不应该被迫写出它们。
    for field, value in (("files", getattr(args, "files", None)),
                         ("gates", getattr(args, "gates", None)),
                         ("summary", getattr(args, "summary", None)),
                         ("new_work", getattr(args, "new_work", None))):
        if not value:
            continue
        node[field] = [name.strip() for name in value.split(",") if name.strip()] \
            if field == "files" else value
    if args.error:
        node["error"] = args.error
        node["attempts"] = int(node.get("attempts", 0)) + 1
    else:
        node.pop("error", None)
    # `current_wave` 是推导出来的，看板会读它。过去只有 plan 会刷新它，
    # 所以记录一波的最后一个节点之后，文件仍指向那个刚刚关闭的波。
    state["current_wave"] = current_wave(state)
    board_note = save_state(state, args.state)

    index_of = wave_of(state)
    node_wave = index_of.get(int(key))
    index = current_wave(state)
    if legacy_note:
        print(f"提示: {legacy_note}")
    if board_note:
        print(board_note)
    print(f"节点 #{key}: {previous} -> {args.status}")
    if args.status == "shipped":
        missing = [field for field in ("files", "gates", "summary") if not node.get(field)]
        if missing:
            print(
                f"  ! 节点 #{key} 没有记录 {', '.join(missing)}——已交付的节点缺了它们，"
                f"只能说它完成了，说不出是什么证明了它。请把报告字段传给 `set`。",
                file=sys.stderr,
            )
    print(render(state))

    if node_wave is None:  # 对格式良好的 state 不可达，但要诚实
        print("\n节点不在任何一波中——重新规划。")
        return 0

    wave = state["waves"][node_wave]
    if all(state["nodes"][str(nid)]["status"] in WAVE_DONE for nid in wave):
        print(f"\n第 {node_wave} 波已关闭。现在做 fan-in:")
        print("  1. 泄漏检查: 共享检出上的 git status --porcelain 必须是干净的")
        print('  2. 集成: git checkout "$BASE"')
        print("     只有配置了上游时才 pull——没有上游时裸 `git pull` 会以 1 退出:")
        print("     git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull")
        if len(wave) > 1:
            print(f"     git checkout -b wave-{node_wave}-<slug>，然后用 --no-ff 合并每个节点分支")
        else:
            print("     用 --no-ff 合并这一个节点分支（单节点的波跳过波分支）")
        print("     并在集成后的树上跑项目的门禁")
        print("  3. 只审查这一波一次（对着默认分支 git diff），修好，重跑门禁")
        print("  4. 用 ship-it 技能只交付这一波一次，关闭它满足的 issue")
        next_index = node_wave + 1
        if next_index < len(state["waves"]):
            print(f"  5. 渲染追踪板，然后派发第 {next_index} 波:")
            for line in dispatch_list(state, next_index):
                print(line)
        else:
            print("  5. 每一波都完成了——写最终总结并清理 worktree。")
    else:
        outstanding = [f"#{nid}" for nid in wave
                       if state["nodes"][str(nid)]["status"] not in WAVE_DONE]
        print(f"\n第 {node_wave} 波仍未关闭——等待 {', '.join(outstanding)}")
        if index != node_wave:
            print(f"（第 {index} 波已经是当前波；第 {node_wave} 波只差关闭）")
    return 0


def node_slug(title: str, node_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")
    return slug[:40] or f"node-{node_id}"


def worktree_root(override: str | None) -> str:
    """节点 worktree 放在哪里：仓库内部，与技能的配方一致。

    放在内部而不是旁边：DSH 的 `workspace-write` 沙箱会拒绝写会话工作目录之外的
    路径，所以同级的 `.graph-worktrees` 在那里会被拒，而报错读起来不像路径问题。
    技能会在第一波之前为这个路径提交一条忽略规则，从而让泄漏检查时的
    `git status` 保持干净。
    """
    if override:
        return os.path.abspath(override)
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True,
                             capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        die("不在 git 仓库内——传 --worktrees 说明 worktree 放哪里")
    return os.path.join(top, ".graph-worktrees")


def load_template(override: str | None) -> str:
    """节点提示词正文，从技能自己的参考文件读取。

    单一事实来源：脚本渲染出的正是人类会复制的那份模板，所以两者不会漂移。
    """
    path = override or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "node-prompt.md")
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        die(f"节点提示词模板不可读（{path}）：{exc}")
    match = re.search(r"```markdown\n(.*?)\n```", text, re.S)
    if not match:
        die(f"{path} 中没有 ```markdown 模板块")
    return match.group(1)


def cmd_prompt(args: argparse.Namespace) -> int:
    state, legacy_note = read_state(args.state)
    key = str(args.node)
    if key not in state["nodes"]:
        die(f"节点 {key} 不在 {args.state} 中")
    node = state["nodes"][key]

    worktree = os.path.join(worktree_root(args.worktrees), f"node-{key}")
    slug = node_slug(node.get("title", ""), key)
    # 检查点是真实分支名唯一可能的来源：一个改过名的子节点（或者分支在 plan
    # 写下来之前就已创建的节点）不能被这个脚本从标题凭空造出的名字顶掉。
    # 合成只用于还没有人创建过的分支，而且头部会说明这一点，而不是把它当事实。
    recorded = node.get("branch")
    branch = str(recorded) if recorded else f"feat/node-{key}-{slug}"
    exists = os.path.isdir(worktree)

    prompt = load_template(args.template)
    criteria = node.get("criteria") or []
    prompt = prompt.replace(
        "- [ ] {criterion 1}\n- [ ] {criterion 2}",
        "\n".join(f"- [ ] {criterion}" for criterion in criteria)
        or "- [ ] (没有记录验收条件——派发前先从 issue 里把它们写出来)")
    # 节点上的 `context` 是编排者的依赖简报。它过去只是一个无法填写的占位符，
    # 意味着每次派发都要把文字手工追加到提示词的临时副本上——一个容易跳过的步骤，
    # 也是一次无声的质量损失（子节点读不到更早节点的对话）。
    context = str(node.get("context") or "").strip()
    prompt = prompt.replace(
        "{dependency_summaries}",
        context or "(此处填写: 每个依赖一到两行——它新增了什么、加在哪里，以及该节点必须"
        "知道的任何事。子节点读不到更早节点的对话，所以这是图唯一的通道。)")
    for token, value in (
        ("{WT}", worktree),
        ("{N}", key),
        ("{slug}", slug),
        ("{branch}", branch),
        ("{branch_state}", "已经创建并检出" if exists else
         "尚未创建——开始前用上面的命令创建它"),
        ("{title}", str(node.get("title", ""))),
        ("{type}", str(node.get("type", "task"))),
        ("{scope_hint}", ", ".join(node.get("scope") or []) or "(无作用域)"),
    ):
        prompt = prompt.replace(token, value)

    deps = ", ".join(f"#{dep}" for dep in node.get("deps") or []) or "无"
    hot = node.get("hot_files") or []
    if legacy_note:
        print(f"提示: {legacy_note}")
    print(f"# 节点 #{key} — {node.get('title', '')}")
    print(f"# 依赖: {deps}   状态: {node.get('status', 'pending')}")
    if hot:
        print(f"# hot 文件: {', '.join(hot)} —— 共享的；除非各自编辑自己的区域，否则"
              f"预计会和这一波里声明了它们的其他任何节点冲突")
    print("#")
    if exists:
        print(f"# worktree 已经存在；下面的提示词指明了它应该持有的分支:")
        print(f'# 用这条命令确认: git -C "{worktree}" rev-parse --abbrev-ref HEAD')
    else:
        print("# 先创建 worktree——下面的提示词指明了这个分支:")
        print(f'git worktree add -b {branch} "{worktree}" "$BASE"')
    if not recorded:
        print("# （那个分支名是从标题推导出来的，目前还不存在——")
        print(f"#  一旦它存在，就记录下来，让后续提示词不再猜: "
              f"graph_state.py set --node {key} --status <same> --branch {branch})")
    print()
    print(prompt)

    leftovers = sorted(set(re.findall(r"\{[a-z][^}]*\}", prompt)))
    if leftovers:
        print()
        print("# 未填充的占位符: " + ", ".join(leftovers))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state, legacy_note = read_state(args.state)
    if legacy_note and not args.json:
        print(f"提示: {legacy_note}")
    if args.json:
        print(json.dumps(state, indent=2, ensure_ascii=False))
    else:
        print(render(state))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="校验、分层成波、写检查点")
    plan.add_argument("--nodes", default=None,
                      help="nodes JSON 文件的路径；省略则从检查点本身重新分层")
    plan.add_argument("--state", default=STATE_DEFAULT,
                      help=f"检查点路径（默认 {STATE_DEFAULT}）")
    plan.add_argument("--max-parallel", type=int, default=None,
                      help="把宽于此值的波拆开（省略时从检查点复用）")
    plan.add_argument("--keep-shipped", action="store_true",
                      help="把现有检查点中每个节点的结果沿用到新布局上")
    plan.add_argument("--only-pending", action="store_true",
                      help="重新分层时让已交付/已跳过的节点不再占用其作用域")
    plan.set_defaults(func=cmd_plan)

    setter = sub.add_parser("set", help="记录一个节点的结果")
    setter.add_argument("--state", default=STATE_DEFAULT)
    setter.add_argument("--node", required=True)
    setter.add_argument("--status", required=True, choices=STATUSES)
    setter.add_argument("--commit")
    setter.add_argument("--branch", help="记录这个节点实际所在的分支")
    setter.add_argument("--error")
    setter.add_argument("--files", help="节点改动的文件，逗号分隔，来自它的报告")
    setter.add_argument("--gates", help="它跑过的门禁命令及其退出码")
    setter.add_argument("--summary", help="它做了什么，以及什么出乎意料")
    setter.add_argument("--new-work", dest="new_work",
                        help="它发现但图没有覆盖的工作")
    setter.set_defaults(func=cmd_set)

    prompt = sub.add_parser("prompt", help="从检查点渲染一个节点的派发提示词")
    prompt.add_argument("--state", default=STATE_DEFAULT)
    prompt.add_argument("--node", required=True)
    prompt.add_argument("--worktrees", help="worktree 根目录（默认: <repo>/.graph-worktrees）")
    prompt.add_argument("--template", help="覆盖节点提示词模板的路径")
    prompt.set_defaults(func=cmd_prompt)

    show = sub.add_parser("show", help="打印当前计划与状态")
    show.add_argument("--state", default=STATE_DEFAULT)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
