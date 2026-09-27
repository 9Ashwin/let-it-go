# issue-001: 阈值来源改成配置文件

**目标**：`LowStockThreshold(warehouse)` 从 `config/thresholds.json` 读该仓库的阈值。

**非目标**：不改判定规则（`IsLowStock` 保持严格小于）。

**验收条件**：

- [ ] 配了就用自己的阈值，没配回退 `DefaultLowStockThreshold`
- [ ] 文件不存在、读不出来、内容不是 JSON 对象时一律回退
- [ ] `make check` 绿

**阻塞边**：无
