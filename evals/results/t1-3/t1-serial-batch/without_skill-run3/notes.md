# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：33.6s
- token：135186
- 步数：11，工具调用：18

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片按依赖顺序做完了，门禁绿。

## 改动

**issue-001 — `Slug`**（`greeter/greet.go`）
```go
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```
`strings.Fields` 天然完成「去首尾空白 + 连续空白折叠」，再 `ToLower` 即得小写 slug。

**issue-002 — `JoinSlug`**（`greeter/greet.go`）
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
纯空白段经 `Slug` 后为 `""`，直接跳过。

**测试**（新文件，未碰冻结基线）
- `greeter/slug_test.go`：三条验收用例
- `greeter/join_slug_test.go`：两条验收用例

## 门禁结果

```
make check
go build ./...   ✅
go test ./...    ok  example.com/greeter/greeter
```

- 全部 5 个用例（含原有 `TestGreet`）通过：`TestGreet` / `TestSlug` / `TestJoinSlug` 均 PASS。
- 冻结基线未改动：`git diff --name-only -- Makefile greeter/greet_test.go` 为空，即逐字节不变。
- 未提交，改动留在工作区（`M greeter/greet.go` + 两个新测试文件）。

（过程中我有一次把 `make check GO=...` 传错了变量导致 make 报 `build: No such file or directory`，那是我命令行拼错，不是仓库门禁问题；上面这次是原样 `make check`，exit 0。）
