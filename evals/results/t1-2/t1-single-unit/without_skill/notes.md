# t1-single-unit / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：28.6s
- token：88857
- 步数：8，工具调用：10

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**卡片内容**：给 `Greet` 所在的 `greeter` 包加一个 `Slug`，三条验收条件。

**改动**
- `greeter/greet.go`：新增 `Slug`，`strings.Fields` 负责去首尾空白并把连续空白折成一段，`ToLower` + `Join(..., "-")` 出结果。6 行，只加了这一处。
- `greeter/slug_test.go`（新文件）：表驱动测试覆盖三条验收条件。

**门禁**：`make check` → `go build ./...` + `go test ./...` 全绿，exit 0。

**冻结基线**：`git diff --quiet -- Makefile greeter/greet_test.go` 通过，两者逐字节未动；改动只落在 `greet.go` 与新增的 `slug_test.go`。
