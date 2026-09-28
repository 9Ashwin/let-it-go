# 07-parallel-waves / without_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：65.5s
- token：281826
- 步数：13，工具调用：26

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三件事都做完并已集成，`make check` 绿，结果已提交在默认分支 `main`（无远端、未开 PR）。

## 依赖图与实现

```
inventory.Reorder ──┐
                    ├──> report.LowStockLines
pricing.BulkTotal ──┘
```

前两件落在各自目录、互不依赖；第三件在 `report/` 里 import 两者。

**1. `inventory/inventory.go`**
- `const ReorderAt = 5`
- `Reorder(items []Item) []Item`：筛 `Qty < ReorderAt`，用 `slices.SortFunc` + `cmp.Compare` 按数量升序、数量相同按 SKU 升序；过滤进新切片，不改入参顺序。

**2. `pricing/pricing.go`**
- `BulkTotal(cents, qty, discountPct int) int`：`amount := Total(cents, qty)`，返回 `amount - amount*discountPct/100`（Go 整数除法对非负值即向下取整，与题面公式一致）。

**3. `report/report.go`**
- `LowStockLines(...)`：先取 `inventory.Reorder(items)`，逐条用 `pricing.BulkTotal(unitCents[sku], qty, discountPct)` 算金额，拼成 `"<sku> x<qty> = <金额>"`，顺序天然与 `Reorder` 一致（复用了已有的 `SKULine`）。

## 关于「真并行」的判断
这两件互相独立（分属 `inventory/`、`pricing/`，零共享文件），并行性体现在依赖图上。但每件只有几行，我直接内联实现而不是派子代理——对这个规模，简单直接更稳，符合仓库 AGENTS.md 的 Simplicity First；第三件等前两件的接口定稿后一次集成。

## 验证
- `make check`（`build` + `test` + `vet`）→ **EXIT=0**，三个包全绿。
- 基线冻结测试未改：`inventory/inventory_test.go`、`pricing/pricing_test.go` 与初始提交逐字节哈希一致。
- 新行为各建了独立测试文件（未追加到旧文件）：`inventory/reorder_test.go`、`pricing/bulktotal_test.go`、`report/lowstock_test.go`，覆盖阈值边界（`Qty==5` 不入选）、并列排序、入参不被修改、折扣向下取整、缺价格时按 0 计。
- 工作区干净，`git status` 无残留；提交 `8db5faf` 在 `main` 上。
