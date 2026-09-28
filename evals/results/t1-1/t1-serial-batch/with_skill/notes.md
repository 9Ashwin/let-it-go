# t1-serial-batch / with_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：356.3s
- token：1377088
- 步数：26，工具调用：45

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

按 `loop-it` 的**串行批次**路径做完了两张卡片。仓库里没有 `gh`（`origin` 是本地 bare 仓库），所以走**本地模式**交付。

## 做了什么

**前置**：`make check` 基线绿、工作树干净、在 `main`；检查点按仓库约定落在 `requirements/01_REQ-greeting/issues/.loop-state.json`（随需求资料版本化）。

**依赖解析的一个坑**：卡片写的是 `Blocked by: issue-001`，而 `loop_state.py` 的解析器只认 `Depends on: #N` / `requires #N` / `Dependencies: #N`。本地卡片→`gh issue list` JSON 的适配层把 `issue-001` 归一化成 `#1`，于是 `scan` 正确识别出 `#2 依赖 #1`，拓扑序为 1 → 2。

| issue | 改动 | commit | 验收证据 |
|---|---|---|---|
| #1 Slug | `greeter/slug.go` + `greeter/slug_test.go`（`strings.Fields` 折空白 + `ToLower`） | `f0724ad` | L1：`go test ./greeter -run TestSlug -v -count=1` |
| #2 JoinSlug | `greeter/join_slug.go` + `greeter/join_slug_test.go`（逐段复用 Slug，跳过空/纯空白） | `19382c4` | L1：`go test ./greeter -run TestJoinSlug -v -count=1` |

每卡一个 commit、各自跑门禁；验收条件逐条记进了 `requirements/01_REQ-greeting/README.md` 的表，机器真相在检查点的 `evidence`（均标 `layer: L1`——这是纯函数库、无运行入口，L3/L4 不适用）。

**批末评审**：派了一个不共享上下文的子代理做对抗性评审，结论 **accept（follow-up 级）**：
- 采纳并修掉：`slug.go` 注释「URL 友好」过度承诺 → 收紧为「小写、连字符分隔」；
- 有意拒绝：把表驱动测试改成 `t.Run`/`t.Errorf` —— 仓库既有 `greet_test.go` 就用普通 `t.Fatalf`，AGENTS 要求匹配既有风格；
- 它抓到一个真实漂移：我把 `#2 shipped` 前的检查点状态漏提交了 → 已在批末 commit `60a1cea` 补上。

**交付（本地模式）**：`feat/01-req-greeting` 已 `--no-ff` 合入 `main`（merge `11ab2dd`），分支保留作留档；没有远端可推、没有 PR 可开。

## 门禁确认

```
make check            → build ./... + test ./...  → ok        [exit 0]
go test ./... -v -count=1 → TestGreet/TestJoinSlug/TestSlug 全 PASS
git diff c9e92f4 HEAD -- Makefile greeter/greet_test.go → 空（冻结基线逐字节未变）
```

检查点 `summary`：**2/2 完成，0 follow-up open**，工作树干净。
