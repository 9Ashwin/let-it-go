# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：21.5s
- token：52395
- 步数：5，工具调用：6

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**（只新增两个文件，未碰冻结基线）：
- `greeter/slug.go`：新增 `Slug`，用 `strings.Fields` 切分——它天然同时完成去首尾空白和把连续空白折成一个分隔符，再 `ToLower` + `Join("-")`。
- `greeter/slug_test.go`：覆盖卡片里三条验收条件。

**门禁结果**：

```
go build ./...   # 通过
go test ./...    # ok example.com/greeter/greeter
exit=0
```

`git status` 只显示这两个新增的未跟踪文件，`Makefile` 与 `greeter/greet_test.go` 逐字节未动。
