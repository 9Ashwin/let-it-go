# review-it 的 DSH 运行时说明

当评审跑在 DeepSeek Harness 下时读这份文件：技能怎么加载、评审者是谁、哪个工具顶替哪类中立动作。

## 加载与调用本技能

DSH 从带排名的根目录发现技能，同一个名字出现在多个根里时排名最低者胜，也就是最近的那一层胜：

| 排名 | 根目录 |
|---|---|
| 100 | 项目 `<root>/.dsh/skills` |
| 200 | 项目 `<root>/.agents/skills` |
| 300 | 自定义根（`customSkillDirs`；bundle patch 里逐桶的那些条目） |
| 400 | `$DSH_HOME/skills`（`$DSH_HOME` 默认 `~/.dsh`） |
| 500 | `~/.agents/skills` |
| 600 | 随包（`$DSH_BUNDLED_SKILL_DIR`） |

一个根只往下扫一层：`<root>/<name>/SKILL.md`。`skills/flow/review-it/` 位于 `skills/` 下两层，所以它自己不是一个根
——`cordis.patch.yml` 把每个桶列成单独的自定义根，`npx skills` 安装时把 `skills/<bucket>/<name>` 摊平到 `~/.agents/skills/<name>`；纯源码检出因此不是技能根。

模型通过 `skill` 工具加载技能：加载器会在前面加上 `<skill_content name="review-it">` 块，其中 `<skill_resources>`
一节带有 `Base directory for this skill: <path>`，相对路径对着它解析——那个路径就是 `<SKILL_DIR>`（随包默认
`~/.agents/skills/review-it`）。被引用的 `references/…` 只在需要时加载，本技能没有随包脚本；`/review-it` 是人的入口，模型则通过 `skill` 工具加载它。

## 评审

DSH 不接任何外部评审 CLI，也没有随包的 runner 去探测宿主——本仓库只面向 DSH，没有逐 CLI 的命令矩阵要查。
所以评审不是「调用方再读一遍 diff」：调用方**派一个全新子代理**当评审者（`subagent`，不是 `subagent_fork`
——后者继承这段对话，等于让生成者评自己），提示词自带评审目标、两轴要求与输出格式，返回**结论**而不是过程。

## 委派与完成

`subagent` 起一个看不到这段对话的全新子代理；`subagent_fork` 是继承这段对话（已完成的回合）的变体。
**两者都默认后台运行**，立刻返回一个持久化的子代理 id，所以一条 assistant 消息里的多次调用并发；
完成后由运行时把结束通知注入父级——不要轮询，不要忙等。**结论是后续动作的前提时，显式传
`run_in_background: false`**：后台子代理不会让本回合保持忙碌，以「等它返回」结束回合就是
`turn_end: completed`。

委派深度上限是 **1**，所以一个节点——深度 1——完全不能委派。子代理加入父级的组合（同一份系统提示词、工具 schema
与技能目录）；只有部署能裁剪它，因为 `toolFilter` 与 `persona` 是 subagent 行上的插件配置，而面向模型的 `subagent`
工具不接受这类参数。子代理不能自行提权；在只读与 workspace-write 策略下审批策略被钉死为 `never`。没有逐子代理的
cwd 或 worktree 参数，每次 bash 调用都是全新 shell，所以要给子代理绝对路径。

| 需要 | 工具 |
|---|---|
| 加载本技能 | `skill`（加载器会加上 `<skill_content>` 与 `Base directory for this skill`） |
| 保持任务清单最新 | `todo_write` |
| 跑一次长构建或测试 | 后台任务（`job_*`） |
| 派发一个全新子代理 | `subagent` |
| 派发一个继承这段对话的子代理 | `subagent_fork` |
| 继续 / 中断 / 审计子代理 | `send_message` / `interrupt_agent` / `list_agents(scope="descendants")` |
| 把文件交给用户 | `present` |
| 派一个评审者 | `subagent` + `run_in_background: false`（全新上下文） |

## `/goal` 与批次边界

`/goal` 是 DSH 的**命令**，不是技能；模型侧是 `create_goal` / `update_goal`，门禁是**回合的来源，不是措辞**：
`create_goal` 要求「当前打开的回合里有人类消息」+「调用者是顶层 agent」——**模型自己就能开，不需要人敲 `/goal`**；
子代理开不了（非 root 的调用直接被拒），只能在顶层开。批末 `update_goal complete`，不显式关掉续跑会烧到轮数上限；
完整边界见 [`../../CONTRACT.md`](../../CONTRACT.md) 第 6 节。
