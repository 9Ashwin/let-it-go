# 历轮结果

`results/` **进版本库**——结果就是证据。这个文件是**快照台账**：
每轮跑完把 `benchmark.md` 的结论记一行，这样「技能改好还是改坏了」有据可查。

跑完一轮之后：

```bash
go -C evals/harness run . bench results/iteration-N --skill-name flow
```

把 `results/iteration-N/benchmark.md` 的表格贴到下面。

臂现在由 `evalctl run` 驱动（`dsh --profile headless`，cwd 就是铺出来的 fixture），
所以 `timing.json` 里的耗时与 token 是真的。

**iteration-1 … iteration-6 的原始结果文件已删**，只留这个文件里的结论。理由：那几轮是
**旧 fixture + 手工派子代理**条件下收的，条件已经变了，留着会有人拿它当可比数据。
**iteration-7 起作为新基线完整保留**，例外是 **iteration-8（隔离有漏洞，整轮作废，见下）**。

⚠️ **隔离是这条流水线的前提，不是细节。** 臂和评测仓库在同一台机器上，所以只要有任何一处
把 `case_id`、`evals/` 路径或「你在被评测」的暗示留在它能读到的地方，它就会去找评分标准。
iteration-8 与 iteration-9 各因此废掉一条臂。下面每一条都记了当时漏在哪——**这类漏洞一次都
不能静默放过**，所以 harness 里有一条污染检查，命中就写 `contaminated.json` 并在 stderr 报警，
那一轮的分数按不可信处理。

---

## iteration-7：护栏复测，和一个「断言错了」的教训

fixture 改完之后，把两条护栏（单次运行，各一条臂）重跑了一遍。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 01-single-unit | 6/6 | 6/6 | 无（护栏，符合预期） |
| 02-mid-flight-change | 7/7 | 7/7 | 无（护栏，符合预期） |

### case 01：技能被扣分，因为断言要求了没人要求的东西

第一次跑出来是 `with_skill` 6/7、`without_skill` 7/7——**技能输给裸模型**。当时的诊断是
「工作区地图与技能单单元判断冲突」。**那个诊断是错的**，查清之后是这样：

- `loop-it` 的单单元模式四步是「读清楚 → 内联实现 → 自证 → 收尾」，**从不产出需求资料**；
  技能里 `/prd（可选）` 也明写着 PRD 是可选的
- fixture 的 `AGENTS.md` 只说**作用域根在哪**，从没要求「每个任务都建一个 scope」
- 而 case 01 有一条断言 `path_glob requirements/*/README.md min 1`——**要求需求资料必须存在**

**所以是断言要求了任务和技能都没要求的东西**，照技能做对的臂反而被扣分。和 case 05 第一版
探针是同一个病：**断言能测什么，取决于任务说清了什么。** 那条断言已删；真正的风险由
`path_absent tasks` 与 `checkpoint_location` 守住。删掉之后两条臂都是 6/6。

### 这一轮还抓到两个真 bug

1. **只有 case 05 的探针修了 cwd，01–04 都没修。** 一条真实的 case 01 臂把配置放在
   `inventory/thresholds.json`——**prompt 就是这么写的**——仍被判「阈值没生效」，因为探针
   从包目录出发，实现去找 `inventory/inventory/thresholds.json`。四个探针都补上「回到仓库根
   再观察」，同一条工作树重打分 6/7。
2. **`workspace_clean` 量的是环境仓库，不是臂。** 它拿 let-it-go 工作树的脏状态当基准，
   两次把 Lead 的动作记成臂的越界。DSH 自己的 `benchmarks/AGENTS.md` 明说不要用
   ambient repositories。已改成只看 fixture 的父目录。

## iteration-8：作废——臂读到了答案键

跑完 8 条臂之后逐条审计 tool call，发现 **4 条爬出了自己的 fixture**：

- 1 条读了 `arms.json`、**另一条臂的检查点**、它的 README 与 `stock.go`，然后照抄那份检查点——
  它是唯一一条产出检查点的 `without_skill` 臂，靠抄拿到了 9/9
- 3 条读了 `evals/cases/<case>/case.json`，也就是**它正在被打分的那些断言**；其中一条还把探针
  复制进了自己的树

两个原因，都是我的：

1. **工作树铺在 `evals/results/` 里**，`../../..` 就爬到 `evals/`。DSH 自己的
   `benchmarks/AGENTS.md` 写着要用 private `mkdtemp` roots——我读过那一行，没照做。
   现在工作树建在仓库外的私有临时根，**打完分才搬回 `results/`**，跑的时候周围什么都没有。
2. **fixture 的 `AGENTS.md` 自称「这是一个评测用的真实代码示例」**——等于在第一条命令之前
   就告诉臂「你在被评测」。现在它只描述这个服务。

**结果文件已删**（8 条里 4 条污染，其中一条的满分是抄来的）。这一轮没有可用的数字。

## iteration-9：隔离修好之后的第一轮干净数据

`04` 两条臂各 3 次、`05` 两条臂各 1 次。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 04-serial-batch | 9/9、9/9、8/9 → 0.963 | 8/9、8/9、8/9 → 0.889 | **检查点** |
| 05-full-pipeline | 见下（首次 5/9，是测量天花板） | 7/9 | **PRD + issue 卡** |

### 修隔离时又抓出四个同类漏洞

前两个修完之后，`04` 的 `without_skill` 仍然被标记污染，于是顺着事件流一路查下去，又找到四个：

3. **seed 文件落在 `work/` 的上一级**，而臂的 cwd 就是 `work/`——一条 `ls ..` 就看见。
   它当时还带着 `case_id` / `case_name` / `workdir` / `seed_commit`，**没有任何地方读它们**，
   纯是写给臂看的线索。实测路径：`read ../work.seed.json` → 拿到 `case_id` →
   `find $HOME -maxdepth 6 -name 04-serial-batch` → 找到 `case.json`（断言就在里面）。
   现在 seed 在跑的时候被挪到另一个临时目录，跑完放回来（`tamper_guard` 要读它的哈希）。
4. **fixture 的第一个 commit 署名 `let-it-go eval <eval@let-it-go.local>`，信息写着
   `seed: eval fixture at its starting state`**——臂的第一条命令就是 `git log`。
   现在是 `dev <dev@example.com>` / `chore: initial import`。
5. **早退路径不清理临时根**（preflight 不合格、写文件失败都直接 `return 1`），于是 `$TMPDIR`
   里躺着上一次运行留下的 `letitgo-eval-*`，里面是**旧格式的 seed**。一条 05 的臂 `ls $TMPDIR`
   翻到了它，再顺着找到仓库。现在清理挂在 `defer` 上。

修完之后的 `04` 六条臂**没有一条带污染标记**。

### case 04：区分点收窄到检查点，而且这次是 3/3 vs 0/3

`without_skill` 三次都**只挂同一条断言**：「串行批次产生了检查点，且落在
`requirements/<scope>/issues/` 下」；`with_skill` 三次都产出了检查点。批次状态是这套技能
唯一稳定的区分点——和 iteration-4 的结论一致，但那次是单次运行，而且当时 fixture 还在
自己规定 scope 形状。

其余断言（门禁、防篡改、分支形状、不越界、批末 push）两边都能过：**它们是护栏，不是区分点。**

### case 05：没加载技能的臂不做规划，加载了技能的臂停下来问人

`without_skill` 7/9，挂的正好是两条**规划**断言：没产出 PRD、没产出 issue 卡。它把代码做对了
（阈值可配置、回退默认、门禁绿），但直接从「一句话诉求」跳到写代码。

`with_skill` 第一次只有 **5/9、30.6s、12 次工具调用**——它按 `/prd` 把 4 个带推荐答案的澄清
问题**用散文写出来，然后结束回合等人回答**。headless 里没有人在场，运行就到此为止。

**这不是技能被用错了，是技能漏了一种环境**：`ask_user_question` **根本不在 headless 的工具
列表里**（实测：让一条 headless 会话列可用工具，里面没有它——headless 刻意不带 Host / 浏览器
插件）。而 `/prd` 当时只说了「澄清必须在能问到人的上下文里做」，没说「问不到人时该怎么办」。
停在「等你回复」上是唯一一定错的做法。已补上（见下）。

### 一个后台子代理吃掉了整个运行

`04/with_skill` run1 停在 8/9，唯一没过的断言是它自己在结尾说的「收到结论后继续批末收尾与 push」。
事件流写得很清楚：

```
thinking: Still running. I'll wait. I need to end the turn.
text:     （等待后台评审返回，收到结论后继续批末收尾与 push。）
status:   turn_end reason=completed
```

它按 `/review-it` 把批末对抗性评审派给一个全新子代理——**做法是对的**——然后结束回合等它。
DSH 的 `subagent` 默认后台跑，而后台子代理**不会让本回合保持忙碌**：交互式会话里完成通知会
唤醒它，headless 里进程先退出了。批末收尾与 push 都没发生。

### 成本

| | with_skill | without_skill |
|---|---|---|
| 04 平均耗时 | 288.3s | 100.9s |
| 04 平均 tokens | 2,310,418 | 863,438 |
| 05 耗时 / tokens | 446.0s / 3,782,560（污染轮，仅作量级参考） | 105.8s / 485,540 |

技能让它多花 2–8 倍。换来的是**批次状态**与**规划产物**——单次小改动不值（iteration-1…3
已经说明），有依赖边的批次与没成形的诉求值。

### 这一轮改了什么

- `57ae748` — **要拿到结果才能继续时传 `run_in_background: false`**。`review-it`、`loop-it`、
  `walkthrough`、`graph` 各自在它规定的委托旁边写了这一条。`graph` 的波级派发本来就用
  `workflow`（自己 await 全部 thunk），所以没有这个问题。
- `prd` — **澄清用 `ask_user_question`，不要用散文；问不到人就不要停。** 工具不在列表里
  （无人值守部署）、调用被拒（子代理）、或用户已经说了「怎么落地你定」，三种情况都**自己定、
  写进 PRD、标 `[Assumption]`，照常产出**。
- `670481c` — 早退路径也清理临时根（`defer`）。

## iteration-10：修完之后复测，5 条臂并发跑

针对**修完上述三条之后的技能集**（`prd` 的「问不到人就别停」、`review-it`/`loop-it`/`walkthrough`/
`graph` 的 `run_in_background: false`）。5 条臂**并发**跑，**9 分 38 秒**跑完（串行要约 25 分钟）。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 04-serial-batch | 9/9、9/9、9/9 → **1.000** | 0.889（iteration-9 的 3 次，未重跑，见下） | **检查点** |
| 05-full-pipeline | **9/9** | 7/9 | **PRD + issue 卡** |

**没有一条带污染标记，也没有一条读到评测仓库**（逐条 grep `workspaces/github/let-it-go`：全 0）。

`04/without_skill` 没有重跑：它不加载任何技能，上面那三处修改不可能影响它，而 iteration-9
的 3 次是干净的。把技能无关的数字重测一遍只是烧时间。

### 三条修改各自被验证了

- **`04` 的 push 断言 3/3 通过**（iteration-9 是 2/3）。run1 那次失败的原因已经查清——臂把批末
  评审派成后台子代理后结束回合等人——所以 `run_in_background: false` 这条写进技能之后，
  它就该稳定通过。现在确实稳定了。
- **`05/with_skill` 从 5/9 到 9/9**，而且不是靠"少做"拿到的：它走完 `prd → to-issues → loop-it
  → review-it`，产出 `documents/prd-per-warehouse-thresholds.md`、两张 issue 卡、
  `records/2026-09-27-delivery.md`。**全程没有停下来等人**——它把每个决定做出来、写进 PRD，
  继续往下走，正是新补的那条规则要求的行为。
- **对抗性评审真的抓到了东西**：第一轮评审发现 `encoding/json` 把 JSON `null` 解成 int `0`
  且**不报错**，于是 `{"beijing": null}` 让该仓库**永不告警**——比崩溃更危险。臂改成按值严格
  校验并补了回归锁。这是「批末必须派一个独立评审者」这条规矩第一次被真实数据支持。

### 并发跑的两个前提

1. **每条臂要有自己的 `TMPDIR` 与 `GOCACHE`。** 串行时臂的私有临时根是 `$TMPDIR` 下唯一的
   一个，看不见彼此；一旦并发，一条 `ls $TMPDIR` 就能看到别的臂**正在做的解**——那正是
   iteration-8 里「抄了另一条臂的检查点」的失败模式。现在 `runHeadless` 把两者指到
   `<臂的根>/tmp`。放在臂自己的根下面（而不是另找一处）是为了不改沙箱的可见范围。
   `workspace_clean` 相应把 `tmp` 加进 `allowedInRunDir`，否则每条臂都会被误报越界。
2. **timing 不再可比。** 并发会抢 CPU 与 API 速率，`duration_ms` 虚高（上表 04 三次
   343s / 523s / 576s 的差距就是这么来的）；**token 与分数不受影响**。
   **要拿 timing 下结论，那一轮就串行跑。**

## iteration-11：补齐护栏与例外路径，又抓到一条持久泄漏

8 条臂并发，**8 分 56 秒**。这一轮第一次跑 **06-exception-path**，并把 01/02/03 在新隔离下重测。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 01-single-unit | 6/6 | 6/6 | 无（护栏，符合预期） |
| 02-mid-flight-change | 7/7（**当轮污染，见下**；iteration-12 复测 7/7） | 7/7 | 无（护栏，符合预期） |
| 03-artifact-handoff | 6/6 | 6/6 | 无（护栏，符合预期） |
| 06-exception-path | 7/9 | 6/9 | **检查点**；例外分支两条都没走 |

01/02/03 三个单单元用例**两条臂完全一样**，这是设计如此——它们守的是「技能别把简单事做复杂」，
不是区分点。真正有区分度的仍是 04（批次状态）、05（规划产物）、06（失败留档）。

### 新泄漏：`~/.dsh/sessions/` 的目录名就是答案键

`02/with_skill` 被标记污染，而它的 tool_result 里**没有** `evals/...` 字样——线索在 `thinking` 里：

> There are prior eval sessions under /Users/mervyn/workspaces/github/let-it-go-evals/results/...
> the session dir names reveal eval variants.

DSH 把每个会话存在 `~/.dsh/sessions/<cwd 的 slug>/`，而 **slug 就是 cwd**。工作树还在
`evals/results/` 里那几轮（iteration-6/7/8），会话目录名直接是：

```
--Users-mervyn-workspaces-github-let-it-go-evals-results-iteration-8-04-serial-batch-without_skill-work--
```

**仓库路径、用例号、臂名、第几次，全在里面，而且永远不会自己消失。** 一共 16 个这样的目录，
已删（用户自己的会话没动）。三处修：

1. 临时根前缀改成中性的 `cache-` / `spill-`——臂自己的会话 slug 从此与任何临时目录无法区分。
2. **`.dsh/sessions` 加进污染标记**：DSH 没有可配置的会话存储根（`DSH_SNAPSHOT_SESSIONS_ROOT`
   只是测试用的），所以**会话记录仍然共享且可读**——读到就必须报出来，不能静默。
3. 历史泄漏目录清掉。

### case 06：例外路径写在技能里，但两条臂都没走

| 断言 | with_skill | without_skill |
|---|---|---|
| 门禁绿 / 阈值生效且仍严格小于 / 留在需求分支上 | ✓ | ✓ |
| **打回的 issue 挪到它自己的分支上留档** | ✗ | ✗ |
| **检查点把 issue-002 记成 `failed` 并写下它的分支** | ✗ | ✗ |
| 产生了检查点 | ✓ | ✗ |
| 不落 `tasks/`、防篡改、不越界 | ✓ | ✓ |

`with_skill` 的臂**认出了冲突**（issue-002 要求含等于，冻结基线断言严格小于，同一个调用结论相反）、
**没有改冻结文件**、也**记了 `failed`**——但它把留档 commit 留在需求分支上，`branch` 写的是
`feat/stock-tweak`，没开 `feat/issue-002-*`。

**这是措辞的漏洞，不是它的判断错。** 技能正文把触发条件写成「**打回或重做**的 issue」，而它认为
自己是在「等用户裁决」；查找表 `references/error-recovery.md` 里 `issue_unclear` 那一行的恢复策略
写的又是「跳过，标记 `failed`」——**没有留档这一步**。两处合起来正好得出它做的事。

改法（`loop-it` 正文 + 查找表）：**触发条件是状态，不是措辞**——凡是记成 `failed` 的（打回、重做、
与冻结基线冲突、信息不足），一律挪到 `feat/issue-N-slug` 留档并把该分支写进检查点 `branch`；
查找表新增 `spec_conflict` 一行。

## iteration-12：两条臂复测

| 用例 | with_skill | 结果 |
|---|---|---|
| 02-mid-flight-change | 7/7 | 干净（iteration-11 那条污染已作废） |
| 06-exception-path | **9/9** | 干净 |

06 复测的臂开了 `feat/issue-002-inclusive` 并推到 origin，检查点里
`issue 2: status=failed, branch=feat/issue-002-inclusive, error_class=spec_conflict`——
用的正是新加的那个类别。两条臂都没有碰 `~/.dsh/sessions`，也没有读到评测仓库。

> 06 的 `without_skill` 用的是 iteration-11 的 6/9（当轮干净）。它不加载技能，这次修改不可能影响它。

## iteration-13 / iteration-14：`graph` 第一次被测

新用例 `07-parallel-waves`：三个工作单元，两个互不依赖（`inventory.Reorder` / `pricing.BulkTotal`），
第三个依赖前两个（`report.LowStockLines`）。**`graph` 是这套技能里唯一零覆盖的一个**——worktree
隔离、波分层、`workflow` 派发、fan-in 屏障、`graph.html` 看板，前面六个用例一个都没碰到。

### iteration-13：作废——fixture 有缺陷，不是臂做错了

首跑 `with_skill` 8/10、`without_skill` 5/10，**两条臂都挂在同一条断言上**：`tamper_guard`。

原因不在臂：**两条臂都把新测试追加进了现有测试文件**（`inventory/inventory_test.go`、
`pricing/pricing_test.go`）——那是完全正常的 Go 习惯。而 `tamper_guard` 比的是**整文件字节**，
于是「追加一条测试」与「把测试改弱」在它眼里是同一件事。**又是 case 01 那个病：断言要求了
任务从没说的事。** 04 与 06 有同一个潜在陷阱，只是碰巧没遇上会追加的臂。

修法：**七个 fixture 的 `AGENTS.md` 都声明这条约定**——现有的 `*_test.go` 是冻结的验收基线，
逐字节不许改；要为新行为写测试就**新建一个文件**，不要往已有测试文件里追加（追加同样会改哈希）。
约定说清楚，守卫才是公平的。

同一条 `waves` 断言也错了，而且错得更有意思：它从检查点里读 `waves`。但技能要求在下一个波之前
用 `--keep-shipped --only-pending` 重规划，而那次重规划**只重排还没交付的节点**——实测最终检查点里
`waves` 只剩 `[[3]]`，已交付的 1、2 不在里面。**技能从没承诺检查点保留历史分层。** 改成看
**合并形状**：一个 merge 提交同时含两条节点分支的祖先，就是它们被一起集成的证据。同一条工作树
复打分：8/10 → 9/10。结果文件已删。

### iteration-14：干净数据，**10/10 vs 6/10**

| 断言 | with_skill | without_skill |
|---|---|---|
| 门禁绿（集成态）· 三个单元都实现 · 不落 `tasks/` · 防篡改 · 不越界 | ✓ | ✓ |
| **图检查点落在作用域根** | ✓ | ✗ |
| **`graph.html` 看板渲染出来** | ✓ | ✗ |
| **两个独立节点在同一个集成点汇合** | ✓ | ✗ |
| **每个节点记了自己的 `feat/` 分支** | ✓ | ✗ |
| 节点分支都并进最终状态 | ✓ | ✓（空集，真空真） |

**4 分差距，是七个用例里最大的**，而且区分点全部落在 graph 那台机器上：检查点、看板、波分层、
worktree 隔离。`without_skill` 把三个函数都写对了（它们不难），但**一点图都没有**——它就是串行做完了。

`with_skill` 的真实形状：三条 `feat/node-*` 分支；`wave-0-low-stock-reorder` 上先
`merge(wave-0): node-1` 再 `merge(wave-0): node-2`（两条独立节点在同一个集成点汇合），
然后才 `merge(wave-1): node-3`；`.graph_state.json`、`graph.html`、`nodes.json`、走查件与
交付记录都落在 `requirements/001-low-stock-reorder/`。

两条臂都没有污染标记，也都没有读到评测仓库。

> 顺带验到了另一件事：走查件在**折进 `ship-it` 之后仍然产出**
> （`notes/walkthrough-low-stock-reorder.md`）——删掉那个技能没有丢掉那个能力。

### 07 怎么跑

它和 01/02/03 一样属于**按需**：一次 `with_skill` 要付三次子代理生命周期（实测 210.8s /
1,568,225 tokens），不该每轮都跑。**改动 `graph` 之后必须跑它。**

## iteration-15：`08-undeclared-workspace`——唯一没被走过的设计约定

仓库的约定是「**工作区说作用域根在哪，流程决定里面长什么样**」。七个 fixture 全都声明了根，
七个用例还都断言 `tasks` 不存在——所以这条约定的**另一半**（「仓库完全没声明时退到默认的
`tasks/<feature>/`」）从来没被走过，而且去掉声明之后现有用例反而会**罚**它。

`08` 与 `05` 是**受控对照**：同一份代码、**prompt 逐字相同**，唯一变量是工作区有没有声明根。
`05` 期望落在 `requirements/`，`08` 期望落在 `tasks/`。

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 08-undeclared-workspace | **7/7** | 6/7 | **PRD 落在默认根** |

**兜底路径是对的**：`with_skill` 把资料放在 `tasks/warehouse-thresholds/`（`documents/prd-*.md`
+ `notes/walkthrough-*.md`），**没有**凭空发明 `requirements/`，门禁绿、Makefile 未动。
`without_skill` 只写了代码，一点规划产物都没有。

为了让它能跑，harness 里两处**把 fixture 的事实写死**的地方得挪开——两处是同一个错误：

- `assertCheckpointLocation` 把 `requirements` 硬编码成 `parts[0]`。按上面那条约定，根是**仓库的
  事实**，所以现在从断言里读可选的 `root`（默认不变）。
- 自检**要求每个 fixture 都有 `AGENTS.md`**（理由：fixture 自己的地图也是被测对象）。对七个用例成立，
  对这个不成立，所以改成 `case.json` 里显式写 `"undeclared_workspace": true`——而不是删掉那条检查，
  误丢地图仍然会在自检里报出来。

`tamper_guard` 只冻 `Makefile`：这个 fixture 没有 `AGENTS.md`，也就**没有任何地方说过**现有
`*_test.go` 是冻结基线——case 07 正是在这里栽的，守卫不能罚一条没声明过的约定。

### 顺手修掉一条罚了正确行为的断言（case 05 与 08）

首跑 `08/with_skill` 是 7/8，挂的是「流程自己走了 `to-issues`」。**臂当场把它驳回了**：

> `to-issues` 有规模下限规则——一个上下文窗口装得下就直接内联——这个改动确实装得下，所以没造 issue 卡。

它引对了。`to-issues` 第 26 行与第 303 行都写着：

> **规模下限：** 如果整个改动一个上下文窗口就装得下，你根本不需要 issue。直接说明，然后就地实现

这条任务确实装得下，**不造卡是照技能做**。断言在要求技能明确允许跳过的东西——又是 case 01 那个病。

**case 05 有同一条断言**，只是那次的臂碰巧造了卡才没暴露。两个用例的 prompt 逐字相同、任务规模相同，
所以取舍也相同：一起删掉。两条都**用已有工作树重打分**，没有重跑：

| 用例 | 改前 | 改后 |
|---|---|---|
| 05-full-pipeline / with_skill | 9/9 | **8/8** |
| 05-full-pipeline / without_skill | 7/9 | **7/8** |
| 08-undeclared-workspace / with_skill | 7/8 | **7/7** |
| 08-undeclared-workspace / without_skill | 6/8 | **6/7** |

**05 的区分度从 2 分收窄到 1 分**（0.778 → 0.875），因为去掉的是一个**假区分点**：它区分的是
「臂这次有没有顺手造卡」，不是技能。剩下的区分点就是它一开始要测的**规划半边**。

## iteration-6：一个负结果——fixture 在替技能干活

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 05-full-pipeline | 9/9 | 9/9 | **无** |

这一轮**把 case 05 的区分点跑没了**，但原因不在技能：**fixture 自己把 scope 的内部形状
规定死了**。五个 fixture 共用一份 `AGENTS.md` + `requirements/README.md`，里面写着
`documents/prd-<feature>.md`、`issues/issue-NNN-<slug>.md`、`notes/`、`records/`，
连「loop-it 的检查点 `.loop-state.json` 就在这一层」都写了。

一旦 fixture 的 `AGENTS.md` 会**自动加载**（headless 让这件事变成默认），任何称职的 agent
都会照着产出那些路径——**用不用技能都一样**。于是「有没有 PRD」测的不再是技能，
而是「agent 会不会读 AGENTS.md」。两条臂都 9/9。

顺带发现 fixture 的 `AGENTS.md` 通篇在说「一个小而完整的 **Python** 服务」、`tests/`（unittest），
而五个 fixture 全是 Go。有一条臂专门花力气指出了这个矛盾。

修法（`b68dc6d`）：fixture 现在**只声明作用域根**，scope 里面怎么组织交给流程自己定——
这正是我们定下的分工：**工作区说 scope 在哪，流程决定里面长什么样**。
副产品是 case 04 的检查点断言也重新变成真的测量。

> 这一轮是**旧 fixture** 下跑的，留着当负结果；不要拿它跟 iteration-7 比分数。

**顺带测到了成本**（这是第一次有真 timing）：同样 9/9，`with_skill` 用了
**221.7s / 2,432,199 tokens / 53 次工具调用**，`without_skill` 只用
**147.6s / 1,177,659 tokens / 42 次**。**技能让它多干了一倍的活，换来的分是一样的。**
这条不能直接推广（旧 fixture、单次运行），但它说明「技能有没有用」不能只看通过率——
还得看它多花掉多少。

## iteration-5

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 05-full-pipeline | 8/9 | 7/9 | **PRD** |

**这是第一个测到规划半边的用例**——前面四个全部从流水线中段进入，需求是我给到手里的。

prompt 只给一个没成形的诉求（「我们要能按仓库配低库存阈值……怎么落地你定」），fixture 里没有
需求资料、没有 issue 卡、没有 PRD。两条臂都自己建了 scope 目录与 issue 卡，**但只有
`with_skill` 产出了 PRD**：

- `with_skill`：scope README + `documents/prd-*.md` + issue 卡 + `notes/walkthrough-*.md`
- `without_skill`：scope README + issue 卡（没有 PRD，也没有走查件）

### ⚠️ 这条用例的探针是坏的（我的设计错误）

两条臂都挂在「阈值真的能按仓库配置」上，但**不是它们做错了**：prompt 说「怎么落地你定」，
于是两条臂都选了 `config/low_stock_thresholds.json`（不是探针写死的 `config/thresholds.json`），
其中 `with_skill` 还用 `go:embed` 把配置编译进二进制——**探针「写配置文件再观察」的做法
对 embed 实现根本不成立**。

修法：要么让任务**把机制定下来**（加一条验收条件：「运维改配置后不重新构建就生效」——
这本来就是真实诉求），要么让探针去 `config/` 下自己找那份配置。前者更诚实：**探针能测什么，
取决于任务有没有把验收条件说清楚**，而不是取决于实现者挑了什么机制。

这条断言对两条臂**同等失效**，所以 PRD 那个区分点仍然成立。

## iteration-4

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 04-serial-batch | 7/7 | 6/7 | **检查点** |

**这是第一个测出技能价值的用例。** 两条臂在工程行为上完全一样——三条行为都实现、
三条 stacked 分支都推到 origin、门禁绿、防篡改过、不越界写入。差别只有一处：

- `with_skill` 建了 `requirements/01_REQ-stock-batch/issues/.loop-state.json`，
  三条 issue 各有 `status` / `branch` / `evidence`（4、3、4 条，按验收条件逐条对应），
  并用 `.git/info/exclude` 把它排除出版本库
- `without_skill` 什么都没留

**没有检查点，中断一次就得从头判断「哪些做完了、证据在哪」。** 这正是这套技能设计上
最该做的事，也是前面三个用例**测不到**的东西——因为那三个都是单单元任务，正好绕开了它的机器。

**结论修正**：不能说「技能没有可测价值」。准确的说法是——**技能的价值在批次状态上，
而不在单次改动的质量上**。用例选单单元，就永远测不出来。

## iteration-1 … iteration-3

三条真实运行，每条两臂、各一次。**结论：只有一个断言区分得出技能的价值。**

| 用例 | with_skill | without_skill | 区分点 |
|---|---|---|---|
| 01-single-unit | 6/7 | 5/7 | 需求资料落点 |
| 02-mid-flight-change | 7/7 | 7/7 | 无（护栏） |
| 03-artifact-handoff | 6/6 | 6/6 | 无 |

读法：

- **case 03 是唯一对「PRD 该不该留」有回答力的**：一个没有任何上下文、也没加载技能的会话，
  只凭上一个会话留下的 `requirements/<scope>/` 就把待办的 issue-002 做对了。
  **那份资料是可用的契约**——所以该留，但留住的是**字段结构**（范围/已交付/未交付/关键决定/未决问题），
  不是「等人批准」这道闸门。
- **三个用例都是单单元任务**，所以「技能没有可测价值」这个读法**不成立**：
  这套流程真正的机器（loop 检查点、串行批次、follow-up 增补、graph 并行）**一个都没测**。
  要下结论，先补那几条用例。
- 两条臂的工程行为（门禁、防篡改、按变更调整、越界写入）在三个用例里**完全一样**。

## ⚠️ iteration-1 … iteration-5 的收集条件

这几轮的分数**不能与 iteration-7 直接比**，两处条件都变了：

- **臂是手工派子代理跑的。** `subagent` 工具没有 cwd 参数，臂继承父会话 cwd，
  fixture 的 `AGENTS.md` **不会自动加载**，只能在 prompt 里显式指认它。
  现在改成 `dsh --profile headless`，cwd 就是铺出来的 fixture，约定自动生效。
- **fixture 当时自己规定了 scope 的内部形状**（见 iteration-6）。
- 没有 timing：那时 tokens / duration 只在子代理通知里出现一次，没当场落盘，
  所以那几轮 benchmark 里的用时与 token 都是 0。**现在由 `evalctl run` 自己采。**

结论的方向仍然可以读（技能的价值在批次状态、在 PRD 的产出），但**分数要重测**——
iteration-7 就是重测。

## 关于 iteration-0-smoke

harness 刚搭好时用「参考解的真实 grading + 一条手工造的 without_skill」做过一次冒烟，
用来验证 `bench` 的汇总与 analyst pass。**那份数据是编的，已经删掉**——不能跟真实运行
混在一起当证据。

## 每条臂要留什么

- `grading.json` — 从**外部**打的分（断言、证据、通过率），不是臂的自述
- `timing.json` — 耗时 / token / 工具调用，由 `evalctl run` 从 `dsh --json` 的事件流里采
- `benchmark.json` / `benchmark.md` — 该轮的汇总（在 iteration 目录下）
- `notes.md` — 臂最后说了什么；以及**断言无效**的原因（例如 Lead 在跑臂期间改了仓库）
- `work/` — 臂的工作副本，scratch，不进库；分数在 `grading.json` 里，产物在 `work/` 里

⚠️ **跑臂期间冻结 harness 与技能集。** `workspace_clean` 已经不量环境仓库了（它只看 fixture 的
父目录，见 iteration-7 第 2 条），所以顺手改仓库不再污染分数。**但改 `evals/harness/` 或重新安装
技能仍然会污染**：`go run` 每次调用都重新编译，所以同一条命令里的第 3 条臂可能跑的是你刚改完的
代码；技能则是在臂启动时从 `~/.agents/skills/` 读的。要改，就等这一轮跑完。
