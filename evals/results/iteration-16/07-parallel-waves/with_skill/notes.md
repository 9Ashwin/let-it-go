# 07-parallel-waves / with_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：348.0s
- token：2805493
- 步数：40，工具调用：68

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成了。用的是 let-it-go 技能集里的 **`graph`** 技能——因为这是「两个互不依赖的单元 + 一个 fan-in」的真并行 DAG，而不是链（`loop-it`）或单单元。

## 执行过程（按 graph 契约）

**规划**：作用域根按仓库约定落在 `requirements/001-lowstock-reorder/`，`graph_state.py` 分层为两波，作用域互不重叠（`inventory/`、`pricing/`、`report/`）：

```
波1:  #1 inventory.Reorder      #2 pricing.BulkTotal      ← 真并行
波2:            \                    /
                  #3 report.LowStockLines                 ← fan-in
```

**波1**：`node-1`、`node-2` 各在独立 git worktree / 分支上由子代理实现（一次 `workflow` 并发派发，校验 schema 回收报告）。fan-in 做泄漏检查 + evidence 检查 → 合并成 `wave-0-reorder-bulktotal` → 集成后 `make check` 绿 → 两轴评审（Spec/Standards，无被接受发现）→ `--no-ff` 本地交付到 `main`。

**波2**：从更新后的 `main` 切出 `node-3` worktree，实现 → 自证 → commit；单节点波直接对 `main` 评审并合入。

## 结果（都在默认分支 `main` 上）

| 项 | commit | 契约 | 证据 |
|---|---|---|---|
| #1 | `671d2e3` | `ReorderAt = 5` + `Reorder`（`Qty<5`，`Qty↑` 再 `SKU↑`，不改入参） | `TestReorder*` ×4，`make check` exit 0 |
| #2 | `111e718` | `BulkTotal = total - total*discountPct/100`（整数向下取整） | `TestBulkTotal`，`make check` exit 0 |
| #3 | `9e6004f` | `LowStockLines` → `"<sku> x<qty> = <金额>"`，顺序沿用 `Reorder`、金额用 `BulkTotal` | `TestLowStockLines*` ×3，`make check` exit 0 |

- **最终 `make check` -> exit 0**（build + test + vet），`report` 包现已带测试通过。
- 冻结基线 `inventory_test.go` / `pricing_test.go` 哈希与初始 commit **逐字节一致**；`report/report.go` 未改动。
- 未开 PR、未推远端（`origin` 只是本地 eval 裸库，`gh` 不可用，走本地 `--no-ff` 合入）。
- 交付留档：`requirements/001-lowstock-reorder/records/2026-09-28-delivery.md`（含逐项证据表），走查件 `notes/walkthrough-wave-0.md`、`notes/walkthrough-wave-1.md`，issue 卡已标 `shipped`；`.graph_state.json` / `graph.html` / `nodes.json` 是被忽略的派生物，未进 git。
- 工作树干净，已清理全部 worktree；节点分支与 `wave-0` 分支保留作留档。

**一处待确认（已记录在交付记录）**：空结果时 `Reorder`/`LowStockLines` 返回非 nil 空切片（`len == 0`）。若验收要求 `nil`，需要微调——目前按更常见的 `[]T{}` 语义实现。
