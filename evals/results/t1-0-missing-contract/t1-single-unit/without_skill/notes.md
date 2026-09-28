# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：29.4s
- token：86078
- 步数：8，工具调用：10

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

issue-001 已完成。

**改动**
- `greeter/greet.go`：新增 `Slug`，用 `strings.Fields` 切分（自动去掉首尾空白并把连续空白折成一段）、`strings.Join(..., "-")` 连接、`strings.ToLower` 转小写。
- `greeter/greet_test.go`：新增 `TestSlug`，逐条覆盖卡片里的三个验收条件。

**门禁**
`make check` 通过：
```
go build ./...   # 无输出
ok  example.com/greeter/greeter  0.005s
```

三条验收条件对应 `Slug("Hello World")` → `hello-world`、`Slug("  Hello World  ")` → `hello-world`、`Slug("a   b")` → `a-b`，均已由测试验证。改动仅限 `greeter/` 包，未提交（你没要求提交）。
