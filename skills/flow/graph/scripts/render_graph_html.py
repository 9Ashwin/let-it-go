#!/usr/bin/env python3
"""从 .graph_state.json 状态文件渲染浅色主题的 graph.html 看板。

用法：
    render_graph_html.py [state.json] [graph.html]
    render_graph_html.py --state state.json --out graph.html

默认读取 ./.graph_state.json 并写入 ./graph.html。两种写法都支持：技能的文档用位置参数，
而人们习惯敲选项；在此之前，`--state x` 会被当成 *路径*，运行直接死在
FileNotFoundError: '--state' 上，完全看不出真正的错误。

/graph 技能在每个检查点都会调用它：`plan` 与 `set` 每次写入后都运行它，于是页面自动跟上
检查点，不需要谁记得重新渲染。状态是内联的，所以页面就是最后一次写入的快照——打开的
标签页每 5 秒自动刷新，因而能跟上检查点，但两次写入之间的任何变化都不会出现。
无第三方依赖——只用标准库。
"""
import argparse
import html
import json
import os
import sys
from datetime import datetime

STATE_DEFAULT = ".graph_state.json"
LEGACY_STATE = ".graph_state"

STATUS = {
    "pending":     ("待处理",  "#8C8579", "#EFECE3"),
    "in_progress": ("进行中",  "#CC785C", "#F7E9E2"),
    "shipped":     ("已交付",  "#3D7A5A", "#DFEEE4"),
    "failed":      ("失败",    "#B54A3E", "#F6DEDA"),
    "blocked":     ("阻塞",    "#9A6C3A", "#F2E6D4"),
    "skipped":     ("已跳过",  "#8C8579", "#EFECE3"),
}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def node_card(nid, n):
    st = n.get("status", "pending")
    label, fg, bg = STATUS.get(st, STATUS["pending"])
    deps = n.get("deps") or []
    deps_str = ", ".join(f"#{d}" for d in deps) if deps else "无依赖"
    meta = []
    if n.get("pr"):
        meta.append(f'PR #{esc(n["pr"])}')
    if n.get("branch"):
        meta.append(f'<code>{esc(n["branch"])}</code>')
    if n.get("attempts"):
        meta.append(f'第 {esc(n["attempts"])} 次尝试')
    meta_html = " · ".join(meta)
    err = f'<div class="err">{esc(n["error"])}</div>' if n.get("error") else ""
    return f"""
      <div class="node" style="border-left:4px solid {fg}">
        <div class="node-top">
          <span class="nid">#{esc(nid)}</span>
          <span class="badge" style="color:{fg};background:{bg}">{label}</span>
        </div>
        <div class="title">{esc(n.get('title','(无标题)'))}</div>
        <div class="deps">{esc(deps_str)}</div>
        {f'<div class="meta">{meta_html}</div>' if meta_html else ''}
        {err}
      </div>"""


def mermaid(state):
    lines = ["graph LR"]
    nodes = state.get("nodes", {})
    for nid, n in nodes.items():
        t = n.get("title", "")
        lines.append(f'  n{nid}["#{nid} {t}"]')
    for nid, n in nodes.items():
        for d in (n.get("deps") or []):
            lines.append(f"  n{d} --> n{nid}")
    # 按状态着色
    for st, (_, fg, bg) in STATUS.items():
        ids = [f"n{nid}" for nid, n in nodes.items() if n.get("status") == st]
        if ids:
            lines.append(f"  classDef {st} fill:{bg},stroke:{fg},color:#33312B;")
            lines.append(f"  class {','.join(ids)} {st};")
    return "\n".join(lines)


TERMINAL = {"shipped", "skipped", "failed", "blocked"}


def current_wave(state):
    """仍在等待工作的那一波——推导得出，绝不从文件里读。

    `state['current_wave']` 只是缓存副本，仅 plan/set 会刷新它，因此信任它的看板可能标错
    波次（记下某一波最后一个节点时，它过去会停留在刚刚收尾的那一波上）。节点状态才是
    唯一事实来源。
    """
    waves = state.get("waves", [])
    nodes = state.get("nodes", {})
    for index, wave in enumerate(waves):
        if any(nodes.get(str(nid), {}).get("status", "pending") not in TERMINAL for nid in wave):
            return index
    return len(waves)


def render(state, source: str = STATE_DEFAULT):
    # 盖章写进页脚，让过期的看板一眼可见过期：页面是快照，每 5 秒的刷新本身改变不了它。
    rendered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nodes = state.get("nodes", {})
    total = len(nodes)
    counts = {k: 0 for k in STATUS}
    for n in nodes.values():
        counts[n.get("status", "pending")] = counts.get(n.get("status", "pending"), 0) + 1
    shipped = counts.get("shipped", 0)
    pct = int(shipped / total * 100) if total else 0
    waves = state.get("waves", [])
    cur = current_wave(state)

    wave_line = (f"波次 {cur} / {max(len(waves) - 1, 0)}" if cur < len(waves)
                 else "所有波次已完成")

    legend = "".join(
        f'<span class="lg"><i style="background:{bg};border-color:{fg}"></i>{label}</span>'
        for label, fg, bg in STATUS.values()
    )

    # 波次是排期布局，而 `--only-pending` 会刻意把已定局的节点从布局里去掉——所以只看
    # `waves` 的看板，会在图重新分层的那一刻丢掉所有已完成的节点。布局不再携带的节点
    # 仍然属于看板，因此它渲染在末尾的独立分区里，而不是凭空消失。它不会被塞回某个编号
    # 波次：那些编号已经找不回来了。`--only-pending` 会压缩布局，所以重新 plan 给出的下标
    # 并不是该节点实际运行时用的下标——按过期的下标分组，会把已完成的工作和仍在进行的工作
    # 合并到同一个编号下，读起来就像存在过一个从未存在过的波次。
    scheduled = {nid for wave in waves for nid in wave}
    loose = sorted((int(key) for key in nodes if int(key) not in scheduled), key=int)

    wave_html = ""
    for index, wave in enumerate(waves):
        state_cls = "cur" if index == cur else ("done" if index < cur else "future")
        running = ' <span class="pill">运行中</span>' if index == cur else ""
        cards = "".join(node_card(str(nid), nodes.get(str(nid), {"title": f"#{nid}"})) for nid in wave)
        wave_html += f"""
      <section class="wave {state_cls}">
        <h2>波次 {index} <span class="wcount">×{len(wave)} 并行</span>{running}</h2>
        <div class="nodes">{cards}</div>
      </section>"""

    if loose:
        cards = "".join(node_card(str(nid), nodes.get(str(nid), {"title": f"#{nid}"})) for nid in loose)
        wave_html += f"""
      <section class="wave done">
        <h2>已结束 <span class="wcount">×{len(loose)} · 已不在布局中</span></h2>
        <div class="nodes">{cards}</div>
      </section>"""

    stat = lambda k: f'<b style="color:{STATUS[k][1]}">{counts.get(k,0)}</b> {STATUS[k][0]}'
    stats = " · ".join(stat(k) for k in ["shipped", "in_progress", "failed", "blocked", "skipped", "pending"])

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- 每 5 秒刷新一次。下面的状态在渲染时已内联，因此刷新只能看到检查点：`plan` 与 `set`
     每次写入都会重新渲染本文件，两次写入之间的任何内容都不会出现在这里。 -->
<meta http-equiv="refresh" content="5">
<title>graph 看板 · {esc(state.get('task','执行'))}</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
  :root {{ --paper:#F5F4EE; --card:#FFFFFF; --ink:#33312B; --muted:#8C8579;
           --coral:#CC785C; --line:#E7E3D9; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink);
    font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:32px 24px 64px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:20px; margin-bottom:24px; }}
  h1 {{ font-size:22px; margin:0 0 4px; font-weight:650; }}
  .sub {{ color:var(--muted); font-size:13px; }}
  .bar {{ height:8px; background:var(--line); border-radius:99px; margin:16px 0 8px; overflow:hidden; }}
  .bar>i {{ display:block; height:100%; width:{pct}%; background:var(--coral); border-radius:99px; }}
  .stats {{ font-size:13px; color:var(--muted); }}
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; margin:14px 0 4px; font-size:12px; color:var(--muted); }}
  .lg {{ display:inline-flex; align-items:center; gap:6px; }}
  .lg i {{ width:12px; height:12px; border-radius:3px; border:1px solid; display:inline-block; }}
  .diagram {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px; margin:20px 0; overflow:auto; }}
  .wave {{ margin:22px 0; }}
  .wave h2 {{ font-size:15px; margin:0 0 12px; display:flex; align-items:center; gap:10px; }}
  .wcount {{ font-weight:400; color:var(--muted); font-size:12px; }}
  .pill {{ font-size:11px; color:#fff; background:var(--coral); padding:2px 9px; border-radius:99px; }}
  .wave.future {{ opacity:.55; }}
  .nodes {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(240px,1fr)); gap:12px; }}
  .node {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px; }}
  .node-top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
  .nid {{ font-weight:650; color:var(--muted); font-size:13px; }}
  .badge {{ font-size:11px; padding:2px 8px; border-radius:99px; font-weight:600; }}
  .title {{ font-weight:550; margin-bottom:6px; }}
  .deps {{ font-size:12px; color:var(--muted); }}
  .meta {{ font-size:12px; color:var(--muted); margin-top:6px; }}
  .meta code, .node code {{ background:var(--paper); padding:1px 5px; border-radius:5px; font-size:11px; }}
  .err {{ font-size:12px; color:#B54A3E; margin-top:6px; white-space:pre-wrap; }}
  footer {{ margin-top:32px; color:var(--muted); font-size:12px; text-align:center; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{esc(state.get('task','任务图执行'))}</h1>
      <div class="sub">{esc(state.get('repo',''))} · {wave_line} · 更新于 {esc(state.get('updated_at',''))}</div>
      <div class="bar"><i></i></div>
      <div class="stats">{shipped}/{total} 已交付（{pct}%） &nbsp;—&nbsp; {stats}</div>
      <div class="legend">{legend}</div>
    </header>
    <div class="diagram"><pre class="mermaid">{esc(mermaid(state))}</pre></div>
    {wave_html}
    <footer><strong>快照</strong>：渲染于 {rendered_at}，由 /graph 从
      <code>{esc(source)}</code> 读入的最后一次检查点。每次 <code>plan</code> 与 <code>set</code> 都会重新渲染本文件，
      因此打开的标签页——每 5 秒自动刷新——会跟上检查点；两次写入之间的工作要到下一次写入才会出现。</footer>
  </div>
  <script>mermaid.initialize({{ startOnLoad:true, theme:"neutral" }});</script>
</body>
</html>"""


def resolve_state(path: str) -> str:
    """回退到 `path` 旁边那份改名前的检查点。"""
    directory = os.path.dirname(path)
    legacy = os.path.join(directory, LEGACY_STATE) if directory else LEGACY_STATE
    if not os.path.exists(path) and os.path.basename(path) == STATE_DEFAULT and os.path.exists(legacy):
        print(f"注意：改为读取改名前的检查点 {legacy}", file=sys.stderr)
        return legacy
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    """既接受文档里的位置参数，也接受人们实际会敲的选项。

    两个位置参数都带 `nargs="?"`，于是 `render.py a.json b.html` 照常可用，同时
    `--state`/`--out` 命名同样两个值。未知选项现在会直接报 argparse 自己的错误，而不是
    被当成文件名读进去。
    """
    parser = argparse.ArgumentParser(
        description="从 /graph 检查点渲染 graph.html。",
        epilog="位置参数与选项两种写法等价。")
    parser.add_argument("state_pos", nargs="?", metavar="STATE", help="要读取的检查点")
    parser.add_argument("out_pos", nargs="?", metavar="OUT", help="要写入的看板")
    parser.add_argument("--state", dest="state_flag", help="要读取的检查点")
    parser.add_argument("--out", dest="out_flag", help="要写入的看板")
    args = parser.parse_args(argv)
    if args.state_pos and args.state_flag:
        parser.error("检查点只给一次：用 STATE 或 --state，不要同时给")
    if args.out_pos and args.out_flag:
        parser.error("输出只给一次：用 OUT 或 --out，不要同时给")
    args.state = args.state_flag or args.state_pos or STATE_DEFAULT
    args.out = args.out_flag or args.out_pos or "graph.html"
    return args


def main():
    args = parse_args(sys.argv[1:])
    src = resolve_state(args.state)
    dst = args.out
    if not os.path.exists(src):
        print(f"render_graph_html: {src} 处没有检查点——请先运行 graph_state.py plan",
              file=sys.stderr)
        return 1
    with open(src, encoding="utf-8") as f:
        state = json.load(f)
    state.setdefault("updated_at", datetime.now().isoformat(timespec="seconds"))
    with open(dst, "w", encoding="utf-8") as f:
        f.write(render(state, source=src))
    print(f"已写入 {dst}（源：{src}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
