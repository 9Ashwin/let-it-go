# t1-single-unit / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：208.1s
- token：551654
- 步数：19，工具调用：27

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片做完了，门禁绿。

## 走的路径

`loop-it` 判为**单单元**（一张卡、改动装得进一个上下文），所以内联做完，**没有**碰 `.loop-state.json`、没有建 worktree、没有开 workflow（契约 §3 对单单元的硬边界）。

## 改动

| 文件 | 改动 |
|---|---|
| `greeter/greet.go` | 新增导出函数 `Slug`：`strings.ToLower(strings.Join(strings.Fields(s), "-"))` |
| `greeter/slug_test.go` | **新文件**，表驱动测试覆盖 3 条验收条件 |
| `requirements/01_REQ-greeting/issues/issue-001-slug.md` | 追加本地模式实现总结 |

`strings.Fields` 一次搞定「去首尾空白 + 连续空白折一」，范围严格限定在卡片要求内。

## 验收证据（L1）

先写测试跑出红态（`undefined: Slug`），再实现转绿：

- `Slug("Hello World")` → `hello-world` ✅
- `Slug("  Hello World  ")` → `hello-world` ✅
- `Slug("a   b")` → `a-b` ✅

全量门禁 `make check`（`go build ./...` + `go test ./...`）**退出码 0**。

## 冻结基线核对

`Makefile` 与 `greeter/greet_test.go` 的 blob 哈希与 `HEAD` 逐字节一致，未改动：

```
Makefile         2cc17b6… = 2cc17b6…
greet_test.go    c2f7e15… = c2f7e15…
```

## 评审

派了**不共享上下文的独立子代理**做对抗性两轴评审（生成者/评判者分离）。它自己重跑门禁、核对基线哈希、并在仓库外临时模块里独立实测三条验收条件——结论：**通过，无必须修项**。它额外提示标点未折叠（`"Hello, World"` → `"hello,-world"`），卡片未要求，已记入卡片「未决事项」。

## 交付（本地模式）

`gh` 未安装 → `ship-it` 本地模式：提交到需求分支、不推送、不开 PR，合入留给 `/merge-it`（只有人能敲）。

- 分支：`feat/issue-001-slug`
- `d4bece9 feat(greeter): add Slug helper for lowercase hyphenated slugs`
- `50d40af docs(greeting): record issue-001 implementation summary`
- 工作树干净，未推送。

合入命令（需你确认后执行）：

```bash
git checkout main && git merge --no-ff feat/issue-001-slug
```
