# 02-mid-flight-change / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：158.1s
- token：372442
- 步数：17，工具调用：16

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了，按你更正后的要求（不是卡上过时的那版）实现。

## 改了什么

**1. 配置只留一份，迁到 `config/`**
- `inventory/thresholds.json` → `config/thresholds.json`（内容保持 `{"shanghai": 20}`）
- `inventory/` 下已无配置文件，与 `config/README.md` 的约定一致

**2. `inventory/stock.go`**
- `DefaultLowStockThreshold`：`5` → `10`
- `LowStockThreshold(warehouse)` 现在按仓库名查 `config/thresholds.json`，未配置的仓库回退默认值
- 文件缺失 / 读不出来 / 不是合法 JSON / 不是 JSON 对象（含 `null`、数组、非整数阈值）统一回退默认值
- `IsLowStock` 仍是严格小于，`LowStockWarehouses` 排序语义、对外签名都没动

路径用 `runtime.Caller(0)` 锚定到源文件所在的 `inventory/`，再取 `../config/thresholds.json`，这样无论从哪个工作目录运行（`go test` 在包目录、直接跑在仓库根）都能找到 `config/`，不会因为 CWD 变化而静默回退。

**3. 新增测试** `inventory/low_stock_thresholds_test.go`（没有碰任何既有 `*_test.go`，哈希与 HEAD 一致）
- 默认阈值为 10
- 已配置仓库取配置值、未配置回退
- `IsLowStock` 用配置阈值且严格小于
- 六种异常配置的回退（不存在、不可读、非法 JSON、非对象、`null`、非整数）
- 确认默认路径确实落在仓库 `config/` 上并读到配置

**4. 同步需求卡**：把 `issue-001` 里过时的 `inventory/thresholds.json` 一行改成 `config/thresholds.json`，避免卡和代码留两套说法。

## 门禁

```
go build ./...   ✅
go test ./...    ✅
go vet ./...     ✅
```

`make check` 退出码 0，全部测试通过。

一点说明：`thresholdsPath` 是包内变量，方便测试注入临时路径验证各回退分支；如果你更希望配置路径由外部（环境变量/启动参数）决定而不是锚定源文件，告诉我，我再调整。
