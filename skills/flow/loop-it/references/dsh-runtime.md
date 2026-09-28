# loop-it 的 DSH 运行时说明

在 DeepSeek Harness 下跑这套串行循环时读这份：技能正文里那些中性动作（委派、任务列表、
后台任务）对应下面这些工具、配置键与发现规则。

## 加载与调用本技能

DSH 在扫描根下**一层**发现技能：`<root>/<name>/SKILL.md` 或 `<root>/<name>.md`。
像本仓库 `skills/<bucket>/<name>/` 这样的嵌套目录树是刻意不被发现的，所以 bundle 把每个
bucket 都列成自己的根（`cordis.patch.yml`），而复制出来的 `~/.agents/skills/loop-it`
平铺即可工作。根之间分权重，文件系统 provider 遇到重名技能时按权重从低到高解析：

| 权重 | 来源 | 路径 |
|---|---|---|
| 100 | 项目 DSH | `<projectRoot>/.dsh/skills` |
| 200 | 项目 agents | `<projectRoot>/.agents/skills` |
| 300 | 自定义 | `Config.customSkillDirs` |
| 400 | 用户 DSH | `$DSH_HOME/skills`（默认 `~/.dsh/skills`） |
| 500 | 用户 agents | `$DSH_AGENTS_HOME/skills`（默认 `~/.agents/skills`） |
| 600 | 内置 | `bundledSkillDir`，配置了才有 |

`projectRoot` 是最近的、含 `.git` 的祖先目录。`skill` 工具按精确名字加载，把正文放在规范
的 `<skill_content>` 块里，连同 `<skill_resources>` 资源块一起返回；它的目录形式会打印
`Base directory for this skill: <path>`，`<SKILL_DIR>` 就是从这个绝对路径解析出来的。
输入 `/loop-it` 是人的入口（用户可调用的技能会被直接注入），`disable-model-invocation`
则是从目录里退出。本技能模型可调用，所以两条路都通。

## 委派

| 需求 | 工具 |
|---|---|
| 内联做一个 issue（循环的默认做法） | — |
| 启动一个全新的子 agent | `subagent` |
| 启动一个继承本会话的子 agent | `subagent_fork` |
| 继续 / 重试一个子 agent | `send_message(child_id, …)` |
| 打断子 agent 当前这一轮 | `interrupt_agent(child_id)` |
| 审计自己启动的子 agent | `list_agents(scope="descendants")` |

`subagent` 默认在后台跑，立刻返回一个持久的 child id，所以一条 assistant 消息里的多次调用
是并发的——宿主对一步内重叠的工具调用数有上限（默认十个），子 agent 结束时父 agent 会收到
通知，因此永远不要轮询。

**要拿到结论才能继续时，必须显式传 `run_in_background: false`。** 默认值由部署的
`backgroundMode` 推（`continuable` → 默认后台），而**后台子代理不会让本回合保持忙碌**：
你以「等它返回」结束回合，回合就是 `turn_end: completed`，headless 里整个运行到此为止。
`subagent_fork` 同样默认后台——它不是"前台版"，只是多带上了本会话已完成的回合。

**委派深度上限为 1**（`maxDepth`，默认值），也就是说子 agent 完全不能再委派。需要第二层工作
的节点只能自己做。每个子 agent 的 `toolFilter` 与 `persona` 属于部署级插件配置，不是技能
字段。子 agent 无法自己提权；在 read-only 与 workspace-write 策略下，它的审批策略被钉死为
`never`。

## 任务列表、后台工作、长周期目标

- `todo_write` 维护任务列表，一个 issue 一行；`job_*`（`job_list`、`job_output`、
  `job_kill`）把耗时的构建或测试作为后台任务运行并收集结果。报告以绝对路径交付；
  要让用户**打开**某个产物（走查件、看板）用 `present`——它把文件登记成卡片。
- `/goal` 是 DSH 的命令——goal 能力面向人的那一半——不是循环运行的技能。面向模型的那一半
  是 `create_goal` / `update_goal`，它的门禁是**回合的来源，而非措辞**：`create_goal` 要求
  「当前打开的回合里有人类消息」+「调用者是顶层 agent」。所以**编排器自己就能开**——人交来
  一批长活时，创建 goal *就是*设计好的行为，也正是它让会话在轮次之间继续工作；**子 agent
  开不了**（非 root 的调用直接被拒），所以只能在顶层开。`edit` / `pause` / `resume` 同样要求
  直接人类回合；`complete` / `blocked` 额外允许「当前目标轮」这一权限来源，而 `blocked` 在
  未达到配置的最小轮次数（默认连续三轮）前会被拒绝。重启或 fork 后活跃的 goal 会被**解除武装**，
  所以人说 “continue” 时需要 `resume` 重新武装它。
- **开跑前开 goal，批末 `complete`。** 不显式关掉，续跑会一直烧到轮数上限（默认 256，自己按
  issue 数给更小的值）。单步输出触顶（`max-tokens`）、turn 被 abort、agent 报错、插件重载都会
  让续跑解除武装——**目标仍 active，只是不再自动续跑**；`.loop-state.json` 还在，人一句「继续」
  就 `resume` 接着跑。

  **一批工作正是它存在的场景。** goal 是会话级的驱动器——一轮结束后重新唤起循环的就是它
  ——而 `.loop-state.json` 是仓库级的记录，记的是这批工作*走到哪了*。两者是两回事，也是两个
  计数器：`maxGoalRounds` 限制续跑，`attempts` 数的是单个 issue 的重试。永远不要让 goal 代替
  检查点，也永远不要让检查点顶替 goal：少了任何一个，长批次要么丢了位置，要么不再推进。

## 宿主侧的硬边界（源码实测）

- **委派深度出厂上限是 1**（`maxDepth`）：子代理**不能再派子代理**。所以「一批活里再分活」只能由
  顶层编排器派，技能里不要写「让子代理自己再拆」。
- **`toolFilter` / `persona` / `maxDepth` / `backgroundMode` 是部署实例配置**，模型的 `subagent`
  schema 里根本没有这些字段——技能给不了，只能靠部署补丁（见 `graph/references/lean-subagent.md`）。
  `run_in_background` 的默认值由 `backgroundMode` 推：`continuable` → 默认后台跑，`one-shot` → 默认前台。
- **子代理不继承**这段对话（spawn 全新；fork 只带已完成回合）、goal、todo、plan mode；它继承 cwd、
  preset 与父级的模型路由。所以子代理读不到你的检查点，也看不到你的 goal——**prompt 必须自包含**。
- **`todo_write` 是整表替换，每轮开始会被清空**，也不作为第二条消息回灌给模型（它是 UI/回放状态），
  长批次里还会先被上下文压缩遮蔽。**所以状态只能落盘**——`.loop-state.json` 是唯一可靠的记忆。
- **上下文压缩只遮蔽、不删日志**：被压掉的恰恰是 todo 的整表参数与子代理的返回。恢复靠检查点，
  不靠对话。
- **没有「失败自动重跑一批活」的官方机制。** 除 goal 之外，`hooks` / `schedule` / `session-query` /
  `ralph` 都不在出厂 bundle，写进技能在这些部署里是空话。失败要自己收：检查点记状态，goal 负责续跑。
