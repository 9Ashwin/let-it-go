# 规划、状态与排障

按需加载：正常路径走 `SKILL.md` 的三步即可；要写节点文件、用重规划旗标、改忽略规则、
或排查一个跑歪的波时读这份。

## 节点文件

规划器唯一的输入。`scope` 是节点预期改动的文件/目录的逗号分隔集合——规划器靠它发现两个无依赖节点
其实并不独立。

```json
{
  "task": "Add user auth",
  "repo": "owner/repo",
  "nodes": [
    {"id": 1, "title": "db schema", "deps": [], "scope": "internal/db",
     "type": "backend", "criteria": ["migration applies on a fresh database"]},
    {"id": 2, "title": "API handler", "deps": [1], "scope": "internal/api", "type": "backend"}
  ]
}
```

- **`criteria`** 是节点的验收清单，会原样抄进子代理的提示词。无论是否重规划它都能活下来——没有节点文件时
  检查点整体往返，有节点文件时规划器逐字段回退到检查点——但还是写在这里。这个文件是人工撰写的记录，
  说明每个节点该做什么，也是图被改动时你要读的那份；**一条只活在检查点里的验收条件曾在下次 `plan` 时消失**，
  然后子代理被告知「从 issue 里把它们写出来」。
- **`context`** 是编排器给子代理的简报：每个依赖一到两行——它加了什么、加在哪、以及本节点必须知道的任何事。
  子代理读不到前面节点的对话，所以这是图唯一的通道；不写它，被派发的节点就会从重新推导图已经知道的事实开始。
  写在这里，而不是粘进提示词的临时副本——下次派发会静默丢掉那份副本。
- **`hot_files`** 是相反的一份清单：节点**会**碰、但必须留在 `scope` **之外**的共享*接线*文件（一个 router、
  一个 `main`、一张路由表、一个 DI 容器、一个 type union），因为把它们列进 `scope` 会把整张图串行化成一条链。
  规划器不会因它们而串行——它只在同一个波里两个节点声明了同一个 hot file 时告警。

  这条告警存在，是因为「只追加的改动能干净合并」有个前提，前提是**每个节点只改自己的区域**。两个节点往同一个
  import 块里追加、写同一张路由表、或扩展同一个 type union，都不是只追加，它们会在集成时冲突——那不是 merge
  事故，那就是这次改动的形状。告警触发时，要么把这些节点串行到不同的波里，要么让一个节点拥有该文件、其余节点
  为它暴露一个注册钩子。把一个并非只追加的文件当作只追加，就是一个波把同一个冲突解三遍的原因。

## 规划器旗标

`--nodes` 只在一张图的**第一次**规划时需要。之后不再传它，规划器会直接从检查点重新分层：节点表已经带有
`plan` 会读的每一个声明式字段（title、deps、scope、hot_files、type、criteria、context，以及任何已记录的
分支），所以只有在图本身变化时——新增节点、移动依赖——才需要节点文件。这一点重要，是因为节点文件是进了
`.gitignore` 的临时输入，弄丢它曾让重规划在最值得重规划的时刻变得不可能。

**`--keep-shipped`：运行中重规划会保留已交付的东西。** 当某个节点其实已经满足、某个节点必须挪动、或图长大了时
加上它：活下来的每个 id 都保留它的 `status`、`branch`、`commit` 和错误历史，只有新 id 从 pending 开始，
你删掉的 id 会被报告而不是静默丢弃。不加这个旗标，重规划会把一切重置为 pending，所以过去重规划就意味着手工
把已交付节点重新记一遍。

**`--only-pending`：一旦有东西交付了就配上它。** 分层管的是同一时间跑什么，几周前就交付的节点不可能和任何东西
冲突——但默认它仍然占着它的文件，于是之后每个碰这些文件的节点都被推进一个只属于自己的波。在一张已经跑了大半的
图上，这会把整条尾巴静默压成每波一个节点。`--only-pending` 释放 `shipped`/`skipped` 节点的作用域，保留
`in_progress` 节点的——后者此刻正在跑：一个与它们共享文件的 pending 节点会被排到它们后面，否则两条依赖链中
较短的那条决定顺序，pending 节点就被派发进一个子代理正在编辑的文件里。两个旗标一起用——`--keep-shipped` 负责
把结果放进检查点供 `--only-pending` 读取。**只要上次规划后又有节点交付，就在下一个波之前重规划；最宽的布局不是
开跑时算出来的那个。**

`--max-parallel` 会写进检查点（`max_parallel`），所以之后省略该旗标的重规划会复用它，而不是静默重新分层；
改变它的重规划会明说。节点文件出于同样的理由可以带 `"max_parallel": 4`——上限塑造布局，而一个没人能复现的
布局就是没人能检查的布局。

## 忽略规则与 worktree 位置

把计划输入和它产出的检查点一起挡在 git 之外：

```bash
grep -qxF '.graph_state*' .gitignore || printf 'nodes*.json\n.graph_state*\ngraph*.html\n.graph-worktrees/\n' >> .gitignore
```

然后**在第一个波之前把这条忽略规则提交掉**。第 4 步的泄漏检查要一个干净的共享检出，而未提交的 `.gitignore`
改动会让编排器把自己标成泄漏。（如果你不想提交一条忽略规则，就把同样几行写进未被跟踪的 `.git/info/exclude`。）

**worktree 故意放在仓库里面。** 在 DSH 的 `workspace-write` 沙箱下，往 session 工作目录之外写会被拒绝，
所以放在仓库旁边的 worktree 根（`$(dirname "$ROOT")/…`）会以一个读起来不像路径问题的沙箱拒绝失败。
`$ROOT/.graph-worktrees/` 在任何模式下都在沙箱内，这就是上面的忽略规则覆盖它的原因。

这三个模式故意都是通配符，合起来覆盖每一次运行：

- `nodes*.json` —— 规划器输入
- `.graph_state*` —— 检查点。默认的 `.graph_state.json`、改名前的 `.graph_state`（**仍然会被读取**，
  所以一张在飞的图能保住进度并在下次写入时迁移）、按次运行的 `--state .graph_state-prd015`，
  以及临时的 `<path>.tmp`
- `graph*.html` —— 看板

因为它们是通配符，第二次运行不额外花钱：给它 `--state .graph_state-prd015`，把输入输出命名为
`nodes-prd015.json` / `graph-prd015.html`。代价是产物必须保持这三个前缀之一——前缀之外的命名需要自己单独一行，
而这些模式存在的意义就是消掉这种反复。第一次写入之后跑 `git status --porcelain` 是「没有东西漏过去」的检查。

## 看板

`graph.html` 是**最后一个检查点的快照**：状态在渲染时被内联，而 `plan` / `set` 每次写入都会在检查点旁边重新
渲染它——所以没有会忘掉的手工步骤。页面每 5 秒自刷新，开着的标签页会跟上那些写入；它无法展示的是两次写入之间
的工作。只有当你想把看板放到别处、或要确认一次报告失败的刷新时，才手动跑渲染命令：

```bash
python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state.json graph.html
```

**一块静默显示旧工作的看板比没有看板更糟**，因为用户相信它。这就是重新渲染挂在写入上、而不是挂在收波上的原因：
过去这个义务挂在收波上，工作一旦不再是波——加节点、提 issue、部署——看板就停在八小时前的旧状态。

## 状态机：哪个动作写哪个状态

`.graph_state.json` 是检查点；`graph.html` 是它的派生视图——**永远不要手改 HTML**，要重新生成。环、作用域冲突
和波分层都是算出来的；状态转换归你。schema 在 [`dsh-runtime.md`](dsh-runtime.md) 里。

| status | 何时写 | 由谁 |
|--------|--------------|-----|
| `pending` | 节点被分层时 | `plan` |
| `in_progress` | **在**节点子代理被派发之前 | 你 |
| `shipped` | 它的分支通过了泄漏检查并进入这个波的合并清单 | 你 |
| `failed` | 它耗尽了重试梯子（SKILL 第 5 步） | 你 |
| `blocked` | 某个依赖失败了；规划器打印清单 | 你 |
| `skipped` | 在一次重规划中被移出图 | 你 |

只有 `plan` 和 `set` 写检查点，且各自都会在它旁边重新渲染 `graph.html`。所以看板有多诚实，完全取决于那些
`set` 调用：跳过它们，图照样跑、代码照样落地，而看板在这期间静默说谎。派发时就标 `in_progress`，
不要等子代理返回——那样一个做到一半的波读起来像没动过。

**记录节点结果时把报告一起记进去**，下游的一切都从检查点读它，未记录的报告会让这个波完全没有 evidence
（workflow 调用返回的是唯一一份副本）：

```bash
python3 <SKILL_DIR>/scripts/graph_state.py set --node {N} --status shipped --commit {sha} \
  --branch {branch} \
  --files "{comma-separated files from the report}" \
  --gates "{the commands it ran and their exit codes}" \
  --summary "{what it did and what surprised it}" \
  --new-work "{what it found that the graph does not capture, or none}"
```

标记节点 `shipped` 却没有 `files` / `gates` / `summary` 会告警，因为那一行等于说节点完成了、却没说是什么证明了它
——而 `files` 正是第 3 步的 diffstat 要对照的东西。

## 常见错误

| 错误 | 修法 |
|---------|-----|
| 在多个响应里分别派发这个波的子代理 | 一个响应、每节点一次调用——分开的响应会让它们一个接一个跑。 |
| 派发时没有把节点标成 `in_progress` | 每个子代理启动前 `set --status in_progress`。 |
| 只在规划时渲染看板 | 每次收波都重新渲染（SKILL 第 4 步）。 |
| 在共享检出里改代码，而不是节点自己的 worktree | 每节点一个 `git worktree`，把它的绝对路径写进提示词。 |
| 两个无依赖节点改同一段逻辑 | 把这个文件列进两个节点的 `scope`，让规划器把它们串行；共享接线放进 `hot_files`。 |
| 在每个子代理结算前就开始下一个波 | fan-in 屏障是强制的。 |
| 为了维持波的推进而合并 `failed` 节点的分支 | 永不；把它的依赖者标成 `blocked`，交付其余部分。 |
| 逐节点跑 `/review-it` 或 `/ship-it` | 每波只评审与交付一次；逐节点 PR 只在用户要求时做。 |
| 过度拆分成琐碎节点 | 合并小单元——一个节点必须值一个子代理的整份提示词。 |
