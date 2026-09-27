# 历轮结果

`results/` 不进版本库（跑一轮会产生一堆临时产物）。这个文件是**快照台账**：
每轮跑完把 `benchmark.md` 的结论记一行，这样「技能改好还是改坏了」有据可查。

跑完一轮之后：

```bash
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

把 `results/iteration-N/benchmark.md` 的表格贴到下面。

---

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

## 关于 iteration-0-smoke

harness 刚搭好时用「参考解的真实 grading + 一条手工造的 without_skill」做过一次冒烟，
用来验证 `bench` 的汇总与 analyst pass。**那份数据是编的，已经删掉**——不能跟真实运行
混在一起当证据。

## 每条臂要留什么

- `grading.json` — `assert_case` 的机械核对结果（断言、证据、通过率）
- `benchmark.json` / `benchmark.md` — 该轮的汇总（在 iteration 目录下）
- `notes.md` — 跑那条臂时的观察，尤其是**断言无效**的原因（例如 Lead 在跑臂期间改了仓库）

⚠️ **`timing.json` 目前是缺的**：子代理通知里的 tokens / duration 只在通知里出现一次，
前几轮没当场落盘，所以 benchmark 里的用时与 tokens 都是 0。后续每轮收到通知就写。
