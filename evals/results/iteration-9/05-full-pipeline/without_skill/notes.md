# 05-full-pipeline / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：105.8s
- token：485540
- 步数：18，工具调用：25

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，`make check` 全绿（build + test + vet），原有 `inventory/stock_test.go` 一字未动。

## 落地方式

配置在 `config/thresholds.json`，内容是「仓库名 → 阈值」的扁平 JSON 对象：

```json
{
  "shanghai": 10,
  "xian": 3
}
```

- 配了的仓库用配置值；**没配的（含空文件/缺文件）回退 `DefaultLowStockThreshold`（5）**。
- 判定语义不变：严格小于。
- **改文件即时生效，不用重新构建或重启**——每次判定都重新读文件，不做启动时缓存。代价是每次判定读一次小文件，对配置这种场景我认为可接受，也避免缓存陈旧值。

## 关键实现

- `inventory/thresholds.go`（新增）：读配置 + 解析；配置路径默认 `config/thresholds.json`，从当前目录**逐级向上找**。这样从仓库根启动、或 `go test` 在 `inventory/` 下跑，读到的都是仓库根那份配置。
- `inventory/stock.go`：`LowStockThreshold` 改为查配置；`LowStockWarehouses` 每次调用只读一次配置，避免按仓库重复读文件。
- `inventory/thresholds_test.go`（新增）：覆盖配置命中、未配置回退、**改文件后无需重建即读到新值**、缺失/损坏回退、`LowStockWarehouses` 混合场景。

## 验证

- `make check` 绿（10 个测试全过）。
- 额外做了一次端到端验证：把仓库根 `config/thresholds.json` 临时写成 `{"shanghai": 7}`，从 `inventory/` 目录跑测试，`shanghai` 读到 7、`wuhan` 仍回落默认值 5，确认向上查找与回退都生效；验证后已还原成 `{}`。

## 另外

按仓库约定把需求登记到了 `requirements/001-per-warehouse-low-stock-thresholds/`（含验收条件与决策记录），并在 `requirements/README.md` 顺序表里登记；`config/README.md` 补了 `thresholds.json` 的格式说明。全程没有加载任何 skill。

一个可讨论点：坏配置（非法 JSON）我选择**整体静默回退默认值**，因为现有 API 返回 `int`、没有错误通道。如果运维改错文件需要告警而不是静默降级，那需要把错误暴露出来（比如加一个 `ThresholdsError()` 或日志），这算接口层面的取舍，你定要不要做。
