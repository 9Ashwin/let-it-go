# 05-full-pipeline / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：502.1s
- token：2249927
- 步数：36，工具调用：57

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 let-it-go 的流程走完：`prd`（需求成形）→ `to-issues`（拆卡）→ `loop-it`（单单元内联实现）→ `review-it`（两轴评审 + 两轮复核）。

## 落地方案（你给的约束都满足）

- **配置位置**：新增 `config/thresholds.json`，扁平映射「仓库名 → 整数阈值」：
  ```json
  { "beijing": 10, "shanghai": 20, "guangzhou": 8 }
  ```
- **免重建**：阈值在**运行期**用 `os.ReadFile` 读取，不用 `//go:embed`、无代码生成。而且不是只做到"读一次"——每次判定都重读，所以运维**直接改文件就立即生效，连重启都不需要**。
- **未配置回退**：配置里没有的仓库、文件缺失或内容坏掉，一律回退 `DefaultLowStockThreshold = 5`，不会 panic。
- 既有导出函数签名不变，冻结的 `inventory/stock_test.go` **逐字节未动**。

关键实现都在 `inventory/stock.go`（新增 `loadThresholds`，`LowStockWarehouses` 每次调用只读一次配置）。

## 验证证据

- `make check`（build + test + vet）**退出码 0**；`go test -race` 也干净。
- 运行时演示：**build 一次**后从仓库根跑同一个二进制 —— 改配置前 `beijing=10`，把文件改成 `1` 后**同一二进制**立刻输出 `beijing=1`，还原后又是 `10`；未配置的 `wuhan`/`chengdu` 恒为 `5`。这直接证明了"改文件即生效、免重建"。
- 新增 `inventory/thresholds_test.go`：配置命中/未配置回退/缺失/坏值/空对象/负阈值/热更新/端到端共 12 个测试全绿。

## 评审抓到并修掉的一个隐患

第一轮对抗性评审发现：JSON `null` 被 `encoding/json` 解成 int `0` 且**不报错**，会让 `{"beijing": null}` 变成阈值 0——该仓库**永不告警**，比崩溃更危险。已改为按值严格校验（`json.RawMessage` + `*int`），`null`/`2.5`/`"9"`/`true`/`1e1`/溢出都整体回退默认，并补了回归锁。第二、三轮复核干净。

## 需求资料

- PRD：`requirements/001-warehouse-thresholds/documents/prd-per-warehouse-thresholds.md`
- issue 卡：`requirements/001-warehouse-thresholds/issues/issue-00{1,2}-*.md`
- 交付记录：`requirements/001-warehouse-thresholds/records/2026-09-27-delivery.md`
- ops 说明：`config/README.md`

## 需要你定的两件事

1. `config/thresholds.json` 里的示例仓库/阈值只是占位，正式值按业务填。
2. 改动目前**留在工作树，未 commit / 未 push**——你没要求交付动作，我就没动。要提交/开 PR 的话说一声，我走 `ship-it`。
