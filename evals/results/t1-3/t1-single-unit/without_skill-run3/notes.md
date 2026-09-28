# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：20.6s
- token：63477
- 步数：6，工具调用：9

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片已做完。

**改动**
- 新增 `greeter/slug.go`：`Slug(s)` 用 `strings.Fields` 切分空白后以 `-` 连接，再 `ToLower`。一条表达式同时满足三条验收（首尾空白自然丢弃、连续空白折成一个连字符、大小写归一）。
- 新增 `greeter/slug_test.go`：覆盖卡片列出的三个用例。

**门禁**
- `make check` 通过（`go build ./...` + `go test ./...`，EXIT=0）。
- 冻结基线未动：`git status` 只显示两个新文件，`Makefile` 与 `greeter/greet_test.go` 无任何 diff。
