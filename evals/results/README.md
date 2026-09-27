# 历轮结果

`results/` **进版本库**——结果就是证据。这个文件是**快照台账**：
每轮跑完把 `benchmark.md` 的结论记一行，这样「技能改好还是改坏了」有据可查。

跑完一轮之后：

```bash
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

把 `results/iteration-N/benchmark.md` 的表格贴到下面。

臂现在由 `evalctl run` 驱动（`dsh --profile headless`，cwd 就是铺出来的 fixture），
所以 `timing.json` 里的耗时与 token 是真的。

**iteration-1 … iteration-6 的原始结果文件已删**，只留这个文件里的结论。理由：那几轮是
**旧 fixture + 手工派子代理**条件下收的，条件已经变了，留着会有人拿它当可比数据。
**iteration-7 起作为新基线完整保留。**

---

## iteration-7：护栏复测，和一个反直觉结果

fixture 改完之后，把两条护栏（单次运行，各一条臂）重跑了一遍。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 01-single-unit | 6/7 | **7/7** | 见下 |
| 02-mid-flight-change | 7/7 | 7/7 | 无（护栏，符合预期） |

**合计：`with_skill` 0.93 ± 0.07 / `without_skill` 1.00 ± 0.00，delta −0.0714。技能反而更低。**

### case 01：技能输给裸模型，而且是它故意的

`with_skill` 唯一挂掉的是「需求资料落在 `requirements/<scope>/` 下」。原因不是它做得差：

- `loop-it` 判定这是**单单元**任务 → 按技能自己的规则**内联做完，不建需求资料**（小改动不做文书）
- `without_skill` 读了 fixture 的 `AGENTS.md`，照着「作用域根是 `requirements/<scope>/`」就建了

**这是工作区地图与技能单单元判断的冲突**：工作区说每个需求都建 scope，技能说单单元不必。
谁该赢是个真的设计问题——不是评测 bug，也不该靠改断言绕过去。

顺带，`with_skill` 还慢得多（206.5s vs 78.7s，token 774K vs 523K）。

### 这一轮还抓到两个真 bug

1. **只有 case 05 的探针修了 cwd，01–04 都没修。** 一条真实的 case 01 臂把配置放在
   `inventory/thresholds.json`——**prompt 就是这么写的**——仍被判「阈值没生效」，因为探针
   从包目录出发，实现去找 `inventory/inventory/thresholds.json`。四个探针都补上「回到仓库根
   再观察」，同一条工作树重打分 6/7。
2. **`workspace_clean` 量的是环境仓库，不是臂。** 它拿 let-it-go 工作树的脏状态当基准，
   两次把 Lead 的动作记成臂的越界。DSH 自己的 `benchmarks/AGENTS.md` 明说不要用
   ambient repositories。已改成只看 fixture 的父目录。

## iteration-6：一个负结果——fixture 在替技能干活

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 05-full-pipeline | 9/9 | 9/9 | **无** |

这一轮**把 case 05 的区分点跑没了**，但原因不在技能：**fixture 自己把 scope 的内部形状
规定死了**。五个 fixture 共用一份 `AGENTS.md` + `requirements/README.md`，里面写着
`documents/prd-<feature>.md`、`issues/issue-NNN-<slug>.md`、`notes/`、`records/`，
连「loop-it 的检查点 `.loop-state.json` 就在这一层」都写了。

一旦 fixture 的 `AGENTS.md` 会**自动加载**（headless 让这件事变成默认），任何称职的 agent
都会照着产出那些路径——**用不用技能都一样**。于是「有没有 PRD」测的不再是技能，
而是「agent 会不会读 AGENTS.md」。两条臂都 9/9。

顺带发现 fixture 的 `AGENTS.md` 通篇在说「一个小而完整的 **Python** 服务」、`tests/`（unittest），
而五个 fixture 全是 Go。有一条臂专门花力气指出了这个矛盾。

修法（`b68dc6d`）：fixture 现在**只声明作用域根**，scope 里面怎么组织交给流程自己定——
这正是我们定下的分工：**工作区说 scope 在哪，流程决定里面长什么样**。
副产品是 case 04 的检查点断言也重新变成真的测量。

> 这一轮是**旧 fixture** 下跑的，留着当负结果；不要拿它跟 iteration-7 比分数。

**顺带测到了成本**（这是第一次有真 timing）：同样 9/9，`with_skill` 用了
**221.7s / 2,432,199 tokens / 53 次工具调用**，`without_skill` 只用
**147.6s / 1,177,659 tokens / 42 次**。**技能让它多干了一倍的活，换来的分是一样的。**
这条不能直接推广（旧 fixture、单次运行），但它说明「技能有没有用」不能只看通过率——
还得看它多花掉多少。

## iteration-5

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 05-full-pipeline | 8/9 | 7/9 | **PRD** |

**这是第一个测到规划半边的用例**——前面四个全部从流水线中段进入，需求是我给到手里的。

prompt 只给一个没成形的诉求（「我们要能按仓库配低库存阈值……怎么落地你定」），fixture 里没有
需求资料、没有 issue 卡、没有 PRD。两条臂都自己建了 scope 目录与 issue 卡，**但只有
`with_skill` 产出了 PRD**：

- `with_skill`：scope README + `documents/prd-*.md` + issue 卡 + `notes/walkthrough-*.md`
- `without_skill`：scope README + issue 卡（没有 PRD，也没有走查件）

### ⚠️ 这条用例的探针是坏的（我的设计错误）

两条臂都挂在「阈值真的能按仓库配置」上，但**不是它们做错了**：prompt 说「怎么落地你定」，
于是两条臂都选了 `config/low_stock_thresholds.json`（不是探针写死的 `config/thresholds.json`），
其中 `with_skill` 还用 `go:embed` 把配置编译进二进制——**探针「写配置文件再观察」的做法
对 embed 实现根本不成立**。

修法：要么让任务**把机制定下来**（加一条验收条件：「运维改配置后不重新构建就生效」——
这本来就是真实诉求），要么让探针去 `config/` 下自己找那份配置。前者更诚实：**探针能测什么，
取决于任务有没有把验收条件说清楚**，而不是取决于实现者挑了什么机制。

这条断言对两条臂**同等失效**，所以 PRD 那个区分点仍然成立。

## iteration-4

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 04-serial-batch | 7/7 | 6/7 | **检查点** |

**这是第一个测出技能价值的用例。** 两条臂在工程行为上完全一样——三条行为都实现、
三条 stacked 分支都推到 origin、门禁绿、防篡改过、不越界写入。差别只有一处：

- `with_skill` 建了 `requirements/01_REQ-stock-batch/issues/.loop-state.json`，
  三条 issue 各有 `status` / `branch` / `evidence`（4、3、4 条，按验收条件逐条对应），
  并用 `.git/info/exclude` 把它排除出版本库
- `without_skill` 什么都没留

**没有检查点，中断一次就得从头判断「哪些做完了、证据在哪」。** 这正是这套技能设计上
最该做的事，也是前面三个用例**测不到**的东西——因为那三个都是单单元任务，正好绕开了它的机器。

**结论修正**：不能说「技能没有可测价值」。准确的说法是——**技能的价值在批次状态上，
而不在单次改动的质量上**。用例选单单元，就永远测不出来。

## iteration-1 … iteration-3

三条真实运行，每条两臂、各一次。**结论：只有一个断言区分得出技能的价值。**

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 01-single-unit | 6/7 | 5/7 | 需求资料落点 |
| 02-mid-flight-change | 7/7 | 7/7 | 无（护栏） |
| 03-artifact-handoff | 6/6 | 6/6 | 无 |

读法：

- **case 03 是唯一对「PRD 该不该留」有回答力的**：一个没有任何上下文、也没加载技能的会话，
  只凭上一个会话留下的 `requirements/<scope>/` 就把待办的 issue-002 做对了。
  **那份资料是可用的契约**——所以该留，但留住的是**字段结构**（范围/已交付/未交付/关键决定/未决问题），
  不是「等人批准」这道闸门。
- **三个用例都是单单元任务**，所以「技能没有可测价值」这个读法**不成立**：
  这套流程真正的机器（loop 检查点、串行批次、follow-up 增补、graph 并行）**一个都没测**。
  要下结论，先补那几条用例。
- 两条臂的工程行为（门禁、防篡改、按变更调整、越界写入）在三个用例里**完全一样**。

## ⚠️ iteration-1 … iteration-5 的收集条件

这几轮的分数**不能与 iteration-7 直接比**，两处条件都变了：

- **臂是手工派子代理跑的。** `subagent` 工具没有 cwd 参数，臂继承父会话 cwd，
  fixture 的 `AGENTS.md` **不会自动加载**，只能在 prompt 里显式指认它。
  现在改成 `dsh --profile headless`，cwd 就是铺出来的 fixture，约定自动生效。
- **fixture 当时自己规定了 scope 的内部形状**（见 iteration-6）。
- 没有 timing：那时 tokens / duration 只在子代理通知里出现一次，没当场落盘，
  所以那几轮 benchmark 里的用时与 token 都是 0。**现在由 `evalctl run` 自己采。**

结论的方向仍然可以读（技能的价值在批次状态、在 PRD 的产出），但**分数要重测**——
iteration-7 就是重测。

## 关于 iteration-0-smoke

harness 刚搭好时用「参考解的真实 grading + 一条手工造的 without_skill」做过一次冒烟，
用来验证 `bench` 的汇总与 analyst pass。**那份数据是编的，已经删掉**——不能跟真实运行
混在一起当证据。

## 每条臂要留什么

- `grading.json` — 从**外部**打的分（断言、证据、通过率），不是臂的自述
- `timing.json` — 耗时 / token / 工具调用，由 `evalctl run` 从 `dsh --json` 的事件流里采
- `benchmark.json` / `benchmark.md` — 该轮的汇总（在 iteration 目录下）
- `notes.md` — 臂最后说了什么；以及**断言无效**的原因（例如 Lead 在跑臂期间改了仓库）
- `work/` — 臂的工作副本，scratch，不进库；分数在 `grading.json` 里，产物在 `work/` 里

⚠️ **跑臂期间冻结仓库。** `workspace_clean` 拿 materialize 时的脏快照比，
Lead 顺手改一行 `.gitignore` 就会被记成那条臂的越界（iteration-6 就这么中过一次）。
