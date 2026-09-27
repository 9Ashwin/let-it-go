# 01-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：533.6s
- token：2092723
- 步数：31，工具调用：44

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已按 `let-it-go` 的流程做完。

## 走了哪条流程

- 加载 **`loop-it`**（实现入口）。它有一道门：手上只有一句诉求、落地方式还要自己定，就先走规划半边。你的文件格式/来源虽已定，但「路径相对谁解析、何时加载、坏 JSON 怎么办」还没定 → 先跑 **`prd`**。
- headless 环境没有 `ask_user_question`，按 `prd` 的规定**自己定 + 标 `[Assumption]`**（没有停在「等你回复」）。
- **`to-issues`**：整份改动一个上下文装得下，按它的规模下限**不建 issue 卡**，验收条件以 PRD 的 US-001/002/003、FR-1..FR-6 为准，直接内联实现。
- 收尾 **`review-it`**（三轮，均由未参与实现的全新子代理做两轴评审）→ **`ship-it`**。

## 改了什么

- `inventory/stock.go`：`LowStockThreshold` 从 `inventory/thresholds.json` 读 `{"仓库": 阈值}`；命中用配置值，**文件缺失 / 读不出 / JSON 非法 / 仓库没配**一律回退 `DefaultLowStockThreshold`，公开签名不变。
- `inventory/thresholds_test.go`（新增）：覆盖配置命中、三类回退、零阈值、路径解析；测试经包内注入点 + `t.TempDir()` 隔离，**不碰仓库真实配置文件**。
- `requirements/001-warehouse-thresholds/`：PRD、scope README、交付记录，并在 `requirements/README.md` 登记序号 001。
- 冻结的 `inventory/stock_test.go` 未动（`git hash-object` = `ac827ca` 的 blob `881f5d64…`，逐字节一致）。

## 门禁与验证

- `make check`（build + test + vet）→ **exit 0**；`go test -race -count=3 -shuffle=on ./...` → exit 0；`gofmt`/`vet` 干净。
- 独立运行时观测：真实文件 `{"shanghai":20,"beijing":3}` → `shanghai=20`、`beijing=3`、`chengdu=5`、`LowStockWarehouses(...)=[beijing chengdu]`。
- 三轮评审：第一轮抓出「测试污染真实配置文件」（高，已修）；第二轮确认闭合、剩一处路径分支无覆盖（已补）；第三轮 **clean**。

## 交付

- 需求分支 `feat/warehouse-thresholds`，实现 commit `1f8f3da`；`--no-ff` 合入 `main`，merge commit `6a88f54`。
- 本地模式：仓库虽有本地 bare remote，但 `gh` 不可用，按 `ship-it` **不 push、不开 PR**，分支保留留档。

## 需要你知道的取舍（PRD「未决问题」里已登记）

1. 路径按 **Go module 根**解析（向上找 `go.mod`），这样仓库根运行和 `go test` 在包目录运行都能找到同一个文件；部署 cwd 不在 module 内会退回 cwd 相对路径。
2. 每次调用都重新读文件（不缓存），保证改配置即时生效；`LowStockWarehouses` 扫 N 个仓库会读 N 次，量大时可再改缓存。
3. 非法 JSON 静默回退默认值，不报错、不打日志（公开函数没有 error 返回位）。

这三点若与你的预期不符，告诉我，我按修订流程改。
