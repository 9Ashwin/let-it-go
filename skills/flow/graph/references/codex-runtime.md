# /graph 的 Codex 运行时说明

这份说明只把 `/graph` 的中性动作映射到 Codex 工具。节点划分、隔离、检查点、fan-in 与放行规则仍以 [`../SKILL.md`](../SKILL.md) 和 [`../../CONTRACT.md`](../../CONTRACT.md) 为准；DSH 映射见 [`dsh-runtime.md`](dsh-runtime.md)。

## 委派

这里用的是普通子代理，不建立 Agent Teams。

**工具名以你当前的工具列表为准**：Codex 有两族协作工具，同一台机器只会暴露其中一族（源码里
`multi_agent_version` 决定，V1 的命名空间是 `multi_agent_v1`、V2 是 `collaboration`）。

| 需要 | V2（`collaboration`） | V1（`multi_agent_v1`） |
|---|---|---|
| 启动节点或独立评审者 | `collaboration.spawn_agent` | `multi_agent_v1__spawn_agent` |
| 等待代理返回 | `collaboration.wait_agent` | `multi_agent_v1__wait_agent` |
| 查看仍在运行的代理 | `collaboration.list_agents` | **V1 没有这个工具** |
| 给运行中的代理补充信息 | `collaboration.send_message` | `multi_agent_v1__send_input` |
| 继续空闲的失败节点 | `collaboration.followup_task` | `multi_agent_v1__resume_agent` |
| 中断卡住的代理 | `collaboration.interrupt_agent` | `multi_agent_v1__close_agent` |

**新节点的上下文隔离也按族走**：V2 设 `fork_turns: "none"`；V1 设 `fork_context: false`，并且
**要显式给 `agent_type: "default"`**——V1 的 `agent_type` 说明写着「省略时按父级类型做全历史
fork」。两族的 `spawn_agent` 都**没有 `cwd` 参数**。

启动图节点时把节点提示词写完整：验收条件、绝对 worktree 路径、分支、门禁、检查点协议和边界都要包含。子代理不应再派生子代理；一波里每个节点由编排器直接派发。

子代理与编排器共享文件系统。**独立上下文不等于独立工作目录**，并行节点必须各自使用 worktree。提示词里给出 worktree 的绝对路径，并要求每条 shell 命令都显式设置 `workdir`，或在命令内 `cd` 到该路径。不要依赖相对路径或先前命令留下的目录状态。

## worktree 与波屏障

用仓库自己的默认分支和节点分支布局建 worktree；例如：

```bash
ROOT="$(git rev-parse --show-toplevel)"
BASE="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
BASE="${BASE:-$(git rev-parse --abbrev-ref HEAD)}"
WT="$ROOT/.graph-worktrees/node-{N}"
git worktree add -b feat/node-{N}-{slug} "$WT" "$BASE"
```

把 `$WT` 和节点分支写入节点记录，再将 `$WT` 的绝对路径交给代理。Codex 管理的 worktree 也可以使用，但创建 worktree 不会自动把代理的 shell 切到那里；仍需在提示词和每条 shell 调用中明确路径。

每波直接派发该波的节点，保存每个代理 id 与节点号的对应关系，然后用 `wait_agent` 等到整波结算再 fan-in。遵守运行时当前可用的代理并发额度；额度不足时分批启动，不要让多个节点共用一个 worktree。不要轮询未变化的状态。

fan-in 时检查节点分支的实际 diff、运行门禁并核对验收证据。代理报告只是自述，不是 evidence。合并前确认编排器检出没有被节点意外改动。失败节点可用「补充信息 / 继续」那对工具（V2 的 `send_message` / `followup_task`，V1 的 `send_input` / `resume_agent`）原地续做；达到技能中的失败边界后保留 worktree 并记录状态。

Codex 的 goal 能力按当前宿主工具规则使用；不要把普通 `/graph` 请求自动解释成创建 goal 的授权。跨轮恢复以 `.graph_state.json` 为准，不以代理列表或聊天记录代替检查点。

## 长命令与独立评审

Codex shell 工具若返回 session id，就用对应的 session 工具读取该命令的后续输出；这只管理一个 shell 命令，不代替图检查点或代理状态。不要假定 DSH 的 `workflow`、`job_*`、`todo_write` 或 `present` 工具存在。

fan-in 后按 `/graph` 规定评审集成结果。编排器没有写节点代码时，小 diff 可由编排器内联检查；需要独立或对抗性评审时，再用 `spawn_agent` 以「新上下文」参数启动评审者（V2 `fork_turns: "none"`；V1 `fork_context: false` + `agent_type: "default"`），并等待结论。评审目标与输出标准必须在提示词里自包含。
