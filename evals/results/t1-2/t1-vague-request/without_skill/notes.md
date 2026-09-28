# t1-vague-request / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：34.6s
- token：92152
- 步数：8，工具调用：11

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**落地方式**（新增两个文件，没碰冻结基线）：

- `greeter/slug.go` — 新增导出函数 `Slug`：

  ```go
  func Slug(name string) string {
      return strings.ToLower(strings.Join(strings.Fields(name), "-"))
  }
  ```

  `strings.Fields` 按 Unicode 空白切分并天然丢掉首尾空白、折叠连续空白，`Join` 补连字符，`ToLower` 实现大小写不敏感。

- `greeter/slug_test.go` — 表驱动测试，覆盖：单词、多词、混合大小写、首尾空白、连续空白折成一个连字符（含 `\t\n`）、已有连字符、空串、纯空白。

**验证结果**：

- `make check` 通过（build + test，`ok example.com/greeter/greeter`）。
- `go vet ./...` 通过。
- `Makefile` 与 `greeter/greet_test.go` 的 SHA-256 与改动前逐字节一致（已核对），`git diff` 为空，工作区只有两个新增未跟踪文件。

**一个我替你定的边界**（按"怎么落地你定"）：只处理空白，标点原样保留（如 `"Ada-Lovelace"` → `"ada-lovelace"`），空/纯空白输入返回空串。如果你要的是"标点也剔除"或"空格不折叠只替换"，说一声我改。
