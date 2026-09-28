# t1-vague-request / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：35.4s
- token：66971
- 步数：6，工具调用：10

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**（两个新文件，冻结基线未动）
- `greeter/slug.go` — 新增 `Slug(name string) string`
- `greeter/slug_test.go` — 覆盖规则的表驱动测试

**实现**
```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```
`strings.Fields` 按 Unicode 空白切分，天然完成三件事：丢掉首尾空白、把连续空白折叠成单个 `-`、忽略制表符/换行等各类空白；再接小写。

**验证**：`make check` 通过（build + test），`Makefile` 与 `greeter/greet_test.go` 逐字节不变。

**一个我替你定的边界，供你确认**：需求只给了三条规则，所以标点等非空白字符**原样保留**——`"Hello, World!"` → `"hello,-world!"`。如果你要的是更严格的 URL 净化（去标点、只留字母数字），那是另一条规则，说一声我加；我没有擅自加进去。

另一个默认：`Slug("")` 和纯空白都返回 `""`（空锚点），没有回退到 `"world"` 之类的兜底。
