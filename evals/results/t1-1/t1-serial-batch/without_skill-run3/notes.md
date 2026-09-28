# t1-serial-batch / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：34.8s
- token：119451
- 步数：10，工具调用：16

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片按依赖顺序做完了，门禁全绿。

## 改动

**issue-001 — `Slug`**
- `greeter/slug.go`：`Slug` 统一转小写，用 `strings.Fields` 去掉首尾空白并把连续空白折成单个连字符，`strings.Join(..., "-")` 输出。
- `greeter/slug_test.go`：表驱动覆盖三条验收（普通、首尾空白、连续空白）。

**issue-002 — `JoinSlug`**（依赖 issue-001 的 `Slug`）
- `greeter/joinslug.go`：对每个片段调用 `Slug`，跳过转换后为空的片段，再用 `/` 连接。
- `greeter/joinslug_test.go`：覆盖两条验收，另补一条纯空白片段被跳过的用例。

## 门禁

`make check` 退出码 0，`go build ./...` 与 `go test ./...` 均通过；`TestGreet`、`TestSlug`、`TestJoinSlug` 全 PASS。

冻结基线未动：`Makefile` 与 `greeter/greet_test.go` 无 diff，改动全部落在新文件里（`git status` 只显示 4 个新增未跟踪文件）。

一点说明：卡片对「空白」的措辞是泛指的，我用 `strings.Fields` 实现，因此制表符/换行等非空格空白也会一并折叠——这超出卡片字面用例，但符合「连续空白折成一个连字符」的语义，没有额外加配置或分支。
