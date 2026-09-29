# 06-exception-path / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：1403.1s
- token：4470063
- 步数：60，工具调用：72

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

批末收尾完成，goal 已关闭。下面是交付报告。

## 结论

- **需求分支**：`feat/stock-tweak`（tip `ae1eb08`），已推到 `origin`，**当前就留在这条分支上**，与 `origin/feat/stock-tweak` 同步。
- **未开 PR**：仓库没有 GitHub 远端（`origin` 是本地 bare 仓库，`gh` 未安装），按本地模式交付。
- **最终门禁**：`make check` 退出码 **0**（build + test + vet）；`go test -trimpath -count=1 ./...` 也是 0。
- **冻结基线未动**：`inventory/stock_test.go`（`bc6044…`）与 `Makefile`（`099fd6a…`）哈希与 `main` 逐字节一致。

## 两个 issue 的处置

| issue | 状态 | 说明 |
|---|---|---|
| issue-001 阈值来源改成配置文件 | ✅ shipped，1 个 commit `ae1eb08` | `LowStockThreshold` 读仓库根 `config/thresholds.json`；配了用自己的，没配/文件缺失/读不出/非 JSON 对象/条目坏值（含 `null`）一律回退 `DefaultLowStockThreshold`。判定规则保持严格小于。新增测试文件 `inventory/stock_config_test.go`，验收证据写进 `requirements/01_REQ-stock-tweak/README.md`。 |
| issue-002 判定改成含等于 | ❌ failed（不可在冻结基线下完成） | 见下。留档分支 `feat/issue-002-inclusive`（`9265d4f`，本地，未推）。 |

**issue-002 为什么做不了**：它的验收条件要求 `IsLowStock(w, LowStockThreshold(w)) == true`；而冻结测试 `stock_test.go` 的 `TestIsLowStockUsesStrictLessThan` 对未配置仓库 `chengdu`（阈值回退默认 5）断言 `IsLowStock(chengdu, 5) == false`。同一个函数、同一组入参，直接互斥；又因 `TestUnconfiguredWarehouseFallsBackToDefault` 把 `chengdu` 的阈值钉死为默认值，无法用配置绕开。冻结测试逐字节不许改，所以「含等于」与「`make check` 绿」不可能同时满足。我按规则把它记为 `failed`、把尝试实现（`<` → `<=`，`make check` 唯一失败在 `stock_test.go:25`）留档到独立分支，需求分支上不留红。

## 评审

`/review-it` 派了不共享上下文的对抗性评审者，共三轮：第一、二轮均 `revise`（依次修掉：公开入口缺证据、`-trimpath` 下路径静默回退、坏条目拖垮整份配置、README 命令空转、`null` 解析成 0、默认路径接缝无测试），第三轮 **`accept`**，无遗留阻塞项。

## 需要你拍板的一件事

**issue-002 只能二选一**：① 放宽冻结基线（改 `stock_test.go` 的严格小于断言，并同步更新哈希核对）；② 修改 issue-002 的验收条件。你定了之后，`feat/issue-002-inclusive` 可以直接作为起点（它已基于修好的 issue-001）。合入默认分支这一步按流程归你（本地 `--no-ff` 合入）。
