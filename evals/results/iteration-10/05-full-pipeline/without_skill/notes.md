# 05-full-pipeline / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：110.4s
- token：526997
- 步数：19，工具调用：27

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，门禁 `make check` 全绿。

## 改了什么

**1. 配置：`config/thresholds.json`（新增）**
```json
{
  "beijing": 10,
  "shanghai": 3
}
```
「仓库名 → 阈值」的扁平 map，只写要覆盖默认值的仓库。

**2. `inventory/stock.go`**
- `LowStockThreshold(warehouse)` 每次调用都重新读 `config/thresholds.json`：配了返回配置值，没配返回 `DefaultLowStockThreshold`（保持 5）。
- 文件缺失或 JSON 非法时整体回退默认值。
- 定位文件：先从进程工作目录逐级往上找 `config/thresholds.json`，找不到再退回本包源码所在仓库位置（兼容 `go test` 工作目录是包目录的情况）。
- `IsLowStock` / `LowStockWarehouses` 签名和行为不变。

**3. 测试：`inventory/per_warehouse_threshold_test.go`（新增）**
覆盖按仓库生效、改文件即时生效、未配置回退默认、缺失/非法配置回退默认。**`stock_test.go` 逐字节未动**（已 `git diff` 校验）。

**4. 仓库约定**
按 `requirements/README.md` 的要求，新建 `requirements/001-per-warehouse-low-stock-threshold/` 并在「当前顺序」表登记；`config/README.md` 补了 `thresholds.json` 的格式与热加载说明。

## 关键设计决定（"改配置不重新构建"）

不做进程内缓存，**每次调用直接读盘**。这是"改文件即生效"最直接、无失效窗口的实现；本服务规模下开销可忽略。如果以后判定 QPS 高，可换成按 mtime/size 校验的缓存，行为不变。

## 验证

- `make check`：build + test + vet 全绿。
- 端到端热加载探针：配置 `beijing=42` 跑通后，**只改文件**为 `beijing=7`、不重新编译，再跑同一测试，`LowStockThreshold("beijing")` 已返回 7 —— 证明读的是改动后的文件，不是编译期快照。探针文件与配置已还原/清理。

未提交，工作区里的改动等你确认。需要我提交的话说一声。
