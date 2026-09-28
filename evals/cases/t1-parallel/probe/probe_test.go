package greeter

import (
	"encoding/json"
	"fmt"
	"testing"

	"example.com/twounits/counter"
)

// TestEvalProbe 只观察，不判断：把实际生效的值打印成 JSON，期望值写在 case.json 里。
//
// 两个单元分在两个包里，探针放在其中一个、import 另一个——一个命令就能同时观测两边的行为。
func TestEvalProbe(t *testing.T) {
	observed := map[string]int{
		"upper_ok": boolToInt(Upper("ada") == "ADA" && Upper("") == ""),
		"max_ok":   boolToInt(counter.Max([]int{3, 9, 4}) == 9 && counter.Max(nil) == 0),
	}
	raw, _ := json.Marshal(observed)
	fmt.Printf("EVAL_PROBE %s\n", raw)
}

func boolToInt(ok bool) int {
	if ok {
		return 1
	}
	return 0
}
