package inventory

import (
	"encoding/json"
	"testing"
)

// eval 探针：**只做观察，不做判断**。它把三条 issue 的行为压成一张数字表，
// 期望值写在 case.json 的 expect 里——数字表是为了让断言器只做数值比对。
//
//	t_<仓库>  LowStockThreshold 的取值
//	o_<仓库>  该仓库在 LowStockWarehouses 结果里的下标（考顺序）
//	r_len     报告条数；r_first_is_wuhan 报告首条是不是数量最少且名字最靠前的那个
func TestEvalProbe(t *testing.T) {
	observed := map[string]int{}
	observed["t_shanghai"] = LowStockThreshold("shanghai")
	observed["t_beijing"] = LowStockThreshold("beijing")

	stock := map[string]int{"wuhan": 2, "xian": 2, "shanghai": 3}
	for index, warehouse := range LowStockWarehouses(stock) {
		observed["o_"+warehouse] = index
	}

	report := LowStockReport(stock)
	observed["r_len"] = len(report)
	if len(report) > 0 && report[0] == "wuhan=2" {
		observed["r_first_is_wuhan"] = 1
	} else {
		observed["r_first_is_wuhan"] = 0
	}

	raw, err := json.Marshal(observed)
	if err != nil {
		t.Fatalf("序列化观察结果失败：%v", err)
	}
	t.Logf("EVAL_PROBE %s", raw)
}
