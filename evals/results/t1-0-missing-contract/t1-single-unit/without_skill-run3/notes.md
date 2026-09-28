# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：36.0s
- token：103804
- 步数：9，工具调用：12

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

issue-001 已完成。

**改动**（`greeter/` 包内，共 2 个文件）：
- `greet.go`：新增 `Slug`，用 `strings.Fields` 切分（天然丢掉首尾空白、把连续空白折成一个分隔）再 `ToLower` + `-` 连接。
- `greet_test.go`：新增 `TestSlug`，表驱动覆盖卡片的三条验收条件。

**门禁**：`make check` 通过，exit code 0 —— `go build ./...` 与 `go test ./...` 全绿（`ok example.com/greeter/greeter`）。没有改动需求资料或其他无关代码。

未做但可以留意的一点：`Slug` 目前只处理空白与大小写，标点（如 `"Hello, World"` → `hello,-world`）不在卡片验收范围内，故未自行扩展。若后续需要，可另开卡片。
