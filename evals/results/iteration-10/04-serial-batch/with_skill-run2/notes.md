# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：522.8s
- token：3673333
- 步数：51，工具调用：70

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已完成：按 `let-it-go` 技能集里的 **loop-it**（串行批次）流程做完整批，并在批末按 `review-it → walkthrough → ship-it` 收尾。

## 交付结果

**分支**：`feat/stock-batch`（当前所在分支），已推送并设为跟踪 `origin/feat/stock-batch`，`HEAD == origin/feat/stock-batch`，**未开 PR、未合入 main**。

**提交（一 issue 一 commit + 批末收尾）**

| commit | 内容 |
|---|---|
| `87f1058` | issue-001：阈值改从 `config/thresholds.json` 读（`#1`） |
| `9caf81a` | issue-002：低库存列表数量升序、同数量按仓库名升序（`#2`） |
| `714d72f` | issue-003：新增 `LowStockReport`，顺序与 `LowStockWarehouses` 一致（`#3`） |
| `5c0dc40` | 批末评审修复：整批只读一次配置、删除 test-only 全局 |
| `1191181` | 更新 scope README + `config/README.md` |
| `7b43496` | 走查件 + 交付记录 |

## 验收证据

- **issue-001**：`TestThresholdConfiguredValue` / `TestThresholdFallback` / `TestThresholdsFileDiscovery` 覆盖「配了用自己的 / 没配或文件缺失、不可读、非 JSON 对象一律回退」；集成实测 `kunming=3, chengdu=5`。
- **issue-002**：`TestLowStockWarehousesOrdering`（含并列数量）断言数量升序 + 名字升序；集成实测 `[chengdu xian shanghai wuhan]`。
- **issue-003**：`TestLowStockReport` 断言 `"<仓库>=<数量>"` 且逐项与 `LowStockWarehouses` 顺序一致。

## 门禁与红线

- `make check` **绿**（build + test + vet），工作树干净；`-` 冻结的 `inventory/stock_test.go` 与 seed commit `eac911e` **逐字节一致**；三个导出签名未变。

## 评审

- 第一轮全新子代理对抗性评审：Spec 轴 **accept**，Standards 轴 **revise**（逐仓库重复读配置、生产代码 test-only 全局）。
- 修复后第二轮另一子代理：Spec/Standards **双 accept**。遗留 M2/L1/L2 判定不修并已写清理由（配置属运行期数据不入断言；坏文件遮蔽祖先、JSON null/小数/负值语义卡片未定义）。

## 落盘产物

- 检查点（记录状态/决策/验证/evidence，已 git 忽略）：`requirements/01_REQ-stock-batch/issues/.loop-state.json`
- 走查件：`requirements/01_REQ-stock-batch/notes/walkthrough-stock-batch.md`
- 交付记录（逐项 commit/证据/人工验收 + 四类总结）：`requirements/01_REQ-stock-batch/records/2026-09-27-delivery.md`
- `requirements/01_REQ-stock-batch/README.md` 已更新「已交付/未交付」。

一点说明：`requirements/README.md` 的「当前顺序」表在 seed 里本来就是空的，属既有状态，按「只做自己该做的」未改动它。
