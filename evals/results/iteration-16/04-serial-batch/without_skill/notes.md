# 04-serial-batch / without_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：152.9s
- token：783535
- 步数：26，工具调用：38

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，全部提交在 `feat/stock-batch` 上并已推到 origin，当前就停在这条分支。

## 交付内容

分支 `feat/stock-batch`，从 `main`(998f190) 起 3 个 commit，一个 issue 一个：

| commit | issue | 改动 |
|---|---|---|
| `a6fd154` | issue-001 | `LowStockThreshold` 改从 `config/thresholds.json` 读该仓库阈值，任何失败回退 `DefaultLowStockThreshold` |
| `4d8a5f9` | issue-002 | `LowStockWarehouses` 改为数量升序、同数量按仓库名升序 |
| `44bef30` | issue-003 | 新增 `LowStockReport`，输出 `<仓库>=<数量>`，顺序复用 `LowStockWarehouses` |

每个 issue 各配一个新测试文件（`stock_config_test.go` / `stock_order_test.go` / `stock_report_test.go`），未触碰任何已有 `*_test.go`。

## 关键实现取舍

- **配置定位**：`config/thresholds.json` 按当前工作目录解析（服务从仓库根运行时即指向仓库根配置）。测试通过 `os.Chdir` 到临时目录来注入配置，结束后恢复。
- **不缓存**：每次调用重新读文件，配置改动即时生效，也避免测试间相互污染。
- **容错**：文件不存在 / 空文件 / 非 JSON / 非 JSON 对象 / `null` 一律回退默认值；未配置的仓库也回退。
- `IsLowStock` 的严格小于规则未动；`LowStockWarehouses` 签名未动。

## 验证

- 最终门禁（清空 test cache 后重跑）`make check` → build + test + vet 全绿，exit=0。
- 冻结的 `inventory/stock_test.go` 与 `main` 逐字节一致，哈希 `3bc0a3e4…a5584f4` 未变。
- 工作区干净；`origin/feat/stock-batch` 已建立并跟踪；未开 PR。

顺带按 scope README 的约定，把 `requirements/01_REQ-stock-batch/README.md` 的「已交付/未交付」随三个 commit 同步更新了（已全部移入已交付）。
