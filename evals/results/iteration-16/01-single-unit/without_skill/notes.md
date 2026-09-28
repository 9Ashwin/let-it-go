# 01-single-unit / without_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：116.1s
- token：232295
- 步数：9，工具调用：16

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

改完了，`make check`（build + test + vet）全绿。

## 改动

**`inventory/stock.go`**（唯一业务文件）
- `LowStockThreshold(warehouse)` 现在按仓库查配置：配置里有就用配置值，否则回退 `DefaultLowStockThreshold`。函数签名不变，冻结测试不受影响。
- 新增 `loadThresholds()`：读 `inventory/thresholds.json` 并解析成 `map[string]int`；**文件不存在、读不到、或 JSON 解析失败都当作“没有配置”**，由调用方回退默认值。
- `LowStockWarehouses` 改为一次加载配置、循环内查表，避免每个仓库都读一次文件。

**`inventory/thresholds_test.go`**（新建，未追加到冻结文件）
覆盖：已配置仓库用自己的值、未配置回退默认、文件缺失回退、JSON 非法回退、`IsLowStock` 严格小于、`LowStockWarehouses` 按仓库阈值判定并排序。

## 两个需要你知道的判断

1. **路径按两个候选依次尝试**：需求给的是 `inventory/thresholds.json`（仓库根相对），但 `go test` 的工作目录是包目录 `inventory/`，此时该路径会错位成 `inventory/inventory/thresholds.json`。所以先试 `inventory/thresholds.json`，再试 `thresholds.json`。我做了端到端验证：在仓库根放 `inventory/thresholds.json` 后，包内测试确实能读到（返回 20）。服务从仓库根启动时走第一个候选。
2. **不缓存配置**：每次调用重新读，避免测试顺序或文件更新导致读到陈旧配置；代价是每次判定有一次文件读取，对这个规模的服务可接受。

**没有创建 `inventory/thresholds.json`**：按需求“文件不存在就回退默认值”，机制已具备；需要配置时按 `{"shanghai": 20}` 放到仓库根即可。

## 门禁证据

- `make check`：build / test / vet 全通过；`-count=1` 强制非缓存跑也通过。
- `git diff --exit-code -- inventory/stock_test.go` 通过，冻结的 `stock_test.go` 逐字节未动；工作区只改了 `stock.go`、新增 `thresholds_test.go`。
