package report

import (
	"encoding/json"
	"testing"

	"example.com/shop/inventory"
	"example.com/shop/pricing"
)

// eval 探针：**只做观察，不做判断**。它把三个单元的行为压成一张数字表，
// 期望值写在 case.json 的 expect 里——数字表是为了让断言器只做数值比对。
//
// 断言器只比数值，所以字符串事实一律编码成 0/1（`reorder_first_is_d` 这种）。
//
//	reorder_n           Reorder 返回几条
//	reorder_first_is_d  第一条是不是 d（数量 1，最少）
//	reorder_second_is_a 第二条是不是 a（数量 2，同数量里 SKU 靠前）
//	bulk                BulkTotal(250, 3, 10)：750 减 10% = 675
//	lines_n             LowStockLines 返回几行
//	lines_first_is_d_x1_45  首行是不是 "d x1 = 45"（50 减 10% = 45）
func TestEvalProbe(t *testing.T) {
	items := []inventory.Item{
		{SKU: "b", Qty: 2},
		{SKU: "a", Qty: 2},
		{SKU: "c", Qty: 9},
		{SKU: "d", Qty: 1},
	}
	units := map[string]int{"a": 250, "b": 100, "c": 400, "d": 50}

	observed := map[string]int{}
	reorder := inventory.Reorder(items)
	observed["reorder_n"] = len(reorder)
	if len(reorder) > 0 && reorder[0].SKU == "d" {
		observed["reorder_first_is_d"] = 1
	}
	if len(reorder) > 1 && reorder[1].SKU == "a" {
		observed["reorder_second_is_a"] = 1
	}

	observed["bulk"] = pricing.BulkTotal(250, 3, 10)

	lines := LowStockLines(items, units, 10)
	observed["lines_n"] = len(lines)
	if len(lines) > 0 && lines[0] == "d x1 = 45" {
		observed["lines_first_is_d_x1_45"] = 1
	}

	out, err := json.Marshal(observed)
	if err != nil {
		t.Fatalf("观察结果序列化失败：%v", err)
	}
	t.Logf("EVAL_PROBE %s", out)
}
