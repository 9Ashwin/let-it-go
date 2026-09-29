# 03-artifact-handoff / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：66.3s
- token：164935
- 步数：11，工具调用：21

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。这个 scope 里唯一未交付的是 **issue-002：`LowStockWarehouses` 的返回顺序**，其余（阈值读取、回退、严格小于）在 issue-001 已完成，无需改动。

需求本身没有歧义（数量升序、同数量按仓库名升序、不改签名、不改判定），所以没有需要问你的地方。

## 改动

**`inventory/stock.go`** — 重写 `LowStockWarehouses` 的排序：先按数量升序，数量相同时按仓库名升序。函数签名与判定逻辑（`IsLowStock`）不变。为拿到数量，遍历时把 `(warehouse, quantity)` 一起收集后再排序，最后抽出名字。

**`inventory/low_stock_order_test.go`（新建）** — 按仓库约定，新行为写进新测试文件，不动既有测试。用 `{"chengdu":3, "wuhan":1, "xian":1}` 断言精确顺序 `[wuhan, xian, chengdu]`：既覆盖数量升序（chengdu 数量最大、名字字母序最小，仍排最后），也覆盖同数量按名字升序（wuhan < xian）。三个仓库都未配置，回退默认阈值，均属低库存。

**需求资料同步** — `issues/issue-002` 三条验收勾选为完成；scope `README.md` 把该项从「未交付」移到「已交付」，未交付记为无。

## 验证

- `make check`（build + test + vet）绿，改动前后各跑一遍。
- `git diff inventory/stock_test.go` 为空——冻结的验收基线逐字节未动。
- 未新增依赖，`sort` 仍在使用；只改了本仓库内文件。

改动清单：`inventory/stock.go`、`inventory/low_stock_order_test.go`（新）、两份需求文档。尚未提交，需要我提交的话说一声。
