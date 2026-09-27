# 04-serial-batch / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：343.1s
- token：2211971
- 步数：36，工具调用：56

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，批末对抗性评审通过后已推送。总结如下。

## 分支与提交

需求分支 `feat/stock-batch`（基于 `main`），**当前就停在它上面**，已推到 origin：

```
6e3ba78 docs(01_REQ-stock-batch): 标记三条 issue 已交付
aaa3c4d feat(inventory): 新增 LowStockReport (issue-003)
723472d feat(inventory): 低库存列表的数量+名字排序 (issue-002)
01e9a06 feat(inventory): 阈值来源改成配置文件 (issue-001)
eac911e chore: initial import
```

每个 issue 恰好一个实现 commit（docs 那条是批末交付记录，不是 issue 提交）。没有 PR。

## 各 issue 做了什么

- **issue-001**：`LowStockThreshold` 改为读仓库根 `config/thresholds.json`；路径用 `runtime.Caller` 锚定源码文件而非进程 cwd（`go test` 的 cwd 是包目录）。文件不存在/不可读/顶层非 JSON 对象一律回退 `DefaultLowStockThreshold`。新增 `config/thresholds.json`（`xian=1`、`beijing=10`）。
- **issue-002**：`LowStockWarehouses` 收集 `(warehouse, quantity)` 后 `sort.Slice`，数量升序、同数量按仓库名升序；签名与严格小于判定不变。
- **issue-003**：新增 `LowStockReport`，直接复用 `LowStockWarehouses` 的顺序拼 `<仓库>=<数量>`，不复制排序逻辑。

## 验证与门禁

- 最终 `make check`（build + test + vet）**退出码 0**。
- `inventory/stock_test.go` 与种子提交逐字节一致（冻结 fixture 未被改动）。
- 三份 issue 的验收条件各有对应测试观测，已写进检查点 `requirements/01_REQ-stock-batch/issues/.loop-state.json`（该文件按技能约定排除出版本库，用 `.git/info/exclude` 而非新提交）。

## 批末对抗性评审

派了一个未参与实现的评审者（独立上下文）审整批 diff，结论 **accept**。它独立跑了 `make check`（绿）、核对了冻结文件哈希、用独立 module 探针验证配置生效与三种回退路径、并用 2 万组随机输入与参考实现比对排序与报告顺序。它提的两条非阻塞修复我已采纳并并入 issue-001 的提交（分支未推，用 fixup rebase，仍是每 issue 一个 commit）：

1. `inventory/thresholds_config_test.go` 过一遍 `gofmt`；
2. 去掉「配置文件至少配一个仓库」的非空断言，改为断言未配置仓库回退默认值——避免在「配置为空」这一合法回退状态下自己的测试误红。

一条已记录的取舍：路径锚定依赖编译期源码路径，在 `go test -trimpath` 下会静默回退默认值；当前门禁不用 `-trimpath`，未做加固。

## 说明

批末 `walkthrough` 未落成单独文件，以免在「一个 issue 一个 commit」之外再增提交；本段即走查内容。scope README 的已交付/未交付与三张卡片的验收框已随 `6e3ba78` 收口。
