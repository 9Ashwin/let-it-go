package pricing

import "testing"

// 冻结的验收基线：任何改动都不许把这条测试改弱。
func TestTotal(t *testing.T) {
	if got := Total(250, 3); got != 750 {
		t.Fatalf("Total(250, 3) = %d，想要 750", got)
	}
}
