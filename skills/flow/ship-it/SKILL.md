---
name: ship-it
description: "把做完的工作交付到「PR 就绪」：提交、推分支、开 PR、补一条实现总结评论，然后停下把合入交给人（/merge-it）。有远端走 GitHub CLI；没有远端或 gh 没登录时走本地模式，只准备好交付资料、不落默认分支。Triggers: 提交代码, 创建PR, ship-it, commit and pr."
---

# ship-it — 把做完的东西交付到「PR 就绪」

提交 → 推送分支 → 开 PR → 补一条实现总结评论。**到这里停。**

**合入不在这里。** 合入是不可逆的对外动作，归 [`/merge-it`](../merge-it/SKILL.md)——那一份只有人能敲。开 PR 是可逆的、也是给人看的，所以留在这里。

工作状态、证据层、产物落点、放行判据都在 [`../loop-it/CONTRACT.md`](../loop-it/CONTRACT.md)——本文件只写**何时调用、边界、失败怎么办**，不复述它。

## 何时调用

- 实现跑完、项目门禁是绿的，且**每条验收条件都拿到了它那一层**的证据。
- 单单元路径在 `/loop-it` 里内联收尾；串行批次在**批末**调一次；并行图在 **fan-in** 调一次。
- 用户说「提交代码 / 创建 PR / ship-it」。

**放行判据是「门禁绿 + 每条验收条件有它那一层的证据」，不是任何人的批准。** 缺证据就回去补观测，不要先把 PR 开了再补。

## 两条路：先解析，再动手

```bash
git remote -v                                  # 没有 origin 就是本地模式
gh auth status 2>/dev/null                     # 非 0 就是本地模式
git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||'
```

| | **远端模式**（有 origin 且 `gh` 已登录） | **本地模式**（无远端 / gh 不可用） |
| --- | --- | --- |
| 推分支 | `git push -u origin` | **不推**——没有远端 |
| 交付落点 | PR | 需求资料里的交付记录（检查点 `note` 或卡片） |
| 关 issue / 合入 | 见 [`/merge-it`](../merge-it/SKILL.md) | 见 [`/merge-it`](../merge-it/SKILL.md) |

**不要因为「技能写的是 PR」就去建一个远端。** 实测过一次：仓库本来没有 remote，编排者照 PR 流程走不通，最后自己用本地 `git merge` 收了尾——那正是本地模式该做的事，但技能没写，于是它成了没人维护的临场发挥。

## 步骤

### Step 0：先备好证据——走查件（批 / 波）

交付前先写走查件；没有它，PR body 里的验收证据只能靠回忆写，而回忆不是证据。给谁看、多长、哪些不算证据见 [`references/walkthrough.md`](references/walkthrough.md)。

- **范围：每批或每波一份**，与评审、交付同一个范围，**绝不逐 issue 一份**——逐 issue 的走查证明的是一份可能活不过集成的 diff，而一批只有一个 PR。单单元路径不写走查件（契约 §3）。
- **承载 L3/L4 的证据**：真的把跑起来的东西点一遍。纯 L1/L2 的改动可以不写，证据照旧记进检查点。
- **上限 ≤ 30 行**：一条命令 + 关键输出 + 截图路径。**原始输出倾倒不是证据，是噪音**——要留完整输出就给路径，不贴进来。
- **它是工作状态的投影**，不是第二份真相：契约字段住在 issue 正文，逐条观测的机器真相在检查点，走查件只引用它们（契约 §1）。**`人工验收状态` 如实标注即可，它不是闸门**——没走过主路径就写「尚未人工验收」。

### Step 1：提交代码

```bash
git status && git diff --stat HEAD
git add <本次改动相关的文件>            # 不混入不相关的变更
git commit -m "{概括这次改动}"
```

一个需求分支上**每个 issue 一个 commit**（`/loop-it` 实现时就地产生），交付前只补提交剩下的（走查件、收尾修的东西）。commit message 用 Conventional Commits 概括改动，**不带 issue 编号**——编号由分支名与 PR body 的 `Closes #N` 承载。

### Step 2：推送分支（仅远端模式）

```bash
git checkout -b feat/<scope-slug>      # 已在需求分支上就跳过
git push -u origin feat/<scope-slug>
```

**一个需求一条分支**（`/loop-it` 的整批、`/graph` 的一波都落在这一条上）；只有单个 issue 的独立小改动才用 `feat/issue-42-short-desc`。本地模式**跳过这一步**，直接去 Step 4。

### Step 3：开 PR（仅远端模式）

```bash
gh pr create --title "{概括这次交付}" --body "$(cat <<'EOF'
## Summary
- {本次交付的变更概述，3-5 条}
Closes #{issue-number}

## 证据
{逐条验收条件 → 它那一层 → 观测命令与结果；引用 issue 正文的契约字段与检查点里的 evidence}
EOF
)"
```

PR body 写 `Closes #N` 或 `Fixes #N`（**合入后**自动关 issue），title ≤ 70 字符。**它是投影**：不重抄契约字段，也不重抄走查件——引用它们（契约 §1）。本地模式**跳过这一步**。

### Step 4：补一条实现总结评论

远端模式在 issue 上补；**本地模式**没有 issue 可评论，同样四类写进**需求资料**——检查点里对应条目的 `note`，或卡片本身，别在两处各写一份。

```bash
gh issue comment {issue-number} --body "$(cat <<'EOF'
## 实现总结
**进度** — {核心变更 3-5 条；PR #N / commit {hash}}
**关键决策** — {设计决策；有意偏离 spec 之处：spec 怎么说 → 实际怎么做 → 为什么；考虑过的备选与最终选择}
**验证记录** — {逐条验收条件 → 它那一层 → 命令与结果；引用检查点里的 evidence，不重抄原始输出}
**未决事项** — {待用户确认的假设或后续跟进项}
---
- **PR**: #{pr-number} · **Commit**: {hash}
EOF
)"
```

- 四类固定：**进度 / 关键决策 / 验证记录 / 未决事项**；某类无内容写 `None` 并简要说明。**批级的**设计决策 / 偏离 / 权衡 / 待确认就在这里承载一次（逐 issue 的那份在检查点 `note`），只产出一次——用户明确要了 `docs/issue#NNNN.md` 那种文件时附链接，不重抄。
- **验证记录是投影**：指向检查点与走查件，不复制第二份真相（契约 §1）。

### Step 5：停在这里，把合入交给人

**不要自己合。** 报告一句，把命令打给人：

```
✅ PR #43 已开：{url}
   证据：{n} 条验收条件全部有它那一层的观测
   合入 → /merge-it（或：gh pr merge --squash --delete-branch）
```

本地模式同理：交付资料写完就停，**`git merge` 那一步归 [`/merge-it`](../merge-it/SKILL.md)**。

## 多个 issue 共用一个 PR（批 / 波末）

一批或一波默认把多个 issue 收进同一个 PR（squash 后只剩一个 commit）。此时 PR body（本地模式：需求资料）**必须逐项列出证据**，不能只写一行 `Closes #1 #2 #3`——否则单项特性既没法审计也没法单独回滚。

| 项 | commit | 关闭的 issue | 验收证据（测试名 / 命令） | 人工验收 |
| --- | --- | --- | --- | --- |
| 节点 3 | `abc1234` | Closes #12 | `TestFooBar` | 尚未人工验收 |
| 节点 4 | `def5678` | Closes #13 | `mise run check` + `TestBaz` | 尚未人工验收 |

- **commit 列必填**：squash 后这些提交在默认分支上已经看不到，只有写下来才能按项追溯与回滚（撤销单项就按上表 commit 手工 revert）。
- **验收证据要具体**：写测试名或命令，不写「测试通过」；**逐项关闭 issue**：每项各自写 `Closes #N`，不要合成一行。
- **人工验收逐项如实标注**：没走过主路径就写「尚未人工验收」，只有用户明确确认后才改并注明确认依据（时间 / 环境）。**这是标注，不是闸门**——放行只看门禁与证据。
- 单项 PR 不需要这张表。

## 失败怎么办

| 场景 | 处理方式 |
|------|---------|
| `gh pr create` 失败（无权限 / 分支没推） | 先确认分支推上去了、`gh auth status` 通；权限不够就按本地模式收尾，**不要新建远端** |
| `gh` 未装 / 未登录 / 没有 origin | **本地模式**，不是错误——按上面本地一列走 |
| 提交时混进了不相关的变更 | `git reset HEAD <file>` 撤出暂存，别把无关改动带进这个 commit |
| 用户要的是一次性 PR，不是批末交付 | 按单项 PR 走：一张卡一条分支一个 PR，仍然**不合入** |

## 示例（远端模式）

```bash
git checkout -b feat/case-model && git push -u origin feat/case-model
gh pr create --title "Add Case data model and Markdown read/write" --body "$(cat <<'EOF'
## Summary
- Define Case struct with YAML frontmatter + Markdown body
Closes #42
## 证据
- 读写往返：L2，`go test ./cases/ -run TestWriteReadCase` → ok
EOF
)"
gh issue comment 42 --body "$(cat <<'EOF'
## 实现总结
**进度** — Case 数据模型 + 读写函数（PR #43 / abc1234）
**关键决策** — body 与 frontmatter 分离存储，便于人工编辑与 diff
**验证记录** — 见检查点 evidence（L2 读写往返）
**未决事项** — None
EOF
)"
# 停。合入 → /merge-it
```
