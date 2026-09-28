# 单单元不产生检查点

单单元 profile **不碰 `.loop-state.json`**：不建检查点、不建 worktree、不开 graph 波次。这是
[CONTRACT §3](../skills/flow/loop-it/CONTRACT.md) 的硬契约，不是「小任务可以省一点」的优化。

## 为什么不

单单元的定义是「整个改动装得进一个上下文」——读清楚、内联实现、门禁自证、commit，四步走完。
检查点存在的理由是**跨回合、跨会话恢复一批活**：它记 `next_action`、`attempts`、`branch`，
由脚本在每次状态转换时落盘。一件装得进一个上下文的事不需要恢复机制，加上它只会带来两样东西：

- **第二份真相**：`.loop-state.json` 里会出现一份与当前上下文并行的状态，两者不一致时没人知道该信谁。
  这正是 issue #3 的病根（同一件事在多处各记一份）。
- **仪式量倒挂**：[CONTRACT §3](../skills/flow/loop-it/CONTRACT.md) 写的是「三个 profile 的仪式量差一个数量级」，
  单单元加上检查点之后，最简单的路径反而先落一次盘、再读一次盘。

判据是**形态**，不是规模感：一条 issue、一张卡、spec 里的一项，装得进一个上下文就是单单元。

## 逃生通道

- 手上有多条有阻塞边的卡片 → 那是**串行批次**，检查点本来就该有（`/loop-it` 的默认路径）。
- 一条 issue 但改动大到装不进一个上下文 → 那不是单单元：先 `/prd` → `/to-issues` 拆开，再进批次。
- 想要「恢复」能力又不想付检查点的代价 → 用 goal（`create_goal`）撑住续跑，位置由当前上下文与
  git 历史承载；**批次才需要检查点**，这是两个不同的东西（CONTRACT §6）。

## 历史上谁提过

- **issue #3（flow 契约合并）第一刀**：把「单单元零仪式」写成硬契约，并让
  `evals/cases/01-single-unit` 用机械断言守着它——`checkpoint_absent`、`.git/worktrees` 不存在、
  事件流里没有 `workflow` 调用。
- **T1 第一刀**（[evals/NEXT.md](../evals/NEXT.md)）：新增 `t1-single-unit`，把同一件事做成分钟级的
  回归网，每次改 `SKILL.md` 正文都跑；`checkpoint_absent` 在两条臂上都是 3/3，作为回归守卫保留
  （负例见 `evals/harness/events_test.go`）。
