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
type Timing struct {
	DurationSeconds float64 `json:"duration_seconds"`
	TotalTokens     int     `json:"total_tokens"`
	ToolCalls       int     `json:"tool_calls"`
	RunNumber       int     `json:"run_number"`
}

// cmdRun 跑一条臂：把用例铺进一个受控目录，让 `dsh --profile headless` 在那里把任务做完，
// 再从外部给结果打分。
//
// 这一步之所以成立，是因为 headless profile 从**进程的 cwd** 出发：铺出来的仓库就是它的
// 工作目录，仓库自己的 AGENTS.md 会被自动加载，`~/.agents/skills/` 下的技能也照常被发现。
// 之前靠手工派子代理，工作目录由调用方决定、改不了——仓库约定根本不生效，子代理还会静默消失。
func cmdRun(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: evalctl run <case-id> --arm with_skill|without_skill --out DIR [--dsh PATH] [--keep]")
		fmt.Fprintln(os.Stderr, "  --out 的相对路径以 evals/ 为基准，惯例是 results/iteration-N/<case-id>/<arm>")
		return 2
	}
	caseID := args[0]
	arm, out, dshPath, keep := "", "", "", false
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
		case "--keep":
			keep = true
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
	dsh, err := resolveDsh(dshPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
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
	work := filepath.Join(out, "work")
	if !keep {
		if err := os.RemoveAll(work); err != nil {
			fmt.Fprintln(os.Stderr, "run:", err)
			return 1
		}
	}
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

	prompt := c.Prompt + "\n\n" + suffix
	started := time.Now()
	events, finalText, runErr := runHeadless(dsh, work, prompt)
	elapsed := time.Since(started).Seconds()

	timing := Timing{
		DurationSeconds: round(elapsed, 2),
		TotalTokens:     events.totalTokens,
		ToolCalls:       events.toolCalls,
		RunNumber:       1,
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
	notes := runNotes(caseID, arm, dsh, finalText, events, elapsed, runErr)
	if err := os.WriteFile(filepath.Join(out, "notes.md"), []byte(notes), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "run:", err)
		return 1
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

// runHeadless 在 workdir 里跑一个任务。dsh 的 headless profile 一个任务跑完就退，
// 答案走 stdout（--json 时是事件流），诊断走 stderr。
func runHeadless(dsh, workdir, prompt string) (runEvents, string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, dsh, "--profile", "headless", "--json", prompt)
	cmd.Dir = workdir
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	if ctx.Err() != nil {
		return runEvents{}, "", fmt.Errorf("超过 %s 还没跑完", commandTimeout)
	}

	var out runEvents
	var finalText string
	for _, line := range strings.Split(stdout.String(), "\n") {
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
	if err != nil {
		// 任务失败也要把已经跑出来的东西带回去，否则没法判断失败在哪一步。
		return out, finalText, fmt.Errorf("%v（stderr 末尾：%s）", err, tail(stderr.String(), 400))
	}
	return out, finalText, nil
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
