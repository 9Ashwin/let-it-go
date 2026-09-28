package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// 触发评估：一组 prompt，看 DSH 实际加载了哪个技能。
//
// 这是八个用例**测不到**的一层。那些用例靠 prompt 后缀强制加载技能，量的是「技能加载之后
// 行为对不对」；这里量的是「**该加载的技能有没有被加载**」。后者一直靠人读 description 判断，
// 而人读到的那一次（`规格说明` 同时挂在 `prd` 与 `to-design` 上，RFC 却把 spec 并进了
// to-design）就是一次真的误路由。
//
// 它借的是 skill-creator 的**想法**，不是它的代码：那个 `run_eval.py` 是 shell 出去调
// `claude -p` 的（docstring 原话：whether a skill's description causes Claude to trigger），
// 而这个仓库只面向 DSH。

type triggerCase struct {
	ID     string   `json:"id"`
	Prompt string   `json:"prompt"`
	Expect []string `json:"expect"`
	// Forbid 是**一次都不许出现在加载链里**的技能名，无论它排第几。
	//
	// 调用轴需要这个形状：`user-invoked`（`disable-model-invocation: true`）的技能，DSH 的
	// `skill` 工具直接返回 isError，模型**猜名字也加载不了**。所以这条断言不是「该加载谁」，
	// 而是「谁绝不能被加载」——`expect` 表达不了它，因为那条链上同时可能有别的合法技能
	//（实测：说「PR 开好了，合入吧」时模型有时会先加载 `ship-it`，那不算违反调用轴）。
	//
	// `expect` 缺省（而不是 `[]`）= 不判「加载了什么」，只判 `forbid`。
	Forbid []string `json:"forbid"`

	// Chain 要求这些技能**按顺序**出现在加载链里（不要求相邻）。
	//
	// `expect` 只管第一段，所以「第一个对、第二个没接力」从它下面溜过去——实测踩过一次真事故：
	// 「写个 go 后台管理系统」第一个加载 `prd`（对），然后直接开写代码，从头到尾没加载
	// `to-issues` / `loop-it`；用户当面追问「为什么不建 issue 不开 loop」它才回头。
	Chain []string `json:"chain,omitempty"`

	// TimeoutSeconds 覆盖这一次运行的上限。
	//
	// 接力用例要看**两跳**，而第一跳之前的环境探测就可能吃掉几分钟。用默认窗口会得到
	// 「0/3」这种结果，而它测的是超时不是接力——踩过一次，见 runTriggerCase 里的 `Undecided`。
	TimeoutSeconds int    `json:"timeout_seconds,omitempty"`
	Why            string `json:"why"`
}

type triggerSet struct {
	Suffix string        `json:"suffix"`
	Cases  []triggerCase `json:"cases"`
}

type triggerResult struct {
	ID     string   `json:"id"`
	Prompt string   `json:"prompt"`
	Expect []string `json:"expect"`
	Forbid []string `json:"forbid,omitempty"`
	Chain  []string `json:"chain,omitempty"`
	// Undecided 是被窗口砍断、链还没走完的次数。它们**不算失败**：那一步根本没跑到。
	Undecided int `json:"undecided,omitempty"`
	// Runs 是每一次实际加载的技能，**按加载顺序**（第一个就是路由决策）。
	// 保留全部几次而不是只留最后一次：实测同一个 prompt 三次跑出来的链不一样，
	// 所以「通过率」才有意义，「一次通过」没有。
	Runs    [][]string `json:"runs"`
	Passed  int        `json:"passed"`
	Repeat  int        `json:"repeat"`
	Pass    bool       `json:"pass"`
	Seconds float64    `json:"seconds"`
	Why     string     `json:"why"`
	Err     string     `json:"err,omitempty"`
}

// triggerTimeout 一次触发评估的上限。后缀明确要求「不要真的动手」，所以正常几秒到几十秒；
// 180s 只用来兜住卡死的会话。armTimeout（1800s）在这里太长了。
const triggerTimeout = 180 * time.Second

// skillsLoaded 从 `dsh --json` 的事件流里取出**真的加载成功**的技能名。
//
// 只看 `skill` 工具调用——**不看模型的自述**：它说「我打算加载 X」和它真的加载 X 是两件事，
// 实测过一条会话明确说「暂不加载、不动手」，于是自述有、工具调用没有。
//
// 但也不能只看调用本身。DSH 对**不存在的名字**与 **`disable-model-invocation` 的技能**都返回
// `isError`，而模型是会猜名字的（实测过一次：它编了一个 `use-git-worktree` 去调）。把失败的
// 调用记成「加载了」是假红——而且正好把 user-invoked 的闸门测反了：那条闸门的期望是「它加载
// 不了」，一次失败的尝试恰恰是闸门在起作用。所以这里把 `tool_call` 与 `tool_result` 按 callId
// 配对，只有**结果不是 error** 的调用才算加载。
func skillsLoaded(raw string) []string {
	type skillCall struct{ callID, name string }
	var calls []skillCall
	status := map[string]string{}
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var event struct {
			Type   string         `json:"type"`
			Tool   string         `json:"tool"`
			CallID string         `json:"callId"`
			Status string         `json:"status"`
			Input  map[string]any `json:"input"`
		}
		if json.Unmarshal([]byte(line), &event) != nil {
			continue
		}
		switch event.Type {
		case "tool_call":
			if event.Tool != "skill" {
				continue
			}
			if name, ok := event.Input["name"].(string); ok && name != "" {
				calls = append(calls, skillCall{event.CallID, name})
			}
		case "tool_result":
			status[event.CallID] = event.Status
		}
	}
	var names []string
	for _, call := range calls {
		if status[call.callID] == "error" {
			continue
		}
		names = append(names, call.name)
	}
	return names
}

// triggerPass 判这次加载链算不算对。
//
// 两条规则，按顺序：
//
//  1. `forbid` 里的技能一次都不许出现在链里（调用轴的闸门：user-invoked 的技能模型加载不了）；
//  2. `expect` **缺省** = 不判「加载了什么」；`expect: []` = 不该加载任何技能；非空 = **第一个**
//     加载的要在期望里（只看路由决策，不看之后的串联）。
func triggerPass(expect, forbid, chain, loaded []string) bool {
	for _, name := range forbid {
		for _, got := range loaded {
			if got == name {
				return false
			}
		}
	}
	if !chainSatisfied(chain, loaded) {
		return false
	}
	if expect == nil {
		return true
	}
	if len(expect) == 0 {
		return len(loaded) == 0
	}
	if len(loaded) == 0 {
		return false
	}
	for _, name := range expect {
		if name == loaded[0] {
			return true
		}
	}
	return false
}

// chainSatisfied 判 chain 是不是 loaded 的**有序子序列**。空 chain 恒真。
func chainSatisfied(chain, loaded []string) bool {
	next := 0
	for _, got := range loaded {
		if next < len(chain) && got == chain[next] {
			next++
		}
	}
	return next == len(chain)
}

func cmdTrigger(args []string) int {
	dshPath, out, only := "", "", ""
	parallel, repeat := 4, 1
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--dsh":
			i++
			if i < len(args) {
				dshPath = args[i]
			}
		case "--out":
			i++
			if i < len(args) {
				out = args[i]
			}
		case "--only":
			i++
			if i < len(args) {
				only = args[i]
			}
		case "--parallel":
			i++
			if i < len(args) {
				fmt.Sscanf(args[i], "%d", &parallel)
			}
		case "--repeat":
			i++
			if i < len(args) {
				fmt.Sscanf(args[i], "%d", &repeat)
			}
		}
	}
	if parallel < 1 {
		parallel = 1
	}
	if repeat < 1 {
		repeat = 1
	}
	// 在这里就把 `--out` 解析成绝对路径：worker 是**并发**跑的，而下面写 triggers.json 的那段
	// 在 `wg.Wait()` 之后——失败运行的事件流如果拿到的是相对路径，会按进程 cwd（`go -C evals/harness
	// run .` 时是 evals/harness）落错地方。踩过一次：事件流全写进了 `evals/harness/results/`。
	out = repoPath(out)

	raw, err := os.ReadFile(filepath.Join(evalsDir, "triggers.json"))
	if err != nil {
		fmt.Fprintln(os.Stderr, "trigger:", err)
		return 1
	}
	var set triggerSet
	if err := json.Unmarshal(raw, &set); err != nil {
		fmt.Fprintf(os.Stderr, "trigger: triggers.json 不是合法 JSON：%v\n", err)
		return 1
	}
	var cases []triggerCase
	for _, c := range set.Cases {
		if only != "" && c.ID != only {
			continue
		}
		cases = append(cases, c)
	}
	if len(cases) == 0 {
		fmt.Fprintln(os.Stderr, "trigger: 没有匹配的用例")
		return 1
	}

	dsh, err := resolveDsh(dshPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "trigger:", err)
		return 1
	}

	results := make([]triggerResult, len(cases))
	work := make(chan int)
	var wg sync.WaitGroup
	for w := 0; w < parallel; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for index := range work {
				results[index] = runTriggerCase(dsh, set.Suffix, out, cases[index], repeat)
			}
		}()
	}
	for index := range cases {
		work <- index
	}
	close(work)
	wg.Wait()

	passed := 0
	fmt.Printf("%-32s %-18s %-6s %-26s %s\n", "用例", "期望", "触发率", "第一次的加载链", "结果")
	for _, r := range results {
		if r.Pass {
			passed++
		}
		mark := "✓"
		switch {
		case r.Pass:
		case r.Undecided > 0 && r.Passed+r.Undecided == r.Repeat:
			// 没跑到的那些不算失败：窗口砍断了，链根本没机会走完。
			mark = fmt.Sprintf("—（%d 次被窗口砍断，不可判）", r.Undecided)
		default:
			mark = "✗"
		}
		chain := "（没加载）"
		if len(r.Runs) > 0 && len(r.Runs[0]) > 0 {
			chain = strings.Join(r.Runs[0], " → ")
		}
		fmt.Printf("%-32s %-22s %-6s %-26s %s\n", r.ID, joinOrNone(r.Expect, r.Forbid, r.Chain),
			fmt.Sprintf("%d/%d", r.Passed, r.Repeat), chain, mark)
		if r.Err != "" {
			fmt.Printf("%-32s   %s\n", "", r.Err)
		}
	}
	fmt.Printf("\n→ %d/%d 用例通过（每个跑 %d 次，全对才算过）\n", passed, len(results), repeat)

	if out != "" {
		// 和 `run` 一样按 evals/ 解析：`go -C evals/harness run .` 的进程 cwd 是
		// evals/harness，直接 MkdirAll 会把结果写到 evals/harness/results/ 去。
		out = repoPath(out)
		if err := os.MkdirAll(out, 0o755); err != nil {
			fmt.Fprintln(os.Stderr, "trigger:", err)
			return 1
		}
		payload := map[string]any{
			"suffix":  set.Suffix,
			"passed":  passed,
			"total":   len(results),
			"results": results,
		}
		if err := os.WriteFile(filepath.Join(out, "triggers.json"), mustJSON(payload), 0o644); err != nil {
			fmt.Fprintln(os.Stderr, "trigger:", err)
			return 1
		}
		fmt.Println("  写入", filepath.Join(out, "triggers.json"))
	}
	if passed != len(results) {
		return 1
	}
	return 0
}

// runTriggerCase 在一个**私有临时目录**里跑一次。cwd 不留在仓库里，所以模型即使动手也
// 碰不到任何真东西；这跟臂的隔离是同一条理由。
func runTriggerCase(dsh, suffix, outDir string, c triggerCase, repeat int) triggerResult {
	result := triggerResult{ID: c.ID, Prompt: c.Prompt, Expect: c.Expect, Forbid: c.Forbid, Chain: c.Chain, Why: c.Why, Repeat: repeat}
	started := time.Now()
	for i := 0; i < repeat; i++ {
		dir, err := os.MkdirTemp("", "trigger-")
		if err != nil {
			result.Err = err.Error()
			break
		}
		limit := triggerTimeout
		if c.TimeoutSeconds > 0 {
			limit = time.Duration(c.TimeoutSeconds) * time.Second
		}
		_, _, raw, runErr := runHeadlessFor(dsh, dir, c.Prompt+"\n\n"+suffix, limit)
		os.RemoveAll(dir)

		loaded := skillsLoaded(raw)
		// **不排序**：顺序就是路由决策本身，排掉之后报告读不出「先加载谁」。
		result.Runs = append(result.Runs, loaded)
		passed := triggerPass(c.Expect, c.Forbid, c.Chain, loaded)
		if passed {
			result.Passed++
		} else if errors.Is(runErr, errTimedOut) {
			// 被窗口砍断、链还没走完：这一次**不可判**。把「没跑到」记成「没接力」，
			// 就会照着假数据改技能——这条判据本身就是被那次事故逼出来的。
			result.Undecided++
		}
		if !passed {
			// 失败的运行**留下事件流**。不留的话，报告只说「0/3」，而为什么失败——它到底有没有
			// 跑那条命令、是不是写完 PRD 就结束了回合——只能靠手工复现一次才知道。我为此手工跑过
			// 一次，代价是七分钟和一个错误的结论。
			dir := filepath.Join(outDir, c.ID)
			os.MkdirAll(dir, 0o755)
			os.WriteFile(filepath.Join(dir, fmt.Sprintf("run%d.events.jsonl", i+1)), []byte(raw), 0o644)
		}
		if runErr != nil && len(loaded) == 0 && result.Err == "" {
			result.Err = runErr.Error()
		}
	}
	result.Seconds = round(time.Since(started).Seconds(), 1)
	result.Pass = result.Passed == repeat
	return result
}

func joinOrNone(expect, forbid, chain []string) string {
	label := "（无）"
	if len(expect) > 0 {
		label = strings.Join(expect, "+")
	} else if expect == nil {
		label = "（不判）"
	}
	if len(chain) > 0 {
		label += " 链:" + strings.Join(chain, "→")
	}
	if len(forbid) > 0 {
		label += " 禁" + strings.Join(forbid, "+")
	}
	return label
}
