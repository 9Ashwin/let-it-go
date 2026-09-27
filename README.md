<div align="right">
  <span>[<a href="./README.md">简体中文</a>]</span>
  <span>[<a href="./README_EN.md">English</a>]</span>
</div>

<div align="center">
  <h1>let-it-go</h1>
  <img src="docs/images/let-it-go-banner.png" alt="纸艺工作流：prd 与 to-design → to-issues → loop-it 或 graph → review-it → ship-it" width="100%" />
  <p>让编码 Agent 按步骤推进，从需求到交付。<br>
  理清需求，拆解任务，按依赖实现，用审查和验证证据完成交付。</p>
  <div align="center">
    <a href="https://9ashwin.github.io/let-it-go/"><img src="https://img.shields.io/badge/%E5%9C%A8%E7%BA%BF%E6%96%87%E6%A1%A3-9ashwin.github.io-d97757" alt="Online docs" /></a>
    <img src="https://img.shields.io/github/license/9Ashwin/let-it-go" alt="License" />
    <img src="https://img.shields.io/github/stars/9Ashwin/let-it-go?style=social" alt="Stars" />
    <img src="https://img.shields.io/github/forks/9Ashwin/let-it-go?style=social" alt="Forks" />
    <img src="https://img.shields.io/github/last-commit/9Ashwin/let-it-go" alt="Last commit" />
  </div>
  <h3>
    <a href="https://9ashwin.github.io/let-it-go/">在线文档</a> ·
    <a href="#快速开始">安装</a> ·
    <a href="#技能">技能</a> ·
    <a href="#它是怎么跑起来的">工作流</a> ·
    <a href="#项目状态">项目状态</a>
  </h3>
</div>

## let-it-go 是什么

let-it-go 是一套供编码 Agent 使用的研发工作流技能集，共 25 个技能。你描述目标，Agent 按任务需要澄清需求、拆解 Issue、实现、验证并交付。每一步都有明确的职责和完成条件。

配图中的五个阶段对应这些技能：

| 阶段 | 技能 | 完成什么 |
| --- | --- | --- |
| 需求与设计 | `/prd` · `/to-design` | 明确验收条件，必要时记录设计方案与取舍 |
| 任务拆解 | `/to-issues` | 拆成带实现契约、验收条件和依赖关系的 Issue |
| 实现 | `/loop-it` 或 `/graph` | 完成代码与验证；按任务依赖选择单项、串行或并行 |
| 审查 | `/review-it` | 检查是否满足需求 |
| 交付 | `/ship-it` | 先写走查件（记录改动与验证证据），再提交、开 PR、合入并关闭已满足的 Issue；无远端时本地合入 |

从任务当前所处的阶段进入即可。已有明确验收条件的单项任务可以直接交给 `/loop-it`；独立任务能在各自 worktree 中实现时，再用 `/graph` 并行推进。

技能负责判断步骤与边界；排序、分层、环检测和检查点读写交给自带测试的 Python 脚本。

## 快速开始

### 方式一：作为技能目录安装（推荐）

```bash
npx skills add 9Ashwin/let-it-go       # 安装到全局（~/.agents/skills）
npx skills update -g                    # 之后按来源更新
```

技能会落到 `~/.agents/skills`，这条装法不必动任何 profile 依赖。

`npx skills` 递归扫描、安装时把 `skills/<桶>/<技能>` 拍平成 `~/.agents/skills/<技能>`——技能根只扫一层，所以必须拍平。手动拷贝时要自己完成这一步：

```bash
cp -R <let-it-go>/skills/flow/graph ~/.agents/skills/graph   # 拍平，不要连桶一起拷
```

### 方式二：作为 DSH bundle 安装（可选）

还可以作为**部署层配置**安装（随包携带 preset、`toolFilter`、persona，可锁定 commit）——安装命令与参数说明见文档站：**<https://9ashwin.github.io/let-it-go/#install>**。

> [!TIP]
> 安装后，直接描述你要做的事。Agent 会按技能描述选择入口；想指定某一步时，也可以直接写技能名。`/teach` 需要手动调用。
>
> 完整使用指南（安装、每一步怎么触发、验收标准、FAQ）在 **<https://9ashwin.github.io/let-it-go/>**，会自动按浏览器语言跳转到中文或英文版；仓库内是 [docs/index_cn.html](docs/index_cn.html) 与 [docs/index_en.html](docs/index_en.html)。

## 它是怎么跑起来的

并行任务按节点实现、按波次交付；串行任务按批次收尾。节点是一个独立 worktree 中的实现子代理，波次是一组可以同时推进的节点。

| 作用域 | 做什么 | 不做什么 |
| --- | --- | --- |
| **节点** | 在自己的 worktree 里实现、用项目门禁自证、**只 commit 到自己的分支** | 不 push、不开 PR、不合并、不自审 |
| **波次** | 泄漏检查 → 只合并已完成的节点 → 在集成后的树上跑门禁 → **评审一次**（逐节点分节，重点看节点之间的结合部）→ **交付一次**（先写走查件：改了什么、跑了什么、证明了什么；PR body 与合并清单在这里唯一产出，一个 PR，带逐项证据表） | 不做节点级 PR；不做节点级走查 |
| **批次** | `/loop-it` 一次实现并 commit 一个 Issue，可内联完成或交给实现者子代理；小批次只做批末对抗性评审，大批次增加逐 Issue supervisor 检查，批末统一交付（先写走查件） | 不省略批末评审；不逐 Issue 开 PR |

几个刻意设计的地方：

- **`/graph` 只在真有并行度时用。** 一个单元、两个共享文件的单元、或「schema → API → UI」这种链式工作，交给 `/loop-it` 或直接内联做——`/graph` 的价值全部来自波内节点的真独立。
- **单节点波不建波分支。** 没有可集成的东西，就直接拿该节点分支评审与交付。
- **失败节点先原地重试。** 用一条追加消息复用该节点自己的上下文，而不是重开一个全新子代理；重试仍失败就重跑、再失败则从波分支剔除——它的兄弟节点本来就相互独立，其余照常交付。
- **一批多 Issue 共用一个 PR 时必须逐项列证据**：commit、关闭的 Issue、证明它的测试名、人工验收状态。squash 之后那些 commit 在 `main` 上就看不见了，没有这张表就无法单独回滚或审计。

## 为什么是 let-it-go

- **按波次算成本，而不是按节点。** 每个子代理都要为它的整个生命周期付父级的 system prompt、工具 schema 与技能目录；一个节点一次 `/review-it` + `/ship-it` 意味着 N 个 PR、N 次 CI、N 次卡在合并冲突上的机会。所以节点止于 commit，评审与交付收在波次上。
- **算术下沉到脚本。** 依赖排序、波次分层、scope 冲突串行化、检查点状态机都随技能放在 `skills/<桶>/<技能>/scripts/` 里，每个都带自测（仓库根的 `scripts/` 只放维护脚本：`check_skills.py` 与 `sync_vendor.py`）；技能写的是「什么时候用、边界在哪」，不是算法复述。
- **为真实约束设计，而不是理想模型。** 子代理没有自己的 cwd、每次 shell 都是新 shell、委派深度有上限、技能目录对每个子代理都收费——这些在技能里都落成了硬约束（绝对路径纪律 + 共享检出泄漏检查、节点不得再派子代理、可选的[节点瘦身补丁](skills/flow/graph/references/lean-subagent.md)）。

## 技能

下表用技能短名，前缀统一是 `/`（DSH）。

主流程之外，排障、测试、重构和文档技能可以按需要单独使用。

| 阶段 | 技能 | 做什么 |
| --- | --- | --- |
| 需求与设计 | `/prd` · `/to-design` | 需求文档 → 设计提案（**只在跨两个及以上服务、改数据模型或迁移、涉及两条以上对外契约时写**；Markdown 是主产物，HTML 只是可选呈现层） |
| 拆解与分诊 | `/to-issues` · `/triage` | 把自己的 PRD 拆成垂直切片，**每条 Issue 正文就是契约**（目标/非目标/验收条件/必须收集的证据/外部边界/完成定义/未决问题）· 把**外面进来的**原始 issue 分流成可执行卡片 |
| 实现 | `/loop-it` · `/test-first` · `/graph` | 单项任务内联完成（不建 worktree、不派子代理）· 有依赖的批次串行推进，按规模选择评审强度，检查点保存证据与 follow-up 台账 · 红-绿写测试 · DAG 波次并行（每节点独立 worktree，节点在 fan-in 时过 evidence check） |
| 排障 | `/diagnose` · `/conflict` | 先拿到一条会变红的命令再推理的排查循环 · 逐 hunk 按意图解 merge/rebase 冲突 |
| 审查与交付 | `/review-it` · `/ship-it` | 双轴评审（Spec + 8 维度标准）· **先写走查件**：合并前交出「改了什么 + 什么被验证过」（**只提供证据，不产 PR body**）· **走查件与 PR body 的唯一产出者**，提交/PR/合入/关闭 Issue，并一次写出实现总结评论 |
| 代码质量 | `/refactor` · `/modern-go` | 两种模式（`audit` 只报不改 / `fix` 按 Fowler 目录重构）· Go 1.0→1.27+ 现代化 |
| 文档与制图 | `/understand` · `/svg-diagram`（vendor） | 把本次改动变成可交互审阅网页 · SVG 制图规范 + 12 项机械校验（自带 `svg-lint`） |
| 第三方（`skills/vendor/`，逐字副本） | `/find-skills` · `/frontend-design` · `/humanizer-zh` · `/pptx` · `/resume-optimizer` · `/skill-creator` · `/teach` · `/ui-ux-pro-max` · `/web-design-guidelines` | 发现并安装生态里的技能 · 前端视觉设计方向 · 中文文本去模板化润色 · `.pptx` / `.potx` 的读写与编辑 · 简历审计与优化（成果型改写、按目标 JD 调整）· 创建/改进技能并跑评测 · 以教学方式讲清一个概念 · 可检索的 UI/UX 设计知识库 · 按 Web Interface Guidelines 审 UI 代码 |

共 25 个技能（flow 8 / bonus 7 / vendor 10），其中 24 个可由模型按 description 自动选择。vendor 的 `teach` 按上游设置保留 `disable-model-invocation`，不进入模型目录，需要手动调用。这 24 个技能的 description 合计 5572 字符；按 DSH 的空白归一化与每条 500 字符上限计算，模型目录共 5340 字符。

`/goal` 是宿主的**命令**（不是技能）。模型侧是 `create_goal` / `update_goal`，门禁是 **authority 而不是措辞**：`create_goal` 只在**顶层 agent 的直接人类回合**有效，所以子代理和编排中途建不了——但**人类不必说 "goal"**，他直接交出一个长期目标（"把这批 issue 全做完"）时就该建，这正是它被设计的用法。长批次里 goal 是**会话级驱动**（一个回合结束后把会话重新推起来），检查点（`.loop-state.json` / `.graph_state.json`）是**仓库级状态**（记到哪了）——两者互补，计数也各算各的（`maxGoalRounds` 管续跑轮数，`attempts` 管单个 issue 的重试）。

## 仓库结构

```
skills/
├── flow/          # PRD → 交付的主流程，按任务需要选用（8 个）
├── bonus/         # 流程中途随时单独触发的工程实践与产物（7 个）
└── vendor/        # 第三方技能的逐字副本，由 manifest 钉住 commit（10 个）
scripts/           # check_skills.py（布局 / frontmatter / 交叉引用 / patch 校验）
                   # sync_vendor.py（vendor 同步与新增）
Makefile           # make check / test / vendor-* 的入口
cordis.patch.yml   # DSH bundle patch：三个桶各列为一个 customSkillDirs root
```

判据是「它在这条链上扮演什么角色」：`flow` 是流水线本身；`bonus` 是你在中途因为「出事了 / 要保证质量 / 需要一个非代码产物」伸手拿的（测试方法、排障、冲突、外部分诊、重构、设计文档、审阅页）；`vendor` 不产生新技能，只是把上游第三方技能逐字收进来，每个目录带一份 `NOTICE.md`（来源 / commit / 许可 / 同步日期）。

DSH 的技能根**只扫一层**（`<root>/<name>/SKILL.md`），所以 `cordis.patch.yml` 把三个桶各列为一个 root，而不是指向 `skills/`。`npx skills add` 是递归扫描、安装时拍平，无论走哪条安装路径，得到的技能集完全相同。`scripts/check_skills.py` 守着三个静默失败面：**技能被放回顶层**（三个 root 都覆盖不到它）、**某个桶漏进 patch**（那一桶会整体消失，且不报错），以及**根目录 `.claude-plugin/marketplace.json` 与桶内容不一致**（安装 picker 退回成一列平铺的技能，同样不报错）。

## 维护

```bash
make check          # 布局、frontmatter、交叉引用、bundle patch
make test           # 先 check，再跑各脚本自测
make vendor         # 按 vendor.json 里钉住的 commit 同步
make vendor-check   # 报告上游是否已前进
make vendor-update  # 重新钉到上游默认分支 HEAD、同步、再校验
make vendor-list    # 列出已 vendor 的技能与 commit
make vendor-add URL=<git url> SKILL="名字 [名字...]"   # 新增（对应 npx skills add <url> --skill <name> 的形态）
```

`skills/vendor/vendor.json` 是 manifest，每个技能记录 `source` / `sourceUrl` / `path` / `ref`（钉到 commit）/ `license`。**`skills/vendor/` 下是逐字副本，不要就地编辑**——要改就改 manifest，再 `make vendor`。

## 项目状态

![License](https://img.shields.io/github/license/9Ashwin/let-it-go) ![Last Commit](https://img.shields.io/github/last-commit/9Ashwin/let-it-go) ![Commit Activity](https://img.shields.io/github/commit-activity/m/9Ashwin/let-it-go) ![Issues](https://img.shields.io/github/issues/9Ashwin/let-it-go) ![Pull Requests](https://img.shields.io/github/issues-pr/9Ashwin/let-it-go)

## 社区与反馈

- 🌐 [**在线文档**](https://9ashwin.github.io/let-it-go/) — 中文 / English 使用指南
- 🐛 [**Issues**](https://github.com/9Ashwin/let-it-go/issues) — 报错、需求、技能改进建议

## 许可

MIT，全文见 [LICENSE](./LICENSE)。
