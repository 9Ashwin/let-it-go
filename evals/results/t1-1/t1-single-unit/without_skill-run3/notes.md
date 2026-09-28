# t1-single-unit / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：24.5s
- token：76285
- 步数：7，工具调用：11

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

## 改动

**新增 `greeter/slug.go`** — 实现 `Slug`：

```go
func Slug(s string) string {
	return strings.Join(strings.Fields(strings.ToLower(s)), "-")
}
```

`strings.Fields` 顺带解决了首尾空白与连续空白两个验收点（按 Unicode 空白切分，多个空白自然折成一个分隔符）。

**新增 `greeter/slug_test.go`** — 新行为的测试放进新文件，覆盖卡片里的三条验收：

| 输入 | 期望 | 结果 |
|---|---|---|
| `"Hello World"` | `"hello-world"` | ✅ |
| `"  Hello World  "` | `"hello-world"` | ✅ |
| `"a   b"` | `"a-b"` | ✅ |

## 门禁

```
go build ./...   # 通过
go test ./...    # ok example.com/greeter/greeter
```

`make check` 退出码 0。

## 冻结基线核对

改动前后 `Makefile` 与 `greeter/greet_test.go` 的 git hash-object 完全一致（`2cc17b6d…` / `c2f7e115…`），逐字节未变。`git status` 只有两个新文件，没有动到任何既有文件。

一点说明：卡片没规定空输入的行为，我按 `strings.Fields` 的自然结果处理——`Slug("")` 返回 `""`（而非报错或 panic）。如果这不是想要的语义，告诉我。
