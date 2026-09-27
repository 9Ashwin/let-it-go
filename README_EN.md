<div align="right">
  <span>[<a href="./README_EN.md">English</a>]</span>
  <span>[<a href="./README.md">简体中文</a>]</span>
</div>

<div align="center">
  <h1>let-it-go</h1>
  <p>A complete software workflow inside your coding agent: requirements → design → breakdown → parallel implementation → review → shipping.<br>
  Skills make the judgment calls; ordering and checkpoints go to tested scripts; implementation goes to subagents isolated in their own git worktree.</p>
  <div align="center">
    <a href="https://9ashwin.github.io/let-it-go/"><img src="https://img.shields.io/badge/%E5%9C%A8%E7%BA%BF%E6%96%87%E6%A1%A3-9ashwin.github.io-d97757" alt="Online docs" /></a>
    <img src="https://img.shields.io/github/license/9Ashwin/let-it-go" alt="License" />
    <img src="https://img.shields.io/github/stars/9Ashwin/let-it-go?style=social" alt="Stars" />
    <img src="https://img.shields.io/github/forks/9Ashwin/let-it-go?style=social" alt="Forks" />
    <img src="https://img.shields.io/github/last-commit/9Ashwin/let-it-go" alt="Last commit" />
  </div>
  <h3>
    <a href="https://9ashwin.github.io/let-it-go/">Online docs</a> ·
    <a href="#quick-start">Install</a> ·
    <a href="#skills">Skills</a> ·
    <a href="#how-it-runs">Workflow</a> ·
    <a href="#project-status">Project Status</a>
  </h3>
</div>

## What is let-it-go?

let-it-go is a set of development-workflow skills: 25 skills that take a change from "an idea" to "shipped code" through standard steps — requirements, design, breakdown, implementation, review, shipping — each owned by one skill. You say what you want; the agent asks the questions, writes the PRD, splits it into contract-carrying Issues, implements in parallel inside isolated worktrees, reviews, opens the PR and merges.

**An implementation node is a subagent** in its own git worktree, and its job stops at "implement → prove it against the project's gates → commit on its own branch". Leak check, integration, gates on the integrated tree, review and shipping are one step, done **once per wave**: a single PR closes every Issue the wave satisfies.

Ordering, layering, cycle detection and checkpointing are arithmetic, and they live in the Python scripts shipped with the skills (standard library only, with self-tests). The skills themselves carry only judgement: **scripts do the arithmetic, skills do the judgement**.

## Quick Start

### Option 1: Install as a skill directory (recommended)

```bash
npx skills add 9Ashwin/let-it-go       # installs globally (~/.agents/skills)
npx skills update -g                    # update from source later
```

The skills land in `~/.agents/skills`, and this route changes nothing in any profile's dependencies.

`npx skills` scans recursively and flattens `skills/<bucket>/<skill>` into `~/.agents/skills/<skill>` — a skill root is scanned only one level deep, so the flattening is required. Copying by hand means doing that step yourself:

```bash
cp -R <let-it-go>/skills/flow/graph ~/.agents/skills/graph   # flattened, not the bucket
```

### Option 2: Install as a DSH bundle (optional)

It can also be installed as **deployment configuration** (a preset that travels with the package, `toolFilter`, persona, commit pinning) — the commands and flags are in the docs: **<https://9ashwin.github.io/let-it-go/#install>**.

> [!TIP]
> Not sure which skill to reach for? Type **`/ask-flow`** — it picks the next step **and starts it**, stopping only when two routes are genuinely close.
>
> The full usage guide (installation, how to trigger each step, acceptance criteria, FAQ) lives at **<https://9ashwin.github.io/let-it-go/>**, which redirects to the Chinese or English version based on your browser language; in the repo it is [docs/index_cn.html](docs/index_cn.html) and [docs/index_en.html](docs/index_en.html).

## How It Runs

Three phases with scopes that do not overlap:

| Scope | Does | Doesn't |
| --- | --- | --- |
| **Node** | Implements in its own worktree, proves itself with the project's gates, and **only commits to its own branch** | No push, no PR, no merge, no self-review |
| **Wave** | Leak check → merge only the nodes that finished → run gates on the integrated tree → **review once** (one section per node, focused on the seams between nodes) → **write the walkthrough once** (evidence only: what changed, what was run, what it proved) → **ship once** (the PR body and merge checklist are produced here and nowhere else; one PR with a per-item evidence table) | No node-level PRs; no per-node walkthrough |
| **Batch** | The serial path in `/loop-it` works the same way: implement and commit one Issue at a time inline, passing a supervisor check per Issue (judged on evidence, not on how the diff reads), then review, walk through and ship once at the end of the batch | — |

A few deliberate design choices:

- **Use `/graph` only when there is real parallelism.** One unit, two units that share a file, or chained work like "schema → API → UI" belongs in `/loop-it` or done inline — all of `/graph`'s value comes from nodes within a wave being genuinely independent.
- **A single-node wave skips the wave branch.** There is nothing to integrate, so that node's branch goes straight to review and shipping.
- **Failed nodes are retried in place first.** A follow-up message reuses that node's own context instead of paying for a fresh child; if the retry still fails, the node is re-run, and if it fails again it is dropped from the wave branch — its siblings were independent all along, so the rest ship as usual.
- **When one PR closes several Issues, list the evidence per item**: the commit, the Issue it closes, the test names that prove it, and the manual acceptance status. After a squash those commits are invisible on `main`, and without this table there is no way to roll back or audit one Issue on its own.

## Why let-it-go

- **Cost is counted per wave, not per node.** Every subagent pays for the parent's system prompt, tool schemas, and skill catalog across its entire lifetime, and a `/review-it` + `/ship-it` per node means N PRs, N CI runs, and N chances to get stuck on a merge conflict. So nodes stop at commit, and review and shipping are collected at the wave level.
- **The arithmetic lives in scripts.** Dependency ordering, wave layering, scope-conflict serialization, and the checkpoint state machine all ship with the skills under `skills/<bucket>/<skill>/scripts/`, each with self-tests (the repo-root `scripts/` holds only the maintenance scripts: `check_skills.py` and `sync_vendor.py`); the skills describe when to use them and where the boundaries are, not how the algorithm works.
- **Designed around real constraints, not an idealized model.** Subagents have no cwd of their own, every shell call is a fresh shell, delegation depth is capped, and the skill catalog is billed to every subagent — all of which became hard rules in the skills (absolute-path discipline plus leak checks against the shared checkout, nodes may not spawn further subagents, and an optional [lean-subagent patch](skills/flow/graph/references/lean-subagent.md)).

## Skills

The table uses short skill names; the prefix is `/` everywhere (DSH).

**Not sure which one? Invoke `ask-flow` first** — it routes and then **starts that step**, instead of naming a skill and leaving you to type it again.

| Stage | Skill | What it does |
| --- | --- | --- |
| Entry | `/ask-flow` | Ask which skill or flow fits your situation: it routes on the skill map and then **starts that step** (model-invocable; it only stops when two routes are genuinely close) |
| Requirements & design | `/prd` · `/to-design` | Requirements doc → design proposal (**only when the change spans two or more services, alters the data model or a migration, or touches two or more external contracts**; Markdown is the main artifact, HTML an optional rendering) |
| Breakdown & triage | `/to-issues` · `/triage` | Split your own PRD into vertical slices where **the Issue body is the contract** (goal / non-goals / acceptance criteria / required evidence / external boundary / definition of done / open questions) · turn **incoming** raw issues into agent-ready cards |
| Implementation | `/implement` · `/test-first` · `/graph` · `/loop-it` | Finish a single unit inline · red-green testing · DAG waves in parallel (one worktree per node, and nodes pass an evidence check at fan-in) · Issues in dependency order, serial (one supervisor check per Issue, resumable checkpoints) |
| Diagnosis | `/diagnose` · `/conflict` | A debugging loop that demands a red-capable command first · resolve merge/rebase conflicts hunk by hunk by intent |
| Review & shipping | `/review-it` · `/walkthrough` · `/ship-it` | Two-axis review (Spec + 8 standards dimensions) · the pre-merge walkthrough proving what changed and what was verified (**evidence only; it does not produce the PR body**) · **the sole producer of the PR body**: commit/PR/merge/close Issue, plus the one implementation summary comment |
| Code quality | `/refactor` · `/modern-go` | Two modes (`audit` reports without changing code / `fix` refactors from Fowler's catalog) · Go 1.0→1.27+ modernization |
| Docs & diagrams | `/understand` · `/svg-diagram` (vendor) | Turn the current change into an interactive review page · SVG diagramming conventions plus 12 mechanical checks (bundled `svg-lint`) |
| Third-party (`skills/vendor/`, verbatim copies) | `/find-skills` · `/frontend-design` · `/humanizer-zh` · `/pptx` · `/resume-optimizer` · `/skill-creator` · `/teach` · `/ui-ux-pro-max` · `/web-design-guidelines` | Discover and install skills from the ecosystem · front-end visual direction · strip template-speak from Chinese prose · read, write and edit `.pptx` / `.potx` · audit and rewrite a résumé around outcomes and the target JD · create and improve skills with evals · explain a concept as a lesson · a searchable UI/UX design knowledge base · review UI code against the Web Interface Guidelines |

`ask-flow` is **model-invocable**: it routes and then **starts that step**, stopping only when two routes are genuinely close — turning every step into a "please confirm" pushes back onto the human a judgement the agent should be making. Across the current 27 skills (flow 10 / bonus 7 / vendor 10) the catalog is 6,446 characters, of which the model actually sees **6,385**. The only skill carrying `disable-model-invocation` is the vendored `teach`, which is upstream's choice and stays out of the model catalog.

`/goal` is a host **command**, not a skill. The model side of that surface is `create_goal` / `update_goal`, and its gate is **authority, not wording**: `create_goal` runs only in a **direct top-level human turn**, so a subagent or a mid-orchestration step cannot mint one — but the human does **not** have to say "goal". Handing over a long-running objective ("work through this whole batch") is exactly when it should be created, and that is the behaviour it was designed for. On a long batch the goal is the **session-scoped driver** (it re-prompts the session once a turn ends) while the checkpoint (`.loop-state.json` / `.graph_state.json`) is the **repo-scoped state** (where the batch got to) — the two are complementary and count different things (`maxGoalRounds` bounds continuation, `attempts` counts one issue's retries).

## Repository layout

```
skills/
├── flow/          # one link in the PRD → ship chain, run in order (10)
├── bonus/         # engineering work and artifacts you reach for mid-flow (7)
└── vendor/        # verbatim third-party copies, pinned to a commit by the manifest (10)
scripts/           # check_skills.py (layout / frontmatter / cross-refs / patch)
                   # sync_vendor.py (vendor sync and additions)
Makefile           # the entry point for make check / test / vendor-*
cordis.patch.yml   # the DSH bundle patch: each of the three buckets is its own customSkillDirs root
```

The test is the role a skill plays: `flow` is the pipeline itself; `bonus` is what you reach for mid-flight because something broke, because quality is at stake, or because you need a non-code artifact (a testing method, diagnosis, conflicts, incoming triage, refactoring, design docs, a review page); `vendor` adds no new skills — it collects upstream third-party skills verbatim, each directory carrying a `NOTICE.md` (source / commit / license / sync date).

A DSH skill root is scanned **exactly one level deep** (`<root>/<name>/SKILL.md`), so `cordis.patch.yml` lists each of the three buckets as its own root rather than pointing at `skills/`. `npx skills add` scans recursively and flattens on install; either install route yields exactly the same set. `scripts/check_skills.py` guards the two silent failures: **a skill left at the top level** (no root covers it) and **a bucket missing from the patch** (that whole bucket disappears without an error).

## Maintenance

```bash
make check          # layout, frontmatter, cross-references, bundle patch
make test           # check first, then the bundled scripts' self-tests
make vendor         # copy every vendored skill in at its pinned commit
make vendor-check   # report vendored skills whose upstream has moved
make vendor-update  # re-pin to upstream HEAD, sync, and validate
make vendor-list    # list vendored skills and the commit each is pinned to
make vendor-add URL=<git url> SKILL="name [name...]"   # add new ones (the shape of npx skills add <url> --skill <name>)
```

`skills/vendor/vendor.json` is the manifest; each skill records `source` / `sourceUrl` / `path` / `ref` (pinned to a commit) / `license`. **Everything under `skills/vendor/` is a verbatim copy — never edit it in place**; change the manifest and run `make vendor`.

## Project Status

![License](https://img.shields.io/github/license/9Ashwin/let-it-go) ![Last Commit](https://img.shields.io/github/last-commit/9Ashwin/let-it-go) ![Commit Activity](https://img.shields.io/github/commit-activity/m/9Ashwin/let-it-go) ![Issues](https://img.shields.io/github/issues/9Ashwin/let-it-go) ![Pull Requests](https://img.shields.io/github/issues-pr/9Ashwin/let-it-go)

## Community & Feedback

- 🌐 [**Online docs**](https://9ashwin.github.io/let-it-go/) — usage guides in Chinese and English
- 🐛 [**Issues**](https://github.com/9Ashwin/let-it-go/issues) — bugs, feature requests, and skill improvements

## License

MIT — see [LICENSE](./LICENSE).
