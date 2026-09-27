package inventory

import (
	"encoding/json"
	"os"
	"testing"
)

// eval 探针：**只做观察，不做判断**。三件事：
//
//	t_shanghai  配置里的阈值真的生效了吗
//	eq_low      库存**正好等于**阈值时算不算低库存（严格小于 → 0；含等于 → 1）
//	below_low   低于阈值时算不算（必须 1）
//
// 由 harness 复制成 inventory/zz_eval_probe_test.go 后 `go test -run TestEvalProbe -v` 运行。
func TestEvalProbe(t *testing.T) {
	// 回到仓库根再观察：Go 把测试二进制的 cwd 设成包目录，按进程 cwd 解析配置的
	// 实现会被误判成没实现。探针不该带进这个隐含假设。
	if err := os.Chdir(".."); err != nil {
		t.Fatalf("回到仓库根失败：%v", err)
	}

	threshold := LowStockThreshold("shanghai")
	eq, below := 0, 0
	if IsLowStock("shanghai", threshold) {
		eq = 1
	}
	if IsLowStock("shanghai", threshold-1) {
		below = 1
	}
	observed := map[string]int{
		"t_shanghai": threshold,
		"eq_low":     eq,
		"below_low":  below,
	}
	raw, err := json.Marshal(observed)
	if err != nil {
		t.Fatalf("序列化观察结果失败：%v", err)
	}
	t.Logf("EVAL_PROBE %s", raw)
}
