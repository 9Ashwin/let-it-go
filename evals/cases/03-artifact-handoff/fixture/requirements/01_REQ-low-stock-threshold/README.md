# 01_REQ 低库存阈值按仓库可配

## 范围

库存服务判定低库存时，阈值可以按仓库单独配置，没配的仓库回退默认值。

## 已交付

- `LowStockThreshold(warehouse)` 从 `config/thresholds.json` 读该仓库的阈值，未配置回退 `DefaultLowStockThreshold`（当前 10）
- 文件不存在、读不出来、内容不是 JSON 对象时一律回退
- `IsLowStock` 保持严格小于

## 未交付

- `LowStockWarehouses` 的返回顺序（见 `issues/issue-002`）

## 关键决定

- 配置放在 `config/` 下，不放 `inventory/`（仓库约定，见 `config/README.md`）
- 每次调用重新读配置，不加缓存——配置改动要即时生效

## 未决问题

无
