# 06-exception-path / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：1556.7s
- token：5198028
- 步数：52，工具调用：76

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。以下是交付结果与一个需要你拍板的冲突。

## 分支与提交

| 分支 | commit | 内容 |
|---|---|---|
| **`feat/stock-tweak`**（当前所在、已推 origin） | `148f36d` | issue-001：阈值来源改成配置文件 |
| `feat/issue-002-inclusive`（留档、已推 origin） | `ff5d0a8` | issue-002 的冲突记录 |

- 每个 issue 一个 commit，message 不带编号；**没有开 PR**（`gh` 不可用、无 GitHub 远端），只把分支推到本地 `origin` 并停在 `feat/stock-tweak` 上。
- 门禁 `make check` 绿（EXIT=0）；冻结基线 `inventory/stock_test.go` 与 `Makefile` 逐字节未变（哈希与 seed `dd04260` 一致）。检查点在 `requirements/01_REQ-stock-tweak/issues/.loop-state.json`（已 gitignore）。

## issue-001 ✅ 已交付

`LowStockThreshold(warehouse)` 现在读 `config/thresholds.json`：配了用自己的、没配/文件不存在/读不出来/内容不是 JSON 对象一律回退 `DefaultLowStockThreshold`；`IsLowStock` 保持严格小于（非目标）。新建 `inventory/thresholds_test.go`（未追加进冻结文件），覆盖配置命中、回退、非对象各型、真实配置文件读取。

## issue-002 ⚠️ 未实现 —— 与冻结验收基线硬冲突，需你裁决

这不是"没做完"，是**验收条件之间逻辑互斥**，且 skill 的 `error-recovery.md` 专门有 `spec_conflict` 这一档：**不要改冻结文件换绿，写进卡片与 scope README，等人裁决**。

矛盾点（三条不可同时成立）：
1. 冻结基线 `TestUnconfiguredWarehouseFallsBackToDefault` 要求未配置仓库 `LowStockThreshold(w) == 5`；
2. 冻结基线 `TestIsLowStockUsesStrictLessThan` 要求 `IsLowStock(w, 5) == false`；
3. issue-002 验收条件要求 `IsLowStock(w, LowStockThreshold(w)) == true`，对未配置仓库即 `IsLowStock(w, 5) == true`。

我实测复现：把 `IsLowStock` 改成 `<=` 后，issue-002 的验收断言通过、但冻结基线 `stock_test.go:25` 变红；保持 `<` 则相反。我也排除了"按阈值来源拆分语义"的绕法——它让判定规则取决于配置来源，语义不自洽且违背 issue-002 的目标。

**请你二选一：**
1. **授权改冻结基线**：同步改 `stock_test.go` 的 `TestIsLowStockUsesStrictLessThan`（及我新增的 `TestConfiguredThresholdKeepsStrictLessThan`）再实现 `<=` —— 这会改变交付核对的基线哈希，必须你点头；
2. **放弃 issue-002**，维持严格小于。

完整证明与选项写在 `feat/issue-002-inclusive` 的 `requirements/01_REQ-stock-tweak/issues/issue-002-inclusive.md`，scope README 也标注了。

## 评审

批末派了两个**不共享上下文**的子代理做对抗性评审，结论均为 `accept`。按首轮发现做了两处非阻塞修正并已并入 issue-001 commit：
- 配置仓库改用冻结测试未引用的 `beijing/shanghai`，消除"`xian` 阈值必须 >0"的隐藏耦合；
- `loadThresholds` 对 `null`（解析成 nil map）也返回 `ok=false`，并补白盒测试 `TestLoadThresholdsContract` 守住（移除该修复后测试转红已验证）。

证据层级：issue-001 的验收条件落在 L1/L2（纯库函数、无服务入口，L3 不适用），已在检查点记录并如实标注。
