# t1-single-unit / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：343.2s
- token：937389
- 步数：24，工具调用：33

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片做完了。这是一张定义完整的**单单元**，按 `loop-it` 单单元路径内联处理：没有开循环、没碰 `.loop-state.json`、没建 worktree、没写走查件。

## 做了什么

**实现** — 新增 `greeter/slug.go`：
```go
func Slug(s string) string {
	return strings.ToLower(strings.Join(strings.Fields(s), "-"))
}
```
`strings.Fields` 天然去首尾空白并把连续空白折成一个分隔符，一行覆盖三条验收条件。

**测试** — 新文件 `greeter/slug_test.go`（三条验收条件 + 混合空白、空串边界），冻结基线 `Makefile`、`greeter/greet_test.go` 逐字节未动（blob 哈希与 HEAD 一致）。

## 门禁与评审

- `make check` → **exit 0**；`go test -count=1 -v ./...`：`TestGreet` PASS、`TestSlug` PASS；`gofmt -l .` 无输出。
- 派了一个**不共享上下文**的子代理做两轴评审：Spec 轴三条验收条件全部满足、无 missing/extra/wrong；Standards 轴八维无阻断发现。
- 评审提了一条可采纳的覆盖缺口（测试只喂 ASCII 空格），我补了混合空白用例 `{"a \t\n b", "a-b"}`。**评审建议的原期望值是错的**（`"a\tb\nc"` 是两个空白段，应为 `"a-b-c"`），门禁当场抓红，已修正——这也说明「子代理结论」不等于证据，最终以门禁为准。
- 复评通过。复评又给了一条可选加固（补 Unicode 空白用例），我**拒绝**了：那是重复验证标准库行为，验收条件未要求，不做无谓扩张。

## 交付状态（本地模式）

`gh` 未安装 → `ship-it` 本地模式：**未推送、未开 PR、未合入**，合入归人工 `/merge-it`。

```
分支 feat/issue-001-slug
  a29faca docs: record issue-001 implementation summary
  998a736 feat(greeter): add Slug helper
交付资料 requirements/01_REQ-greeting/notes/issue-001-implementation.md
```

未合入默认分支 `main`（按契约默认分支只经 PR 进入）。你要收尾的话：`git checkout main && git merge --no-ff feat/issue-001-slug`，或走 `/merge-it`。
