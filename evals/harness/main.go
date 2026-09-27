// evalctl —— let-it-go 的 eval harness。
//
// 四件事，全部在 agent 之外：
//
//	materialize  把用例的 fixture 变成一次运行用的干净仓库（git init + seed commit）
//	assert       先证明起点是红的（preflight），再核对结果（grade）
//	bench        把一轮结果汇总成 skill-creator 的 benchmark.json / benchmark.md
//	selfcheck    eval 工作区结构自检（挂在 `make check` 上）
//	list         列出用例
//
// 为什么断言必须在 agent 之外执行：DSH 自己的 swebench 冒烟测试就是这个立场——
// 「agent 声称它成功了……然后世界要同意」。这里的「世界」是 fixture 自己的门禁、
// 一个不依赖实现细节的行为探针，以及文件树本身。关键词探针不算证据。
//
// 为什么 fixture 不带 .git：嵌套仓库无法被 let-it-go 正常入库，版本控制留给运行时。
// 顺带的好处是每次运行都从同一个 seed commit 开始，而且 fixture 自带 .git 之后
// 它就是自己的 project root（DSH 取最近的 .git 祖先），它自己的 AGENTS.md 才会生效。
package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"time"
)

// ---------------------------------------------------------------------------
// 路径：用编译期的源文件位置定位，而不是 cwd
//
// `go run` 起进程时的 cwd 是调用者的 cwd，不是模块目录，所以不能用 os.Getwd。
// runtime.Caller 给的是本文件的源码路径，在任何调用方式下都指向 evals/harness。
// ---------------------------------------------------------------------------

var (
	harnessDir = sourceDir()
	evalsDir   = filepath.Dir(harnessDir)
	repoDir    = filepath.Dir(evalsDir)
)

func sourceDir() string {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		panic("evalctl: 定位不到源码目录")
	}
	return filepath.Dir(file)
}

// repoPath 把命令行上的相对路径解析成相对 **evals/** 的绝对路径。
//
// 不能靠 cwd：`go -C evals/harness run .` 会把进程的 cwd 换到 harness 目录，
// 相对路径会解析到 harness 下面去。基址选 evals/ 而不是仓库根，因为 run.md 与
// README 里写的都是 `results/iteration-1/...` 这种形式（结果就在 evals/results/ 下）。
func repoPath(path string) string {
	if path == "" || filepath.IsAbs(path) {
		return path
	}
	return filepath.Join(evalsDir, path)
}

func mustJSON(v any) []byte {
	var buffer bytes.Buffer
	encoder := json.NewEncoder(&buffer)
	encoder.SetIndent("", " ")
	// Go 默认把 < > & 写成 \u003c 之类；这份 JSON 也是给人看的产物，
	// 而 Python 版不转义，关掉才对齐。
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(v); err != nil {
		panic(err)
	}
	return bytes.TrimRight(buffer.Bytes(), "\n")
}

// ---------------------------------------------------------------------------
// 用例声明
// ---------------------------------------------------------------------------

// Case 是 cases/<id>/case.json。字段与 Python 版一一对应。
type Case struct {
	ID            string          `json:"id"`
	Name          string          `json:"name"`
	WhatItTests   string          `json:"what_it_tests"`
	Prompt        string          `json:"prompt"`
	ExpectedOut   string          `json:"expected_output"`
	Fixture       string          `json:"fixture"`
	TamperGuard   []string        `json:"tamper_guard"`
	Assertions    []AssertionSpec `json:"assertions"`
	unknownFields []string
}

// AssertionSpec 是声明式断言。同一种 kind 在不同用例里的附加字段不同，
// 所以没有强类型：probe 用 files/command/extract/config/scenarios，gate 用 command，
// path_glob 用 glob/min。用 map 反而更贴近「声明式」这件事。
type AssertionSpec map[string]any

func (s AssertionSpec) str(key string) string {
	value, _ := s[key].(string)
	return value
}

func (s AssertionSpec) strs(key string) []string {
	raw, ok := s[key].([]any)
	if !ok {
		return nil
	}
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		if text, ok := item.(string); ok {
			out = append(out, text)
		}
	}
	return out
}

func (s AssertionSpec) intOr(key string, fallback int) int {
	if value, ok := s[key].(float64); ok {
		return int(value)
	}
	return fallback
}

// Scenario 是 probe 断言的一个场景：写一份配置，看实际生效的值。
type Scenario struct {
	Thresholds map[string]int `json:"thresholds"`
	Expect     map[string]int `json:"expect"`
}

func (s AssertionSpec) scenarios() []Scenario {
	raw, ok := s["scenarios"].([]any)
	if !ok {
		return nil
	}
	out := make([]Scenario, 0, len(raw))
	for _, item := range raw {
		entry, _ := item.(map[string]any)
		scenario := Scenario{}
		if thresholds, ok := entry["thresholds"].(map[string]any); ok {
			scenario.Thresholds = toIntMap(thresholds)
		}
		if expect, ok := entry["expect"].(map[string]any); ok {
			scenario.Expect = toIntMap(expect)
		}
		out = append(out, scenario)
	}
	return out
}

func toIntMap(raw map[string]any) map[string]int {
	out := make(map[string]int, len(raw))
	for key, value := range raw {
		if number, ok := value.(float64); ok {
			out[key] = int(number)
		}
	}
	return out
}

func loadCase(caseID string) (Case, error) {
	path := filepath.Join(evalsDir, "cases", caseID, "case.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		return Case{}, fmt.Errorf("没有这个用例：%s", path)
	}
	var parsed Case
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return Case{}, fmt.Errorf("%s 不是合法 JSON：%w", path, err)
	}
	return parsed, nil
}

func caseDirs() []string {
	entries, err := os.ReadDir(filepath.Join(evalsDir, "cases"))
	if err != nil {
		return nil
	}
	var out []string
	for _, entry := range entries {
		if entry.IsDir() {
			out = append(out, entry.Name())
		}
	}
	sort.Strings(out)
	return out
}

// ---------------------------------------------------------------------------
// seed 清单：受保护文件的哈希 + 运行前 let-it-go 本来就有的脏
//
// 写在 workdir **外面**，免得 eval 基础设施漏进被测仓库。
// ---------------------------------------------------------------------------

type Seed struct {
	CaseID             string            `json:"case_id"`
	CaseName           string            `json:"case_name"`
	Workdir            string            `json:"workdir"`
	SeedCommit         string            `json:"seed_commit"`
	Protected          map[string]string `json:"protected"`
	ProtectedMissing   []string          `json:"protected_missing_at_seed"`
	LetitgoDirtyAtSeed []string          `json:"letitgo_dirty_at_seed"`
}

func seedPath(workdir string) string {
	abs, err := filepath.Abs(workdir)
	if err != nil {
		abs = workdir
	}
	return abs + ".seed.json"
}

func loadSeed(workdir string) (Seed, error) {
	raw, err := os.ReadFile(seedPath(workdir))
	if err != nil {
		return Seed{}, fmt.Errorf("找不到 seed 清单：%s", seedPath(workdir))
	}
	var parsed Seed
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return Seed{}, fmt.Errorf("%s 不是合法 JSON：%w", seedPath(workdir), err)
	}
	return parsed, nil
}

// ---------------------------------------------------------------------------
// 外部命令与文件小工具
// ---------------------------------------------------------------------------

// commandTimeout 是一次门禁/探针调用的上限。
//
// 没有它，一个挂住的 `make check` 会让整轮 eval 永久卡住——Python 版有 300 秒，
// 这里对齐。
const commandTimeout = 300 * time.Second

func runIn(workdir string, name string, args ...string) (string, int) {
	ctx, cancel := context.WithTimeout(context.Background(), commandTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = workdir
	combined, err := cmd.CombinedOutput()
	if ctx.Err() == context.DeadlineExceeded {
		return string(combined) + "\n[evalctl] 命令超时", -1
	}
	if err != nil {
		if exit, ok := err.(*exec.ExitError); ok {
			return string(combined), exit.ExitCode()
		}
		return string(combined) + "\n" + err.Error(), -1
	}
	return string(combined), 0
}

func git(workdir string, args ...string) (string, int) {
	return runIn(workdir, "git", args...)
}

// dirtyLines 是 `git status --porcelain` 的非空行，排序。
func dirtyLines(repo string) []string {
	out, _ := git(repo, "status", "--porcelain")
	var lines []string
	for _, line := range strings.Split(out, "\n") {
		if trimmed := strings.TrimSpace(line); trimmed != "" {
			lines = append(lines, trimmed)
		}
	}
	sort.Strings(lines)
	return lines
}

func hashFile(path string) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func exists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func tail(text string, limit int) string {
	text = strings.TrimSpace(text)
	if len(text) <= limit {
		return text
	}
	return "…" + text[len(text)-limit:]
}

// resolveGo 把 `go` 解析成实际路径。
//
// 本机没有把 go 装进默认 PATH——它只在 mise 的 installs 目录下。门禁由 fixture 自己解析，
// 但探针是 harness 起的，所以这里补一次，免得把「工具链找不到」记成 flow 的缺陷。
func resolveGo(name string) string {
	if name != "go" {
		return name
	}
	if path, err := exec.LookPath("go"); err == nil {
		return path
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return name
	}
	matches, _ := filepath.Glob(filepath.Join(home, ".local/share/mise/installs/go/*/bin/go"))
	if len(matches) == 0 {
		return name
	}
	sort.Strings(matches)
	return matches[len(matches)-1]
}

// ---------------------------------------------------------------------------
// 断言：每条返回 (通过, 证据)
// ---------------------------------------------------------------------------

type Expectation struct {
	Text     string `json:"text"`
	Passed   bool   `json:"passed"`
	Evidence string `json:"evidence"`
}

func assertGate(caseID, workdir string, spec AssertionSpec) (bool, string) {
	command := spec.strs("command")
	if len(command) == 0 {
		command = []string{"make", "check"}
	}
	command[0] = resolveGo(command[0])
	out, code := runIn(workdir, command[0], command[1:]...)
	return code == 0, fmt.Sprintf("%s → exit %d\n%s", strings.Join(command, " "), code, tail(out, 400))
}

func assertProbe(caseID, workdir string, spec AssertionSpec) (bool, string) {
	caseDir := filepath.Join(evalsDir, "cases", caseID)
	command := spec.strs("command")
	if len(command) == 0 {
		return false, "probe 断言缺少 command"
	}
	command[0] = resolveGo(command[0])

	// 探针文件放进 workdir，跑完删掉——它们是 eval 基础设施，不属于被测仓库。
	var copied []string
	for _, pair := range spec["files"].([]any) {
		parts, _ := pair.([]any)
		if len(parts) != 2 {
			continue
		}
		src := filepath.Join(caseDir, parts[0].(string))
		dest := filepath.Join(workdir, parts[1].(string))
		if !exists(src) {
			return false, fmt.Sprintf("探针文件不存在：%s", src)
		}
		if err := os.MkdirAll(filepath.Dir(dest), 0o755); err != nil {
			return false, err.Error()
		}
		raw, err := os.ReadFile(src)
		if err != nil {
			return false, err.Error()
		}
		if err := os.WriteFile(dest, raw, 0o644); err != nil {
			return false, err.Error()
		}
		copied = append(copied, dest)
	}
	defer func() {
		for _, path := range copied {
			os.Remove(path)
		}
	}()

	configRel := spec.str("config")
	configAbs := ""
	if configRel != "" {
		configAbs = filepath.Join(workdir, configRel)
	}
	defer func() {
		if configAbs != "" {
			os.Remove(configAbs)
		}
	}()

	pattern := regexp.MustCompile(spec.str("extract"))
	if spec.str("extract") == "" {
		pattern = regexp.MustCompile(`(\{.*\})`)
	}

	ok := true
	var lines []string
	for _, scenario := range spec.scenarios() {
		label, _ := json.Marshal(scenario.Thresholds)
		if scenario.Thresholds == nil {
			label = []byte("null")
		}
		if configAbs != "" {
			if scenario.Thresholds == nil {
				os.Remove(configAbs)
			} else {
				os.MkdirAll(filepath.Dir(configAbs), 0o755)
				os.WriteFile(configAbs, mustJSONCompact(scenario.Thresholds), 0o644)
			}
		}
		out, code := runIn(workdir, command[0], command[1:]...)
		match := pattern.FindStringSubmatch(out)
		var observed map[string]any
		if len(match) > 1 {
			json.Unmarshal([]byte(match[1]), &observed)
		}
		if observed == nil {
			lines = append(lines, fmt.Sprintf("  %s → 探针没有输出可解析的 JSON（exit %d）%s",
				label, code, tail(out, 200)))
			ok = false
			continue
		}
		same := true
		for key, want := range scenario.Expect {
			// 按数值比较，且**缺键不算通过**——把观察值收成 int 时缺键会被当成 0，
			// 期望恰好是 0 的场景就会误判通过。
			got, present := observed[key]
			if !present || number(got) != float64(want) {
				same = false
			}
		}
		ok = ok && same
		got, _ := json.Marshal(observed)
		if same {
			lines = append(lines, fmt.Sprintf("  ok   %s → %s", label, got))
		} else {
			want, _ := json.Marshal(scenario.Expect)
			lines = append(lines, fmt.Sprintf("  FAIL %s → %s  期望 %s", label, got, want))
		}
	}
	return ok, strings.Join(lines, "\n")
}

// number 把 JSON 解码出来的数值统一成 float64。
func number(value any) float64 {
	switch typed := value.(type) {
	case float64:
		return typed
	case int:
		return float64(typed)
	case json.Number:
		parsed, _ := typed.Float64()
		return parsed
	}
	return math.NaN()
}

func mustJSONCompact(v any) []byte {
	raw, _ := json.Marshal(v)
	return raw
}

func assertPathGlob(caseID, workdir string, spec AssertionSpec) (bool, string) {
	matches, _ := filepath.Glob(filepath.Join(workdir, spec.str("glob")))
	need := spec.intOr("min", 1)
	return len(matches) >= need,
		fmt.Sprintf("%s → 命中 %d 个（需要 ≥%d）", spec.str("glob"), len(matches), need)
}

func assertPathAbsent(caseID, workdir string, spec AssertionSpec) (bool, string) {
	present := exists(filepath.Join(workdir, spec.str("glob")))
	state := "不存在"
	if present {
		state = "存在"
	}
	return !present, fmt.Sprintf("%s → %s", spec.str("glob"), state)
}

func assertCheckpointLocation(caseID, workdir string, spec AssertionSpec) (bool, string) {
	var found []string
	filepath.WalkDir(workdir, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		// 跳过隐藏目录（Python 的 glob `**` 不匹配隐藏项），否则 .git 之类会被扫进来
		if entry.IsDir() && path != workdir && strings.HasPrefix(entry.Name(), ".") {
			return filepath.SkipDir
		}
		if !entry.IsDir() && entry.Name() == ".loop-state.json" {
			found = append(found, path)
		}
		return nil
	})
	if len(found) == 0 {
		return true, "没有产生 loop 检查点（单单元模式不该产生，允许）"
	}
	var bad, good []string
	for _, path := range found {
		rel, _ := filepath.Rel(workdir, path)
		parts := strings.Split(rel, string(os.PathSeparator))
		// 期望 requirements/<scope>/issues/.loop-state.json
		if len(parts) == 4 && parts[0] == "requirements" && parts[2] == "issues" {
			good = append(good, rel)
		} else {
			bad = append(bad, rel)
		}
	}
	if len(bad) > 0 {
		return false, fmt.Sprintf("检查点落点不对：%s（期望 requirements/<scope>/issues/）",
			strings.Join(bad, "、"))
	}
	return true, "检查点落点正确：" + strings.Join(good, "、")
}

func assertWorkspaceClean(caseID, workdir string, spec AssertionSpec) (bool, string) {
	// 只报**本次运行新产生的**脏：materialize 时快照过 let-it-go 本来就有的脏，
	// 开发 eval 工作区本身时那份是非空的。
	before := map[string]bool{}
	if seed, err := loadSeed(workdir); err == nil {
		for _, line := range seed.LetitgoDirtyAtSeed {
			before[line] = true
		}
	}
	now := dirtyLines(repoDir)
	var fresh []string
	for _, line := range now {
		if before[line] {
			continue
		}
		// `evals/` 整个不算：那是 eval 工作区自己的家，跑一轮的过程里 harness、
		// 结果目录、fixture 定义本来就会变。仓库的其它内容仍然受检查——臂不该碰
		// `skills/`、`scripts/`、`docs/` 或根文件。
		//
		// 这条断言只在**跑臂期间仓库被冻结**时可信：Lead 顺手改一行 `skills/`
		// 会被记成臂的越界。run.md 里把这条写成了流程规则。
		if strings.Contains(line, "evals/") {
			continue
		}
		fresh = append(fresh, line)
	}
	if len(fresh) > 0 {
		return false, "本次运行往 let-it-go 工作树里写了东西：\n  " + strings.Join(fresh, "\n  ")
	}
	return true, fmt.Sprintf("let-it-go 工作树没有新脏（运行前已有 %d 条，运行后 %d 条）",
		len(before), len(now))
}

func assertTamperGuard(caseID, workdir string, spec AssertionSpec) (bool, string) {
	// fixture 自带的门禁与断言不许被改弱——DSH 那句「一个把测试废掉而不是把 bug 修好的
	// agent，应该在这里失败，而不是只栽在关键词探针上」说的就是这个。
	seed, err := loadSeed(workdir)
	if err != nil {
		return false, err.Error()
	}
	var problems, names []string
	for rel, want := range seed.Protected {
		names = append(names, rel)
		got, err := hashFile(filepath.Join(workdir, rel))
		if err != nil {
			problems = append(problems, rel+" 被删除")
		} else if got != want {
			problems = append(problems, rel+" 被改动")
		}
	}
	sort.Strings(names)
	if len(problems) > 0 {
		sort.Strings(problems)
		return false, "受保护文件被动过：" + strings.Join(problems, "、")
	}
	return true, "受保护文件逐字节未变：" + strings.Join(names, "、")
}

type assertFunc func(caseID, workdir string, spec AssertionSpec) (bool, string)

var assertKinds = map[string]assertFunc{
	"gate":                assertGate,
	"probe":               assertProbe,
	"path_glob":           assertPathGlob,
	"path_absent":         assertPathAbsent,
	"checkpoint_location": assertCheckpointLocation,
	"workspace_clean":     assertWorkspaceClean,
	"tamper_guard":        assertTamperGuard,
}

// ---------------------------------------------------------------------------
// grade / preflight
// ---------------------------------------------------------------------------

type Grade struct {
	CaseID       string        `json:"case_id"`
	CaseName     string        `json:"case_name"`
	Workdir      string        `json:"workdir"`
	Expectations []Expectation `json:"expectations"`
	Passed       int           `json:"passed"`
	Total        int           `json:"total"`
	PassRate     float64       `json:"pass_rate"`
}

type Preflight struct {
	CaseID         string        `json:"case_id"`
	Phase          string        `json:"phase"`
	Checks         []Expectation `json:"checks"`
	OK             bool          `json:"ok"`
	ProbeRedAtSeed bool          `json:"probe_red_at_seed"`
}

func grade(caseID, workdir string, c Case) Grade {
	var expectations []Expectation
	for _, spec := range c.Assertions {
		kind := spec.str("kind")
		text := spec.str("text")
		if text == "" {
			text = kind
		}
		handler, known := assertKinds[kind]
		if !known {
			expectations = append(expectations, Expectation{Text: text, Passed: false,
				Evidence: fmt.Sprintf("未知的断言类型 `%s`", kind)})
			continue
		}
		passed, evidence := handler(caseID, workdir, spec)
		expectations = append(expectations, Expectation{Text: text, Passed: passed, Evidence: evidence})
	}
	abs, _ := filepath.Abs(workdir)
	passed := 0
	for _, item := range expectations {
		if item.Passed {
			passed++
		}
	}
	rate := 0.0
	if len(expectations) > 0 {
		rate = float64(passed) / float64(len(expectations))
	}
	return Grade{CaseID: caseID, CaseName: c.Name, Workdir: abs,
		Expectations: expectations, Passed: passed, Total: len(expectations), PassRate: rate}
}

// preflight 检查起点：门禁必须绿、探针必须红。
//
// 探针在起点就绿，说明这条断言区分不了任何东西——DSH 自己的 swebench 冒烟测试
// 也是先 `expect(before.status).not.toBe(0)`。
func preflight(caseID, workdir string, c Case) Preflight {
	var checks []Expectation
	for _, spec := range c.Assertions {
		switch spec.str("kind") {
		case "gate":
			passed, evidence := assertGate(caseID, workdir, spec)
			checks = append(checks, Expectation{Text: "起点：fixture 自己的门禁是绿的",
				Passed: passed, Evidence: evidence})
		case "probe":
			passed, evidence := assertProbe(caseID, workdir, spec)
			checks = append(checks, Expectation{Text: "起点：行为探针是红的（需求确实还没实现）",
				Passed: !passed, Evidence: evidence})
		}
	}
	ok := true
	probeRed := true
	for _, check := range checks {
		if !check.Passed {
			ok = false
		}
		if strings.Contains(check.Text, "探针") {
			probeRed = check.Passed
		}
	}
	return Preflight{CaseID: caseID, Phase: "preflight", Checks: checks, OK: ok, ProbeRedAtSeed: probeRed}
}

// ---------------------------------------------------------------------------
// 子命令
// ---------------------------------------------------------------------------

func cmdMaterialize(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "usage: evalctl materialize <case-id> [--dest DIR] [--json]")
		return 2
	}
	caseID := args[0]
	dest := ""
	asJSON := false
	for i := 1; i < len(args); i++ {
		switch args[i] {
		case "--dest":
			i++
			if i < len(args) {
				dest = args[i]
			}
		case "--json":
			asJSON = true
		}
	}

	c, err := loadCase(caseID)
	if err != nil {
		fmt.Fprintln(os.Stderr, "materialize:", err)
		return 1
	}
	fixture := filepath.Join(evalsDir, "cases", caseID, c.Fixture)
	if !exists(fixture) {
		fmt.Fprintf(os.Stderr, "materialize: 用例没有 fixture 目录：%s\n", fixture)
		return 1
	}
	dest = repoPath(dest)
	if dest == "" {
		tmp, err := os.MkdirTemp("", "eval-"+caseID+"-")
		if err != nil {
			fmt.Fprintln(os.Stderr, "materialize:", err)
			return 1
		}
		dest = tmp
	} else if entries, err := os.ReadDir(dest); err == nil && len(entries) > 0 {
		fmt.Fprintf(os.Stderr, "materialize: 目标目录不是空的：%s\n", dest)
		return 1
	}

	if err := copyTree(fixture, dest); err != nil {
		fmt.Fprintln(os.Stderr, "materialize:", err)
		return 1
	}
	for _, command := range [][]string{
		{"init", "-q"},
		{"config", "user.email", "eval@let-it-go.local"},
		{"config", "user.name", "let-it-go eval"},
		{"add", "-A"},
		{"commit", "-q", "-m", "seed: eval fixture at its starting state"},
	} {
		if out, code := git(dest, command...); code != 0 {
			fmt.Fprintf(os.Stderr, "materialize: git %s 失败：%s\n", strings.Join(command, " "), out)
			return 1
		}
	}

	commit, _ := git(dest, "rev-parse", "HEAD")
	seed := Seed{
		CaseID:             caseID,
		CaseName:           c.Name,
		SeedCommit:         strings.TrimSpace(commit),
		Protected:          map[string]string{},
		ProtectedMissing:   []string{},
		LetitgoDirtyAtSeed: dirtyLines(repoDir),
	}
	if seed.LetitgoDirtyAtSeed == nil {
		// nil 切片会 marshal 成 null；schema 里它是数组，统一成 []
		seed.LetitgoDirtyAtSeed = []string{}
	}
	abs, _ := filepath.Abs(dest)
	seed.Workdir = abs
	for _, rel := range c.TamperGuard {
		hash, err := hashFile(filepath.Join(dest, rel))
		if err != nil {
			seed.ProtectedMissing = append(seed.ProtectedMissing, rel)
			continue
		}
		seed.Protected[rel] = hash
	}
	if err := os.WriteFile(seedPath(dest), mustJSON(seed), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "materialize:", err)
		return 1
	}

	if asJSON {
		os.Stdout.Write(mustJSON(seed))
		fmt.Println()
	} else {
		fmt.Println(abs)
		if len(seed.ProtectedMissing) > 0 {
			fmt.Fprintf(os.Stderr, "  警告：case.json 声明了 tamper_guard 但 fixture 里没有：%v\n",
				seed.ProtectedMissing)
		}
	}
	return 0
}

func copyTree(src, dst string) error {
	return filepath.WalkDir(src, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if entry.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		info, err := entry.Info()
		mode := os.FileMode(0o644)
		if err == nil {
			mode = info.Mode().Perm()
		}
		return os.WriteFile(target, raw, mode)
	})
}

func cmdAssert(args []string) int {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: evalctl assert <case-id> <workdir> --phase preflight|grade [--out FILE] [--json]")
		return 2
	}
	caseID, workdir := args[0], repoPath(args[1])
	phase, out, asJSON := "grade", "", false
	for i := 2; i < len(args); i++ {
		switch args[i] {
		case "--phase":
			i++
			if i < len(args) {
				phase = args[i]
			}
		case "--out":
			i++
			if i < len(args) {
				out = args[i]
			}
		case "--json":
			asJSON = true
		}
	}

	c, err := loadCase(caseID)
	if err != nil {
		fmt.Fprintln(os.Stderr, "assert:", err)
		return 1
	}

	var payload any
	if phase == "preflight" {
		payload = preflight(caseID, workdir, c)
	} else {
		payload = grade(caseID, workdir, c)
	}
	if out != "" {
		// --out 的父目录不存在时自动建：跑一轮要手写多级路径，
		// 让人先去 mkdir 是没必要的摩擦。
		if err := os.MkdirAll(filepath.Dir(repoPath(out)), 0o755); err != nil {
			fmt.Fprintln(os.Stderr, "assert:", err)
			return 1
		}
		if err := os.WriteFile(repoPath(out), mustJSON(payload), 0o644); err != nil {
			fmt.Fprintln(os.Stderr, "assert:", err)
			return 1
		}
	}
	if asJSON {
		os.Stdout.Write(mustJSON(payload))
		fmt.Println()
	} else if phase == "preflight" {
		result := payload.(Preflight)
		for _, check := range result.Checks {
			fmt.Printf("  %s %s\n", mark(check.Passed), check.Text)
			fmt.Printf("       %s\n", firstLine(check.Evidence))
		}
		verdict := "不通过"
		if result.OK {
			verdict = "通过"
		}
		fmt.Printf("  → preflight %s\n", verdict)
	} else {
		result := payload.(Grade)
		for _, item := range result.Expectations {
			fmt.Printf("  %s %s\n", mark(item.Passed), item.Text)
			for _, line := range strings.Split(item.Evidence, "\n") {
				fmt.Printf("       %s\n", line)
			}
		}
		fmt.Printf("  → %d/%d 通过（%.0f%%）\n", result.Passed, result.Total, result.PassRate*100)
	}

	if phase == "preflight" {
		if payload.(Preflight).OK {
			return 0
		}
		return 1
	}
	// grade：**全部通过才 0**——「有通过就 0」会把 6/7 记成成功。
	if payload.(Grade).Passed == payload.(Grade).Total {
		return 0
	}
	return 1
}

func mark(passed bool) string {
	if passed {
		return "ok  "
	}
	return "FAIL"
}

func firstLine(text string) string {
	if index := strings.Index(text, "\n"); index >= 0 {
		return text[:index]
	}
	return text
}

func cmdSelfcheck(_ []string) int {
	var problems []string
	dirs := caseDirs()
	if len(dirs) == 0 {
		fmt.Fprintln(os.Stderr, "selfcheck: evals/cases/ 下没有用例")
		return 1
	}
	for _, name := range dirs {
		problems = append(problems, selfcheckCase(name)...)
	}
	if !exists(filepath.Join(evalsDir, "arms.json")) {
		problems = append(problems, "缺 arms.json（两条臂的 prompt 后缀）")
	} else {
		raw, _ := os.ReadFile(filepath.Join(evalsDir, "arms.json"))
		// 用 map[string]any 而不是 struct：arms.json 里还有一个 `_comment` 键
		// （JSON 没有注释，用下划线键是惯例），解进 struct 会让整份文件失败。
		var arms map[string]any
		if err := json.Unmarshal(raw, &arms); err != nil {
			problems = append(problems, "arms.json 不是合法 JSON")
		} else {
			for _, arm := range []string{"with_skill", "without_skill"} {
				entry, _ := arms[arm].(map[string]any)
				if suffix, _ := entry["suffix"].(string); suffix == "" {
					problems = append(problems, fmt.Sprintf("arms.json 缺 `%s.suffix`", arm))
				}
			}
		}
	}

	if len(problems) > 0 {
		fmt.Fprintf(os.Stderr, "eval 工作区有 %d 处问题：\n", len(problems))
		for _, problem := range problems {
			fmt.Fprintf(os.Stderr, "  - %s\n", problem)
		}
		return 1
	}
	fmt.Printf("ok: %d 个用例结构完好（fixture 无 .git、探针齐、tamper_guard 指得到、两条臂的后缀都在）\n",
		len(dirs))
	return 0
}

func selfcheckCase(name string) []string {
	var problems []string
	caseDir := filepath.Join(evalsDir, "cases", name)
	raw, err := os.ReadFile(filepath.Join(caseDir, "case.json"))
	if err != nil {
		return []string{name + ": 没有 case.json"}
	}
	var c Case
	if err := json.Unmarshal(raw, &c); err != nil {
		return []string{fmt.Sprintf("%s: case.json 不是合法 JSON：%v", name, err)}
	}
	for field, value := range map[string]string{
		"id": c.ID, "name": c.Name, "prompt": c.Prompt,
	} {
		if value == "" {
			problems = append(problems, fmt.Sprintf("%s: case.json 缺 `%s`", name, field))
		}
	}
	if len(c.Assertions) == 0 {
		problems = append(problems, name+": case.json 缺 `assertions`")
	}
	if c.ID != name {
		problems = append(problems, fmt.Sprintf("%s: case.json 的 id 是 `%s`，与目录名不一致", name, c.ID))
	}

	fixture := filepath.Join(caseDir, c.Fixture)
	if !exists(fixture) {
		problems = append(problems, name+": 没有 fixture 目录")
	} else {
		if exists(filepath.Join(fixture, ".git")) {
			problems = append(problems, name+": fixture 里有 .git —— 嵌套仓库无法被 let-it-go 正常入库，版本控制留给运行时")
		}
		if !exists(filepath.Join(fixture, "AGENTS.md")) {
			problems = append(problems, name+": fixture 缺 AGENTS.md —— 它自己的地图正是被测对象之一")
		}
	}
	for _, rel := range c.TamperGuard {
		if !exists(filepath.Join(fixture, rel)) {
			problems = append(problems, fmt.Sprintf("%s: tamper_guard 指的 `%s` 在 fixture 里不存在", name, rel))
		}
	}

	kinds := map[string]bool{}
	for _, spec := range c.Assertions {
		kind := spec.str("kind")
		kinds[kind] = true
		if _, known := assertKinds[kind]; !known {
			problems = append(problems, fmt.Sprintf("%s: 未知的断言类型 `%s`", name, kind))
		}
	}
	if !kinds["gate"] {
		problems = append(problems, name+": 缺少 `gate` 断言")
	}
	if !kinds["probe"] {
		problems = append(problems, name+": 缺少 `probe` 断言（没有探针的用例只有文件树断言，区分度弱）")
	}
	if !kinds["tamper_guard"] {
		problems = append(problems, name+": 缺少 `tamper_guard` —— 没有它，把门禁改弱换绿是能通过的")
	}

	probeDir := filepath.Join(caseDir, "probe")
	entries, err := os.ReadDir(probeDir)
	if err != nil || len(entries) == 0 {
		problems = append(problems, name+": 没有 probe/ 目录（探针文件放这里）")
	}
	return problems
}

func cmdList(_ []string) int {
	for _, name := range caseDirs() {
		c, err := loadCase(name)
		if err != nil {
			fmt.Printf("  %-16s （case.json 读不了）\n", name)
			continue
		}
		fmt.Printf("  %-16s %s\n", name, c.Name)
		fmt.Printf("      %s\n", c.WhatItTests)
	}
	return 0
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, strings.Join([]string{
			"usage: evalctl <command> [args]",
			"",
			"  materialize <case-id> [--dest DIR] [--json]",
			"  assert <case-id> <workdir> --phase preflight|grade [--out FILE] [--json]",
			"  bench <iteration-dir> [--skill-name NAME] [--executor-model M]",
			"  selfcheck",
			"  list",
		}, "\n"))
		os.Exit(2)
	}
	command, rest := os.Args[1], os.Args[2:]
	switch command {
	case "materialize":
		os.Exit(cmdMaterialize(rest))
	case "assert":
		os.Exit(cmdAssert(rest))
	case "bench":
		os.Exit(cmdBench(rest))
	case "selfcheck":
		os.Exit(cmdSelfcheck(rest))
	case "list":
		os.Exit(cmdList(rest))
	default:
		fmt.Fprintf(os.Stderr, "evalctl: 未知子命令 `%s`\n", command)
		os.Exit(2)
	}
}
