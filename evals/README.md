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
go -C evals/harness run . run 01-single-unit --arm with_skill \
    --out results/iteration-1/01-single-unit/with_skill
go -C evals/harness run . run 01-single-unit --arm without_skill \
    --out results/iteration-1/01-single-unit/without_skill
go -C evals/harness run . bench results/iteration-1 --skill-name flow
```

`run` 自己铺工作区、卡起点（必须是红的）、把任务交给 `dsh --profile headless`、
再从外部打分——一条命令一条臂。

最后用 skill-creator 的 viewer 交人评审：

```bash
python ~/.agents/skills/skill-creator/eval-viewer/generate_review.py \
    results/iteration-1 --skill-name flow --benchmark results/iteration-1/benchmark.json
```

## 用例

| 用例 | 测什么 |
|---|---|
| [01-single-unit](cases/01-single-unit/case.json) | 单个单元：`loop-it` 应该判成单单元模式内联做完（不建 worktree、不派子代理）；产物落在 fixture 声明的作用域根下 |
| [02-mid-flight-change](cases/02-mid-flight-change/case.json) | 需求在实现**中途**变化：流程能不能在同一轮内调整，而不是冻结计划或让两套并存 |
| [03-artifact-handoff](cases/03-artifact-handoff/case.json) | **上一个会话留下的需求资料能不能用**：fixture 里种着一份 `requirements/<scope>/`，看一个全新会话能不能只凭它把待办的 issue-002 做对 |
| [04-serial-batch](cases/04-serial-batch/case.json) | **串行批次**：三条有依赖边的 issue，`loop-it` 该建检查点、逐 issue 在自己的分支上做、推到 origin——这套技能区别于裸模型的那台机器 |
| [05-full-pipeline](cases/05-full-pipeline/case.json) | **全流程**：prompt 只给一个还没成形的业务诉求，看流程会不会自己走完 `prd → to-issues → loop-it`——前面四条都从流水线中段进入，规划半边只有这条测到了 |

## 已知限制

- **单轮、单次运行**，没有跑 3 次求方差。波动大时 `bench` 的 analyst pass 会标出来。
- **中途变更还没验证**：headless 一个任务跑完就退，`--session-id` 能接回同一个会话
  再跑一个任务，但「变更递送」这件事本身没实测过——别在结论里当成已验证。
- **无人值守就没人可问**：headless 里 `ask_user_question` 没有人类可答。所以澄清类场景
  要断言**它留下了什么**（决策记录、假设标注、未决项），不要断言它问了。
- **探针能测什么，取决于验收条件说清了什么。** 探针带进隐含假设会把正确实现判成错的：
  case 05 第一版没写配置放哪，两条臂各自挑了文件名；后来又发现探针默认「进程 cwd 就是
  仓库根」，而 Go 把测试的 cwd 设成包目录——一个完全合理的实现被判成没实现。加断言前先问：
  这条假设任务里说过吗？
