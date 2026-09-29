# 01-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：138.4s
- token：264242
- 步数：13，工具调用：17

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

改完了，`make check`（build + test + vet）全绿。

## 改了什么

**`inventory/stock.go`**（唯一改动的既有文件）
- 新增常量 `thresholdsPath = "inventory/thresholds.json"`，相对进程工作目录解析。
- `LowStockThreshold(warehouse)` 改为：先查 JSON 里的该仓库阈值，命中就返回；否则返回 `DefaultLowStockThreshold`。
- 新增未导出 `loadThresholds(path)`：读取并解析 `map[string]int`；**文件不存在、解析失败都返回 nil**，走回退。
- `IsLowStock`、`LowStockWarehouses`、`DefaultLowStockThreshold` 原样未动。

**`inventory/thresholds_test.go`**（新建，没碰冻结的 `stock_test.go`）
- 配置命中：`{"shanghai":20}` → shanghai=20、chengdu 回退 5，且 `IsLowStock` 仍严格小于。
- 文件缺失 → 全回退默认值。
- 文件损坏 → 回退默认值。
- `LowStockWarehouses` 按各仓库自己的阈值判定并排序。

## 验证

- 冻结测试文件哈希与 HEAD 逐字节一致：`881f5d64…`（`git diff` 为空）。
- 8 个测试全 PASS（原有 4 + 新增 4）。
- 额外从仓库根目录做了一次真实端到端：有 `inventory/thresholds.json` 时 `shanghai=20`、`chengdu=5`、聚合 `[chengdu shanghai]`；删掉文件后全部回退 5、聚合 `[chengdu]`。临时文件已清理，工作区只剩 `stock.go` 改动与新增测试文件。

## 两个我做主的判断（供你复核）

1. **路径按进程工作目录解析**。`inventory/thresholds.json` 字面就是相对 cwd 的路径，服务从仓库根目录启动即可命中；从别处启动则视为「文件不存在」回退默认值。这是唯一自然的读法，我没有加多路径探测之类的兜底。
2. **每次调用重新读文件**，没有缓存。因为需求没规定加载时机/热更新语义，读盘每次调用都能反映当前文件，行为最简单也最好测；代价是 `LowStockWarehouses` 会对每个仓库各读一次盘。如果你们期望启动时加载一次并缓存，告诉我，我改成 `sync.Once` 或显式 `Load()`。

另外按你的要求没有加载任何技能，也没有新建 `requirements/` 下的需求文档（你没要，且明确说直接做完）。
