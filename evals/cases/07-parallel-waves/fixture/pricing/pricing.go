package pricing

// Total 返回一批货的金额（单位：分）。
func Total(cents, qty int) int {
	return cents * qty
}
