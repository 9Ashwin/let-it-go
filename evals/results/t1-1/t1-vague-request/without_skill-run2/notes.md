# t1-vague-request / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：42.3s
- token：100357
- 步数：8，工具调用：12

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。`make check` 通过，冻结基线逐字节未动。

## 落地方式

新增两个文件，不碰现有代码：

- `greeter/slug.go` — `Slug(name string) string`
- `greeter/slug_test.go` — 新行为的测试

实现只有一行：

```go
func Slug(name string) string {
	return strings.Join(strings.Fields(strings.ToLower(name)), "-")
}
```

`strings.Fields` 按任意空白切分并丢掉空段，天然同时满足三条规则：先 `ToLower` 做到大小写不敏感（统一输出小写，`Slug("Ada") == Slug("ADA")`），中间空白折成单个连字符，首尾不产生连字符。`strings.Fields` 的切分覆盖空格、Tab、换行。

## 覆盖的用例

单名、全大写、连续空格折叠、首尾空白、Tab/换行、空串、纯空白，另加一条「不同大小写+不同空白量得到同一 slug」的等价断言。

## 两个我替你定的决定

1. **只处理你点名的三条规则**。非空白字符（标点、`/`、中文等）原样保留，没做删除或转义——"URL 友好" 可以引申到这些，但你没要求，我没加。若锚点要更严格，告诉我规则。
2. **没建 `requirements/<scope>/` 过程文档**。仓库约定里写了这个作用域根，但这次是一行函数的小改动、需求你已直接给出，我按"最小改动"处理，没有造 PRD/issue。如果你要补档，说一声。

## 验证

- `make check`：build + test 全绿，exit 0
- `Makefile` / `greeter/greet_test.go` 的 SHA-256 与开工前一致
- `git status`：仅新增 `greeter/slug.go`、`greeter/slug_test.go`

改动未提交，需要我 commit 或补过程文档再说。
