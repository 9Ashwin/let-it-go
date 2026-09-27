# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：164.6s
- token：1824612
- 步数：41，工具调用：66

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三条 issue 已按依赖顺序做完，整批在 `feat/stock-batch` 上，一个 issue 一个 commit，已推到 origin 并留在该分支上。

## 交付内容

分支/提交（相对 `main` 共 3 个 commit，当前就在 `feat/stock-batch`）：

| commit | issue | 改动 |
|---|---|---|
| `f0fa108` | issue-001 | `LowStockThreshold` 改读 `config/thresholds.json`；未配置/文件缺失/读不出/非 JSON 对象一律回退 `DefaultLowStockThreshold` |
| `446a5b4` | issue-002 | `LowStockWarehouses` 按数量升序、同数量按仓库名升序（签名与判定规则未动） |
| `0782d43` | issue-003 | 新增 `LowStockReport`，`"<仓库>=<数量>"`，顺序直接复用 `LowStockWarehouses` |

## 关键取舍

- **配置路径按进程 cwd 解析**：任务只说「配置放在 `config/thresholds.json`」、没说进程从哪启动；Go 把测试 cwd 设成包目录，所以这是合理的相对路径实现（eval 探针本身会先 `chdir` 回仓库根再观察）。
- **不缓存配置、每次调用重读**：避免测试间残留状态互相污染；也符合验收里「文件没了就回退」的要求。
- 新增了三个测试文件（`thresholds_test.go`/`order_test.go`/`report_test.go`），覆盖配置命中与回退、排序键、报告顺序；未改动任何受保护文件（`Makefile`、`inventory/stock_test.go` 与 seed 的 SHA-256 逐字节一致）。
- 批末顺手把 `requirements/01_REQ-stock-batch/README.md` 的「已交付/未交付」改成实际状态，并补了 `issues/.loop-state.json` 作为批次检查点（都在 scope 目录内，随 issue-003 一起提交）。

## 验证

- 集成态 `make check`（build + test + vet）→ exit 0。
- 本地复演了 eval 探针两个场景，输出与期望逐项一致：
  - 配 `{"shanghai":20}`：`t_shanghai=20, t_beijing=5, o_wuhan=0, o_xian=1, o_shanghai=2, r_len=3, r_first_is_wuhan=1`
  - 无配置：`t_shanghai=5`，其余同上
  - 复演用的探针文件与临时配置已清理，`git status` 干净。
- 结构核验：`feat/` 分支仅 1 条；`main..HEAD` 3 个 commit；本地 HEAD 与 `origin/feat/stock-batch` 一致；无 `tasks/` 目录；未提交 `config/thresholds.json`。

没有加载任何技能。未开 PR。
