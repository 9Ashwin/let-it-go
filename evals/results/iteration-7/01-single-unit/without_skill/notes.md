# 01-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：79.6s
- token：271000
- 步数：13，工具调用：18

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。只改了 `inventory/stock.go` 一个文件。

## 改了什么

`LowStockThreshold(warehouse)` 现在先查配置，查不到才回退：

```go
func LowStockThreshold(warehouse string) int {
	if threshold, ok := loadThresholds()[warehouse]; ok {
		return threshold
	}
	return DefaultLowStockThreshold
}
```

`IsLowStock` / `LowStockWarehouses` 签名和行为不变，仍走 `LowStockThreshold`，所以配置对它们自动生效。

配置加载（`loadThresholds`）的规则：
- 从 `inventory/thresholds.json` 读，JSON 形如 `{"shanghai": 20}`。
- 文件不存在 / 读不出来 / JSON 解析失败 / 仓库没配 → 返回空 map，调用方回退 `DefaultLowStockThreshold`。
- **每次调用重新读盘，不做缓存**。这点是刻意的：门禁里的测试会先调用 `LowStockThreshold`，如果 `sync.Once` 缓存了「文件不存在」的结果，之后写入的配置就永远读不到了。

关于路径：`go test` 的进程工作目录是包目录（`inventory/`），直接写死仓库根相对的 `inventory/thresholds.json` 在测试里会变成 `inventory/inventory/thresholds.json`。所以 `thresholdsCandidatePaths` 按优先级找：源码文件旁边（用 `runtime.Caller`，最稳）→ 相对 CWD 的 `inventory/thresholds.json` → 相对 CWD 的 `thresholds.json`。这样测试、`go run`、独立编译产物三种跑法都能落到同一个文件。

## 验证

- `make check`（build + test + vet）绿。
- 临时放 `{"shanghai": 20}` + 临时测试：`shanghai=20`、`chengdu` 走默认 5、`IsLowStock("shanghai", 20)==false`（严格小于）、`LowStockWarehouses` 结果正确。
- 把配置改成坏 JSON：冻结测试全过，`shanghai` 回退 5。
- 临时文件已全部删除，`git status` 只有 `M inventory/stock.go`，`stock_test.go` 逐字节未动。

两点说明：
1. 我没有提交 `inventory/thresholds.json` 本体——需求里「文件不存在就回退」是明确要支持的初始状态，配置内容应由业务按仓库填；需要的话我可以补一个示例文件。
2. 直接 `make check` 在本沙箱里首次会因默认 `~/Library/Caches/go-build` 不可写而失败，我用 `GOCACHE=$PWD/.tmp/gocache` 跑的；这不是代码问题，但你那边若也受限，需要设一个可写的 `GOCACHE`。临时缓存目录已清理。
