# 03-artifact-handoff / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：50.8s
- token：222301
- 步数：12，工具调用：25

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。没有需要问的地方——`requirements/01_REQ-low-stock-threshold/` 里「未交付」只有一项，`issue-002` 把它定义得很清楚，scope README 的「未决问题」也是「无」。

## 现状梳理

scope README 记录：issue-001（阈值按仓库可配）已交付，唯一未交付是 **`LowStockWarehouses` 的返回顺序**，对应 `issues/issue-002`：数量升序，数量相同按仓库名升序。

## 改动

1. **`inventory/stock.go`** — 把 `LowStockWarehouses` 里的 `sort.Strings`（只按名字）换成 `sort.Slice`：先比数量，数量相同再比仓库名。签名、判定规则未动，符合 issue 的非目标。
2. **`inventory/low_stock_order_test.go`（新增）** — 补两条回归测试，覆盖验收条件：
   - `TestLowStockWarehousesOrdersByQuantity`：用名称序与数量序**相反**的数据，确保能区分「按数量排」和「按名称排」。
   - `TestLowStockWarehousesBreaksTiesByName`：同数量时按名称升序。
   
   只用 fixture 保证未配置的 `chengdu`/`wuhan`、数量取 0/1，不依赖任何具体仓库配置。
3. **文档同步** — `issue-002` 三条验收勾选；scope README 把顺序从「未交付」移到「已交付」，「未交付」改为「无」。

受保护的 `inventory/stock_test.go` 逐字节未动（已用 `git diff --exit-code` 核对）。

## 门禁

```
go build ./...   ✅
go test ./...    ok  example.com/inventory/inventory
go vet ./...     ✅
[exit code: 0]
```

`make check` 绿，新增的两条排序测试与其原有测试全部通过。

一个我替你做的判断：我加了排序的回归测试。原 `stock_test.go` 是刻意只断言集合、不断言顺序的（注释也说明顺序是 issue-002 要改的东西），所以排序如果不落到测试里，门禁其实验不出来——加在受保护文件之外的新文件里应该不违背 fixture 的意图。如果你希望严格只改业务代码、不加测试，我可以撤掉这个文件。
