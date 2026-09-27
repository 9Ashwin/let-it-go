# 08-undeclared-workspace / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：114.0s
- token：462577
- 步数：17，工具调用：21

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按仓库配低库存阈值已落地，`make check` 全绿，冻结的 `stock_test.go` 逐字节未动。

## 怎么落地的

**配置格式** —— `config/thresholds.json`，仓库名直接映射阈值：
```json
{ "beijing": 20, "shanghai": 10, "guangzhou": 3 }
```
文件里没有的仓库回退到原来的 `DefaultLowStockThreshold`（5），行为与之前一致。

**不重建即生效** —— 关键点是配置文件在**每次查询时从磁盘读取**（`os.ReadFile` + `json.Unmarshal`），没有用 `go:embed`、也没有编译期常量或进程级缓存，所以运维 `vim config/thresholds.json` 保存后，下一次调用立刻是新值，既不重新构建也不用重启。`LowStockWarehouses` 批量场景一次调用只读一次盘，供循环里所有仓库共用。

**容错** —— 文件缺失、JSON 非法、值不是整数或为负数，都整体回退默认值，不会让库存查询失败。

**路径解析** —— 默认从工作目录向上逐层找 `config/thresholds.json`，到含 `go.mod` 的模块根为止。这样从仓库根目录、从 `inventory/` 下跑 `go test`、以及部署目录都能找到同一份；工作目录不在仓库根时可用 `INVENTORY_THRESHOLDS_CONFIG` 指定绝对路径。

## 改动的文件

- 新增 `config/thresholds.json`、`inventory/thresholds.go`（约 80 行，含路径解析与容错）、`inventory/thresholds_test.go`
- 改 `inventory/stock.go`：`LowStockThreshold` 改为查运行时配置
- 补 `config/README.md`：记录 schema、回退规则、热更新约定和环境变量

## 验证

- `make check`（build + test + vet）通过。
- `git diff --exit-code inventory/stock_test.go` 为空，冻结测试未改。
- 新增单测覆盖：命中配置、未配置回退、严格小于、改文件后立即生效、批量路径、非法/缺失/负数容错。
- 手工跑了一个临时程序确认：从仓库根和从 `inventory/` 两种 CWD 下 `beijing` 都读到 20、`chengdu` 回退 5，环境变量覆盖也生效（临时文件已删除）。

一个需要你拍板的点：我把 JSON 定成了**扁平映射**（`{"beijing": 20}`），没有加可配置的全局默认值——因为你明确说未配置的仓库走「原来的默认值」。如果以后想连默认值也配置化，再加个 `default` 字段的包裹结构即可，现在没做是避免超出需求。

改动都在工作区，没有提交。
