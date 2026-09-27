# 历轮结果

`results/` 不进版本库（跑一轮会产生一堆临时产物）。这个文件是**快照台账**：
每轮跑完把 `benchmark.md` 的结论记一行，这样「技能改好还是改坏了」有据可查。

跑完一轮之后：

```bash
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

把 `results/iteration-N/benchmark.md` 的表格贴到下面。

---

## iteration-0-smoke

不是真实运行，是 harness 的冒烟验证：用参考解的真实 grading（7/7）加一条手工造的
`without_skill`（3/7）检查 `bench` 的汇总与 analyst pass 对不对。

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 0.0 | 0 |
| without_skill | 0.43 ± 0.00 | 0.0 | 0 |
| **delta** | **+0.5714** | +0.0 | +0.0 |

analyst pass 当场就标出三条断言在两条臂上都通过——它们区分不出技能的价值。这正是它该做的。
