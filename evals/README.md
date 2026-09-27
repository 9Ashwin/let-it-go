# evals — flow 技能的回归网

改技能之前先看这里，改完用它验证。**「感觉更好了」不是证据。**

## 它测什么

给 agent 一个**真实代码示例**（fixture，Go 写的：有源码、有测试、有门禁、有它自己的
`AGENTS.md`），让它跑一遍 flow，然后**在 agent 之外**机械核对结果。

测的不是「agent 会不会写代码」，而是**这套技能有没有让流程变好**：

| 断言类型 | 它回答的问题 |
|---|---|
| `gate` | 改动之后 fixture 自己的门禁还绿吗 |
| `probe` | 需求**真的**实现了吗（跑代码看实际行为，不看关键词） |
| `path_glob` / `path_absent` | 产物落在仓库声明的作用域根下，还是落在技能的默认值 `tasks/` 下 |
| `checkpoint_location` | 检查点在 `requirements/<scope>/issues/` 下吗 |
| `tamper_guard` | 门禁与自带断言被改弱了吗（把测试删掉换绿要能抓住） |
| `workspace_clean` | 有没有写到 fixture 之外（臂的 cwd 就是 fixture，越界仍然是这条路的典型失败） |

## 两条臂

每个用例跑两次：

- `with_skill` — 正常目录 + 「先加载并遵循 let-it-go 里对应的技能」
- `without_skill` — 同一 prompt + 「不要加载任何技能，凭你自己的判断做」

后缀在 [arms.json](arms.json)，`evalctl run --arm` 会去那里取。delta 就是这套技能的价值。

> **`evalctl` 是这个 harness 自己的名字**（它的 usage 就自称 `evalctl`），仓库里并不预装它：
> 平时用 Makefile 的 `$(EVAL)`，也就是 `go -C evals/harness run . <命令>`；
> 想要一个真的叫 `evalctl` 的二进制就 `make eval-build`（产物落在 `evals/harness/evalctl`，已在 `.gitignore` 里）。

## 抄了 DSH 自己的三个模式

`deepseek-harness` 仓库里 `apps/cli/tests/profiles/headless/tests/` 有自己的评测设施，
三个模式直接搬过来了：

1. **起点必须是红的** — `coding-task.e2e.ts` 里 `expect(before.status).not.toBe(0)`：
   fixture 在 agent 动手之前必须先失败。所以有 `preflight` 阶段，探针在起点就绿 = 这条断言白写。
2. **断言在 agent 之外执行** — 「agent 声称它成功了……然后世界要同意」：自己重跑门禁、
   自己跑行为探针、自己核对文件逐字节。
3. **不许把测试废掉换绿** — 「一个把测试废掉而不是把 bug 修好的 agent，应该在这里失败，
   而不是只栽在关键词探针上」：这就是 `tamper_guard`。

## 怎么跑

完整步骤在 [harness/run.md](harness/run.md)。最短路径：

```bash
go -C evals/harness run . selfcheck                 # 用例结构自检（也挂在 make check 上）
go -C evals/harness run . list                      # 有哪些用例
for c in 04-serial-batch 05-full-pipeline; do       # 每轮必跑的两条
  for arm in with_skill without_skill; do
    go -C evals/harness run . run "$c" --arm "$arm" --out "results/iteration-N/$c/$arm"
  done
done
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

`run` 自己铺工作区、卡起点（必须是红的）、把任务交给 `dsh --profile headless`、
再从外部打分——一条命令一条臂。

最后用 skill-creator 的 viewer 交人评审：

```bash
python ~/.agents/skills/skill-creator/eval-viewer/generate_review.py \
    results/iteration-1 --skill-name flow --benchmark results/iteration-1/benchmark.json
```

## 用例

**只有两条在量技能的价值**（两条臂分数不同），其余三条是护栏（两条臂一样）。
所以每轮只跑前两条；护栏**改了对应路径才跑**。

### 每轮必跑

| 用例 | 测什么 | 实测区分点 |
|---|---|---|
| [04-serial-batch](cases/04-serial-batch/case.json) | **串行批次**：三条有依赖边的 issue，`loop-it` 该建检查点、**整批在一条需求分支上**（每 issue 一个 commit）、批末推到 origin——这套技能区别于裸模型的那台机器 | **检查点／批次状态** |
| [05-full-pipeline](cases/05-full-pipeline/case.json) | **全流程**：prompt 只给一个还没成形的业务诉求，看流程会不会自己走完 `prd → to-issues → loop-it`，并按技能规定的形状落盘 | **规划半边 + 产物形状** |

### 按需跑（护栏）

| 用例 | 护的是什么 | 什么时候跑 |
|---|---|---|
| [01-single-unit](cases/01-single-unit/case.json) | 单单元任务也会不会建需求资料；不落到技能默认的 `tasks/` | 动了 `loop-it` 的单单元路径 |
| [02-mid-flight-change](cases/02-mid-flight-change/case.json) | 同一轮内调整，而不是冻结计划或让两套并存 | 动了中途变更／follow-up 逻辑 |
| [03-artifact-handoff](cases/03-artifact-handoff/case.json) | 一个全新会话只凭上一个会话留下的 `requirements/<scope>/` 能不能把待办的 issue-002 做对 | 动了 `prd`／产物的字段结构 |
| [06-exception-path](cases/06-exception-path/case.json) | 打回的 issue 挪到 `feat/issue-N-*` 留档、检查点记成 `failed` 并写下那条分支 | 动了例外路径／失败处理 |
| [07-parallel-waves](cases/07-parallel-waves/case.json) | 两个互不依赖的节点进同一个波、各自 worktree 与分支、fan-in 汇合；检查点与 `graph.html` 落在作用域根 | **动了 `graph`**（它零覆盖时最该跑的一条） |
| [08-undeclared-workspace](cases/08-undeclared-workspace/case.json) | **工作区什么都不声明**时退到默认作用域根 `tasks/<feature>/`，而不是凭空发明一个约定 | 动了产物落点／作用域根那条约定 |

01/02/03 是**纯护栏**：两条臂分数一样，它们只告诉你「技能没把简单事做复杂」。
**06 与 07 不一样——它们有区分度**（06 是 9/9 vs 6/9，07 是 10/10 vs 6/10，是七个用例里最大的差距），
但不放进每轮：07 一次 `with_skill` 要付三次子代理生命周期（实测 210.8s / 1,568,225 tokens）。
**改了对应路径就必须跑它们**，这正是它们存在的理由。

## 触发评估：唯一没被测过的那一层

八个用例靠 prompt 后缀**强制加载**技能，所以量的是「技能加载之后行为对不对」。
**「该加载的技能有没有被加载」一直没测过**——它靠人读 description 判断，而人读到的那一次
（`规格说明` 同时挂在 `prd` 与 `to-design` 上，RFC 却把 spec 并进了 `to-design`）就是一次真的误路由。

```bash
go -C evals/harness run . trigger --dsh /tmp/bin/dsh --parallel 6 --repeat 3 --out results/triggers-N
```

用例在 [`triggers.json`](triggers.json)：每条 prompt 的期望都能在对应技能自己的 description 或
正文里找到依据；近邻是**共享关键词但该走别的技能**（或根本不该加载）的那种。自检会校验
`expect` 里的名字确实是某个桶里的技能——写错名字跑出来是「路由错了」，那是假红。

**判定只看第一个加载的技能**，不看之后的串联。第一版要求「加载的都在期望里」，跑出来 20/24，
而四条失败里三条是**误判**：技能是串联的，模型会照着技能自己的话把下游一并加载——`loop-it`
正文写着批末走 `/review-it` → `/ship-it`，它的单单元模式又写着「需要先把行为定下来时用
`/test-first`」。那不是误路由，是照做。串联属于编排质量，由那八个用例量。

**必须跑多次。** 同一个 prompt 三次跑出来的链不一样（实测 `graph-parallel` 三次分别是 `graph`、
`graph+loop-it`、`graph+review-it+ship-it`），所以只有**触发率**有意义，「一次通过」没有。
`--repeat 1` 只是为了快，下结论用 3。

### 第一次结果（24 条 × 3 次，2 分 48 秒）

**23/24**。十二个 flow 技能场景**全部 3/3**，十二个近邻里十一个 3/3。

唯一没过的**不是 flow 技能**：「帮我用 Go 写一个快速排序函数」这条平凡请求，三次里有**一次**
加载了 `modern-go`——`bonus` 桶里那条 description 对「Go」这个词有点贪。

顺带看到一件用例设计没打算测的事：一次 `near-conflict` 的链路是
`conflict → conflict → use-git-worktree`，而**`use-git-worktree` 不是任何桶里的技能**——
模型编了一个听起来合理的名字去调 `skill` 工具。只记录不处理：它不在首位，所以不影响判定，
但它说明目录边界在「谁负责 worktree」这件事上不够显眼（那是 `graph` 的活）。

## 已知限制

- **方差**：`bench` 支持一条臂跑多次（目录名带 `-runN`、传 `--run N`，它归到同一个
  configuration 下报 mean ± stddev）。**默认仍然只跑一次**——单次跑分不清 6/7 vs 7/7
  是技能还是噪声，所以下结论前跑 3 次。
- **中途变更还没验证**：headless 一个任务跑完就退，`--session-id` 能接回同一个会话
  再跑一个任务，但「变更递送」这件事本身没实测过——别在结论里当成已验证。
- **无人值守就没人可问**：headless 里 `ask_user_question` 没有人类可答。所以澄清类场景
  要断言**它留下了什么**（决策记录、假设标注、未决项），不要断言它问了。
- **探针能测什么，取决于验收条件说清了什么。** 探针带进隐含假设会把正确实现判成错的：
  case 05 第一版没写配置放哪，两条臂各自挑了文件名；后来又发现探针默认「进程 cwd 就是
  仓库根」，而 Go 把测试的 cwd 设成包目录——一个完全合理的实现被判成没实现。加断言前先问：
  这条假设任务里说过吗？
