# 01-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：796.6s
- token：2916414
- 步数：46，工具调用：53

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成了。按 `loop-it` 的单单元模式（一件定义清楚的小改动，内联做完，不开循环）走完，并按它的流程做了 `/review-it` → `/ship-it`。

## 改了什么

**`inventory/stock.go`**
- `LowStockThreshold` 不再返回常量：读 `inventory/thresholds.json` 里该仓库的配置值，未配置 / 文件不存在 / JSON 解析失败都回退 `DefaultLowStockThreshold`。
- 配置定位不依赖进程工作目录：从 CWD 向上找到最近的 `go.mod` 作为仓库根，再读 `<root>/inventory/thresholds.json`。这样服务从仓库根启动、`go test` 在包目录下运行，都命中同一个文件（`go test` 的 CWD 是包目录，直接按 `inventory/thresholds.json` 会落空）。

**新增 `inventory/thresholds.json`**：`{"shanghai": 20}`。

**新增 `inventory/thresholds_test.go`**（没有往冻结测试里追加）：配置命中、未配置回退、文件缺失回退、解析失败回退。

**`requirements/001-per-warehouse-low-stock-threshold/`**：按仓库约定建作用域并登记，README 里放验收表与证据，`records/2026-09-28-delivery.md` 放交付记录。

## 门禁与验收证据

`make check`（build + test + vet）**退出码 0**，10 个测试全绿（含 4 个冻结测试）。冻结的 `inventory/stock_test.go` 逐字节未动，SHA-256 仍是 `54dfdfa58d35dfdeae13d51e55dfd24024c684ff8cba431492c6ea9944ec8882`。

| 验收条件 | 观测 |
|---|---|
| 配置的仓库返回配置阈值 | `TestConfiguredWarehouseUsesConfiguredThreshold`；另起探针从仓库根运行 → `shanghai=20` |
| 未配置仓库回退默认值 | `TestUnconfiguredWarehouseStillFallsBackToDefault` → `chengdu=5` |
| 文件不存在回退默认值 | `TestMissingThresholdsFileFallsBackToDefault`；从无配置目录运行 → `shanghai=5` |
| 门禁不破 | `make check` 全绿、冻结哈希未变 |

## 评审（`review-it`）

因为我是 diff 作者，评审派了独立子代理（不共享本会话上下文）。第一轮判 `revise`，抓到一个真问题：我最初用了 `["inventory/thresholds.json", "thresholds.json"]` 两个候选路径，导致**自动化测试其实从未读过 spec 指定的 `inventory/thresholds.json`**，而且行为依赖 CWD、任意目录的同名裸文件会静默覆盖。改成 go.mod 定位仓库根后，第二轮评审判 **`accept`**，3 个变异（严格小于、配置命中、仓库根解析）全部被门禁抓住。

## 交付

`gh` 不可用、远端是本地裸库，按 `ship-it` 走**本地模式**：`feat/per-warehouse-low-stock-threshold` 分支上两个 commit（`6940f1e` 实现、`da7a166` 交付记录），`git merge --no-ff` 合入 `main`（合并点 `7dc87f1`），未推送。工作树干净。

## 留档的低优先项（不阻塞）

评审的第二轮还记了几条低优先残留，已写进 scope README 的「未决事项」：`LowStockWarehouses` 对 N 个仓库读 N 次；阈值未校验（`null` → `0`、负数原样采信）；测试硬编码 `20` 依赖已提交的数据文件。都不违反本次验收条件，需要的话我可以单独处理。
