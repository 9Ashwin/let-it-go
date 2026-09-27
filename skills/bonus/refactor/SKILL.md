---
name: refactor
description: "Find and fix structural problems without changing behaviour: audit mode detects code and architecture smells, complexity hotspots and anti-patterns and reports them by severity (report only, no code); fix mode applies Fowler's catalog to remove them. Triggers: refactor, 重构, smell, code smell, 代码坏味道, 架构坏味道, 反模式, find anti-patterns, complexity analysis, extract method, clean up, simplify."
---

# Refactor — Audit and Fix Structural Problems

Two jobs share one seam: finding what is structurally wrong, and removing it without changing behaviour. **`audit`** detects and reports; **`fix`** applies Martin Fowler's *Refactoring* (2nd Edition) catalog in small, behaviour-preserving steps.

**This skill is guidance, not a script: a refactoring that cannot be justified by a named smell is not worth making, and an audit earns nothing by listing candidates it never validated.** This file is the map — modes, workflow, decision rubric. The smell and technique entries are lookup material in `references/`, read one entry at a time once you have named the symptom.

## Two Modes

| Mode | Job | Output | Writes code? |
|------|-----|--------|--------------|
| **`audit`** (report only) | Detect code and architecture smells, complexity hotspots, and anti-patterns; validate candidates against context, callers, history, workload, and measurement; rank confirmed findings by severity | A markdown report under `tasks/`, plus a summary of confirmed findings and a separate candidate list | No |
| **`fix`** (default) | Apply the smallest Fowler refactoring that addresses one named smell, keeping behaviour fixed | Small commits, one refactoring each, tests green | Yes |

### Choosing a Mode

- **`fix`** when the smell is already named and scoped, the user asks to clean up / extract / rename / simplify, or an audit's roadmap is in hand.
- **`audit`** when the scope is unknown, the user asks what is wrong or whether the architecture is healthy, or you need a prioritized list before touching anything.
- When a request mixes both ("find the problems and fix them"), run `audit` first, confirm the findings with the user, then switch to `fix` on the agreed list.
- `audit` never edits code. `fix` never expands scope beyond the named smell.

The two are the same seam: **the audit's confirmed findings and roadmap are the fix's input list.** Each finding already names its location, failure/change scenario, primary principle, smallest recommendation, and verification — exactly the decision card `fix` needs. `fix` closes the loop by recording which finding it resolved.

## When to Use / When NOT to Use

Use this skill when:

- Code is hard to understand or maintain; functions or classes have grown too large
- Smells or anti-patterns are suspected, or a recent change set needs a quality assessment
- Algorithmic complexity hotspots (nested loops, N+1 queries, sort-in-loop) need investigation
- A prioritized, evidence-backed refactoring roadmap is wanted
- The user says: refactor, 重构, clean up, improve code, code smell, smell, 代码坏味道, 架构坏味道, 反模式, complexity analysis, extract method, rename, simplify

Do not use this skill when:

- The request is a line-by-line code review or style/lint pass — that is `review-it`
- The request is a design document rather than a findings report — that is `to-design`
- The scope is a single trivial function — the evidence-gathering overhead is not justified

| Scenario | Action |
|----------|--------|
| Code works and won't change again | Leave it alone |
| Critical production path with no tests | Write characterization tests first |
| Under tight deadline pressure | Document the smell, refactor later |
| No clear purpose or benefit | Don't refactor for refactoring's sake |
| Code is fundamentally wrong | This is a rewrite, not a refactoring |

## The Golden Rules (`fix`)

1. **Behaviour is preserved.** Only *how* the code works changes, never *what* it does. Tests that passed before must pass after; a behavioural change is a rewrite, not a refactoring.
2. **Small steps.** Each change is the smallest transformation that compiles and passes tests, so a break points at exactly one change.
3. **Version control is your friend.** Commit before starting and after each successful step; branch from a clean tree so the attempt can be abandoned.
4. **Tests are essential.** "Without tests, you're not refactoring — you're just editing." Write characterization tests first when none exist.
5. **One thing at a time.** Never mix refactoring with feature work, and never refactor two unrelated things at once.

## `audit` Workflow

1. **Scope.** Ask what to analyse: whole project, a module/directory, recent changes (`git diff`), or architecture-level issues only. Default to recent changes for repos over ~200 files, full analysis otherwise. [`references/principles-and-severity.md`](references/principles-and-severity.md) carries the fallback handling for unusual scopes (empty or monorepo projects, unsupported languages, quick or single-category runs, filename conflicts).
2. **Gather evidence.** Delegate breadth to fresh children: there are no child *types* to select, a fresh child sees none of this conversation, so every prompt must be self-contained (state the directory and exactly what to report). Dispatch them all in one message to run concurrently, keep them shallow, and collect them when they settle rather than polling. Cover project structure and architectural style; dependency graph and circular dependencies; module size and cohesion; known anti-pattern signatures; test coverage patterns; naming and clarity; algorithmic complexity hotspots.
3. **Validate candidates.** Static patterns, metrics, and dependency scans produce *candidates only*. Read the implementation and relevant callers; check change frequency, input size, runtime frequency, framework constraints, generated/vendor status, and existing mitigations. Then merge candidates sharing one root cause, affected path, failure/change scenario, and remediation direction into a single finding — counted by root cause, never by the number of principles implicated. Record evidence strength (`Measured`/`Observed`/`Inferred`) separately from confidence (`High`/`Medium`/`Low/Candidate`); evidence strength does not imply severity. Read [`references/principles-and-severity.md`](references/principles-and-severity.md) before merging or assigning severity, and [`references/complexity-heuristics.md`](references/complexity-heuristics.md) before reporting any performance finding.
4. **Report.** Generate the report from the skeleton and worked example in [`references/report-template-and-example.md`](references/report-template-and-example.md): executive summary, architectural style detected, findings by severity (🔴 Critical / 🟡 Warning / 🔵 Suggestion) with a separate *Candidates Requiring Measurement* section, detailed findings, dependency graph analysis, module health scorecard, smell distribution, and a roadmap ordered by impact, confidence, dependency sequence, and verification cost. Save it to `tasks/refactor-audit-report-[YYYY-MM-DD-HHmm].md` and present a brief summary that leads with confirmed findings and keeps candidates separate.

A confirmed finding must name its location (`file:line`, plus relevant callers), a concrete failure or change scenario, and how the fix will be verified. Anything whose runtime impact, change frequency, or workload is not yet established stays a candidate.

## `fix` Workflow

1. **Identify the smell.** Name one primary smell before touching code — one root cause backed by evidence: location, behaviour, callers, change history, or measurement. The five families and the architecture-level catalog are in [`references/smells.md`](references/smells.md); thresholds are candidate signals, not verdicts.
2. **Prepare.** Write characterization tests if they don't exist, record a baseline for the claimed problem (representative behaviour, change spread, relevant callers, or a benchmark/profile/query count), commit from a clean tree, and branch away from feature work.
3. **Record a decision card** (see the rubric below) and pick the smallest technique that addresses the root cause. The technique catalogs are in `references/`.
4. **Change in small steps.** Address one verifiable part of the primary smell per change; compile; run the tests; check that any new interface, adapter, or indirection removes real caller complexity or supports an existing variation; commit (`refactor: extract validateEmail method`). Undo rather than press on when a test fails.
5. **Verify.** Behaviour (tests, type checks, compilation, smoke test); structure (dependency direction, callers, duplicated knowledge, change spread against the decision card); fail-fast semantics (error types/codes, aggregation, retry, transaction, cleanup); performance (re-run the same workload and environment, report the result and noise range — without a baseline, claim only that no obvious regression was observed); and a diff review for unintended changes.
6. **Clean up.** Remove comments the refactoring made obvious, delete code it orphaned, remove speculative seams (single-implementation interfaces, pass-through modules, unused extension points), and make a final commit summarizing the sequence.

## Refactoring Decision Rubric

Principles guide judgment; they are not independent reasons to rewrite code. Before choosing a technique, record one decision card:

| Field | Required answer |
|-------|-----------------|
| **Primary smell** | One root cause, not one entry per principle |
| **Evidence** | Location, behaviour, callers, change history, or measurement |
| **Primary principle** | The most specific applicable principle |
| **Related principles** | Explanatory labels only; do not count separately |
| **Expected impact** | Observable reduction in change spread, cognitive load, duplicated knowledge, coupling, delayed failure, or measured runtime cost |
| **Smallest refactoring** | The least invasive Fowler technique that addresses the root cause |
| **Baseline / success condition** | How behaviour preservation and the expected benefit will be verified |

Use these four decision lenses:

| Lens | Principles | Questions to answer |
|------|------------|---------------------|
| **Responsibility and dependencies** | SOLID, SRP, OCP, DIP, Separation of Concerns | Are reasons to change mixed? Does a real new variant repeatedly modify stable logic? Does high-level policy depend on concrete mechanism? Do concerns leak across a boundary? |
| **Reuse and structure** | DRY, Composition | Is the same knowledge duplicated, or merely similar syntax? Would composition localize a real variation better than inheritance? |
| **Simplicity and scope** | KISS, YAGNI | Is the proposed structure simpler for today's problem? Is every abstraction backed by an existing variation or boundary? |
| **Runtime and feedback** | Fail Fast, Measure First | Can invalid state fail nearer its source without changing error semantics? What baseline proves the problem and the result? |

`SOLID` is an umbrella. When evidence supports `SRP`, `OCP`, or `DIP`, use that specific lens and do not create a second SOLID issue. LSP and ISP may be labeled `SOLID/LSP` and `SOLID/ISP`. DRY means shared knowledge, not all similar code. Composition is preferred when inheritance creates real coupling, not by default. OCP and DIP never justify speculative layers that violate KISS or YAGNI.

## References

The catalog is lookup material: load the file that matches what you are investigating, not all of them at once.

**Naming the problem (`audit`, and the start of every `fix`)**

- [`references/smells.md`](references/smells.md) — the merged smell catalog: Fowler's five families (bloaters, object-orientation abusers, change preventers, dispensables, couplers) plus the architecture, coupling, design, naming, readability, and testing signals above them, each with its detection signal and primary refactoring. Read it first, to put a name to the symptom.
- [`references/architecture-smells.md`](references/architecture-smells.md) — prose catalog of architectural anti-patterns (Big Ball of Mud, Distributed Monolith, Anemic Domain Model, ...) and the Top Ten architecture mistakes, with symptoms and remedy. Read for an architecture- or layering-level finding.
- [`references/coupling-and-design-smells.md`](references/coupling-and-design-smells.md) — coupling and cohesion smells plus the object-orientation abusers, with symptoms and remedy. Read for coupling, inheritance, or interface design.
- [`references/code-and-testing-smells.md`](references/code-and-testing-smells.md) — code-level and testing smells (Long Method, Primitive Obsession, Dead Code, No Tests, ...) with remedies. Read for a code-quality or testing smell.
- [`references/complexity-heuristics.md`](references/complexity-heuristics.md) — the algorithmic complexity catalog with detection, impact, remedy, and correctness checks, plus Measure First and what not to flag. Read before reporting any performance or complexity finding.
- [`references/principles-and-severity.md`](references/principles-and-severity.md) — the 11-principle matrix with false-positive constraints, the design-principle refinements, the evidence-strength and severity rubric, and the edge-case fallbacks. Read before merging candidates or assigning severity.
- [`references/report-template-and-example.md`](references/report-template-and-example.md) — the full report skeleton and a worked summary example. Read when writing or presenting an audit report.

**Removing it (`fix`)**

- [`references/composing-methods.md`](references/composing-methods.md) — Extract/Inline Method, Extract Variable, Replace Temp with Query, Replace Method with Method Object, Substitute Algorithm, with mechanics and before/after examples. Read when a method is too long or a name no longer fits.
- [`references/moving-features.md`](references/moving-features.md) — Move Method/Field, Extract/Inline Class, Hide Delegate, Remove Middle Man, foreign methods, and the generalization moves (Pull Up, Push Down, Extract Superclass/Interface, Replace Inheritance with Delegation). Read when behaviour sits in the wrong class or the hierarchy has drifted.
- [`references/organizing-data.md`](references/organizing-data.md) — Self Encapsulate Field, value/reference conversions, Replace Array with Object, type codes, magic numbers, and collection encapsulation. Read when raw data carries meaning an object should carry instead.
- [`references/simplifying-conditionals-and-method-calls.md`](references/simplifying-conditionals-and-method-calls.md) — Decompose Conditional, guard clauses, Replace Conditional with Polymorphism, Null Object, assertions, and the naming and parameter moves. Read when conditionals nest deeply or a call site is hard to read.
- [`references/checklist-and-safety.md`](references/checklist-and-safety.md) — the code-quality, structure, conditionals, type-safety, and testing checklist; the before/every-step/if-tests-break/on-completion safety protocol; and the edge-case table. Read before starting, after each step, and whenever a test breaks.
- [`references/applying-the-catalog.md`](references/applying-the-catalog.md) — common multi-step sequences, design-pattern pairings, and per-language notes (Java, JavaScript/TypeScript, Python, Go, Rust). Read once the smell is named and you want a known order of steps.

## Resources and Knowledge Base

- Martin Fowler, *Refactoring: Improving the Design of Existing Code* (2nd Edition, 2018) — [refactoring.com](https://refactoring.com) and [refactoring.guru](https://refactoring.guru), whose 6-category / 66-technique catalog and code-smell taxonomy (Bloaters, Object-Orientation Abusers, Change Preventers, Dispensables, Couplers) this skill mirrors.
- Architecture: Big Ball of Mud (Foote & Yoder, 1997); Clean, Onion, and Hexagonal Architecture; Domain-Driven Design, CQRS, Event-Driven Architecture; [awesome-software-architecture](https://github.com/mehdihadeli/awesome-software-architecture).
- Principles: SOLID (with explicit SRP/OCP/DIP lenses), DRY, KISS, YAGNI, Composition, Separation of Concerns, Fail Fast, Measure First; GRASP.
