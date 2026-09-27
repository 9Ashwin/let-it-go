# eval 工作区约定

这里评测的是 **flow 技能本身**：把真实代码示例交给 agent，让它跑一遍技能，
然后在 agent 之外核对结果。改技能之前读 [README.md](README.md)，
跑一轮的完整步骤在 [harness/run.md](harness/run.md)。

## 三条硬规则

1. **fixture 不带 `.git`。** 嵌套仓库无法被 let-it-go 正常入库；版本控制留给运行时——
   `harness/materialize` 会复制到临时目录、`git init`、打一个 seed commit。
   这样每次运行都从同一个起点开始，而且 fixture 自带 `.git` 之后它就是自己的 project root
   （DSH 取最近的 `.git` 祖先），fixture 自己的 `AGENTS.md` 才会生效。
2. **探针只观察，不判断。** `cases/*/probe/` 里的代码只打印实际生效的值；
   期望值写在 `case.json` 的 `expect` 里，由 harness 比对。观察与判断分开，
   探针才能跨语言复用，也才不会被「实现细节变了」牵着走。
3. **断言必须在 agent 之外执行。** 不读 agent 的自述——DSH 自己的 swebench 冒烟测试
   就是这个立场（「agent 声称它成功了……然后世界要同意」）。这里的「世界」是
   fixture 自己的门禁、行为探针，以及文件树本身。

## 每条用例必须有这三样

- `gate`：fixture 自己的门禁（改动之后必须绿）
- `probe`：行为探针（**起点必须是红的**，否则这条断言区分不了任何东西）
- `tamper_guard`：fixture 的门禁与自带断言不许被改弱。没有它，
  「把测试删掉换绿」是能通过的——DSH 那句「一个把测试废掉而不是把 bug 修好的 agent
  应该在这里失败」说的就是这个。

`harness/selfcheck` 会查这三样在不在，它挂在 `make check` 上。

## harness

`harness/` 是 **Go** 写的（和 fixture 同一种语言，`make eval-*` 只需要一套工具链）：

```bash
go -C evals/harness run . selfcheck
go -C evals/harness run . list
go -C evals/harness run . materialize <case-id> --dest <dir>
go -C evals/harness run . assert <case-id> <dir> --phase preflight|grade [--out FILE]
go -C evals/harness run . bench <iteration-dir> --skill-name flow
```

`bench` 的输出严格照 skill-creator 的 `references/schemas.md`——viewer 读的就是那些
字段名（`configuration`、`result.pass_rate`、`run_summary.delta`），换个名字它会显示成空的。

## 落点

- `results/` **不进版本库**（只有 `results/README.md` 记每轮 benchmark 的快照）。
- 子代理通知里的 `total_tokens` / `duration_ms` **只在通知里出现一次**，
  收到就写进对应臂的 `timing.json`，不落盘就没了。
- 新增用例：fixture 用哪种语言由**被测仓库的样子**决定（现在都是 Go），
  harness 不用改——探针是声明式的。
