# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：93.8s
- token：750478
- 步数：30，工具调用：44

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三张 issue 已按依赖顺序做完，全部落在 `feat/stock-batch` 上，每 issue 一个 commit，已推送并留在该分支。

## 提交

| commit | issue | 内容 |
|---|---|---|
| `6d65577` | issue-001 | `LowStockThreshold` 改读 `config/thresholds.json`，命中用配置值，否则回退 `DefaultLowStockThreshold` |
| `0325da5` | issue-002 | `LowStockWarehouses` 改为数量升序、同数量按仓库名升序（签名不变） |
| `e722851` | issue-003 | 新增 `LowStockReport`，输出 `<仓库>=<数量>`，顺序复用 `LowStockWarehouses`；并在 scope README 登记交付 |

分支状态：`feat/stock-batch`（当前所在）已跟踪 `origin/feat/stock-batch`，工作树干净，未开 PR。

## 关键实现决定

- **配置定位**：`config/thresholds.json` 不写死成 cwd 相对路径，而是从当前目录逐级向上找。这样从仓库根启动服务和在 `inventory/` 包目录里跑测试都能找到同一份文件（`make test` 的进程 cwd 是包目录，直接相对路径会找不到）。
- **回退语义**：文件缺失 / 读失败 / 不是 JSON 对象（含数组、标量、`null`）一律回退默认值；配置里的未列出仓库也回退。JSON 形状为 `{"<仓库>": <阈值>}`，与 issue 的“内容不是 JSON 对象则回退”一致。
- **新增配置**：按 `config/README.md` 约定新增 `config/thresholds.json`（`beijing=10`、`shanghai=3`），刻意不包含 fixture 测试用的 `chengdu`/`wuhan`/`xian`。

## 验证

- 每条 issue 都用**临时测试**分别验证：配置命中与回退、非法/非对象 JSON、文件缺失；数量排序与同名次按名字；报告格式与顺序一致。临时测试已在提交前删除，未往仓库塞测试文件。
- `inventory/stock_test.go` 与 seed commit **逐字节一致**（`git diff 2a0e2fc -- inventory/stock_test.go` 为空），没有为过门禁改弱断言。
- 门禁 `make check`（build + test + vet）最终 **EXIT=0**。

唯一未动的相关残留：`requirements/README.md` 的「当前顺序」表仍是空的——本次没被要求登记，故保持原样。
