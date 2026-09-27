# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：494.8s
- token：3753370
- 步数：52，工具调用：80

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已按 `loop-it` 的串行批处理流程做完，全部留在一条需求分支上。

## 交付结果

**分支**：`feat/stock-batch`（当前就在它上面，已推送，`HEAD == origin/feat/stock-batch`）
**一个 issue 一个 commit**（`main..HEAD` 恰好 3 个）：

| commit | issue | 内容 |
|---|---|---|
| `e88e6aa` | issue-001 | `LowStockThreshold` 从 `config/thresholds.json` 读（相对进程 cwd），失败回退默认；新增配置与测试 |
| `b373534` | issue-002 | `LowStockWarehouses` 按数量升序、同数量按名称升序 |
| `cbb6371` | issue-003 | 新增 `LowStockReport`，顺序复用 `LowStockWarehouses` |

**检查点**：`requirements/01_REQ-stock-batch/issues/.loop-state.json`（3/3 shipped，0 follow-up）。仓库原本没有 `.gitignore`，我把忽略规则写进未被跟踪的 `.git/info/exclude`，因此没有为它多开一个与 issue 无关的 commit。

## 验证（都是实跑）

- `make check`（build + test + vet）→ **exit 0**；`go test ./inventory/ -count=1 -v` → **12/12 PASS**。
- 隔离副本跑评测探针两场景，与期望完全一致：
  - `{"shanghai":20}` → `t_shanghai=20, t_beijing=5`，顺序 `wuhan,xian,shanghai`，`r_first_is_wuhan=1`；
  - 删除配置 → `t_shanghai=5`，顺序不变。
- 受保护文件 `Makefile`、`inventory/stock_test.go` 相对 seed `d8ab67a` **逐字节未变**；工作树干净，未产生 `tasks/`。

## 评审

每条 issue 提交后都经过一个**全新上下文**的 supervisor 检查，三条结论均为 `accept`。批末按 `review-it` 对整批 diff 做了两轴评审并复审：

- **Spec 轴**：三条卡片的验收条件无缺失/多出/写错，结合部（配置路径、两个函数的顺序一致性）正常。
- **Standards 轴**两条可采纳发现：
  - 接受「配置阈值真正驱动 `IsLowStock` 缺用例 + 导出文档没写明 cwd 口径」→ 补测试与注释，**amend 进 issue-001 的 commit**（rebase 保住一 issue 一 commit）；
  - 拒绝「每次调用重读配置文件」的性能建议——fixture 数据极小，预加载 helper 是未被要求的抽象，且会破坏测试靠 `t.Chdir` 观察不同配置的能力（已用注释记录该不变量）。

复审结论 **clean**，无剩余可采纳发现。按你的要求**没有开 PR**，分支留在 `feat/stock-batch` 上等待验收。
