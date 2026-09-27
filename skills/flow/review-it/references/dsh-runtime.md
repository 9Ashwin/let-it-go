# review-it 的 DSH 运行时说明

当评审跑在 DeepSeek Harness 下时读这份文件：技能是怎么加载的、该调用哪个评审者、哪个工具
顶替哪一类中立动作。技能正文假定这些事实成立；这份文件就是它们待的地方，这样正文才能保持简短。

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

一个根只往下扫一层：`<root>/<name>/SKILL.md`。`skills/flow/review-it/` 位于 `skills/` 下两层，
所以它自己不是一个根：`cordis.patch.yml` 把每个桶列成一个单独的自定义根，而 `npx skills` 安装时
把 `skills/<bucket>/<name>` 摊平到 `~/.agents/skills/<name>`。这就是为什么一份纯源码检出不是技能根。

模型通过 `skill` 工具加载技能。加载器会在前面加上一个 `<skill_content name="review-it">` 块，
其中 `<skill_resources>` 一节带有 `Base directory for this skill: <path>`，并告诉模型相对路径对着
它解析。那个路径就是 `<SKILL_DIR>`；随包默认值是 `~/.agents/skills/review-it`。被引用的文件
（`scripts/review-it`、`references/…`）只在需要时才加载。

`/review-it` 是人的入口——直接调用本技能——而模型通过 `skill` 工具加载它。

## 评审

DSH 不接任何外部评审 CLI，所以调用方 agent 就是评审者：它自己生成 diff，自己套用评审重点。
这里没有逐 CLI 的命令矩阵要查，也没有随包的 runner 去探测宿主——本仓库只面向 DSH，读 diff、自己判断。

## 委派与完成

`subagent` 起一个看不到这段对话的全新子代理；`subagent_fork` 是继承这段对话的那个变体。
`subagent` 调用默认在后台运行并立刻返回一个持久化的子代理 id，所以同一条 assistant 消息里的多次
调用是并发的（`subagent_fork` 则是一次性、前台）。后台子代理完成后由运行时把一条结束通知注入父级
来回报——不要轮询它，不要忙等。用 `send_message(child_id, ...)` 继续一个子代理，用
`interrupt_agent(child_id)` 停掉一个，用 `list_agents(scope="descendants")` 审计整棵树。

委派深度上限是 **1**，所以一个节点——深度 1——完全不能委派。子代理加入父级的组合（同一份系统提示词、
工具 schema 与技能目录）；只有部署能裁剪它，因为 `toolFilter` 与 `persona` 是 subagent 行上的插件配置，
而面向模型的 `subagent` 工具不接受这类参数。子代理不能自行提权；在只读与 workspace-write 策略下，
它的审批策略被钉死为 `never`。没有逐子代理的 cwd 或 worktree 参数，而且每次 bash 调用都是全新 shell，
所以要给子代理绝对路径。

| 需要 | 工具 |
|---|---|
| 加载本技能 | `skill`（加载器会加上 `<skill_content>` 与 `Base directory for this skill`） |
| 保持任务清单最新 | `todo_write` |
| 跑一次长构建或测试 | 后台任务（`job_*`） |
| 派发一个全新子代理 | `subagent` |
| 派发一个继承这段对话的子代理 | `subagent_fork` |
| 继续一个子代理 | `send_message(child_id, ...)` |
| 审计子代理 | `list_agents(scope="descendants")` |
| 中断一个子代理 | `interrupt_agent(child_id)` |
| 把文件交给用户 | `present` |
| 跑评审者 | 无——调用方 agent 自己评审 |
