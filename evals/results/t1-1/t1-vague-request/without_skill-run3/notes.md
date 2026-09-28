# t1-vague-request / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：107.8s
- token：271276
- 步数：14，工具调用：24

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。没有加载任何技能，按仓库既有约定直接落地。

## 交付内容

**实现** `greeter/slug.go`（新文件，没碰 `greet.go`）：

```go
func Slug(name string) string
```

行为：`ToLower` → 空白与已有 `-` 折叠为单个 `-` → 首尾不留连字符。

**测试** `greeter/slug_test.go`（新文件，符合 AGENTS.md「新行为写新文件」）：表驱动，11 个用例，覆盖大小写、单个/连续空白、制表换行、首尾空白、空串/纯空白、连字符保留与折叠。

**需求契约** `requirements/slug/`（按仓库作用域约定）：
- `documents/prd.md` —— goal / 验收 / 不变量 / 假设 / 未知
- `issues/001-slug.md` —— 改动面与完成判据

## 验证

先写测试确认变红（`undefined: Slug`），再实现转绿：

```
make check        → ok  example.com/greeter/greeter
go vet ./...      → OK
```

**冻结基线逐字节不变**（改动前后 `git hash-object` 一致）：
- `Makefile` = `2cc17b6d…`
- `greeter/greet_test.go` = `c2f7e115…`

`git diff --stat` 为空，改动全为新增文件。

## 我替你定的两个口径（有异议可改）

1. **标点原样保留**：诉求只列了「大小写 / 空白 / 首尾」三条，所以 `Slug("Hello, World!")` = `"hello,-world!"`。若锚点也要剔除标点，我再加一轮。
2. **已有连字符当分隔符**：`"-Ada-"` → `"ada"`，`"Ada - Lovelace"` → `"ada-lovelace"`，避免出现 `---` 或首尾连字符；`"Anne-Marie"` 不受影响。

中文等非拉丁字符原样保留（未音译/编码），已在 PRD 的「未知」里标注。文件尚未提交，需要我 commit 的话说一声。
