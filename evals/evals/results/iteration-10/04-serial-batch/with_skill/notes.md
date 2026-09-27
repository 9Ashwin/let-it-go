# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：574.0s
- token：4030690
- 步数：67，工具调用：85

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，整批落在 `feat/stock-batch` 上，每个 issue 一个 commit，已推到 origin 并留在该分支（未开 PR）。

## 交付结果

分支：`feat/stock-batch` → 已推送，`origin/feat/stock-batch` = 本地 HEAD = `83ef0e4`；`main` 未动。当前仍 checkout 在该分支，工作树干净。

| 项 | commit | 关闭的 issue | 验收证据（测试/命令） | 人工验收 |
|---|---|---|---|---|
| issue-001 阈值来源改成配置文件 | `7df8e08` | issue-001 | `TestConfiguredWarehouseUsesConfiguredThreshold`、`TestRelativeThresholdsFileFoundFromPackageDirectory`、`ThresholdsFile\|NonObject` 系列、`make check` | 尚未人工验收 |
| issue-002 低库存列表顺序 | `570ea3e` | issue-002 | `TestLowStockWarehousesOrderedByQuantityAscending`、`TestLowStockWarehousesTiesByNameAscending`、`make check` | 尚未人工验收 |
| issue-003 低库存报告 | `83ef0e4` | issue-003 | `TestLowStockReportFormat`、`TestLowStockReportMatchesLowStockWarehousesOrder`、`make check` | 尚未人工验收 |

## 实现要点

- **issue-001**：`LowStockThreshold` 改为读 `config/thresholds.json`（`{"<仓库>": <阈值>}`）；文件不存在、读不出来、内容不是 JSON 对象（含 `null`、数组、值类型错）一律回退 `DefaultLowStockThreshold`。路径用可注入的包级变量 `thresholdsFile`，相对路径会从 CWD 向上找，使 `go test`（CWD=`inventory/`）与从仓库根运行都能命中同一份配置。判定仍是严格小于。
- **issue-002**：`LowStockWarehouses` 用 `sort.Slice` 按（数量升序，同数量仓库名升序），签名与判定规则未动。
- **issue-003**：新增 `LowStockReport`，复用 `LowStockWarehouses` 的输出顺序，每条 `"<仓库>=<数量>"`，未改 `LowStockWarehouses` 本身。

## 门禁与基线

- 最终 `make check` 绿（build + test + vet），另用 `go test ./... -count=1` 强制重跑也绿。
- 冻结的 `inventory/stock_test.go` 相对 `main` **逐字节未变**（`git diff main...HEAD -- inventory/stock_test.go` 为空）；新行为全部写在新建的 `*_test.go` 里。
- scope README 已更新「已交付/未交付」与逐条验收表。

## 批末对抗性评审（两轮，均派未参与实现的子代理）

第一轮判定 `revise`，返工三处并已折回 issue-001 的 commit（仍是 3 个 commit）：
1. 给 `findThresholdsFile` 的相对路径向上查找补了测试——变异核验：砍掉该分支后测试确实变红。
2. README 去掉了不可复现的临时 `go run` runtime 断言，改引用可复现测试。
3. 记录冻结基线对真实配置的约束：`chengdu`/`wuhan` 必须未配置、`xian` 阈值须 `>0`（实测 `{"xian":0}` 会让 `TestLowStockWarehousesSorted` 变红）。

第二轮复审确认前两条已解决，指出第 3 条表述不全（漏 `xian`），已修正；核心变异（配置回退、顺序、报告同序）均被测试抓住。

**设计决策/权衡**：配置文件由使用方提供、本仓库不附带（issue 只要求读取来源，未要求附带数据）；`LowStockThreshold` 每次调用重新读文件（不缓存），以换取测试可观测性。**偏离**：无。**待确认**：无。

需求资料检查点保留在 `requirements/01_REQ-stock-batch/issues/.loop-state.json`（按技能默认排除出版本库，用 `.git/info/exclude` 而非额外 commit）。
