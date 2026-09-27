# issue-002: 判定改成含等于

**目标**：`IsLowStock` 从「严格小于」改成「**小于等于**」——库存正好等于阈值也算低库存。

**非目标**：不改 `LowStockThreshold` 的取值来源。

**验收条件**：

- [ ] `IsLowStock(w, LowStockThreshold(w))` 返回 true
- [ ] `IsLowStock(w, LowStockThreshold(w)-1)` 返回 true
- [ ] `make check` 绿

**阻塞边**：issue-001
