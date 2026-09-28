# t1-vague-request / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：27.5s
- token：84844
- 步数：7，工具调用：13

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，门禁绿。

## 改动

新增两个文件，既有文件一律没碰：

- `greeter/slug.go` — `Slug(name string) string`
- `greeter/slug_test.go` — 表驱动测试 + 大小写不敏感等价测试

```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

`strings.Fields` 天然按“任意空白连续段”切分并丢掉首尾空白，`Join` 用连字符接回，再整体小写——三件事一行搞定，不用手写 trim/折叠。

## 行为与验证

| 输入 | 输出 |
|---|---|
| `"Ada Lovelace"` | `ada-lovelace` |
| `"Ada \t\n Lovelace"` | `ada-lovelace` |
| `"  Ada Lovelace  "` | `ada-lovelace` |
| `"ADA LOVELACE"` | 与 `"ada lovelace"` 相同 |
| `""` / 纯空白 | `""` |

- `make check`：build + test 全过（`ok example.com/greeter/greeter`）。
- 冻结基线 `Makefile`、`greeter/greet_test.go` 改动前后 sha256 逐字节一致。
- `gofmt -l greeter/` 无输出。

## 两个我替你拍的决定

1. **“大小写不敏感”落成输出小写**，这样不同大小写的名字映射到同一个锚点，符合锚点去重的用途。如果你其实想要保留原大小写、只是比较时不敏感，告诉我改。
2. **只按你列的规则处理**：空白折连字符、首尾不留。标点、中文、下划线等其它字符原样保留，没有做“非字母数字一律剔除”的完整 slugify。需要那种更强清洗的话再加。
