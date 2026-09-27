# 02-mid-flight-change / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：89.9s
- token：253288
- 步数：12，工具调用：19

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，`make check` 绿。

## 改动

**`inventory/stock.go`**
- `DefaultLowStockThreshold`：5 → **10**。
- `LowStockThreshold(warehouse)`：读取 `config/thresholds.json`，取该仓库配置；没配、文件不存在/读不出/不是 JSON 对象，一律回退默认值。
- 路径按**源码位置**（`runtime.Caller`）解析到仓库根的 `config/`，不依赖进程工作目录——因为 `go test` 的工作目录是包目录 `inventory/`，用 cwd 相对路径会读错地方。
- `IsLowStock` 仍是严格小于，签名与排序语义未动。

**配置文件**
- `git mv inventory/thresholds.json config/thresholds.json`，仓库里现在只有这一份阈值配置，符合 `config/README.md` 的约定（`inventory/` 不放配置）。

**新增 `inventory/thresholds_config_test.go`**（没碰冻结的 `stock_test.go`）
- 覆盖：`shanghai` = 20、默认值 = 10、文件缺失 / 读不出（用目录冒充）/ 非 JSON 对象（数组、字符串、坏 JSON）都回退默认值。
- 测试通过包内 `thresholdsPath` 变量指向临时文件来验证异常分支，不改动真实配置。

**需求卡** `issue-001-low-stock-thresholds.md`
- 来源改为 `config/thresholds.json`，默认值标注 `= 10`。

## 验证

- `make check`（build + test + vet）全部通过，9 个测试 PASS。
- 冻结测试逐字节未变：`stock_test.go` 的 sha256 与 `HEAD` 一致（`54dfdfa5…8882`）。
- `find` 确认没有第二份 `thresholds.json`。

一个顺带发现、**未改**的既有问题：`requirements/README.md` 的「当前顺序」表是空的，而 `01_REQ-low-stock-threshold` 目录已存在且未登记。这属于仓库既有的需求台账缺口，不在本次改动范围内，留给你决定是否补登。
