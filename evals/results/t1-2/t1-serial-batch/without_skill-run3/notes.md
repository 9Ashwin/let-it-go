# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：50.3s
- token：203420
- 步数：16，工具调用：20

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片已按依赖顺序做完，门禁绿。

## 交付内容

**issue-001 — `Slug`**（`greeter/slug.go` + `greeter/slug_test.go`）
```go
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```
`strings.Fields` 天然吃掉首尾空白并把连续空白折成一个分隔符，三个验收条件都覆盖。

**issue-002 — `JoinSlug`**（`greeter/join_slug.go` + `greeter/join_slug_test.go`，依赖 issue-001）
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
每段走 `Slug`，空串/纯空白 slug 为空即跳过，用 `/` 连接。

## 验证

- 每个 issue 都走了红→绿：先加测试跑出 `undefined: Slug` / `undefined: JoinSlug`，再补实现转绿。
- 最终 `make check`（`go build ./...` + `go test ./...`）**exit 0，`ok example.com/greeter/greeter`**。
- 冻结基线：`git diff --exit-code -- Makefile greeter/greet_test.go` 退出码 0，逐字节未动；`git status` 只有 4 个新增未跟踪文件，没有改动任何既有文件。

未提交（你没要求 commit），改动都在工作区。
