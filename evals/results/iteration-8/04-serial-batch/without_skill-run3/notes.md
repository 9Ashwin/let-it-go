# 04-serial-batch / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：128.6s
- token：1058848
- 步数：34，工具调用：50

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

三个 issue 已按依赖顺序做完，全部落在需求分支 `feat/stock-batch` 上，一个 issue 一个 commit，已推到 origin 并停留在该分支。

## 交付结果

分支：`feat/stock-batch`（基于 `main` 的 seed commit `77c1246`），已 `git push -u` 到 origin，当前 HEAD：

| commit | 内容 |
|---|---|
| `116a866` | issue-001：`LowStockThreshold` 从 `config/thresholds.json` 读阈值，没配/文件不存在/读不出/非 JSON 对象一律回退 `DefaultLowStockThreshold` |
| `88b1714` | issue-002：`LowStockWarehouses` 改为数量升序、同数量按仓库名升序（签名与判定规则未动） |
| `7f2d093` | issue-003：新增 `LowStockReport`，输出 `<仓库>=<数量>`，顺序委托给 `LowStockWarehouses` 保证一致 |

未开 PR（仓库无 GitHub 远端）。

## 关键决定（需要你知道的权衡）

- **配置路径解析**：用 `runtime.Caller` 按源码位置定位仓库根的 `config/thresholds.json`，而不是相对进程工作目录。原因是 Go 测试进程的 CWD 是包目录，相对路径会读不到仓库根的配置；这样无论从哪里跑都在读同一份文件。
- **配置文件**：按 `config/README.md`「新配置一律加在这里」新增了 `config/thresholds.json`，内容为示例 `{"beijing": 10, "shanghai": 3}`；`chengdu`/`wuhan` 刻意不配，保留为回退样例。如果你希望这个文件不提交（由部署侧提供），告诉我，我可以移掉。
- 每次读调用都重新读文件（不缓存），这样配置变化即时生效，也便于验证。

## 验证

- 每个 issue 都用临时测试先红后绿地验证了行为（覆盖配置命中/各类回退、排序稳定性、报告格式与顺序），临时文件已在提交前删除，未混入 commit。
- **门禁 `make check` 绿**（build + test + vet，`go test -count=1` 复跑也通过）。
- 受保护文件与 seed 逐字节一致：`Makefile` 与 `inventory/stock_test.go` 的 sha256 均匹配 `work.seed.json`。
- 工作树干净，3 个 commit 各自只含对应 issue 的改动（commit1 无排序/报告，commit2 有排序无报告，commit3 才有报告）。

当前仍在 `feat/stock-batch` 上，验收可以直接在它上面看。
