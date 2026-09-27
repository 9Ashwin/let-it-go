#!/usr/bin/env python3
"""loop_state.py 的测试 —— 用 `python3 test_loop_state.py` 运行。

纯 Python，不用 pytest，不联网：脚本刻意只用标准库，它的测试也是。针对临时夹具端到端地
跑解析/排序/恢复这些辅助函数以及各个子命令。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location("loop_state", os.path.join(HERE, "loop_state.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ls = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def run(*argv: str, stdin: str | None = None) -> tuple[int, str, str]:
    """在进程内运行 CLI，捕获（退出码、stdout、stderr）。`stdin` 供 `--batch -` 用。"""
    out, err = io.StringIO(), io.StringIO()
    saved = sys.stdin
    code = 0
    if stdin is not None:
        sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                ls.main([str(a) for a in argv])
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.stdin = saved
    return code, out.getvalue(), err.getvalue()


def write_issues(tmp: str, specs: list[tuple[int, str, str]]) -> str:
    """specs: (number, title, body)。返回夹具路径。"""
    payload = [
        {"number": number, "title": title, "body": body, "labels": []}
        for number, title, body in specs
    ]
    path = os.path.join(tmp, "issues.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return path


def read_state(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_parse_dependencies_variants():
    check("Dependencies: #3, #5", ls.parse_deps("Dependencies: #3, #5") == [3, 5])
    check("Depends on: #3", ls.parse_deps("Depends on: #3") == [3])
    check("depends on #3 内联", ls.parse_deps("The view depends on #3 to render.") == [3])
    check("requires #3", ls.parse_deps("requires #3") == [3])
    check("and 连接的列表", ls.parse_deps("Depends on: #3 and #5") == [3, 5])
    check("多个短语合并", ls.parse_deps("Dependencies: #1\nrequires #4") == [1, 4])
    check("列表在散文处停止", ls.parse_deps("depends on #3, see the PRD for details") == [3])
    check("无依赖", ls.parse_deps("Just a normal issue body.") == [])
    check("空正文", ls.parse_deps("") == [])
    check("自引用被丢弃", ls.parse_deps("Depends on: #7", 7) == [])
    check("只取被引用的那一段", ls.parse_deps("Dependencies: #2\n\n#9 is unrelated") == [2])


def test_topological_order():
    numbers = [5, 1, 2, 3]
    deps = {1: set(), 2: {1}, 3: {2}, 5: set()}
    order, warnings = ls.topology(numbers, deps)
    check("链 + 独立节点的顺序", order == [1, 2, 3, 5], str(order))
    check("无环时没有告警", warnings == [], str(warnings))

    order, _ = ls.topology([4, 2, 3, 1], {4: {2, 3}, 2: {1}, 3: {1}, 1: set()})
    index = {n: i for i, n in enumerate(order)}
    check("菱形依赖中依赖排在前面", index[1] < index[2] and index[1] < index[3]
          and index[2] < index[4] and index[3] < index[4], str(order))


def test_cycle_breaking():
    deps = {4: {5}, 5: {4}, 6: {5}}
    order, warnings = ls.topology([4, 5, 6], deps)
    check("环内成员都被排序", sorted(order) == [4, 5, 6], str(order))
    check("编号最小的排在最前", order[0] == 4, str(order))
    check("依赖方仍排在其依赖之后", order.index(5) < order.index(6), str(order))
    check("打印了环的告警", any("循环依赖" in w for w in warnings), str(warnings))
    check("告警指名了破环点", any("#4" in w and "#5" in w for w in warnings), str(warnings))


def test_resume_from_existing_state():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        previous = {
            "version": 1,
            "started_at": "2025-06-09T10:00:00Z",
            "updated_at": "2025-06-09T10:30:00Z",
            "repo": "owner/repo",
            "total_issues": 2,
            "issues": {
                "1": {"status": "shipped", "branch": "feat/issue-1-add-priority", "attempts": 2,
                      "started_at": "2025-06-09T10:00:00Z", "completed_at": "2025-06-09T10:10:00Z"},
                "9": {"status": "skipped", "attempts": 0},
            },
        }
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(previous, handle)
        issues = write_issues(tmp, [
            (1, "Add priority field", "No deps."),
            (2, "Display indicator", "Dependencies: #1"),
        ])
        code, out, err = run("scan", "--issues", issues, "--state", state_path, "--repo", "owner/repo")
        check("scan 退出码为 0", code == 0, err)
        state = read_state(state_path)
        check("已记录的状态被保留", state["issues"]["1"]["status"] == "shipped")
        check("分支被保留", state["issues"]["1"]["branch"] == "feat/issue-1-add-priority")
        check("attempts 被保留", state["issues"]["1"]["attempts"] == 2)
        check("已关闭的 issue 被保留", state["issues"]["9"]["status"] == "skipped")
        check("新 issue 以 pending 加入", state["issues"]["2"]["status"] == "pending")
        check("新 issue 的依赖被记录", state["issues"]["2"]["deps"] == [1])
        check("标题被记录", state["issues"]["1"]["title"] == "Add priority field")
        check("repo 被保留", state["repo"] == "owner/repo")
        check("total 统计被跟踪的 issue 数", state["total_issues"] == 3)
        check("输出里有检查点文件名", ".loop-state.json" in out, out)

        code, out, err = run("next", "--state", state_path)
        check("恢复后的 next 是 #2", "#2" in out and "📊 next: #2" in out, out)
        check("next 说明了等待原因", "#9" not in out, out)


def test_corrupt_state_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        corrupt = "{ this is not json"
        with open(state_path, "w", encoding="utf-8") as handle:
            handle.write(corrupt)
        issues = write_issues(tmp, [(1, "One", "no deps")])
        code, out, err = run("scan", "--issues", issues, "--state", state_path)
        check("损坏的状态文件是硬错误", code != 0, out)
        check("错误信息里有文件名", state_path in err, err)
        with open(state_path, encoding="utf-8") as handle:
            check("损坏的文件未被覆盖", handle.read() == corrupt)
        code, _, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("set 同样拒绝损坏的状态文件", code != 0, err)
        code, _, err = run("next", "--state", os.path.join(tmp, "missing.json"))
        check("next 缺少检查点是错误", code != 0, err)


def test_evidence_batch_appends_in_one_write():
    """批量写证据：一次调用写多条，条数与内容都对。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = os.path.join(tmp, "issues.json")
        with open(issues, "w", encoding="utf-8") as handle:
            json.dump([{"number": 1, "title": "t", "labels": [], "body": "- [ ] a"}], handle)
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")
        run("set", "--issue", 1, "--status", "in_progress", "--state", state_path)

        batch = "\n".join(json.dumps(r, ensure_ascii=False) for r in [
            {"kind": "test", "command": "go test ./... -count=1", "result": "pass"},
            {"kind": "runtime", "command": "curl -si localhost:8080/healthz", "result": "pass",
             "artifact": "out/health.txt"},
            {"kind": "runtime", "command": "curl -si localhost:8080/static/", "result": "pass"},
        ])
        code, out, err = run("evidence", "add", "--issue", 1, "--state", state_path,
                             "--batch", "-", stdin=batch)
        check("批量退出码为 0", code == 0, err)
        records = read_state(state_path)["issues"]["1"]["evidence"]
        check("一次写入三条", len(records) == 3, records)
        check("命令原样保留", records[0]["command"] == "go test ./... -count=1")
        check("artifact 保留", records[1].get("artifact") == "out/health.txt")
        check("每条都打了时间戳", all(r.get("observed_at") for r in records))

        # 非法行要拦下来，而不是写进去一半
        code, _, err = run("evidence", "add", "--issue", 1, "--state", state_path, "--batch", "-",
                           stdin='{"kind":"nope","command":"x","result":"pass"}')
        check("非法 kind 被拒", code != 0, out)
        check("被拒时没写进去", len(read_state(state_path)["issues"]["1"]["evidence"]) == 3)


def test_blocked_and_next_computation():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [
            (1, "Foundation", "no deps"),
            (2, "Middle", "Depends on: #1"),
            (3, "Top", "Dependencies: #2"),
        ])
        code, out, err = run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")
        check("scan 退出码为 0", code == 0, err)
        check("第一个可执行项是 #1", "📊 next: #1" in out, out)
        check("blocked 列表提到 #2 和 #3", "🔒 blocked:" in out and "#2" in out and "#3" in out, out)

        code, out, err = run("set", "--issue", 1, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("attempts 已递增", state["issues"]["1"]["attempts"] == 1, str(state["issues"]["1"]))
        check("started_at 已打戳", bool(state["issues"]["1"].get("started_at")))
        check("phase 默认为 implement", state["issues"]["1"]["phase"] == "implement")
        check("next 仍停在 in_progress 的 issue 上", "📊 next: #1" in out and "恢复" in out, out)

        run("set", "--issue", 1, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("重试递增 attempts", state["issues"]["1"]["attempts"] == 2, str(state["issues"]["1"]))

        run("evidence", "add", "--issue", 1, "--kind", "test", "--command", "go test ./...",
            "--result", "pass", "--state", state_path)
        code, out, err = run("set", "--issue", 1, "--status", "shipped",
                             "--branch", "feat/issue-1-foundation", "--state", state_path)
        state = read_state(state_path)
        check("shipped 已记录", state["issues"]["1"]["status"] == "shipped")
        check("分支已记录", state["issues"]["1"]["branch"] == "feat/issue-1-foundation")
        check("completed_at 已打戳", bool(state["issues"]["1"].get("completed_at")))
        check("next 移到 #2", "📊 next: #2" in out, out)
        check("#3 仍在等 #2", "#3" in out and "等待" in out, out)

        code, out, err = run("set", "--issue", 2, "--status", "failed",
                             "--error-class", "build_failure", "--error", "boom",
                             "--state", state_path)
        state = read_state(state_path)
        check("failed 已记录", state["issues"]["2"]["status"] == "failed")
        check("error_class 已记录", state["issues"]["2"]["error_class"] == "build_failure")
        check("last_error 已记录", state["issues"]["2"]["last_error"] == "boom")
        check("failed 清掉了 completed_at", "completed_at" not in state["issues"]["2"])
        check("没有可执行的 issue 了", "📊 next: (无可执行项)" in out, out)
        check("打印了失败原因", "上次失败" in out and "build_failure" in out, out)

        code, out, err = run("summary", "--state", state_path)
        check("summary 退出码为 0", code == 0, err)
        check("summary 统计 shipped", "shipped:    1" in out, out)
        check("summary 统计 failed 并带原因", "failed:     1" in out and "build_failure" in out, out)
        check("summary 列出 blocked 的 #3", "blocked:    1" in out and "#3" in out, out)

        code, out, err = run("set", "--issue", 2, "--status", "in_progress", "--state", state_path)
        state = read_state(state_path)
        check("重试只清掉 completed_at", state["issues"]["2"]["status"] == "in_progress")
        check("next 恢复 #2", "📊 next: #2" in out, out)


def test_untracked_dependency_waits():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(2, "Needs a closed issue", "Depends on: #99")])
        code, out, err = run("scan", "--issues", issues, "--state", state_path)
        check("scan 退出码为 0", code == 0, err)
        check("报告了未被跟踪的依赖", "#99" in out and "不在本批" in out, out)
        check("未被跟踪的依赖阻塞 next", "📊 next: (无可执行项)" in out, out)


def test_notes_are_kept_verbatim():
    """这四个类别是一批做完的工作仍可审计的原因。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(1, "Only", "no deps")])
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")

        code, out, err = run("note", "--issue", 1, "--state", state_path)
        check("没有内容可记录的 note 被拒绝", code == 1, out)

        code, out, err = run("note", "--issue", 1, "--decisions", "chose X over Y",
                             "--verification", "go test ./... exit 0", "--open", "none",
                             "--state", state_path)
        check("note 退出码为 0", code == 0, err)
        notes = read_state(state_path)["issues"]["1"]["notes"]
        check("decisions 已记录", notes["decisions"][0]["text"] == "chose X over Y", str(notes))
        check("progress 仍是可选的", "progress" not in notes, str(notes))

        run("note", "--issue", 1, "--decisions", "and later Z", "--state", state_path)
        kept = [entry["text"] for entry in read_state(state_path)["issues"]["1"]["notes"]["decisions"]]
        check("notes 追加而非替换", kept == ["chose X over Y", "and later Z"], str(kept))

        run("evidence", "add", "--issue", 1, "--kind", "test", "--command", "go test ./...",
            "--result", "pass", "--state", state_path)
        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("记录齐全时 shipped 不告警", "没有记录 decisions" not in err, err)


def test_shipping_without_evidence_is_refused():
    """背后没有观察的 shipped 记录是断言，不是记录——这条是阻塞，不是告警。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(1, "Only", "no deps")])
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")

        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("没有 evidence 的 shipped 被拒绝", code != 0, out)
        check("拒绝时说明怎么补", "evidence add" in err and "--waive" in err, err)
        check("被拒绝的转移没有落盘",
              read_state(state_path)["issues"]["1"]["status"] != "shipped",
              str(read_state(state_path)["issues"]["1"]))

        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path,
                             "--waive", "只有线上环境能验，本地拿不到观察")
        check("写明原因后可以豁免", code == 0, err)
        entry = read_state(state_path)["issues"]["1"]
        check("豁免的原因记进了检查点",
              entry["status"] == "shipped"
              and entry["evidence_waiver"]["reason"] == "只有线上环境能验，本地拿不到观察"
              and entry["evidence_waiver"]["at"], str(entry))
        check("豁免时给一行信息而非告警", "已豁免" in err, err)

        code, out, err = run("summary", "--state", state_path)
        check("summary 标出这条豁免", "#1(已豁免)" in out, out)


def test_shipping_without_notes_warns():
    """缺 decisions / verification / open 只告警不拦——那是判断，不是可核验的事实。"""
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(1, "Only", "no deps")])
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")

        run("evidence", "add", "--issue", 1, "--kind", "test", "--command", "go test ./...",
            "--result", "pass", "--state", state_path)
        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("状态转移本身仍然成功", code == 0, err)
        check("三个缺失的类别都被指名",
              "没有记录 decisions, verification, open" in err, err)

        run("note", "--issue", 1, "--decisions", "d", "--state", state_path)
        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("记录不全时仍对剩下的告警",
              "没有记录 verification, open" in err, err)


def test_evidence_is_recorded_structured():
    """shipped 的记录背后需要有观察，而不只是关于观察的散文。

    `note --verification` 说的是整次运行证明了什么；这里说的是哪条观察支撑哪个论断、由什么
    命令产生，这就是"读者能重跑的记录"与"读者只能相信的一句话"之间的区别。
    """
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(1, "Only", "no deps")])
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")

        code, out, err = run("evidence", "add", "--issue", 1, "--kind", "runtime",
                             "--command", "curl -s localhost:8080/health", "--result", "pass",
                             "--artifact", "tmp/health.txt", "--state", state_path)
        check("evidence add 退出码为 0", code == 0, err)
        record = read_state(state_path)["issues"]["1"]["evidence"][0]
        check("记录带有 kind、command、result、artifact 和时间",
              record["kind"] == "runtime" and record["result"] == "pass"
              and record["command"] == "curl -s localhost:8080/health"
              and record["artifact"] == "tmp/health.txt" and record["observed_at"], str(record))

        run("evidence", "add", "--issue", 1, "--kind", "test",
            "--command", "go test ./...", "--result", "deferred", "--state", state_path)
        check("第二条观察是追加而非替换",
              len(read_state(state_path)["issues"]["1"]["evidence"]) == 2)

        code, out, err = run("evidence", "list", "--issue", 1, "--state", state_path)
        check("list 打印产生每条记录的命令",
              "go test ./..." in out and "[test] deferred" in out, out)

        code, out, err = run("evidence", "add", "--issue", 1, "--kind", "vibes",
                             "--command", "x", "--result", "pass", "--state", state_path)
        check("未知的 kind 被拒绝", code != 0, out)

        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")
        check("重新 scan 保留记录",
              len(read_state(state_path)["issues"]["1"]["evidence"]) == 2)

        code, out, err = run("set", "--issue", 1, "--status", "shipped", "--state", state_path)
        check("有 evidence 时 shipped 不告警 evidence",
              "没有记录 evidence" not in err, err)


def test_followups_are_a_queue_not_a_note():
    """supervisor 判定为 `follow-up` 的东西必须有地方落下来，否则就丢了。

    要点是一批工作能在运行中生长：follow-up 被记录下来，熬过一次重新 scan，在 `summary`
    里可见，并且可以被提升成真正的 issue 进入下一轮，而不是只活在发现它的那次对话里。
    """
    with tempfile.TemporaryDirectory() as tmp:
        state_path = os.path.join(tmp, ".loop-state.json")
        issues = write_issues(tmp, [(1, "Only", "no deps")])
        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")

        code, out, err = run("followup", "add", "--from-issue", 1, "--title", "extract the seam",
                             "--why", "two copies of the same rule", "--state", state_path)
        check("followup add 退出码为 0", code == 0, err)
        item = read_state(state_path)["followups"][0]
        check("它初始为 open，并锚定到发现它的 issue",
              item["status"] == "open" and item["from_issue"] == 1, str(item))

        code, out, err = run("followup", "add", "--from-issue", 99, "--title", "x",
                             "--state", state_path)
        check("来自未跟踪 issue 的 follow-up 被拒绝", code == 1, out)

        code, out, err = run("summary", "--state", state_path)
        check("summary 露出 open 的队列", "follow-ups: 1 open" in out, out)

        run("scan", "--issues", issues, "--state", state_path, "--repo", "o/r")
        check("重新 scan 保留队列", len(read_state(state_path)["followups"]) == 1)

        code, out, err = run("followup", "resolve", "--id", "f1", "--status", "promoted",
                             "--issue", 7, "--state", state_path)
        check("resolve 退出码为 0", code == 0, err)
        item = read_state(state_path)["followups"][0]
        check("promotion 记录它变成了哪个 issue",
              item["status"] == "promoted" and item["promoted_to"] == 7, str(item))

        # 同 scope、不阻塞的发现要能**当场进本轮**，而不是等下一次 scan：
        # 只在批末 promote 的话，执行中获得的理解决不了正在做的事。
        promoted = read_state(state_path)["issues"].get("7")
        check("promotion 直接把新 issue 插进本轮，并记下它从哪来",
              promoted is not None and promoted["status"] == "pending"
              and promoted.get("origin") == "f1", str(promoted))
        # 计数要跟着走：它只在 scan 时算一次，插进来的这条不算进去就会永久落后于实际条数
        # （真实运行里出现过 total_issues=6 而实际 7 条）。
        after = read_state(state_path)
        check("promotion 之后 total_issues 等于实际条数",
              after["total_issues"] == len(after["issues"]),
              f"total_issues={after['total_issues']} 实际={len(after['issues'])}")

        code, out, err = run("followup", "resolve", "--id", "f1", "--status", "dropped",
                             "--state", state_path)
        check("已解决的 follow-up 不会重开", code == 1, out)

        run("followup", "add", "--from-issue", 1, "--title", "second", "--state", state_path)
        check("解决之后 id 不会被复用",
              read_state(state_path)["followups"][-1]["id"] == "f2")


def main() -> int:
    print("loop_state.py 测试")
    for test in (
        test_parse_dependencies_variants,
        test_topological_order,
        test_cycle_breaking,
        test_resume_from_existing_state,
        test_corrupt_state_is_refused,
        test_blocked_and_next_computation,
        test_untracked_dependency_waits,
        test_notes_are_kept_verbatim,
        test_shipping_without_evidence_is_refused,
        test_shipping_without_notes_warns,
        test_evidence_is_recorded_structured,
        test_evidence_batch_appends_in_one_write,
        test_followups_are_a_queue_not_a_note,
    ):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} 个失败: {', '.join(failures)}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
