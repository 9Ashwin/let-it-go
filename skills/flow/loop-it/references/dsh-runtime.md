# DSH runtime notes for loop-it

Read this when you run the serial loop under DeepSeek Harness: the body's
neutral actions (delegate, task list, background job) map to the tools, config
keys and discovery rules below.

## Loading and invoking this skill

DSH discovers a skill at `<root>/<name>/SKILL.md` or `<root>/<name>.md` one
level below a scanned root. Nested trees such as this repo's
`skills/<bucket>/<name>/` are deliberately not discovered, which is why the
bundle lists every bucket as its own root (`cordis.patch.yml`) and a copied
`~/.agents/skills/loop-it` works flat. Roots are ranked, and the filesystem
provider resolves a duplicate skill name by rank, lowest first:

| Rank | Source | Path |
|---|---|---|
| 100 | project DSH | `<projectRoot>/.dsh/skills` |
| 200 | project agents | `<projectRoot>/.agents/skills` |
| 300 | custom | `Config.customSkillDirs` |
| 400 | user DSH | `$DSH_HOME/skills` (default `~/.dsh/skills`) |
| 500 | user agents | `$DSH_AGENTS_HOME/skills` (default `~/.agents/skills`) |
| 600 | bundled | `bundledSkillDir`, when configured |

`projectRoot` is the nearest ancestor holding `.git`. The `skill` tool loads by
exact name and returns the body in a canonical `<skill_content>` block together
with a `<skill_resources>` resource block; its directory form reads
`Base directory for this skill: <path>`, and that absolute path is what
`<SKILL_DIR>` resolves from. Typing `/loop-it` is the human entry point (a
user-invocable skill is injected directly), and `disable-model-invocation` is
the catalog opt-out. This skill is model-invocable, so both paths work.

## Delegation

| Need | Tool |
|---|---|
| Do one issue inline (the loop default) | — |
| Start a fresh child | `subagent` |
| Start a child that inherits this conversation | `subagent_fork` |
| Continue / retry a child | `send_message(child_id, …)` |
| Interrupt a child's current turn | `interrupt_agent(child_id)` |
| Audit the children you started | `list_agents(scope="descendants")` |

Calls to `subagent` run in the background by default and return a durable child id
immediately, so several calls in one assistant message are concurrent — the host caps how
many tool calls overlap in one step (ten by default), and the parent is notified when a
child settles, so never poll. `subagent_fork` is the opposite: one-shot and foreground,
so reach for it when you want the answer in the same turn.

**Delegation depth is capped at 1** (`maxDepth`, default), which means a child cannot
delegate at all. A node that needs a second level of work has to do it itself. Per-child
`toolFilter` and `persona` are deployment-level plugin config, not skill fields. A child
cannot escalate its own permissions; under the read-only and workspace-write policies its
approval policy is pinned to `never`.

## Task list, background work, long-horizon goals

- `todo_write` keeps the task list, one row per issue; `job_*` (`job_list`,
  `job_output`, `job_kill`) runs and collects a long build or test as a
  background job. DSH has no `present` — hand the report over as an absolute
  path.
- `/goal` is a DSH command — the human-facing half of the goal surface — not a
  skill the loop runs. The model-facing half is `create_goal` / `update_goal`, and
  its gate is **authority, not wording**: `create_goal` runs only in a direct
  top-level human turn, so neither a subagent nor a goal round can mint one. That
  does **not** mean waiting for the word "goal" — when the human hands over a
  long-running objective ("work through this whole batch"), creating the goal *is*
  the designed behaviour, and it is what keeps the session working between turns.
  `edit` / `pause` / `resume` carry the same restriction; `complete` / `blocked`
  are also allowed during this goal's own rounds, and `blocked` is refused before
  the configured minimum round count. After a restart an active goal is disarmed,
  so a human saying "continue" needs `resume` to rearm it.

  **A batch is the case this exists for.** The goal is the session-scoped driver —
  it is what re-prompts the loop after a turn ends — while `.loop-state.json` is
  the repo-scoped record of *where* the batch is. They are two different things and
  two different counters: `maxGoalRounds` bounds the continuation, `attempts`
  counts one issue's retries. Never let the goal substitute for the checkpoint, and
  never let the checkpoint stand in for the goal: without one of them a long batch
  either loses its place or stops moving.
