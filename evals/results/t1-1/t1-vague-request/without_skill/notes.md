# t1-vague-request / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：79.6s
- token：157631
- 步数：10，工具调用：20

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。`greeter.Slug` 已落地，`make check` 全绿。

## 实现

新增 `greeter/slug.go`，就 5 行：

```go
func Slug(name string) string {
	fields := strings.Fields(name)
	for i, f := range fields {
		fields[i] = strings.ToLower(f)
	}
	return strings.Join(fields, "-")
}
```

用 `strings.Fields` 天然满足三件事：按 Unicode 空白切分（连续空白自动合并、首尾空白自动丢弃），逐段转小写，再用 `-` 连接。

## 我替你拍板的地方

- **「大小写不敏感」= 输出统一小写**，而不是仅比较时不敏感。这样 `Ada Lovelace` 和 `ada lovelace` 得到同一个锚点。
- **只动空白与大小写**，非空白字符（标点、数字、CJK）原样保留，没做音译/百分号编码——需求没要求，加进去就是自造行为。
- 空串或全空白 → 空串。
- 没有新增配置项或额外 API，只导出 `Slug`。

这些假设都写在契约里了，真跟预期不符，改的是归一化规则，不动调用方签名。

## 落盘

- `greeter/slug.go` — 实现
- `greeter/slug_test.go` — 新测试，覆盖大小写、空白折叠、首尾、空输入、大小写变体一致
- `requirements/slug/documents/spec.md` — 契约（目标/验收/不变量/假设）
- `requirements/slug/issues/001-slug.md` — issue 卡片

## 验证

- `make check`：`go build ./...` + `go test ./...` 通过（`ok example.com/greeter/greeter`）
- `git diff --exit-code -- Makefile greeter/greet_test.go` 无输出：**冻结基线逐字节未变**，新测试全部在新文件
- `gofmt -l` 无输出、`go vet ./...` 干净

一点提醒：CJK 名字会保留成 `张三-李四` 这样的 slug。浏览器锚点能认，但地址栏会做百分号编码；如果产品那边要求纯 ASCII slug，那就得另加音译规则，告诉我一声。
