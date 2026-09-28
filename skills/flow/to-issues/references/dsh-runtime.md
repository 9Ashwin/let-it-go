# to-issues 的 DSH 运行时说明

在 DeepSeek Harness 下发布 issue 时读这份，或者当正文里的"全新子代理"
措辞需要落到一个工具名时读它。拆解本身与 `gh issue create` 这条路
和宿主无关——只有发现、调用和下面的派发行是 DSH 专有的。

## 加载与调用这个技能

DSH 在扫描根的下一层、按 `<root>/<name>/SKILL.md` 发现技能，
所以嵌套的 `skills/flow/to-issues/` 布局必须在安装时拍平（bundle 把
每个 bucket 列为自己的根；拷到 `~/.agents/skills/to-issues` 时本来就是平的）。
`disable-model-invocation` 是目录级的退出开关，本技能不设它。`skill`
工具按精确名字加载，把正文放进规范的 `<skill_content>` 块，并带一个
`<skill_resources>` 资源块，其目录形式读作 `Base directory for this skill: <path>`——
`<SKILL_DIR>` 解析出的就是这个绝对路径，尽管本技能没有附带脚本。
人类入口是敲 `/to-issues`。

## 派发映射

正文里那张"怎么跑"的表告诉用户如何消费这些 issue。正文有两种措辞
对应到一个 DSH 工具：

| 正文措辞 | DSH |
|---|---|
| 把 issue 正文当自包含提示词交给一个**全新子代理** | `subagent` |
| 继承上下文的 **fork 出来的子代理** | `subagent_fork` |

GitHub CLI 发布这条路不需要映射：`gh` 在任何宿主上跑法都一样。其余几行
本来就是中立的——`/loop-it` 与 `/graph` 是 DSH 技能。

**长跑目标不是"人自己敲 `/goal`"。** 面向模型的那一半是 `create_goal` / `update_goal`：它的门禁是
「当前打开的回合里有人类消息」+「调用者是顶层 agent」——**模型自己就能开**，子代理开不了。
一批活开工时创建它，会话就会跨回合自动续跑；批末 `update_goal complete`。见 `skills/flow/loop-it/CONTRACT.md` 第 6 节。
