package inventory

import "testing"

// 冻结的验收基线：任何改动都不许把这条测试改弱。
func TestStock(t *testing.T) {
	items := []Item{{SKU: "a", Qty: 3}, {SKU: "b", Qty: 0}}
	if got := Stock(items, "a"); got != 3 {
		t.Fatalf("Stock(a) = %d，想要 3", got)
	}
	if got := Stock(items, "zz"); got != 0 {
		t.Fatalf("Stock(zz) = %d，想要 0", got)
	}
}
