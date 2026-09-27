# 08-undeclared-workspace / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：399.9s
- token：2178810
- 步数：32，工具调用：53

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 let-it-go 流程走完：`prd`（入口）→ `to-issues` → `loop-it` 单单元内联 → `review-it` → `ship-it`。

## 选技能的依据

你这个请求是「一句诉求 + 落地方案你定」，正好命中 `prd` 的触发说明（“需求还没成形，先在这里把决策定清楚再实现”）；`loop-it` 的入口门也写着同样的路由。`to-issues` 有规模下限规则——一个上下文窗口装得下就直接内联——这个改动确实装得下，所以没造 issue 卡。

## 落地方式（关键决策）

- 配置 `config/thresholds.json`，格式 `{ "仓库名": 阈值 }`，例如 `{"wuhan": 10, "xian": 3}`；**初始提交空对象 `{}`，部署上去零行为变化**。
- `LowStockThreshold` **每次调用都重新读盘**（`inventory/thresholds.go`）——这是「改文件立即生效」最简的实现：无构建、无重启、无缓存失效逻辑。`LowStockWarehouses` 收敛为一次调用只读一次，避免 N 次 I/O。
- 没配的仓库回退 `DefaultLowStockThreshold`（5）；文件缺失 / JSON 非法 / 路径不可读都整份回退默认值，不 panic。公开签名没动。
- 运维改完文件下一次判定即生效；格式和边界行为写在 `config/README.md`。

## 证据

- `make check` 绿（build + test + vet）。
- 12 条测试全过：新增 8 条，覆盖配置生效、未配置回退、缺文件/非法 JSON 回退、**同进程改文件 10→3 立即生效**、批量按各自阈值、端到端。
- 冻结的 `inventory/stock_test.go` 与 seed commit `6e6aaba` 逐字节一致。

## 评审

按 `review-it` 要求，作者不审自己 → 派了两个**未参与实现的全新子代理**独立评审。两轮 Spec / Standards 两轴均 `accept`、0 blocker。接受并修了：删掉无效的 `filepath.FromSlash`、补批量路径的回退测试、README 补 `null`/负数/非整数的真实后果（`null` 会被当成 `0`，已实测确认）。拒绝的：静默降级与每调用读盘是 PRD 显式决策/非目标，`stock_test.go` 是冻结文件不能改。

## 交付

`gh` 未安装 → `ship-it` 判定本地模式：分支 `feat/warehouse-thresholds`，commit `a9ca6b4`，已 `--no-ff` 合入 `main`（合并点 `4702661`）。**没有推送**，分支留档未删。

需求资料：`tasks/warehouse-thresholds/documents/prd-warehouse-thresholds.md`、`tasks/warehouse-thresholds/notes/walkthrough-warehouse-thresholds.md`（走查件 + 交付总结）。

## 要你拍板的三点

1. 配置写坏时目前是**静默回退默认值**（受冻结签名 `LowStockThreshold(string) int` 限制，无法返回 error），要不要加日志/告警？
2. `null` 会被当作 `0`（永不告警）、负数和 `0` 原样接受——要不要改成校验并拒绝？
3. 条目变多后是否需要 mtime 缓存？现在是每次判定读盘。
