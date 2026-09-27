# benchmark — flow

用例：02-mid-flight-change

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 0.86 ± 0.00 | 0.0 | 0 |
| without_skill | 1.00 ± 0.00 | 0.0 | 0 |
| **delta** | **-0.1429** | +0.0 | +0.0 |

## 逐用例

| 用例 | 配置 | 通过 | pass_rate |
|---|---|---|---|
| mid-flight-change | with_skill | 6/7 | 86% |
| mid-flight-change | without_skill | 7/7 | 100% |

## 观察

- 断言「fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿）」在两条臂上都通过——它区分不出技能的价值
- 断言「作废的来源没有留下来（不许两套并存）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有写到 fixture 之外（子代理没有自己的 cwd，越界是这条路的典型失败）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有落到技能默认的 tasks/<feature>/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「若产生了 loop 检查点，它必须在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「阈值真的从**变更后**的来源（config/thresholds.json）生效，默认值也按变更后（10）」在两条臂上都通过——它区分不出技能的价值
