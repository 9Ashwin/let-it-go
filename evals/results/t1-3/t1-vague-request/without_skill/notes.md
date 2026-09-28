# t1-vague-request / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：52.9s
- token：145650
- 步数：11，工具调用：19

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

## 落地内容

新增两个文件，没动任何既有文件：

- `greeter/slug.go` — 导出函数 `Slug(name string) string`：

```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

- `greeter/slug_test.go` — 覆盖三条验收：大小写不敏感（含 `Slug("Ada Lovelace") == Slug("ada lovelace")`）、空白折连字符、首尾不留，另加空串/纯空白/混合空白（tab、换行）边界。

## 我替你定的语义（`怎么落地你定` 的部分）

- **空白折成连字符**：连续空白折成**一个** `-`，不是每个空白字符各出一个。这是 URL 锚点的通行做法，也符合"首尾不留"的意图。
- **大小写不敏感**：实现方式是输出统一转小写，所以 `Ada` 与 `ada` 得到同一个锚点。
- **空白判定**：按 `strings.Fields` 的任意 Unicode 空白切分，空格、tab、换行一视同仁。
- **未做**：标点/非 ASCII 音译、下划线等额外清洗——需求没提，按最小实现处理。

## 验证

- `make check`：build + test 全绿（`ok example.com/greeter/greeter`）。
- 冻结基线：`git diff` 对 `Makefile` 与 `greeter/greet_test.go` 为空，逐字节未变；工作区仅多出两个新文件。
- `gofmt` 检查干净。

如果你希望连续空白保留成多个连字符，或者输出保留原大小写，告诉我，改一行即可。
