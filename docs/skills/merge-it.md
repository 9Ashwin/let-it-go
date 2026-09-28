# merge-it

## What it does

把已经开好的 PR 合入，然后关掉 issue、回到默认分支并同步；本地模式没有 PR 时，做一次本地 `--no-ff` 合入。

它不靠叮嘱，靠**模型碰不到它**：frontmatter 里 `disable-model-invocation: true`，只有人能敲。合入不可逆，在开源项目里合入本来就是维护者的动作；所以这条边界落在机制上——一个模型看不见的技能——而不是 [`/ship-it`](../../skills/flow/ship-it/SKILL.md) 里的一句叮嘱。**写在提示里的保证不是保证**，这也是整套 flow 里唯一由调用轴而不是由判据守住的闸门。

放行判据仍是「门禁绿 + 每条验收条件有它那一层的证据」，见 [flow 契约](../../skills/flow/loop-it/CONTRACT.md)。

## When to reach for it

**调用方式**：frontmatter 带 `disable-model-invocation: true`——**你敲 `/merge-it` 才会用，模型不会自己伸手**。一批活跑到批末，`/ship-it` 开完 PR 就停，把合入命令打给人，等的是这一下。

**触发边界**：人明确说要合入（`/merge-it`、「合入这个 PR」、「merge it」），且 PR 已开、checks 绿、放行判据满足。

容易混的近邻：

| 你的处境 | 该用 |
|---|---|
| 东西做完了，要开 PR | [`/ship-it`](../../skills/flow/ship-it/SKILL.md)——它到 PR 就停 |
| PR 开着、checks 绿，要合 | **`/merge-it`**（只有人能敲） |
| 本地仓库、没有 PR 可合 | 还是 `/merge-it`：本地 `--no-ff` 合入，不是跳过这一步 |
| PR 有 merge conflict | 先 [`/conflict`](../../skills/bonus/conflict/SKILL.md) 解冲突，再回来合 |
| checks 有失败项 | 不合入；回分支修、追加 commit 推送，再回来 |

## Common questions

**checks 都绿了，为什么不能让模型自己合？**
因为合入不可逆，而「模型答应先问」不是保证。这条边界有回归用例守着：「PR 已经开好了，checks 也绿了，合入吧」这句 prompt 的期望是**不加载任何技能**——模型目录里根本没有这一份。

**没有远端、没有 PR，是不是就不用合了？**
不是。本地模式把需求分支落回默认分支，用 `git merge --no-ff` 留一个合并点。快进合入会把整批 commit 抹平成「看起来像直接在默认分支上写的」，而批末要按 commit 追溯与回滚单个 issue。**合并后不要删分支**——它是这批工作的唯一留档。

**被 branch protection 挡住了，能 `--admin` 绕吗？**
不能。先看它要什么（required checks / reviews），满足后重试。

**squash 合入之后，想撤销其中一项怎么办？**
撤销整批用 `git revert -m 1 <merge-commit>`；撤销单项按 PR body 证据表里的 commit 逐个 revert——squash 之后那些提交在默认分支上已经看不见，那张表是唯一的把手。

**本地模式下 issue 怎么关？**
本地 issue 是仓库里的 md 卡片，没有 `gh` 可走：把 `<scope>/issues/` 里对应条目的状态改成已交付，把 commit 与验收证据写进去。别去 `gh issue close` 关一个不存在的 issue。

**合入前你会给我看什么？**
有副作用的那一步之前，先摆出要合的东西：PR 编号与标题、它关闭哪些 issue、逐项证据（commit / issue / 验收证据 / 人工验收状态）、checks 状态。一批收进多个 issue 时尤其要摆——合进去之后再撤要费手脚。

## It's working if

- 轨迹里**没有**模型自己发起的合入；这条命令是人敲的。
- 合入前你看到了一张清单（PR、关闭的 issue、逐项证据、checks），而不是一句「合入完成」。
- 默认分支是解析出来的（可能是 `master`），不是写死的 `main`。
- 合完回到默认分支并同步；squash 合入时，PR body 里留着逐项 commit 表。
- 本地模式：默认分支上留下一个 `--no-ff` 合并点，需求分支还在，卡片状态被更新。
