# 05-full-pipeline / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：236.7s
- token：466283
- 步数：16，工具调用：26

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。核心结论：阈值改成**运行期**从 `config/thresholds.json` 读取，未配置的仓库仍走 `DefaultLowStockThreshold`，所以运维改文件即可生效，无需重建或重启。

## 落地方式

**配置格式**（`config/thresholds.json`，扁平映射，只写要覆盖的仓库）：
```json
{
  "shanghai": 3,
  "beijing": 10
}
```
当前提交里是 `{}`（全走默认），格式与语义写在 `config/README.md`。

**代码**（`inventory/stock.go`）：
- `LowStockThreshold` 每次调用都 `os.ReadFile` + `json.Unmarshal` 一次配置，命中键返回值，否则返回 `DefaultLowStockThreshold`。**没有用 `go:embed`**，配置不参与构建，所以改文件即生效。
- `LowStockWarehouses` 每次调用只读一次文件，再逐仓库取阈值，避免每个仓库重复读盘。
- 文件缺失或 JSON 非法时，`loadThresholds` 返回 `nil`，全部回退默认值（不会因配置写错而崩）。
- 配置文件路径默认从 cwd 向上找最近的 `config/thresholds.json`，这样从仓库根启动、或在 `inventory/` 里跑测试都能定位到同一份；另留了一个未导出的 `configPath` 变量作为测试接缝。

## 改了哪些文件
- `inventory/stock.go` — 实现上述逻辑（原有函数签名与 `DefaultLowStockThreshold` 不变）。
- `config/thresholds.json` — 新增，空的覆盖表。
- `config/README.md` — 补 `thresholds.json` 的格式与「改完即生效」说明。
- `inventory/thresholds_test.go` — 新增测试：按仓库覆盖、未配置回退、改文件后下一次调用即读到新值、非法/缺失配置回退、路径定位。
- `requirements/001-per-warehouse-thresholds/README.md` + `requirements/README.md` 登记 — 按仓库的 `requirements/<scope>/` 约定落了一条需求。

## 验证
- `make check`（build + test + vet）绿。
- `inventory/stock_test.go` 的 blob hash 与 HEAD 逐字节一致（`bc604456…`），没有动既有验收基线。
- 端到端验证了「不重建」：构建一个探针二进制 → 配置 `shanghai=3` 跑一次 → 只改文件为 `shanghai=9` → **同一个二进制**再跑，阈值从 3 变 9；未配置的 `chengdu` 始终是默认 5。

## 一个假设（已记在需求里）
配置采用扁平的 `{"<warehouse>": <int>}`，默认值不进配置文件、仍由代码常量兜底——因为你说的是「没配的仓库走原来的默认值」。如果你更希望文件里能显式写默认值或带版本字段，告诉我，我改成带外层结构的版本。

改动都在工作区，没有提交（你没要求）。
