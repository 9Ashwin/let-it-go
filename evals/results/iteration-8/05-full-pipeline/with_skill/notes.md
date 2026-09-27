# 05-full-pipeline / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：474.7s
- token：5371732
- 步数：64，工具调用：97

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `let-it-go` 的入口技能 `prd` 进场，走完了 **`prd → to-issues → loop-it → review-it`** 整条流水线。

## 落地方式（你说“怎么落地你定”，决策都记进了 PRD 的 [Assumption]）

| 决策 | 选择 |
|---|---|
| 配置格式 | 扁平 JSON `{"<仓库>": <整数阈值>}`，放 `config/thresholds.json`（随仓库附空 `{}`，不替业务预设值） |
| 生效方式 | **每次判定重新读盘**——无进程内缓存、无 `go:embed`。运维改文件即生效，不重建、不重启 |
| 回退 | 未配该仓库 / 文件缺失 / 内容非法 → `DefaultLowStockThreshold`(5)；显式 `0` 是合法值，仍生效 |
| 定位配置 | 从进程 cwd 向上找 `go.mod` 定位仓库根，兼容从仓库根或 `inventory/` 运行（`go test` 会把 cwd 设成包目录） |
| 兼容性 | `LowStockThreshold` / `IsLowStock` / `LowStockWarehouses` 签名与语义不变（仍是严格小于） |

## 证据

- `make check` → **退出码 0**（build + test + vet）。
- 新增 `inventory/thresholds_test.go` 全绿：配置命中、未配置回退、配置缺失、非法内容（`not json`/数组/数字/`null`/`{"shanghai":null}`）、显式 0、**同进程改写文件即生效**、仓库根与包目录两种 cwd、配置阈值下的严格小于。
- 真实运行态 demo（同一进程内编辑真实配置文件，未重建/未重启）：
  `before shanghai=5 → 写 {"shanghai":20} → 20 → 再写 {"shanghai":20,"beijing":3} → beijing=3 → 清空 {} → 回到 5`，未配置的 `chengdu` 始终 5。
- 基线红过：实现前同一批测试 4 条失败，改完才转绿。
- 受保护文件 `Makefile`、`inventory/stock_test.go` **逐字节未改**。

## 评审（`review-it` 两轴，独立上下文子代理）

- **Spec 轴**：要求了什么就做了什么——无缺失、无多出、无写错。
- **Standards 轴**：3 条 low 已修（JSON `null` 曾被当成阈值 0、缺“cwd=仓库根”的定位测试、缺显式 0 与 null 的不变式用例）；两轮复检后 **clean**。

## 落盘产物

```
requirements/01_REQ-per-warehouse-thresholds/
├── README.md                范围 / 状态 / 关键决定
├── documents/prd-per-warehouse-thresholds.md
├── issues/issue-001-per-warehouse-thresholds.md
└── records/2026-09-27-delivery.md
config/thresholds.json       新增配置
config/README.md             记录 thresholds.json 格式
inventory/thresholds.go      新增：运行期读配置
inventory/stock.go           LowStockThreshold 改为配置优先
inventory/thresholds_test.go 新增测试
requirements/README.md       登记 scope 01
```

改动都在工作树里，**尚未提交**（`origin` 是本地 bare 仓库，没有可开 PR 的 GitHub remote）。你确认后我可以 `/ship-it` 做本地提交/合入；或者直接说一声我来提交。
