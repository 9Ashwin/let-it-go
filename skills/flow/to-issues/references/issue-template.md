# issue 契约字段块

**issue 正文就是契约**（[`../../CONTRACT.md`](../../CONTRACT.md) §1）。两种载体，字段一模一样：GitHub issue 正文，或作用域里的 `issues/NN-<slug>.md`。没有第二份要放在上下文里的 SPEC——目标、非目标、验收条件、外部边界、证据、完成定义、未决问题全在正文里，所以一个不共享这段对话的全新子代理拿起来就能照它行事。

让这些字段保持诚实：**一条没有观测能证明的验收条件不算验收条件。**

## GitHub 正文

```
issue #N: [标题——一个行为，不是一层]
---
Goal: [这次端到端交付的是什么行为，以及为什么]
Non-goals: [明确不做什么——作用域围栏]
Demo path: [它落地后你能演示的那一件事]
Acceptance Criteria:
- [ ] [可证伪——点出一个在基线 commit 上会失败的观测]
- [ ] ...
Evidence required: [每条验收条件对应哪个能证明它的观测——测试名、命令、页面、查询。绝不写"测试通过"。]
External boundary: [要让这条算数，什么必须是真的——跑着的服务、数据库、第三方 API、人工检查。改动是纯本地的就写 "None"。]
Definition of done: [门禁全绿 + 每条验收条件都带着证据 + 演示路径真的跑过]
Human checkpoint: [碰了危险面的卡写清停点（见 CONTRACT §5）；否则 None]
Open questions: [每条未决项：认领人，或「按 X 假设推进」[Assumption]。不许写 None]
Blocked by: [None / issue #X, #Y]
Priority: [high / medium / low]
```

## 本地文件骨架

落点 `<scope>/issues/NN-<slug>.md`（`NN` 补零，是真实卡片 ID）：

```markdown
# [标题——一个行为]

## Goal
[这次端到端交付的是什么行为，以及为什么]

## Non-goals
[明确不做什么]

## Demo path
[它落地后你能演示的那一件事]

## Acceptance Criteria
- [ ] [可证伪的验收条件 1]
- [ ] [可证伪的验收条件 2]

## Evidence required
[每条验收条件对应：能证明它的观测——测试名、命令、页面、查询]

## External boundary
[要让这条算数，什么必须为真；纯本地的就写 "None"]

## Definition of done
[门禁全绿 + 每条验收条件都带着证据 + 演示路径跑过]

## Human checkpoint
[碰了危险面的卡写清停点；否则 None]

## Open questions
[每条未决项：认领人，或「按 X 假设推进」[Assumption]]

## Blocked by
[None / #NN, #NN]

## Priority
[high / medium / low]
```

## 契约质量检查（发布任何东西之前）

- [ ] 每条验收条件都对应一份**可观测**的证据，而不是"测试通过"
- [ ] 没有留下 `TBD` / `TODO` —— 现在就解决，或挪进 Open questions 并给它归宿
- [ ] 失败路径在验收条件里有位置，不只是顺利路径
- [ ] 非目标写清楚了，否则实现会自己扩作用域
- [ ] 外部边界说清了要让这条算数什么必须*为真*——本地假实现只证明得了本地契约
- [ ] 完成定义包含"演示路径真的跑过"，而不是"代码看起来对"
- [ ] 每条 Open question 要么有人认领，要么显式写下「按 X 假设推进」（`[Assumption]`）——**`None` 是没想，不是没有**

反模式：把请求换种说法当成一条验收条件；为没有特殊逻辑的 CRUD 写算法章节；不看项目已经在用什么就选技术；列出在基线 commit 上已经为真的行为；把文件路径和行号写进正文。
