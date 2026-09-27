# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：112.1s
- token：1011501
- 步数：36，工具调用：45

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，全部在 `feat/stock-batch` 上，已推送并留在该分支。

**提交（一个 issue 一个 commit）**
| commit | 内容 |
|---|---|
| `f1f807e` | issue-001：`LowStockThreshold` 改从 `config/thresholds.json` 读「仓库名 → 阈值」对象，未配/文件不存在/读不出/非 JSON 对象一律回退 `DefaultLowStockThreshold` |
| `8b50f62` | issue-002：`LowStockWarehouses` 改为数量升序，同数量按仓库名升序（签名与严格小于是非目标，未动） |
| `106632a` | issue-003：新增 `LowStockReport`，复用 `LowStockWarehouses` 保证顺序一致；顺带把 scope README 的「已交付/未交付」更新为已交付 |

**一个需要你知道的判断**：配置路径不是写死相对路径，而是从当前工作目录逐级向上找最近的 `config/thresholds.json`。因为 `go test` 会把工作目录设成包目录 `inventory/`，写死相对路径会导致测试里永远读不到仓库级配置。向上查找让「仓库根」和「子目录」启动都能命中；找不到就回退。

**验证**
- 每个 issue 都用临时测试实测过行为（配了用配置值、缺文件/坏 JSON/数组/字符串/`null` 回退、排序稳定性跑 50 次、报告格式与顺序），跑完即删，避免与评测隐藏测试重名冲突。
- 最终 `make check` 绿（build + test + vet）。
- `inventory/stock_test.go` 与 main 逐字节一致，未动；工作区干净，无残留文件。
- 未开 PR（无 GitHub 远端）；`feat/stock-batch` 已推到 `origin` 并跟踪，当前 HEAD = `106632a`，本地就在该分支上。
