---
name: loop-it
description: "实现入口：一个单元就内联做完，一批有依赖的 issue 就串行循环（带检查点与恢复），真并行交给 /graph。Triggers: implement, 实现, 开始做, 做这个 issue, 落地, 把这个做了, loop-it, issue loop, 批量实现, 循环实现, 恢复循环, resume loop."

---

# loop-it — 实现入口：单单元内联，或一批串行循环

这是**实现**这一步的入口。进来先判规模，别默认开循环。

**工作状态、证据层、三个 profile 的边界、产物落点见 [`../CONTRACT.md`](../CONTRACT.md)——本文件不复述。** 这里只写三件事：怎么选模式、单个 issue 的边界、批末怎么收。

**这是指导，不是脚本。** 排序（拓扑 + 环打破）、下一项判定、检查点读写全部由 `scripts/loop_state.py` 完成并落盘——不要用散文重推这些算法，跑脚本、读它的输出即可。

检查点固定在**作用域根的 `issues/.loop-state.json`**（默认 `tasks/<feature>/issues/.loop-state.json`）。下面命令里的相对路径都相对作用域根；从别处跑就显式传 `--state <路径>`。**先设一次，后面所有命令原样可抄**：

```bash
S=<SKILL_DIR>/scripts/loop_state.py
ST=requirements/<scope>/issues/.loop-state.json    # 仓库约定的作用域根
python3 $S next --state $ST
```

## 何时调用

- 手上有**别人写好的验收条件**——一条 issue 卡、spec 里的一项、一份 PRD——要落地实现。
- 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复。
- **只有一句诉求、落地方案还要自己定** → 不是这里：先 `/prd` → `/to-issues`，再回来。
- 节点之间**真并行**（互不共享文件） → `/graph`。

## 先判模式

| 情形 | 模式 |
|------|------|
| **一个单元**（一条 issue / 一张卡片 / spec 里的一项），整个改动装得进一个上下文 | **单单元**：不开循环，内联做完 |
| 一批 issue 之间有真实阻塞边，要串行推进、崩溃可恢复 | **串行循环**：本技能的默认路径 |
| 节点之间真并行（互不共享文件、能各自 worktree 隔离） | 交给 `/graph` |
| 有依赖，但部分分支可并行 | 交给 `/graph`；这里只做纯串行批次 |

**「装得进一个上下文」不等于「定义好了」。** 判据是形态，不是规模感——手上只有一句诉求、落地方案还要自己定时，那不是单单元，是还没成形的需求（CONTRACT §3）。

## 单单元模式

用户已经给了定义好的工作，而且只有一件。做完它，**不要顺手扩张范围**：范围外的改动会让这份 diff 失去可评审性，也让验收条件对不上。

1. **读清楚它。** 把正文里的验收条件逐条列出来；它引用的 PRD / SPEC / 设计文档一并读；再读相邻代码与现有测试，让命名、错误处理、日志风格与仓库一致。验收条件含糊就先问清楚——猜出来的验收条件会一路错到交付。
2. **实现。** 就在当前会话里写代码，**不建 worktree、不建波分支**——那些编排是 `/graph` 的波次与串行批次的调度，各有自己一套上下文与分支约定，在这里重复一遍只会把两套契约混在一起。需要先把行为定下来时用 `/test-first`（红 → 绿，一次一个接缝）。
3. **自证。** 跑**项目自己的门禁**（`make check`、`go build ./... && go test ./...`、`pnpm --dir web lint` …）：边写边跑相关单测，最后跑一次全量。**每条验收条件先标它要哪一层证据，再给那一层的证据**——层次定义、四层不自动升级也不能互相替代、缺层如实记录见 CONTRACT §4；工作区要有 `make smoke` 时，L3 的证据用它一次跑完。**门禁红着不要进下一步**：把红的留给评审，等于让评审去猜哪里坏了。
4. **收尾。** 用 `/review-it` 审这一份 diff，改掉被接受的发现、再跑一次门禁，然后 `/ship-it` 交付。

在 `/graph` 的节点里或本技能的串行循环里运行时，**第 4 步的交付不做**——只 commit 到需求分支，PR 与合入由编排器在波末 / 批末各做一次。

## 串行批次

**一台机器：一条需求分支 + 每卡一个 commit + 每卡门禁；批末一次评审、一次交付。** 为什么先连通再加固、follow-up 怎么收口、`failed` 怎么留档，见 [`references/batch-model.md`](references/batch-model.md)。

- **评审强度按这张卡碰不碰危险面判。** 不碰（纯页面 / 表单 / 展示）→ 只做批末那一次，且必须是对抗性的：派一个没参与实现的评审者，任务是找「看起来完成了其实没有」。碰了（并发 / 认证边界 / 共享接口）→ 批末一次 + 该卡单独一次。**批末那一次永远不能省**——它是唯一能看到结合部的评审。判据与实证见 [`references/batch-model.md`](references/batch-model.md)。
- **每个 issue 一个 commit**，message 概括改动、**不带 issue 编号**（编号由分支名承载，逐 issue 追溯靠 commit 顺序、检查点与批末 PR 描述）。
- **整批不 push、不开 PR**——push 与 PR 在批末做一次。
- **怎么实现：内联，还是派一个实现者子代理。** issue 少或都小就内联；一批多或每个都大就派——编排者的上下文要活到批末。派的时候子代理看不到这段对话，prompt 必须自包含（卡片正文、工作目录 + 分支名、门禁命令、检查点协议、边界，五样缺一不可，清单见 [`references/batch-model.md`](references/batch-model.md)）。**子代理说它做完了不是证据**——证据核对与检查点落盘仍由编排者负责。
- **要拿到结果才能往下走，就传 `run_in_background: false`。** 后台子代理不会让本回合保持忙碌：以「等它返回」结束回合就是 `turn_end: completed`，headless 里整个运行到此为止。实测过一次：把批末对抗性评审派成后台子代理后停在 8/9，唯一没过的断言正是结尾那句「收到结论后继续批末收尾与 push」。
- **`failed` 的 issue 一律挪到 `feat/issue-N-slug` 上留档**，需求分支上不留它——**按状态触发，不按措辞**：打回 / 重做 / 等用户裁决 / 信息不足，只要记成 `failed` 就走这条。

## 前置检查（串行循环）

```bash
git rev-parse --is-inside-work-tree   # 在仓库里吗？
git status --porcelain                # 工作树干净吗？
git branch --show-current             # 在默认分支上吗？
git ls-remote --heads origin          # 远程可达吗？（仅远端模式）
gh auth status                        # 仅远端模式
```

**纯本地仓库（没有 `origin`、不打算开 PR）跳过最后两条**——批处理模型一字不变，只是没有 push 与 PR 这一步，批末交付落在仓库里的需求资料。**任一硬失败就停下并报告**；逐条的失败处理（工作树脏、`gh` 未认证、恢复还是重来）见 [`references/edge-cases.md`](references/edge-cases.md)。

**检查点默认排除出版本库，并在开跑前把忽略规则提交掉**——仓库有约定要把它随需求资料一起版本化（例如就放在 `<scope>/issues/` 下随需求提交）就照仓库的来，跳过这一段：

```bash
grep -qxF '.loop-state.json' .gitignore || echo '.loop-state.json' >> .gitignore
git add .gitignore && git commit -m "chore: ignore the loop checkpoint"
```

上面的前置检查要求工作树干净，留着未提交的忽略规则会让循环卡在第一步。（不想往 `.gitignore` 里加规则，
就把同一行写进未被跟踪的 `.git/info/exclude`。）

## 开跑前先开 goal

**这一轮如果是人交来的活，现在就 `create_goal`。** 它的门禁是「当前打开的回合里有人类消息 + 调用者是顶层 agent」——**模型自己就能开**，不需要人敲 `/goal`；子代理开不了，所以只能在顶层开。

```
create_goal(objective="把 <这批 issue> 按 /loop-it 做完，直到批末评审与交付",
            max_goal_rounds=<issue 数 × 3 左右>)
```

- **`max_goal_rounds` 自己给。** 默认 256 太大；打满会变成 `blocked`（`round-limit`），而那时 `resume` 会被拒，得先 `edit` 提高上限才能接上。
- **批末必须 `update_goal complete`。** 轮提示写的是「还有工作就保持 active」，不显式关掉会一直烧到上限。
- **中途被 disarm 不是灾难**：单步输出触顶（`max-tokens`）、turn 被 abort、agent 报错、插件重载都会让续跑停下（目标仍 active）。检查点还在——人一句「继续」就 `resume` 接着跑。所以**每个状态转换都要先落盘**。
- 机制细节见 [`references/dsh-runtime.md`](references/dsh-runtime.md)，边界见 CONTRACT §6。

## 执行循环

### 1. 取 issue、排序、建检查点（全部交给脚本）

```bash
gh issue list --state open --json number,title,labels,body | python3 $S scan
# 也可先落盘：python3 $S scan --issues issues.json [--repo owner/name]
python3 $S next      # 下一项 + 其它为什么在等
python3 $S summary   # 进度表
```

脚本负责解析依赖边、排序、与已有状态合并（**已记录的状态绝不丢失**，损坏文件报错拒绝覆盖）和写检查点；**支持哪些写法、怎么破环、状态文件有哪些字段，一律以 `scripts/loop_state.py` 的 docstring 为准**——本文件不复述。

### 2. 逐个 issue

以 `next` 的输出为准：

```bash
python3 $S set --issue N --status in_progress     # attempts +1，写检查点
```

**分支：一个需求一条，整批共用；已存在就直接切回去**——恢复循环走的也是这条路，所以这里必须幂等。例外留档分支（`feat/issue-N-slug`）不在这里开：它是 `failed` 时才用的，见 [`references/batch-model.md`](references/batch-model.md)。

```bash
set -e   # 任一步失败就停：基线切错比中断更贵
BRANCH="feat/<scope-slug>"
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
  BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
  git checkout "$BASE"
  git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1 && git pull   # 没有 upstream 时裸 pull 退出 1
  git checkout -b "$BRANCH"
fi
```

然后**内联实现**：读卡片标题与正文，提取全部验收条件；正文引用的 PRD / SPEC 一并读；按目标仓库既有风格改代码；跑该项目的门禁自证；长构建 / 测试作为**后台任务**运行。持续到验收条件全部满足、门禁通过，然后**在这条需求分支上 commit 一个 issue**。

**验收条件满足一条就记一条**——记在 **scope README 的一张表**里（验收条件 / 怎么验的 / 命令），而不是事后回忆。那是给人看的投影，也是 `/ship-it` 走查件的原料：

| 验收条件 | 观测方式 | 命令 |
|---|---|---|
| 未登录访问 /users 跳登录 | runtime | `curl -si localhost:8080/users` |

**检查点里的 `evidence` 是机器真相，不是可选的**——`shipped` 的闸门读它（零证据会被拒绝；一条都没标层、或只到 L1/L2，都会告警）：

```bash
python3 $S evidence add --issue N --kind test --result pass \
  --command "<真正跑的那条命令>" --layer <L1|L2|L3|L4> [--artifact <留下来的输出路径>]
```

**多条一起记：`--batch -` 从 stdin 读 JSON 行。** 一次观测能覆盖多条验收条件时，**观测写成一个脚本、证据一次写完**——别为了对应关系把一次验证拆成 N 次往返：

```bash
python3 $S evidence add --state $ST --issue N --batch - <<'EV'
{"kind":"runtime","command":"bash smoke.sh  # 一个脚本跑完 6 个端点","result":"pass","layer":"L3"}
{"kind":"test","command":"go test ./... -count=1","result":"pass","layer":"L1"}
EV
```

`kind` 是观测的**种类**不是强度（`test` 单元/静态、`runtime` 本地真实链路、`database` 存储读回、`external` 外部系统往返、`human` 人工验收）；`layer` 才是层次，**别省**。`deferred` 是「没跑」的诚实答案，必须能和 `pass` 分开。

收尾时记录结果（脚本据此重算下一项）：

```bash
python3 $S set --issue N --status shipped --branch "$BRANCH"   # 例外时才是 feat/issue-N-slug
python3 $S set --issue N --status shipped --waive "<为什么拿不到观察>"   # 自愿声明，不是豁免
python3 $S set --issue N --status skipped
python3 $S set --issue N --status failed --error-class build_failure --error "<message>"
```

- **跳过**：提问/讨论、纯文档、已实现、重复、带 `wontfix`/`question`/`discussion`/`invalid` 标签、无验收条件且推不出需求。
- **blocked**：依赖未 `shipped`（`next` 已经给出，不要自己判断）；依赖不在本批（issue 已关闭）也按未 `shipped` 处理。
- **整批都留在需求分支上**，不要每个 issue 切回默认分支：下一个 issue 接着在这条分支上做。

回到 `next` 处理下一项，直到 `set` 输出「全部 issue 处理完毕」。

### 3. 批末收尾（只做一次）

`followup list` 收口 → `/review-it` 审整批 diff → `/ship-it`（先写走查件，再由它给出 PR body）→ `summary` → `update_goal complete` → **把 PR 链接与合入命令打给人**。合入归 [`/merge-it`](../merge-it/SKILL.md)，那一份只有人能敲。完整清单与逐项说明见 [`references/batch-model.md`](references/batch-model.md)。

## 边界

- **不新增审批闸门，不新增执行模式。** profile 判据、仪式量、危险面停点全部以 CONTRACT 为准。
- **不等「回复 OK」**：落盘即视为可用，反馈当修订。
- **两条红线**：不无限重试（一个卡住的 issue 会把整批的时间吃光，检查点里 `failed` 才是诚实的记录）；不 force-push。
- **每次 shell 调用都是全新 shell**：`cd`、变量不跨调用保留；切基线 + 条件 pull + 开分支必须写在同一条命令里。
- 维护每个 issue 一条的**任务清单**；它与 `.loop-state.json` 在同一状态转换后更新，冲突时以脚本为准。
- 严格串行：一次只处理一个 issue（实现会改工作树）。依赖图里有真并行分支时改用 `/graph`。

## 失败怎么办

错误类别（build / test / lint / merge / ci / auth / rate-limit / network / unknown）、恢复策略与最大重试次数见 [`references/error-recovery.md`](references/error-recovery.md)——它是查找表，按需加载。分类后按上限重试；重试耗尽就 `set --status failed --error-class <class> --error "<msg>"` 并继续下一项。

## References

- [`references/batch-model.md`](references/batch-model.md) — 批处理模型、评审强度、follow-up 落点、`failed` 留档、批末清单。
- [`references/edge-cases.md`](references/edge-cases.md) — 边界情况处理表。
- [`references/error-recovery.md`](references/error-recovery.md) — 错误分类表与恢复协议。
- [`references/dsh-runtime.md`](references/dsh-runtime.md) — DSH 侧的发现/调用方式与委派工具映射。
- `scripts/loop_state.py` — `scan` / `set` / `note` / `evidence` / `followup` / `next` / `summary`，顺序与检查点的唯一实现。
- `scripts/test_loop_state.py` — 自测：`python3 <SKILL_DIR>/scripts/test_loop_state.py`。

## 与其他 skill 的关系

```
/prd（可选）→ /to-issues ─┬─→ /loop-it  单单元：内联做完 → /review-it → /ship-it
                          ├─→ /loop-it  串行：一次一个 issue（本文件默认路径）
                          └─→ /graph    并行：波次 fan-out
```

每个 issue：内联实现 → 门禁自证（观测写进 scope README 的验收表）→ 在需求分支上 commit（碰危险面时该卡加一次评审）。批末（各一次）：follow-up 收口 → `/review-it` → `/ship-it`。
