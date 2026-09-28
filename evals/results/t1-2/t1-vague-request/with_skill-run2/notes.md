# t1-vague-request / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：293.7s
- token：897611
- 步数：22，工具调用：36

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `let-it-go` 技能集的流程走完，对应入口技能是 **`prd`**（一句诉求 + 「怎么落地你定」正是它的触发条件）。

## 流程与判定

- **`/prd`** → 契约五字段落盘到 `requirements/slug/documents/prd-slug.md`。
- **规模判定：单单元**。整件事装得进一个上下文，按 `to-issues` 的硬边界**不产 issue 卡**（不为「有卡片」而建卡片），直接内联实现。
- **`/loop-it` 单单元** → 内联实现 + 门禁自证 + 提交。
- **`/review-it`** → 派了不共享实现上下文的子代理做两轴评审，两轮均通过。
- **`/ship-it` 本地模式**（本机没有 `gh`）→ 只落交付资料，**不 push、不开 PR、不合入**。

## 实现

`greeter/slug.go`：

```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

`strings.Fields` 一次覆盖三条要求：连续空白折成一个连字符、首尾空白裁掉、任意 Unicode 空白（tab / 换行 / NBSP）都算空白；空与纯空白输入返回 `""`。新代码独立成文件，没碰 `greet.go`。

## 证据（L1）

| 验收条件 | 观测 |
|---|---|
| `Slug("Ada Lovelace") == "ada-lovelace"` | 子测试 PASS |
| `Slug("  Grace   Hopper  ") == "grace-hopper"` | 子测试 PASS |
| `Slug("Alan\tTuring\n") == "alan-turing"` | 子测试 PASS |
| `Slug("")`、`Slug("   ")` == `""` | 子测试 PASS |
| `make check` 全绿、冻结基线未改 | 退出码 0；`Makefile`、`greeter/greet_test.go` 逐字节 diff 为空 |

评审：两轮独立子代理，Spec 轴 missing/extra/wrong 均为 None，Standards 轴无阻塞发现。第一轮唯一的非阻塞建议（PRD 假设「空白含 NBSP」但没测例）已补 `slug_test.go` 并复评确认。

## 交付

- 分支 `feat/slug`（base `main`），两个 commit：`cf4c855`（实现）、`9826d16`（交付记录）。
- 交付资料：`requirements/slug/documents/prd-slug.md`、`requirements/slug/notes/delivery.md`。
- 工作树干净，未 push、未合入。

**合入归你**（`/merge-it`，本地模式就是一句 `git merge --no-ff feat/slug`）。留一个未决项：标点 / 非 ASCII 字符的 slug 策略没做（需求只点名大小写、空白、首尾），需要时另开。
