package inventory

import (
	"encoding/json"
	"os"
	"testing"
)

// eval 探针：**只做观察，不做判断**。它把 LowStockWarehouses 返回的**顺序**打成
// {仓库: 下标}，期望顺序写在 case.json 的 expect 里。
//
// 用固定库存：wuhan 与 xian 数量相同（考并列时的名字序），shanghai 数量更大
// （考数量升序）。按名字排的话 shanghai 会跑到最前，所以这两种排法区分得开。
func TestEvalProbe(t *testing.T) {
	// 回到仓库根再观察。任务只说了配置放在哪，没说进程从哪个目录启动；而 Go 会把测试
	// 二进制的 cwd 设成**包目录**，于是按进程 cwd 解析配置的实现（完全合理）会被误判成
	// 没实现。探针不该带进这个隐含假设。
	if err := os.Chdir(".."); err != nil {
		t.Fatalf("回到仓库根失败：%v", err)
	}
	stock := map[string]int{"wuhan": 2, "xian": 2, "shanghai": 3}
	observed := map[string]int{}
	for index, warehouse := range LowStockWarehouses(stock) {
		observed[warehouse] = index
	}
	raw, err := json.Marshal(observed)
	if err != nil {
		t.Fatalf("序列化观察结果失败：%v", err)
	}
	t.Logf("EVAL_PROBE %s", raw)
}
