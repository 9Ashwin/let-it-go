package report

import "fmt"

// SKULine 是报表里最基础的一行：SKU 与数量。
func SKULine(sku string, qty int) string {
	return fmt.Sprintf("%s x%d", sku, qty)
}
