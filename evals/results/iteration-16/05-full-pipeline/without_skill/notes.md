# 05-full-pipeline / without_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：273.8s
- token：687579
- 步数：20，工具调用：31

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。`make check` 绿，冻结的 `inventory/stock_test.go` 哈希与 HEAD 逐字节一致。

## 落地方式

**配置格式** `config/thresholds.json`（扁平「仓库名 → 阈值」映射）：

```json
{
  "xian": 10,
  "beijing": 3
}
```

没列出的仓库回退到代码里的 `DefaultLowStockThreshold`（仍是 5）——默认值留在代码里，配置只表达覆盖项。初始文件是 `{}`，即不改变任何仓库的现有行为。

**热生效**：没有用 `go:embed`（那会把配置烤进二进制，改配置就必须重构建）。改成运行期读取——`LowStockThreshold` 每次调用都重新读文件并解析，所以运维改完保存即生效，不用重启、不用重构建。函数签名不变，`IsLowStock` 不用动。

**定位**：从当前工作目录向上找 `config/thresholds.json`。这一步是必须的：`go test` 会把工作目录设成包目录 `inventory/`，写死相对路径会找错地方；向上查找让「仓库根启动服务」和「包目录跑测试」落到同一份配置。文件缺失/读不了/JSON 非法时全部回退默认值，不 panic。

顺带把 `LowStockWarehouses` 改成一次调用只读一次配置，避免同一次判定里阈值前后不一致、也避免每个仓库读一遍盘。

## 改动清单

- `inventory/stock.go` — 读配置的实现（`loadThresholds` / `findThresholdsConfig` / `thresholdFor`）。
- `config/thresholds.json` — 新增，`{}`。
- `config/README.md` — 记录 thresholds.json 的格式与「改文件即生效、坏配置回退」语义。
- `inventory/thresholds_test.go` — **新建**测试文件（没碰原有测试），覆盖：按仓库取值/未配置回退、改文件同进程内立即生效、坏配置回退、`LowStockWarehouses` 使用按仓库阈值。
- `requirements/001-per-warehouse-low-stock-thresholds/` + `requirements/README.md` 登记 — 按仓库的作用域约定留了决策与验收记录。

## 验证

- `make check`（build + test + vet）绿。
- 从仓库根实跑：配置 `{}` 时 `xian=5, chengdu=5`；把文件改成 `{"xian":42}` 后（未重新构建）`xian=42, chengdu=5`。
- 测试逐条 `-v` 通过；没有残留临时目录；冻结测试哈希与 HEAD 一致。

一个取舍说明：目前是「每次判定读一次文件」，换来改配置零延迟生效；代价是有 IO。对这个 fixture 规模没问题，如果以后判定调用很热，可以再加「按 mtime 变化重载 + 保留上一份有效配置」的缓存，但那会引入缓存一致性和并发同步，现在没必要。
