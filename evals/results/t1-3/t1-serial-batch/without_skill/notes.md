# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：41.7s
- token：164084
- 步数：13，工具调用：22

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡都按依赖顺序做完了，门禁通过。

## 做了什么

**issue-001 — `Slug`**（新建 `greeter/slug.go`）
```go
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```
`strings.Fields` 一次性覆盖了卡里的三条验收：它按 Unicode 空白切分并丢弃空字段，所以首尾空白被去掉、连续空白天然折成一个 `-`，再统一转小写。

**issue-002 — `JoinSlug`**（新建 `greeter/join_slug.go`，依赖 001）
```go
func JoinSlug(parts ...string) string {
	slugs := make([]string, 0, len(parts))
	for _, p := range parts {
		if s := Slug(p); s != "" {
			slugs = append(slugs, s)
		}
	}
	return strings.Join(slugs, "/")
}
```
空串和纯空白经 `Slug` 后都是 `""`，用同一个判断一起跳过，无需单独区分两种输入。

## 验证

- 测试写在新文件 `greeter/slug_test.go`、`greeter/join_slug_test.go`，逐条覆盖卡里的验收条件（额外补了 `JoinSlug("a", "   ", "b")` 这条纯空白用例）。
- `make check` → `build` 与 `test` 全绿。
- 冻结基线逐字节未动：`git diff -- Makefile greeter/greet_test.go` 为空。
- 顺手确认 `go vet ./...` 无告警、`go fmt ./...` 无改动。

改动全是新增文件，没有碰 `greet.go` 和既有测试。
