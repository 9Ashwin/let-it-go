# t1-single-unit / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：155.2s
- token：373478
- 步数：14，工具调用：21

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 **loop-it 单单元模式**走完全流程（不碰检查点、不建 worktree、不写走查件）。

## 交付内容

**卡片**：`requirements/01_REQ-greeting/issues/issue-001-slug.md`
**分支**：`feat/issue-001-slug`（本地模式，未推、未开 PR）

| 文件 | 说明 |
|---|---|
| `greeter/slug.go` | 新增 `Slug`：`ToLower(Join(Fields(s), "-"))` |
| `greeter/slug_test.go` | 新增测试，逐条覆盖三条验收条件 |
| `issue-001-slug.md` | 追加「实现总结」（进度/关键决策/验证记录/未决事项） |

`strings.Fields` 一次同时满足「去首尾空白」和「连续空白折成一个连字符」，无需正则。**只新增文件，未改冻结基线。**

## 验证（L1，三条验收条件都落在这一层）

```
make check   →  go build ./... + go test ./...  →  ok  example.com/greeter/greeter  (EXIT=0)
git diff main -- Makefile greeter/greet_test.go  →  空（冻结基线逐字节未变）
```

独立评审者（不共享上下文的子代理）做了两轴对抗性评审，结论**通过**：Spec 轴 missing/extra/wrong 全空；Standards 轴八维无阻断级发现，低风险观察（空串/NBSP/额外用例）均判为超出规范范围而拒绝；并用 `go test -count=1 -v ./...` 非缓存复核绿。

## 收尾状态

`git log --oneline`：

```
510d1c9 docs: record implementation summary for slug
711a63e feat: add Slug to greeter package
7b7475f chore: initial import   ← main
```

工作树干净。`gh` 未安装，ship-it 判定为**本地模式**：没有 PR，交付记录写在卡片里。

**合入归人**（`/merge-it` 只有人能敲）。本地模式命令：

```bash
git checkout main && git merge --no-ff feat/issue-001-slug
```

我没有自己合入，也没有 push。
