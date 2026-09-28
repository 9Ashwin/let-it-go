# to-issues

## What it does

把 PRD / SPEC 拆成一批**垂直切片**、写清真实阻塞边的 issue，再创建到 GitHub 或本地。

它的关键事实是：**issue 正文就是契约本身**——`Goal` / `Non-goals` / `Demo path` /
`Acceptance Criteria` / `Evidence required` / `External boundary` / `Definition of done` /
`Human checkpoint` / `Open questions` / `Blocked by` / `Priority` 全在里面，一个不共享这段对话的
全新子代理拿起来就能照它行事。所以切片按「一次观测能验完什么」切，不按层、也不按页面切；契约只有
一个载体，它不碰检查点、不开 worktree、不写长文档。

## When to reach for it

**调用方式：** 你敲 `/to-issues`，或者模型在任务对得上时自己伸手（没有 `disable-model-invocation`）。

该伸手的场合：

- 手上有 PRD / SPEC / 成形需求，要拆成多条能分别实现、分别演示的卡片。
- 只有一句诉求、落地方案还要自己定 → 先 `/prd` 或 `/to-design`，再回来。
- 一次改动装得进一个上下文 → 不用它，直接内联做完（要长跑就在顶层 `create_goal`）。

与近邻的分界：

| 你其实想要 | 该用哪个 |
|---|---|
| 「要什么」还没定 | [`/prd`](../../skills/flow/prd/SKILL.md) |
| 「为什么这么选」要留档 | [`/to-design`](../../skills/flow/to-design/SKILL.md) |
| 拆卡、写阻塞边 | `/to-issues`（「拆」是它的动词） |
| 把拆好的卡做出来 | [`/loop-it`](../../skills/flow/loop-it/SKILL.md) 或 `/graph` |

## Common questions

**怎么算切对了？**
检验只有一句：「做完这个我能演示什么？」答案是一个行为（「用户能设置任务优先级并看到它持久化」）
就对了；答案是一层（「数据库多了个 priority 列」）就重切。按页面切会把同一套观测重复四遍。

**要拆几张卡？**
杠杆是**验收条件的条数，不是卡数**。一个 CRUD 后台这种量级 3 张够；往上加之前先问：这张卡有没有
自己的失败模式？没有就并进上一张。想少写测试，杠杆也在验收条件上——实测的斜率是测试行数
≈ 验收条件数 × 29，把卡数减半不会让每条变便宜。

**它会不会问我要建到 GitHub 还是本地？**
不会，它自己判并说明依据：有 `origin` 且 `gh auth status` 通过 → GitHub；否则 → 本地文件。这是
仓库里读得到的事实，不是问句。

**拆完就停下来等我吗？**
不会。报告完按形态直接进 `/loop-it` 或 `/graph`。唯一的例外是**真往远端建 issue 之前**——建出去
再撤要费手脚，所以先把清单摆出来；写本地文件没有这个问题。

**大范围机械重构（重命名一列、改共享符号的类型）怎么拆？**
任何垂直切片都落不了绿时按 **expand → migrate → contract** 排序：先加新形式、再分批迁调用点、
最后删旧形式；批次自己保不住绿，就让它们共用一个集成分支并全部阻塞最后一条 integrate-and-verify。

## It's working if

- 每条 issue 的 demo 答案是一个行为，不是一层。
- 清单是编号的，每条带一行真实 `Blocked by`，排最前的那条没有阻塞。
- 每条卡能用**一次观测**验完，没有哪两条在重复同一套观测。
- 正文里没有文件路径或行号。
- 每条验收条件在基线 commit 上会失败（起点是红的）。
- 本地模式下没有停在「等你回复」的回合；远端模式只在创建前摆一次清单。
