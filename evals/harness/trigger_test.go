package main

// 触发评估的两处承重逻辑的自测。
//
// 一、`forbid`：调用轴的闸门。DSH 的 `skill` 工具对 `disable-model-invocation` 的技能返回
// isError，所以「它加载不了」这条断言不能写成「什么都不许加载」——链上出现别的合法技能
//（实测：说「合入吧」时模型会先加载 `ship-it`）不算违反调用轴。
//
// 二、`skillsLoaded` 只认**成功**的加载：模型会猜名字（实测编过一个 `use-git-worktree`），
// 把失败的尝试记成「加载了」正好把闸门测反。

import "testing"

func TestTriggerPass(t *testing.T) {
	cases := []struct {
		name   string
		expect []string
		forbid []string
		loaded []string
		want   bool
	}{
		{"forbid：链上没有它就算过", nil, []string{"merge-it"}, []string{"ship-it"}, true},
		{"forbid：链上有它就判红", nil, []string{"merge-it"}, []string{"merge-it"}, false},
		{"forbid：排在第二也判红", nil, []string{"merge-it"}, []string{"ship-it", "merge-it"}, false},
		{"expect 缺省：不判加载了什么", nil, nil, []string{"ship-it"}, true},
		{"expect []：要求什么都没加载", []string{}, nil, []string{"ship-it"}, false},
		{"expect []：真没加载就过", []string{}, nil, nil, true},
		{"expect 非空：只看第一个", []string{"loop-it"}, nil, []string{"graph", "loop-it"}, false},
		{"expect 非空：第一个对上就过", []string{"loop-it"}, nil, []string{"loop-it", "review-it"}, true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := triggerPass(tc.expect, tc.forbid, tc.loaded); got != tc.want {
				t.Fatalf("triggerPass(%v, %v, %v) = %v，期望 %v", tc.expect, tc.forbid, tc.loaded, got, tc.want)
			}
		})
	}
}

func TestSkillsLoadedIgnoresFailedCalls(t *testing.T) {
	ok := eventLines(
		`{"type":"tool_call","callId":"c1","tool":"skill","input":{"name":"loop-it"}}`,
		`{"type":"tool_result","callId":"c1","status":"completed","result":"<skill_content…"}`,
	)
	if got := skillsLoaded(ok); len(got) != 1 || got[0] != "loop-it" {
		t.Fatalf("成功加载该被记下，得到 %v", got)
	}

	// user-invoked 的技能：DSH 的 skill 工具返回 isError，这不是「加载了」。
	rejected := eventLines(
		`{"type":"tool_call","callId":"c2","tool":"skill","input":{"name":"merge-it"}}`,
		`{"type":"tool_result","callId":"c2","status":"error","result":"skill \"merge-it\" is unknown or no longer available"}`,
	)
	if got := skillsLoaded(rejected); len(got) != 0 {
		t.Fatalf("被拒的调用不算加载，得到 %v", got)
	}

	// 混在一起：只有成功的那条算数。
	mixed := eventLines(
		`{"type":"tool_call","callId":"c3","tool":"skill","input":{"name":"use-git-worktree"}}`,
		`{"type":"tool_result","callId":"c3","status":"error","result":"unknown"}`,
		`{"type":"tool_call","callId":"c4","tool":"skill","input":{"name":"graph"}}`,
		`{"type":"tool_result","callId":"c4","status":"completed","result":"<skill_content…"}`,
	)
	got := skillsLoaded(mixed)
	if len(got) != 1 || got[0] != "graph" {
		t.Fatalf("只有成功的那条该算，得到 %v", got)
	}
}
