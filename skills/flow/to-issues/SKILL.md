---
name: to-issues
description: "把 PRD/SPEC 拆成垂直切片、写清真实阻塞边的 issue，再创建到 GitHub 或本地。契约字段住在 issue 正文里，一个不共享这段对话的全新子代理拿起来就能照它行事。Triggers: 创建issue, 拆解issue, 生成卡片, create issues, issues from spec."
---

# to-issues — 把工作状态拆成 issue

把输入拆成小的、**可独立演示**的 issue，每条都装得进一个全新上下文窗口，然后创建到 GitHub 或本地。可以单独使用，不必先跑 `/prd`。

**工作状态、证据层、三个 profile、零人工闸门、产物落点见 [`../CONTRACT.md`](../CONTRACT.md)——本文件不复述。** 这里只写：何时调用、输入、输出、边界、失败怎么办。

`/prd`（需求）→ `/to-design`（为什么这么选）→ **`/to-issues`**（拆卡）→ `/loop-it` 或 `/graph`（实现）→ `/review-it` → `/ship-it`。

---

## 何时调用

- 手上有 PRD / SPEC / 成形需求，要拆成多条能分别实现、分别演示的卡片。
- 一次改动**装得进一个上下文** → 不用本技能，直接内联做完（长跑就在顶层开目标，见「输出」）。
- 「装得进一个上下文」不等于「定义好了」：只有一句诉求、落地方案还要自己定 → 先 `/prd` 或 `/to-design`，再回来。
- 下游是 `/loop-it`（串行批次）或 `/graph`（真并行前沿）。本技能只产出卡片，不实现。

## 输入

```
这些 issue 要基于什么？

A. 自动探测：扫 tasks/ 里近期的 PRD 和 SPEC
B. 指定 PRD 文件（例如 <scope>/documents/prd-priority-system.md）
C. 指定 SPEC 文件（例如 <scope>/documents/spec-priority-system.md）
D. PRD 和 SPEC 都要（最好：PRD 给需求，SPEC 给技术契约）
E. 直接粘贴需求
```

- 自动探测时把可用文件列出来选。
- PRD + SPEC → 以 SPEC 的 Issue Mapping 为主要依据，用 PRD 的验收条件补充；只有 PRD → 从契约五字段（`goal` / `acceptance` / `invariants` / `unknowns` / `human_checkpoint`）推导，**`acceptance` 是切片的主要依据**。
- **全新子代理看不到这段对话**（[`../CONTRACT.md`](../CONTRACT.md) §1）：issue 正文必须自包含。这是硬契约，不是风格建议。

## 输出

每条 issue 就是一份契约，**issue 正文是唯一载体**。字段块与本地文件骨架见 [`references/issue-template.md`](references/issue-template.md)：

`Goal / Non-goals / Demo path / Acceptance Criteria / Evidence required / External boundary / Definition of done / Human checkpoint / Open questions / Blocked by / Priority`

**拆解规则：**

- **垂直切片（曳光弹），不是分层。** 一条穿过它触及的每一层的窄而完整的路径。横向切片（所有 schema 一张卡、所有 API 另一张、所有 UI 第三张）在每层都落地之前什么都跑不起来，而且每张卡的验收条件都得伸手到别的卡负责的活里——这是模型默认会掉的坑，避开它。
- **检验是「做完这个我能演示什么？」** 答案是一层（「数据库多了个 priority 列」）而不是一个行为（「用户能设置任务优先级并看到它持久化」）→ 切错了，重切。
- **按行为切，不按层、也不按页面切。** 一条卡要能用**一次观测**验完（一条命令、一次演示路径、一轮 e2e）。按页面切（列表 / 新建 / 编辑 / 删除 各一张）会把同一套观测重复四遍。
- 一个 User Story 太大 → 切成 2–3 个*更窄的行为*，每个仍然垂直，并写明阻塞边；1–2 条单独拿不出演示的琐碎验收条件 → 并进相关的卡。
- **规模上限：** 一个 CRUD 后台这种量级 3 张够（骨架 + 认证 / 主体 CRUD / 交付验收）。往上加之前先问：**这张卡有没有自己的失败模式？** 没有就并进上一张。
- **杠杆是验收条件的条数，不是卡数。** 写每一条之前先问：这一条能不能和上一条合成一次观测？「用户列表分页正确」是一条，「第 1 页 10 条 / 最后一页不满 / 超范围返回末页 / 负数归一到 1」是四条——而它们能被**同一次**请求序列证明。
- **验收条件必须可证伪：** 点出能证明它*为假*的观测，并确认它在实现者起手的那个 commit 上会失败。拒绝三种形态——在基线 commit 上已经为真的；只有靠别的 issue 负责的活才能满足的；只是把请求换个说法重述一遍的。
- **有 SPEC 时**用它给卡片加料（API 契约、数据模型章节、错误处理），但把文件路径和行号**挡在正文之外**——它们会烂；改为描述行为和契约。
- **prefactoring 排最前：** 让功能卡变小、变安全的机械铺垫（抽出共用辅助函数、放宽一个类型、加一个接缝、挪一个文件）做成它自己的 issue，排在所有功能卡之前。什么都没找到就跳过，不要凭空造活。
- **阻塞边显式声明、按依赖顺序编号：** 阻塞方在前，实现者（或跟踪器）总有一个可用的前沿可以起手。这些边才是这份产物的重点。

**发布流程：**

1. **定位输入 → 先找 prefactoring → 垂直拆解 → 摆清单 → 判定模式 → 创建 → 摘要 → 直接往下。**
2. **把清单摆出来**（编号 + 每条一行真实阻塞边 + demo）。拆得太碎和无意中切成横向是最常见的两种失败——摆出来才接得住。示例见 [`references/examples.md`](references/examples.md)。
3. **判定创建模式，自己判、不问：** 有 `origin` 且 `gh auth status` 通过 → **GitHub**（`gh` CLI，原生阻塞链接，v2.94+ 才有 `--blocked-by` / `--parent`）；否则 → **本地**（`<scope>/issues/` 下的 `NN-<slug>.md`，跟随 `AGENTS.md` 路由表）。判完在报告里说明选了哪个、依据是什么。
4. **先建阻塞方**，好让它们的编号在依赖它们的 issue 之前就存在。GitHub：`gh issue create --title ... --body ... --label "priority: X" --blocked-by ...`；只有跟踪器拒绝该 flag 时，才退回在正文里写一行 `Blocked by #X`。本地：`mkdir -p` 后按依赖顺序写文件，`NN` 是真实卡片 ID。
5. **摘要报告：** 来源 / 模式 / 条数 + 表格（`# | 标题（行为） | Blocked by | 标识`）+ **当前前沿**（没有未决阻塞、现在就能开始的那些）。模板见 [`references/examples.md`](references/examples.md)。
6. **直接往下：** 报告完按形态进 `/loop-it`（单条或串行批次）或 `/graph`（真并行前沿），不要交回控制权。默认继续，判据全在仓库里。
7. **唯一的例外：** 真往**远端**建 issue 之前，把清单摆出来让人当场接住——建出去再撤要费手脚。本地写文件没这个问题，落盘即视为可用，反馈当修订。

**怎么派发：**

| 形态 | 怎么跑 |
|---|---|
| 现在就一条 issue | issue 正文当自包含提示词交给一个**全新子代理**（`subagent`），或直接内联实现 |
| 串行批次 | `/loop-it` —— 带检查点，一次一条 issue |
| 真并行前沿（不共享文件作用域） | `/graph` —— DAG → 波 → 每节点一个 worktree，波间 fan-in 屏障 |
| 一个该自己一直跑下去的长目标 | 顶层 agent 自己 `create_goal`：门禁是「当前打开的回合里有人类消息」+「调用者是顶层 agent」——**模型自己就能开**，不需要人敲 `/goal`；子代理开不了（CONTRACT §6） |

DSH 工具名与技能发现方式见 [`references/dsh-runtime.md`](references/dsh-runtime.md)。长跑目标**不会自动关闭卡片**——做完自己更新它的状态。

**大范围重构的例外。** 一次机械性改动铺满整个代码库（重命名一列、改共享符号的类型）、任何垂直切片都落不了绿时，按 **expand → migrate → contract** 排序：expand 在旧形式旁边加新形式，什么都不坏（一条）；migrate 按影响面分批迁移调用点，一批一条、每条都被 expand 阻塞（旧形式还在，CI 保持绿）；contract 删掉旧形式，被所有 migrate 批次阻塞。批次自己都保不住绿，就让它们共用一个集成分支并全部阻塞最后一条 integrate-and-verify，只在它那里承诺绿。

## 边界

- **规模下限是硬边界：** 一个上下文装得下的改动不产 issue。要么内联做完，要么在顶层 `create_goal` 后继续——不要为了「有卡片」而建卡片。
- **不新增审批闸门，不新增执行模式。** profile 判据、仪式量、危险面停点全部以 CONTRACT 为准。
- **不等「回复 OK」**（本地发布尤其）：落盘即视为可用，反馈当修订。为什么不能设闸门，见 CONTRACT §5。
- **`Open questions` 必须有归宿：** 每条 unknown 要么**有人认领**，要么显式写下「按 X 假设推进」（`[Assumption]`）。**不许写 `None` 了事**——模型会自己把空白补上，误解会沿多个文件往深处传播，而 `None` 通常是没想，不是没有。
- **碰危险面的卡在正文里写明 `Human checkpoint`**（改公开 API / 兼容性、数据迁移 / 破坏性变更、权限 / 认证边界、不可逆 / 对外承诺）；判据见 CONTRACT §5。
- 本技能不碰 `.loop-state.json`、不开 worktree、不写走查件与长文档——契约只有一个载体，就是 issue 正文。
- **契约质量检查清单**在 [`references/issue-template.md`](references/issue-template.md)——发布任何东西之前跑一遍。

## 失败怎么办

| 场景 | 处理 |
|---|---|
| 整个改动一个上下文窗口装得下 | 跳过 issue，内联实现；要长跑就在顶层 `create_goal` |
| tasks/ 里找不到 PRD/SPEC | 让人给文件路径或粘贴需求 |
| PRD 只有契约五字段 | 从 `acceptance` 推导切片；`unknowns` 还空着就回 `/prd` 补 |
| SPEC 带 Issue Mapping | 以它为主要来源，与 PRD 交叉参照 |
| 产出的是每层一条 issue | 摆清单时拦住：demo 是一层的全部重新垂直切 |
| 拆得太碎（3 行改动 12 张卡） | 要求合并；整件事一个窗口装得下就跳过 issue |
| 大范围机械重构 | expand → migrate → contract |
| `gh` 太旧，不支持 `--blocked-by` / `--parent` | 退回正文写 `Blocked by` 行；建议升到 v2.94+ |
| GitHub 模式下 `gh` 未登录 | 报错，建议 `gh auth login`，并提出切到本地模式 |
| 本地 issue 目录不存在 | 自动 `mkdir -p` 按功能分的目录 |
| 前沿确实并行 | 推荐 `/graph`；作用域重叠就改串行 |
| 用户拒绝创建 issue | 把按依赖排序的清单作为文本打印出来，方便之后手工创建 |
| 契约里还留着 `TBD` 或 `Open questions: None` | 当场补：解决、认领、或标 `[Assumption]` |

## 算它在起作用

- 每条 issue 都回答得出「做完这个我能演示什么？」，而且答案是一个行为，不是一层。
- 发布之前清单就是编号的，每条带一行真实的 `Blocked by`；排在最前的那条没有阻塞，立刻能开始。
- 没有哪条 issue 正文带着文件路径或行号（原型产出的片段除外）。
- 每条 issue 读起来都像一个全新会话不需要你在旁边就能做完的东西。
- prefactoring（如果找到了）排在顺序最前，不和功能 issue 混在一起。
- 每条验收条件都点出一个在基线 commit 上会失败的观测。
