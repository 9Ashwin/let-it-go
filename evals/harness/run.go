package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// Timing 是一次臂运行的开销。以前这里永远是 0：臂由人手派出去，时间和 token 没人记。
// 现在臂由本命令自己驱动，wall clock 由它计时，token 从 dsh 的 --json 事件里累加。
//
// 字段名跟着 skill-creator 的 `references/schemas.md`：`total_tokens` / `duration_ms` /
// `total_duration_seconds` 是它的 viewer 与 aggregate 脚本认的名字。多出来的
// `duration_seconds` / `tool_calls` 是我们自己 `bench` 用的，一并留着。
type Timing struct {
	TotalTokens          int     `json:"total_tokens"`
	DurationMs           int     `json:"duration_ms"`
	TotalDurationSeconds float64 `json:"total_duration_seconds"`
	DurationSeconds      float64 `json:"duration_seconds"`
	ToolCalls            int     `json:"tool_calls"`
	RunNumber            int     `json:"run_number"`
}

// cmdRun 跑一条臂：把用例铺进一个受控目录，让 `dsh --profile headless` 在那里把任务做完，
// 再从外部给结果打分。
//
// 这一步之所以成立，是因为 headless profile 从**进程的 cwd** 出发：铺出来的仓库就是它的
// 工作目录，仓库自己的 AGENTS.md 会被自动加载，`~/.agents/skills/` 下的技能也照常被发现。
// 之前靠手工派子代理，工作目录由调用方决定、改不了——仓库约定根本不生效，子代理还会静默消失。
func cmdRun(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: evalctl run <case-id> --arm with_skill|without_skill --out DIR [--dsh PATH] [--keep|--regrade]")
		fmt.Fprintln(os.Stderr, "  --out 的相对路径以 evals/ 为基准，惯例是 results/iteration-N/<case-id>/<arm>")
		fmt.Fprintln(os.Stderr, "  --regrade 不重跑 dsh，只对已有的 work/ 重新打分并重生成人看的交付件")
		fmt.Fprintln(os.Stderr, "  --run N 这是同一条臂的第几次运行（第 2 次起目录名带 -runN 后缀）")
		return 2
	}
	caseID := args[0]
	arm, out, dshPath, keep, regrade := "", "", "", false, false
	runNumber := 1
	for i := 1; i < len(args); i++ {
		switch args[i] {
		case "--arm":
			i++
			if i < len(args) {
				arm = args[i]
			}
		case "--out":
			i++
			if i < len(args) {
				out = args[i]
			}
		case "--dsh":
			i++
			if i < len(args) {
				dshPath = args[i]
			}
		case "--run":
			i++
			if i < len(args) {
				fmt.Sscanf(args[i], "%d", &runNumber)
			}
		case "--keep":
			keep = true
		case "--regrade":
			regrade = true
		}
	}
	if arm == "" || out == "" {
		fmt.Fprintln(os.Stderr, "run: --arm 与 --out 都是必填")
		return 2
	}
	suffix, known := armSuffix(arm)
	if !known {
		fmt.Fprintf(os.Stderr, "run: arms.json 里没有这条臂：%s\n", arm)
		return 2
	}
	c, err := loadCase(caseID)
	if err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	out = repoPath(out)
	if err := os.MkdirAll(out, 0o755); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	if regrade {
		return regradeExisting(out, caseID, arm, c)
	}
	dsh, err := resolveDsh(dshPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	// 臂的工作树建在**仓库之外的私有临时根**里，不能待在 results/ 下：
	// 那样 `../../..` 就爬到 evals/ 了——用例定义（连断言一起）、arms.json、
	// 别的臂的 results/、harness 源码全在那里。实测有臂真的爬出去读了自己这一轮的
	// 期望值，还读到了别的臂的检查点。DSH 自己的 benchmarks/AGENTS.md 要求
	// private mkdtemp roots，就是为了这个。打完分再把树搬回 results/ 供复核。
	// 前缀要是**中性的**：DSH 把会话存在 `~/.dsh/sessions/<cwd 的 slug>/` 下，而臂能列这个
	// 目录——`letitgo-eval-` 这样的名字等于在臂自己的会话目录名里写着「你在被评测」。现在它
	// 与任何一个临时目录无法区分。代价是我也不能靠名字找残留根了，所以名字仍可 grep。
	root, err := os.MkdirTemp("", "cache-")
	if err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	// 清理必须挂 defer：早退路径（preflight 不合格、dsh 解析失败、写文件失败）原先
	// 直接 `return 1`，把临时根连同 `work.seed.json` 一起留在 $TMPDIR 里。实测有臂
	// `ls $TMPDIR` 翻到了上一次运行留下的 seed，读出 case_id，再顺着找到用例定义——
	// 隔离只挡住了「工作树周围」，挡不住「上一次没扫干净的地」。
	defer os.RemoveAll(root)
	work := filepath.Join(root, "work")
	_ = keep // 工作树现在每次都是全新的；留着这个旗标只为不改调用方
	if code := cmdMaterialize([]string{caseID, "--dest", work}); code != 0 {
		return code
	}

	// 起点必须是红的。探针在起点就是绿的，意味着这个用例在开跑之前就已经满足，
	// 之后无论跑成什么样都测不出这条臂做了什么——那是一条假证据。
	if p := preflight(caseID, work, c); !p.OK {
		os.WriteFile(filepath.Join(out, "preflight.json"), mustJSON(p), 0o644)
		if !p.ProbeRedAtSeed {
			fmt.Fprintln(os.Stderr, "run: 起点探针已经是绿的——用例还没跑就已经满足，测不出东西")
		} else {
			fmt.Fprintln(os.Stderr, "run: 起点不合格（fixture 自己的门禁在起点就该是绿的，见 preflight.json）")
		}
		return 1
	}

	// seed 文件落在 `work/` 的**上一级**，而臂的 cwd 就是 `work/`——一条 `ls ..`
	// 就看得见。它现在不再带 case_id（见 Seed 的注释），但文件名与 `protected`
	// 哈希仍然等于告诉臂「这是评测，去周围找找评分标准」。跑的时候把它挪到另一个
	// 临时目录，臂跑完再放回来：tamper_guard 与 workspace_clean 都要读它。
	secret, err := os.MkdirTemp("", "spill-")
	if err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	defer os.RemoveAll(secret)
	seedFile := work + ".seed.json"
	hiddenSeed := filepath.Join(secret, "seed.json")
	if exists(seedFile) {
		if err := os.Rename(seedFile, hiddenSeed); err != nil {
			fmt.Fprintln(os.Stderr, "run:", err)
			return 1
		}
	}

	prompt := c.Prompt + "\n\n" + suffix
	started := time.Now()
	events, finalText, rawEvents, runErr := runHeadless(dsh, work, prompt)
	elapsed := time.Since(started).Seconds()

	// 放回去再打分：tamper_guard 要读受保护文件的哈希，workspace_clean 要认这个目录。
	if exists(hiddenSeed) {
		if err := os.Rename(hiddenSeed, seedFile); err != nil {
			fmt.Fprintln(os.Stderr, "run:", err)
			return 1
		}
	}

	// 原始事件流落盘：超时或半途失败时，这是唯一能看出「它卡在哪一步」的东西。
	if rawEvents != "" {
		os.WriteFile(filepath.Join(out, "events.jsonl"), []byte(rawEvents), 0o644)
	}

	timing := Timing{
		TotalTokens:          events.totalTokens,
		DurationMs:           int(elapsed * 1000),
		TotalDurationSeconds: round(elapsed, 2),
		DurationSeconds:      round(elapsed, 2),
		ToolCalls:            events.toolCalls,
		RunNumber:            runNumber,
	}
	if err := os.WriteFile(filepath.Join(out, "timing.json"), mustJSON(timing), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	g := grade(caseID, work, c)
	if err := os.WriteFile(filepath.Join(out, "grading.json"), mustJSON(g), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	// 污染检查：臂不该碰到评测仓库的 evals/。隔离已经把工作树挪到仓库外，所以正常
	// 情况下这里永远是空的——但隔离一旦被改坏，这一轮必须自己喊出来，而不是静默变成
	// 一条「成绩很好」的假数据。实测过一次：4/8 条臂爬出去读了用例定义与别的臂的结果，
	// 其中一条靠抄别人的检查点拿到了满分。
	contaminated := contaminationIn(rawEvents)
	notes := runNotes(caseID, arm, dsh, finalText, events, elapsed, runErr)
	if len(contaminated) > 0 {
		notes += "\n- ⚠️ **这一轮污染了**：臂碰到了 " + strings.Join(contaminated, "、") +
			"——分数不可信，别用它下结论。\n"
		os.WriteFile(filepath.Join(out, "contaminated.json"), mustJSON(contaminated), 0o644)
		fmt.Fprintf(os.Stderr, "  ⚠️ 污染：臂碰到了 %s——这一轮的分数不可信\n", strings.Join(contaminated, "、"))
	}
	if err := os.WriteFile(filepath.Join(out, "notes.md"), []byte(notes), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	if err := writeReviewArtifacts(out, work, caseID, c, g, finalText); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	// 打分完了才搬回来：此时它已经影响不到任何一次运行。
	if err := parkWorkTree(work, out); err != nil {
		fmt.Fprintf(os.Stderr, "run: 搬工作树失败（不影响分数）：%v\n", err)
	}

	fmt.Printf("%s/%s  %.2f（%d/%d）  %.1fs  %d tokens  %d 次工具调用\n",
		caseID, arm, g.PassRate, g.Passed, g.Total, elapsed, events.totalTokens, events.toolCalls)
	if runErr != nil {
		fmt.Fprintf(os.Stderr, "  dsh 退出异常：%v\n", runErr)
		return 1
	}
	return 0
}

// runEvents 是从 --json 事件流里累加出来的东西。
type runEvents struct {
	totalTokens int
	toolCalls   int
	steps       int
}

// armTimeout 是一条臂跑到底的上限。300s 太紧——case 05 的正常运行已经到 221s，
// 再大一点的用例就会被误砍。断言用的 commandTimeout 不动，那是另一回事。
//
// 1800s：`07-parallel-waves` 跑的是 `graph`，编排器要规划、为每个节点派一个子代理、
// 在波边界 fan-in 并评审——三次子代理生命周期都算在这一条臂的墙上时间里。900s 会把
// 一次正常但慢的运行砍成「超时」，而那种失败读起来像技能的问题，其实是超时设小了。
// 代价是卡住的臂要多占一倍时间；`events.jsonl` 会留下它卡在哪一步。
const armTimeout = 1800 * time.Second

// runHeadless 在 workdir 里跑一个任务。dsh 的 headless profile 一个任务跑完就退，
// 答案走 stdout（--json 时是事件流），诊断走 stderr。
//
// 返回的第三个值是**原始事件流**：超时被砍的时候，前面已经发生的事不能丢——
// 丢掉的正是「它到底卡在哪一步」这条线索。
func runHeadless(dsh, workdir, prompt string) (runEvents, string, string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), armTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, dsh, "--profile", "headless", "--json", prompt)
	cmd.Dir = workdir
	// 每条臂一个**自己的** TMPDIR 与 GOCACHE。
	//
	// 串行跑时臂的私有临时根是 $TMPDIR 下唯一的一个，所以看不出问题；一旦并发，
	// 臂 A 一条 `ls $TMPDIR` 就能看到臂 B 正在做的解（`work/`）甚至它的 seed——
	// iteration-8 里「抄了另一条臂的检查点，成了唯一拿到满分的 without_skill」就是
	// 这类失败。要并发，就得先让每条臂只看得到自己的临时目录。GOCACHE 同理：共享
	// 的话会留下别的臂编译过的对象。
	//
	// 放在**臂自己的临时根下面**（而不是另找一处），是为了不改变沙箱的可见范围：
	// headless 允许写工作区与系统临时目录，臂的根就在系统临时目录里。
	armTmp := filepath.Join(filepath.Dir(workdir), "tmp")
	if err := os.MkdirAll(filepath.Join(armTmp, "gocache"), 0o755); err != nil {
		return runEvents{}, "", "", fmt.Errorf("建臂的临时目录失败：%w", err)
	}
	// headless 的沙箱允许工作区与临时目录，但**拒绝工作区之外的默认构建缓存**
	// （`~/Library/Caches/go-build`）。不指一下的话，每条臂都要先自己踩一遍这个坑、
	// 再想办法绕开——那是环境噪声，不是被测的东西。
	cmd.Env = append(os.Environ(),
		"TMPDIR="+armTmp,
		"GOCACHE="+filepath.Join(armTmp, "gocache"),
	)
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	raw := stdout.String()
	out, finalText := parseEvents(raw)
	if ctx.Err() != nil {
		// 超时被砍：已采到的事件照样带回去，它们说明了卡在哪一步。
		return out, finalText, raw, fmt.Errorf("超过 %s 还没跑完（最后一步是 step %d，已调用 %d 次工具）",
			armTimeout, out.steps, out.toolCalls)
	}
	if err != nil {
		// 任务失败也要把已经跑出来的东西带回去，否则没法判断失败在哪一步。
		return out, finalText, raw, fmt.Errorf("%v（stderr 末尾：%s）", err, tail(stderr.String(), 400))
	}
	return out, finalText, raw, nil
}

// parseEvents 把 `dsh --json` 的事件流累加成开销与最后一段话。
func parseEvents(raw string) (runEvents, string) {
	var out runEvents
	var finalText string
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var event map[string]any
		if json.Unmarshal([]byte(line), &event) != nil {
			continue
		}
		switch event["type"] {
		case "status":
			if event["phase"] != "step_end" {
				continue
			}
			out.steps++
			if usage, ok := event["usage"].(map[string]any); ok {
				out.totalTokens += int(number(usage["totalTokens"]))
			}
		case "tool_call":
			out.toolCalls++
		case "final":
			if text, ok := event["text"].(string); ok {
				finalText = text
			}
		}
	}
	return out, finalText
}

// armSuffix 从 arms.json 取这条臂的提示后缀——臂怎么定义只在一个地方说。
func armSuffix(arm string) (string, bool) {
	raw, err := os.ReadFile(filepath.Join(evalsDir, "arms.json"))
	if err != nil {
		return "", false
	}
	var arms map[string]json.RawMessage
	if json.Unmarshal(raw, &arms) != nil {
		return "", false
	}
	entry, ok := arms[arm]
	if !ok {
		return "", false
	}
	var parsed struct {
		Suffix string `json:"suffix"`
	}
	if json.Unmarshal(entry, &parsed) != nil || parsed.Suffix == "" {
		return "", false
	}
	return parsed.Suffix, true
}

// resolveDsh 找 dsh 可执行文件。顺序：--dsh、$EVAL_DSH、PATH。
func resolveDsh(explicit string) (string, error) {
	for _, candidate := range []string{explicit, os.Getenv("EVAL_DSH")} {
		if candidate == "" {
			continue
		}
		if !exists(candidate) {
			return "", fmt.Errorf("run: 没有这个文件：%s", candidate)
		}
		return candidate, nil
	}
	if found, err := exec.LookPath("dsh"); err == nil {
		return found, nil
	}
	return "", fmt.Errorf("run: 找不到 dsh——用 --dsh PATH 或环境变量 EVAL_DSH 指定")
}

func runNotes(caseID, arm, dsh, finalText string, events runEvents, elapsed float64, runErr error) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# %s / %s\n\n", caseID, arm)
	fmt.Fprintf(&b, "- dsh：`%s`\n", dsh)
	fmt.Fprintf(&b, "- 耗时：%.1fs\n", elapsed)
	fmt.Fprintf(&b, "- token：%d\n", events.totalTokens)
	fmt.Fprintf(&b, "- 步数：%d，工具调用：%d\n", events.steps, events.toolCalls)
	if runErr != nil {
		fmt.Fprintf(&b, "- ⚠️ dsh 退出异常：%v\n", runErr)
	}
	b.WriteString("\n同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。\n")
	b.WriteString("工作目录留在 `work/`，可以自己进去复核。\n")
	if finalText != "" {
		b.WriteString("\n## 臂最后说了什么\n\n")
		b.WriteString(finalText)
		b.WriteString("\n")
	}
	return b.String()
}

// writeReviewArtifacts 产出 skill-creator 的 eval viewer 能读的东西。
//
// viewer 的契约是：**含 `outputs/` 子目录的目录就是一个 run**，同级读
// `eval_metadata.json`（拿 prompt）与 `grading.json`（拿分数）。它只取 `outputs/`
// 下的**顶层文件**，所以这里把「人该看什么」汇成一份交付件，而不是倒一整个仓库树。
func writeReviewArtifacts(out, work, caseID string, c Case, g Grade, finalText string) error {
	metadata := map[string]any{
		"eval_id":    caseNumber(caseID),
		"eval_name":  caseID,
		"prompt":     c.Prompt,
		"assertions": assertionTexts(c),
	}
	if err := os.WriteFile(filepath.Join(out, "eval_metadata.json"), mustJSON(metadata), 0o644); err != nil {
		return err
	}

	outputs := filepath.Join(out, "outputs")
	if err := os.RemoveAll(outputs); err != nil {
		return err
	}
	if err := os.MkdirAll(outputs, 0o755); err != nil {
		return err
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# %s\n\n", caseID)
	fmt.Fprintf(&b, "**%d/%d 通过**（%.2f）\n\n", g.Passed, g.Total, g.PassRate)

	b.WriteString("## 任务\n\n")
	b.WriteString(c.Prompt)
	b.WriteString("\n\n## 改了什么\n\n")

	status, _ := git(work, "status", "--porcelain")
	if strings.TrimSpace(status) == "" {
		b.WriteString("（工作树是干净的——这条臂什么都没改）\n\n")
	} else {
		b.WriteString("```\n")
		b.WriteString(strings.TrimRight(status, "\n"))
		b.WriteString("\n```\n\n")
		if diffstat, _ := git(work, "diff", "--stat", "HEAD"); strings.TrimSpace(diffstat) != "" {
			b.WriteString("```\n")
			b.WriteString(strings.TrimRight(diffstat, "\n"))
			b.WriteString("\n```\n\n")
		}
	}

	b.WriteString("## 需求资料（判别点多半在这里）\n\n")
	b.WriteString(requirementMaterial(work))

	b.WriteString("## 分数\n\n")
	for _, e := range g.Expectations {
		fmt.Fprintf(&b, "- %s %s", mark(e.Passed), e.Text)
		if !e.Passed && e.Evidence != "" {
			fmt.Fprintf(&b, "\n  - %s", firstLine(e.Evidence))
		}
		b.WriteString("\n")
	}

	if finalText != "" {
		b.WriteString("\n## 臂最后说了什么\n\n")
		b.WriteString(finalText)
		b.WriteString("\n")
	}

	return os.WriteFile(filepath.Join(outputs, "交付件.md"), []byte(b.String()), 0o644)
}

// requirementMaterial 把 requirements/ 下的文件连路径一起列出来——「产物落在哪」
// 本身就是被断言的东西，所以路径不能丢。
func requirementMaterial(work string) string {
	root := filepath.Join(work, "requirements")
	if !exists(root) {
		return "（没有 `requirements/` 目录）\n\n"
	}
	var b strings.Builder
	filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil || entry.IsDir() {
			return nil
		}
		rel, relErr := filepath.Rel(work, path)
		if relErr != nil {
			return nil
		}
		raw, readErr := os.ReadFile(path)
		if readErr != nil {
			return nil
		}
		fmt.Fprintf(&b, "### `%s`\n\n", filepath.ToSlash(rel))
		text := string(raw)
		if len(text) > 4000 {
			text = text[:4000] + "\n…（截断）"
		}
		b.WriteString(text)
		if !strings.HasSuffix(text, "\n") {
			b.WriteString("\n")
		}
		b.WriteString("\n")
		return nil
	})
	if b.Len() == 0 {
		return "（`requirements/` 是空的）\n\n"
	}
	return b.String()
}

func assertionTexts(c Case) []string {
	texts := make([]string, 0, len(c.Assertions))
	for _, spec := range c.Assertions {
		text := spec.str("text")
		if text == "" {
			text = spec.str("kind")
		}
		texts = append(texts, text)
	}
	return texts
}

// caseNumber 取用例 id 的数字前缀，viewer 按 eval_id 排序。
func caseNumber(caseID string) int {
	digits := ""
	for _, r := range caseID {
		if r < '0' || r > '9' {
			break
		}
		digits += string(r)
	}
	n := 0
	fmt.Sscanf(digits, "%d", &n)
	return n
}

// regradeExisting 对已经跑过的臂重新打分并重生成交付件，**不碰 dsh**。
// 改了探针或断言之后用它：臂的产物没变，变的是量它的那把尺子。
func regradeExisting(out, caseID, arm string, c Case) int {
	work := filepath.Join(out, "work")
	if !exists(work) {
		fmt.Fprintf(os.Stderr, "run: %s 下没有 work/，没法 --regrade\n", out)
		return 1
	}
	// 搬回来的树里，origin 的路径可能还指着已经删掉的临时根；不修的话 push 断言会误判。
	if origin := filepath.Join(work, ".git", "eval-origin.git"); exists(origin) {
		git(work, "remote", "set-url", "origin", origin)
	}
	var events runEvents
	var finalText string
	if raw, err := os.ReadFile(filepath.Join(out, "events.jsonl")); err == nil {
		events, finalText = parseEvents(string(raw))
	}
	var timing Timing
	readJSONFile(filepath.Join(out, "timing.json"), &timing)
	// 早期几轮的 timing.json 没有 schema 要的字段名，这里补齐，免得 viewer 显示 0。
	if timing.DurationMs == 0 && timing.DurationSeconds > 0 {
		timing.DurationMs = int(timing.DurationSeconds * 1000)
	}
	if timing.TotalDurationSeconds == 0 {
		timing.TotalDurationSeconds = timing.DurationSeconds
	}
	os.WriteFile(filepath.Join(out, "timing.json"), mustJSON(timing), 0o644)

	g := grade(caseID, work, c)
	if err := os.WriteFile(filepath.Join(out, "grading.json"), mustJSON(g), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	notes := runNotes(caseID, arm, "（--regrade：没重跑 dsh，只重新打分）", finalText, events, timing.DurationSeconds, nil)
	if err := os.WriteFile(filepath.Join(out, "notes.md"), []byte(notes), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	if err := writeReviewArtifacts(out, work, caseID, c, g, finalText); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
	}
	fmt.Printf("%s/%s  重打分 %.2f（%d/%d）\n", caseID, arm, g.PassRate, g.Passed, g.Total)
	return 0
}

// parkWorkTree 把打完分的臂工作树从私有临时根搬进 results/，供人事后复核。
// 只有跑完之后才搬——跑的时候它必须待在一个别的臂够不着的地方。
func parkWorkTree(work, out string) error {
	dst := filepath.Join(out, "work")
	os.RemoveAll(dst)
	if err := os.Rename(work, dst); err != nil {
		return err
	}
	if seed := work + ".seed.json"; exists(seed) {
		os.Remove(filepath.Join(out, "work.seed.json"))
		if err := os.Rename(seed, filepath.Join(out, "work.seed.json")); err != nil {
			return err
		}
	}
	// origin 建在 `.git/` 里（沙箱只允许写工作区），所以它跟着树一起搬过来了；
	// 但 `.git/config` 里记的是**临时根的绝对路径**，搬完就成了死链——`--regrade`
	// 会在 push 断言上误判。这里把 remote 路径改成新位置。
	origin := filepath.Join(dst, ".git", "eval-origin.git")
	if exists(origin) {
		git(dst, "remote", "set-url", "origin", origin)
	}
	return nil
}

// contaminationMarkers 是臂**不该碰**的东西。工作树现在建在仓库外的私有临时根里，
// 所以它够不着这些；这条检查是保险，让隔离失效时能被看见。
//
// `.dsh/sessions` 是后补的一条：DSH 把每个会话存在 `~/.dsh/sessions/<cwd 的 slug>/` 下，
// 而 **slug 就是 cwd**。工作树还在 `evals/results/` 里那几轮，会话目录名直接是
// `--Users-…-let-it-go-evals-results-iteration-8-04-serial-batch-without_skill-work--`——
// 仓库路径、用例号、臂名、第几次全在里面，而且**永远不会自己消失**。实测 iteration-11 的
// 02/with_skill 就是列了会话目录才被标记的。工作树挪走之后 slug 不再泄漏这些，但
// **会话记录本身仍然共享且可读**（DSH 没有可配置的存储根），所以读到就要报出来。
var contaminationMarkers = []string{"evals/cases", "evals/results", "evals/harness", "arms.json", ".dsh/sessions"}

func contaminationIn(rawEvents string) []string {
	var found []string
	for _, marker := range contaminationMarkers {
		if strings.Contains(rawEvents, marker) {
			found = append(found, marker)
		}
	}
	return found
}
