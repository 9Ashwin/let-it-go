# t1-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：168.4s
- token：405835
- 步数：14，工具调用：23

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已完成。按 `let-it-go` 的 `/loop-it` 技能判定为**单单元模式**（一张卡、装得进一个上下文），走完「实现 → 门禁自证 → `/review-it` → `/ship-it`」，未开循环、未碰 `.loop-state.json`、未建 worktree。

## 改动

- `greeter/greet.go`：新增 `Slug`
  ```go
  func Slug(s string) string {
      return strings.Join(strings.Fields(strings.ToLower(s)), "-")
  }
  ```
  `strings.Fields` 按空白 run 切分，天然去掉首尾空白并把连续空白折成一个连字符。
- `greeter/slug_test.go`：新文件，三条验收条件各一条用例。
- 冻结基线 `Makefile`、`greeter/greet_test.go` **逐字节未动**（`git diff HEAD --` 为空）。

## 验收条件 → 证据（均为 L1：纯函数行为）

| 验收条件 | 观测 | 命令 |
|---|---|---|
| `Slug("Hello World")` → `hello-world` | pass | `go test ./...`（`TestSlug`） |
| `Slug("  Hello World  ")` → `hello-world` | pass | 同上 |
| `Slug("a   b")` → `a-b` | pass | 同上 |

## 门禁与评审

- `make check`：**绿**（`go build ./...` + `go test ./...`，exit 0）。
- `/review-it`：派了一个**不共享上下文**的独立子代理，两轴分开判——Spec 轴三条全部达标、无缺失/多出/写错；Standards 轴八个维度无遗留可采纳发现（标点剥离、空串等被有意拒绝：不在契约内）。结论 **放行**。

## 交付状态（本地模式）

`gh` 不可用 → `/ship-it` 本地模式：未推、未开 PR，交付记录写进卡片本身。

- 分支：`feat/issue-001-slug`，工作树干净
- commit：`47dbe0c feat(greeter): add Slug helper` + `6508f81 docs: record Slug implementation summary`
- 未决事项：None

合入（不可逆，归 `/merge-it`，只有人能敲）：

```bash
git checkout main && git merge --no-ff feat/issue-001-slug
```
