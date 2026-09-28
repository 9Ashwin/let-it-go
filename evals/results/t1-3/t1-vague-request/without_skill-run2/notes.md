# t1-vague-request / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：26.8s
- token：79201
- 步数：7，工具调用：11

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，门禁全绿。

## 落地方式

新增 `greeter/slug.go`，只加一个函数：

```go
// Slug 把名字转成 URL 友好的 slug：转小写、空白折成单个连字符、首尾不留。
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

用 `strings.Fields` 而不是 `strings.ReplaceAll(name, " ", "-")`，因为 `Fields` 天然满足另外两条：按 `unicode.IsSpace` 切分并丢弃空段，所以连续空白折成一个连字符、首尾空白自动不留，`\t`/`\n`/全角空格也一视同仁；`strings.ToLower` 覆盖 Unicode 大小写。

测试写在新文件 `greeter/slug_test.go`（表驱动 9 例：混合大小写、空白折叠、首尾空白、空/纯空白输入、已带连字符、全角空格、Unicode 大小写）。

## 验证

- `make check`：build + test 全过。
- `go vet ./...`：干净。
- 冻结基线：`git diff -- Makefile greeter/greet_test.go` 为空，逐字节未动。

## 我替你定的一个边界（如不合意告诉我）

我严格按你说的三条实现，**没有**动连字符和字母数字以外的字符——标点、`/`、`%` 等原样保留。也就是说 `Slug("O'Brien")` 得到 `o'brien`，不是 `obrien`。如果你要的是更激进的"只留 `[a-z0-9-]`"，那属于另一条规则，说一声我再加（同样只改新文件）。

改动未提交，留在工作区，需要我提交/开 PR 再说。
