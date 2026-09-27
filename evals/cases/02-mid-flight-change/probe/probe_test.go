package inventory

import (
	"encoding/json"
	"testing"
)

// eval 探针：**只做观察，不做判断**。它把三个仓库实际生效的阈值打出来，
// 期望值写在 case.json 里，由 harness 比对。
//
// 由 harness 复制成 inventory/zz_eval_probe_test.go 后 `go test -run TestEvalProbe -v` 运行，
// 每个场景一个新进程，所以实现里有没有缓存都不影响结果。
func TestEvalProbe(t *testing.T) {
	observed := map[string]int{}
	for _, warehouse := range []string{"shanghai", "beijing", "chengdu"} {
		observed[warehouse] = LowStockThreshold(warehouse)
	}
	raw, err := json.Marshal(observed)
	if err != nil {
		t.Fatalf("序列化观察结果失败：%v", err)
	}
	t.Logf("EVAL_PROBE %s", raw)
}
