# 不做第二份真相

工作状态只有一个对象、契约只有一个载体、规则只有一个维护层级。PRD 长文、SPEC 长文、走查件、
批末评论都是它的**投影**——只引用，不复制第二份真相；能只从状态 + issue 正文 + 代码重新推出来的
文档，删掉不损失信息（[CONTRACT §1](../skills/flow/loop-it/CONTRACT.md)）。

## 为什么不

issue #3 的病根就是**同一条规则五处各写一遍**：计划散在 PRD / issue 正文 / scope README / 检查点
四处时，同一个问题会有三种口径，agent 遇到它就无法判断该信谁。冲突时以谁为准这件事，一旦需要
「看情况」，就等于没有真相源。

## 逃生通道

- **要复述 → 指向唯一说明，不抄。** [`../skills/flow/loop-it/CONTRACT.md`](../skills/flow/loop-it/CONTRACT.md) 的
  「维护层级」写清了每一层该写什么、不写什么：`scripts/` 是机器行为真相、`SKILL.md` 只写何时调用
  与边界、`references/` 放解释与排障、`README`/`docs` 是项目地图、`evals/` 验证契约。
- **要摘要 → 不做「摘要的摘要」。** 如果需要再生成一份更短的版本才能读，那说明该写的不是文档，
  是状态——`loop_state.py summary` 那张短表就是人读的形态。
- **投影与状态冲突 → 以状态为准。** 走查件与 PR body 引用 scope README 的验收表，不再复制一份。

## 历史上谁提过

- **issue #3 第一刀**：`skills/flow/loop-it/CONTRACT.md` 成为 flow 的唯一真相源，七份 `SKILL.md` 只写
  「何时调用、边界、失败怎么办」。
- **loop-it / graph 收尾那轮**：两份 416 / 303 行的 `SKILL.md` 缩到 211 / 199 行，长表搬进
  `references/batch-model.md` 与 `references/planning.md`，正文只留判断 + 指针。
- **合入拆分那轮**：`/ship-it` 与 `/merge-it` 的边界写一次，另一处只指路。
