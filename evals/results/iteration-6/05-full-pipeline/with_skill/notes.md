# 05-full-pipeline / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：221.7s
- token：2432199
- 步数：41，工具调用：53

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `let-it-go` 的流水线走完：**`prd` → `to-issues` → `loop-it`（单单元模式）→ `review-it` → `walkthrough` → `ship-it`**。

## 怎么落地的

需求只有一处行为变化：阈值来源从写死常量改成按仓库读配置。

- **`inventory/thresholds.go`（新增）**：读仓库根的 `config/thresholds.json`（扁平 JSON：`{"shanghai": 20}`）。因为 `go test` 运行 `inventory` 包时工作目录是 `inventory/`，而配置在仓库根，所以**从工作目录向上查找** `config/thresholds.json`——从仓库根启动和从子目录启动都能定位到同一份。
- **`inventory/stock.go`**：`LowStockThreshold(warehouse)` 改为每次调用都重新读盘再查表。没配的仓库、文件缺失或内容不可解析，一律回退 `DefaultLowStockThreshold`（仍是 5）。函数签名和 `IsLowStock` 的严格小于语义都没动。
- **`config/thresholds.json`（新增）**：`{"shanghai": 20}`。
- **"改配置不重新构建"**：运行期 `os.ReadFile` + 无进程内缓存 + 无 `go:embed`，运维改文件下次判定即生效。

按仓库约定产出了需求资料：`requirements/01_REQ-per-warehouse-thresholds/`（README、`documents/prd-*.md`、`issues/issue-001-*.md`、`notes/walkthrough-*.md`、`records/2026-09-27-delivery.md`），并登记了 root `requirements/README.md`。

## 证据

- 复现 eval 探针三场景，输出全部符合期望：
  - `{"shanghai":20}` → shanghai=20 / beijing=5 / chengdu=5
  - `{"shanghai":20,"beijing":3}` → 20 / 3 / 5
  - 文件删除 → 全部 5
- `make check` exit 0；`go test -count=1 -v ./inventory/` 全绿（含新增的"同进程改文件即生效"与配置缺失/损坏回退测试）。
- 受保护文件 `Makefile`、`inventory/stock_test.go` 的 sha256 与 seed 逐字节一致。

## 评审

- **Spec 轴**：干净，逐条对齐 issue-001 验收条件。
- **Standards 轴**：采纳并修复 1 条——补了 `IsLowStock` 在非默认配置阈值下的严格小于断言；另有 1 条 `<低>`（每次判定读盘）系"即时生效"的有意取舍，未改。

## 交付状态（需要你知道的两点）

1. **推送被沙箱拦下**：`origin` 裸仓库在 fixture 之外，当前 workspace-write 不允许写出去。所以我在本地把 `feat/issue-001-per-warehouse-thresholds`（commit `7fdb389`）以 `--no-ff` 合进了 `main`（`a9c6b6a`），工作树干净。
2. **`gh` 未安装**，无法开 PR / 在 issue 上评论。`ship-it` 的四类总结（设计决策 / 偏离 / 权衡 / 待确认）已落到 `records/2026-09-27-delivery.md`，PR body 目前不在仓库里。等 `gh` 可用或网络放开，我可以补推分支、开 PR。

一处假设已在 PRD 标注：配置写坏时静默回退默认值（函数签名不返回 error），是否需要显式告警留待你确认。
