# issue-001: 低库存阈值按仓库可配

**目标**：每个仓库能设自己的低库存阈值；没配的仓库沿用默认值。

**非目标**：不改 `LowStockWarehouses` 的排序语义，不动对外函数签名。

**验收条件**：

- [ ] `LowStockThreshold(warehouse)` 返回该仓库配置的阈值；没配时回退 `DefaultLowStockThreshold`
- [ ] 阈值来源是 `inventory/thresholds.json`，形如 `{"shanghai": 20}`
- [ ] 文件不存在、读不出来、内容不是 JSON 对象时，一律回退默认值
- [ ] `IsLowStock` 保持严格小于（等于阈值不算低库存）
- [ ] `make check` 绿

**阻塞边**：无
