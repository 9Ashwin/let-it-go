# 01-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：105.5s
- token：239440
- 步数：11，工具调用：18

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

改完了，门禁绿。

## 改动

**`inventory/stock.go`** — `LowStockThreshold` 现在按仓库取值：

- 从 `inventory/thresholds.json`（`{"shanghai": 20}` 形式）读 `map[string]int`；
- 命中该仓库就用配置值；
- 文件不存在、读取/解析失败、或该仓库没配，一律回退 `DefaultLowStockThreshold`；
- `IsLowStock` / `LowStockWarehouses` 不用动，它们本来就经过 `LowStockThreshold`。

两个实现选择说明一下：

1. **路径解析**：文件按“与包源码同目录”定位（用 `runtime.Caller`），也就是仓库根下的 `inventory/thresholds.json`。这样无论进程从仓库根启动，还是 `go test` 从 `inventory/` 目录启动，都读同一个物理文件，不依赖 CWD。
2. **每次调用重读，不做 init 缓存**：配置改动无需重启；也让测试在运行时创建文件后立刻生效，避免“首次调用把缺失状态缓存住”的坑。

**没有提交 `inventory/thresholds.json` 本体**：它是可选的运维配置，缺失即全部走默认值，符合你的回退要求。

## 测试

- `inventory/stock_test.go` **一字未动**，改前改后哈希都是 `a9a92c27…`（按约定验收基线冻结）。
- 新行为测试放在新文件 `inventory/thresholds_test.go`，覆盖：配置仓库取配置值、未配置仓库回退默认、文件缺失回退、JSON 损坏回退、`IsLowStock` 严格小于用的是配置阈值、`LowStockWarehouses` 混用两种阈值且排序正确。测试写文件后自行清理还原。

## 门禁

`make check`（build + test + vet）全绿，`exit=0`。工作区只有 `stock.go` 修改 + 新增 `thresholds_test.go`，没有残留的 `thresholds.json`。

一点提醒：如果生产里仓库数量很大、`LowStockWarehouses` 会被高频调用，现在是每仓库读一次文件；要压这点可以后续加一层带 mtime 失效的缓存，但那是另一个需求了，这次没做。
