# 08-undeclared-workspace / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：816.7s
- token：3349677
- 步数：48，工具调用：64

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `prd`（let-it-go 里对应「一句诉求 + 怎么落地你定」的技能）走完整条链：`prd → to-issues → loop-it → review-it → ship-it`。

## 落地结果

**行为**：`LowStockThreshold(warehouse)` 现在读 `config/thresholds.json`（`{"xian": 10}` 这种「仓库名 → 阈值」对象）；文件里没有的仓库、文件缺失/为空/损坏/类型不符/`null` 值，一律回退 `DefaultLowStockThreshold`（5）。`IsLowStock` 仍是严格小于。

**热生效**：每次调用都重新读盘、**不缓存**，所以运维改完文件下一次判定即生效，不用重建也不用重启（明确没用 `go:embed`）。

**路径**：从进程 cwd 逐级向上找 `config/thresholds.json`——因为 `go test ./...` 以包目录为 cwd，只有向上找才能让「配置在仓库根」对包内测试和真实进程同时成立。

## 交付物

分支 `feat/per-warehouse-thresholds`，commit `79c1b16`（`main` 没动，仍 `b5e1e49`）：

- `inventory/thresholds.go`（新增，读盘 + 路径解析）、`inventory/stock.go`（`LowStockThreshold` 改接配置）
- `inventory/thresholds_test.go`（新增，命中/回退/walk-up/同进程热生效）
- `config/thresholds.json`（`{}`）+ `config/README.md`（记了格式与热生效）
- `tasks/per-warehouse-thresholds/`（PRD 契约、验收表与证据、L3 记录）

**合入留给你**（本地模式：有 origin 但不是 GitHub、`gh` 不可用，没 push 也没开 PR）：

```bash
git checkout main && git merge --no-ff feat/per-warehouse-thresholds
```

## 验证

- `make check`（build+test+vet）exit 0；`inventory/stock_test.go` 与 seed 逐字节一致。
- 新增测试全 PASS（含 `{"xian":null}`、损坏 JSON、缺失文件、祖先目录查找、同进程改写文件）。
- L3：真实编译进程读真实文件，`{"xian":10}`→10、改文件→3、`{}`→5，全程同进程不重启；记录在 `tasks/.../notes/l3-hot-reload.txt`。
- `review-it` 派了不共享上下文的子代理，两轮都判**通过**、无必改项。

## 两点要你知道

1. **没建 issue 卡**：`to-issues` 的硬边界是「一个上下文装得下的改动不产 issue」，这是个单单元改动，所以只落了 PRD 契约、就地内联实现，也没建 `.loop-state.json`。（副作用：`loop_state.py route` 的批处理模型不认这条「跳过卡片」的路，会仍指向 `to-issues`；这是脚本的模型边界，不是流程漏走。）
2. **一个有意保留的取舍**（评审提出、记在 scope README）：向上查找让以 `inventory/` 为 cwd 的冻结测试也会读到仓库根配置。冻结测试把 `chengdu`/`wuhan` 当「未配置」样本、并假设 `xian=0` 属低库存——如果哪天给这几个名字配了会让断言不成立的取值，`make check` 会变红。改动前建议先看 PRD 的 unknowns 再决定是否换成锚定路径。
