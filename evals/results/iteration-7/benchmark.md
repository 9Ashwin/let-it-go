# benchmark — flow

用例：01-single-unit, 02-mid-flight-change

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 206.5 | 774130 |
| without_skill | 1.00 ± 0.00 | 78.7 | 522660 |
| **delta** | **+0.0000** | +127.8 | +251470.0 |

## 逐用例

| 用例 | 配置 | 通过 | pass_rate |
|---|---|---|---|
| single-unit | with_skill | 6/6 | 100% |
| single-unit | without_skill | 6/6 | 100% |
| mid-flight-change | with_skill | 7/7 | 100% |
| mid-flight-change | without_skill | 7/7 | 100% |

## 观察

- 断言「fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿）」在两条臂上都通过——它区分不出技能的价值
- 断言「作废的来源没有留下来（不许两套并存）」在两条臂上都通过——它区分不出技能的价值
- 断言「按仓库配置的阈值真的生效，且缺省回退到默认值」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿」在两条臂上都通过——它区分不出技能的价值
- 断言「没有写到 fixture 之外（臂的 cwd 就是 fixture，越界是这条路的典型失败）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有落到技能默认的 tasks/<feature>/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「若产生了 loop 检查点，它必须在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「阈值真的从**变更后**的来源（config/thresholds.json）生效，默认值也按变更后（10）」在两条臂上都通过——它区分不出技能的价值
