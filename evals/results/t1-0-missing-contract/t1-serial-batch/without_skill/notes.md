# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：48.4s
- token：191734
- 步数：15，工具调用：18

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片已按依赖顺序做完，门禁通过。

## 改动

**issue-001 — `Slug`**（`greeter/greet.go`）
```go
func Slug(s string) string {
	return strings.Join(strings.Fields(strings.ToLower(s)), "-")
}
```
`strings.Fields` 一并解决了首尾空白与连续空白折叠两个验收点。

**issue-002 — `JoinSlug`**（依赖 issue-001）
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
复用 `Slug`，空白片段 slug 后为空自然被跳过。

**测试**（`greeter/greet_test.go`）：`TestSlug` 覆盖三条验收；`TestJoinSlug` 覆盖两条验收（含纯空白片段）。

## 门禁

```
$ make check
go build ./...
go test ./...
ok  	example.com/greeter/greeter	0.005s
```
另外 `go vet` 与 `gofmt -l` 均无输出。改动共 2 文件、+46 行，未触碰其他代码，也**没有提交**（卡片只要求补代码与测试、跑门禁，未要求 commit）。
