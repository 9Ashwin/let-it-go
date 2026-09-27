# 02-mid-flight-change / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：393.5s
- token：1247125
- 步数：24，工具调用：40

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。按 loop-it 的单单元流程走完了：实现 → 门禁自证 → 独立评审 → 交付。

## 改了什么

| 文件 | 变更 |
|---|---|
| `inventory/stock.go` | `LowStockThreshold` 读取 `config/thresholds.json` 按仓库取阈值；`DefaultLowStockThreshold` 5 → 10；新增路径解析与 JSON 读取 |
| `config/thresholds.json` | 新建（内容 `{"shanghai": 20}`），阈值配置的唯一来源 |
| `inventory/thresholds.json` | **删除**，不再留两套 |
| `inventory/thresholds_test.go` | 新建测试文件（不碰冻结基线），覆盖配置命中、回退、严格小于、仓库边界 |
| `requirements/.../issue-001-*.md` | 卡片过时来源改为 `config/thresholds.json`，补上「默认 10」验收项，并记录交付状态与实现总结 |
| `requirements/01_REQ-low-stock-threshold/README.md` | 新建 scope README，放验收证据表 |

关键实现点：`go test` 时工作目录是包目录 `inventory/`，所以路径解析从当前目录逐级向上找 `config/thresholds.json`，以 `go.mod` 为仓库边界即停；找不到或内容不是 JSON 对象就回退默认值。每次调用重新读文件、不缓存，保证「改配置立即生效」和回退行为可观测。

## 验证

- `make check`（build + test + vet）**绿**，12 个测试全过。
- 冻结基线 `inventory/stock_test.go` 与 seed commit **逐字节一致**（`cmp` 通过）。
- 两轮独立子代理评审（作者不自审）：首轮 `accept`，复核轮 `accept`，无 must-fix；变异测试证明「配置读取」这条关键路径确实被测试守住。

## 交付

`gh` 未安装、远端只是仓库内的本地 bare repo，按 ship-it 走**本地模式**：

- 需求分支 `feat/low-stock-threshold`：`dc55bbd` 实现 + `4536b3d` 交付记录
- 已 `--no-ff` 合入 `main`（`9810945`），分支保留作留档
- 按技能约定本地模式**未 push**（远端不是 GitHub、无 PR 可开）。如果你希望我把 `main` 推到那个本地 origin，说一声即可。
