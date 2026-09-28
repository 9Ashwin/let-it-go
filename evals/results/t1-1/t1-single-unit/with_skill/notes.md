# t1-single-unit / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：138.9s
- token：479834
- 步数：17，工具调用：24

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `loop-it` 的单单元路径走完，没有碰检查点、worktree 或 graph 波次。

## 实现

- `greeter/greet.go` 新增 `Slug`：`strings.ToLower(strings.Join(strings.Fields(s), "-"))`，`Fields` 同时解决首尾空白与连续空白。
- 新测试文件 `greeter/slug_test.go`，三条验收条件各一条断言。

## 门禁与证据

| 验收条件 | 证据层 | 观测 |
|---|---|---|
| `Slug("Hello World")` → `hello-world` | L1 | `make check` → ok，`TestSlug` PASS |
| `Slug("  Hello World  ")` → `hello-world` | L1 | 同上 |
| `Slug("a   b")` → `a-b` | L1 | 同上 |

- `make check` 绿（合入 `main` 后又跑了一次；`go test -count=1 -v` 强制非缓存，`TestGreet`/`TestSlug` 均 PASS）。
- 冻结基线 `Makefile`、`greeter/greet_test.go` 经 `git diff --exit-code` 确认逐字节不变。
- 工作树干净。

## 评审

`/review-it`：派了一个不共享上下文的独立子代理，两轴分开判。Spec 轴三条验收条件全满足、无 missing/extra/wrong；Standards 轴八维无阻断发现。结论通过。

## 交付（本地模式）

`gh` 不可用 → `/ship-it` 走本地模式：

- 分支 `feat/issue-001-slug`，commit `01972bc` `feat(greeter): add Slug helper`
- 本地 `--no-ff` 合入 `main`（`4e8ca69`）
- 交付记录（状态 / commit / 证据 / 评审）写进 `requirements/01_REQ-greeting/issues/issue-001-slug.md`，commit `9a55bc0`
- 仓库里有一个本地裸库 `origin`，已把 `main` 与需求分支推送同步（没有开 PR，因为 `gh` 缺失）

未决事项：无。
