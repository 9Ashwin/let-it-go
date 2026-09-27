# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：628.5s
- token：4372071
- 步数：58，工具调用：96

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。三条 issue 已按依赖顺序做完，全部落在需求分支 `feat/stock-batch` 上并已推送到 origin，当前就停在它上面；`make check` 最终一遍绿。

## 交付分支

```
feat/stock-batch  →  origin/feat/stock-batch  (e39b520, 已 tracking, 未开 PR)
工作树干净；本地 HEAD == origin HEAD
```

| commit | 内容 |
|---|---|
| `c55867d` | issue-001 阈值来源改成 `config/thresholds.json` |
| `e61e1e7` | issue-002 低库存列表按数量升序、同数量按名字升序 |
| `f06f8cc` | issue-003 新增 `LowStockReport`，顺序复用 `LowStockWarehouses` |
| `51e7fa5` | 评审补充：配置不可读（目录）/ 顶层 `null` 的回退用例 |
| `e39b520` | 走查件 + scope README 交付状态 + 检查点终态 |

## 逐条验收（证据）

- **issue-001**：配了用自己的值（`shanghai=10`）、没配回退（`chengdu=5`）、文件缺失/不可读/非对象/坏 JSON/顶层 `null` 全部回退；`IsLowStock` 仍是严格小于。配置路径以「cwd 向上找到的模块根」为基准，`go test` 在 `inventory/` 下也能读到仓库根配置。新增 `inventory/config_source_test.go`，冻结的 `inventory/stock_test.go` 逐字节未动。
- **issue-002**：`(数量, 仓库名)` 全序，`-count=20` 复跑与连续 `go run` 输出恒为 `[beijing wuhan xian nanjing]`，排除 map 迭代随机性；签名与判定规则未改。
- **issue-003**：`"<仓库>=<数量>"` 且直接委托 `LowStockWarehouses`，顺序由构造保证；`LowStockWarehouses` 本身未改。
- **门禁**：`make check`（build + test + vet）退出码 0，`go test ./... -race` 也绿。

## 流程（loop-it 串行批次，按你的分支约定调整）

- 用 `loop_state.py scan` 建依赖图（#1→#2→#3）与检查点 `requirements/01_REQ-stock-batch/issues/.loop-state.json`（随需求资料版本化，已入库）。
- 每个 issue：内联实现 → `make check` 自证 → 记结构化 evidence/notes → **另一个上下文的 supervisor 独立复核**（三条均 `accept`）→ commit。
- 批末：follow-up 收口（0 条）→ `review-it` 两轴评审整合 diff（Spec/Standards 分开报，`accept`）→ 走查件 `notes/walkthrough-stock batch.md`。
- 与技能默认不同处（按你的指令）：单条需求分支、一个 issue 一个 commit、**不开 PR**、只 push 并留在分支上。

## 评审中主动拒绝的项（有意为之）

- **O(N) 配置读**：一次性读会迫使把严格小于规则复制进循环，破坏「判定规则单一来源」这一更强不变量；此 fixture 上收益是推测性的。
- **`thresholdConfigPath` 命名**：`var x = resolveX` 是 Go 常见测试接缝写法（类 `var now = time.Now`）。
- **`.loop-state.json` 入库**：本仓库约定作用域内布局由需求流程决定，该检查点即流程的版本化记录。

一条评审指出的**注释事实错误已修**：原写「与进程当前目录无关」不准确——解析起点正是 cwd；已改为「以 cwd 向上找到的模块根为基准」，并用「从 `/tmp` 运行则回退 `shanghai=5`」反例验证。

未做人工验收，如实记在走查件里。
