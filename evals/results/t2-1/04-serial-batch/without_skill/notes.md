# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：238.7s
- token：948051
- 步数：31，工具调用：41

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，都在 `feat/stock-batch` 上，一个 issue 一个 commit，分支已推到 `origin` 并留在上面（未开 PR）。

## 提交

```
f271c1b feat(inventory): add LowStockReport                          # issue-003
78566cc feat(inventory): order low stock warehouses by quantity then name  # issue-002
f6f079d feat(inventory): read low stock threshold from config/thresholds.json # issue-001
97a1b42 chore: initial import
```

## 各 issue 落地

**issue-001 — 阈值来源改成配置文件**
- `LowStockThreshold(warehouse)` 从 `config/thresholds.json`（`map[string]int`）读该仓库阈值；未配置的仓库、文件不存在/读不出来/内容不是 JSON 对象一律回退 `DefaultLowStockThreshold`。
- 路径解析做了兼容：先看当前工作目录下的 `config/thresholds.json`，再向上找到仓库根（含 `go.mod`）拼出同一路径。这样从仓库根运行和 `go test`（工作目录是包目录 `inventory/`）都能读到同一份配置。
- `IsLowStock` 仍严格小于，判定规则未动。

**issue-002 — 低库存列表顺序**
- `LowStockWarehouses` 改为按数量升序，数量相同按仓库名升序；签名与判定规则不变。

**issue-003 — 低库存报告**
- 新增 `LowStockReport(stock map[string]int) []string`，每条 `<仓库>=<数量>`，直接复用 `LowStockWarehouses` 保证顺序一致；未改动 `LowStockWarehouses`。

## 测试与门禁

- 新增三个测试文件（`threshold_config_test.go` / `low_stock_order_test.go` / `low_stock_report_test.go`），覆盖配置生效、回退的各种情况（缺失/坏 JSON/非对象）、顺序规则、报告格式与顺序一致。
- 既有 `inventory/stock_test.go` 逐字节未动（`git diff 97a1b42 HEAD -- inventory/stock_test.go` 为空），新行为全部写在新文件里。
- `make check` 绿（build + test + vet），`-count=1 -v` 下 19 条测试全过；工作区干净，无遗留的 `config/thresholds.json`。
- 另外把 `requirements/01_REQ-stock-batch/README.md` 的「已交付/未交付」随每个 issue 同步更新。

当前状态：`* feat/stock-batch f271c1b [origin/feat/stock-batch]`。
