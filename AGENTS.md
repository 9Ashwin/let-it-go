# let-it-go 协作入口

这是一套研发工作流技能集（25 个技能，三桶）。本文件是维护这个仓库时的入口：
**常驻的核心规则**。使用技能（而不是维护技能）时读 [README.md](README.md) 与
[docs/index_cn.html](docs/index_cn.html)，不需要本文件。

## 结构

```
skills/flow/     流水线本身：prd to-design to-issues loop-it graph review-it ship-it merge-it
skills/bonus/    中途伸手拿的：conflict diagnose modern-go refactor test-first triage understand
skills/vendor/   第三方技能的逐字副本，由 vendor.json 钉住 commit
scripts/         维护脚本（check_skills.py、link_skills.py、sync_vendor.py、strip_scroll_reveal.py）
evals/           评测工作区：用真实代码示例跑一遍 flow，再机械核对（见 evals/AGENTS.md）
docs/            使用指南（index.html 语言路由页 + 中英两份 index_*.html）
.out-of-scope/   「决定不做」的留档：什么不做、为什么不、逃生通道、谁提过
```

技能发现是**根目录下一层**扫描（`<root>/<name>/SKILL.md`），所以三个桶在
`cordis.patch.yml` 里各列为一个 root，安装时拍平到 `~/.agents/skills/<name>`。

**本机安装用软链，不用拷贝：`make link`**（`scripts/link_skills.py`）。`npx skills add` 是给外人的
分发路径，它只加不删、也不复制不是技能的文件（`CONTRACT.md` 就是被它漏掉的那份）；维护本机时用
软链——`git pull` 就更新，技能删掉之后链接变悬空，下次 `make link` 清掉，不留尸体。

## 门禁

```bash
make check   # 技能结构 + 交叉引用 + 安装清单 + eval 工作区自检
make test    # 再跑各技能自带脚本的自测
```

改动之后必须绿。唯一允许的红是 `vendor/` 里上游技能的 description 超 500 字符
（DSH 会在模型目录里截断）——那是上游的形态，不就地改。

## 硬规则

- **`skills/vendor/` 下是逐字副本，不要就地编辑。** 要改就改 `skills/vendor/vendor.json`
  再 `make vendor`；否则下次 `make vendor-update` 会静默覆盖掉你的改动。
- **技能正文写判断，算术写脚本。** 排序、分层、环检测、检查点状态机都在技能自带的
  脚本里（纯标准库、带自测）；技能只写「什么时候用、边界在哪」。
- **同一件事只有一个维护层级**，改行为时按这个顺序落：
  `scripts` + 自带测试 = 机器行为真相；`SKILL.md` = 入口选择、边界与调用顺序；
  `references` = 解释、例子与故障排查；`README` / `docs` = 项目地图，不写细节规则；
  `evals` = 验证契约，不反向定义流程。**同一条规则不要在多层各写一份**——
  要复述就在那一层指向唯一说明，别把脚本已经实现的 schema 或算法抄进 SKILL。
- **flow 的唯一真相源是 [`skills/flow/CONTRACT.md`](skills/flow/CONTRACT.md)。** 工作状态、
  证据层、三个 profile 的边界、产物落点、goal 燃料都在那里；七份 `SKILL.md` 只写「何时调用、
  边界、失败怎么办」，开头一句链接过去。**别把契约抄回 SKILL，也别在 README 里复述细节规则。**
- **每个技能都要落在调用轴上：`user-invoked` 还是 `model-invoked`。** 判据一句话——**模型能不能
  自己判断该不该用它**。能，就是 `model-invoked`（默认，什么都不用写）；不能（不可逆、只该由人
  在合适的时刻敲），就在 frontmatter 写 `disable-model-invocation: true`，它就变成 `user-invoked`。
  描述跟着分两套写法：`model-invoked` 带触发词（那是路由信号），`user-invoked` 只写一行**给人看的
  摘要**——模型根本读不到它的目录，触发词写在那里等于给一个不存在的读者配路由。
  `scripts/check_skills.py` 会拦 `user-invoked` 却带 `Triggers:` 的描述。现状：25 个技能里只有
  `vendor/teach`（上游的选择）与 `flow/merge-it`（合入不可逆）是 `user-invoked`。
- **「决定不做」有地方记：`.out-of-scope/`。** 一条决定做过一次就该留档——什么不做、为什么不、
  逃生通道在哪、历史上谁提过（带 issue 号）。没有它，同一个请求下次还会被提一遍、再被补一遍。
  判据不是「这个功能有没有道理」，而是「它有没有推翻 `.out-of-scope/` 里那条理由」。
- **提交与推送**：分支只留 `master`，做完就提交并推 `origin/master`；临时分支用完就删（远端一起删）。
- **并发用 `subagent` / `workflow`，不用 Agent Teams。** 要并行就派普通子代理，或写一个 workflow
  脚本 fan-out；不要建 teammates。
- **技能正文里不写来源出处**（谁写的、从哪读的都不写），也不带任何具体项目的工作约定——
  参考别人的仓库时只借机制，不借内容。要留出处就放 [`docs/references-notes.md`](docs/references-notes.md)。
- **flow 技能不设审批闸门。** 规划半边是连续的——`理解 → 做 → 观察 → 追问 → 调整`，不是
  `问 → 写文档 → 等人批准 → 才敢继续`；闸门还奖励"一次问够"，于是澄清问题膨胀成一份要通读的清单。
  所以：**该问的当场问，剩下的边做边收**，产物落盘即视为可用（原文在 `skills/flow/prd/SKILL.md`
  的「为什么不设评审闸门」）。加技能、改技能时不要把它带回来。
  只允许两类例外，且要在技能里写明属于哪一类：**真歧义**（探测到多个 PRD 该用哪个、`failed`
  节点重试还是跳过）、**只能人拍板的事**（谁来评审；含破坏性操作的选项）。
  **判据在仓库里能自己查到的，一律自己判**——有没有 `origin`、`gh auth status` 通不通、门禁是什么、
  产物该落到哪，这些都不是问句。
- **每个组件都编码了一个「模型做不到什么」的假设，假设会过期。** 技能里每一条规则、脚本里
  每一道检查，都是因为曾经观察到模型在这里失败才加上的。所以：**观察到某条规则不再被需要，
  就删掉它**（本仓库删过审批闸门、删过 `to-issues` 的盘问环节，都是因为这个）；改模型、
  换推理档位之后，重新压力测试一遍——**别让规则攒成没人敢动的沉积层**。
  判断标准不是"它有没有道理"，而是"**它还在减少重复失败吗**"。
- **面向模型的文字用中文**（description 里的英文触发词保留，那是路由信号）；
  代码标识符、命令、路径不翻译。脚本注释也写中文。
- **技能改名 / 新增 / 删除之后**：`scripts/check_skills.py` 会查死引用，
  但 `README.md`、`README_EN.md`、两份 `docs/index_*.html`、`.claude-plugin/marketplace.json`
  里的清单与计数要手动跟上（数量、目录字符数都要重算）。

## 评测

`evals/` 是这套技能的回归网：每个用例把一个真实代码示例（Go 写的 fixture）变成干净仓库，
让 agent 真跑一遍 flow，然后**在 agent 之外**机械核对结果。改技能之前先看它的
[README](evals/README.md)，改完用它验证——「感觉更好了」不是证据。
