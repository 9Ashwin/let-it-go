# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：365.7s
- token：1585624
- 步数：33，工具调用：48

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。按 let-it-go 的 **loop-it** 技能走了串行批次流程，三条 issue 全部做完。

## 交付状态

- **分支**：`feat/stock-batch`，已推送到 `origin` 并停在该分支（`## feat/stock-batch...origin/feat/stock-batch`，无领先/落后）。按要求未开 PR（仓库也无 GitHub 远端）。
- **提交**（一个 issue 一个 commit，基于 `main` 线性推进）：
  - `e19a9c0` feat: read low-stock threshold from config/thresholds.json — issue-001
  - `d220496` feat: order low-stock warehouses by quantity then name — issue-002
  - `43f4715` feat: add LowStockReport in LowStockWarehouses order — issue-003
- **门禁**：批末 `make check`（build + test + vet）绿，exit 0。

## 各 issue 做法与证据

| issue | 实现 | 证据（test/pass） |
|---|---|---|
| 001 阈值来源 | `LowStockThreshold` 读 `config/thresholds.json`；路径由包级 `thresholdsPath` 承载，默认相对源码定位到仓库根 config，避免 `go test` 在 `inventory/` 下跑时 cwd 相对路径失效；文件缺失/读失败/非 JSON 对象均回退 | `TestLowStockThreshold*`（配置命中、未配置回退、不存在/读不出/数组/非法 JSON） |
| 002 列表顺序 | `LowStockWarehouses` 改 `sort.Slice`，键为（数量, 仓库名），签名与 `IsLowStock` 严格小于判定未动 | `TestLowStockWarehousesSortedByQuantity`、`...TieBreaksByName` |
| 003 报告 | 新增 `LowStockReport`，复用 `LowStockWarehouses` 的顺序拼 `<仓库>=<数量>`，不改该函数 | `TestLowStockReport*`（格式、逐项顺序一致、非低库存排除） |

每个 issue 都是在实现后由**全新上下文的 supervisor** 独立复核（首次均 `accept`），并逐条落进 `<scope>/issues/.loop-state.json` 检查点（evidence / decisions / verification / open）。

## 批末评审（review-it，两轴分开）

- **Spec 轴：干净**。三条卡片的验收条件逐条对上，无非目标越界（`IsLowStock` 严格小于、`LowStockWarehouses` 签名、seed 文件 `inventory/stock_test.go` 均未动，逐字节一致）。
- **Standards 轴：无阻断项**。两条中等建议我判定不在本批修并留痕 drop：
  - S1 每次调用按仓库逐次读盘——本 fixture map 很小，修复要在判定路径再引入一条阈值解析分支，收益不抵复杂度；
  - S2 真实默认配置路径无仓库内测试守护——落地测试要往仓库根写 `config/thresholds.json`，失败残留会污染 seed 的「未配置回退」断言，改由评审在仓库外副本交叉验证。
  这两条连同 issue-001 的两条低优先级观察（对象内 `null`→阈值 0、`-trimpath` 下路径失效）都已记入检查点并明确 drop 了原因。

## 说明

- 检查点 `.loop-state.json` 通过 `.git/info/exclude` 忽略，未进版本库，因此分支 diff 只有 4 个代码/测试文件（+196/-4）。
- 我**没有**改 `requirements/01_REQ-stock-batch/README.md` 的「已交付/未交付」，以免产生第 4 个非 issue 提交；若需要更新台账可以再说。
