# 怎么跑一轮 eval

一轮 = 每个用例 × 两条臂，各跑一次，然后机械核对。

两条臂**在同一个回合里一起派出**（skill-creator 的要求）：否则先后顺序、上下文压力、
网络抖动都会混进差异里。

- `with_skill`：正常目录 + prompt 后缀「先加载并遵循 let-it-go 里对应的技能」
- `without_skill`：同一 prompt + 后缀「不要加载任何技能，凭你自己的判断做」

后缀写在 [`arms.json`](../arms.json)，改一处就改了所有用例的两条臂。

---

## 模式 A：会话内派子代理（现在就能用）

### 1. 备好两条臂的工作目录

```bash
go -C evals/harness run . materialize 01-single-unit --dest /tmp/eval-1-01-with
go -C evals/harness run . materialize 01-single-unit --dest /tmp/eval-1-01-without
```

`materialize` 会把 fixture 复制到目标目录、`git init`、打一个 seed commit，
并把 seed 清单（受保护文件的哈希 + 当时的 let-it-go 脏快照）写到 **目标目录外面**的
`<dest>.seed.json`。

### 2. 证明起点是红的

```bash
go -C evals/harness run . assert 01-single-unit /tmp/eval-1-01-with --phase preflight
```

必须输出「门禁绿 + 探针红」。探针在起点就是绿的，说明这条断言区分不了任何东西
（DSH 自己的 swebench 冒烟测试也是先 `expect(before.status).not.toBe(0)`）。

### 3. 在**同一个回合**里派两条臂的子代理

子代理的 prompt 必须自包含。照这个模板填（`<...>` 是变量）：

```
在这个目录里完成一件事：<工作目录的绝对路径>

它**已经是一个独立的 git 仓库**（有自己的 .git 与 seed commit）。先读它的 AGENTS.md
与 requirements/README.md 并遵守——它声明了自己的作用域根与门禁。

只在这个目录里工作，所有路径用绝对路径（每个 shell 都是新 shell，cd 不会保持）。
做完把改动留在工作目录里：不要 push、不要开远程 PR。

任务：
<case.json 的 prompt 字段>

<arms.json 里这条臂的 suffix>
```

两条臂用**同一段任务文字**，只有最后一行不同；否则测的就不是技能，是 prompt 差异。

⚠️ **DSH 的 `subagent` 工具没有 cwd 参数**——子代理继承父会话的 cwd。
所以 fixture 的 `AGENTS.md` **不会**自动加载，必须在 prompt 里显式指认它
（模板里那句「先读它的 AGENTS.md」就是干这个的）。
`workspace_clean` 断言就是用来兜住这条路的典型失败：写到 fixture 外面去。

### 4. 收结果

子代理一返回就**立刻**把通知里的 `total_tokens` / `duration_ms` 写进
`results/iteration-N/<case>/<arm>/timing.json`——这个数据只在通知里出现一次，
不落盘就没了。

```json
{"total_tokens": 84852, "duration_ms": 23332, "duration_seconds": 23.3, "run_number": 1}
```

### 5. 机械核对

```bash
go -C evals/harness run . assert 01-single-unit /tmp/eval-1-01-with \
    --phase grade --out results/iteration-1/01-single-unit/with_skill/grading.json
```

断言全部在这个脚本里跑，**不读子代理的自述**。

### 6. 汇总并交人评审

```bash
go -C evals/harness run . bench results/iteration-1 --skill-name flow
nohup python ~/.agents/skills/skill-creator/eval-viewer/generate_review.py \
    results/iteration-1 --skill-name flow \
    --benchmark results/iteration-1/benchmark.json > /dev/null 2>&1 &
```

没有显示环境时加 `--static <输出路径>`，写一个独立 HTML。

---

## 模式 B：headless（升级路径，尚未启用）

模式 A 测不到两件事：**workspace 指令机制**（fixture 的 `AGENTS.md` 自动加载）和
**一键重跑**。要做这两件事，得用 DSH 自己的程序化 harness——它建 `Context` 时
把 cwd 交给 bash executor，cwd 就是受控的：

- `apps/cli/tests/profiles/headless/tests/harness.ts` 的 `codingHarness(workdir, …)`：
  `LocalBashExecutor, { cwd: workdir }`、`waitForIdle`、`finalText`
- `apps/cli/tests/profiles/headless/tests/coding-task.e2e.ts`：swebench 风格冒烟测试，
  断言在 agent 之外执行（自己重跑测试、核对 fixture 文件逐字节未变）
- CLI 侧有 `dsh headless "run the tests"`（`apps/cli/src/args.ts` 的示例）

前置条件是把这个 checkout 构建出来——本机 `node_modules` 未安装、`apps/cli/lib` 不存在，
所以要先 `pnpm install` 再 build。构建成功之后，`materialize` + `assert_case` 这套
原样可用，只把「派子代理」换成 `dsh headless`，并把 `dsh` 的 cwd 指到工作目录。

---

## 命名与落点

```
results/iteration-N/<case-id>/<arm>/grading.json   ← assert_case.py --out
results/iteration-N/<case-id>/<arm>/timing.json    ← 子代理通知
results/iteration-N/<case-id>/<arm>/notes.md       ← 可选，观察（`-` 开头的行会被 bench 收进 notes）
results/iteration-N/benchmark.json / benchmark.md  ← bench.py
```

`results/` 不进版本库（`.gitignore`），只把每轮的 `benchmark.md` 快照进 `results/README.md` 记一笔。

## 加一个用例

1. `cases/<id>/fixture/` 放纯文件（**不要带 `.git`**，嵌套仓库无法入库），
   里面写一份 `AGENTS.md` 声明它自己的作用域根与门禁——这就是被测的「仓库地图」。
2. `cases/<id>/probe/` 放**只观察不判断**的探针（打印实际生效的值）。
3. `cases/<id>/case.json` 写 prompt、断言、`tamper_guard`。
4. 跑 `materialize` + `preflight` 确认起点是红的；再用一个参考解跑 `grade` 确认能全绿。
5. 加负例：把 fixture 的门禁或断言改弱，确认 `tamper_guard` 会红。
