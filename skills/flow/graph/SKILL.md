---
name: graph
description: "并行实现：**只在节点互不共享文件、彼此也没有依赖边时用**——共享文件、或 schema→API→UI 这种链交给 /loop-it；用时以脚本规划 DAG，每个波为每个节点在各自 git worktree 里派一个子代理，每波只评审与交付一次，波边界更新检查点与 graph.html 看板。Triggers: graph, graph engineering, build a graph, task graph, dependency graph, DAG, parallel implement, 并发实现, 并行实现, 任务图, 把任务变成图, 建图, 依赖图, fan-out, fan-out fan-in, superstep, dynamic workflow, 动态工作流."

---

# graph — DAG → 并行波

把一个任务（或 PRD / SPEC / issue 集合）变成一张有向无环的工作单元图，分层成波，然后让每个波里互相独立的节点并发实现：每个节点派一个全新子代理，各自一个 git worktree。波与波之间由 fan-in 屏障集成、评审并**只交付一次**。

**工作状态、证据层、三个 profile 的边界、产物落点见 [`../CONTRACT.md`](../CONTRACT.md)——本文件不复述。** 这里只写三件事：怎么拆节点、怎么跑波、fan-in 怎么收。

下文中的工具名与 `workflow` 脚本写法是 DSH 侧用法；在 Codex 下执行时，工具映射见 [`references/codex-runtime.md`](references/codex-runtime.md)，节点边界、检查点与 fan-in 契约不变。

本技能的两个产物——`.graph_state.json`（检查点）与 `graph.html`（看板）——落在**作用域根**；`.graph-worktrees/` 留在仓库根。下面命令里的相对路径都相对作用域根理解。

**这是指导，不是脚本。** 排序的算术——环检测、作用域冲突、波分层、检查点状态转换——属于 `scripts/graph_state.py`，它有测试。跑它、读它的输出；不要用散文重推分层。

## 何时调用

当工作里有**真并行**时才用它：两个及以上互不依赖、也不改同一段逻辑的单元。这就是全部价值所在——一个波只有在内部节点真独立时才回本。

不要在以下情况用它：

- 整个改动装得进一个上下文窗口——直接内联实现；
- 只有一个单元，或两个共享文件——直接派一个全新子代理，或用 `/loop-it`；
- 单元之间是分层的而不是独立的（schema → API → UI，每一步都在等上一步）——那是链，`/loop-it` 才是对的形状；
- 你会为了几个工具调用就能内联做完的事去开一个节点。每个子代理整个生命周期都要付父级的完整提示词、工具 schema 和技能目录（成本形态见 [`references/dsh-runtime.md`](references/dsh-runtime.md)），所以一个琐碎节点花的远多于它省的。

**判形态先于跑脚本。** 上面这几条**读输入就能判**——单元数、单元之间是不是分层、有没有共享文件。所以先判；判下来命中任一条就**直接转 `/loop-it`，不要跑 `plan`**。

原因是有副作用的：`plan` 一写检查点就**自动渲染 `graph.html`**（这是刻意的，见「看板」——刷新挂在写入上，才不会有过期看板）。于是**没建图也会留下 `.graph_state.json` 和 `graph.html`**。真的跑过 `plan` 才发现该转的，把这两个文件删掉：它们是派生物，不是成果。

## 契约：三个作用域

| 作用域 | 做什么 | 不做什么 |
|-------|------|----------|
| **节点** | 实现、用项目门禁自证、在自己的分支上 commit | push、开 PR、merge、自审 |
| **波** | 泄漏检查、evidence 检查、集成、在集成后的树上跑门禁、**评审一次**、**交付一次** | — |
| **run** | 最终总结、收口 tracker、重规划剩余工作 | — |

**评审与交付刻意放在波级。** 逐节点的 `/review-it` 是对一个可能活不过集成的 diff 的自审；逐节点的 `/ship-it` 意味着 N 个 PR、N 次 CI、N 次卡在 merge 冲突上的机会。**走查件、PR body 与合并清单都归 `/ship-it`**——它是唯一产出者，走查件提供证据、body 采用它，而不是两份 body。用户明确要求每个节点一个可评审的 PR 时，逐节点 PR 仍然可用——那是昂贵模式；用之前先说清楚并确认。完整的成本明细见 [`references/dsh-runtime.md`](references/dsh-runtime.md)。

**每个节点在 fan-in 时仍然要过一次 evidence 检查**（第 4 步第 1 项）。那不是代码评审：它问的是每条验收条件能否指向一次实际观测，且要发生在节点分支被接进波之前。在那里抓住「声称做完了、却没有 evidence」远比 merge 之后才抓住便宜。

## 第 1 步：拆成节点

接受一个自由形式的任务、一份 PRD/SPEC，或一个已有的 issue 集合。复用 `/to-issues` 的规则：**一条能独立验证的切片一个节点**，大切片拆开，小切片合并，给每个节点真实的验收条件。

写一个节点文件——这是规划器唯一的输入。**字段、示例，以及 `criteria` / `context` / `hot_files` 各自为什么必须写，见 [`references/planning.md`](references/planning.md)。** 一句话概括：

- `scope` 是节点预期改动的文件/目录集合——规划器靠它发现两个无依赖节点其实并不独立。
- `criteria` 是节点的验收清单，原样抄进子代理的提示词；**只活在检查点里的验收条件会在下次 `plan` 时消失**。
- `context` 是编排器给子代理的简报（每个依赖一到两行）——子代理读不到前面节点的对话，这是图唯一的通道。
- `hot_files` 是节点**会**碰、但必须留在 `scope` **之外**的共享接线文件（router、`main`、路由表、DI 容器、type union）。把它们列进 `scope` 会把整张图串行化成一条链；规划器只在同一个波里两个节点声明了同一个 hot file 时告警——那说明「只追加的改动能干净合并」这个前提不成立。

## 第 2 步：规划

`<SKILL_DIR>` 是本技能自己的目录（绝对路径）——从加载本技能时 harness 报告的路径解析。内置默认位置是 `~/.agents/skills/graph`。

```bash
python3 <SKILL_DIR>/scripts/graph_state.py plan --nodes nodes.json --max-parallel 4
```

规划器做校验（环是致命的，幻影边和自环边会被丢弃并告警）、把波分层到依赖与不相交作用域同时成立、写 `.graph_state.json`，并打印计划、一张 Mermaid 图和当前波的派发清单。同一个波里两个节点声明了同一个 hot file 时它也会告警。`--nodes` 只在一张图的**第一次**规划时需要；之后规划器直接从检查点重新分层。

**运行中重规划会保留已交付的东西。** `--keep-shipped` 让活下来的 id 保留 `status` / `branch` / `commit` 和错误历史；**一旦有东西交付了就配上 `--only-pending`**，否则已交付节点仍然占着它们的文件，把整条尾巴静默压成每波一个节点。**只要上次规划后又有节点交付，就在下一个波之前重规划——最宽的布局不是开跑时算出来的那个。** 两个旗标与 `--max-parallel` 的完整行为见 [`references/planning.md`](references/planning.md)。

**worktree 故意放在仓库里面**（`$ROOT/.graph-worktrees/`）：DSH 的 `workspace-write` 沙箱拒绝往 session 工作目录之外写，放在仓库旁边会以一个读起来不像路径问题的沙箱拒绝失败。检查点、节点文件与看板一起挡在 git 之外，**并在第一个波之前把忽略规则提交掉**——第 4 步的泄漏检查要一个干净的共享检出，未提交的 `.gitignore` 改动会让编排器把自己标成泄漏：

```bash
grep -qxF '.graph_state*' .gitignore || printf 'nodes*.json\n.graph_state*\ngraph*.html\n.graph-worktrees/\n' >> .gitignore
```

把计划给用户看，让他们在任何子代理启动**之前**调整节点、边或并发上限。

**`graph.html` 是最后一个检查点的快照**：状态在渲染时被内联，而 `plan` / `set` 每次写入都会在旁边重新渲染它——所以没有会忘掉的手工步骤，页面每 5 秒自刷新。只有当你想把看板放到别处、或要确认一次报告失败的刷新时，才手动跑渲染命令。**一块静默显示旧工作的看板比没有看板更糟**，因为用户相信它。细节见 [`references/planning.md`](references/planning.md)。

## 第 3 步：跑一个波

**预检，只在第一次 fan-out 之前做一次**（与 `/loop-it` 同一精神；任何硬失败都终止这次运行）：

```bash
git rev-parse --is-inside-work-tree   # 在仓库里吗？
git status --porcelain                # 工作树干净吗？（脏 → stash 或中止）
git branch --show-current             # 在默认分支上吗？
git ls-remote --heads origin          # 远程可达吗？（波要交付到 GitHub 时还要 gh auth status）
```

对每个波，为每个节点创建一个 worktree，记下每个**绝对**路径（分支布局与解析默认分支的命令见 [`references/dsh-runtime.md`](references/dsh-runtime.md)）。**在派发之前，把这个波里每个节点标成 `in_progress`**——没有别的东西写这个状态，而看板是用户唯一的进度信号：

```bash
python3 <SKILL_DIR>/scripts/graph_state.py set --node {N} --status in_progress [--branch {real-branch}]
```

每份提示词都是自包含的——全新子代理看不到这段对话。**从检查点渲染它，而不是手写**：

```bash
python3 <SKILL_DIR>/scripts/graph_state.py prompt --node {N}
```

它直接从 `.graph_state.json` 填进 worktree 路径、分支、标题、类型、作用域、hot files 和验收条件，并打印它命名的那条分支的 `git worktree add` 行。**分支是检查点的，不是脚本的：** 节点记录了 `branch` 就原样使用；只有未记录的节点才从标题派生名字，这时头部会说明名字是派生的、且该分支还不存在。还有两件事留给你：**依赖摘要**（没有脚本能知道更早的节点实际产出了什么）和 issue 正文补充的任何内容。发出之前读一遍渲染出来的提示词：生成器消掉的是抄写错误，不是判断。模板与占位符填法见 [`references/node-prompt.md`](references/node-prompt.md)。

一次部署可以裁掉节点子代理的工具——节点不需要技能，因为节点提示词已经带着它的全部契约。可选的瘦身委派成本杠杆在 [`references/lean-subagent.md`](references/lean-subagent.md)。

### 派发这个波

把每份渲染好的提示词交给**每个波一次 `workflow` 调用**，而不是打出一把裸 `subagent` 调用：`agent({ schema })` 是 DSH 里唯一能从子代理返回**校验过的**对象的路径，并发上限由引擎——不是模型——持有。

**两个 schema 细节是承重的**，两个都要花一个波才能艰难发现：`enum` 旁边需要一个显式的 `type`（裸的 `{ enum: [...] }` 会被当作超出受支持子集而拒绝，整个脚本随之死掉），以及**`summary` 是放散文的地方**——结构化子代理会被运行时要求以工具调用收尾，而*不是*以纯文本回答收尾，所以六个机械键承载不了的东西必须有自己的键，否则就丢了。脚本全文见 [`references/node-prompt.md`](references/node-prompt.md)。

那次调用的三个性质决定了这个波剩下的部分怎么写：

- **失败的节点以 `null` 回来。** `parallel` 把逐项失败降级为 `null` 并保住其余结果，所以返回值每个节点总有一个槽位；`null` 槽位是一个要重试（第 5 步）或标记 `failed` 的节点。钩子误用——坏选项、触顶的上限——则会抛出并杀死脚本，这正是你要的：它说明派发本身错了，不是节点错了。
- **schema 不匹配也是 `null`**：一个没产出对象就结束的子代理，与一个失败的子代理无法区分，需要同样的处理。
- **没有整体超时。** 卡住的波不会过期：把 workflow 放到后台跑，它不动了就 `job_kill` 它。这是引擎级并发上限的代价，也是检查点仍然归编排器所有的原因。

返回的对象是节点的**自述**。它直接誊进检查点，这就是校验它值得这次调用的原因——但它**不是 evidence**。泄漏检查、对它所声称 `files` 的 diffstat、以及集成后的门禁，才是验证这个波的东西。一份 `files` 清单与自己的 diffstat 不符的报告是最便宜的捕获，而它只有在你比较而不是信任时才起作用。

**子代理没有自己的 cwd**：文件工具把相对路径解析到**编排器**的检出，而每次 shell 调用都是全新 shell。两者正是 worktree 路径要以绝对路径传入、且每条命令都以 worktree 为工作目录运行（`cd <abs worktree> && …`）的原因。陷阱细节见 [`references/dsh-runtime.md`](references/dsh-runtime.md)。

不要轮询正在跑的波。`workflow` 调用在整个波完成时返回；你自己起的裸 `subagent` 则以一条通知结算——**审计你起的子代理**，看谁还在跑。

**但那条通知只在交互式会话里会来。** headless 里回合结束就是运行结束，所以**凡是「要拿到它的结果才能继续」的裸 `subagent`，都传 `run_in_background: false`**——否则你会以「等它返回」结束回合（`turn_end: completed`），被派出去的那个节点连同它后面的 fan-in 一起消失。波级派发用 `workflow` 就是为了避开这件事：它自己 await 全部 thunk。

## 第 4 步：fan-in——屏障、集成、评审、交付

屏障是**每个**节点的子代理都已结算。然后按顺序：

**只有一个节点的波没有东西可集成。** 跳过波分支和合并仪式——直接拿该节点分支对默认分支（`$BASE`）评审与交付。波存在的意义是合并多个节点；只有一个节点时它纯属仪式。

1. **泄漏检查、evidence 检查，然后记录。** 节点被接进波之前有两道门禁。

   *泄漏检查。* 共享检出上的 `git status --porcelain` 必须是干净的，且每个节点的文件只能存在于它自己的分支上——这就是绝对路径纪律守住了的证据。（属于*另一个* session 的未跟踪文件不是泄漏；被修改的*已跟踪*文件是。）这正是第 2 步要提前提交忽略规则的原因。

   *evidence 检查。* 走一遍节点的验收条件，逐条问哪一次实际观测证明了它——跑过的门禁、命令的输出、一个页面、一次查询。节点自己的报告不是 evidence，所以拿它和 diffstat、和你真正能看到的门禁对照。背后什么都没有的验收条件意味着该节点**不是** `shipped`：原地重试（第 5 步）或标成 `failed`。判 evidence，不判 diff 观感；节点明显落在模型可靠范围内就保持检查便宜，越靠近边界越往下钻。任何发现都必须具体到不用再查就能动手——`file:line` + 根因 + 该改成什么；「建议补测试」不算发现。

   然后用规划器记下结果，**包括节点实际工作的那条分支**和**节点自己的报告**——下游的一切（合并清单、之后的重规划、渲染出的提示词）都从检查点读它，所以未记录的分支会回退成从标题派生的名字，未记录的报告会让这个波完全没有 evidence：workflow 调用返回的是唯一一份副本，而一旦那一步结束，会话记录就不是任何人会去审计的地方。命令形态见 [`references/planning.md`](references/planning.md)。

2. **集成并验证组合，而不是各部分。** 只合并 `shipped` 的节点——`failed` 节点的分支永不合并：

   ```bash
   git checkout "$BASE"
   git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull   # 只有配了 upstream 才 pull
   git checkout -b wave-{K}-{slug}              # 波里只有一个节点时跳过
   git merge --no-ff feat/node-{N}-{slug}      # 每个 shipped 节点一次，用各自记录的分支
   <the project's gates>                        # 例如 ./run_all.sh，在集成后的树上跑
   ```

   每个节点单独通过、集成却失败，是正常结果。就在这里、在这个波里修。如果有节点失败，见第 5 步——只要波里没有东西依赖那次失败，其余部分照常交付。

3. **评审这个波一次，逐节点过。** 目标是 `git diff "$BASE"...wave-{K}-{slug}`（或单节点的分支）。把它当作**每个节点一节**、按计划顺序读，对*结合部*——共享接口、装配/初始化文件、两个节点都碰的配置与状态——比对节点内部投入更多注意力：那是逐节点评审在结构上看不见的一类缺陷。编排器在 diff 小的时候内联读它——它本来就持有上下文，是最便宜的读者——在 diff 大或独立性更重要时交给**一个**全新子代理。逐节套用 `/review-it` 的 Review Focus，修掉被接受的，重跑门禁。逐节点的 evidence 已在第 1 项检查过，所以这一遍花在结合部上。**两件事不要做**：跳过这一遍（结合部缺陷在结构上只有这里看得见），或让某一个功能的小节吞掉整遍（下一个波会照着被你放过的接口继续建）。

4. **写走查件，然后把这个波交付一次。** 对集成后的 diff 走 **`/ship-it`**——它先写走查件（改了什么、你跑了什么、它打印了什么、演示路径的可视化证据、风险点和人工验收状态），再由它开一个 commit/PR——**到此为止：合入归 [`/merge-it`](../merge-it/SKILL.md)，那一份只有人能敲**。走查件只提供 evidence；**PR body 与合并清单是同一处的产出**，只产出一次。一个 squash commit 埋掉 N 个功能，所以那份 body 必须带上逐项证据表（commit、issue、证明它的测试、人工验收状态）——没有它，你或用户之后都无法审计或回滚单个功能。

5. **更新看板——无条件。** `set` 已经写下了每个节点的结果，包括波的最后一个节点，所以检查点是最新的。仍然重新渲染：渲染结果才是用户真正看的东西，而一次静默失败的 `set`、一个自定义 `--state`、或一次带外编辑，会让文件和页面对不上。

   ```bash
   python3 <SKILL_DIR>/scripts/render_graph_html.py .graph_state.json graph.html
   ```

   重新渲染是每个波的收尾动作，不是规划时的一次性动作：页面是快照，跳过它用户就会一直读到上一个波，直到他们碰巧来问。（用自定义 `--state` 时，把这里和本技能每条命令里的名字换掉。）看板从节点状态推导出仍在进行中的波，所以没有单独的 `current_wave` 要写。

6. 删掉已完成的 worktree（失败的留着）。
7. **重规划。** 读每个节点的 `NEW_WORK:` 行；只要有一个不是 `none`，就加上这些节点，并在下一个波之前用 `--keep-shipped --only-pending` 把剩余工作重新分层。把变化给用户看。

## 第 5 步：节点失败时

先原地重试——用一条点名失败点和要修什么的追加消息**让那个子代理继续**：它复用节点自己的上下文，而不必再付一个全新子代理。再失败就保留它的 worktree，标成 `failed`，并把每个依赖它的节点标成 `blocked`（规划器会打印出来）。复用 `/loop-it` 在 [`../loop-it/references/error-recovery.md`](../loop-it/references/error-recovery.md) 里的错误类别，不要另发明一套。

**一个波不是全有或全无。** 失败节点的依赖者一旦 `blocked`，就把那个节点从波分支里剔除并交付其余部分——它的兄弟节点按构造就是独立的，让它们等一次重规划什么也买不到。永不合并失败的分支，也永不为了维持波的推进而把它标成 `shipped`。按顺序给用户这架梯子：原地重试、换新节点重试、然后剔除。

## 边界

- **worktree 隔离是强制的**——两个节点在同一个检出里实现会互相破坏。**节点内必须用绝对路径**——失败模式是静默的，且会毁掉一个波。
- **每次合并前做泄漏检查**——共享检出里被修改的*已跟踪*文件意味着某个节点逃出了它的 worktree；来自另一个 session 的未跟踪文件不是泄漏。
- **每波一次评审、一次交付**——逐节点评审是自审；逐节点 PR 是昂贵模式。**永不 force-push 默认分支**：节点 commit 到自己的分支，波交付一个 PR。
- **节点是叶子**——depth 预算为 1，节点不得再派自己的子代理。
- **限制并发**（默认 3–4），**优先 2–3 个节点的波**，并**让子代理数量诚实**——一个波是一次坏集成的爆炸半径，所以琐碎的事内联做。
- **第一次 fan-out 之前确认计划**，并让 `.graph_state.json` + `graph.html` 保持最新。

## 失败怎么办

| 场景 | 处理 |
|---|---|
| 节点报告 `shipped`，但集成后的门禁失败 | 以集成为准——节点测的是它的 worktree，不是组合；就地修 |
| 节点以 `null` 回来（失败，或没产出有效对象） | 原地重试；再失败就标 `failed` 并把依赖者标 `blocked` |
| 某个节点必须挪动 / 图长大了 | `plan --keep-shipped --only-pending` 重规划，把变化给用户看 |
| 崩溃或换 session | `graph_state.py show`；用同一个节点文件 `plan --keep-shipped --only-pending` 重新分层，别动 `shipped`/`skipped`，重试每个 `failed` 之前先问用户 |
| 派发时忘了标 `in_progress` | 立刻补——一个做到一半的波读起来像没动过 |
| 逐节点跑了 `/review-it` 或 `/ship-it` | 停：每波只评审与交付一次 |

## References

- [`references/planning.md`](references/planning.md) — 节点文件字段、规划器旗标（`--keep-shipped` / `--only-pending` / `--max-parallel`）、忽略规则与看板、状态机谁写哪个状态、常见错误表。
- [`references/dsh-runtime.md`](references/dsh-runtime.md) — DSH 的委派机制、两个工作目录陷阱、depth/并发/成本、分支布局、状态 schema，以及为什么评审与交付放在波级。
- [`references/codex-runtime.md`](references/codex-runtime.md) — Codex 下的独立子代理、worktree 路径、波屏障与 fan-in 映射。
- [`references/node-prompt.md`](references/node-prompt.md) — 节点提示词模板、怎么填、`workflow` 派发脚本、怎么读节点的报告。
- [`references/lean-subagent.md`](references/lean-subagent.md) — 仅 DSH 的部署补丁，去掉节点子代理的技能目录（可选成本杠杆），附注意事项。
- `scripts/graph_state.py`（`plan` / `set` / `prompt` / `show`）——校验、分层、检查点，以及由它们渲染出的节点提示词。`set --branch` 记录节点实际所在；`prompt` 优先用它而不是从标题派生的名字。
- `scripts/render_graph_html.py [state.json] [graph.html]` — 渲染 `graph.html` 看板；`--state` / `--out` 命名同样这两个值。`plan` / `set` 每次写入都调用它。
- `scripts/test_graph_state.py` / `scripts/test_render_graph_html.py` — 规划器与渲染器的自测；改动之后跑一遍。
