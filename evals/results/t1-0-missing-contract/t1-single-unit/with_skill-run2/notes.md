# t1-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：192.9s
- token：381735
- 步数：18，工具调用：23

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。按 `loop-it` 单单元模式走完全程。

## 做的事

**实现**（`greeter/` 包，内联完成）
- `greeter/greet.go`：新增导出函数 `Slug`，用 `strings.Fields` + `strings.Join(..., "-")` + `strings.ToLower` —— `Fields` 天然完成去首尾空白与折叠连续空白。
- `greeter/greet_test.go`：新增表驱动 `TestSlug`，三条验收条件各一例。先红（`undefined: Slug`）后绿。

**评审**（`review-it`）：派了一个不共享上下文的子代理，两轴分开判。结论**通过**：
- Spec 轴：三条验收条件全部实现并有测试对应，无缺失 / 多出 / 写错。
- Standards 轴：八维度无阻塞发现；唯一非阻塞观察是表驱动里用 `t.Fatalf` 首败即停（与现有 `TestGreet` 风格一致，且不构成必须修项，按评审结论保留）。
- 评审者独立复跑了 `make check`、`go test -count=1 -v ./...`、`go vet ./...`，并做了注入扫描，均干净。

**交付**（`ship-it`，本地模式）：仓库有 `origin` 但 `gh` 不可用，按 skill 判为本地模式——不开 PR、不 push，本地 `--no-ff` 合入。commit message 不带 issue 编号。

```
3ac222e docs: record issue-001 delivery evidence   (main)
7115bce Merge feat/issue-001-slug: add Slug helper (main)
9272c3a feat: add Slug helper to greeter package   (feat/issue-001-slug, 保留作留档)
```

交付状态与验收证据已写进 `requirements/01_REQ-greeting/issues/issue-001-slug.md`（含进度 / 关键决策 / 验证记录 / 未决事项）。

## 门禁

合入后在 `main` 上跑了一遍，绿：

```
go build ./...
go test ./...
ok  example.com/greeter/greeter
[exit 0]
```

工作树干净。验收条件与证据：三条都是纯函数行为，在 L1（`TestSlug` via `make check`）即可完整观测，无需 L3/L4。

未决事项：无。
