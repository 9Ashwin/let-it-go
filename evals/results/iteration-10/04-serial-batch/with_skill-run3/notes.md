# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：576.2s
- token：2627163
- 步数：37，工具调用：68

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已按 `loop-it`（let-it-go 技能集）的串行批处理流程做完这 3 条本地 issue 卡片。

## 结果

**分支**：`feat/stock-batch`，已推送到 `origin`，**当前就留在它上面**（验收直接看这条分支），未开 PR。

**提交**（`main..HEAD`，一个 issue 一个 commit）：

| commit | 内容 |
|---|---|
| `195c213` | `feat: issue-001 阈值来源改成配置文件` |
| `1dabf07` | `feat: issue-002 低库存列表的顺序` |
| `9b2f6dc` | `feat: issue-003 低库存报告` |
| `d4dfab2` | `docs: issue-001..003 交付走查与需求资料更新`（批末交付件，非 issue 实现） |

**门禁**：`make check` 绿（build + test + vet）。并且把 `origin/feat/stock-batch` 全新 clone 出来再跑了一遍 `make check`，同样绿，确认推送出去的就是可验收的。

**实现要点**（都在 `inventory/stock.go`）：
- `LowStockThreshold` 从仓库根 `config/thresholds.json` 读；文件缺失/读不出/非 JSON 对象整体回退，单个非法值（含 `null`）逐仓库回退，严格小于判定未动。
- `LowStockWarehouses` 改为数量升序、同数量按仓库名升序；抽出的内部 `lowStockSorted` 是排序的单一来源。
- 新增 `LowStockReport`，与 `LowStockWarehouses` 复用同一排序，保证同序。
- 新增 3 个测试文件（11 条测试）；冻结的 `inventory/stock_test.go` 与基线逐字节一致（diff 0 字节）。

**批末对抗性评审**（全新上下文子代理，两轮）：第二轮 Spec 轴、Standards 轴均 `accept`。第一轮的真实发现已修并复验——补了真实路径解析测试、`null` 不再被静默当 0、单个坏值不再作废整份配置；「每次调用重读配置」的取舍经复核可接受并写进代码注释。

## 落盘产物
- 走查件：`requirements/01_REQ-stock-batch/notes/walkthrough-stock-batch.md`
- 需求资料：三张卡片的验收框已勾选并写入 commit + 证据；scope README 已把三项移入「已交付」
- 检查点：`requirements/01_REQ-stock-batch/issues/.loop-state.json`（3/3 shipped，每条验收条件都有 `evidence`；按技能默认排除出版本库，用 `.git/info/exclude` 忽略，未提交）

一个可留意的点：没有提交真实 `config/thresholds.json`——默认仍是「未配置→回退」语义，且冻结测试要求 `chengdu`/`wuhan` 保持未配置。要启用自定义阈值时新增该文件即可（别包含这两个仓库）。
