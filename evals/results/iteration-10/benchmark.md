# benchmark — flow

用例：04-serial-batch, 05-full-pipeline

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 486.1 | 2690598 |
| without_skill | 0.78 ± 0.00 | 110.4 | 526997 |
| **delta** | **+0.2222** | +375.6 | +2163601.5 |

## 逐用例

| 用例 | 配置 | 通过 | pass_rate |
|---|---|---|---|
| serial-batch | with_skill | 9/9 | 100% |
| serial-batch | with_skill | 9/9 | 100% |
| serial-batch | with_skill | 9/9 | 100% |
| full-pipeline | with_skill | 9/9 | 100% |
| full-pipeline | without_skill | 7/9 | 78% |

## 观察

- 断言「fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿）」在两条臂上都通过——它区分不出技能的价值
- 断言「scope 目录本身建起来了（需求资料落在仓库声明的作用域根下）」在两条臂上都通过——它区分不出技能的价值
- 断言「三条 issue 的行为都真的实现了（阈值来源、列表顺序、报告）」在两条臂上都通过——它区分不出技能的价值
- 断言「串行批次产生了检查点，且落在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「批末把需求分支推到了 origin（技能说 push 只在批末做一次）」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿（在集成态上）」在两条臂上都通过——它区分不出技能的价值
- 断言「整批只有一条 feat 分支（技能说一个需求一条分支，不逐 issue 开）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有写到 fixture 之外（臂的 cwd 就是 fixture，越界是这条路的典型失败）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有落到技能默认的 tasks/<feature>/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「若产生了 loop 检查点，它必须在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「这条分支上至少三个 commit（一个 issue 一个，单个 issue 才回滚得掉）」在两条臂上都通过——它区分不出技能的价值
- 断言「阈值真的能按仓库配置，没配的回退默认值」在两条臂上都通过——它区分不出技能的价值
- 缺少这些臂的结果：04-serial-batch/without_skill
