# loop-it 的 Codex 运行时说明

这份说明把 `/loop-it` 的中性动作映射到 Codex。单单元 / 串行批次的判据、检查点 schema、状态转换与 evidence 规则仍以 [`../SKILL.md`](../SKILL.md)、[`../CONTRACT.md`](../CONTRACT.md) 和 `scripts/loop_state.py` 为准；DSH 映射见 [`dsh-runtime.md`](dsh-runtime.md)。

## 单单元

单单元就在当前 Codex task 内联完成：不建 worktree、不为一件小事派子代理。运行项目门禁并逐条记录实际 evidence，按 `/review-it` 的 Codex 运行时说明完成独立评审，再按 `/ship-it` 交付。

## 串行批次

`.loop-state.json` 是跨回合恢复的机器真相。运行 `loop_state.py` 的 `scan`、`next`、`set`、`evidence`、`followup` 与 `summary`；每条 issue 的状态转换由编排者在核实真实结果之后写入。不要用代理报告、对话记录或 UI 任务清单替代检查点。

需要委派实现时用普通子代理。**工具名以你当前的工具列表为准**：Codex 有两族协作工具，同一台机器只暴露其中一族（源码里 `multi_agent_version` 决定，V1 的命名空间是 `multi_agent_v1`、V2 是 `collaboration`）。

| 需要 | V2（`collaboration`） | V1（`multi_agent_v1`） |
|---|---|---|
| 派发一个 issue | `collaboration.spawn_agent` | `multi_agent_v1__spawn_agent` |
| 等待代理结算 | `collaboration.wait_agent` | `multi_agent_v1__wait_agent` |
| 查看代理状态 | `collaboration.list_agents` | **V1 没有这个工具** |
| 给运行中的代理补充信息 | `collaboration.send_message` | `multi_agent_v1__send_input` |
| 继续空闲的代理 | `collaboration.followup_task` | `multi_agent_v1__resume_agent` |
| 中断卡住的代理 | `collaboration.interrupt_agent` | `multi_agent_v1__close_agent` |

每张卡都用**新上下文**参数（V2 `fork_turns: "none"`；V1 `fork_context: false` **加** `agent_type: "default"`——V1 省略 `agent_type` 等于按父级做全历史 fork），并把 issue 正文、绝对仓库路径、需求分支、门禁命令、冻结文件与检查点协议放进自包含提示词。Codex 子代理与编排者共享文件系统；串行批次复用同一需求分支时，一次只让一个代理改工作树，父级等它结算并核验后再开始下一张卡。`spawn_agent` 没有 `cwd` 参数，提示词要写明绝对路径，代理的每条 shell 调用也要显式指定 `workdir` 或先 `cd`。

只有需要结论才能继续时才等待代理：用等待工具等结果；「补充信息」那个工具只对运行中的代理生效，代理空闲时要「继续」它才会动（V2 是 `send_message` / `followup_task`，V1 是 `send_input` / `resume_agent`）。不要把“已派发”当作完成，也不要把异步通知当成检查点。

长构建或测试若返回 shell session id，记录该 id，并用 Codex 提供的 session 输出工具读取最终退出状态与结果；不要只看第一段输出就写 evidence。每条命令都是新的 shell 进程，`cd` 与变量不会跨命令保留。若当前 Codex 环境提供任务清单，可把它作为可见进度；没有对应工具时不补造第二份持久状态，检查点仍是恢复依据。

串行批次只有一条需求分支，按 issue 顺序推进，不为每张卡另建并行 worktree。新会话接手时按 CONTRACT §7 读取 issue、检查点和最近提交，再从 `loop_state.py next` 继续；不要从旧聊天推断状态。

## goal 与跨回合续跑

本技能中的自动 `create_goal` / `update_goal` 生命周期描述的是 DSH 行为。Codex 的 goal 工具按当前宿主授权规则调用；**不要仅因收到一批 issue，就推断用户授权创建 goal**。若用户明确要求创建长周期 goal 且当前 Codex 工具允许，才按工具说明创建，并在目标完成时关闭它。

没有获准的活动 goal 时，在当前 task 中持续推进；如果回合中断，检查点保留位置，之后按上面的恢复步骤接着做。检查点不能替代实际续跑，聊天中的“继续”也不能替代检查点。

## 与 DSH 的差异

- `run_in_background: false`、`job_*`、`todo_write`、`skill` 与 DSH 的结束通知不是 Codex 工具契约；不要照抄这些名字。
- 需要独立评审时，按 [`../../review-it/references/codex-runtime.md`](../../review-it/references/codex-runtime.md) 派发新上下文并等待结论。
- Codex 可用的子代理数量与后台命令行为取决于当前 host；按实际工具结果判断，不假设固定额度或自动重试。
