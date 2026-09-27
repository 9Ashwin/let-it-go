# 怎么跑一轮 eval

一轮 = **每轮必跑的两条用例**（`04-serial-batch`、`05-full-pipeline`）× 两条臂，
各跑一次，然后从外部机械核对。

只有那两条在量技能的价值——实测里两条臂的分数**不同**。其余三条
（`01-single-unit`、`02-mid-flight-change`、`03-artifact-handoff`）是护栏，
各自护着一条不同的路径，**改了对应路径才跑**（见 [README 的用例表](../README.md#用例)）。
每轮全跑要 40–70 分钟，而其中三条的结论永远是「两条臂一样」。

- `with_skill`：正常目录 + prompt 后缀「先加载并遵循 let-it-go 里对应的技能」
- `without_skill`：同一 prompt + 后缀「不要加载任何技能，凭你自己的判断做」

两条臂**只有最后一行不同**，否则测的就不是技能，是 prompt 差异。后缀写在
[`arms.json`](../arms.json)，改一处就改了所有用例的两条臂。

---

## 一条命令跑一条臂

```bash
go -C evals/harness run . run 05-full-pipeline --arm with_skill \
    --out results/iteration-6/05-full-pipeline/with_skill \
    --dsh /path/to/dsh
```

它按顺序做四件事：

1. **materialize** 到 `<out>/work`——复制 fixture、`git init`、打 seed commit、
   建一个本地 bare origin（`loop-it` 的串行前置会跑 `git ls-remote origin`，没有它跑不起来）。
2. **preflight**：起点必须是红的（fixture 自己的门禁绿 + 探针红）。不红就直接停——
   一个在开跑之前就已经满足的用例，之后无论跑成什么样都测不出这条臂做了什么。
3. **让 dsh 把任务做完**：`dsh --profile headless --json "<prompt>\n\n<suffix>"`，
   **cwd 指到 `<out>/work`**。
4. **从外部打分**：`grade` 的结果写进 `grading.json`，耗时与 token 写进 `timing.json`，
   臂最后说了什么写进 `notes.md`。

`--out` 的相对路径以 `evals/` 为基准。加 `--keep` 就不清掉已有的 `work/`；
`--regrade` 不重跑 dsh，只对已有的 `work/` 重新打分并重生成交付件（改了探针/断言之后用——
臂的产物没变，变的是量它的那把尺子）。

### 跑多次求方差

**一条臂只跑一次，分不清「技能更强」还是噪声。** 第 2 次起目录名带 `-runN` 后缀、
并传 `--run N`；`bench` 会把它们归到同一个 configuration 下，报 mean ± stddev：

```bash
for c in 04-serial-batch 05-full-pipeline; do
  for arm in with_skill without_skill; do
    for k in 1 2 3; do
      d="results/iteration-N/$c/$arm"; [ "$k" -gt 1 ] && d="$d-run$k"
      go -C evals/harness run . run "$c" --arm "$arm" --out "$d" --run "$k" --dsh /path/to/dsh
    done
  done
done
```

### 并发跑：能省一大半时间，但别拿 timing 下结论

臂之间没有共享状态（各自的 `--out`、各自的私有临时根），所以可以一起跑。上面那个三重循环
把 `go -C evals/harness run . run …` 加个 `&`、末尾 `wait` 就行：5 条臂从约 25 分钟降到
**9 分半**（等于最慢那条，而不是总和）。

**两条前提：**

- **`TMPDIR` 与 `GOCACHE` 已经按臂隔离**（`runHeadless` 指到 `<臂的根>/tmp`）。串行时臂的
  临时根是 `$TMPDIR` 下唯一的一个，看不出问题；并发时不隔开，一条 `ls $TMPDIR` 就能看到
  别的臂**正在做的解**——iteration-8 的「抄了另一条臂的检查点」就是这么发生的。
- **timing 不再可比。** 并发抢 CPU 与 API 速率，`duration_ms` 虚高；**token 与分数不受影响**。
  要用耗时下结论，那一轮就串行跑。

### 给人看：skill-creator 的 eval viewer

`run` 会为每条臂写 `eval_metadata.json`（prompt）与 `outputs/交付件.md`（任务 + 改了什么 +
需求资料带路径 + 逐条分数 + 臂最后说了什么）——viewer 的契约是「**含 `outputs/` 的目录
就是一个 run**」，它读这两样。所以别删 `outputs/`，否则那一条就看不见了。

```bash
$PY ~/.agents/skills/skill-creator/eval-viewer/generate_review.py \
    evals/results/iteration-N --skill-name flow --static /tmp/review.html
```

⚠️ 要用 **Python 3.10+**：系统 `python3` 是 3.9，viewer 直接挂在 `dict | None` 上。
bundled runtime（3.12）在 `~/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3`。

### 前提：一个 dsh 可执行文件

`run` 按 `--dsh` → `$EVAL_DSH` → `PATH` 里的 `dsh` 的顺序找。本机没有装 dsh 命令，
需要先把这个 checkout 构建出来：

```bash
cd ~/workspaces/github/deepseek-harness && pnpm install && pnpm build
```

入口是 `apps/cli/lib/bin.js`（**不是** `apps/cli/lib/index.js`——构建不会产出那个名字，
第一次找错就卡在这里）。它是本仓库之外的东西、路径随环境变，所以不写死进 harness，
用包装脚本指过去：

```sh
#!/bin/sh
exec /opt/homebrew/bin/node "$HOME/workspaces/github/deepseek-harness/apps/cli/lib/bin.js" "$@"
```

## 为什么这条路对了，而手工派子代理不对

headless profile **从进程的 cwd 出发**——铺出来的仓库就是它的工作目录。于是：

- fixture 自己的 `AGENTS.md` **自动加载**。实测：在一个只有 `AGENTS.md` 的目录里让它
  复述约定里的暗号，它复述了，还自己指出「这个目录不是 git 仓库」。
- `~/.agents/skills/` 下的技能**照常发现**。实测：它能列出技能名，`loop-it`、`prd`、
  `to-issues`、`review-it`、`walkthrough` 都在里面。
- `--json` 的事件流里 `status/step_end` 带 `usage`，token 从那里累加；wall clock 自己计时。
  **`timing.json` 不再是永远的 0。**

手工派的代价（留个记录，别再走回去）：`subagent` 工具**没有 cwd 参数**，臂继承父会话的
cwd，仓库约定根本不生效，只能在 prompt 里手动指认 `AGENTS.md`；派出去的臂**寻址不到**，
没法中途递东西进去；而且它们**会静默消失**，消失后没有痕迹可查。

## 中途变更与澄清：还没验证

headless 一个任务跑完就退。`--session-id <id>` 可以接回同一个会话再跑一个任务——
这是「中途变更」的路径，**但还没实测**，别在结论里当成已验证。

无人值守的 headless 也**没人可问**。所以「有不懂的先问」落不到实处，臂只会带着假设继续。
判定要看**结果对不对**（探针），以及**它留下了什么**（决策记录、假设标注、未决项），
而不是看它有没有问。

## workspace_clean 现在看哪里

它检查的是 **fixture 的父目录**（harness 自己的运行目录）有没有多出臂留下的东西。

早先的版本拿**环境里那个 let-it-go 仓库的脏状态**当基准——那是个坏设计：DSH 自己的
`benchmarks/AGENTS.md` 明说「不要用 ambient repositories」，量出来的东西取决于你此刻在
工作区里改了什么，而不是臂做了什么；它也确实两次把 Lead 的动作记成臂的越界。
现在跑臂期间改仓库**不再影响**这条断言。

## 机械核对

断言全部在这个脚本里跑，**不读臂的自述**。`run` 已经替你做了，单独跑是为了复核或重打分：

```bash
go -C evals/harness run . assert 05-full-pipeline results/iteration-6/05-full-pipeline/with_skill/work \
    --phase grade --out results/iteration-6/05-full-pipeline/with_skill/grading.json
```

## 汇总

```bash
go -C evals/harness run . bench results/iteration-6 --skill-name flow
```

出评审页见上面「给人看：skill-creator 的 eval viewer」。

---

## 跨会话交接：`03-artifact-handoff`

这条用例回答「flow 该不该有 PRD」。别的用例只查「需求资料有没有落盘」，查不出它是不是
《Plan mode is dead》说的那种「没人愿意读的 AI 文本」。

做法：fixture 里**种着**一份 `requirements/<scope>/`（README 写了范围/已交付/未交付/关键决定，
`issues/` 里有待办的 issue-002），代码是 issue-001 已交付的状态。臂的 prompt 只指认那个目录：

> 这是上一个会话留下的需求资料：requirements/01_REQ-low-stock-threshold/。
> 按它把还没做完的做掉。有不懂的先问，别猜。做完跑一遍门禁确认没弄坏。

**关键在于臂拿不到别的东西**：没有 PRD 之外的任务描述，没人告诉它 issue-002 是什么。
它只能靠那份资料。做得对 = 资料是可用的契约；做不对或卡住 = 那份资料只是没人读的文本。

判定看的是**结果对不对**（探针），不是它有没有问——见上面「没人可问」那条。

## 命名与落点

```
results/iteration-N/<case-id>/<arm>/grading.json   ← 从外部打的分（证据）
results/iteration-N/<case-id>/<arm>/timing.json    ← 耗时 / token / 工具调用
results/iteration-N/<case-id>/<arm>/notes.md       ← 臂最后说了什么（`-` 开头的行会被 bench 收进 notes）
results/iteration-N/<case-id>/<arm>/work/          ← 臂的工作副本，scratch，不进库
results/iteration-N/benchmark.json / benchmark.md  ← bench
```

`results/` **进版本库**——结果就是证据。`work/`、`work.origin.git`、`work.seed.json`
是 scratch（整个仓库副本 + `.git` + 本地 origin），在 `.gitignore` 里排掉；
留在原处是为了复核：分数在 `grading.json` 里，产物在 `work/` 里。

## 加一个用例

1. `cases/<id>/fixture/` 放纯文件（**不要带 `.git`**，嵌套仓库无法入库），
   里面写一份 `AGENTS.md` 声明它自己的作用域根与门禁——这就是被测的「仓库地图」。
2. `cases/<id>/probe/` 放**只观察不判断**的探针（打印实际生效的值）。
3. `cases/<id>/case.json` 写 prompt、断言、`tamper_guard`。
4. 用一个参考解跑一遍，确认能全绿；再确认起点是红的（`run` 会自己卡这一步）。
5. 加负例：把 fixture 的门禁或断言改弱，确认 `tamper_guard` 会红。

⚠️ **探针能测什么，取决于验收条件有没有说清楚。** case 05 第一版没写配置放哪、
也没写「改配置不重新构建」，两条臂就各自挑了文件名、其中一条还把配置 `go:embed`
进了二进制——探针「写文件再观察」的做法直接失效。那不是臂的错，是任务没说清。
