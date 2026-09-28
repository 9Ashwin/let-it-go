# /review-it 的 Codex 运行时说明

这份说明只映射 Codex 下的独立评审调用；Spec / Standards 两轴、八个评审维度、证据要求与放行判据仍以 [`../SKILL.md`](../SKILL.md) 和 [`../../CONTRACT.md`](../../CONTRACT.md) 为准。DSH 映射见 [`dsh-runtime.md`](dsh-runtime.md)。

## 派发独立评审者

用当前工具列表里的 `spawn_agent` 启动一个**新上下文**的评审者。Codex 有两族协作工具，同一台机器只暴露一族：V2 是 `collaboration.spawn_agent`，新上下文设 `fork_turns: "none"`；V1 是 `multi_agent_v1__spawn_agent`，新上下文设 `fork_context: false` **并且**显式给 `agent_type: "default"`（V1 省略 `agent_type` 等于按父级做全历史 fork）。不要用继承当前对话的子代理，也不要把写实现的节点代理当评审者。

评审提示词必须自包含，至少给出：

- 评审目标及其绝对路径：未提交改动、明确的分支比较，或 graph 波级集成 diff；
- 对应的 issue / PRD / SPEC 验收条件；找不到 spec 时，明确要求按用户原始请求评；
- 本技能的 Spec 轴（missing / extra / wrong）、Standards 轴八个维度、证据门槛和报告格式；
- 明确要求只读评审、只返回发现与结论，不要修改文件或修复发现。

新上下文不保证加载了当前会话里的 `/review-it` 技能正文，因此不要只写“按技能评审”。评审者与编排器共享文件系统，Codex 工具也不一定能强制只读；评审委派本身不得要求它改文件，返回后检查工作树，确认它没有留下改动。

## 等待与收尾

评审结论是后续修复或放行的前提时，用等待工具（V2 `collaboration.wait_agent`、V1 `multi_agent_v1__wait_agent`）等到评审者结算；不要把「已派发」报告成「已评审」。需要补充信息或继续同一个评审者时用对应那对工具（V2 `send_message` / `followup_task`，V1 `send_input` / `resume_agent`；V1 没有列出当前代理的工具）。若运行时没有可用的独立子代理能力，保留评审为未完成并说明原因，不把自审冒充独立评审。

拿到结论后，作者只核实和处理具体发现；修改后重跑受影响的门禁，并对新的 diff 再派独立评审。Shell 会话的轮询只用于读取长命令结果，不是评审代理的等待机制。不要依赖 DSH 的 `run_in_background`、`job_*`、`todo_write` 或结束通知语义。
