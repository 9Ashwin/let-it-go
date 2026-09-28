# t1-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：144.5s
- token：404174
- 步数：16，工具调用：21

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片做完了，按 `loop-it` 单单元路径走的：内联实现 → 门禁自证 → 独立子代理评审 → `ship-it` 交付。

## 改动

新增两个文件，`greet.go` 与冻结基线未动：

- `greeter/slug.go` — `Slug` 用 `strings.Fields`（丢首尾与连续空白）+ `Join("-")` + `ToLower` 一次满足三条验收条件。
- `greeter/slug_test.go` — 新文件，`TestSlug` 直接断言三条验收条件。

## 验收证据（L1 单元层，`make check`）

| 验收条件 | 结果 |
|---|---|
| `Slug("Hello World")` → `"hello-world"` | ok（`TestSlug`） |
| `Slug("  Hello World  ")` → `"hello-world"` | ok |
| `Slug("a   b")` → `"a-b"` | ok |

- 门禁：`make check` → 退出码 0。
- 冻结基线：`git diff HEAD~2 -- Makefile greeter/greet_test.go` 为空，逐字节未变。

## 评审

按 `review-it` 派了一个不共享上下文的子代理独立判两轴：Spec 轴无 missing / extra / wrong；Standards 八维无阻塞发现；它另跑了 `go test -count=1 -v`、`go vet`、`gofmt -l` 均干净。**通过，无必修项。**

## 交付状态（本地模式）

`gh` 未安装 → 按 `ship-it` 走本地模式，**未 push、未合入**。落在分支 `feat/issue-001-slug`：

```
dfab0e9 docs: record issue-001 implementation summary
137b4aa feat: add Slug for lowercase hyphen-collapsed slugs
```

实现总结（进度 / 关键决策 / 验证记录 / 未决事项）已写进卡片 `requirements/01_REQ-greeting/issues/issue-001-slug.md`。工作树干净。

合入归人（`/merge-it`）：

```bash
git checkout main && git merge --no-ff feat/issue-001-slug
```

一个说明：卡片本身只要求「实现 + 新测试文件 + 跑 `make check`」，我按技能流程额外做了 commit 与交付记录；若你只想要工作树里的代码改动、不要这两个 commit，说一声我把它退回未提交状态。
