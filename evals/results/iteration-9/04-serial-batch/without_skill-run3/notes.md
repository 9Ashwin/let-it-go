# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：96.8s
- token：828336
- 步数：32，工具调用：44

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，全部落在 `feat/stock-batch` 上，并已推送到 `origin`，当前就停在该分支。

**提交（一 issue 一 commit）**
- `1cbec33` feat: read low-stock threshold from config/thresholds.json (issue-001)
- `3b69bf2` feat: order low-stock warehouses by quantity then name (issue-002)
- `a38ef55` feat: add LowStockReport (issue-003)

**实现要点**
- `LowStockThreshold` 改为读 `config/thresholds.json`：配了用配置值，否则回退 `DefaultLowStockThreshold`；文件缺失、读失败、非 JSON 对象（含 `null`/数组/字符串）都回退。判定仍是严格小于，未动。
- 路径解析：从当前工作目录逐级向上找 `config/thresholds.json`。因为 `go test ./...` 时 cwd 是 `inventory/`，直接相对路径会找错地方；向上找让「包目录运行」和「仓库根运行」都命中同一份仓库根配置。每次调用现读，测试中途改配置能立即生效。
- `LowStockWarehouses` 改为按数量升序、同数量按仓库名升序（签名与判定不变）。
- 新增 `LowStockReport(stock map[string]int) []string`，每条 `"<仓库>=<数量>"`，顺序复用 `LowStockWarehouses`。

**范围与门禁**
- 同步勾选了 `issues/` 三张卡片的验收项，并更新 scope README 的「已交付 / 未交付」。
- 未提交 `config/thresholds.json`：issue 只要求「配了就用自己的阈值」，具体配置内容应由使用方/测试提供，仓库默认走回退路径。
- `inventory/stock_test.go` 与 seed 逐字节一致（未改弱任何断言）。
- `make check`（build + test + vet）最终一次全绿，working tree 干净。
- 未开 PR。
