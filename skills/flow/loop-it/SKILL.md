---
name: loop-it
description: "串行 issue 循环，带检查点与恢复：按依赖给 open issue 排序，逐个在自己的分支上内联实现，最后整批评审、交付一次。Triggers on: loop-it, issue loop, 批量实现, 循环实现, 恢复循环, resume loop."

---

# loop-it — 带检查点恢复的串行 Issue 循环

取一批有阻塞关系的 open GitHub issue，按依赖顺序**一次一个**内联实现，进度落到 `<scope>/issues/.loop-state.json`，崩溃后可从检查点恢复。

**产物落点：作用域内的形状固定，仓库只决定作用域根。** 都落在 `<scope>/` 下——`documents/`（PRD、SPEC、设计：`prd-<feature>.md`、`spec-<feature>.md`、`design-<feature>.md`）、`issues/`（`issue-NNN-<slug>.md`）、`notes/`（走查件、实现笔记、`environment.md`）、`records/`（`<YYYY-MM-DD>-delivery.md`）、`checklists/`（`<YYYY-MM-DD>-<服务>.md`）。**作用域根默认 `tasks/<feature>/`**；仓库有约定（如 `requirements/<scope>/`，或 `AGENTS.md` 里的路由表）就用它的根，目录名不变；仓库完全没约定时用默认值。本文件下面写的路径若与此冲突，以这一段为准。

**这是指导，不是脚本。** 排序（拓扑 + 环打破）、下一项判定、检查点读写全部由 `scripts/loop_state.py` 完成并落盘——不要用散文重推这些算法，跑脚本、读它的输出即可。本文件只说明何时用、单个 issue 的边界，以及批末收尾。

检查点固定在**作用域根的 `issues/.loop-state.json`**（默认 `tasks/<feature>/issues/.loop-state.json`）。下面命令里的相对路径都相对作用域根；从别处跑就显式传 `--state <路径>`。

## 何时用 / 何时不用

| 场景 | 选择 |
|------|------|
| 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复 | **本 skill** |
| 节点之间**真并行**（互不共享文件、能各自 worktree 隔离） | `/graph`：每节点独立 worktree，按波次 fan-out；loop-it 是单工作树串行，并行会互相踩 |
| 有依赖，但部分分支可并行 | 用 `/graph`；loop-it 只做纯串行批次 |
| 只有一个 issue | 直接内联实现 → `/review-it` → `/ship-it`，不必开循环 |

## 批处理模型

默认（也是推荐）模式：**每个 issue 过一次 supervisor 检查，ship 只在批末做一次**。

```
每个 issue（N 次）:  内联实现 → 用项目门禁自证 → supervisor 检查 → 在该 issue 的分支上 commit
批末（1 次）:        /review-it 审整批合并 diff → /walkthrough → /ship-it → 1 个 PR → merge → 关闭本批满足的 issue
```

- 每个 issue 用自己的分支，命名不变：`feat/issue-N-slug`（与 `/ship-it` 一致）。**不 push、不开 PR。**
- 「项目门禁」= 目标仓库自己的构建/测试/lint（如 `go build ./...`、`go test ./...`、`pnpm lint`、`mise run check`），以 issue 所属项目为准。
- 为什么逐 issue 过一次检查：**审自己刚写完的代码是最弱的评审**，但把反馈全推到批末同样有代价——批末才发现的方向性错误，会让前面每个 issue 跟着返工。逐 issue 的检查由**另一个上下文**做，判据是证据。
- 为什么 ship 仍然只在批末做：per-issue PR = N 个 PR、N 次 CI、N 次 merge 争用。默认不做。
- 批末那次 review 不因此取消：它看集成后的完整 diff，专找逐 issue 检查看不见的**结合部**缺陷（共享接口、装配文件、配置与状态）。
- 批末把各 issue 分支汇总到一条批次分支（`git merge --no-ff` 各分支，或直接在累积分支上顺序 commit；**`failed` 的分支不要并入**），`/review-it` 看这条分支相对默认分支（`main` 或 `master`，先解析，别假设）的 diff，`/ship-it` 从它开一个 PR。批末 PR 关闭多个 issue，因此按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出 commit / 关闭的 issue / 验收证据 / 人工验收状态——否则单个 issue 的实现无法追溯与回滚。
- **per-issue PR 模式**（仅当用户明确要求）：每个 issue 都走 `/review-it` + `/ship-it`，成本是 N 个 PR / N 次 CI / N 次 merge；这就是「昂贵模式」，用户没点名就用默认。

## 前置检查

开始前逐条验证，任一失败就停下并报告。

| 检查 | 命令 | 失败处理 |
|------|------|----------|
| gh 已认证 | `gh auth status` | 停止，提示 `gh auth login` |
| 在 git 仓库内 | `git rev-parse --is-inside-work-tree` | 停止 |
| 工作树干净 | `git status --porcelain` | 让用户选：stash 后继续 / 中止（默认）/ 强制继续 |
| 在默认分支 | `git branch --show-current` | 提示切回默认分支，并在有 upstream 时 `git pull` |
| 远程可达 | `git ls-remote --heads origin` | 停止，检查网络与权限 |
| 恢复还是重来 | `<scope>/issues/.loop-state.json` 是否存在 | 恢复 / 删除重来 / 中止；`scan` 会自动合并旧状态，只有损坏文件才要求用户处理 |

**检查点默认排除出版本库**，并**在开跑前把忽略规则提交掉**——仓库有约定要把它随需求资料一起版本化（例如就放在 `<scope>/issues/` 下随需求提交）就照仓库的来，跳过这一段：

```bash
grep -qxF '.loop-state.json' .gitignore || echo '.loop-state.json' >> .gitignore
git add .gitignore && git commit -m "chore: ignore the loop checkpoint"
```

上面的前置检查要求工作树干净，留着未提交的忽略规则会让循环卡在第一步。（不想往 `.gitignore`
里加规则，就把同一行写进未被跟踪的 `.git/info/exclude`。）若它已经被 git 跟踪，提醒用户
`git rm --cached`。

## 执行循环

`<SKILL_DIR>` 是本技能自己的目录（绝对路径）——从加载本技能时 harness 报告的路径解析；内置默认位置是 `~/.agents/skills/loop-it`。

### 1. 取 issue、排序、建检查点（全部交给脚本）

```bash
gh issue list --state open --json number,title,labels,body | python3 <SKILL_DIR>/scripts/loop_state.py scan
# 也可先落盘：python3 <SKILL_DIR>/scripts/loop_state.py scan --issues issues.json [--repo owner/name]
```

脚本负责：解析 `Dependencies: #3, #5` / `Depends on: #3` / `depends on #3` / `requires #3`；建依赖图；按编号打破环并打印警告；拓扑排序；与已有状态合并（**已记录的状态绝不丢失**，损坏文件报错拒绝覆盖）；写检查点；打印有序列表、下一项、blocked/skipped。

状态文件 schema 与旧版一致（`version`、`repo`、`total_issues`、`issues.<n>.{status,branch,phase,error_class,attempts,started_at,updated_at,completed_at,last_error}`），旧状态文件可直接恢复；`title`、`deps` 是 `scan` 追加的附加字段。

随时查进度，不要自己算：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py next      # 下一项 + 其它为什么在等
python3 <SKILL_DIR>/scripts/loop_state.py summary   # 进度表
```

### 2. 逐个 issue

以 `next` 的输出为准，处理下一项：

```bash
# 记开始：attempts +1，写检查点
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status in_progress

# 分支：每次 bash 都是全新 shell，多步 git 必须写在同一条命令里
set -e   # 任一步失败就停：基线切错比中断更贵
# 默认分支不一定是 main，先解析再切
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
git checkout "$BASE"
# 只有配置了 upstream 才 pull —— 裸 `git pull` 在没有 upstream 的仓库里退出 1
git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull
git checkout -b feat/issue-N-slug
```

然后**内联实现**：读 issue 标题与正文，提取全部验收条件；正文引用的 PRD/SPEC（如 `<scope>/documents/prd-*.md`）一并读；按目标仓库既有风格改代码；跑该项目的门禁自证；长时间构建/测试作为**后台任务**运行。持续到验收条件全部满足、门禁通过，然后在该 issue 的分支上 commit。

**验收条件满足一条就记一条证据**，当场写进检查点——哪次实际观测证明了哪条，附上产生它的命令，而不是事后回忆：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py evidence add --issue N \
  --kind <test|runtime|database|external|human> --result <pass|fail|deferred> \
  --command "<真正跑的那条命令>" [--artifact <留下来的输出路径>]
```

`kind` 是观测的**种类**不是强度：`test` 单元/静态、`runtime` 本地真实链路、`database` 存储读回、`external` 外部系统往返、`human` 人工验收。`deferred` 是"没跑"的诚实答案——它必须能和 `pass` 分开，把没跑的写成 `pass` 就是伪造证据。

它与 `note --verification` 分工不同，别互相顶替：`evidence` 记**哪条验收条件被哪次观测证明**（可重跑），`note --verification` 记**这一轮整体证明了什么、覆盖到哪一层、哪里没覆盖**（叙述）。

**commit 之后、记结果之前，过一次 supervisor 检查。** 这一步不是自审：刚写完这段代码的就是你，你的判断是这一环里最弱的一环。把证据交给一个**全新上下文**的评审者（怎么交、交给谁由宿主决定，见 `references/*-runtime.md`），它看不到本次实现过程，只看得到证据。

四条判据：

1. **判据是证据，不是 diff 观感。** 这次实现声明的每条验收条件，各自对应哪一条实际证据（测试输出 / 运行态 / 数据库 / 外部边界 / 人工验证）——就是上面 `evidence add` 记下来的那些。拿不出证据的验收条件就是没做完，"代码看起来对"不算证据。
2. **能跑起来看就跑起来看。** 起服务、点界面、查库、打接口，优先于读 diff。静态审查最容易漏的是"接线断了"：每个部分单独看都对，合起来不通。
3. **发现必须具体到不用再查就能动手**：`file:line` + 根因 + 该改成什么。宽泛意见（"建议补测试"、"可以考虑重构"）不算发现，不进打回清单。
4. **深度随任务条件化。** 任务落在当前模型能独立做稳的范围内，检查就该便宜——核一遍证据即可；越接近能力边界越要往下钻。不要为了走流程把简单任务拖成长检查。

结论四选一：

| 结论 | 含义 |
|------|------|
| `accept` | 证据齐、验收条件逐条对上，进下一个 issue |
| `revise` | 打回本 issue 修改，改完**重跑检查**（不是重跑一遍自证就算过） |
| `retry` | 实现方向错了，重做而不是补丁 |
| `follow-up` | 本 issue 可放行，但新发现要记成后续任务——用下面的 `followup add` 落进检查点，别只留在会话里 |

`follow-up` 的落点：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py followup add --from-issue N \
  --title "<要做什么>" --why "<观察到什么，为什么不是本 issue 的活>" [--evidence "<哪条证据让它可见>"]
```

它写进检查点、随需求资料版本化、由 `summary` 列出来。批末若还有 open 的，`set` 会提醒你收口：要么 `followup resolve --id fN --status promoted --issue M` 变成新 issue 再跑一轮（之后重跑 `scan` 把 M 拉进本批），要么 `--status dropped --why "<为什么不做>"` 明确丢掉。**不允许"记在脑子里"**——这就是"任务树允许在执行中增长"的落点，没有它，RFC 里的 follow-up 只是一个结论词。

**打回或重做的 issue 不进批次分支**：`set --status failed` 记下原因并保留分支，继续下一个。**ship 仍然只在批末做一次**——每个 issue 一次 PR 是这条流水线明确排除的。

收尾时记录结果（脚本据此重算下一项）：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status shipped --branch feat/issue-N-slug
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status shipped --waive "<为什么拿不到观察>"
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status skipped
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status blocked
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status failed --error-class build_failure --error "<message>"
```

**`shipped` 之前先把检查点填成一条记录，而不是一个状态。** 检查点要原样保留四类内容，不压成摘要——进度、关键决策以及为什么这么决策、验证记录、未决事项。**一条 evidence 都没有的 `shipped` 会被直接拒绝**（退出码 1，状态不落盘）：那是唯一一处"事实类"缺口，脚本能判定，就不该交给人自觉。确实拿不到观察时用 `--waive "原因"` 显式豁免——原因会记进检查点，`summary` 里会标成 `#N(已豁免)`，所以豁免是留痕的，不是静默的。缺 `decisions` / `verification` / `open` 只告警不拦：那是判断，不是可核验的事实。补齐四类：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py note --issue N \
  --decisions "<选了什么、放弃了什么、为什么>" \
  --verification "<跑了什么命令、退出码、证明了哪条验收条件>" \
  --open "<还没解决或要交出去的>"          # 没有就写"无"，别省这一步
```

四类都是**追加**而不是覆盖，所以后面推翻前面的决定时，前面那条还在——被覆盖掉的决策正是这份记录存在的理由。内容长到不适合放进检查点时，写进仓库约定的笔记位置，在 `--verification` 里给出路径。

- **跳过**：提问/讨论、纯文档、已实现、重复、带 `wontfix`/`question`/`discussion`/`invalid` 标签、无验收条件且推不出需求。
- **blocked**：依赖未 `shipped`（`next` 已经给出，不要自己判断）。依赖不在本批（issue 已关闭）也按未 `shipped` 处理；确实要放行就 `set --issue <dep> --status shipped` 手工补记。
- 每个 issue 结束后切回默认分支；**失败的分支保留**，不要删。
- 回到 `next` 处理下一项，直到 `set` 输出「全部 issue 处理完毕」。

### 3. 批末收尾（只做一次）

```bash
# 0) 先收口 follow-up：promote 成新 issue 再跑一轮，或写清理由 drop
python3 <SKILL_DIR>/scripts/loop_state.py followup list
# 1) 把各 issue 分支汇总成批次分支后，审整批合并 diff
/review-it
# 2) 一份走查件：改了什么、跑了什么、证明了什么，并给出 PR body 与合并清单
/walkthrough
# 3) 一个 PR、一次 CI、一次 merge，关闭本批满足的 issue
/ship-it
python3 <SKILL_DIR>/scripts/loop_state.py summary
```

留着 open 直接 ship，等于把那些发现交给运气：`promoted` 的会变成新 issue，重跑 `scan` 就进下一轮；`dropped` 的必须写清为什么不做的。

批末评审同样**逐 issue 分节**过一遍合并 diff，重点看 issue 之间的结合部（共享接口、装配文件、配置与状态），而不是每个 issue 的内部实现。

`walkthrough` 也只在批末做一次，理由与评审相同：它证明的是集成后的整体，而逐 issue 走查会为每个可能活不过集成的 diff 各付一轮截图。PR body 由 `/ship-it` 产出——它是唯一产出者，`/walkthrough` 只提供证据。批级的**设计决策/偏离/权衡/待确认**四类由 `/ship-it` 的实现总结评论承载一次；**逐 issue 的四类**（进度/关键决策/验证记录/未决事项）落在检查点里（上面的 `note`），每条验收条件的结构化观测落在 `evidence`，新发现的任务落在 `followup`，都不另出笔记文件——只有仓库约定要求时才另写一份，并把路径写进 `--verification`。批末 PR 按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出每个 issue 的 commit、关闭编号、验收证据与人工验收状态。`failed` 的 issue 不进批次分支，也不进这张表。

`/ship-it` 之后保留 `.loop-state.json` 作为记录，由用户决定何时删除。

## 失败处理

错误类别（build / test / lint / merge / ci / auth / rate-limit / network / unknown）、恢复策略与最大重试次数见 [`references/error-recovery.md`](references/error-recovery.md)——它是查找表，按需加载。分类后按上限重试；重试耗尽就 `set --status failed --error-class <class> --error "<msg>"` 并继续下一项，**绝不无限重试，绝不 force-push**。

## 运行须知

- 「实现 issue」就是 agent 自己读 issue、写代码、跑门禁；不依赖任何外部命令替你完成，**也不要在循环里另起一个长期目标**。
- 每次 shell 调用都是全新 shell：`cd`、变量不跨调用保留；切基线 + 条件 pull + 开分支（含解析默认分支那两行）必须写在同一条命令里。
- 维护每个 issue 一条的**任务清单**；它与 `.loop-state.json` 在同一状态转换后更新，冲突时以脚本为准。
- 长构建/测试作为**后台任务**运行，不要阻塞在单次调用里。
- 严格串行：一次只处理一个 issue（实现会改工作树）。依赖图里有真并行分支时改用 `/graph`。

宿主侧的工具名与配置键见 [`references/dsh-runtime.md`](references/dsh-runtime.md)。

## References

- [`references/error-recovery.md`](references/error-recovery.md) — 错误分类表与恢复协议。
- [`references/edge-cases.md`](references/edge-cases.md) — 边界情况处理表。
- [`references/dsh-runtime.md`](references/dsh-runtime.md) — DSH 侧的发现/调用方式与委派工具映射。
- `scripts/loop_state.py` — `scan` / `set` / `note` / `evidence` / `followup` / `next` / `summary`，顺序与检查点的唯一实现。
- `scripts/test_loop_state.py` — 自测：`python3 <SKILL_DIR>/scripts/test_loop_state.py`。

## 与其他 skill 的关系

```
/prd（可选）→ /to-issues ─┬─→ /loop-it  (串行，一次一个 issue)
                                   └─→ /graph    (并行，波次 fan-out)

每个 issue:  内联实现 → 门禁自证 → 记 evidence → supervisor 检查 → commit 到自己的分支
每个节点:    内联实现 → 门禁自证 → commit 到自己的分支（节点不自审，评审留波末）
批末 / 波末（各一次）:  follow-up 收口 → /review-it → /walkthrough → /ship-it
                        （决策/偏离/权衡由 /ship-it 的 issue 评论承载一次）
```
