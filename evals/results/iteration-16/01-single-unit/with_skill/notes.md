# 01-single-unit / with_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：272.5s
- token：633618
- 步数：16，工具调用：25

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

## 完成情况

**技能与模式**：加载的是 `let-it-go` 技能集里的实现入口 **`loop-it`**。这是**单单元**（一条诉求，且来源/格式/回退规则都已给全，落地方案不需要另定），所以按单单元模式内联做完，未开循环、未建 worktree/分支。

### 改动（3 处，均在仓库内）

| 文件 | 改动 |
|---|---|
| `inventory/stock.go` | `LowStockThreshold` 改为先查配置，查不到回退 `DefaultLowStockThreshold`；新增 `readThresholds` |
| `inventory/thresholds_test.go` | **新建**测试文件（没碰冻结的 `stock_test.go`） |
| `requirements/warehouse-thresholds/README.md` + `requirements/README.md` | 按仓库约定登记 scope、验收条件与证据 |

核心逻辑：

```go
var thresholdsPath = "inventory/thresholds.json"   // 包内测试接缝

func LowStockThreshold(warehouse string) int {
    if threshold, ok := readThresholds(thresholdsPath)[warehouse]; ok {
        return threshold
    }
    return DefaultLowStockThreshold
}
```

### 验收证据（按层给，不互相替代）

| # | 验收条件 | 证据 |
|---|---|---|
| A1 | 配了的仓库用自己的阈值 | L1：`TestConfiguredWarehouseUsesOwnThreshold` PASS |
| A2 | 没配的仓库回退默认值 | L1：`TestWarehouseMissingFromFileFallsBackToDefault` PASS |
| A3 | 文件不存在全部回退 | L1 + **L3**：删文件后从仓库根跑真程序读回 `shanghai=5 chengdu=5` |
| A4 | 来源/格式为 `inventory/thresholds.json` | **L3**：仓库根放 `{"shanghai": 20}`，读回 `shanghai=20 chengdu=5` |
| A5 | 新阈值参与 `IsLowStock`/`LowStockWarehouses` | L1：`TestConfiguredThresholdAppliesToStockChecks` PASS |
| A6 | 门禁绿、冻结测试逐字节不变 | `make check` EXIT=0；`stock_test.go` SHA-256 `54dfdfa5…8882` 与 seed 一致 |

- **门禁**：`make check`（build + test + vet）退出码 0，10 个测试全绿（4 冻结 + 6 新增），`gofmt -l` 无输出。
- **L3 验证脚本已清理**，`git status` 只剩预期改动，无残留文件。

### 复核（Spec / Standards 两轴）

- **Spec 轴**：6 条验收条件逐条对上，无 missing / extra / wrong。新测试文件是必要产物，`thresholdsPath` 变量是最小测试接缝，requirements 文档是仓库约定要求的落点。
- **Standards 轴**：nil map 索引安全；用 `ok` 区分「配了 0」与「没配」；错误处理遵循签名（无 error 返回，按 spec 静默回退）；风格与仓库一致（中文注释、包内小函数）。
- **已知取舍**：每次判定重新读文件（不缓存）——实现最小、文件改动立即生效、便于测试；代价是 `LowStockWarehouses` 每个仓库一次文件读。若后续要上高频路径，可加 `sync.Once`/mtime 缓存，但那会让「文件不存在回退」与热更新语义变复杂，当前 spec 未要求。

### 一点说明

按你「改完跑门禁」的范围，我**没有提交、没有 push、没有开 PR**（仓库的 `origin` 只是本地 `eval-origin.git`）。改动都在工作树里。如果你要我把这次改动 commit 到 `main`（或切 `feat/warehouse-thresholds` 分支）并交付，说一声我就走 `ship-it`。
