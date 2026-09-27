# 历轮结果

`results/` 不进版本库（跑一轮会产生一堆临时产物）。这个文件是**快照台账**：
每轮跑完把 `benchmark.md` 的结论记一行，这样「技能改好还是改坏了」有据可查。

跑完一轮之后：

```bash
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

把 `results/iteration-N/benchmark.md` 的表格贴到下面。

---

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

## iteration-0-smoke

不是真实运行，是 harness 的冒烟验证：用参考解的真实 grading（7/7）加一条手工造的
`without_skill`（3/7）检查 `bench` 的汇总与 analyst pass 对不对。

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 0.0 | 0 |
| without_skill | 0.43 ± 0.00 | 0.0 | 0 |
| **delta** | **+0.5714** | +0.0 | +0.0 |

analyst pass 当场就标出三条断言在两条臂上都通过——它们区分不出技能的价值。这正是它该做的。
