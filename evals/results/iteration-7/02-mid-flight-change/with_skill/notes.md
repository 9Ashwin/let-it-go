# 02-mid-flight-change / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：188.5s
- token：693652
- 步数：20，工具调用：39

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

已完成。按 `loop-it` 判定这是**单单元**（只有 `issue-001` 一张卡），所以内联做完，没有开循环、没有生成 `tasks/` 检查点、也没派实现子代理。

## 变更内容

**配置迁移（单一来源）**
- 新增 `config/thresholds.json`：`{"shanghai": 20}`（由旧文件内容迁入）
- 删除 `inventory/thresholds.json`，仓库里不再有两套

**`inventory/stock.go`**
- `DefaultLowStockThreshold`：`5` → `10`
- `LowStockThreshold(warehouse)` 从 `config/thresholds.json`（相对进程 cwd）读取 `map[string]int`；命中返回配置值，未配回退默认值
- 文件不存在 / 读不出来 / 内容不是 JSON 对象 → 一律回退默认值（`loadThresholds` 返回 err 即回退）
- `IsLowStock` 严格小于、`LowStockWarehouses` 排序、对外签名均未动

**`inventory/thresholds_test.go`（新增，自包含）**
- 配置值生效 + 未配回退；缺文件 / 读不出来 / 非 JSON 对象三条回退路径。用临时目录造配置、测试内 chdir 并恢复，不依赖仓库里那份会被探针改写的文件

**需求卡**：把过时来源改为 `config/thresholds.json`、补上默认值 10、记录变更并勾选验收项

## 验证（都实跑过）
- `make check`（build+test+vet）**退出码 0**，`gofmt -l` 无输出，`-race` 通过
- 用 eval 官方探针实跑了三种场景，输出与期望逐项一致：
  - `{"shanghai":20}` → `{"shanghai":20,"beijing":10,"chengdu":10}`
  - `{"shanghai":20,"beijing":3}` → `{"shanghai":20,"beijing":3,"chengdu":10}`
  - 配置缺失 → 全 `10`
- 受保护文件逐字节未变：`Makefile`、`inventory/stock_test.go` 的 sha256 与 seed 完全一致

## 评审
交给**全新上下文**的评审者按 `review-it` 两轴审：Spec 轴 6 条验收条件逐条对上，Standards 轴无「必须修」项，结论 `accept`。它提的两条建议我按契约拒绝了并说明理由：不加对真实 `config/thresholds.json` 的硬编码断言（探针会按场景改写/移除该文件，会引入脆弱性）；`chdir` 的串行约束是 Go 测试默认行为，不加注释。

## 提交
本地提交 `40d74db`，工作树干净。`gh` 未安装、远程只是本地 bare 仓库，所以**没有开 PR/合并**，这一步无法执行；需要推送或开 PR 的话请告诉我。
