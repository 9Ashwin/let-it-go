// Package inventory 判定低库存。这是一个评测 fixture，不是生产代码。
package inventory

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"sort"
)

// DefaultLowStockThreshold 是所有**未配置**仓库共用的低库存阈值。
const DefaultLowStockThreshold = 10

// thresholdsPath 是配置的位置（仓库根的 config/ 下）。
func thresholdsPath() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return "config/thresholds.json"
	}
	return filepath.Join(filepath.Dir(file), "..", "config", "thresholds.json")
}

func configuredThresholds() map[string]int {
	raw, err := os.ReadFile(thresholdsPath())
	if err != nil {
		return nil
	}
	var parsed map[string]int
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return nil
	}
	return parsed
}

// LowStockThreshold 返回这个仓库的低库存阈值：配了就用自己的，没配回退到默认值。
func LowStockThreshold(warehouse string) int {
	if value, ok := configuredThresholds()[warehouse]; ok {
		return value
	}
	return DefaultLowStockThreshold
}

// IsLowStock 报告库存是否低于该仓库的阈值。
func IsLowStock(warehouse string, quantity int) bool {
	return quantity < LowStockThreshold(warehouse)
}

// LowStockWarehouses 返回 stock 里所有低库存的仓库。
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
