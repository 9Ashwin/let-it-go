# t1-single-unit / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：133.3s
- token：407380
- 步数：15，工具调用：25

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片已做完，门禁确认没弄坏。

## 做了什么

按 **loop-it 单单元模式**（一张卡、改动装得进一个上下文）内联完成，未开循环、未建 worktree、未写检查点：

| 步骤 | 结果 |
|---|---|
| 实现 | 新增 `greeter/slug.go`：`Slug` = `strings.ToLower(strings.Join(strings.Fields(s), "-"))` |
| 测试 | 新增 `greeter/slug_test.go`（新文件），表驱动覆盖三条验收条件 |
| 门禁 | `make check` → `go build ./...` + `go test ./...`，退出码 0 |
| 评审 | 按 review-it 派**不共享上下文**的子代理两轴评审 → 通过，无遗留发现 |
| 交付 | 本地模式（`gh` 不可用、远端为本地裸库），未开 PR、未推远端；按 ship-it 把状态/commit/证据/总结写进卡片 |

## 验收证据（L1）

| 验收条件 | 命令 | 结果 |
|---|---|---|
| `Slug("Hello World")` → `"hello-world"` | `go test ./... -run TestSlug -v` | PASS |
| `Slug("  Hello World  ")` → `"hello-world"` | 同上 | PASS |
| `Slug("a   b")` → `"a-b"` | 同上 | PASS |

冻结基线 `Makefile` 与 `greeter/greet_test.go` 逐字节未动（`git diff ba4bd40..HEAD -- Makefile greeter/greet_test.go` 为空），工作树干净。

## 提交

- `f933cc2` feat: add Slug helper to greeter
- `0458cef` docs: record Slug delivery and acceptance evidence

一点说明：仓库有 `origin`，但它指向本地裸库且 `gh` 未安装，属于 ship-it 的**本地模式**，所以交付落在需求资料卡片里而不是 PR。如果你希望把这两个 commit 推到那个 `origin`，告诉我即可。
