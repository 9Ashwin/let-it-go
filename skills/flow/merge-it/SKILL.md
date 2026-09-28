---
name: merge-it
description: "把已经开好的 PR 合入：先摆出要合的东西与 checks 状态，再合入、关 issue、回默认分支同步；本地模式没有 PR 时做本地 --no-ff 合入。只有人能敲它——合入不可逆，模型不该自己决定。"
disable-model-invocation: true
---

# merge-it — 合入（人的动作）

`/ship-it` 把东西准备到「PR 开着、证据齐、等着合」；**合入这一步交回给人**，就是这一份。

**为什么单独一份、而且只有人能敲。** 开 PR 是可逆的，也是给人看的；合入不可逆，而且在开源项目里合入本来就是维护者的动作。**门禁要落在机制上**——所以它是一个模型碰不到的技能，而不是 `ship-it` 里的一句叮嘱。写在提示里的保证不是保证。

工作状态、证据层、产物落点、放行判据见 [`../loop-it/CONTRACT.md`](../loop-it/CONTRACT.md)。

## 何时调用

- 人明确说要合入：`/merge-it`、「合入这个 PR」、「merge it」。
- **模型不要自己走到这里。** 一批活跑到批末，`/ship-it` 开完 PR 就停，把合入的命令打给人。
- 前置：PR 已开、checks 绿、放行判据满足（**门禁绿 + 每条验收条件有它那一层的证据**）。缺证据就回去补观测，不要先合了再补。

## 先解析，别假设

```bash
git remote -v
gh auth status 2>/dev/null
git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||'   # 可能是 master，别写死 main
gh pr view --json number,title,mergeStateStatus,statusCheckRollup
```

## 步骤

### 1. 合入前先把清单摆出来

这是有副作用的一步：PR 编号与标题、它关闭哪些 issue、逐项证据（commit / issue / 验收证据 / 人工验收状态）、checks 状态，一起摆给人当场接住。这批收进多个 issue 时尤其要摆。

### 2. 确认 checks 绿

```bash
gh pr checks
```

有失败项就**不要合**：回到那条分支修，追加 commit 推送，再回来。

### 3. 合入

```bash
gh pr merge --squash --delete-branch      # 或 --merge / --rebase
```

被 branch protection 挡住时，先看它要什么（required checks / reviews），满足后重试。**不要用 `--admin` 绕门禁。**

一批多 issue 共用一个 PR 时，commit 列已经在 PR body 的证据表里——squash 之后那些提交在默认分支上看不见了，撤销单项就按表里的 commit 手工 revert。

### 4. 关闭 issue

PR body 里写了 `Closes #N` 的已经自动关。没关的：

```bash
gh issue close {issue-number} --reason completed
```

### 5. 回到默认分支并同步

```bash
git checkout <默认分支> && git pull
```

## 本地模式（没有远端，或 gh 没登录）

没有 PR 可合，合入就是把需求分支落回默认分支：

```bash
git checkout <默认分支>
git merge --no-ff feat/<scope-slug>
```

用 `--no-ff` 留一个合并点：批末要按 commit 追溯与回滚单个 issue，快进合入会把那串 commit 抹平成「看起来像直接在默认分支上写的」。**合并后不要删分支**——它是这批工作的唯一留档。

本地模式下 issue 是仓库里的 md 卡片，没有 `gh` 可走：把 `<scope>/issues/` 里对应条目的状态改成已交付，把 commit 与验收证据写进去。**别去 `gh issue close` 关一个不存在的 issue。**

## 失败怎么办

| 场景 | 处理 |
|---|---|
| `gh pr checks` 有失败项 | 不合入；回分支修，追加 commit 推送 |
| PR 有 merge conflict | `git fetch origin <默认分支> && git rebase origin/<默认分支>`，解冲突后 force push（这条分支只有你在推） |
| 被 branch protection 阻止 | 看它要什么，满足后重试；**不要 `--admin`** |
| issue 合入后没自动关 | 确认 PR body 含 `Closes #N`，否则手动 `gh issue close` |
| 合入后想撤销整批 | `git revert -m 1 <merge-commit>`；撤销单项按证据表里的 commit 逐个 revert |
| 没有远端 | **本地模式**，不是错误——按上面那一节走，**不要为此新建远端** |
