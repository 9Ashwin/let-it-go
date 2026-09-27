# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：93.5s
- token：742086
- 步数：30，工具调用：45

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序在 `feat/stock-batch` 上做完，一个 issue 一个 commit，已推送 origin 并停在该分支，未开 PR。

## 提交

| commit | issue |
|---|---|
| `fb9e144` | issue-001 阈值改读 `config/thresholds.json`（含回退） |
| `ff6a3b2` | issue-002 `LowStockWarehouses` 数量升序、同数量按仓库名升序 |
| `a0cce7a` | issue-003 新增 `LowStockReport` |

## 实现要点

- **issue-001**：新增 `config/thresholds.json`（`beijing:3`、`shenzhen:12`）。`loadThresholds` 读文件 → 失败/非 JSON 对象/值非整数一律返回 nil，`LowStockThreshold` 命中配置就用它，否则回退 `DefaultLowStockThreshold`。
  - 候选路径按 `config/thresholds.json`、`../config/thresholds.json` 依次尝试，兼容「从仓库根运行服务」和「从 `inventory/` 运行包测试」两种 cwd；用包级 `thresholdFiles` 变量作为测试接缝。刻意未配置 fixture 测试用到的 `chengdu/wuhan/xian`，原有断言不受影响。
- **issue-002**：`sort.Slice` 先比数量、再比仓库名，签名与严格小于判定不变。
- **issue-003**：直接基于 `LowStockWarehouses(stock)` 的输出拼 `"<仓库>=<数量>"`，保证顺序天然一致。
- 每个 issue 配了独立测试文件（config / order / report 三份），覆盖配置命中与四种回退、排序与并列、报告格式与空输入。`inventory/stock_test.go` 与 seed 逐字节一致（已 `git diff --exit-code` 核对），没有为过门禁改动 fixture 断言。
- 同步更新了 `requirements/01_REQ-stock-batch/README.md` 的交付状态，并在 `requirements/README.md` 顺序表登记该 scope。

## 验证

- `make check`（build + test + vet）最终绿：`exit=0`。
- 本地 `HEAD` 与 `origin/feat/stock-batch` 同一提交 `a0cce7a`，工作区干净，当前仍在 `feat/stock-batch` 分支上。
