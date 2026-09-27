---
name: loop-it
description: "实现入口：一个单元就内联做完，一批有依赖的 issue 就串行循环（带检查点与恢复），真并行交给 /graph。Triggers: implement, 实现, 开始做, 做这个 issue, 落地, 把这个做了, loop-it, issue loop, 批量实现, 循环实现, 恢复循环, resume loop."

---

# loop-it — 实现入口：单单元内联，或一批串行循环

这是**实现**这一步的入口。进来先判规模，别默认开循环。

**产物落点：作用域内的形状固定，仓库只决定作用域根。** 都落在 `<scope>/` 下——`documents/`（PRD、SPEC、设计：`prd-<feature>.md`、`spec-<feature>.md`、`design-<feature>.md`）、`issues/`（`issue-NNN-<slug>.md`）、`notes/`（走查件、实现笔记、`environment.md`）、`records/`（`<YYYY-MM-DD>-delivery.md`）、`checklists/`（`<YYYY-MM-DD>-<服务>.md`）。**作用域根默认 `tasks/<feature>/`**；仓库有约定（如 `requirements/<scope>/`，或 `AGENTS.md` 里的路由表）就用它的根，目录名不变；仓库完全没约定时用默认值。本文件下面写的路径若与此冲突，以这一段为准。

**这是指导，不是脚本。** 排序（拓扑 + 环打破）、下一项判定、检查点读写全部由 `scripts/loop_state.py` 完成并落盘——不要用散文重推这些算法，跑脚本、读它的输出即可。本文件只说明怎么选模式、单个 issue 的边界，以及批末收尾。

检查点固定在**作用域根的 `issues/.loop-state.json`**（默认 `tasks/<feature>/issues/.loop-state.json`）。下面命令里的相对路径都相对作用域根；从别处跑就显式传 `--state <路径>`。

## 先过一道门：这份工作定义好了吗

「定义好了」= 手上有**别人写好的验收条件**——一条 issue 卡、spec 里的一项、一份 PRD。
单单元模式的第一步就是「把正文里的验收条件逐条列出来」，它读的是**已经存在**的东西。

如果你手上只有**一句诉求**，落地方案还要你自己定（「怎么落地你定」「文件格式你定」「要不要压实你定」），
那它**不是单单元，是还没成形的需求**。先走规划半边，再回到这里：

```
/prd（把决策问清、写成可验证的验收条件）→ /to-issues（拆成带阻塞边的卡片）→ /loop-it
```

**别把「装得进一个上下文」当成「定义好了」。** 一个 KV 存储的 TTL 语义、文件格式、压实策略
都是**要定的决策**，不是抄一遍代码——没定就实现，等于把决策藏进代码里，没人评审得了。

## 先判模式

| 情形 | 模式 |
|------|------|
| **一个单元**（一条 issue / 一张卡片 / spec 里的一项），整个改动装得进一个上下文 | **单单元**：不开循环，按下面「单单元模式」内联做完 |
| 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复 | **串行循环**：本技能的默认路径，从「批处理模型」往下读 |
| 节点之间**真并行**（互不共享文件、能各自 worktree 隔离） | 交给 `/graph`：每节点独立 worktree、按波 fan-out；这里是单工作树串行，并行会互相踩 |
| 有依赖，但部分分支可并行 | 交给 `/graph`；这里只做纯串行批次 |

## 单单元模式

用户已经给了你定义好的工作，而且只有一件。做完它，**不要顺手扩张范围**：范围外的改动会让这份 diff 失去可评审性，也让验收条件对不上。

**如果它还没定义好**——你手上只有一句诉求、落地方案要你自己定——回上面那道门：先走 `/prd`，别在这里硬做。

1. **读清楚它。** 把正文里的验收条件逐条列出来；它引用的 PRD / SPEC / 设计文档一并读；再读相邻代码与现有测试，让命名、错误处理、日志风格与仓库一致。验收条件含糊就先问清楚——猜出来的验收条件会一路错到交付。
2. **内联实现。** 就在当前会话里写代码，**不建 worktree、不派子代理、不建波分支**：一件小事派出去，交接成本比它本身还大；那些编排是 `/graph` 的波次与串行批次的调度，各有自己一套上下文与分支约定，在这里重复一遍只会把两套契约混在一起。需要先把行为定下来时用 `/test-first`（红 → 绿，一次一个接缝，接缝先与用户约定）。
3. **自证。** 跑**项目自己的门禁**（`mise run check`、`go build ./... && go test ./...`、`pnpm --dir web lint` …）：边写边跑相关单测，最后跑一次全量，并补上验收条件隐含的测试——没被测过的验收条件不算满足。**门禁红着不要进下一步**：把红的留给评审，等于让评审去猜哪里坏了。
4. **收尾。** 用 `/review-it` 审这一份 diff（先定 Spec 轴：这条 issue 到底要求什么），改掉被接受的发现、再跑一次门禁，然后 `/ship-it` 交付；走查按 `/walkthrough` 的时机判断。

在 `/graph` 的节点里或本技能的串行循环里运行时，**第 4 步的交付不做**——只 commit 到需求分支，PR 与合入由编排器在波末 / 批末各做一次。串行循环的每条 issue 仍过一次 supervisor 检查（见「批处理模型」）；`/graph` 的节点不自审，评审留波末一次做。

## 批处理模型

默认（也是推荐）模式：**整批在一条需求分支上推进**，每个 issue 一个 commit，过一次 supervisor 检查，ship 只在批末做一次。**分支是例外路径的工具，不是每个 issue 的固定开销**——正常路径永远只有那一条需求分支。

```
每个 issue（N 次）:  实现（内联，或派一个实现者子代理）→ 用项目门禁自证 → supervisor 检查 → 在需求分支上 commit
批末（1 次）:        /review-it 审整批 diff → /walkthrough → /ship-it → 1 个 PR → merge → 关闭本批满足的 issue
```

- **一个需求一条分支，整批共用**：`feat/<scope-slug>`（仓库有分支命名约定就用它的）。**正常路径不逐 issue 开分支**——N 条分支要 N 次汇总、N 套上下文，换来的只是「单个 issue 能单独回滚」，而那个用一个 commit 就拿到了。
- **例外才开 issue 分支**：某个 issue 要打回、重做、或需要单独给人看时，把它切到 `feat/issue-N-<slug>` 上留档（见下面「打回或重做」）。这样它不污染需求分支，也还被人翻得出来——**分支数是按需的，不是固定的 N**。
- **每个 issue 一个 commit**，message 带 issue 编号与标题：单个 issue 的追溯与回滚靠 **commit**（`git revert <那个 commit>`），不靠分支。**整批不 push、不开 PR**——push 与 PR 在批末做一次。
- **每个 issue 怎么实现：内联，还是派一个实现者子代理。**
  - **内联**：issue 少、或者每个都小，自己写最省事。
  - **派子代理**：一批 issue 多、或者每个都大——因为**编排者的上下文要活到批末**（它得一直盯着
    检查点、做批末的 `/review-it` 与 `/walkthrough`），实现细节不该把它撑爆。DSH 的 `subagent`
    工具自己就是这么定位的：「offload focused, independent work — research, **a scoped
    implementation**, an analysis — **so it does not consume this conversation's context**」。

  派的时候子代理**不共享这个会话的上下文**，prompt 必须自包含，至少给全这几样——少一样，
  回来的东西就不可信：
  1. 这一张卡片的**正文**（验收条件逐条），它读不到你的上下文
  2. 工作目录 + **需求分支名**（`feat/<scope-slug>`），以及「只在这条分支上 commit、不要 push」
  3. **门禁命令**，以及这个环境特有的坑（`go` 不在 PATH 上之类）
  4. **检查点协议**：`loop_state.py` 的路径与要跑哪几条（`evidence add` / `set --status`）——
     不给它，证据就退化成口头汇报
  5. 边界：不要动默认分支、不要改冻结的测试、不要越出仓库

  子代理返回的是**结果**，不是过程。**证据核对与检查点落盘仍由你（编排者）负责**——
  别把「子代理说它做完了」当成证据。
- 「项目门禁」= 目标仓库自己的构建/测试/lint（如 `go build ./...`、`go test ./...`、`pnpm lint`、`mise run check`），以 issue 所属项目为准。
- 为什么逐 issue 过一次检查：**审自己刚写完的代码是最弱的评审**，但把反馈全推到批末同样有代价——批末才发现的方向性错误，会让前面每个 issue 跟着返工。逐 issue 的检查由**另一个上下文**做，判据是证据。
- 为什么 ship 仍然只在批末做：per-issue PR = N 个 PR、N 次 CI、N 次 merge 争用。默认不做。
- 批末那次 review 不因此取消：它看集成后的完整 diff，专找逐 issue 检查看不见的**结合部**缺陷（共享接口、装配文件、配置与状态）。
- 批末不用汇总（本来就只有一条分支）：`/review-it` 直接看它相对默认分支（`main` 或 `master`，先解析，别假设）的完整 diff，`/ship-it` 从它开一个 PR。批末 PR 关闭多个 issue，因此按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出 commit / 关闭的 issue / 验收证据 / 人工验收状态——单个 issue 的实现靠 commit 追溯与回滚。
- **per-issue PR 模式**（仅当用户明确要求）：每个 issue 都走 `/review-it` + `/ship-it`，成本是 N 个 PR / N 次 CI / N 次 merge；这就是「昂贵模式」，用户没点名就用默认。

## 前置检查（串行循环）

**先看这个仓库是哪种模式，两条清单不一样：**

- **有远端**（GitHub / 公司 GitLab / 自建）：下面全表都跑。
- **纯本地**（没有 `origin`，也不打算开 PR）：**跳过「gh 已认证」与「远程可达」两条**。
  批处理模型一字不变——一条需求分支、每卡一个 commit、每卡跑门禁、批末一次评审——只是没有
  push 与 PR 这一步；批末的交付落在**仓库里的需求资料**：scope README 的里程碑、检查点、
  issue 卡片状态。

`/to-issues` 也支持本地模式（创建到 GitHub **或本地**），两边要对齐：**本地建的卡就在本地交付，
不要因为「gh 没认证」停下。** 那不是失败，是模式不同。

开始前逐条验证，任一失败就停下并报告。

| 检查 | 命令 | 失败处理 |
|------|------|----------|
| gh 已认证（**仅远端模式**） | `gh auth status` | 停止，提示 `gh auth login`；纯本地仓库跳过这条 |
| 在 git 仓库内 | `git rev-parse --is-inside-work-tree` | 停止 |
| 工作树干净 | `git status --porcelain` | 让用户选：stash 后继续 / 中止（默认）/ 强制继续 |
| 在默认分支 | `git branch --show-current` | 提示切回默认分支，并在有 upstream 时 `git pull` |
| 远程可达（**仅远端模式**） | `git ls-remote --heads origin` | 停止，检查网络与权限；纯本地仓库跳过这条 |
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
# 一个需求一条分支，整批共用。已存在就直接切回去——恢复循环时走的也是这条路，
# 所以这里必须幂等，不能无条件 checkout -b。例外留档分支（feat/issue-N-slug）
# 不在这里开：它是打回时才用的，见「打回或重做」。
BRANCH="feat/<scope-slug>"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  # 默认分支不一定是 main，先解析再切
  BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
  BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
  git checkout "$BASE"
  # 只有配置了 upstream 才 pull —— 裸 `git pull` 在没有 upstream 的仓库里退出 1
  git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull
  git checkout -b "$BRANCH"
fi
```

然后**内联实现**：读 issue 标题与正文，提取全部验收条件；正文引用的 PRD/SPEC（如 `<scope>/documents/prd-*.md`）一并读；按目标仓库既有风格改代码；跑该项目的门禁自证；长时间构建/测试作为**后台任务**运行。持续到验收条件全部满足、门禁通过，然后**在这条需求分支上 commit 一个 issue**——一个 issue 一个 commit，message 带编号与标题。

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

`follow-up` 的落点：**先判它该进本轮，还是留到批末。** 只记台账的话，执行中获得的理解决不了正在做的事——那正是把连续过程切成瀑布的地方。

| 情况 | 做法 |
|------|------|
| 同 scope、不阻塞本批剩下的 issue、批还没收尾 | **当场 promote 进本轮**：`followup resolve --id fN --status promoted --issue M`（M 取本批下一个空号）。脚本会把 M 作为 pending 条目插进检查点，`next` 立刻取得到——**不用停下来重跑 `scan`**。卡可以很短：目标 + 验收条件 + 阻塞边，写完就开工 |
| 跨 scope、需要新决策、或批已经收尾 | 记进台账，批末统一收口：promote 成下一轮的 issue，或 `--status dropped --why "<为什么不做>"` |

记录用：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py followup add --from-issue N \
  --title "<要做什么>" --why "<观察到什么，为什么不是本 issue 的活>" [--evidence "<哪条证据让它可见>"]
```

它写进检查点、随需求资料版本化、由 `summary` 列出来。批末若还有 open 的，`set` 会提醒你收口。**不允许"记在脑子里"**——这就是"任务树允许在执行中增长"的落点，没有它，RFC 里的 follow-up 只是一个结论词。

**打回或重做的 issue 挪到它自己的分支上留档，需求分支上不留它。** 这就是例外路径：

```bash
# 已经 commit 了：在那个 commit 上开分支留档，再从需求分支撤掉
git branch feat/issue-N-slug <那个 commit>
git revert --no-edit <那个 commit>
# 还没 commit：把工作树挪到 issue 分支上收起来，再回到需求分支
git checkout -b feat/issue-N-slug && git commit -am "wip: issue-N 打回" && git checkout feat/<scope-slug>
```

`set --status failed` 记下原因（**并把 `--branch feat/issue-N-slug` 记进去**——检查点的 `branch` 字段正是在这种时候才有意义：正常路径上它一直是需求分支），继续下一个。**ship 仍然只在批末做一次**——每个 issue 一次 PR 是这条流水线明确排除的；例外分支不进批末 PR。

收尾时记录结果（脚本据此重算下一项）：

```bash
python3 <SKILL_DIR>/scripts/loop_state.py set --issue N --status shipped --branch feat/<scope-slug>   # 例外时才是 feat/issue-N-slug
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
- **整批都留在需求分支上**，不要每个 issue 切回默认分支：下一个 issue 接着在这条分支上做。例外分支只用来留档，不在上面继续推进。
- 回到 `next` 处理下一项，直到 `set` 输出「全部 issue 处理完毕」。

### 3. 批末收尾（只做一次）

```bash
# 0) 先收口 follow-up：promote 成新 issue 再跑一轮，或写清理由 drop
python3 <SKILL_DIR>/scripts/loop_state.py followup list
# 1) 就在这条需求分支上审整批 diff
/review-it
# 2) 一份走查件：改了什么、跑了什么、证明了什么，并给出 PR body 与合并清单
/walkthrough
# 3) 一个 PR、一次 CI、一次 merge，关闭本批满足的 issue
/ship-it
python3 <SKILL_DIR>/scripts/loop_state.py summary
```

留着 open 直接 ship，等于把那些发现交给运气：`promoted` 的会变成新 issue，重跑 `scan` 就进下一轮；`dropped` 的必须写清为什么不做的。

批末评审同样**逐 issue 分节**过一遍合并 diff，重点看 issue 之间的结合部（共享接口、装配文件、配置与状态），而不是每个 issue 的内部实现。

`walkthrough` 也只在批末做一次，理由与评审相同：它证明的是集成后的整体，而逐 issue 走查会为每个可能活不过集成的 diff 各付一轮截图。PR body 由 `/ship-it` 产出——它是唯一产出者，`/walkthrough` 只提供证据。批级的**设计决策/偏离/权衡/待确认**四类由 `/ship-it` 的实现总结评论承载一次；**逐 issue 的四类**（进度/关键决策/验证记录/未决事项）落在检查点里（上面的 `note`），每条验收条件的结构化观测落在 `evidence`，新发现的任务落在 `followup`，都不另出笔记文件——只有仓库约定要求时才另写一份，并把路径写进 `--verification`。批末 PR 按 `/ship-it` 的「多个 issue 共用一个 PR」逐项列出每个 issue 的 commit、关闭编号、验收证据与人工验收状态。`failed` 的 issue 已经 `revert` 掉了，也不进这张表。

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
/prd（可选）→ /to-issues ─┬─→ /loop-it  单单元：内联做完 → /review-it → /ship-it
                          ├─→ /loop-it  串行：一次一个 issue（本文件默认路径）
                          └─→ /graph    并行：波次 fan-out

每个 issue:  内联实现 → 门禁自证 → 记 evidence → supervisor 检查 → 在需求分支上 commit
每个节点:    内联实现 → 门禁自证 → commit 到自己的分支（节点不自审，评审留波末）
批末 / 波末（各一次）:  follow-up 收口 → /review-it → /walkthrough → /ship-it
                        （决策/偏离/权衡由 /ship-it 的 issue 评论承载一次）
```
