package main

// 只读事件流断言的负例自测。
//
// 存在的理由就是那条红线：**每条断言都要能失败**——从不失败的传感器说明它不必要。
// 这些用例把每条传感器喂给一份**故意做错**的观测（没加载技能、没开 goal、结尾在等人、
// 证据缺层、调了不该调的工具），确认它真的判红；再喂一份做对的，确认它判绿。
//
// 没有这层自测，「两边满分」就分不清是「技能做对了」还是「传感器坏了」。

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// fakeRun 铺一个 harness 运行目录：`<parent>/work/` + `<parent>/work.seed.json` + `<parent>/events.jsonl`。
// events 为空串时不写事件流——那是「记录不可核实」的场合，必须判红。
func fakeRun(t *testing.T, events string) string {
	t.Helper()
	parent := t.TempDir()
	work := filepath.Join(parent, "work")
	if err := os.MkdirAll(work, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(parent, "work.seed.json"), []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}
	if events != "" {
		if err := os.WriteFile(filepath.Join(parent, "events.jsonl"), []byte(events), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	return work
}

func eventLines(lines ...string) string {
	return strings.Join(lines, "\n") + "\n"
}

const (
	evSkillLoop   = `{"type":"tool_call","tool":"skill","input":{"name":"loop-it"}}`
	evSkillGraph  = `{"type":"tool_call","tool":"skill","input":{"name":"graph"}}`
	evBash        = `{"type":"tool_call","tool":"bash","input":{"command":"ls"}}`
	evGoal        = `{"type":"tool_call","tool":"create_goal","input":{"objective":"做完这批"}}`
	evWorkflow    = `{"type":"tool_call","tool":"workflow","input":{}}`
	evAskUser     = `{"type":"tool_call","tool":"ask_user_question","input":{}}`
	evFinalOK     = `{"type":"final","text":"做完了，门禁绿。"}`
	evFinalWaits  = `{"type":"final","text":"（等待后台评审返回，收到结论后继续批末收尾与 push。）"}`
	evFinalThanks = `{"type":"final","text":"没有停在「等你回复」上，也没有需要你知道的取舍。"}`
)

func TestSkillLoaded(t *testing.T) {
	cases := []struct {
		name   string
		events string
		expect []any
		want   bool
	}{
		{"先加载了期望的技能", eventLines(evSkillLoop, evBash), []any{"loop-it"}, true},
		{"先加载的是别的技能", eventLines(evSkillGraph, evSkillLoop), []any{"loop-it"}, false},
		{"一个技能都没加载", eventLines(evBash), []any{"loop-it"}, false},
		{"平凡请求不该加载技能", eventLines(evBash), []any{}, true},
		{"平凡请求却加载了", eventLines(evSkillLoop), []any{}, false},
		{"读不到事件流判红", "", []any{"loop-it"}, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			work := fakeRun(t, tc.events)
			passed, evidence := assertSkillLoaded("t", work, AssertionSpec{"expect": tc.expect})
			if passed != tc.want {
				t.Fatalf("passed=%v want=%v（证据：%s）", passed, tc.want, evidence)
			}
		})
	}
}

func TestGoalOpened(t *testing.T) {
	cases := []struct {
		name   string
		events string
		want   bool
	}{
		{"开了 goal", eventLines(evBash, evGoal), true},
		{"没开 goal", eventLines(evBash), false},
		{"读不到事件流判红", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			work := fakeRun(t, tc.events)
			if passed, evidence := assertGoalOpened("t", work, nil); passed != tc.want {
				t.Fatalf("passed=%v want=%v（证据：%s）", passed, tc.want, evidence)
			}
		})
	}
}

func TestNoHumanWait(t *testing.T) {
	cases := []struct {
		name   string
		events string
		want   bool
	}{
		{"正常收尾", eventLines(evBash, evFinalOK), true},
		{"结尾在等后台评审", eventLines(evBash, evFinalWaits), false},
		{"回合停在 ask_user_question", eventLines(evBash, evAskUser, evFinalOK), false},
		{"「没有停在等你回复」不算等待", eventLines(evBash, evFinalThanks), true},
		{"没有 final 文本判红", eventLines(evBash), false},
		{"读不到事件流判红", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			work := fakeRun(t, tc.events)
			if passed, evidence := assertNoHumanWait("t", work, nil); passed != tc.want {
				t.Fatalf("passed=%v want=%v（证据：%s）", passed, tc.want, evidence)
			}
		})
	}
}

// writeCheckpoint 在 work 下铺一份 loop 检查点。
func writeCheckpoint(t *testing.T, work, body string) {
	t.Helper()
	dir := filepath.Join(work, "requirements", "01_REQ-demo", "issues")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, ".loop-state.json"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestEvidenceLayer(t *testing.T) {
	cases := []struct {
		name       string
		checkpoint string
		want       bool
	}{
		{"每条证据都带层", `{"issues":{"1":{"evidence":[{"kind":"test","layer":"L1"},{"kind":"runtime","layer":"L3"}]}}}`, true},
		{"证据缺层", `{"issues":{"1":{"evidence":[{"kind":"test","layer":"L1"},{"kind":"runtime"}]}}}`, false},
		{"层非法", `{"issues":{"1":{"evidence":[{"kind":"test","layer":"L9"}]}}}`, false},
		{"一条证据都没有", `{"issues":{"1":{"evidence":[]}}}`, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			work := fakeRun(t, eventLines(evBash))
			writeCheckpoint(t, work, tc.checkpoint)
			if passed, evidence := assertEvidenceLayer("t", work, nil); passed != tc.want {
				t.Fatalf("passed=%v want=%v（证据：%s）", passed, tc.want, evidence)
			}
		})
	}
	t.Run("没有检查点", func(t *testing.T) {
		work := fakeRun(t, eventLines(evBash))
		if passed, evidence := assertEvidenceLayer("t", work, nil); passed {
			t.Fatalf("没有检查点该判红（证据：%s）", evidence)
		}
	})
}

// TestToolAbsent 守的是重构后的等价性：tool_absent 现在和其余过程断言共用事件流读取。
func TestToolAbsent(t *testing.T) {
	spec := AssertionSpec{"tools": []any{"workflow"}}
	cases := []struct {
		name   string
		events string
		want   bool
	}{
		{"没开图", eventLines(evBash, evFinalOK), true},
		{"开了图", eventLines(evBash, evWorkflow, evFinalOK), false},
		{"读不到事件流判红", "", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			work := fakeRun(t, tc.events)
			if passed, evidence := assertToolAbsent("t", work, spec); passed != tc.want {
				t.Fatalf("passed=%v want=%v（证据：%s）", passed, tc.want, evidence)
			}
		})
	}
}

// TestNotApplicableOutsideRunDir：手工把 fixture 铺到别处时，父目录没有 work.seed.json，
// 过程断言如实说「不适用」而不是报假红——这是唯一允许的通过型不适用。
func TestNotApplicableOutsideRunDir(t *testing.T) {
	work := t.TempDir()
	for name, check := range map[string]func() (bool, string){
		"skill_loaded":  func() (bool, string) { return assertSkillLoaded("t", work, AssertionSpec{"expect": []any{"loop-it"}}) },
		"goal_opened":   func() (bool, string) { return assertGoalOpened("t", work, nil) },
		"no_human_wait": func() (bool, string) { return assertNoHumanWait("t", work, nil) },
	} {
		passed, evidence := check()
		if !passed || !strings.Contains(evidence, "不适用") {
			t.Fatalf("%s：期望「不适用」型通过，得到 passed=%v（%s）", name, passed, evidence)
		}
	}
}
