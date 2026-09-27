package inventory

// Item 是库存里的一条记录。
type Item struct {
	SKU string
	Qty int
}

// Stock 返回某个 SKU 的数量；没有这个 SKU 时返回 0。
func Stock(items []Item, sku string) int {
	for _, it := range items {
		if it.SKU == sku {
			return it.Qty
		}
	}
	return 0
}
