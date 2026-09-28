package main

// bench：把一个 iteration 目录汇总成 skill-creator 的 benchmark.json / benchmark.md。
//
// **字段名严格照 skill-creator 的 references/schemas.md**——viewer 读的就是那些名字
// （`configuration`、`result.pass_rate`、`run_summary.delta`），换个名字它就会显示成空的。
// 所以这个文件只做汇总，不改口径。

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

var arms = []string{"with_skill", "without_skill"}

// armNames 是上面的集合形式，用来判断一个目录名（剥掉 `-runN` 之后）是不是已知的臂。
var armNames = func() map[string]struct{} {
	known := map[string]struct{}{}
	for _, arm := range arms {
		known[arm] = struct{}{}
	}
	return known
}()

// runSuffix 返回 `with_skill-run2` 里的 `run2`；没有这个后缀就返回空串。
// 同一条臂跑多次时，第 2 次起目录名带这个后缀，bench 靠它把多次运行归到同一个
// configuration 下——单次跑分不清「技能更强」还是噪声。
func runSuffix(name string) string {
	index := strings.LastIndex(name, "-run")
	if index < 0 {
		return ""
	}
	tail := name[index+len("-run"):]
	if tail == "" {
		return ""
	}
	for _, r := range tail {
		if r < '0' || r > '9' {
			return ""
		}
	}
	return "run" + tail
}

// Stat 是 schema 里的 {mean,stddev,min,max}。
type Stat struct {
	Mean   float64 `json:"mean"`
	Stddev float64 `json:"stddev"`
	Min    float64 `json:"min"`
	Max    float64 `json:"max"`
}

type RunResult struct {
	PassRate    float64 `json:"pass_rate"`
	Passed      int     `json:"passed"`
	Failed      int     `json:"failed"`
	Total       int     `json:"total"`
	TimeSeconds float64 `json:"time_seconds"`
	Tokens      int     `json:"tokens"`
	ToolCalls   int     `json:"tool_calls"`
	Errors      int     `json:"errors"`
}

type Run struct {
	EvalID        string        `json:"eval_id"`
	EvalName      string        `json:"eval_name"`
	Configuration string        `json:"configuration"`
	RunNumber     int           `json:"run_number"`
	Result        RunResult     `json:"result"`
	Expectations  []Expectation `json:"expectations"`
	Notes         []string      `json:"notes"`
}

type ArmSummary struct {
	PassRate    Stat `json:"pass_rate"`
	TimeSeconds Stat `json:"time_seconds"`
	Tokens      Stat `json:"tokens"`
}

type RunSummary struct {
	WithSkill    ArmSummary        `json:"with_skill"`
	WithoutSkill ArmSummary        `json:"without_skill"`
	Delta        map[string]string `json:"delta"`
}

type Metadata struct {
	SkillName            string   `json:"skill_name"`
	SkillPath            string   `json:"skill_path"`
	ExecutorModel        string   `json:"executor_model"`
	AnalyzerModel        string   `json:"analyzer_model"`
	Timestamp            string   `json:"timestamp"`
	EvalsRun             []string `json:"evals_run"`
	RunsPerConfiguration int      `json:"runs_per_configuration"`
}

type Benchmark struct {
	Metadata   Metadata   `json:"metadata"`
	Runs       []Run      `json:"runs"`
	RunSummary RunSummary `json:"run_summary"`
	Notes      []string   `json:"notes"`
}

func statOf(values []float64) Stat {
	if len(values) == 0 {
		return Stat{}
	}
	sum := 0.0
	for _, value := range values {
		sum += value
	}
	mean := sum / float64(len(values))
	variance := 0.0
	for _, value := range values {
		variance += (value - mean) * (value - mean)
	}
	stddev := 0.0
	if len(values) > 1 {
		stddev = math.Sqrt(variance / float64(len(values)))
	}
	lowest, highest := values[0], values[0]
	for _, value := range values {
		if value < lowest {
			lowest = value
		}
		if value > highest {
			highest = value
		}
	}
	return Stat{
		Mean:   round(mean, 4),
		Stddev: round(stddev, 4),
		Min:    round(lowest, 4),
		Max:    round(highest, 4),
	}
}

func round(value float64, places int) float64 {
	scale := math.Pow(10, float64(places))
	return math.Round(value*scale) / scale
}

func readJSONFile(path string, into any) bool {
	raw, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	return json.Unmarshal(raw, into) == nil
}

func cmdBench(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: evalctl bench <iteration-dir> [--skill-name NAME] [--executor-model M]")
		return 2
	}
	iteration := repoPath(args[0])
	skillName, executor := "flow", "deepseek-v4-flash"
	for i := 1; i < len(args); i++ {
		switch args[i] {
		case "--skill-name":
			i++
			if i < len(args) {
				skillName = args[i]
			}
		case "--executor-model":
			i++
			if i < len(args) {
				executor = args[i]
			}
		}
	}
	abs, err := filepath.Abs(iteration)
	if err != nil || !exists(abs) {
		fmt.Fprintf(os.Stderr, "bench: 没有这个目录：%s\n", iteration)
		return 1
	}

	caseEntries, err := os.ReadDir(abs)
	if err != nil {
		fmt.Fprintln(os.Stderr, "bench:", err)
		return 1
	}

	var runs []Run
	var missing []string
	maxRuns := 0
	for _, entry := range caseEntries {
		if !entry.IsDir() {
			continue
		}
		caseID := entry.Name()
		armDirs, err := os.ReadDir(filepath.Join(abs, caseID))
		if err != nil {
			continue
		}
		found := map[string]int{}
		for _, armEntry := range armDirs {
			if !armEntry.IsDir() {
				continue
			}
			// 一条臂可以跑多次：第 2 次起目录名带 `-run2` 后缀，这里剥掉，
			// 于是它们算同一个 configuration 的多次运行——方差就是这么来的。
			arm := strings.TrimSuffix(armEntry.Name(), "-"+runSuffix(armEntry.Name()))
			if _, known := armNames[arm]; !known {
				continue
			}
			runDir := filepath.Join(abs, caseID, armEntry.Name())
			var grading Grade
			if !readJSONFile(filepath.Join(runDir, "grading.json"), &grading) {
				continue
			}
			var timing struct {
				TotalTokens     int     `json:"total_tokens"`
				DurationSeconds float64 `json:"duration_seconds"`
				ToolCalls       int     `json:"tool_calls"`
				RunNumber       int     `json:"run_number"`
			}
			readJSONFile(filepath.Join(runDir, "timing.json"), &timing)
			runNumber := timing.RunNumber
			if runNumber == 0 {
				runNumber = found[arm] + 1
			}
			found[arm]++
			runs = append(runs, Run{
				EvalID:        caseID,
				EvalName:      grading.CaseName,
				Configuration: arm,
				RunNumber:     runNumber,
				Result: RunResult{
					PassRate:    grading.PassRate,
					Passed:      grading.Passed,
					Failed:      grading.Total - grading.Passed,
					Total:       grading.Total,
					TimeSeconds: timing.DurationSeconds,
					Tokens:      timing.TotalTokens,
					ToolCalls:   timing.ToolCalls,
					Errors:      0,
				},
				Expectations: grading.Expectations,
				Notes:        notesFrom(runDir),
			})
		}
		for _, arm := range arms {
			if found[arm] == 0 {
				missing = append(missing, caseID+"/"+arm)
			}
			if found[arm] > maxRuns {
				maxRuns = found[arm]
			}
		}
	}
	if len(runs) == 0 {
		fmt.Fprintf(os.Stderr, "bench: %s 下没有找到任何 grading.json（每条臂一个）\n", abs)
		return 1
	}

	benchmark := Benchmark{
		Metadata: Metadata{
			SkillName:            skillName,
			SkillPath:            evalsDir,
			ExecutorModel:        executor,
			AnalyzerModel:        "inline",
			Timestamp:            time.Now().UTC().Format("2006-01-02T15:04:05Z"),
			EvalsRun:             evalIDs(runs),
			RunsPerConfiguration: maxRuns,
		},
		Runs:       runs,
		RunSummary: summarize(runs),
		Notes:      analystNotes(runs),
	}
	if len(missing) > 0 {
		benchmark.Notes = append(benchmark.Notes,
			"缺少这些臂的结果："+strings.Join(missing, "、"))
	}

	os.WriteFile(filepath.Join(abs, "benchmark.json"), mustJSON(benchmark), 0o644)
	markdown := benchmarkMarkdown(benchmark)
	os.WriteFile(filepath.Join(abs, "benchmark.md"), []byte(markdown), 0o644)
	fmt.Print(markdown)
	if len(missing) > 0 {
		fmt.Fprintf(os.Stderr, "  注意：缺少这些臂的 grading.json：%s\n", strings.Join(missing, "、"))
	}
	return 0
}

func notesFrom(runDir string) []string {
	raw, err := os.ReadFile(filepath.Join(runDir, "notes.md"))
	if err != nil {
		return nil
	}
	var notes []string
	for _, line := range strings.Split(string(raw), "\n") {
		if trimmed := strings.TrimSpace(line); strings.HasPrefix(trimmed, "-") {
			notes = append(notes, trimmed)
		}
	}
	return notes
}

func evalIDs(runs []Run) []string {
	seen := map[string]bool{}
	var out []string
	for _, run := range runs {
		if !seen[run.EvalID] {
			seen[run.EvalID] = true
			out = append(out, run.EvalID)
		}
	}
	sort.Strings(out)
	return out
}

func summarize(runs []Run) RunSummary {
	pick := func(arm string, field func(RunResult) float64) []float64 {
		var values []float64
		for _, run := range runs {
			if run.Configuration == arm {
				values = append(values, field(run.Result))
			}
		}
		return values
	}
	summaryFor := func(arm string) ArmSummary {
		return ArmSummary{
			PassRate:    statOf(pick(arm, func(r RunResult) float64 { return r.PassRate })),
			TimeSeconds: statOf(pick(arm, func(r RunResult) float64 { return r.TimeSeconds })),
			Tokens:      statOf(pick(arm, func(r RunResult) float64 { return float64(r.Tokens) })),
		}
	}
	withSkill, withoutSkill := summaryFor("with_skill"), summaryFor("without_skill")
	return RunSummary{
		WithSkill:    withSkill,
		WithoutSkill: withoutSkill,
		Delta: map[string]string{
			"pass_rate":    fmt.Sprintf("%+.4f", withSkill.PassRate.Mean-withoutSkill.PassRate.Mean),
			"time_seconds": fmt.Sprintf("%+.1f", withSkill.TimeSeconds.Mean-withoutSkill.TimeSeconds.Mean),
			"tokens":       fmt.Sprintf("%+.1f", withSkill.Tokens.Mean-withoutSkill.Tokens.Mean),
		},
	}
}

// analystNotes 读一遍数字，把聚合统计会盖住的模式挑出来（skill-creator 的 analyst pass）。
func analystNotes(runs []Run) []string {
	var notes []string
	byText := map[string][]bool{}
	for _, run := range runs {
		for _, item := range run.Expectations {
			byText[item.Text] = append(byText[item.Text], item.Passed)
		}
	}
	var texts []string
	for text := range byText {
		texts = append(texts, text)
	}
	sort.Strings(texts)
	for _, text := range texts {
		results := byText[text]
		all, none := true, true
		for _, passed := range results {
			if !passed {
				all = false
			}
			if passed {
				none = false
			}
		}
		if all {
			notes = append(notes, fmt.Sprintf("断言「%s」在两条臂上都通过——它区分不出技能的价值", text))
		} else if none {
			notes = append(notes, fmt.Sprintf("断言「%s」在两条臂上都失败——要么用例坏了，要么断言写错了", text))
		}
	}
	byCase := map[string][]float64{}
	for _, run := range runs {
		byCase[run.EvalName] = append(byCase[run.EvalName], run.Result.PassRate)
	}
	var names []string
	for name := range byCase {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		values := byCase[name]
		lowest, highest := values[0], values[0]
		for _, value := range values {
			if value < lowest {
				lowest = value
			}
			if value > highest {
				highest = value
			}
		}
		if len(values) > 1 && highest-lowest >= 0.3 {
			notes = append(notes, fmt.Sprintf("用例「%s」波动大（%.0f%%–%.0f%%），可能是 flaky",
				name, lowest*100, highest*100))
		}
	}
	return notes
}

func benchmarkMarkdown(b Benchmark) string {
	var out strings.Builder
	fmt.Fprintf(&out, "# benchmark — %s\n\n", b.Metadata.SkillName)
	fmt.Fprintf(&out, "用例：%s\n\n", strings.Join(b.Metadata.EvalsRun, ", "))
	out.WriteString("| 配置 | pass_rate | 用时(s) | tokens |\n|---|---|---|---|\n")
	for _, arm := range arms {
		summary := b.RunSummary.WithSkill
		if arm == "without_skill" {
			summary = b.RunSummary.WithoutSkill
		}
		fmt.Fprintf(&out, "| %s | %.2f ± %.2f | %.1f | %.0f |\n", arm,
			summary.PassRate.Mean, summary.PassRate.Stddev,
			summary.TimeSeconds.Mean, summary.Tokens.Mean)
	}
	fmt.Fprintf(&out, "| **delta** | **%s** | %s | %s |\n\n",
		b.RunSummary.Delta["pass_rate"], b.RunSummary.Delta["time_seconds"], b.RunSummary.Delta["tokens"])
	out.WriteString("## 逐用例\n\n| 用例 | 配置 | 每次 | 判定 |\n|---|---|---|---|\n")
	for _, row := range caseArmRuns(b.Runs) {
		fmt.Fprintf(&out, "| %s | %s | %s | %s |\n", row.Case, row.Arm, row.PerRun, row.Verdict)
	}
	out.WriteString("\n**判定口径：一次都没全过就不算通过。** 同一配置的每次运行都是 100% 才是「通过」；")
	out.WriteString("每次都一样但不满分是「不通过」；几次之间不一致是 **flaky，不算通过**——60% 不是通过。\n")

	out.WriteString(discriminationMarkdown(b.Runs))

	if len(b.Notes) > 0 {
		out.WriteString("\n## 观察\n\n")
		for _, note := range b.Notes {
			fmt.Fprintf(&out, "- %s\n", note)
		}
	}
	return out.String()
}

// caseArmRow 是「用例 × 配置」的多次运行汇总。
type caseArmRow struct {
	Case    string
	Arm     string
	PerRun  string
	Verdict string
}

// caseArmRuns 把同一条臂的多次运行并成一行，并给出判定——**不许把 60% 记成通过**。
func caseArmRuns(runs []Run) []caseArmRow {
	type key struct{ eval, arm string }
	grouped := map[key][]Run{}
	var keys []key
	for _, run := range runs {
		k := key{run.EvalID, run.Configuration}
		if _, seen := grouped[k]; !seen {
			keys = append(keys, k)
		}
		grouped[k] = append(grouped[k], run)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].eval != keys[j].eval {
			return keys[i].eval < keys[j].eval
		}
		return keys[i].arm < keys[j].arm
	})
	var rows []caseArmRow
	for _, k := range keys {
		group := grouped[k]
		var parts []string
		lowest, highest := 1.0, 0.0
		for _, run := range group {
			parts = append(parts, fmt.Sprintf("%d/%d", run.Result.Passed, run.Result.Total))
			if run.Result.PassRate < lowest {
				lowest = run.Result.PassRate
			}
			if run.Result.PassRate > highest {
				highest = run.Result.PassRate
			}
		}
		verdict := "不通过"
		switch {
		case lowest == 1.0:
			verdict = "通过"
		case lowest != highest:
			verdict = "flaky（不算通过）"
		}
		rows = append(rows, caseArmRow{Case: k.eval, Arm: k.arm,
			PerRun: strings.Join(parts, " / "), Verdict: verdict})
	}
	return rows
}

// discRow 是「用例 × 断言」在两条臂上的通过率。
type discRow struct {
	Case                        string
	Text                        string
	Kind                        string
	WithPassed, WithTotal       int
	WithoutPassed, WithoutTotal int
}

func (r discRow) withRate() float64    { return rate(r.WithPassed, r.WithTotal) }
func (r discRow) withoutRate() float64 { return rate(r.WithoutPassed, r.WithoutTotal) }

func rate(passed, total int) float64 {
	if total == 0 {
		return -1
	}
	return float64(passed) / float64(total)
}

// discrimination 按 用例 × 断言 汇总两条臂的通过率。
//
// 这是 NEXT.md 第一刀要求的那张表：**每条断言先量区分度再留**。两边都满分的断言花掉 token
// 却什么都没测出来；某条臂几次之间不一致的是 flaky，单独列，不算通过。
func discrimination(runs []Run) []discRow {
	type key struct{ eval, text string }
	grouped := map[key]*discRow{}
	var keys []key
	for _, run := range runs {
		for _, item := range run.Expectations {
			k := key{run.EvalID, item.Text}
			row, seen := grouped[k]
			if !seen {
				row = &discRow{Case: run.EvalID, Text: item.Text, Kind: item.Kind}
				grouped[k] = row
				keys = append(keys, k)
			}
			if run.Configuration == "with_skill" {
				row.WithTotal++
				if item.Passed {
					row.WithPassed++
				}
			} else {
				row.WithoutTotal++
				if item.Passed {
					row.WithoutPassed++
				}
			}
		}
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].eval != keys[j].eval {
			return keys[i].eval < keys[j].eval
		}
		return keys[i].text < keys[j].text
	})
	var rows []discRow
	for _, k := range keys {
		rows = append(rows, *grouped[k])
	}
	return rows
}

// verdictOf 把一条断言归到四类之一。判定顺序很重要：flaky 优先于「区分」与「两边满分」，
// 因为「3 次里过了 2 次」既不是通过也不是不通过。
//
// `gate` / `probe` / `tamper_guard` 是用例的**结果底线**，由 evals/AGENTS.md 强制每条用例
// 必须有，不参与「两边满分就删」这条规则——那条规则管的是契约断言（过程传感器）。
func verdictOf(r discRow) string {
	with, without := r.withRate(), r.withoutRate()
	flakyWith := with > 0 && with < 1
	flakyWithout := without > 0 && without < 1
	switch {
	case flakyWith || flakyWithout:
		return "flaky（不算通过）"
	case isFloorKind(r.Kind):
		return "底线（必留）"
	case with == 1 && without == 1:
		return "两边满分（无区分度 → 删掉或改成能失败的形态）"
	case with == 0 && without == 0:
		return "两边全红（用例或断言坏了）"
	default:
		return "区分"
	}
}

// isFloorKind 是每条用例都必须有的三样结果底线。
func isFloorKind(kind string) bool {
	switch kind {
	case "gate", "probe", "tamper_guard":
		return true
	}
	return false
}

func discriminationMarkdown(runs []Run) string {
	rows := discrimination(runs)
	if len(rows) == 0 {
		return ""
	}
	var out strings.Builder
	out.WriteString("\n## 断言区分度（用例 × 断言）\n\n")
	out.WriteString("| 用例 | 断言 | with_skill | without_skill | 判定 |\n|---|---|---|---|---|\n")
	for _, row := range rows {
		fmt.Fprintf(&out, "| %s | %s | %s | %s | %s |\n",
			row.Case, firstLine(row.Text),
			fmtRate(row.WithPassed, row.WithTotal), fmtRate(row.WithoutPassed, row.WithoutTotal),
			verdictOf(row))
	}
	out.WriteString("\n判定只看两条臂的**通过率差**与**同臂多次之间的一致性**。`gate` / `probe` / " +
		"`tamper_guard` 是每条用例的结果底线（evals/AGENTS.md 强制），标「底线（必留）」；" +
		"删留规则管的是其余契约断言（过程传感器）。\n")
	var flaky []string
	for _, row := range rows {
		if strings.HasPrefix(verdictOf(row), "flaky") {
			flaky = append(flaky, fmt.Sprintf("- `%s` / %s：with_skill %s，without_skill %s —— **不算通过**",
				row.Case, firstLine(row.Text), fmtRate(row.WithPassed, row.WithTotal),
				fmtRate(row.WithoutPassed, row.WithoutTotal)))
		}
	}
	if len(flaky) > 0 {
		out.WriteString("\n### flaky（单独列，不算通过）\n\n")
		out.WriteString(strings.Join(flaky, "\n"))
		out.WriteString("\n")
	}
	return out.String()
}

func fmtRate(passed, total int) string {
	if total == 0 {
		return "—"
	}
	return fmt.Sprintf("%d/%d", passed, total)
}
