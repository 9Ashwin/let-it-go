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
通知，因此永远不要轮询。`subagent_fork` 正相反：一次性的、前台运行，想在同一轮里拿到答案
就用它。

**委派深度上限为 1**（`maxDepth`，默认值），也就是说子 agent 完全不能再委派。需要第二层工作
的节点只能自己做。每个子 agent 的 `toolFilter` 与 `persona` 属于部署级插件配置，不是技能
字段。子 agent 无法自己提权；在 read-only 与 workspace-write 策略下，它的审批策略被钉死为
`never`。

## 任务列表、后台工作、长周期目标

- `todo_write` 维护任务列表，一个 issue 一行；`job_*`（`job_list`、`job_output`、
  `job_kill`）把耗时的构建或测试作为后台任务运行并收集结果。DSH 没有 `present` —— 报告
  以绝对路径交付。
- `/goal` 是 DSH 的命令——goal 能力面向人的那一半——不是循环运行的技能。面向模型的那一半
  是 `create_goal` / `update_goal`，它的门禁是**权限，而非措辞**：`create_goal` 只在直接的
  人类顶层轮次里运行，所以子 agent 和目标轮次都造不出来。这**并不**意味着要等 “goal” 这个
  词出现——当人交来一个长周期目标（“把这整批做完”）时，创建 goal *就是*设计好的行为，也
  正是它让会话在轮次之间继续工作。`edit` / `pause` / `resume` 受同样的限制；`complete` /
  `blocked` 在该 goal 自己的轮次里也允许，而 `blocked` 在未达到配置的最小轮次数前会被拒绝。
  重启后活跃的 goal 会被解除武装，所以人说 “continue” 时需要 `resume` 重新武装它。

  **一批工作正是它存在的场景。** goal 是会话级的驱动器——一轮结束后重新唤起循环的就是它
  ——而 `.loop-state.json` 是仓库级的记录，记的是这批工作*走到哪了*。两者是两回事，也是两个
  计数器：`maxGoalRounds` 限制续跑，`attempts` 数的是单个 issue 的重试。永远不要让 goal 代替
  检查点，也永远不要让检查点顶替 goal：少了任何一个，长批次要么丢了位置，要么不再推进。
