# loop-it

## What it does

实现这一步的入口：一个单元就内联做完，一批有真实阻塞边的 issue 就串行循环（带检查点与恢复）。

它进来先判**形态**，不默认开循环：装得进一个上下文的单单元走**零仪式**——不碰 `.loop-state.json`、
不建 worktree、不开 graph 波次、不写走查件、不合入；只有多条有真实阻塞边的 issue 才开那台机器
（一条需求分支 + 每卡一个 commit + 每卡门禁，批末一次评审、一次交付）。判据是形态，不是规模感；
而且「装得进一个上下文」不等于「定义好了」：只有一句诉求、落地方案还要自己定时，先走
[`/prd`](../../skills/flow/prd/SKILL.md) → [`/to-issues`](../../skills/flow/to-issues/SKILL.md)。
工作状态、三个 profile、证据层的完整定义见 [`../../skills/flow/loop-it/CONTRACT.md`](../../skills/flow/loop-it/CONTRACT.md)。

## When to reach for it

**调用方式：** 你敲 `/loop-it`，或者模型在任务对得上时自己伸手（没有 `disable-model-invocation`）。

该伸手的场合：

- 手上有**别人写好的验收条件**——一条 issue 卡、spec 里的一项、一份 PRD——要落地实现。
- 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复。

与近邻的分界：

| 形态 | 交给谁 |
|---|---|
| 一个单元（一条卡 / spec 里的一项） | `/loop-it` 单单元，内联做完 |
| 一批有真实阻塞边的 issue | `/loop-it` 串行循环（默认路径） |
| 节点之间真并行（互不共享文件、能各自 worktree 隔离） | `/graph` |
| 有依赖但部分分支可并行 | `/graph`——这里只做纯串行批次 |
| 只有一句诉求、落地方案自己定 | 先 `/prd` → `/to-issues` |
| 已经开到 PR、要合入 | [`/merge-it`](../../skills/flow/merge-it/SKILL.md)——**只有人能敲** |

## Common questions

**我的仓库没有远端，这套还能跑吗？**
能。纯本地仓库跳过 `gh auth status` 与远端可达两条前置检查，批处理模型一字不变，只是没有 push
与 PR，批末交付落在仓库里的需求资料。实测过一次：一条本地-only 的运行自己把批次模型重新推了
一遍才跑通——它本来就不需要那么多假设。判据在仓库里读得到（有没有 `origin`、`gh` 通不通），
不是问句。

**一条 issue 也要建检查点、开 worktree 吗？**
不。单单元路径上出现 `.loop-state.json`、worktree 登记或 `workflow` 调用就是错的，`evals` 用机械
断言守着这一条。一条 issue 但改动大到装不进一个上下文 → 那不是单单元，先拆开再进批次。

**它会不会停下来等我回 OK？**
不会，落盘即视为可用。但有一种真实的停法要认出来：**把要等结论的子代理派成后台**——后台子代理
不让本回合保持忙碌，以「等它返回」结束回合就是 `turn_end: completed`，无人值守时整个运行到此为
止。实测停在 8/9，唯一没过的断言正是它自己承诺的「收到结论后继续批末收尾」。要拿到结论才能往下
走时传 `run_in_background: false`。

**卡住的 issue 会重试到天荒地老吗？**
不会。两条红线：不无限重试，不 force-push。错误先分类再按上限重试，重试耗尽就记成 `failed` 并
继续下一项。`failed` 的 issue 一律挪到 `feat/issue-N-slug` 上留档，需求分支上不留它——触发条件是
**状态**，不是「打回 / 重做」这两个词。

**我需要自己敲 `/goal` 吗？**
不用。面向模型的那一半是 `create_goal` / `update_goal`，模型自己就能开（门禁是「当前回合里有人类
消息」+「调用者是顶层 agent」），子代理开不了。批末记得 `complete`——不显式关掉会一直烧到轮数
上限。

**批末的评审和交付要做几次？**
各一次，不是每个 issue 一次。评审强度按这张卡碰不碰危险面选；不碰就只做批末那一次，且必须是对抗
性的。逐 issue 开 PR 是这条流水线明确排除的。

## It's working if

- 单单元的活跑完，仓库里没有 `.loop-state.json`，也没有 worktree。
- 整批只开一条需求分支，每个 issue 一个 commit，message 里没有 issue 编号。
- 批末的评审与交付各只发生一次。
- 检查点里的每条 evidence 都带 L1–L4 的层，不是只写「测试通过」。
- 没有以「等你回复」结束的回合；要等结论的子代理是前台的。
- 批末 goal 被 `complete`，而不是烧到轮数上限。
