package greeter

import (
	"encoding/json"
	"fmt"
	"testing"
)

// TestEvalProbe 只观察，不判断：把实际生效的值打印成 JSON，期望值写在 case.json 里。
func TestEvalProbe(t *testing.T) {
	observed := map[string]int{
		"slug_hello_world": boolToInt(Slug("Hello World") == "hello-world"),
		"slug_trim":        boolToInt(Slug("  Hello World  ") == "hello-world"),
		"slug_collapse":    boolToInt(Slug("a   b") == "a-b"),
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
