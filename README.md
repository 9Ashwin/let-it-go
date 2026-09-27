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

let-it-go 的核心是 [`skills/flow`](skills/flow) 中的 7 个研发工作流技能。你描述目标，Agent 按任务需要澄清需求、拆解 Issue、实现、验证并交付。每一步都有明确的职责和完成条件。

这 7 个技能组成配图中的五个阶段：

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

### 作为技能目录安装

```bash
npx skills add 9Ashwin/let-it-go
```

技能会落到 `~/.agents/skills`，这条装法不必动任何 profile 依赖。

`npx skills` 递归扫描、安装时把 `skills/<桶>/<技能>` 拍平成 `~/.agents/skills/<技能>`——技能根只扫一层，所以必须拍平。

> [!TIP]
> 安装后，直接描述你要做的事。Agent 会按技能描述选择入口；想指定某一步时，也可以直接写技能名。
>
> 完整使用指南（安装、每一步怎么触发、验收标准、FAQ）在 **<https://9ashwin.github.io/let-it-go/>**。

## 接入到你的仓库

技能装好之后，**你的仓库声明四件事**——流程读它们，才知道产物放哪、跑哪个门禁。

| 要声明 | 谁决定 | 说明 |
|---|---|---|
| **作用域根** | 扫仓库 | 需求资料放哪。仓库有约定（`requirements/<scope>/`、`docs/`、`specs/`）就用它的根 |
| **门禁** | 扫仓库 | 改动之后必须绿的命令：`make check` · `go build ./... && go test ./...` · `pnpm lint` · `mise run check` |
| **验收基线** | **人拍板** | 哪些测试是冻结的、新测试写在哪。不声明的话，往现有测试文件里追加也可能被当成「把测试改弱」 |
| **只改本仓库内的文件** | 建议 | 防止 agent 写到仓库外去 |

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

项目核心集中在 [`skills/flow`](skills/flow)。下表用 `/技能名` 表示调用入口（DSH），点击名称可查看完整规则。

| 技能 | 职责与边界 |
| --- | --- |
| [`/prd`](skills/flow/prd/SKILL.md) | 澄清目标、范围和未决问题，写成可验证的验收条件 |
| [`/to-design`](skills/flow/to-design/SKILL.md) | 需要明确方案与取舍时写设计提案；Markdown 是主产物，HTML 是可选呈现 |
| [`/to-issues`](skills/flow/to-issues/SKILL.md) | 拆成垂直切片，Issue 正文写清实现契约、验收条件、证据要求与阻塞关系 |
| [`/loop-it`](skills/flow/loop-it/SKILL.md) | 实现入口：单项内联完成，有依赖的批次串行推进；检查点支持恢复，评审强度按批次大小选择 |
| [`/graph`](skills/flow/graph/SKILL.md) | 有真实并行度时按依赖图分波执行，每个节点独立 worktree，汇合时检查证据，波末统一评审与交付 |
| [`/review-it`](skills/flow/review-it/SKILL.md) | 分别检查需求符合度（Spec）和代码标准（8 个维度），两轴独立报告 |
| [`/ship-it`](skills/flow/ship-it/SKILL.md) | 先写走查件、整理验证证据，再生成 PR body，完成提交、推送、PR、合入、关闭 Issue 与实现总结；无远端时本地合入 |

<details>
<summary>随仓库收录的自用补充技能</summary>

`skills/bonus` 和 `skills/vendor` 是作者收集来自己使用的补充工具。它们随仓库保留，方便按需取用；项目介绍与主流程以 `skills/flow` 为中心。

| 目录 | 收录内容 |
| --- | --- |
| [`skills/bonus`](skills/bonus) | `/conflict`、`/diagnose`、`/modern-go`、`/refactor`、`/star`、`/test-first`、`/triage`、`/understand`：冲突处理、排障、代码质量、**工作区初始化**、测试、分诊与变更解释 |
| [`skills/vendor`](skills/vendor) | `/find-skills`、`/frontend-design`、`/humanizer-zh`、`/pptx`、`/resume-optimizer`、`/skill-creator`、`/svg-diagram`、`/teach`、`/ui-ux-pro-max`、`/web-design-guidelines`：技能管理、设计、写作、演示文稿、简历与制图等工具 |

仓库合计收录 25 个技能（核心 7 个，补充 18 个）。其中 24 个支持模型按 description 自动选择；`/teach` 按上游设置保留 `disable-model-invocation`，需要手动调用。`vendor` 中的技能为上游逐字副本，来源、版本与许可见各目录的 `NOTICE.md`。

</details>

## 仓库结构

```
skills/
├── flow/          # PRD → 交付的主流程，按任务需要选用（7 个）
├── bonus/         # 收集自用的工程补充工具（8 个）
└── vendor/        # 收集自用的上游逐字副本，由 manifest 钉住 commit（10 个）
scripts/           # check_skills.py（布局 / frontmatter / 交叉引用 / patch 校验）
                   # sync_vendor.py（vendor 同步与新增）
Makefile           # make check / test / vendor-* 的入口
cordis.patch.yml   # DSH bundle patch：三个桶各列为一个 customSkillDirs root
```

`flow` 是本项目的核心工作流；`bonus` 与 `vendor` 是自用补充集合。`vendor` 按上游原样同步，每个目录带一份 `NOTICE.md`（来源 / commit / 许可 / 同步日期）。

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
