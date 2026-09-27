# 07-parallel-waves / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：56.0s
- token：276506
- 步数：15，工具调用：29

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三件事都做完并集成，已提交到默认分支 `main`（commit `2a468a1`），没有开 PR。

## 改动

**1. `inventory.Reorder`**（`inventory/inventory.go`，只碰 `inventory/`）
- 新增常量 `ReorderAt = 5`，过滤 `Qty < ReorderAt`
- 按 `Qty` 升序、同数量按 `SKU` 升序；用新切片实现，不改入参

**2. `pricing.BulkTotal`**（`pricing/pricing.go`，只碰 `pricing/`）
- `gross := cents*qty`，返回 `gross - gross*discountPct/100`；整数除法天然向下取整

**3. `report.LowStockLines`**（`report/report.go`，依赖前两件）
- 调 `inventory.Reorder` 拿到顺序，逐条用 `pricing.BulkTotal(unitCents[sku], qty, discountPct)`
- 复用已有的 `SKULine` 拼出 `"<sku> x<qty> = <金额>"`，顺序与 `Reorder` 完全一致

## 关于并行
- 1、2 确实互不依赖，两处改动与各自测试互相独立地一并落地
- 3 在 1、2 的接口稳定后收口，`report` 只通过公开函数依赖两者，符合仓库「`inventory`/`pricing` 互不依赖、`report` 依赖两者」的边界约定

## 验证
- 按仓库约定新建测试文件（未追加进任何已有 `*_test.go`）：`inventory/reorder_test.go`、`pricing/bulktotal_test.go`、`report/lowstock_test.go`，覆盖过滤+排序、同数量按 SKU、不修改入参、空结果、折扣向下取整、以及 `LowStockLines` 的集成顺序与金额
- 冻结基线逐字节未变（sha256 比对 `015f8c6` 原版）：
  - `inventory/inventory_test.go` OK
  - `pricing/pricing_test.go` OK
- `make check` 绿（另跑了一遍禁缓存的 `go build` + `go test -count=1` + `go vet`，exit 0），`gofmt` 无差异，工作区干净

`requirements/` 未改动——本次是直接实现既有诉求，没有走写需求文档的流程。
