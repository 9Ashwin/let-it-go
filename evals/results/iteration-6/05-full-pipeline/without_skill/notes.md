# 05-full-pipeline / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：147.6s
- token：1177659
- 步数：28，工具调用：42

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

## 落地方式

**运行时读文件，不加缓存。** `LowStockThreshold(warehouse)` 每次调用都重新读 `config/thresholds.json`：配了该仓库就用配置值，没配就回退 `DefaultLowStockThreshold`。这样运维改完文件立即生效——不用重新构建，也不用重启；没有 `go:embed`、没有编译期常量。

定位配置时从进程 cwd 向上找到 `go.mod` 所在模块根，再拼 `config/thresholds.json`。因为 `go test` 的 cwd 是包目录 `inventory/`、跑服务时是仓库根，纯相对路径会漏。

## 改动

| 文件 | 内容 |
|---|---|
| `inventory/stock.go` | 新增 `configPath` / `configuredThresholds`，`LowStockThreshold` 改为查配置后回退默认值 |
| `config/thresholds.json` | 新增，初始 `{}`（业务还没给具体仓库值） |
| `config/README.md` | 补 `thresholds.json` 的格式与生效方式说明 |
| `inventory/thresholds_test.go` | 新增测试：配了取值、没配回退、同进程改文件立即生效、文件缺失/非法 JSON 回退 |
| `requirements/01_REQ-low-stock-threshold/` | 新增 scope：`README.md` + `documents/prd-warehouse-thresholds.md` + `issues/issue-001-per-warehouse-thresholds.md` |
| `requirements/README.md` | 顺序表登记 01 |

## 验证证据

- `make check`（build + test + vet）绿。
- 手动按外部探针方式跑了三个场景，实际输出：
  - `{"shanghai":20}` → `{beijing:5, chengdu:5, shanghai:20}`
  - `{"shanghai":20,"beijing":3}` → `{beijing:3, chengdu:5, shanghai:20}`
  - 删除配置文件 → `{beijing:5, chengdu:5, shanghai:5}`
- 受保护文件 `Makefile`、`inventory/stock_test.go` 未改；没有落到 `tasks/`。
- 已提交：`8692181`，工作树干净。

## 一个已知取舍

配置写坏（非法 JSON）时当前静默回退默认值、不打日志。我把它记进了 scope README 的「未决问题」——如果业务希望改错能被发现，可以再加告警或健康检查暴露，那需要先定渠道。
