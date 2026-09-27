# 02-mid-flight-change / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：410.0s
- token：1765792
- 步数：30，工具调用：51

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

完成。按 `let-it-go` 技能集里的 **`loop-it`**（实现入口）走的是**单单元模式**：一个 issue、内联做完、不建 worktree、不派实现子代理；收尾按它的流程走了 `/review-it`（独立子代理评审）→ `/ship-it`（本地模式交付）。

## 改了什么

- **阈值来源改为仓库根的 `config/thresholds.json`**（符合 `config/README.md` 的约定），`LowStockThreshold(warehouse)` 按仓库名查表，命中返回值，否则回退默认值。
- **`DefaultLowStockThreshold` 5 → 10**。
- **删除 `inventory/thresholds.json`**，仓库里只剩 `config/thresholds.json` 一份，无两套并存。
- 缺失 / 读不出 / 内容不是 JSON 对象（数组、字符串、`null`）一律回退默认值；`IsLowStock` 仍是严格小于。
- 对外函数签名未动；冻结的 `inventory/stock_test.go` 与 seed commit 逐字节一致。

配置定位用两个相对候选路径（`config/` 优先，其次 `../config/`），覆盖「从仓库根运行」和「`go test` CWD 是 `inventory/`」两种情形，不依赖源文件路径。新增测试覆盖 loader 回退、端到端按仓库取阈值、以及配置缺失时回退。

## 门禁

`make check`（`go build` + `go test` + `go vet`）在交付后的 `main` 上退出码 **0**；另外 `go test -trimpath ./inventory/` 也 0、无 SKIP。

## 独立评审

派了 3 轮看不到会话的独立评审者（我自己就是作者，技能要求交给全新上下文）：

1. 第一轮报 4 条：`runtime.Caller` 在 `-trimpath` 下静默失效（高）、端到端测试可被 Skip 绕过（中）、每调用读盘（低-中）、配置未跟踪（低）。
2. 修了第 1 条（改为相对候选路径），部分修第 2 条；**拒绝**了缓存那条（fixture 规模小，缓存反而引入全局状态、让回退行为不可测）。第二轮核验修复通过，还剩第 2 条。
3. 按建议把配置测试的 `Skip` 改成 `Fatal`，并用 `t.Chdir` 补了「配置缺失 → 回退」的端到端用例。第三轮结论 **clean**。

## 交付

本地模式（`gh` 不可用，不 push、不建 PR）：

- 分支 `feat/low-stock-thresholds`，两个 commit：`0abcc8b` 实现、`6248a73` 需求资料交付记录
- `main` 上 `--no-ff` 合入：merge `d3e6f8a`（分支保留作留档）

需求卡 `requirements/01_REQ-low-stock-threshold/issues/issue-001-low-stock-thresholds.md` 的过时来源已更正为 `config/thresholds.json`、默认值标注为 10，验收条件勾选，并写入了四类实现总结（设计决策 / 偏离 / 权衡 / 待确认）与验收证据。
