# t1-single-unit / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：183.7s
- token：465441
- 步数：16，工具调用：29

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 **loop-it 单单元路径**（一张卡片、改动装得进一个上下文）走完，没有碰检查点、没有建 worktree、没有开 graph 波次。

## 改了什么

`greeter/greet.go` 新增 `Slug`：

```go
// Slug 把 s 归一成小写连字符形式：去掉首尾空白，连续空白折成一个 "-"。
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```

`strings.Fields` 天然覆盖三条验收条件——去首尾空白、连续空白折叠；`Join(..., "-")` 折成连字符；`ToLower` 归一化。

新测试写在**新文件** `greeter/slug_test.go`（三条验收条件各一条断言），冻结基线 `Makefile` 与 `greeter/greet_test.go` 逐字节未动。

## 验收证据

三条都是纯函数行为，需要 **L1**（单元/静态）层，`make check` 的 `go test` 就是该层观测；纯函数库无 L2–L4 可观测面。

| 验收条件 | 证据 | 命令 |
|---|---|---|
| `Slug("Hello World")` → `hello-world` | L1 | `make check` → `ok example.com/greeter/greeter` |
| `Slug("  Hello World  ")` → `hello-world` | L1 | 同上（`TestSlug`） |
| `Slug("a   b")` → `a-b` | L1 | 同上（`TestSlug`） |

## 评审

派了一个**不共享上下文**的子代理（`subagent`，非 fork）对 `main...HEAD` 做两轴评审：**Spec 轴 clean**（无 missing/extra/wrong），**Standards 轴八维 clean**，冻结基线哈希一致，结论 **PASS**。无返工。

## 交付（本地模式：有 origin 但 `gh` 不可用）

- `feat/issue-001-slug` 分支上两个 commit：`14821e5 feat: add Slug normalization to greeter`、`0c5f6a8 docs: record Slug delivery`
- `git merge --no-ff` 合入 `main`（合并点 `7905200`），分支保留作留档
- 交付记录（状态 / commit / 证据）写进 `requirements/01_REQ-greeting/issues/issue-001-slug.md`

## 门禁确认

`main` 上最终 `make check` → build + test 全绿，exit 0；`git diff ba4bd40 HEAD -- Makefile greeter/greet_test.go` 为空，工作树干净。没弄坏。

一点说明：`gh` 不可用，所以走了技能里的本地合入路径（未推远端、未开 PR），这符合 CONTRACT 对「无 GitHub 远端」的约定。
