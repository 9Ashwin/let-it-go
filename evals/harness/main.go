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
func abs0(path string) string {
	abs, err := filepath.Abs(path)
	if err != nil {
		return path
	}
	return abs
}

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
	ID          string `json:"id"`
	Name        string `json:"name"`
	WhatItTests string `json:"what_it_tests"`
	Prompt      string `json:"prompt"`
	ExpectedOut string `json:"expected_output"`
	Fixture     string `json:"fixture"`
	// Tier 是用例所属的层：`t1` 是小任务 + 只读事件流的过程断言（分钟级，每次改 SKILL 正文
	// 都跑）；留空 = `t2`，现有的结果用例（小时级，发版前跑）。分层按「要花多少钱」分，
	// 不按重要性分——见 evals/NEXT.md。
	Tier string `json:"tier"`
	// UndeclaredWorkspace 声明「这个 fixture **故意**没有 AGENTS.md / 作用域根声明」。
	// 默认每个 fixture 都要有地图，因为流程的产物落点靠它；但「没声明时会怎样」也是一条
	// 真实路径（技能写着「仓库完全没约定时用默认值 tasks/<feature>/」），测它就必须没有地图。
	// 做成显式字段而不是删掉那条检查：误删地图仍然要在自检里报出来。
	UndeclaredWorkspace bool            `json:"undeclared_workspace"`
	TamperGuard         []string        `json:"tamper_guard"`
	Assertions          []AssertionSpec `json:"assertions"`
	unknownFields       []string
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

// Seed 只放断言真正要读的东西。它曾经还带 case_id / case_name / workdir /
// seed_commit，但没有任何地方读——纯粹是**写给被测臂看的线索**：实测有臂读到
// case_id 之后 `find $HOME -maxdepth 6 -name 04-serial-batch`，直接找到了用例
// 定义（断言就在里面），然后照着期望值做。
type Seed struct {
	Protected        map[string]string `json:"protected"`
	ProtectedMissing []string          `json:"protected_missing_at_seed"`
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
	Kind     string `json:"kind"`
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
	// 探针要写配置文件，跑完必须把**原样**还回去。只删不还的话，一次 grade 就把臂
	// 留下的产物毁掉，第二次 grade 的结果就不是同一次运行的了（实测踩到过：
	// 臂的测试依赖那份配置，重跑时突然变红）。
	if configAbs != "" {
		original, readErr := os.ReadFile(configAbs)
		existed := readErr == nil
		defer func() {
			if existed {
				os.WriteFile(configAbs, original, 0o644)
			} else {
				os.Remove(configAbs)
			}
		}()
	}

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

// findCheckpoints 找出工作树里所有的 loop 检查点。
func findCheckpoints(workdir string) []string {
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
	return found
}

// assertCheckpointAbsent 检查**没有**产生 loop 检查点。
//
// 契约 §3 把「单单元零仪式」写成硬契约：不碰检查点、不建 worktree、不开 graph 波次。
// `checkpoint_location` 只约束「产生了就放对地方」——它允许产生，守不住零仪式。
func assertCheckpointAbsent(caseID, workdir string, spec AssertionSpec) (bool, string) {
	found := findCheckpoints(workdir)
	if len(found) == 0 {
		return true, "没有产生 loop 检查点（单单元模式：零仪式）"
	}
	rels := make([]string, 0, len(found))
	for _, path := range found {
		rel, _ := filepath.Rel(workdir, path)
		rels = append(rels, rel)
	}
	return false, "单单元模式不该产生检查点，却找到了：" + strings.Join(rels, "、")
}

func assertCheckpointLocation(caseID, workdir string, spec AssertionSpec) (bool, string) {
	found := findCheckpoints(workdir)
	if len(found) == 0 {
		return true, "没有产生 loop 检查点（单单元模式不该产生，允许）"
	}
	// 作用域根是**仓库的事实**，不是通用事实：技能说「仓库有约定就用它的根，没约定才用
	// 默认的 tasks/」。所以期望的根要能由用例指定，写死 requirements/ 会让「没声明根」的
	// 用例即使做对了也判错。
	root := spec.str("root")
	if root == "" {
		root = "requirements"
	}
	var bad, good []string
	for _, path := range found {
		rel, _ := filepath.Rel(workdir, path)
		parts := strings.Split(rel, string(os.PathSeparator))
		// 期望 <root>/<scope>/issues/.loop-state.json
		if len(parts) == 4 && parts[0] == root && parts[2] == "issues" {
			good = append(good, rel)
		} else {
			bad = append(bad, rel)
		}
	}
	if len(bad) > 0 {
		return false, fmt.Sprintf("检查点落点不对：%s（期望 %s/<scope>/issues/）",
			strings.Join(bad, "、"), root)
	}
	return true, "检查点落点正确：" + strings.Join(good, "、")
}

// assertWorkspaceClean 检查臂有没有写到 fixture 外面去。
//
// 早先的版本拿**环境里那个 let-it-go 仓库的脏状态**当基准。那是个坏设计，有两个原因：
// 一是 DSH 自己的 `benchmarks/AGENTS.md` 明说「不要用 ambient repositories」——
// 量出来的东西取决于你此刻在工作区里改了什么，而不是臂做了什么；二是它两次把
// Lead 的动作记成臂的越界（改了 `.gitignore` 那次）。
//
// 现在只看 **fixture 的父目录**：那是 harness 自己的地盘（`grading.json` 这些），
// 臂往里写任何别的东西就是越界。headless 的沙箱本来就只允许工作区与 /tmp，
// 所以这条是廉价的兜底，不是主要防线。
func assertWorkspaceClean(caseID, workdir string, spec AssertionSpec) (bool, string) {
	parent := filepath.Dir(filepath.Clean(workdir))
	// 只在 harness 自己的运行目录里才有意义：那里除了 `work/` 与 harness 自己写的
	// 那几样，不该有别的东西。手工把 fixture 铺到 /tmp 下时父目录是 /tmp，
	// 满屏都是无关文件——那种情况下如实说「不适用」，而不是报一堆假越界。
	if !exists(filepath.Join(parent, "work.seed.json")) {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断越界"
	}
	entries, err := os.ReadDir(parent)
	if err != nil {
		return false, fmt.Sprintf("读不了 fixture 的父目录 %s：%v", parent, err)
	}
	var fresh []string
	for _, entry := range entries {
		name := entry.Name()
		if allowedInRunDir(name) {
			continue
		}
		fresh = append(fresh, name)
	}
	if len(fresh) > 0 {
		return false, "臂往 fixture 外面写了东西（在 " + parent + " 下）：\n  " +
			strings.Join(fresh, "\n  ")
	}
	return true, fmt.Sprintf("fixture 外面没有多出东西（%s 下 %d 项，全是 harness 自己的）",
		parent, len(entries))
}

// allowedInRunDir 列出 harness 自己在运行目录里放的东西。
func allowedInRunDir(name string) bool {
	switch name {
	case "work", "work.origin.git", "work.seed.json", "tmp",
		"grading.json", "timing.json", "notes.md", "events.jsonl",
		"eval_metadata.json", "preflight.json", "outputs":
		// `tmp` 是臂自己的 TMPDIR 与 GOCACHE（见 runHeadless）：并发跑时必须让每条臂
		// 只看得到自己的临时目录，否则一条 `ls $TMPDIR` 就能看到别的臂正在做的解。
		return true
	}
	return false
}

// assertToolAbsent 读同一次运行的事件流，确认 `tools` 里点名的工具一次都没被调用。
//
// 有些边界在文件系统里看不到：单单元模式「不开图」不会留下任何文件，而编排式的
// `workflow` 调用会出现在 events.jsonl 里。事件流是 harness 自己的产物、不在 workdir
// 内，所以和 workspace_clean 一样从 fixture 的父目录读。断言哪些工具由用例自己的
// `tools` 字段决定。
//
// **读不到事件流判红，不判「不适用」**：一次真实运行至少会调用几次工具，读不到或解析到
// 零个 `tool_call`，说明这次运行的记录不可核实（dsh 没吐事件、或事件字段改了名），
// 把它记成通过就是一条假绿。唯一说「不适用」的场合和 workspace_clean 相同——
// 父目录不是 harness 的运行目录（没有 work.seed.json），那是手工铺开、无从判断。
func assertToolAbsent(caseID, workdir string, spec AssertionSpec) (bool, string) {
	tools := spec.strs("tools")
	raw, applicable, err := runEventsIn(workdir)
	if !applicable {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断工具调用"
	}
	if err != nil {
		return false, err.Error()
	}
	toolCalls, byName := countToolCalls(raw)
	if toolCalls == 0 {
		return false, "事件流里一条 tool_call 都没有 —— 这次运行没跑起来，或者事件格式变了，无法核实"
	}
	var called []string
	for _, tool := range tools {
		if n := byName[tool]; n > 0 {
			called = append(called, fmt.Sprintf("%s×%d", tool, n))
		}
	}
	if len(called) > 0 {
		sort.Strings(called)
		return false, "被调用了：" + strings.Join(called, "、")
	}
	return true, fmt.Sprintf("事件流里 %d 次工具调用，没有 %s", toolCalls, strings.Join(tools, "、"))
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
	"checkpoint_absent":   assertCheckpointAbsent,
	"workspace_clean":     assertWorkspaceClean,
	"tool_absent":         assertToolAbsent,
	"tamper_guard":        assertTamperGuard,
	// T1 的只读过程断言（见 events.go）：量的是契约本身，不是结果。
	"skill_loaded":   assertSkillLoaded,
	"goal_opened":    assertGoalOpened,
	"no_human_wait":  assertNoHumanWait,
	"evidence_layer": assertEvidenceLayer,
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
			expectations = append(expectations, Expectation{Text: text, Kind: kind, Passed: false,
				Evidence: fmt.Sprintf("未知的断言类型 `%s`", kind)})
			continue
		}
		passed, evidence := handler(caseID, workdir, spec)
		expectations = append(expectations, Expectation{Text: text, Kind: kind, Passed: passed, Evidence: evidence})
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
	// 只跑**第一条** gate：那是 fixture 自己的门禁。后面的 gate 是结构性检查
	// （分支数、产物形状之类），起点必然还不满足——拿它们卡 preflight 是错的。
	seenGate := false
	for _, spec := range c.Assertions {
		switch spec.str("kind") {
		case "gate":
			if seenGate {
				continue
			}
			seenGate = true
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
		// 身份与提交信息都要中性：`let-it-go eval` / `seed: eval fixture` 等于
		// 在第一条命令（`git log`）里就告诉臂「你在被评测」，那是在邀请它去找评分标准。
		{"config", "user.email", "dev@example.com"},
		{"config", "user.name", "dev"},
		{"add", "-A"},
		{"commit", "-q", "-m", "chore: initial import"},
	} {
		if out, code := git(dest, command...); code != 0 {
			fmt.Fprintf(os.Stderr, "materialize: git %s 失败：%s\n", strings.Join(command, " "), out)
			return 1
		}
	}

	// 给 fixture 一个**真的 origin**（本地 bare 仓库）：loop-it 的串行前置检查要
	// `git ls-remote --heads origin`，没有 remote 会在第一步就停下——那样测的就不是
	// 流程，而是「评测环境没有远端」。本地 bare 不需要网络，也不会碰 GitHub。
	//
	// 它放在 fixture 的 `.git/` **里面**：headless 的沙箱只允许写工作区，放在外面时
	// `git push` 会被拒（`unable to create temporary object directory`），于是「推到
	// origin」这条要求变成不可完成——那是环境问题，不是被测的东西。放进 `.git/` 之后
	// 沙箱允许，且 `git status` 看不见它。
	origin := filepath.Join(abs0(dest), ".git", "eval-origin.git")
	if out, code := runIn("", "git", "init", "--bare", "-q", origin); code != 0 {
		fmt.Fprintf(os.Stderr, "materialize: 建 origin 失败：%s\n", out)
		return 1
	}
	for _, command := range [][]string{
		{"remote", "add", "origin", origin},
		{"push", "-q", "origin", "HEAD:refs/heads/main"},
		{"symbolic-ref", "HEAD", "refs/heads/main"},
	} {
		if out, code := git(dest, command...); code != 0 {
			fmt.Fprintf(os.Stderr, "materialize: git %s 失败：%s\n", strings.Join(command, " "), out)
			return 1
		}
	}

	seed := Seed{
		Protected:        map[string]string{},
		ProtectedMissing: []string{},
	}
	for _, rel := range c.TamperGuard {
		hash, err := hashFile(filepath.Join(dest, rel))
		if err != nil {
			seed.ProtectedMissing = append(seed.ProtectedMissing, rel)
			continue
		}
		seed.Protected[rel] = hash
	}
	abs, _ := filepath.Abs(dest)
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

// selfcheckTriggers 校验触发用例集。
//
// 和 check_skills.py 的 `scripts/` 守卫同一条理由：`expect` 里写错一个技能名，跑出来的
// 是「这个 prompt 路由错了」，而不是「你把名字拼错了」——一条假的红比没有更糟。
func selfcheckTriggers() []string {
	raw, err := os.ReadFile(filepath.Join(evalsDir, "triggers.json"))
	if err != nil {
		return []string{"缺 triggers.json（触发用例集）"}
	}
	var set triggerSet
	if err := json.Unmarshal(raw, &set); err != nil {
		return []string{fmt.Sprintf("triggers.json 不是合法 JSON：%v", err)}
	}
	var problems []string
	if strings.TrimSpace(set.Suffix) == "" {
		problems = append(problems, "triggers.json 缺 suffix（附加在每条 prompt 后面的那句）")
	}
	known := map[string]bool{}
	for _, bucket := range []string{"flow", "bonus", "vendor"} {
		entries, err := os.ReadDir(filepath.Join(evalsDir, "..", "skills", bucket))
		if err != nil {
			continue
		}
		for _, entry := range entries {
			if entry.IsDir() {
				known[entry.Name()] = true
			}
		}
	}
	if len(known) == 0 {
		problems = append(problems, "读不到 skills/*/ —— 没法校验 expect 里的技能名")
	}
	seen := map[string]bool{}
	for _, c := range set.Cases {
		if c.ID == "" || strings.TrimSpace(c.Prompt) == "" {
			problems = append(problems, "triggers.json 有用例缺 id 或 prompt")
			continue
		}
		if seen[c.ID] {
			problems = append(problems, c.ID+": id 重复")
		}
		seen[c.ID] = true
		for _, name := range c.Expect {
			if !known[name] {
				problems = append(problems, fmt.Sprintf("%s: expect 里的 `%s` 不是任何一个桶里的技能", c.ID, name))
			}
		}
	}
	return problems
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

	problems = append(problems, selfcheckTriggers()...)

	if len(problems) > 0 {
		fmt.Fprintf(os.Stderr, "eval 工作区有 %d 处问题：\n", len(problems))
		for _, problem := range problems {
			fmt.Fprintf(os.Stderr, "  - %s\n", problem)
		}
		return 1
	}
	fmt.Printf("ok: %d 个用例结构完好（fixture 无 .git、探针齐、tamper_guard 指得到、两条臂的后缀都在）；触发用例集完好\n",
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
		if !exists(filepath.Join(fixture, "AGENTS.md")) && !c.UndeclaredWorkspace {
			problems = append(problems, name+": fixture 缺 AGENTS.md —— 它自己的地图正是被测对象之一。"+
				"若这条用例测的就是「没声明时会怎样」，在 case.json 里加 \"undeclared_workspace\": true")
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
		fmt.Printf("  %-16s [%s] %s\n", name, c.tier(), c.Name)
		fmt.Printf("      %s\n", c.WhatItTests)
	}
	return 0
}

// tier 是用例所属的层，缺省 t2：只有显式写了 `"tier": "t1"` 的才是小任务用例。
func (c Case) tier() string {
	if c.Tier == "" {
		return "t2"
	}
	return c.Tier
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, strings.Join([]string{
			"usage: evalctl <command> [args]",
			"",
			"  materialize <case-id> [--dest DIR] [--json]",
			"  assert <case-id> <workdir> --phase preflight|grade [--out FILE] [--json]",
			"  run <case-id> --arm with_skill|without_skill --out DIR [--dsh PATH] [--keep]",
			"  bench <iteration-dir> [--skill-name NAME] [--executor-model M]",
			"  trigger [--out DIR] [--dsh PATH] [--only ID] [--parallel N] [--repeat N]",
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
	case "run":
		os.Exit(cmdRun(rest))
	case "bench":
		os.Exit(cmdBench(rest))
	case "trigger":
		os.Exit(cmdTrigger(rest))
	case "selfcheck":
		os.Exit(cmdSelfcheck(rest))
	case "list":
		os.Exit(cmdList(rest))
	default:
		fmt.Fprintf(os.Stderr, "evalctl: 未知子命令 `%s`\n", command)
		os.Exit(2)
	}
}
