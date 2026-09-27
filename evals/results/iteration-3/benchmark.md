# benchmark — flow

用例：03-artifact-handoff

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 0.0 | 0 |
| without_skill | 1.00 ± 0.00 | 0.0 | 0 |
| **delta** | **+0.0000** | +0.0 | +0.0 |

## 逐用例

| 用例 | 配置 | 通过 | pass_rate |
|---|---|---|---|
| artifact-handoff | with_skill | 6/6 | 100% |
| artifact-handoff | without_skill | 6/6 | 100% |

## 观察

- 断言「fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿）」在两条臂上都通过——它区分不出技能的价值
- 断言「只凭那份资料就做对了 issue-002：数量升序，同数量按名字」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿」在两条臂上都通过——它区分不出技能的价值
- 断言「没有写到 fixture 之外（子代理没有自己的 cwd，越界是这条路的典型失败）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有落到技能默认的 tasks/<feature>/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「若产生了 loop 检查点，它必须在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
