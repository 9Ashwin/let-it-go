#!/usr/bin/env python3
"""render_graph_html.py 的单元测试——用 `python3 test_render_graph_html.py` 运行。

看板才是用户真正阅读的产物，所以这些测试检查的是：它不能声称检查点里没有的东西。
不用测试框架：渲染器刻意只用标准库，它的测试也一样。
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_module():
    spec = importlib.util.spec_from_file_location(
        "render_graph_html", os.path.join(HERE, "render_graph_html.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rh = load_module()
failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


def board(state, source=None):
    return rh.render(state, source=source) if source else rh.render(state)


def marked_current(html: str) -> int:
    """看板标记为运行中的波次下标，没有则 -1。"""
    for match in re.finditer(r'<section class="wave ([a-z]+)">', html):
        if match.group(1) == "cur":
            return html[:match.start()].count('<section class="wave')
    return -1


def stale_state():
    """缓存的 `current_wave` 落后于节点状态的检查点。

    这是真实运行会产生的那种形态：用 `set` 记录波次 0 的最后一个节点时，并没有刷新那个
    缓存字段。
    """
    return {
        "version": 1, "task": "t", "repo": "owner/repo", "current_wave": 0,
        "waves": [[1], [2]],
        "nodes": {
            "1": {"title": "a", "status": "shipped", "commit": "aaa1111"},
            "2": {"title": "b", "status": "pending"},
        },
    }


def test_current_wave_is_derived_not_read():
    """回归：看板过去信任 `state['current_wave']`，而它只有 plan/set 才会刷新，
    于是高亮的正是刚刚收尾的那一波。"""
    html = board(stale_state())
    check("还有未完成工作的波次就是当前波次", marked_current(html) == 1,
          f"marked={marked_current(html)}")
    check("已收尾的波次没有被标成运行中", "wave done" in html, html[:200])
    check("副标题按推导出的波次计数", "波次 1 / 1" in html,
          re.search(r'<div class="sub">.*?</div>', html).group(0) if '<div class="sub">' in html else "")

    # 反向对照：确实处在波次 0 的检查点仍然这么说。
    fresh = stale_state()
    fresh["nodes"]["1"]["status"] = "in_progress"
    check("确实当前的波次 0 依然是波次 0", marked_current(board(fresh)) == 0)


def test_finished_graph_says_so():
    state = stale_state()
    state["nodes"]["1"]["status"] = "shipped"
    state["nodes"]["2"]["status"] = "shipped"
    state["current_wave"] = 99  # 反方向的过期
    html = board(state)
    check("全部到达终态后没有波次被标成运行中", marked_current(html) == -1,
          f"marked={marked_current(html)}")
    check("副标题说明图已收尾", "所有波次已完成" in html)
    check("而且绝不会声称存在超出末波的波次", "波次 2 / 1" not in html)


def settled_out_of_layout_state():
    """`plan --keep-shipped --only-pending` 写出的形态。

    工作一旦定局，布局就不再携带它，于是 `waves` 只描述剩下的部分，而每个节点仍带着状态
    留在节点表里。
    """
    return {
        "version": 1, "task": "t", "repo": "owner/repo", "current_wave": 0,
        "waves": [[3]],
        "nodes": {
            "1": {"title": "a", "status": "shipped", "commit": "aaa1111"},
            "2": {"title": "b", "status": "shipped", "commit": "bbb2222"},
            "3": {"title": "c", "status": "pending"},
        },
    }


def test_settled_nodes_stay_on_the_board():
    """回归：`waves` 是排期布局，而 `--only-pending` 会把已定局的节点从布局里去掉，所以只看
    `waves` 的看板，会在图重新分层的那一刻丢掉所有已完成的节点。mermaid 图还让它们保持绿色
    ——它走的是节点表——而下面的卡片却直接不存在了，于是一次做了一半的运行，看起来就像一张
    从头到尾只有一波的图。"""
    html = board(settled_out_of_layout_state())
    for nid in ("1", "2"):
        check(f"已结束的 #{nid} 仍有卡片", f'<span class="nid">#{nid}</span>' in html)
    check("并且被报告为已结束，而不是被丢弃",
          '<h2>已结束 <span class="wcount">×2' in html,
          re.search(r"<h2>已结束.*?</h2>", html, re.S).group(0) if "已结束" in html else "")
    check("仍在进行的那一波依然是标记为运行中的那个", marked_current(html) == 0,
          f"marked={marked_current(html)}")

    # 反向对照：不会为已结束的工作编造波次编号。它运行时用的下标已经没了——`--only-pending`
    # 会压缩布局——而沿用新的下标会画出一个从未存在过的波次。
    check("没有为它们编造波次编号", "波次 1" not in html,
          html[html.find("已结束"):][:160])

    # 反向对照：没有任何节点脱离布局的图，不会多出一个分区。
    intact = settled_out_of_layout_state()
    intact["waves"] = [[1, 2], [3]]
    check("没有已结束节点就没有已结束分区", "<h2>已结束" not in board(intact))


def test_footer_names_the_real_source():
    """页脚过去写死了默认文件名，于是从每次运行的检查点渲染出的看板，会声称自己来自
    `.graph_state.json`。"""
    html = board(stale_state(), source=".graph_state-prd015")
    footer = re.search(r"<footer>(.*?)</footer>", html, re.S).group(1)
    check("页脚写出实际渲染的文件名", ".graph_state-prd015" in footer, footer[:200])
    check("而不是默认文件名", ".graph_state.json" not in footer, footer[:200])

    # 反向对照：未标注来源的渲染，报告的仍然是默认值。
    default = board(stale_state())
    check("未指定来源的渲染报告默认文件名",
          rh.STATE_DEFAULT in re.search(r"<footer>(.*?)</footer>", default, re.S).group(1))


def test_snapshot_is_stated_and_stamped():
    html = board(stale_state())
    footer = re.search(r"<footer>(.*?)</footer>", html, re.S).group(1)
    check("页脚自称快照", "快照" in footer, footer[:120])
    check("页脚带有渲染时间戳", re.search(r"渲染于 \d{4}-\d\d-\d\d \d\d:\d\d:\d\d", footer) is not None,
          footer[:200])
    check("页面说明每 5 秒的刷新会跟上检查点",
          "每 5 秒自动刷新" in footer and "重新渲染本文件" in footer, footer[:260])
    # 替换掉的那句话的反向对照：看板过去告诉读者刷新「不会显示新进度」，而当 plan/set 开始
    # 在每次写入时重新渲染它之后，这句话就不再成立了。
    check("不再声称刷新看不到进度",
          "不会显示新进度" not in footer and "never shows new progress" not in footer,
          footer[:260])


def test_both_argument_spellings_work():
    """`--state x` 过去被当成 *路径*，于是运行死在 FileNotFoundError: '--state' 上，
    完全没说明真正的错误。"""
    positional = rh.parse_args(["a.json", "b.html"])
    check("位置参数 STATE 就是状态文件", positional.state == "a.json", str(positional))
    check("位置参数 OUT 就是输出文件", positional.out == "b.html", str(positional))
    flagged = rh.parse_args(["--state", "a.json", "--out", "b.html"])
    check("--state 指向同一个字段", flagged.state == "a.json", str(flagged))
    check("--out 指向同一个字段", flagged.out == "b.html", str(flagged))
    check("选项绝不会被误认成文件名",
          not any(value.startswith("--") for value in (flagged.state, flagged.out)), str(flagged))
    defaulted = rh.parse_args([])
    check("不给参数时回落到文档里的默认值",
          defaulted.state == rh.STATE_DEFAULT and defaulted.out == "graph.html", str(defaulted))


def test_a_repeated_value_is_refused():
    # 每个值都有两种写法，同时给出是歧义，而不是悄悄以最后一个为准。位置参数 OUT 的用例
    # 需要前面先有一个位置参数 STATE，否则第一个裸参数会被填进 STATE。
    for argv in (["a.json", "--state", "b.json"],
                 ["a.json", "b.html", "--out", "c.html"]):
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                rh.parse_args(argv)
            check(f"{argv} 被拒绝", False, "parse_args 接受了重复的值")
        except SystemExit as exc:
            check(f"{argv} 被拒绝", exc.code == 2, str(exc.code))


def test_an_unknown_flag_is_refused():
    try:
        with contextlib.redirect_stderr(io.StringIO()) as err:
            rh.parse_args(["--bogus", "a.json"])
        check("未知选项被拒绝", False, "parse_args 接受了 --bogus")
    except SystemExit as exc:
        check("未知选项被拒绝", exc.code == 2, str(exc.code))
        check("并且 argparse 报出了它的名字", "--bogus" in err.getvalue(), err.getvalue())


def test_missing_checkpoint_reports_instead_of_raising():
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "nope.json")
        err = io.StringIO()
        saved_argv = sys.argv
        sys.argv = ["render_graph_html.py", missing, os.path.join(tmp, "out.html")]
        try:
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = rh.main()
        finally:
            sys.argv = saved_argv
        check("缺少检查点时以非零码退出", code == 1, str(code))
        check("并说明如何生成一个检查点", "graph_state.py plan" in err.getvalue(), err.getvalue())


def main() -> int:
    print("render_graph_html.py 测试")
    for test in (test_current_wave_is_derived_not_read, test_finished_graph_says_so,
                 test_settled_nodes_stay_on_the_board,
                 test_footer_names_the_real_source, test_snapshot_is_stated_and_stamped,
                 test_both_argument_spellings_work, test_a_repeated_value_is_refused,
                 test_an_unknown_flag_is_refused, test_missing_checkpoint_reports_instead_of_raising):
        print(f"- {test.__name__}")
        test()
    if failures:
        print(f"\n{len(failures)} 项失败：{', '.join(failures)}")
        return 1
    print("\nok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
