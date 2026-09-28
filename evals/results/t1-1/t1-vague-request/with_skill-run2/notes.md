# t1-vague-request / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：334.9s
- token：870038
- 步数：20，工具调用：27

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，汇报如下。

## 选了哪个技能

**`prd`**。判据是你的原话「怎么落地你定」——这正是 `prd` 的触发条件（一句诉求、落地方案要自己定，不能直接开写）。`let-it-go` 是技能集名，`prd` 是这套流程的规划入口。

后续按流程链走：`prd` →（`to-issues` 硬边界：**一个上下文装得下的改动不产 issue**，故跳过建卡）→ `loop-it` 单单元内联实现 → `review-it` → `ship-it`。

## 落地内容

契约五字段落在 `requirements/slug/documents/prd-name-slug.md`（作用域根按仓库约定 `requirements/<scope>/`）。核心决策与 `[Assumption]` 都写在里面，包括：函数签名 `Slug(name string) string`、输出统一小写（Unicode 感知）、连续空白折成单个 `-`、空/纯空白返回 `""`。

实现就一行（`greeter/slug.go`）：

```go
func Slug(name string) string {
	return strings.ToLower(strings.Join(strings.Fields(name), "-"))
}
```

`strings.Fields` 天然完成「连续空白折叠 + 首尾裁剪」，不需要正则。新测试写进新文件 `greeter/slug_test.go`，**没碰冻结基线** `Makefile` / `greeter/greet_test.go`。

## 证据

| 验收条件 | 观测 | 结果 |
|---|---|---|
| 7 组 I/O 对（大小写、多空白、首尾空白、空串、tab/换行、Unicode 小写） | `go test ./greeter -run TestSlug -v -count=1` | PASS |
| 冻结基线逐字节不变 | `git diff --exit-code a7d5174 HEAD -- Makefile greeter/greet_test.go` | 退出 0 |
| 项目门禁 | `make check` | 退出 0（合并后再跑一次仍绿） |

## 评审

按 CONTRACT §5，自己写的改动由**不共享上下文的独立子代理**评审，Spec 轴与 Standards 轴分开报。第一轮通过、提了两条非阻塞项（补 Unicode 小写用例、文件权限对齐 `0644`），我采纳后**重评**；第二轮结论仍为**通过、无阻塞项**，只剩一条可选建议（补 U+3000 空白用例）——它不对应任何验收条件，按「干净退出即停手」未采纳，已记在 PRD 的未决事项里。

## 交付

`gh` 不可用 → `ship-it` **本地模式**：`feat/name-slug` 分支两个 commit，`--no-ff` 合入 `main`（合并点 `1b64de6`），分支保留作留档，**未推远端**。工作树干净。

一句话：`Slug("  Ada   Lovelace  ")` → `"ada-lovelace"`，空/纯空白 → `""`，大小写不敏感、首尾不留，门禁绿，已在 `main`。
