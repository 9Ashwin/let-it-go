# t1-single-unit / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：24.5s
- token：65394
- 步数：6，工具调用：9

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片做完了。

**改动**（只新增两个文件，未碰任何既有文件）：

- `greeter/slug.go` — 新增 `Slug`：用 `strings.Fields` 按空白切分（自动丢弃首尾空段、合并连续空白），逐段 `ToLower`，再用 `"-"` 连接。
- `greeter/slug_test.go` — 三条验收条件各一个用例，表驱动。

**验证**：

- `make check` 通过（`go build ./...` + `go test ./...`，exit 0）。
- 冻结基线 `Makefile` 与 `greeter/greet_test.go` 的 `git diff` 为空，逐字节未变。

`git status` 只有两个新文件，没有多余改动。
