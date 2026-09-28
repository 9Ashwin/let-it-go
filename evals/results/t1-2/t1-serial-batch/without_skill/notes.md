# t1-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：29.1s
- token：83803
- 步数：7，工具调用：12

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

## 结果

按依赖顺序（issue-001 → issue-002）实现，`make check` 通过（exit 0），冻结基线逐字节未变。

**issue-001 —— `Slug`**
- `greeter/slug.go`：`strings.ToLower(strings.Join(strings.Fields(s), "-"))`。`Fields` 天然完成去首尾空白 + 连续空白折叠。
- `greeter/slug_test.go`：覆盖三条验收（含首尾空白、连续空白）。

**issue-002 —— `JoinSlug`（依赖 issue-001）**
- `greeter/join_slug.go`：逐段调用 `Slug`，跳过空结果，再用 `/` 连接。
- `greeter/join_slug_test.go`：覆盖两条验收；「纯空白跳过」除空串外补了 `"   "` 一例。

## 门禁与基线

```
go build ./...   ok
go test ./...    ok  example.com/greeter/greeter
```

- `Makefile` 与 `greeter/greet_test.go` 的 SHA-256 与动手前完全一致。
- `git status` 只有 4 个新增未跟踪文件，没有改动任何既有文件。

改动只包含实现与测试，未触碰无关代码。
