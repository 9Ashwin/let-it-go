# benchmark — flow

用例：t1-serial-batch, t1-single-unit, t1-vague-request

| 配置 | pass_rate | 用时(s) | tokens |
|---|---|---|---|
| with_skill | 1.00 ± 0.00 | 275.5 | 971992 |
| without_skill | 0.71 ± 0.09 | 34.8 | 98385 |
| **delta** | **+0.2917** | +240.7 | +873607.8 |

## 逐用例

| 用例 | 配置 | 每次 | 判定 |
|---|---|---|---|
| t1-serial-batch | with_skill | 8/8 / 8/8 / 8/8 | 通过 |
| t1-serial-batch | without_skill | 5/8 / 5/8 / 5/8 | 不通过 |
| t1-single-unit | with_skill | 6/6 / 6/6 / 6/6 | 通过 |
| t1-single-unit | without_skill | 5/6 / 5/6 / 5/6 | 不通过 |
| t1-vague-request | with_skill | 6/6 / 6/6 / 6/6 | 通过 |
| t1-vague-request | without_skill | 4/6 / 4/6 / 4/6 | 不通过 |

**判定口径：一次都没全过就不算通过。** 同一配置的每次运行都是 100% 才是「通过」；每次都一样但不满分是「不通过」；几次之间不一致是 **flaky，不算通过**——60% 不是通过。

## 断言区分度（用例 × 断言）

| 用例 | 断言 | with_skill | without_skill | 判定 |
|---|---|---|---|---|
| t1-serial-batch | fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿） | 3/3 | 3/3 | 底线（必留） |
| t1-serial-batch | 两张卡的行为都真的实现了（Slug 与 JoinSlug） | 3/3 | 3/3 | 底线（必留） |
| t1-serial-batch | 串行批次产生了检查点，且落在 requirements/<scope>/issues/ 下 | 3/3 | 3/3 | 两边满分（无区分度 → 删掉或改成能失败的形态） |
| t1-serial-batch | 先加载了实现入口 loop-it（这一层量的是技能契约本身，不是结果） | 3/3 | 0/3 | 区分 |
| t1-serial-batch | 开工先开了 goal（事件流里有 create_goal，CONTRACT §6） | 3/3 | 0/3 | 区分 |
| t1-serial-batch | 改动之后 fixture 自己的门禁 make check 仍然绿（在集成态上） | 3/3 | 3/3 | 底线（必留） |
| t1-serial-batch | 检查点里的证据带了层（每条 evidence 都标了 L1–L4，CONTRACT §4） | 3/3 | 0/3 | 区分 |
| t1-serial-batch | 没有以「等你回复」结束回合（CONTRACT §5） | 3/3 | 3/3 | 两边满分（无区分度 → 删掉或改成能失败的形态） |
| t1-single-unit | Slug 的行为真的对了（大小写、首尾空白、连续空白） | 3/3 | 3/3 | 底线（必留） |
| t1-single-unit | fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿） | 3/3 | 3/3 | 底线（必留） |
| t1-single-unit | 先加载了实现入口 loop-it（这一层量的是技能契约本身，不是结果） | 3/3 | 0/3 | 区分 |
| t1-single-unit | 单单元零仪式：不产生 loop 检查点（CONTRACT §3 的硬契约） | 3/3 | 3/3 | 两边满分（无区分度 → 删掉或改成能失败的形态） |
| t1-single-unit | 改动之后 fixture 自己的门禁 make check 仍然绿 | 3/3 | 3/3 | 底线（必留） |
| t1-single-unit | 没有以「等你回复」结束回合（CONTRACT §5） | 3/3 | 3/3 | 两边满分（无区分度 → 删掉或改成能失败的形态） |
| t1-vague-request | Slug 的行为真的对了（大小写、首尾空白、连续空白） | 3/3 | 3/3 | 底线（必留） |
| t1-vague-request | fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿） | 3/3 | 3/3 | 底线（必留） |
| t1-vague-request | 先加载了规划入口 prd（一句诉求 + 落地方式自己定 → 不是单单元） | 3/3 | 0/3 | 区分 |
| t1-vague-request | 改动之后 fixture 自己的门禁 make check 仍然绿 | 3/3 | 3/3 | 底线（必留） |
| t1-vague-request | 没有以「等你回复」结束回合（CONTRACT §5：问不到人就自己定并标 [Assumption]） | 3/3 | 3/3 | 两边满分（无区分度 → 删掉或改成能失败的形态） |
| t1-vague-request | 规划半边真的走了：scope 下产出了 PRD | 3/3 | 0/3 | 区分 |

判定只看两条臂的**通过率差**与**同臂多次之间的一致性**。`gate` / `probe` / `tamper_guard` 是每条用例的结果底线（evals/AGENTS.md 强制），标「底线（必留）」；删留规则管的是其余契约断言（过程传感器）。

## 观察

- 断言「Slug 的行为真的对了（大小写、首尾空白、连续空白）」在两条臂上都通过——它区分不出技能的价值
- 断言「fixture 的门禁与自带断言逐字节未变（不许把测试改弱来换绿）」在两条臂上都通过——它区分不出技能的价值
- 断言「两张卡的行为都真的实现了（Slug 与 JoinSlug）」在两条臂上都通过——它区分不出技能的价值
- 断言「串行批次产生了检查点，且落在 requirements/<scope>/issues/ 下」在两条臂上都通过——它区分不出技能的价值
- 断言「单单元零仪式：不产生 loop 检查点（CONTRACT §3 的硬契约）」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿」在两条臂上都通过——它区分不出技能的价值
- 断言「改动之后 fixture 自己的门禁 make check 仍然绿（在集成态上）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有以「等你回复」结束回合（CONTRACT §5）」在两条臂上都通过——它区分不出技能的价值
- 断言「没有以「等你回复」结束回合（CONTRACT §5：问不到人就自己定并标 [Assumption]）」在两条臂上都通过——它区分不出技能的价值
- 用例「t1-serial-batch」波动大（62%–100%），可能是 flaky
- 用例「t1-vague-request」波动大（67%–100%），可能是 flaky
