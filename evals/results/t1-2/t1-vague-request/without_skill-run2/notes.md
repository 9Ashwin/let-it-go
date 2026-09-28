# t1-vague-request / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：41.3s
- token：87016
- 步数：7，工具调用：11

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

## 落地方式

新增 `greeter/slug.go`，导出 `Slug(name string) string`：

```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

三条要求一次到位：
- **大小写不敏感** → 统一转小写，`"ADA"` 和 `"ada"` 得到同一个锚点；
- **空白折成连字符** → `strings.Fields` 按任意空白切分（含空格/Tab/换行，且自动丢掉空段），再用 `-` 连接，连续空白折叠成一个连字符；
- **首尾不留** → `Fields` 天然丢弃首尾空白，不会产出前后导连字符。

## 验证

- 新增测试在独立文件 `greeter/slug_test.go`（表驱动，覆盖大小写、连续空白、首尾空白、Tab/换行、空串、纯空白）。
- `make check` 通过；`go vet ./...` 干净；`TestSlug` 8 个子用例全绿。
- 冻结基线 `Makefile`、`greeter/greet_test.go` 逐字节未动（`git diff` 为空），改动只有两个新增文件。

## 一个我替你定的取舍

需求只列了那三条，所以**除大小写与空白外的字符一律原样保留**（比如 `"Ada & Bob"` → `"ada-&-bob"`，不剥离标点）。严格说这类字符不算 URL 友好；如果要连标点也清掉，告诉我规则（保留哪些字符集），我再补一层过滤和对应测试。
