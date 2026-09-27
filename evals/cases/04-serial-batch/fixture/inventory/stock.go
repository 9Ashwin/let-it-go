// Package inventory 判定低库存。这是一个评测 fixture，不是生产代码。
package inventory

import "sort"

// DefaultLowStockThreshold 是所有**未配置**仓库共用的低库存阈值。
const DefaultLowStockThreshold = 5

// LowStockThreshold 返回这个仓库的低库存阈值。
//
// 现在不看 warehouse——所有仓库共用 DefaultLowStockThreshold。
func LowStockThreshold(warehouse string) int {
	return DefaultLowStockThreshold
}

// IsLowStock 报告库存是否低于该仓库的阈值。
func IsLowStock(warehouse string, quantity int) bool {
	return quantity < LowStockThreshold(warehouse)
}

// LowStockWarehouses 返回 stock 里所有低库存的仓库，按名字排序。
func LowStockWarehouses(stock map[string]int) []string {
	low := make([]string, 0, len(stock))
	for warehouse, quantity := range stock {
		if IsLowStock(warehouse, quantity) {
			low = append(low, warehouse)
		}
	}
	sort.Strings(low)
	return low
}
