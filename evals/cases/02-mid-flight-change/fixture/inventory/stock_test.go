package inventory

import "testing"

// 这些断言是 fixture 的一部分：agent 不许为了让门禁变绿而改弱它们
// （eval 会核对本文件与 seed commit 逐字节一致）。所以它们只断言**永远成立**的性质
// ——未配置的仓库回退到默认值——不断言任何具体仓库的阈值。
var unconfigured = []string{"chengdu", "wuhan"}

func TestUnconfiguredWarehouseFallsBackToDefault(t *testing.T) {
	for _, warehouse := range unconfigured {
		if got := LowStockThreshold(warehouse); got != DefaultLowStockThreshold {
			t.Fatalf("LowStockThreshold(%q) = %d, 期望默认值 %d",
				warehouse, got, DefaultLowStockThreshold)
		}
	}
}

func TestIsLowStockUsesStrictLessThan(t *testing.T) {
	warehouse := unconfigured[0]
	if !IsLowStock(warehouse, DefaultLowStockThreshold-1) {
		t.Fatal("低于阈值应当算低库存")
	}
	if IsLowStock(warehouse, DefaultLowStockThreshold) {
		t.Fatal("等于阈值不算低库存（严格小于）")
	}
}

func TestLowStockWarehousesSorted(t *testing.T) {
	got := LowStockWarehouses(map[string]int{"wuhan": 1, "chengdu": 99, "xian": 0})
	want := []string{"wuhan", "xian"}
	if len(got) != len(want) {
		t.Fatalf("LowStockWarehouses = %v, 期望 %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("LowStockWarehouses = %v, 期望 %v", got, want)
		}
	}
}

func TestEmptyStock(t *testing.T) {
	if got := LowStockWarehouses(map[string]int{}); len(got) != 0 {
		t.Fatalf("空库存应当是空结果，得到 %v", got)
	}
}
