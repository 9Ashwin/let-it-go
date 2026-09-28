# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：28.6s
- token：76969
- 步数：7，工具调用：10

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**（都是新增文件，未碰任何既有文件）：

- `greeter/slug.go` — 新增 `Slug`：
  ```go
  func Slug(s string) string {
      return strings.Join(strings.Fields(strings.ToLower(s)), "-")
  }
  ```
  `strings.Fields` 一步同时满足「去首尾空白」和「连续空白折成一个连字符」，`ToLower` 负责大小写。
- `greeter/slug_test.go` — 新文件，表驱动覆盖卡片三条验收条件。

**门禁结果**：

- `make check`：build + test 全绿（`ok example.com/greeter/greeter`）。
- 冻结基线 `Makefile`、`greeter/greet_test.go`：`git diff` 为空，逐字节未变；`git status` 只显示两个新增文件。
- 额外跑了 `go vet ./...` 和 `gofmt -l`，均干净。
