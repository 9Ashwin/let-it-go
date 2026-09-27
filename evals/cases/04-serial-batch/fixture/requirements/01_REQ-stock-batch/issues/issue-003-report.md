# issue-003: 低库存报告

**目标**：新增 `LowStockReport(stock map[string]int) []string`，返回 `"<仓库>=<数量>"` 组成的列表，**顺序与 `LowStockWarehouses` 一致**。

**非目标**：不改 `LowStockWarehouses` 本身。

**验收条件**：

- [ ] 每条是 `<仓库>=<数量>`
- [ ] 顺序与 `LowStockWarehouses` 一致
- [ ] `make check` 绿

**阻塞边**：issue-002
