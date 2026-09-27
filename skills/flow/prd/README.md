# PRD Generator Skill

Generate structured Product Requirements Documents (PRD) for new features. Focused solely on producing a clear, implementable PRD — Issue decomposition is handled by `/to-issues`.

## Features

- Asks 3-5 clarifying questions with lettered options for quick iteration
- Generates a well-structured PRD with user stories, numbered functional requirements, non-goals, success metrics, and more
- Enforces verifiable acceptance criteria (observable / testable / verifiable)
- Supports user review and adjustment before saving
- Saves output to `tasks/prd-[feature-name].md`
- Bilingual (Chinese & English) edge case handling

## Workflow

The PRD skill is the first step in a two-stage pipeline:

| Stage | Skill | Purpose |
|-------|-------|---------|
| 1. Requirements | `/prd` (this skill) | Define *what* to build |
| 2. Decomposition | `/to-issues` | Break into implementable tickets, each carrying its own contract block (GitHub / Local) |

After a PRD is confirmed, run `/to-issues`. There is no separate technical-design document: each Issue body carries goal, non-goals, acceptance criteria, required evidence, external boundary, definition of done and open questions.

## Usage

Trigger with prompts like:

- "create a prd for..."
- "write prd for..."
- "写PRD"
- "需求文档"
- "需求分析"

## Files

- `SKILL.md` — Skill definition and instructions
- `evals/evals.json` — Test prompts with the expectations a run is graded against
