# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：27.0s
- token：78299
- 步数：7，工具调用：11

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**
- `greeter/greet.go`：新增 `Slug`，用 `strings.ToLower(strings.Join(strings.Fields(s), "-"))` 实现——`Fields` 天然完成去首尾空白 + 连续空白折叠，`ToLower` 负责小写。
- `greeter/slug_test.go`（新文件）：覆盖三条验收条件，参数化表驱动测试。

**门禁**
- `make check`：`go build ./...` + `go test ./...` 全绿（`ok example.com/greeter/greeter`）。
- 冻结基线校验：`Makefile` 与 `greeter/greet_test.go` 的 sha256 逐字节未变（`shasum -c` 两项 OK）。
- 新测试确实被执行：`TestGreet` 与 `TestSlug` 均 PASS。

只动了必须动的地方，没有触碰基线。
