# t1-vague-request / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：165.5s
- token：715770
- 步数：22，工具调用：32

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 let-it-go 的 flow 走的：一句诉求 + 「怎么落地你定」→ 入口是 **`prd`**，落契约后按默认继续 `to-issues` → `loop-it`；`to-issues` 判定这个改动一个上下文装得下，**不产 issue 卡、不建检查点**，直接单单元内联实现，最后 `ship-it`。

## 落地结果

新增两个文件，`greet.go` 一行未动：

- `greeter/slug.go` — `func Slug(name string) string`
  ```go
  return strings.Join(strings.Fields(strings.ToLower(name)), "-")
  ```
  一行同时满足三条规则：`ToLower` 折叠大小写、`Fields` 按 Unicode 空白切分（连续空白自然折成一个连字符、首尾自动丢弃）、`Join("-")` 补连字符。
- `greeter/slug_test.go` — 表驱动测试，6 条观测覆盖全部验收条件（含空串、纯空白、已有连字符）。

## 证据（L1）

| 观测 | 命令 | 结果 |
|---|---|---|
| 门禁 | `make check` | `go build` + `go test` 全绿，exit 0 |
| slug 行为 | `go test ./greeter/ -run TestSlug -v` | 6 个子用例全 PASS |
| 冻结基线 | sha256 前后比对 | `Makefile` `3ba8f86e…`、`greet_test.go` `de952bb1…` 均未变 |
| 依赖 | `git diff go.mod` | 无改动 |

红→绿也留了痕：实现前先跑测试得到 `undefined: Slug` 的失败。

## 交付（本地模式：无远端可用 / `gh` 未安装）

改动落在需求分支 `feat/slug`，未推、未合入默认分支：

```
8d29750 docs: record slug implementation summary
fc4cb42 feat: add Slug for URL-friendly page anchors   ← 代码 + 测试 + PRD
```

- 契约：`requirements/slug/documents/prd-slug.md`
- 交付记录：`requirements/slug/notes/implementation-summary.md`

合入归你（`/merge-it`）：

```bash
git checkout main && git merge --no-ff feat/slug
```

## 需要你知道的假设

需求只点名了三条规则，其余我按下面默认推进并标了 `[Assumption]`，不合预期就当修订：

1. **非空白标点不剔除**——`Slug("Hi, Ada!")` 得到 `hi,-ada!`。URL 片段允许这些字符；要更严格的 URL 安全得另开一条。
2. **连续空白折成单个连字符**，不是每个空白一个。
3. **空 / 纯空白输入返回 `""`**，不做 `"world"` 兜底（那是 `Greet` 的职责）。

另外「大小写不敏感」我落成了**输出统一小写**，所以 `"Ada"` 与 `"ada"` 得到同一个 slug。

- ⚠️ **这一轮污染了**：臂碰到了 evals/cases——分数不可信，别用它下结论。
