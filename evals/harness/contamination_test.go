package main

// 污染检测器的自测。它守的判据是「臂伸手碰评测目录了吗」，而这个判据出过一次假阳性，
// 那次事故的形状值得钉死在这里：
//
// 臂照技能要求读了 `CONTRACT.md`，契约正文里带着路径字面量 `evals/cases/...`，于是
// **每一条 with_skill 运行**都被标成污染，而 `bench` 照收——那份数字因此不可信。
//
// 修法是两处：契约改掉那句字面量，`selfcheck` 加守卫不许技能正文再写进去（`selfcheckSkillText`）。
// 检测器保持简单——**只扫工具入参和工具返回**，不扫 `thinking` / `text` / `final`：模型在推理里
// 复述一个路径不等于它访问了那里。

import "testing"

func TestContaminationDetector(t *testing.T) {
	cases := []struct {
		name   string
		events string
		want   int
	}{
		{
			name: "读技能集里的 CONTRACT.md（正文干净）——不算",
			events: eventLines(
				`{"type":"tool_call","callId":"c1","tool":"read","input":{"file_path":"/Users/x/.agents/skills/CONTRACT.md"}}`,
				`{"type":"tool_result","callId":"c1","status":"completed","result":"111: 单单元路径上出现 .loop-state.json 就是错的"}`,
			),
			want: 0,
		},
		{
			name: "读了契约，又在思考里复述带路径的那句话——不算（不看 thinking）",
			events: eventLines(
				`{"type":"tool_call","callId":"c1","tool":"read","input":{"file_path":"/Users/x/.agents/skills/CONTRACT.md"}}`,
				`{"type":"tool_result","callId":"c1","status":"completed","result":"111: 单单元就是错的"}`,
				`{"type":"thinking","text":"契约说 evals/cases/01-single-unit 用机械断言守着"}`,
				`{"type":"text","text":"我按 evals/cases/01-single-unit 那条做"}`,
			),
			want: 0,
		},
		{
			name: "技能正文违规写了字面量——算（自检会先拦，但真发生就要报）",
			events: eventLines(
				`{"type":"tool_call","callId":"c2","tool":"skill","input":{"name":"loop-it"}}`,
				`{"type":"tool_result","callId":"c2","status":"completed","result":"<skill_content>…evals/cases/01-single-unit…"}`,
			),
			want: 1,
		},
		{
			name: "直接去读用例定义——算",
			events: eventLines(
				`{"type":"tool_call","callId":"c3","tool":"read","input":{"file_path":"../../evals/cases/t1-single-unit/case.json"}}`,
				`{"type":"tool_result","callId":"c3","status":"completed","result":"{\"assertions\":[…}"}`,
			),
			want: 1,
		},
		{
			name: "入参干净但结果泄漏了别的臂的路径——算",
			events: eventLines(
				`{"type":"tool_call","callId":"c4","tool":"bash","input":{"command":"ls $TMPDIR"}}`,
				`{"type":"tool_result","callId":"c4","status":"completed","result":"cache-123/evals/results/iteration-16"}`,
			),
			want: 1,
		},
		{
			name: "干净的一次运行——不算",
			events: eventLines(
				`{"type":"tool_call","callId":"c5","tool":"bash","input":{"command":"make check"}}`,
				`{"type":"tool_result","callId":"c5","status":"completed","result":"ok"}`,
				`{"type":"final","text":"做完了"}`,
			),
			want: 0,
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := contaminationIn(tc.events)
			if len(got) != tc.want {
				t.Fatalf("contaminationIn = %v，期望 %d 个标记", got, tc.want)
			}
		})
	}
}
