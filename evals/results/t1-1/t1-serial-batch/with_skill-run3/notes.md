# t1-serial-batch / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：230.3s
- token：968896
- 步数：28，工具调用：39

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

按 `loop-it` 的**串行批次**路径做完了。

## 模式判定与流程
两张卡有真实阻塞边（issue-002 blocked by issue-001），按技能判为串行批次：一条需求分支 + 每卡一个 commit + 每卡门禁，批末一次评审、一次交付。全程状态落在 `requirements/01_REQ-greeting/issues/.loop-state.json`（已通过 `.git/info/exclude` 排除出版本库，未污染仓库）。

前置检查通过（工作树干净、在默认分支、`origin` 可达、无 `gh` → 交付走本地模式）。

## 实现（依赖顺序）
| issue | 改动 | commit | 门禁 |
|---|---|---|---|
| 001 Slug | 新增 `greeter/slug.go` 的 `Slug` + 新测试文件 `greeter/slug_test.go` | `28279d6` | `make check` ✅ |
| 002 JoinSlug | `greeter/slug.go` 增 `JoinSlug` + 新测试文件 `greeter/join_slug_test.go` | `feec424` | `make check` ✅ |

- `Slug` 用 `strings.Fields` + `ToLower`，同时满足去首尾空白、连续空白折一、转小写。
- `JoinSlug` 复用 `Slug`，以结果为空跳过空串与纯空白段。
- 每张卡的 5 条验收条件逐条写进了检查点 `evidence`（均 L1，纯函数无 L3/L4 可跑）和 scope README 的验收表。

## 批末收尾
- **`/review-it`**：派了不共享上下文的子代理做两轴评审 → **通过**。Spec 轴 5/5 满足、无 missing/extra/wrong；Standards 八维度无可采纳发现；门禁复跑（含 `-count=1`）绿。
- **`/ship-it`（本地模式）**：补 `docs: record delivery evidence...`（`b9d7713`），`git merge --no-ff feat/req-greeting` 合入 `main`（merge `dd693b5`），分支保留作留档；未推远端（无 `gh`，符合本地模式约定）。
- 实现总结（进度/关键决策/验证记录/未决事项 + 逐项 commit 证据表）写进了 `requirements/01_REQ-greeting/README.md`。
- `loop_state.py summary`：2/2 shipped，0 follow-up；goal 已 `complete`。

## 最终门禁确认
在合入后的 `main` 上跑 `make check`：`go build ./...` + `go test ./...` → `ok`，退出码 0。

冻结基线逐字节未动：
```
3ba8f86e...c3b  Makefile              ✅ 与开工前一致
de952bb1...ae   greeter/greet_test.go ✅ 与开工前一致
```

一处如实说明：两条 shipped 都只到 L1（脚本给了告警）。本需求是纯函数库，没有服务/接口可点，L1 单测就是它适用的那一层，不存在欠观测。
