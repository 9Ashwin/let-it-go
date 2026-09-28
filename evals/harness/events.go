package main

// 只读事件流的过程断言：T1 层量的是「过程事实」，不是结果。
//
// 结果断言（gate / probe / tamper_guard）回答「东西做出来没有」；这一层回答技能契约本身：
// 加载了哪个技能、开没开 goal、有没有停在等人、检查点里的证据带没带层。它们全部**只读**
// 已经发生的观测——`dsh --json` 的事件流与工作树本身——不读臂的自述。
//
// 事件流是 harness 自己的产物、不在 workdir 内，所以和 workspace_clean / tool_absent 一样
// 从 fixture 的父目录读。**读不到就判红，不判「不适用」**：一次真实运行至少会调用几次工具，
// 读不到或解析到零个 tool_call，说明这次运行的记录不可核实，记成通过就是一条假绿。

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// runEventsIn 读同一次运行的事件流。
//
// 第二个返回值是「不适用」：父目录不是 harness 的运行目录（没有 work.seed.json），
// 那是手工把 fixture 铺到别处、无从判断的场合，如实说「不适用」而不是报假红。
func runEventsIn(workdir string) (string, bool, error) {
	parent := filepath.Dir(filepath.Clean(workdir))
	if !exists(filepath.Join(parent, "work.seed.json")) {
		return "", false, nil
	}
	path := filepath.Join(parent, "events.jsonl")
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", true, fmt.Errorf("读不到事件流 %s —— 这次运行的过程无法核实", path)
	}
	return string(raw), true, nil
}

// countToolCalls 数事件流里的工具调用：总数 + 按名字。
func countToolCalls(raw string) (int, map[string]int) {
	byName := map[string]int{}
	total := 0
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var event struct {
			Type string `json:"type"`
			Tool string `json:"tool"`
		}
		if json.Unmarshal([]byte(line), &event) != nil || event.Type != "tool_call" {
			continue
		}
		total++
		if event.Tool != "" {
			byName[event.Tool]++
		}
	}
	return total, byName
}

// lastToolCall 返回事件流里最后一次工具调用的名字。
func lastToolCall(raw string) string {
	last := ""
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		var event struct {
			Type string `json:"type"`
			Tool string `json:"tool"`
		}
		if json.Unmarshal([]byte(line), &event) != nil || event.Type != "tool_call" {
			continue
		}
		last = event.Tool
	}
	return last
}

// assertSkillLoaded 读事件流，核对**第一个**加载的技能。
//
// 只看 `skill` 工具调用，不看模型的自述：它说「我打算加载 X」和它真的加载 X 是两件事。
// 期望为空 = 这件事不该加载任何技能（平凡请求）。判定只看路由决策（第一个），不看之后的
// 串联——技能本来就互相点名下游阶段，串联属于编排质量，由结果用例量。
func assertSkillLoaded(caseID, workdir string, spec AssertionSpec) (bool, string) {
	expect := spec.strs("expect")
	raw, applicable, err := runEventsIn(workdir)
	if !applicable {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断加载了什么"
	}
	if err != nil {
		return false, err.Error()
	}
	total, _ := countToolCalls(raw)
	if total == 0 {
		return false, "事件流里一条 tool_call 都没有 —— 这次运行没跑起来，或者事件格式变了，无法核实"
	}
	loaded := skillsLoaded(raw)
	chain := "（没加载）"
	if len(loaded) > 0 {
		chain = strings.Join(loaded, " → ")
	}
	if len(expect) == 0 {
		if len(loaded) == 0 {
			return true, "没有加载任何技能（期望如此）"
		}
		return false, "这件事不该加载技能，却加载了：" + chain
	}
	if len(loaded) == 0 {
		return false, "没有加载任何技能，期望先加载 " + strings.Join(expect, " 或 ")
	}
	for _, name := range expect {
		if name == loaded[0] {
			return true, "先加载了 " + loaded[0] + "（链：" + chain + "）"
		}
	}
	return false, "先加载的是 " + loaded[0] + "，期望 " + strings.Join(expect, " 或 ") + "（链：" + chain + "）"
}

// assertGoalOpened 读事件流，确认这一轮开过 goal（`create_goal`）。
//
// CONTRACT §6：人交来一批活，开工先 `create_goal`——它是唯一让循环不靠人推的东西。
// 单单元任务不该断言这条：goal 的门禁是「长跑目标」，不是「单回合能做完的事」。
func assertGoalOpened(caseID, workdir string, spec AssertionSpec) (bool, string) {
	raw, applicable, err := runEventsIn(workdir)
	if !applicable {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断 goal"
	}
	if err != nil {
		return false, err.Error()
	}
	total, byName := countToolCalls(raw)
	if total == 0 {
		return false, "事件流里一条 tool_call 都没有 —— 这次运行没跑起来，或者事件格式变了，无法核实"
	}
	if n := byName["create_goal"]; n > 0 {
		return true, fmt.Sprintf("事件流里 create_goal ×%d", n)
	}
	return false, "事件流里没有 create_goal —— 这一轮没有开 goal（CONTRACT §6：人交来的活开工先开 goal）"
}

// humanWaitPatterns 是「以等人类回复结束回合」的文字信号。
//
// 这是一条**文字传感器**，不是结构事实——所以它刻意收得很紧：只收在历史运行上零误报的形态。
// 宽一点的写法（`需要你…`、`等你…`）在真实产物上误报过：一条臂写的是「没有停在『等你回复』」，
// 另一条写的是「需要你知道的取舍」——都是正常总结，不是等人。
//
// 校准记录：34 份历史 final 文本里只有 1 条命中，正是那次真实的等待
// （iteration-9 的 04-serial-batch/with_skill：「等待后台评审返回，收到结论后继续批末收尾与 push」，
// 唯一没过的断言就是它没把分支推到 origin）。
var humanWaitPatterns = []*regexp.Regexp{
	regexp.MustCompile(`等待[^\n]{0,12}(返回|回复|答复)`),
	regexp.MustCompile(`收到[^\n]{0,10}(结论|回复|结果|消息)[^\n]{0,8}后`),
	regexp.MustCompile(`请你?(确认|拍板|裁决)`),
	regexp.MustCompile(`(?i)(awaiting|waiting for (your|the)|let me know|please confirm)`),
}

// assertNoHumanWait 确认这一轮没有停在「等你回复」上。
//
// CONTRACT §5：无人值守下问不到人不是失败，**停在「等你回复」上是唯一一定错的做法**——
// headless 里 `turn_end: completed` 就是这个回合的终点，等下去等于把剩下的活丢掉。
//
// 两个信号：最后一次工具调用是 `ask_user_question`（回合就停在问题上），或者结尾那段话命中
// humanWaitPatterns（在等一个还没回来的结果）。
func assertNoHumanWait(caseID, workdir string, spec AssertionSpec) (bool, string) {
	raw, applicable, err := runEventsIn(workdir)
	if !applicable {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断"
	}
	if err != nil {
		return false, err.Error()
	}
	total, _ := countToolCalls(raw)
	if total == 0 {
		return false, "事件流里一条 tool_call 都没有 —— 这次运行没跑起来，或者事件格式变了，无法核实"
	}
	if last := lastToolCall(raw); last == "ask_user_question" {
		return false, "回合停在 ask_user_question 上 —— headless 里没人可答（CONTRACT §5）"
	}
	_, finalText := parseEvents(raw)
	for _, pattern := range humanWaitPatterns {
		if match := pattern.FindString(finalText); match != "" {
			return false, "结尾在等人：" + strings.TrimSpace(match) +
				"\n  —— headless 里回合到此为止，剩下的活不会发生（CONTRACT §5）"
		}
	}
	if strings.TrimSpace(finalText) == "" {
		return false, "事件流里没有 final 文本 —— 这次运行的过程无法核实"
	}
	return true, "结尾没有等待人类的信号（最后一句：" + firstLine(strings.TrimSpace(finalText)) + "）"
}

// assertEvidenceLayer 读检查点，确认里面的证据带了层。
//
// CONTRACT §4：每条验收条件先标它要哪一层，再给那一层的证据；层级写在证据里
// （`evidence add --layer`），缺层如实记录。`shipped` 的闸门只对「一条都没标层」告警，
// 所以这条断言守的是那个告警管不住的部分：检查点里到底有没有层。
//
// 判定：至少一条 evidence 记录，且**每条**都带合法的 L1–L4。
// assertSkillChain 断言这些技能**按顺序**出现在加载链里（不要求相邻）。
//
// 它跟 `skill_loaded` 的分工：后者只看第一段（T0 与 T1 都用），前者守**接力**——「第一个
// 加载对了、第二个没接上」从它下面溜过去。踩过一次真事故：空仓库 + 一句大诉求，模型加载
// `prd`、写完 PRD 就直接开写代码，整条链一步没走，直到用户当面追问才回头。
//
// **它只能在 T1 这一层测**，别放回 T0：T0 的 prompt 只有「用户话 + 先加载对应技能」，模型
// 会把它当路由题来答（实测三次里两次只调了 1–2 次工具，交一段「该加载谁」的说明就结束回合，
// PRD 没写、第二跳根本没机会出现）。T1 有 fixture 和真任务，才看得到链。
func assertSkillChain(caseID, workdir string, spec AssertionSpec) (bool, string) {
	chain := spec.strs("chain")
	if len(chain) == 0 {
		return false, "skill_chain 断言缺 `chain`（要按顺序出现的技能名）"
	}
	raw, applicable, err := runEventsIn(workdir)
	if !applicable {
		return true, "不适用：这个 fixture 不在 harness 的运行目录里（父目录没有 work.seed.json），无从判断加载了什么"
	}
	if err != nil {
		return false, err.Error()
	}
	total, _ := countToolCalls(raw)
	if total == 0 {
		return false, "事件流里一条 tool_call 都没有 —— 这次运行没跑起来，或者事件格式变了，无法核实"
	}
	names := skillsLoaded(raw)
	next := 0
	for _, got := range names {
		if next < len(chain) && got == chain[next] {
			next++
		}
	}
	if next == len(chain) {
		return true, "接力链完整：" + strings.Join(names, " → ")
	}
	missing := strings.Join(chain[next:], "、")
	return false, fmt.Sprintf("接力断了：期望按顺序出现 %s，缺 %s（实际链：%s）",
		strings.Join(chain, " → "), missing, joinOrNone(names, nil, nil))
}

func assertEvidenceLayer(caseID, workdir string, spec AssertionSpec) (bool, string) {
	found := findCheckpoints(workdir)
	if len(found) == 0 {
		return false, "没有找到 loop 检查点（.loop-state.json）—— 读不到证据层"
	}
	type evidenceRecord struct {
		Kind   string `json:"kind"`
		Layer  string `json:"layer"`
		Result string `json:"result"`
	}
	// 每个检查点都要**重新解**：把这个结构放在循环外，第二个文件若不带 `issues`，
	// `Unmarshal` 会保留上一个文件留下的 map——空检查点会被前一个的数据盖住。
	valid := map[string]bool{"L1": true, "L2": true, "L3": true, "L4": true}
	totalRecords := 0
	var missing, lines []string
	for _, path := range found {
		raw, err := os.ReadFile(path)
		if err != nil {
			return false, "读不了检查点 " + path + "：" + err.Error()
		}
		var checkpoint struct {
			Issues map[string]struct {
				Evidence []evidenceRecord `json:"evidence"`
			} `json:"issues"`
		}
		if err := json.Unmarshal(raw, &checkpoint); err != nil {
			return false, "检查点不是合法 JSON：" + path
		}
		rel, _ := filepath.Rel(workdir, path)
		var numbers []string
		for number := range checkpoint.Issues {
			numbers = append(numbers, number)
		}
		sort.Strings(numbers)
		for _, number := range numbers {
			entry := checkpoint.Issues[number]
			layers := map[string]int{}
			for _, record := range entry.Evidence {
				totalRecords++
				if valid[record.Layer] {
					layers[record.Layer]++
				} else {
					missing = append(missing, fmt.Sprintf("issue %s 的 evidence 缺层或层非法（kind=%s, layer=%q）",
						number, record.Kind, record.Layer))
				}
			}
			if len(entry.Evidence) == 0 {
				missing = append(missing, fmt.Sprintf("issue %s 一条 evidence 都没有", number))
				continue
			}
			var parts []string
			for _, layer := range []string{"L1", "L2", "L3", "L4"} {
				if layers[layer] > 0 {
					parts = append(parts, fmt.Sprintf("%s×%d", layer, layers[layer]))
				}
			}
			lines = append(lines, fmt.Sprintf("issue %s: %d 条（%s）", number, len(entry.Evidence), strings.Join(parts, "、")))
		}
		lines = append(lines, "  检查点："+rel)
	}
	if totalRecords == 0 {
		return false, "检查点里一条 evidence 记录都没有 —— 证据层无从谈起"
	}
	if len(missing) > 0 {
		return false, strings.Join(missing, "\n")
	}
	return true, "证据带了层：" + strings.Join(lines, "；")
}
