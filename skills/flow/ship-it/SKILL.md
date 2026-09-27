---
name: ship-it
description: "交付已完成的工作：提交、推送、开 PR、合入、关闭 issue，再补一条实现总结评论。有远端走 GitHub CLI；仓库没有远端或 gh 没登录时走本地合入。Triggers: 提交代码, 创建PR, 合入, 关闭issue, ship-it, commit and merge."
---

# After-Goal: 代码提交、合入、Issue 关闭工作流

完成实现后的标准收尾流程：提交代码 → 合入 → 关闭 Issue → 补实现总结。

## 先决定走哪条路

**在动手之前先解析：这个仓库有没有可用的远端，`gh` 是不是已登录。**

```bash
git remote -v                                  # 没有 origin 就是本地模式
gh auth status 2>/dev/null                     # 非 0 就是本地模式
git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||'
```

| | **远端模式**（有 origin 且 `gh` 已登录） | **本地模式**（无远端 / gh 不可用） |
| --- | --- | --- |
| 提交 | 一样 | 一样 |
| 推分支 | `git push -u origin` | **不推**——没有远端 |
| 交付落点 | PR | **本地合入默认分支** |
| 关闭 issue | `Closes #N` 自动关 / `gh issue close` | **改需求资料**：卡片或检查点里对应条目的状态 + commit + 验收证据 |
| 实现总结 | Issue 评论 | **写进需求资料**（检查点 `note`，或卡片本身） |

**不要因为「技能写的是 PR」就去建一个远端。** 真实跑过的一次：仓库本来就没有 remote，
编排者照着本技能的 PR 流程走不通，最后自己用本地 `git merge` 收了尾——那正是本地模式该
做的事，但技能没写，于是它成了没人维护的临场发挥。下面每一步都标了它属于哪种模式。

## 先备好证据：走查件

**交付前先写一份走查件**——它是 PR body（或本地模式的交付记录）的原料。没有它，body 里的
「验收证据」只能靠回忆写，而回忆不是证据。

- **范围：每批或每波一份**，与评审、交付同一个范围，**绝不逐 issue 一份**。逐 issue 的走查
  证明的是一份可能活不过集成的 diff，而一批只有一个 PR。
- **时机：`/review-it` 过完、门禁绿了之后**，提交之前或之后都行。给一份马上要改的代码写走查，
  等于写一份还得重写的走查。
- **落点：`<scope>/notes/walkthrough-<feature>.md`**（作用域根见 `/prd` 的落点约定）。
- **它是证明，不是 diff 倾倒。** 记录的是**你实际跑过什么、它打印出什么、你看到了什么**：
  命令与原始输出、演示路径的可视化证明、带 diff stat 的高风险说明、逐项人工验收状态。
- **跳过它只有一种理由**：一行改动或纯机械改动，既没有演示路径也没有可追的东西——那就直接把
  diff 递过去。

详细的产物结构、逐项清单与反模式见 [`references/walkthrough.md`](references/walkthrough.md)。
**这份 body 与这份走查件都只在本技能产出一次**：走查件提供证据，body 采用它，不要再另写一份摘要。

## 工作流

### Step 1: 提交代码

```bash
# 1a. 检查变更状态
git status
git diff --stat HEAD

# 1b. 暂存本次 Issue 相关的文件（不要 add 不相关的文件）
git add <files related to this issue>

# 1c. 提交，commit message 关联 Issue
git commit -m "$(cat <<'EOF'
{简要描述} (#issue-number)

{可选的详细说明}
EOF
)"
```

**关键规则：**
- commit message 中包含 `#issue-number` 以关联 Issue
- 只暂存当前 Issue 相关的文件，不要混入其他变更

### Step 2: 推送分支（仅远端模式）

```bash
# 如果还在 main/master 上，先创建功能分支
git checkout -b {branch-name}  # 如已在功能分支则跳过

# 推送到远程
git push -u origin {branch-name}
```

本地模式**跳过这一步**：没有远端可推，分支留在本地等 Step 4 合入。

分支命名：**一个需求一条分支**，用需求作用域取名——`feat/<scope-slug>`（仓库有约定就用它的）。`/loop-it` 的整批就落在这条分支上，每个 issue 一个 commit。只有「单个 issue 的独立小改动」才用 `feat/issue-42-short-desc`。

### Step 3: 创建 PR（仅远端模式）

本地模式**跳过这一步**，直接去 Step 4 本地合入。

```bash
gh pr create \
  --title "{简要描述}" \
  --body "$(cat <<'EOF'
## Summary
- 实现内容概述

Closes #{issue-number}

## Test plan
- [ ] 测试项 1
- [ ] 测试项 2
EOF
)"
```

**关键规则：**
- PR body 中写 `Closes #N` 或 `Fixes #N`，合入后 GitHub 自动关闭 Issue
- title 简洁，不超过 70 字符
- **本技能是走查件与 PR body 的唯一产出者。** 走查件提供证据（命令与真实输出、可视化、风险点、人工验收状态），body 直接采用它，不要再另写一份摘要——同一份内容维护两处就是重复

### Step 4: 合入

**远端模式**：

```bash
# 4a. 查看 PR 状态（确认 checks 通过）
gh pr checks

# 4b. 合入（默认 merge commit，可选 --squash 或 --rebase）
gh pr merge --squash --delete-branch
```

**参数说明：**
- `--squash`: 压缩为单个 commit 合入（推荐）
- `--rebase`: rebase 合入
- `--merge`: 普通 merge commit
- `--delete-branch`: 合入后删除远程分支

**本地模式**：

```bash
git checkout main              # 或 master——用「先决定走哪条路」里解析出来的默认分支，别假设
git merge --no-ff feat/<scope-slug>
```

用 `--no-ff` 留一个合并点：批末要按 commit 追溯与回滚单个 issue，快进合入会把那串
commit 抹平成「看起来像直接在 main 上写的」。合并后**不要删分支**——它是这批工作的
唯一留档，等用户确认交付完再删。

### Step 5: 添加实现总结

**远端模式**：PR 合入 / Issue 关闭时，始终在 Issue 上添加实现总结评论，方便后续直接从 Issue 回溯设计决策与代码变更。

参考固定四类结构组织总结内容：**Design Decisions（设计决策）**、**Deviations（偏离）**、**Tradeoffs（权衡）**、**Open Questions（待确认）**。某一类无内容时写 `None` 并简要说明。

```bash
gh issue comment {issue-number} --body "$(cat <<'EOF'
## 实现总结

**核心变更**
- {从 PR body Summary 提取的实现摘要，3-5 条 bullet}

**实现亮点（Highlights）**
- {值得强调的技术亮点：性能优化、优雅设计、复用抽象、关键测试覆盖等}，或 None

**设计决策（Design Decisions）**
- {spec 模糊/未定处所做的选择及理由}，或 None

**偏离（Deviations）**
- {有意偏离 spec 之处：spec 怎么说 → 实际怎么做 → 为什么}，或 None

**权衡（Tradeoffs）**
- {考虑过的备选方案及最终选择的原因}，或 None

**待确认（Open Questions）**
- {需用户确认的假设或后续跟进项}，或 None

---
- **PR**: #{pr-number}
- **Commit**: {hash}
EOF
)"
```

**关键规则：**
- 无论是 auto-close 还是手动 close，都必须添加此评论
- 四类结构固定为设计决策 / 偏离 / 权衡 / 待确认；某类无内容写 `None`
- 「实现亮点」提炼本次实现最值得关注的技术点（性能、设计、复用、测试等），无则写 `None`
- 核心变更从 PR body 的 Summary 部分提取，保持简洁（3-5 条 bullet）
- 附加 PR 编号和 commit hash，方便直接跳转
- 这四类内容**在本技能产出一次**。不要先把同样内容写进一份 `docs/issue#NNNN.md` 笔记再抄进评论；若用户明确要求了那个文件，附上链接，不重抄

**本地模式**：没有 Issue 可评论，同样的四类内容写进**需求资料**——检查点（`<scope>/issues/.loop-state.json`）里对应条目的 `note`，或 issue 卡片本身（仓库有约定就用它的落点）。落点仍由本技能产出一次，别在检查点和卡片里各写一份。

### Step 6: 关闭 Issue

**远端模式**：如果 PR body 中已写 `Closes #N`，合入后 Issue 会自动关闭，跳过此步。否则手动关闭：

```bash
gh issue close {issue-number} --reason completed
```

**本地模式**：没有 `gh` 可走，issue 是仓库里的 md 卡片。交付的落点是**仓库里的需求资料**——把 `<scope>/issues/` 里对应条目的状态改成已交付，并把 commit 与验收证据写进去。别去调 `gh issue close` 关一个不存在的 issue。

### Step 7: 回到默认分支并同步

```bash
git checkout main          # 或 master
git pull                   # 本地模式没有远端，跳过
```

## 多个 issue 共用一个 PR（波 / 批末模式）

`/graph` 的一波与 `/loop-it` 的一批默认把多个 issue 收进同一个 PR（squash 后只剩一个 commit）。此时 PR body **必须逐项列出证据**，不能只写一行 `Closes #1 #2 #3`——否则单项特性既没法审计也没法单独回滚。

本地模式同样需要这张表，落点是需求资料而不是 PR body：`--no-ff` 合入后 commit 还在
`main` 的历史里，但「哪一项由哪个 commit 实现、靠什么验收」仍然只有写下来才查得到。

这份 body 由**本技能**产出，本技能是它的唯一产出者。走查件只提供证据（命令与真实输出、可视化、风险点、人工验收状态）——两处各写一份 PR body 正是要避免的重复。

```markdown
| 项 | commit | 关闭的 issue | 验收证据（测试名 / 命令） | 人工验收 |
| --- | --- | --- | --- | --- |
| 节点 3 | `abc1234` | Closes #12 | `TestFooBar` | 尚未人工验收 |
| 节点 4 | `def5678` | Closes #13 | `mise run check` + `TestBaz` | 尚未人工验收 |

本 PR 由 2 项合并而成；squash 后如需撤销单项，按上表 commit 手工 revert。
```

**关键规则：**
- **commit 列必填**：squash 之后这些提交在 `main` 上已经看不到，只有写进 PR body 才能按项追溯与回滚。
- **验收证据要具体**：写测试名或命令，不写「测试通过」。
- **人工验收逐项标注**：该项主路径没人走过就写「尚未人工验收」；只有用户明确确认后才能改，并注明确认依据（时间 / 环境）。
- **逐项关闭 issue**：每项各自写 `Closes #N`（或合入后按 Step 6 手工关闭），不要合成一行。
- 单项 PR（一个 issue 一个 PR）不需要这张表，按 Step 3 的模板即可。

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| `gh pr checks` 有失败项 | 查看失败原因，修复后追加 commit 推送 |
| PR 有 merge conflict | `git fetch origin main && git rebase origin/main`，解决冲突后 force push |
| `gh pr merge` 被 branch protection 阻止 | 确认 required reviews 已满足，或请 reviewer approve |
| Issue 合入后未自动关闭 | 确认 PR body 包含 `Closes #N`，或执行 Step 6 手动 `gh issue close` |
| `gh` 未安装 / 未登录 / 仓库没有 origin | **本地模式**，不是错误——按「先决定走哪条路」的本地一列走，不要为此新建远端 |
| 本地合入后想撤销整批 | `git revert -m 1 <merge-commit>`；撤销单项按证据表里的 commit 逐个 revert |

## 完整示例

```bash
# 创建分支并提交
git checkout -b feat/issue-42-case-model
git add cases/case.go cases/case_test.go
git commit -m "$(cat <<'EOF'
Add Case data model and Markdown read/write (#42)

Define Case struct with YAML frontmatter + Markdown body
serialization. Provide WriteCase/ReadCase/ListCases/UpdateCase.
EOF
)"

# 推送
git push -u origin feat/issue-42-case-model

# 创建 PR
gh pr create \
  --title "Add Case data model and Markdown read/write" \
  --body "$(cat <<'EOF'
## Summary
- Define Case struct with YAML frontmatter + Markdown body
- Implement WriteCase/ReadCase/ListCases/UpdateCase functions
- Add comprehensive test coverage

Closes #42

## Test plan
- [x] Unit tests pass
- [x] go vet / lint clean
EOF
)"

# 确认 checks 通过后合入
gh pr checks
gh pr merge --squash --delete-branch

# 添加实现总结评论（四类结构）
gh issue comment 42 --body "$(cat <<'EOF'
## 实现总结

**核心变更**
- Define Case struct with YAML frontmatter + Markdown body
- Implement WriteCase/ReadCase/ListCases/UpdateCase

**实现亮点（Highlights）**
- 单文件自包含存储，读写无需外部索引，测试覆盖率 100%

**设计决策（Design Decisions）**
- Markdown body 与 YAML frontmatter 分离存储，便于人工编辑与 diff

**偏离（Deviations）**
- None — 实现与 spec 一致

**权衡（Tradeoffs）**
- 选用 frontmatter 而非独立 JSON 元数据：单文件自包含，牺牲了少量解析性能

**待确认（Open Questions）**
- None

---
- **PR**: #43
- **Commit**: abc1234
EOF
)"

# 切回默认分支并同步（分支名可能是 main 或 master）
git checkout main   # 或 master
git pull
```

## 完整示例（本地模式）

```bash
# Step 0：确认走哪条路——没有 origin，gh 也没登录，所以是本地模式
git remote -v            # 空

# Step 1：提交（每个 issue 一个 commit，落在同一条需求分支上）
git checkout -b feat/embedded-kv
git add kv/store.go kv/store_test.go
git commit -m "feat(kv): embedded store with crash-safe writes (#1)"

# Step 2/3：跳过——没有远端可推，也没有 PR

# Step 4：本地合入，留一个合并点
git checkout main
git merge --no-ff feat/embedded-kv

# Step 5：四类总结写进需求资料（这里是检查点的 note，不是 Issue 评论）
#   python3 <loop-it>/scripts/loop_state.py ... --note "..."

# Step 6：把卡片状态改成已交付，并写进 commit 与验收证据
#   requirements/kv/issues/issue-001-*.md：status: shipped，evidence 填测试名与命令

# Step 7：分支留着（这批工作的唯一留档），不用 pull
```
