# 01-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：89.0s
- token：378033
- 步数：16，工具调用：19

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

改完了，门禁绿。

## 改动

**`inventory/stock.go`**
- `LowStockThreshold(warehouse)` 现在先查每仓库配置，查不到才返回 `DefaultLowStockThreshold`，`IsLowStock` / `LowStockWarehouses` 沿用该函数，无需改动。
- 新增 `loadThresholds()`：读取 `inventory/thresholds.json`（`map[string]int`）。文件不存在、读不出、或 JSON 解析失败，都返回空配置 → 全部回退默认值。
- `findThresholdsFile()` 定位文件：优先按源码位置（即仓库根的 `inventory/thresholds.json`），再退回工作目录相对路径。这样无论进程 cwd 是仓库根还是 `go test` 的 package 目录都能读到同一个文件。
- 刻意**不缓存**：配置文件替换后立即生效，测试也能"先写文件再断言"。

**`inventory/thresholds_test.go`（新增）**
- 配了 `{"shanghai": 20}` 时用 20、未配置仓库回退默认值、`IsLowStock` 对该仓库严格小于；
- 配置非法 JSON 时回退默认值。
- 写完会恢复原文件，不污染环境。

## 验证

```
make check  → build + test + vet 全部通过 [exit code: 0]
go test -count=1 -v ./inventory/  → 6 个测试全 PASS
gofmt -l inventory/ → 无输出
```

受保护的 `inventory/stock_test.go` 与 seed commit 逐字节一致（`git diff` 为空），没有为过门禁改弱断言。

## 两点说明

1. 我**没有**提交 `inventory/thresholds.json` 本身——按"文件不存在就回退"的语义，它属于部署时的外部配置，留空即保持原默认行为。如果你想要一份示例/初始文件（比如 `{"shanghai": 20}`），我可以补上。
2. 需求里只说了"文件不存在 / 仓库没配"要回退；**JSON 解析失败**你没明确，我按同样的回退处理（静默降级），没有加报错通道。若你希望解析失败时显式报错或打日志，告诉我。

另外按你"不加载任何技能、直接做完"的要求，我没有走 `requirements/<scope>/` 那套需求文档流程，只动了代码。
