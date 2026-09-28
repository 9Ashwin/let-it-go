# let-it-go 协作入口

这是一套研发工作流技能集（24 个技能，三桶）。本文件是维护这个仓库时的入口：
**常驻的核心规则**。使用技能（而不是维护技能）时读 [README.md](README.md) 与
[docs/index_cn.html](docs/index_cn.html)，不需要本文件。

## 结构

```
skills/flow/     流水线本身：prd to-design to-issues loop-it graph review-it ship-it
skills/bonus/    中途伸手拿的：conflict diagnose modern-go refactor test-first triage understand
skills/vendor/   第三方技能的逐字副本，由 vendor.json 钉住 commit
scripts/         维护脚本（check_skills.py、sync_vendor.py、strip_scroll_reveal.py）
evals/           评测工作区：用真实代码示例跑一遍 flow，再机械核对（见 evals/AGENTS.md）
docs/            使用指南（index.html 语言路由页 + 中英两份 index_*.html）
```

技能发现是**根目录下一层**扫描（`<root>/<name>/SKILL.md`），所以三个桶在
`cordis.patch.yml` 里各列为一个 root，安装时拍平到 `~/.agents/skills/<name>`。

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
- **产物落点由技能定义、仓库只决定作用域根。** 会写产物的技能
  （`prd` / `to-design` / `to-issues` / `loop-it` / `graph`，以及 `ship-it` 的
  `references/walkthrough.md`）开头那段「产物落点」是唯一正文，别在别处复述。
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
