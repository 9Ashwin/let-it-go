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

let-it-go 的核心是 [`skills/flow`](skills/flow) 中的 8 个研发工作流技能。你描述目标，Agent 按任务需要澄清需求、拆解 Issue、实现、验证并交付。

**一个工作状态，三个 profile，零人工闸门。** 要做什么、什么算做完，写在一处——GitHub issue 正文（`goal` / `acceptance` / `invariants` / `unknowns` / `human_checkpoint`）；走到哪了写在检查点里。其余文档（PRD、走查件、PR 描述）都是它的**投影**。契约全文见 [`skills/flow/CONTRACT.md`](skills/flow/CONTRACT.md)。

**拿不准走哪条，先看形态：**

| 你手上的东西 | 走哪条 | 仪式量 |
| --- | --- | --- |
| 只有一句诉求，落地方案还要自己定 | `/prd` → `/to-issues` | 需求还没成形，先把决策定清楚 |
| 一条 issue / 一张卡 / spec 里的一项，装得进一个上下文 | `/loop-it`（单单元） | **零仪式**：不碰检查点、不建 worktree、不写走查件 |
| 一批有真实阻塞边的 issue | `/loop-it`（串行批次） | 一条需求分支 + 每卡一个 commit；批末一次评审与交付 |
| 节点之间真并行 | `/graph` | worktree 波 + fan-in；波末一次评审与交付 |
| 有真岔口要留档（公开 API / 数据迁移 / 权限 / 兼容性） | 插一步 `/to-design` | 只在碰危险面时 |
| 一个难复现的 bug / 偶发 flake / 性能回归 | `/diagnose` | 先拿到一条已经变红的命令 |
| 别人提来的原始 issue | `/triage` | 先复现，再补成 agent 可执行的卡片 |

**一批活不靠人推。** 开工时开一个持久目标（`create_goal`），跑到批末；**不逐条等人说"继续"**，也**不需要人工评审才放行**——评审由 `/review-it` 派一个不共享上下文的子代理做，**门禁绿 + 每条验收条件有它那一层的证据**就是放行条件。人只在两个地方被叫：危险面（公开 API / 数据迁移 / 权限 / 不可逆操作），以及**合入**——它不可逆，所以归 `/merge-it`，只有人能敲。

技能负责判断步骤与边界；排序、分层、环检测和检查点读写交给自带测试的 Python 脚本。

## 快速开始

### 作为技能目录安装

```bash
npx skills add 9Ashwin/let-it-go
```

技能会落到 `~/.agents/skills`，这条装法不必动任何 profile 依赖。

`npx skills` 递归扫描、安装时把 `skills/<桶>/<技能>` 拍平成 `~/.agents/skills/<技能>`——技能根只扫一层，所以必须拍平。

**拍平会漏掉一份不是技能的文件：`CONTRACT.md`。** 八份 flow `SKILL.md` 都写着「工作状态、证据层、profile 边界、产物落点见 `../CONTRACT.md`」，而拍平之后那个相对路径指向 `~/.agents/skills/CONTRACT.md`——它不在任何技能目录里，`npx skills` 不会复制它。装完补一条：

```bash
cp skills/flow/CONTRACT.md ~/.agents/skills/CONTRACT.md
```

漏掉的症状很安静：技能照常加载，agent 只是读不到唯一真相源，然后花好几个工具调用到处找它（T1 eval 就是这么发现的）。
技能根下多一份 `CONTRACT.md` 不会被当成技能——它没有 frontmatter，DSH 直接忽略。

### 在本仓库里维护时：软链，不拷贝

上面那条是给外人的分发路径。**自己改这套技能时用 `make link`**（`scripts/link_skills.py`）——把每个技能
软链进 `~/.agents/skills`，连同 `CONTRACT.md` 一起：

```bash
make link          # 软链全部技能 + 共享文档；替换掉旧的拷贝，清掉悬空链接
make link-check    # 只报告漂移（仓库与安装目录不一致时退出码 1）
```

拷贝式安装咬过两次，软链一次解决两个：

- **删技能不留尸体。** `npx skills add` 只加不删，技能从仓库删掉之后 `~/.agents/skills/<name>` 还留着；
  软链会变成悬空链接，`make link` 直接清掉。
- **`CONTRACT.md` 不再漏。** 软链之后 `<技能目录>/../CONTRACT.md` 按 OS 的路径解析会走回仓库里那份；
  脚本同时在技能根软链一份，两种解析方式都成立。
- 顺带：`git pull` 就是更新，不需要重跑安装。

别的来源的技能（`~/.agents/skills` 下不是本仓库的条目）**不动**，只列出来给人看。

> [!TIP]
> 安装后，直接描述你要做的事。Agent 会按技能描述选择入口；想指定某一步时，也可以直接写技能名。
>
> 完整使用指南（安装、每一步怎么触发、验收标准、FAQ）在 **<https://9ashwin.github.io/let-it-go/>**。

## 接入到你的仓库

**流程读 `AGENTS.md`，但不替你写它。** 写仓库约定是人的事——通用底线已经是流程自己的默认（不 force-push、不提交凭据、默认分支只经 PR 进入、不把冻结的测试改弱），仓库特有的危险面由 `human_checkpoint` 在碰到的那一刻问你（公开 API / 数据迁移 / 权限 / 不可逆操作）。

想让它更确定，就在仓库根的 `AGENTS.md` 里写这几件它扫不出来的事：

| 要写进去 | 说明 |
|---|---|
| **门禁** | 改动之后必须绿的命令：`make check` · `go build ./... && go test ./...` · `pnpm lint` · `mise run check`。不写的话流程自己扫 Makefile / `package.json` / `go.mod` / `.github/workflows` |
| **验收基线** | 哪些测试是冻结的、新测试写在哪。不写的话，往现有测试文件里追加也可能被当成「把测试改弱」 |
| **作用域根** | 仓库**已经有**需求目录约定（如 `requirements/<scope>/`）才写；没有就不写，技能用自己的默认值 |
| **红线** | 这个仓库不可协商的底线。没有就写「暂无」 |

**没写进 `AGENTS.md` 的约定，流程当作不存在**——它只读得到仓库里的东西。`RULES.md` / `CONSTRAINTS.md` 这类登记表不用铺：它们要有维护者才不腐烂，而腐烂的约定比没有更糟。

## 它是怎么跑起来的

并行任务按节点实现、按波次交付；串行任务按批次收尾。节点是一个独立 worktree 中的实现子代理，波次是一组可以同时推进的节点。

| 作用域 | 做什么 | 不做什么 |
| --- | --- | --- |
| **节点** | 在自己的 worktree 里实现、用项目门禁自证、**只 commit 到自己的分支** | 不 push、不开 PR、不合并、不自审 |
| **波次** | 泄漏检查 → 只合并已完成的节点 → 在集成后的树上跑门禁 → **评审一次**（逐节点分节，重点看节点之间的结合部）→ **交付一次**（先写走查件：改了什么、跑了什么、证明了什么；PR body 与合并清单在这里唯一产出，一个 PR，带逐项证据表） | 不做节点级 PR；不做节点级走查 |
| **批次** | `/loop-it` 一次实现并 commit 一个 Issue，可内联完成或交给实现者子代理；评审强度按**危险面**选（并发 / 认证边界 / 共享接口），批末统一交付（先写走查件） | 不省略批末评审；不逐 Issue 开 PR |

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
| [`/ship-it`](skills/flow/ship-it/SKILL.md) | 把做完的工作交付到「PR 就绪」：先写走查件、整理交付证据，再提交、推分支、开 PR、补实现总结；**到这里停**，合入交给人 |
| [`/merge-it`](skills/flow/merge-it/SKILL.md) | 合入已经开好的 PR：摆出要合的东西与 checks 状态、合入、关 Issue、回默认分支同步。**只有人能敲它**——合入不可逆 |

每个核心技能还有一页**给人看**的文档（[`docs/skills/`](docs/skills/)），四个固定小节：`What it does`
（它一句话做什么，以及它和显而易见的默认做法差在哪）、`When to reach for it`（你敲它还是模型自己
伸手、什么时候该伸手）、`Common questions`（真被问过的问题）、`It's working if`（**不打开 `SKILL.md`
就能自己核对**的信号）。`make check` 会检查每个 flow 技能都有这一页。

<details>
<summary>随仓库收录的自用补充技能</summary>

`skills/bonus` 和 `skills/vendor` 是作者收集来自己使用的补充工具。它们随仓库保留，方便按需取用；项目介绍与主流程以 `skills/flow` 为中心。

| 目录 | 收录内容 |
| --- | --- |
| [`skills/bonus`](skills/bonus) | `/conflict`、`/diagnose`、`/modern-go`、`/refactor`、`/test-first`、`/triage`、`/understand`：冲突处理、排障、代码质量、测试、分诊与变更解释 |
| [`skills/vendor`](skills/vendor) | `/find-skills`、`/frontend-design`、`/humanizer-zh`、`/pptx`、`/resume-optimizer`、`/skill-creator`、`/svg-diagram`、`/teach`、`/ui-ux-pro-max`、`/web-design-guidelines`：技能管理、设计、写作、演示文稿、简历与制图等工具 |

仓库合计收录 25 个技能（核心 8 个，补充 17 个）。其中 23 个支持模型按 description 自动选择；`/teach` 与 `/merge-it` 保留 `disable-model-invocation`，需要手动调用。`vendor` 中的技能为上游逐字副本，来源、版本与许可见各目录的 `NOTICE.md`。

</details>

## 仓库结构

```
skills/
├── flow/          # PRD → 交付的主流程，按任务需要选用（8 个）
├── bonus/         # 收集自用的工程补充工具（7 个）
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
