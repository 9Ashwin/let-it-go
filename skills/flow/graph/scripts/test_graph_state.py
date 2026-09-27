#!/usr/bin/env python3
"""graph_state.py 的单元测试——用 `python3 test_graph_state.py` 运行。

不用测试框架：规划器有意只用标准库，它的测试也一样。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location("graph_state", os.path.join(HERE, "graph_state.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gs = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def nodes(*specs):
    return {int(nid): {"id": nid, "title": f"n{nid}", "deps": list(deps), "scope": scope}
            for nid, deps, scope in specs}


def test_dependencies_hold_across_waves():
    by_id = nodes((1, [], "a"), (2, [], "b"), (3, [1], "c"), (4, [2], "d"), (5, [3, 4], "e"))
    waves, _ = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("依赖 1 先于 3", index[1] < index[3])
    check("依赖 2 先于 4", index[2] < index[4])
    check("3 和 4 先于 5", index[3] < index[5] and index[4] < index[5])
    check("独立节点共享第 0 波", sorted(waves[0]) == [1, 2])


def test_scope_collision_defers_without_breaking_order():
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [1], "internal/api"))
    waves, notes = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("冲突的节点被拆开", index[1] != index[2])
    check("冲突被报出", any("等待一波" in n for n in notes), str(notes))
    check("下游仍在它的依赖之后", index[1] < index[3])


def test_cycle_is_fatal():
    by_id = nodes((1, [2], "a"), (2, [1], "b"))
    try:
        gs.layer(by_id)
        check("检测到环", False, "layer() 返回了，而没有退出")
    except SystemExit as exc:
        check("检测到环", exc.code == 1)


def test_missing_dep_is_dropped_with_warning():
    by_id, warnings = gs.validate([{"id": 1, "title": "a", "deps": [99]}])
    check("幽灵边被丢弃", by_id[1]["deps"] == [])
    check("发出了警告", any("不存在的节点 99" in w for w in warnings), str(warnings))


def test_self_dep_is_dropped():
    by_id, warnings = gs.validate([{"id": 7, "title": "self", "deps": [7]}])
    check("自环边被丢弃", by_id[7]["deps"] == [])
    check("自身依赖警告", any("依赖自身" in w for w in warnings), str(warnings))


def test_end_to_end_plan_and_set():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [
                {"id": 1, "title": "a", "scope": "x"},
                {"id": 2, "title": "b", "scope": "y"},
                {"id": 3, "title": "c", "deps": [1, 2], "scope": "z"},
            ]}, handle)
        code = gs.main() if False else None  # main() 只面向 CLI；直接驱动这些命令
        del code
        spec = json.load(open(nodes_path, encoding="utf-8"))
        by_id, _ = gs.validate(spec["nodes"])
        waves, _ = gs.layer(by_id)
        check("两波", waves == [[1, 2], [3]], str(waves))

        state_obj = {
            "version": 1, "task": "t", "repo": "", "waves": waves, "current_wave": 0,
            "nodes": {str(nid): {"title": f"n{nid}", "deps": [], "status": "pending"} for nid in (1, 2, 3)},
        }
        state_obj["nodes"]["1"]["status"] = "shipped"
        state_obj["nodes"]["2"]["status"] = "shipped"
        check("第 0 波关闭", gs.current_wave(state_obj) == 1)
        state_obj["nodes"]["3"]["status"] = "blocked"
        check("所有波都已终结", gs.current_wave(state_obj) == len(waves))
        check("render 提到阻塞", "阻塞: #3" in gs.render(state_obj), gs.render(state_obj))


def test_max_parallel_split_preserves_order():
    by_id = nodes((1, [], "a"), (2, [], "b"), (3, [], "c"), (4, [1], "d"))
    waves, _ = gs.layer(by_id)
    widened = []
    for wave in waves:
        for start in range(0, len(wave), 2):
            widened.append(wave[start:start + 2])
    index = {nid: i for i, wave in enumerate(widened) for nid in wave}
    check("拆分保持依赖顺序", index[1] < index[4])
    check("没有波超过上限", all(len(w) <= 2 for w in widened))


def test_closing_a_wave_announces_fan_in_for_that_wave():
    """回归：fan-in 清单必须描述刚刚关闭的那一波。"""
    import io, contextlib, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1, 2], [3]], "current_wave": 0,
                 "nodes": {str(n): {"title": f"n{n}", "deps": [], "status": "shipped" if n < 3 else "pending"}
                           for n in (1, 2, 3)}}
        state["nodes"]["2"]["status"] = "in_progress"
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "2", "status": "shipped",
                              "commit": "abc1234", "branch": None, "error": None})()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_set(args)
        text = out.getvalue()
        check("第 0 波宣布 fan-in", "第 0 波已关闭。现在做 fan-in:" in text, text[-300:])
        check("列出了下一波派发", "派发第 1 波" in text, text[-300:])
        check("没有假的第 1 波 fan-in", "第 1 波已关闭" not in text)
        check("pull 受上游检查保护",
              "git rev-parse --abbrev-ref --symbolic-full-name '@{u}'" in text, text[-400:])
        check("没有裸 git checkout+pull", "git checkout main && git pull" not in text, text[-400:])
        check("多节点波保留波分支",
              "git checkout -b wave-0-<slug>" in text, text[-400:])


def test_single_node_wave_skips_wave_branch():
    """回归：单节点的波不能被要求创建波分支（D4）。"""
    import io, contextlib, tempfile
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[1], [2]], "current_wave": 0,
                 "nodes": {"1": {"title": "n1", "deps": [], "status": "in_progress"},
                           "2": {"title": "n2", "deps": [1], "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        args = type("A", (), {"state": state_path, "node": "1", "status": "shipped",
                              "commit": "abc1234", "branch": None, "error": None})()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_set(args)
        text = out.getvalue()
        check("单节点波宣布 fan-in", "第 0 波已关闭。现在做 fan-in:" in text, text[-300:])
        check("一个节点时没有波分支", "wave-0-<slug>" not in text, text[-300:])
        check("完全没有波分支命令", "git checkout -b wave-" not in text, text[-300:])
        check("单节点直接合入", "单节点的波跳过波分支" in text, text[-400:])


def test_hot_file_overlap_warns_without_serializing():
    """hot 文件留在 `scope` 之外，所以只有这个检查能看到冲突。"""
    shared = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/a.ts",
                  "hot_files": "src/router.ts"},
              2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts",
                  "hot_files": "src/router.ts"},
              3: {"id": 3, "title": "c", "deps": [], "scope": "src/c.ts",
                  "hot_files": "src/other.ts"}}
    waves, notes = gs.layer(shared)
    check("hot 文件不会把这一波串行", waves == [[1, 2, 3]], str(waves))
    hit = [n for n in notes if "src/router.ts" in n]
    check("重叠的 hot 文件被点出", len(hit) == 1, str(notes))
    check("警告点出了两个编辑者",
          bool(hit) and "#1" in hit[0] and "#2" in hit[0], str(hit))
    check("只被改动一次的 hot 文件不上报",
          not any("src/other.ts" in n for n in notes), str(notes))

    # 负对照：同样的形状但 hot 文件不相交时必须保持沉默。
    apart = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/a.ts", "hot_files": "src/r1.ts"},
             2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts", "hot_files": "src/r2.ts"}}
    _, quiet = gs.layer(apart)
    check("不相交的 hot 文件不产生提示", not any("hot 文件" in n for n in quiet), str(quiet))


def test_keep_shipped_carries_outcome():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit="abc1234", branch="feat/issue-9-reworked",
                                             error=None))
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"},
                                              {"id": 2, "title": "b", "scope": "y"},
                                              {"id": 3, "title": "c", "scope": "z"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        carried = json.load(open(state_path, encoding="utf-8"))
        check("已交付的节点在重新规划后存活", carried["nodes"]["1"]["status"] == "shipped",
              str(carried["nodes"]["1"]))
        check("commit 也存活", carried["nodes"]["1"].get("commit") == "abc1234")
        # 记录过的分支必须在重新分层后存活，即使 nodes 文件不再提到它——
        # 否则 `prompt` 会退回推导出来的名字。
        check("真实分支在重新规划后存活",
              carried["nodes"]["1"].get("branch") == "feat/issue-9-reworked",
              str(carried["nodes"]["1"]))
        check("新增节点从 pending 开始", carried["nodes"]["3"]["status"] == "pending")

        # 负对照：不带这个标志时，重新规划会重置已交付的节点。
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
        reset = json.load(open(state_path, encoding="utf-8"))
        check("没有 --keep-shipped 时结果被重置",
              reset["nodes"]["1"]["status"] == "pending", str(reset["nodes"]["1"]))


def test_prompt_renders_from_the_checkpoint():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "wire the router", "deps": [3], "type": "frontend",
                                 "scope": ["src/app.ts"], "hot_files": ["src/router.ts"],
                                 "criteria": ["the route resolves", "lint passes"],
                                 "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        out = buffer.getvalue()
        check("worktree 路径按节点命名",
              os.path.join(worktrees, "node-7") in out, out[:400])
        check("什么都没记录时，头部和提示词对推导出的名字一致",
              "feat/node-7-wire-the-router" in out)
        check("验收条件渲染成清单",
              "- [ ] the route resolves" in out and "- [ ] lint passes" in out)
        check("作用域被填入", "src/app.ts" in out)
        check("依赖摘要被标为编排者的活", "此处填写" in out)
        check("hot 文件被呈现出来", "src/router.ts" in out)
        check("没有占位符被无声地漏掉",
              "未填充的占位符" not in out, out[-300:])


def test_hot_file_colliding_with_a_scope_is_reported():
    """那个花了三次解冲突的形状：一个节点拥有文件，另一个编辑它。"""
    by_id = {1: {"id": 1, "title": "owns the router", "deps": [], "scope": "src/router.ts"},
             2: {"id": 2, "title": "registers a route", "deps": [], "scope": "src/b.ts",
                  "hot_files": "src/router.ts"}}
    waves, notes = gs.layer(by_id)
    check("被拥有的文件加 hot 文件不会串行", waves == [[1, 2]], str(waves))
    hit = [n for n in notes if "src/router.ts" in n]
    check("跨类冲突被点出", len(hit) == 1, str(notes))
    check("警告点出了双方",
          bool(hit) and "#1" in hit[0] and "#2" in hit[0], str(hit))
    check("它说明了谁拥有文件", bool(hit) and "作用域" in hit[0], str(hit))

    # 负对照：同样的形状，没有共享 -> 沉默。
    apart = {1: {"id": 1, "title": "a", "deps": [], "scope": "src/x.ts"},
             2: {"id": 2, "title": "b", "deps": [], "scope": "src/b.ts", "hot_files": "src/y.ts"}}
    _, quiet = gs.layer(apart)
    check("没有共同利益就不产生提示",
          not any("干净合并" in n for n in quiet), str(quiet))


def test_node_context_fills_the_dependency_slot():
    """依赖简报过去没有入口：节点上的 `context` 填上了它。

    在此之前，那个位置渲染的是一个无法填充的占位符，编排者只能把简报粘贴到
    提示词的临时副本里——而下一次派发就把它丢了。
    """
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        briefing = "#191 landed migration 012 in internal/storage; the table already exists."
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "wire the router", "deps": [3], "type": "frontend",
                                 "scope": ["src/app.ts"], "criteria": ["the route resolves"],
                                 "context": briefing, "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        out = buffer.getvalue()
        check("简报到达了子节点", briefing in out, out[-600:])
        check("占位符消失了", "此处填写" not in out, out[-600:])


def test_replan_keeps_criteria_and_context_only_the_checkpoint_holds():
    """回归：重新规划会从 nodes 文件重建每个节点，所以只记在检查点里的验收条件
    被悄悄抹掉，子节点被告知“从 issue 里把它们写出来”。"""
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
        # 编排者在 issue 提出后记录它们的方式
        state = json.load(open(state_path, encoding="utf-8"))
        state["nodes"]["1"]["criteria"] = ["migration applies on a fresh database"]
        state["nodes"]["1"]["context"] = "#191 landed migration 012; do not create the table again."
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)

        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        again = json.load(open(state_path, encoding="utf-8"))
        check("验收条件在重新规划后存活",
              again["nodes"]["1"].get("criteria") == ["migration applies on a fresh database"],
              str(again["nodes"]["1"]))
        check("context 在重新规划后存活",
              "migration 012" in (again["nodes"]["1"].get("context") or ""),
              str(again["nodes"]["1"]))


def test_recorded_branch_beats_the_synthesized_name():
    """回归：`prompt` 不能凭空造出一个节点实际并不在的分支。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        worktrees = os.path.join(tmp, "wt")
        state = {"version": 1, "task": "t", "repo": "", "waves": [[7]], "current_wave": 0,
                 "nodes": {"7": {"title": "webui", "deps": [], "scope": ["src/app.ts"],
                                 "branch": "feat/node-7-webui-auth-e2e", "status": "pending"}}}
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("使用了记录的分支", "feat/node-7-webui-auth-e2e" in text, text[:400])
        check("worktree 命令写的是记录的分支",
              "git worktree add -b feat/node-7-webui-auth-e2e" in text, text[:400])
        check("不存在的 worktree 不会被说成就绪",
              "已经创建并检出" not in text, text[:400])
        check("提示词说明分支还不存在", "尚未创建" in text)

        # 负对照：没有记录分支时使用合成的名字，头部承认它是推导出来的，
        # 而不是把它当作事实。
        state["nodes"]["7"].pop("branch")
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("什么都没记录时名字从标题推导",
              "feat/node-7-webui" in text, text[:400])
        check("推导被披露", "从标题推导" in text, text[:600])
        check("并被提议写入检查点", "--branch feat/node-7-webui" in text, text[:600])

        # 已存在的 worktree 不能被要求跑 `git worktree add`。
        os.makedirs(os.path.join(worktrees, "node-7"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="7",
                                                worktrees=worktrees, template=None))
        text = out.getvalue()
        check("已存在的 worktree 不会被重建", "git worktree add" not in text, text[:400])
        check("提示词说明分支已被检出",
              "已经创建并检出" in text)


def test_set_records_the_branch_for_later_prompts():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "x"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="in_progress",
                                             commit=None, branch="feat/a-renamed", error=None))
        check("分支落进检查点",
              json.load(open(state_path, encoding="utf-8"))["nodes"]["1"]["branch"] == "feat/a-renamed")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_prompt(gs.argparse.Namespace(state=state_path, node="1",
                                                worktrees=os.path.join(tmp, "wt"), template=None))
        text = out.getvalue()
        check("提示词把它捡起来了", "feat/a-renamed" in text, text[:400])
        check("没有什么需要猜了", "从标题推导" not in text, text[:600])


def test_max_parallel_persists_and_is_reused_on_replan():
    """回归：不带这个标志重新规划会悄悄重新分层。"""
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        spec = {"task": "t", "nodes": [{"id": n, "title": f"n{n}", "scope": f"src/{n}.ts"}
                                       for n in range(1, 7)]}
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump(spec, handle)

        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=4, keep_shipped=False))
        first = json.load(open(state_path, encoding="utf-8"))
        check("上限被写进检查点", first.get("max_parallel") == 4, str(first))
        check("而且它塑造了布局", first["waves"] == [[1, 2, 3, 4], [5, 6]], str(first["waves"]))

        # 缺陷所在：重新规划时丢掉这个标志，布局不得改变。
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        again = json.load(open(state_path, encoding="utf-8"))
        check("不带标志重新规划保留上限", again.get("max_parallel") == 4, str(again))
        check("并保留同样的波", again["waves"] == [[1, 2, 3, 4], [5, 6]], str(again["waves"]))
        note = out.getvalue()
        check("继承被宣布出来，不是无声的", "复用记录的 4" in note, note[:600])
        check("render 显示上限", "上限 4" in gs.render(again), gs.render(again))

        # 有意的改动必须被应用并作为改动报出。
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=6, keep_shipped=True))
        raised = json.load(open(state_path, encoding="utf-8"))
        check("新的上限被应用", raised["waves"] == [[1, 2, 3, 4, 5, 6]], str(raised["waves"]))
        check("不一致被报出", "与记录的 4 不同" in out.getvalue(),
              out.getvalue()[:600])

        # 负对照：显式的 0 表示“无上限”，不得继承。
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=0, keep_shipped=True))
        free = json.load(open(state_path, encoding="utf-8"))
        check("显式的 0 清空上限", free.get("max_parallel") == 0, str(free))
        check("并塌回一波",
              free["waves"] == [[1, 2, 3, 4, 5, 6]], str(free["waves"]))
        check("显式的 0 不会被描述成未设置",
              "复用记录的" not in out.getvalue(), out.getvalue()[:600])

        # nodes 文件也能带上限，好让计划活得比一个 shell 久。
        spec["max_parallel"] = 2
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump(spec, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        from_spec = json.load(open(state_path, encoding="utf-8"))
        check("nodes 文件可以设置上限",
              from_spec["waves"] == [[1, 2], [3, 4], [5, 6]], str(from_spec["waves"]))


def test_legacy_checkpoint_name_is_still_read():
    """检查点被改名为 .graph_state.json——已经在运行的图不能因为改名而丢进度。"""
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            legacy = {"version": 1, "task": "legacy run", "repo": "", "waves": [[1]],
                      "current_wave": 0,
                      "nodes": {"1": {"title": "n1", "deps": [], "status": "shipped"}}}
            with open(gs.LEGACY_STATE, "w", encoding="utf-8") as handle:
                json.dump(legacy, handle)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(state=gs.STATE_DEFAULT, json=False))
            out = buffer.getvalue()
            check("改名前的检查点仍被读取", "legacy run" in out, out[:200])
            check("改名被披露", "改名前" in out, out[:200])

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_set(gs.argparse.Namespace(state=gs.STATE_DEFAULT, node="1",
                                                 status="in_progress", commit=None,
                                                 branch=None, error=None))
            check("写入迁移到新名字", os.path.exists(gs.STATE_DEFAULT),
                  str(os.listdir(".")))
            migrated = json.load(open(gs.STATE_DEFAULT, encoding="utf-8"))
            check("带着迁移后的状态", migrated["nodes"]["1"]["status"] == "in_progress",
                  str(migrated["nodes"]["1"]))

            # 负对照：新文件一旦存在就胜出，即使旧文件仍在磁盘上且内容不同。
            with open(gs.LEGACY_STATE, "w", encoding="utf-8") as handle:
                json.dump({**legacy, "task": "stale legacy"}, handle)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(state=gs.STATE_DEFAULT, json=True))
            out = buffer.getvalue()
            check("新检查点胜过过期的旧文件", "stale legacy" not in out)
            check("没有任何东西被报成改名前", "改名前" not in out)

            # 绝对路径必须在请求的文件旁边解析旧名字，而不是在进程 cwd 旁边——
            # 当检查点位于当前目录之外时，/graph 就是这样调用的。
            elsewhere = os.path.join(tmp, "elsewhere")
            os.makedirs(elsewhere, exist_ok=True)
            with open(os.path.join(elsewhere, gs.LEGACY_STATE), "w", encoding="utf-8") as handle:
                json.dump({**legacy, "task": "absolute legacy"}, handle)
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                gs.cmd_show(gs.argparse.Namespace(
                    state=os.path.join(elsewhere, gs.STATE_DEFAULT), json=True))
            check("绝对路径能找到它旁边的旧文件",
                  "absolute legacy" in buffer.getvalue(), buffer.getvalue()[:200])
        finally:
            os.chdir(cwd)


def test_nodes_file_can_clear_a_checkpoint_value():
    """nodes 文件是事实来源，包括它说“什么都没有”的时候。

    由字段是否存在决定，而非真假值：`"criteria": []` 是有意的清空，把它读成
    “未提供”会让检查点的值复活，于是验收条件永远无法通过重新规划移除。
    """
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")

        def replan(spec):
            with open(nodes_path, "w", encoding="utf-8") as handle:
                json.dump(spec, handle)
            with contextlib.redirect_stdout(io.StringIO()):
                gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                                  only_pending=False,
                                                  max_parallel=None, keep_shipped=True))
            return json.load(open(state_path, encoding="utf-8"))["nodes"]["1"]

        replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                        "criteria": ["from the plan"]}]})
        # 编排者直接在检查点里替换它们
        state = json.load(open(state_path, encoding="utf-8"))
        state["nodes"]["1"]["criteria"] = ["written into the checkpoint"]
        state["nodes"]["1"]["context"] = "briefing written into the checkpoint"
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts"}]})
        check("省略的字段回退到检查点",
              node["criteria"] == ["written into the checkpoint"]
              and "checkpoint" in node["context"], str(node))

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                               "criteria": [], "context": ""}]})
        check("显式的空列表清空验收条件", node["criteria"] == [], str(node))
        check("显式的空字符串清空 context", node["context"] == "", str(node))

        node = replan({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "src/a.ts",
                                               "criteria": ["replaced"],
                                               "context": "replaced"}]})
        check("nodes 文件里的值仍然胜出",
              node["criteria"] == ["replaced"] and node["context"] == "replaced", str(node))


def test_only_pending_frees_a_settled_nodes_scope():
    # 它防的 bug：运行中重新规划一张图时，很久以前就已交付的节点仍然占着它们的
    # 作用域，于是每个还要做、且碰同一个目录的节点都被推进自己独占的一波。
    # 代价是真实的——一条尾巴本可放进四波的图，排成了七波。
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [], "internal/api"))
    without, _ = gs.layer(by_id)
    with_settled, _ = gs.layer(by_id, settled={1})
    before = {nid: i for i, wave in enumerate(without) for nid in wave}
    after = {nid: i for i, wave in enumerate(with_settled) for nid in wave}
    check("不带标志时已结算的拥有者仍会串行", before[1] != before[2])
    check("剩下的两个节点共享第一波", after[2] == 0 and after[3] == 0,
          str(with_settled))
    check("已结算的工作离开它不再约束的布局", 1 not in after,
          str(with_settled))


def test_only_pending_still_serializes_two_pending_nodes():
    # 上面的负对照：释放已结算的作用域不能把关掉作用域冲突检测。
    # 两个真会一起跑的节点仍然拆开。
    by_id = nodes((1, [], "internal/db"), (2, [], "internal/db"), (3, [], "internal/api"))
    waves, notes = gs.layer(by_id, settled={3})
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("同一路径上的两个待办节点仍然拆开", index[1] != index[2], str(waves))
    check("冲突仍被报出", any("等待一波" in n for n in notes), str(notes))


def test_only_pending_via_plan_moves_work_into_earlier_waves():
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "a", "scope": "internal/db"},
                                              {"id": 2, "title": "b", "scope": "internal/db"},
                                              {"id": 3, "title": "c", "scope": "internal/db"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit=None, branch=None, error=None))
        # 不带标志时，已交付的节点仍然独占一个位置。
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=True))
        held = json.load(open(state_path, encoding="utf-8"))
        check("不带标志时已交付节点占住一波", len(held["waves"]) == 3,
              str(held["waves"]))
        # 带上它，剩下的两个节点可以共享它们就绪的第一波。
        with contextlib.redirect_stdout(io.StringIO()):
            freed = gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                                      only_pending=True,
                                                      max_parallel=None, keep_shipped=True))
        state = json.load(open(state_path, encoding="utf-8"))
        check("带标志重新规划成功", freed == 0, str(freed))
        check("布局塌缩到剩下的工作", len(state["waves"]) == 2,
              str(state["waves"]))
        check("结果仍被沿用", state["nodes"]["1"]["status"] == "shipped")
        check("已结算的工作不在波列表里",
              all(1 not in wave for wave in state["waves"]), str(state["waves"]))


def test_only_pending_layers_inflight_ahead_of_what_it_blocks():
    # 咬人的形状：#208 正在 internal/webui 上运行，而它正是 #165/#173/#174/#190
    # 仍待办的原因——但那些 id 都更小，于是按 id 破平局先把它们排了出来，
    # 会把它们派发到 #208 当时正在编辑的文件里。
    by_id = nodes((165, [], "internal/webui"), (208, [], "internal/webui"))
    plain, _ = gs.layer(by_id)
    guarded, _ = gs.layer(by_id, inflight={208})
    plain_index = {nid: i for i, wave in enumerate(plain) for nid in wave}
    kept_index = {nid: i for i, wave in enumerate(guarded) for nid in wave}
    check("只按 id 时阻塞者被排在最后", plain_index[208] > plain_index[165],
          str(plain))
    check("运行中的工作拿走它已在用的位置", kept_index[208] == 0, str(guarded))
    check("它阻塞的东西在等待", kept_index[165] == 1, str(guarded))
    check("运行中的工作仍然占用其作用域", kept_index[165] != kept_index[208])


def test_only_pending_does_not_invent_a_cycle_across_settled_nodes():
    # 弄坏它的真实形状：#135 和 #140 都已交付，且都改
    # internal/fleetq/protocol.go；#144 正在运行并依赖 #140。把运行中屏障接到
    # 已结算的 #135 上，闭合出了 #135 -> #144 -> #140 -> #135，
    # 整张图被报成存在依赖环。
    by_id = nodes((2, [], "internal/fleetq/protocol.go"),
                  (1, [2], "internal/fleetq/protocol.go"))
    try:
        waves, _ = gs.layer(by_id, settled={2}, inflight={1})
    except SystemExit as exc:
        check("已结算的节点绝不会被接到运行中的节点上", False,
              f"layer() 以 {exc.code} 退出了")
        return
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("layer() 在已结算的兄弟节点下存活", sorted(index) == [1], str(waves))
    check("运行中的节点被排出", index[1] == 0, str(waves))


def test_a_directory_scope_covers_the_files_inside_it():
    # 真实的一对：#174 的作用域是整个 `internal/config` 包，#217 是
    # `internal/config/config.go`。只比相等把它们判为兼容，放进同一波，
    # 也就是两个 agent 在编辑一个目录。
    by_id = nodes((1, [], "internal/config"), (2, [], "internal/config/config.go"))
    waves, notes = gs.layer(by_id)
    index = {nid: i for i, wave in enumerate(waves) for nid in wave}
    check("目录和它里面的文件被拆开", index[1] != index[2], str(waves))
    check("冲突被报出", any("等待一波" in n for n in notes), str(notes))

    # 负对照：修复不能把共享一个目录的所有东西都串行。
    # 一个包里的两个不同文件正是并行波存在的意义。
    siblings = nodes((1, [], "internal/config/a.go"), (2, [], "internal/config/b.go"))
    sibling_waves, _ = gs.layer(siblings)
    sibling_index = {nid: i for i, wave in enumerate(sibling_waves) for nid in wave}
    check("一个目录里两个不同的文件仍然共享一波",
          sibling_index[1] == sibling_index[2], str(sibling_waves))


def test_scopes_overlap_treats_nesting_as_a_collision():
    check("相同路径冲突", gs.scopes_overlap("a/b", "a/b"))
    check("子路径与父路径冲突", gs.scopes_overlap("a/b/c.go", "a/b"))
    check("反过来也一样", gs.scopes_overlap("a/b", "a/b/c.go"))
    check("兄弟路径不冲突", not gs.scopes_overlap("a/b", "a/c"))
    check("名字前缀不是路径前缀", not gs.scopes_overlap("a/bc", "a/b"))


def test_every_checkpoint_write_refreshes_the_board():
    # 回归：看板把检查点内联进去，而刷新它曾是挂在“收尾一波”上的义务。一旦工作
    # 不再是一波波的——新增节点、提 issue、部署——状态动了而页面没动：它过期了
    # 八个小时，谁打开它看到的都是已经交付的工作。现在刷新搭在写入本身上。
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        board = os.path.join(tmp, "graph.html")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "nodes": [{"id": 1, "title": "alpha", "scope": "x"}]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False,
                                              max_parallel=None, keep_shipped=False))
        check("plan 把看板写在检查点旁边", os.path.exists(board), board)
        first = open(board, encoding="utf-8").read() if os.path.exists(board) else ""
        check("看板显示了该节点", "alpha" in first, first[:200])

        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit="abc1234", branch=None, error=None))
        second = open(board, encoding="utf-8").read()
        check("状态写入也会刷新它", second != first,
              "状态写入后看板没有变化")
        check("写入在计数里可见", "1/1 已交付" in second, second[:300])
        check("没有过期渲染的提示", "没有被刷新" not in second, second[:200])


def test_render_names_settled_work_the_layout_dropped():
    # 看板丢了已结算的节点，因为 `waves` 不再承载它们。CLI 摘要读的是同一个数组，
    # 于是它也丢了它们，两者在一张“只剩剩下工作”的图上达成了一致。
    # 现在摘要会点出它们。
    state = {
        "version": 1, "task": "t", "repo": "", "max_parallel": 0,
        "waves": [[3]], "current_wave": 0,
        "nodes": {
            "1": {"title": "a", "deps": [], "status": "shipped"},
            "2": {"title": "b", "deps": [], "status": "shipped"},
            "3": {"title": "c", "deps": [], "status": "pending"},
        },
    }
    out = gs.render(state)
    check("摘要点出已结算的节点", "已结算，不在布局中" in out, out)
    check("带着它们的结果", "#1 (已交付)" in out and "#2 (已交付)" in out, out)
    check("仍然列出剩下的那一波", "第 0 波" in out, out)

    # 负对照：没有脱离布局的东西，就没有多余的行。
    state["waves"] = [[1, 2], [3]]
    check("所有东西都在布局里的图不多说什么",
          "已结算，不在布局中" not in gs.render(state), gs.render(state))


def test_plan_re_layers_from_the_checkpoint_alone():
    # 检查点是 nodes 文件的严格超集，所以只有图本身变化时才需要那个文件。
    # 它过去在每次 plan 时都被要求，恰恰在重新规划最值钱的时候让它变得不可能：
    # 运行中、被 gitignore 的一次性输入已经丢了之后。
    with tempfile.TemporaryDirectory() as tmp:
        nodes_path = os.path.join(tmp, "nodes.json")
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(nodes_path, "w", encoding="utf-8") as handle:
            json.dump({"task": "t", "repo": "owner/repo", "nodes": [
                {"id": 1, "title": "a", "deps": [], "scope": "internal/db",
                 "criteria": ["migration applies"]},
                {"id": 2, "title": "b", "deps": [], "scope": "internal/db"},
                {"id": 3, "title": "c", "deps": [1], "scope": "internal/api",
                 "context": "reads a's schema"},
            ]}, handle)
        with contextlib.redirect_stdout(io.StringIO()):
            gs.cmd_plan(gs.argparse.Namespace(nodes=nodes_path, state=state_path,
                                              only_pending=False, max_parallel=None,
                                              keep_shipped=False))
            gs.cmd_set(gs.argparse.Namespace(state=state_path, node="1", status="shipped",
                                             commit="aaa1111", branch="feat/a", error=None))
        os.remove(nodes_path)  # 一次性输入没了

        with contextlib.redirect_stdout(io.StringIO()):
            code = gs.cmd_plan(gs.argparse.Namespace(nodes=None, state=state_path,
                                                     only_pending=True, max_parallel=None,
                                                     keep_shipped=True))
        rebuilt = json.load(open(state_path, encoding="utf-8"))

        check("没有 nodes 文件也能成功规划", code == 0, str(code))
        check("每个节点都回来了", sorted(rebuilt["nodes"]) == ["1", "2", "3"],
              str(sorted(rebuilt["nodes"])))
        check("deps 回来了", rebuilt["nodes"]["3"]["deps"] == [1],
              str(rebuilt["nodes"]["3"]["deps"]))
        check("criteria 回来了", rebuilt["nodes"]["1"]["criteria"] == ["migration applies"],
              str(rebuilt["nodes"]["1"]["criteria"]))
        check("context 回来了", rebuilt["nodes"]["3"]["context"] == "reads a's schema",
              str(rebuilt["nodes"]["3"]["context"]))
        check("记录的分支回来了", rebuilt["nodes"]["1"].get("branch") == "feat/a",
              str(rebuilt["nodes"]["1"].get("branch")))
        check("沿用的结果回来了", rebuilt["nodes"]["1"]["status"] == "shipped")
        # 负对照：图没有变，所以分层必须与 nodes 文件产出的一致——共享作用域
        # 仍然把 #1 和 #2 拆开，依赖仍然把 #3 排在 #1 之后（#1 已结算，因此缺席）。
        check("重新分层的布局就是该文件的布局", rebuilt["waves"] == [[2, 3]],
              str(rebuilt["waves"]))


def test_plan_without_nodes_or_checkpoint_is_refused():
    # 上面的负对照：回退绝不能凭空造出一张空图。
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                gs.cmd_plan(gs.argparse.Namespace(nodes=None, state=state_path,
                                                  only_pending=False, max_parallel=None,
                                                  keep_shipped=False))
            check("没有 nodes 文件也没有检查点会被拒", False, "cmd_plan 返回了")
        except SystemExit as exc:
            check("没有 nodes 文件也没有检查点会被拒", exc.code == 1, str(exc.code))
            check("消息里说要传 --nodes", "--nodes" in err.getvalue(),
                  err.getvalue())


def test_a_node_report_is_written_into_the_checkpoint():
    """一波的 workflow 调用返回的是节点证据的唯一副本，所以它必须落地。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".graph_state.json")
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump({"version": 1, "task": "t", "repo": "", "waves": [[1]], "current_wave": 0,
                       "nodes": {"1": {"title": "n1", "deps": [], "status": "in_progress"}}}, handle)

        def ship(**extra):
            fields = {"state": state_path, "node": "1", "status": "shipped", "commit": "abc1234",
                      "branch": None, "error": None}
            fields.update(extra)
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                gs.cmd_set(type("A", (), fields)())
            return err.getvalue()

        stderr = ship()
        check("没有报告就交付会点名每个缺失字段",
              "没有记录 files, gates, summary" in stderr, stderr)

        stderr = ship(files="src/a.py, tests/test_a.py", gates="pytest -q -> exit 0",
                      summary="wrote the parser", new_work="none")
        with open(state_path, encoding="utf-8") as handle:
            node = json.load(handle)["nodes"]["1"]
        check("files 被拆分并去空白",
              node["files"] == ["src/a.py", "tests/test_a.py"], str(node))
        check("gates 被记录", node["gates"] == "pytest -q -> exit 0", str(node))
        check("summary 被记录", node["summary"] == "wrote the parser", str(node))
        check("new_work 被记录", node["new_work"] == "none", str(node))
        check("完整的报告不告警", "没有记录" not in stderr, stderr)


def main() -> int:
    print("graph_state.py 测试")
    for test in (test_dependencies_hold_across_waves, test_scope_collision_defers_without_breaking_order,
                 test_cycle_is_fatal, test_missing_dep_is_dropped_with_warning,
                 test_self_dep_is_dropped, test_end_to_end_plan_and_set,
                 test_max_parallel_split_preserves_order,
                 test_closing_a_wave_announces_fan_in_for_that_wave,
                 test_single_node_wave_skips_wave_branch,
                 test_hot_file_overlap_warns_without_serializing,
                 test_hot_file_colliding_with_a_scope_is_reported,
                 test_keep_shipped_carries_outcome,
                 test_only_pending_frees_a_settled_nodes_scope,
                 test_only_pending_still_serializes_two_pending_nodes,
                 test_only_pending_via_plan_moves_work_into_earlier_waves,
                 test_only_pending_layers_inflight_ahead_of_what_it_blocks,
                 test_only_pending_does_not_invent_a_cycle_across_settled_nodes,
                 test_a_directory_scope_covers_the_files_inside_it,
                 test_scopes_overlap_treats_nesting_as_a_collision,
                 test_every_checkpoint_write_refreshes_the_board,
                 test_render_names_settled_work_the_layout_dropped,
                 test_plan_re_layers_from_the_checkpoint_alone,
                 test_plan_without_nodes_or_checkpoint_is_refused,
                 test_prompt_renders_from_the_checkpoint,
                 test_node_context_fills_the_dependency_slot,
                 test_replan_keeps_criteria_and_context_only_the_checkpoint_holds,
                 test_recorded_branch_beats_the_synthesized_name,
                 test_set_records_the_branch_for_later_prompts,
                 test_max_parallel_persists_and_is_reused_on_replan,
                 test_legacy_checkpoint_name_is_still_read,
                 test_nodes_file_can_clear_a_checkpoint_value,
                 test_a_node_report_is_written_into_the_checkpoint):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} 个失败: {', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
