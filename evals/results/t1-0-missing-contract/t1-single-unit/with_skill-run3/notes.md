# t1-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：170.6s
- token：509572
- 步数：24，工具调用：30

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片已做完并交付。

## 做了什么

**实现**（`greeter/greet.go`）
```go
// Slug 把 name 转成小写，并用单个连字符连接被空白分隔的词。
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```
`strings.Fields` 一次搞定「去首尾空白 + 连续空白折叠」，无需额外逻辑。

**测试**（`greeter/greet_test.go`）新增 `TestSlug`，表驱动覆盖三条验收条件。先写测试跑出红（`undefined: Slug`），再实现转绿。

## 验收证据

| 验收条件 | 层次 | 观测方式 | 结果 |
|---|---|---|---|
| `Slug("Hello World")` → `"hello-world"` | L1 | `TestSlug` 用例 | pass |
| `Slug("  Hello World  ")` → `"hello-world"` | L1 | `TestSlug` 用例 | pass |
| `Slug("a   b")` → `"a-b"` | L1 | `TestSlug` 用例 | pass |
| 门禁 | — | `make check`（build + test） | exit 0 |

## 评审与交付

- **`/review-it`**：派了不共享上下文的子代理做两轴评审。Spec 轴 pass（无 missing/extra/wrong）；Standards 轴八维度 pass，仅一条低严重度发现——我原注释写「URL 友好形式」但实现不处理 `/`、`?`、`#` 等保留字符，属未兑现承诺。采纳并改成只描述实际契约，重跑门禁后做了二次复核，通过。
- **`/ship-it`**：仓库有 `origin` 但 `gh` 不可用 → **本地模式**，不推远端。
  - 分支 `feat/issue-001-slug`，实现 commit `79262f0`、交付记录 commit `1282685`
  - `--no-ff` 合入 `main`：merge commit `739a9b4`（分支保留作留档）
  - issue 卡片 `requirements/01_REQ-greeting/issues/issue-001-slug.md` 追加了「交付记录」（状态/commit/证据）
  - 工作树干净，当前在 `main`，最终 `make check` 仍为 exit 0

## 未决事项

None。改动纯新增函数，未触碰 `Greet`，无兼容性影响。
