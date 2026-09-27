package inventory

import (
	"encoding/json"
	"os"
	"testing"
)

// eval 探针：**只做观察，不做判断**。它把三个仓库实际生效的阈值打出来，
// 期望值写在 case.json 里，由 harness 比对。
//
// 由 harness 复制成 inventory/zz_eval_probe_test.go 后 `go test -run TestEvalProbe -v` 运行，
// 每个场景一个新进程，所以实现里有没有缓存都不影响结果。
func TestEvalProbe(t *testing.T) {
	// 回到仓库根再观察。任务只说「配置放 config/thresholds.json」，没说进程从哪个目录启动；
	// 而 Go 会把测试二进制的 cwd 设成**包目录**，于是按进程 cwd 解析配置的实现
	// （「假设工作目录在仓库根」，完全合理）会被误判成没实现。探针不该带进这个隐含假设。
	if err := os.Chdir(".."); err != nil {
		t.Fatalf("回到仓库根失败：%v", err)
	}

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
