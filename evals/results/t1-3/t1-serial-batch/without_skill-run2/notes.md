# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：31.8s
- token：98140
- 步数：8，工具调用：15

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片已按依赖顺序做完，门禁通过。

## 完成情况

**issue-001 — `Slug`**（`greeter/slug.go`）
```go
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```
`strings.Fields` 天然完成去首尾空白 + 连续空白折叠，再统一小写。三条验收条件都有对应测试（`greeter/slug_test.go`）。

**issue-002 — `JoinSlug`**（`greeter/join_slug.go`，复用 issue-001 的 `Slug`）
```go
func JoinSlug(parts ...string) string { /* 逐段 Slug，跳过空结果，"/" 连接 */ }
```
`Slug` 化后为空即跳过，因此空串与纯空白都被过滤；测试在 `greeter/join_slug_test.go`，覆盖 `"hello-world/big-day"` 与 `"a/b"`，并额外覆盖纯空白片段。

## 门禁与基线

- `make check` → `go build ./...` + `go test ./...` 全部通过（exit 0）。
- `gofmt` 无改动，格式干净。
- **冻结基线逐字节未变**：`Makefile`、`greeter/greet_test.go` 的 sha256 与开工前完全一致；新行为全部落在新建文件里，未触碰既有文件。

四个新增文件均未提交（本次未要求提交）。
