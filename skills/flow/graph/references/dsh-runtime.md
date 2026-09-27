# /graph 的 DSH 运行时说明

当某个波行为异常、当你正要派发节点、或当你需要确切的机制时读它。技能正文假设了这些事实；这个文件是它们所在的地方，好让正文保持短。

## 委派

`subagent` 启动一个**全新**子代理，它看不到这段对话；`subagent_fork` 是继承这段对话的变体。调用默认在后台运行并立刻返回一个持久的子代理 id，所以**一条 assistant 消息里的多个 `subagent` 调用是并发的**。后台子代理通过一条**结算通知**回报——永远不要轮询它，永远不要忙等；通知到达就说明那个节点完成了。

| 需要 | 工具 |
|---|---|
| 启动一个节点 | `subagent`（全新上下文） |
| 一次启动 N 个节点 | **一条** assistant 消息里的 N 个 `subagent` 调用 |
| 波屏障 | 等每个节点的结算通知 |
| 审计代理树 | `list_agents(scope="descendants")` |
| 重试 / 继续一个节点 | `send_message(child_id, ...)` |
| 杀掉卡住的节点 | `interrupt_agent(child_id)` |
| 节点内的长构建或测试 | 后台任务（`job_*`） |
| 波的进度 | `todo_write`，以及为 `graph.html` 调 `present` |

## DSH 语境下的两个陷阱

正文陈述的是与宿主无关的事实；这里是它们在 DSH 里怎么咬人：

1. **相对路径。** `read` / `write` / `edit` 把*相对*路径解析到调用方 session 的 cwd——主检出，不是调用者的 worktree。写 `internal/foo.go` 的节点会写进共享工作树。**在节点里，永远传它 worktree 下的绝对路径。**
2. **全新 shell。** `cd` 不跨调用保留。传 `workdir=<abs worktree>`，或在同一条命令里加前缀 `cd <abs worktree> && …`。裸的 `go test ./...` 跑在主检出里。

编排器自己的泄漏检查（合并前对共享检出跑 `git status --porcelain`）就是证明这条纪律守住了的东西。

## depth、并发、成本

- **depth。** 委派深度默认上限是 **1**，所以一个节点——depth 1——完全不能委派。在节点提示词里说清楚：需要第二层工作的节点自己做。
- **并发。** 宿主限制一步里有多少工具调用重叠（默认十个），运行时另外限制一个父级能持有多少可继续的子代理。波的上限（技能第 2 步，默认 3–4）是你真正能控制的刹车，所以自己执行它。
- **成本形态。** 全新子代理加入父级的 composition，所以它收到*同样的* system prompt、*同样的*完整工具 schema 和*同样的*技能目录；这些都不按 depth 裁剪，也不存在 token 预算——轮数是唯一的约束。只有部署层能裁掉子代理（subagent 那一行上的 `toolFilter` / `persona` 是插件配置，不是技能字段；模型面的 `subagent` 工具不接受这类参数）。因此每个子代理整个生命周期都要付这份固定开销，这就是本技能让节点止于"committed"而不延伸进评审与交付的原因，也是琐碎工作属于编排器内联、而不属于节点的原因。
  部署*可以*给节点一个更便宜的子代理：在第二个 `@deepseek-ai/dsh-tool-subagent` 行上配 `toolFilter.deny: [skill]`，会直接去掉那个子代理的目录和加载器，因为目录的可见性与 `skill` 工具匹配。`references/lean-subagent.md` 有可直接粘贴的补丁、实测节省和注意事项——承诺节省之前先读它。
- **模型路由（可选开启，默认关闭）。** 如果部署启用了宿主的 `subagent-model-selection` 设置，`subagent` 还会接受 `provider`、`model` 和 `reasoning_effort`，并出现 `list_subagent_models`。这些字段不在 schema 里时就不可用——每个节点继承父级的路由。不要围绕你看不到的路由做计划。

## `/goal` 与其它技能

`/goal` 是 DSH 的**命令**，不是技能：敲它是人的动作。同一个界面的模型侧是 goal 工具（`create_goal` / `update_goal`），它们的门禁是**权限，不是措辞**：`create_goal` 只在**直接的人类顶层回合**里运行——节点子代理的权限是子代理的权限，不能为自己铸造长期目标，编排器在波中也一样不能。这不等于要等"goal"这个词：当人交来一个长期目标（"把整张图跑完"）时，创建 goal *就是*被设计的行为，也是让 session 在波与波之间继续工作的东西。`edit` / `pause` / `resume` 受同样的限制；`complete` / `blocked` 在这个 goal 自己的轮次里也允许。一次 graph 运行正是这种情况：goal 驱动 session，`.graph_state.json` 记住布局——两件不同的东西，两个不同的计数器。

"实现"永远指节点子代理写代码。`/review-it` 和 `/ship-it` 是真实技能、可以调用——由编排器调用，每波一次。

命令里的 `<SKILL_DIR>` 在 `SKILL.md` 里定义了一次：本技能自己的目录（绝对路径）。DSH 在每次技能加载时前置一个资源块（`<skill_resources>` / `Base directory for this skill: <path>`），告诉你要把技能的相对路径解析到它上面。内置默认位置是 `~/.agents/skills/graph`。

## 分支与 worktree 布局

```bash
ROOT="$(git rev-parse --show-toplevel)"
# 默认分支不一定是 `main`。解析一次，下面所有地方都用 $BASE：
# 默认分支是 `master` 的仓库会让每一条假设相反的命令失败。
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
mkdir -p "$ROOT/.graph-worktrees"
WT="$ROOT/.graph-worktrees/node-{N}"
git worktree add -b feat/node-{N}-{slug} "$WT" "$BASE"
echo "$WT"      # 这个绝对路径进节点提示词
```

节点 commit 到 `feat/node-{N}-{slug}`。波把它们集成进从默认分支（`$BASE`）切出的 `wave-{K}-{slug}`，被评审与被交付的就是那条分支。用 `git worktree remove <abs path>` 删掉已完成的 worktree；失败的那个留着排查。

## 状态文件与 tracker

检查点放在仓库根目录，并且必须以 `.graph_state*` 被忽略——这是个模式，所以默认的 `.graph_state.json`、改名前的 `.graph_state`（仍会被读取）、按次运行的 `--state .graph_state-prd015`，以及临时的 `.tmp` 都被覆盖。在第一个波之前把这条忽略规则提交掉：它是已跟踪文件，所以未提交的改动会让第 4 步的泄漏检查把编排器自己标出来。它归规划器脚本所有——永远不要手写。它的 schema：

```json
{
  "version": 1,
  "updated_at": "2026-07-21T10:30:00Z",
  "task": "Add user auth",
  "repo": "owner/repo",
  "waves": [[1, 2], [3, 4], [5]],
  "current_wave": 1,
  "nodes": {
    "1": { "title": "db schema", "deps": [], "scope": ["internal/db"],
           "type": "backend", "criteria": [], "status": "shipped", "commit": "a7b2b8d" },
    "5": { "title": "integration", "deps": [3, 4], "status": "blocked", "error": "dep #3 failed" }
  }
}
```

状态：`pending | in_progress | shipped | failed | blocked | skipped`。`shipped` 和 `skipped` 是完成；`failed` 和 `blocked` 会拖住依赖者，但不会让一个波永远开着——编排器决定是重试、跳过还是停下。

随时渲染实时看板（它每 5 秒自刷新；一次 `present` 调用会让它重新出现在 DSH 里）：

```bash
python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state.json graph.html
```

恢复时：`python3 <SKILL_DIR>/scripts/graph_state.py show`，就 `failed` 节点问用户（重试还是跳过），然后从 `current_wave` 继续。

## 为什么评审与交付放在波级

- 逐节点的 `/review-it` 是**自审**：刚写完代码的 agent 带着同样的假设重读它，而且是在一个可能活不过集成的 diff 上。同样的 token 买到的信号，远少于让一个没写过它的人评审集成后的 diff。
- 逐节点的 `/ship-it` 意味着 **N 个 PR**：N 次 CI、N 次 merge，以及 N 次让 merge 冲突卡住一个本来已经完成的波的机会。一个波级 PR 把这三样都收敛成一次。
- harness 没有规定任何一种做法；这个位置是关于 token 和墙上时钟实际花在哪的判断，也是节点提示词止于 commit 的原因。

放在波级有真实成本，本技能是去偿还它们，而不是假装它们不存在：

- **一个 squash commit 埋掉 N 个功能**，所以回滚其中一个意味着手工回滚。这就是波级 PR 要带逐项证据表（commit、issue、证明测试）的原因——squash 之后，commit 是唯一剩下的把手。
- **一遍评审覆盖 N 个功能 diff 会稀释注意力。** 这就是第 4 步逐节评审、并把这一遍花在节点之间结合部的原因——那正是波级评审真正强于逐节点评审的地方。
- **一个卡住的节点会拖住整个波。** 这就是原地重试排在第一位、以及失败节点的依赖者一旦 `blocked` 就把该节点从波分支剔除的原因：兄弟节点按构造就是独立的，拖住它们什么也买不到。
- **波越大，爆炸半径越大。** 额外的并行买不到多少时，把波保持在 2–3 个节点；当每个功能都必须能独立回滚或评审时，逐节点 PR 仍然是正确的形状。
