# Smell Catalog

The lookup table behind both modes: name the symptom, read its detection signal, and take the primary
refactoring when you move to `fix`. It merges Fowler's five families with the architecture, coupling,
design, naming, and readability smells that sit above them.

Thresholds and static patterns here are **candidate signals, not findings**: a line count, nesting depth,
naming match, or Big-O shape must be validated against responsibility, callers, change history, workload,
and intentional constraints before it is reported or acted on. The validating workflow is in `SKILL.md`;
the prose definitions and remedies are in the thematic reference files named under each group.

### Bloaters

Things that have grown too big.

| Smell | Detection signal (candidate) | Primary refactoring |
|-------|------------------------------|-------------------|
| **Long Method** | Method > 10-15 lines; nesting > 3 levels; several levels of abstraction mixed | Extract Method, Replace Temp with Query |
| **Large Class / God Object** | Many fields and methods; a class/module > 500 lines or > 20 public methods handling unrelated concerns | Extract Class, Extract Subclass |
| **Primitive Obsession** | Primitives where a domain type belongs (`string email`, `int money`, `decimal` without currency) | Replace Data Value with Object, Replace Type Code with Class |
| **Long Parameter List** | > 3-4 parameters; boolean flags controlling behaviour | Introduce Parameter Object, Preserve Whole Object |
| **Data Clumps** | The same group of 3+ fields or parameters recurring across signatures | Extract Class, Introduce Parameter Object |

### Object-Orientation Abusers

Misused OO mechanisms.

| Smell | Detection signal (candidate) | Primary refactoring |
|-------|------------------------------|-------------------|
| **Switch Statements** | The same `switch`/if-else on a type code or enum repeated in several places | Replace Conditional with Polymorphism, Replace Type Code with Subclasses |
| **Temporary Field** | Instance field set and used only in certain circumstances, empty otherwise | Extract Class, Introduce Null Object |
| **Refused Bequest** | Subclass ignores inherited members or overrides them to throw/no-op | Replace Inheritance with Delegation, Push Down Method/Field |
| **Alternative Classes with Different Interfaces** | Two classes do the same thing behind differently named methods | Rename Method, Move Method, Extract Superclass |

### Change Preventers

Structure that makes one change ripple.

| Smell | Detection signal (candidate) | Primary refactoring |
|-------|------------------------------|-------------------|
| **Divergent Change** | One class/module repeatedly changed for unrelated reasons | Extract Class |
| **Shotgun Surgery** | A single change requires edits in 5+ files across unrelated modules | Move Method, Move Field, Inline Class |
| **Parallel Inheritance Hierarchies** | Adding a subclass in one hierarchy forces adding one in another | Move Method, Move Field |

### Dispensables

Things that could be removed.

| Smell | Detection signal (candidate) | Primary refactoring |
|-------|------------------------------|-------------------|
| **Comments** | Comments explaining *what* the code does rather than why; commented-out blocks | Extract Method, Rename Variable, Introduce Assertion |
| **Duplicate Code** | Identical or near-identical logic in 3+ places; copy-paste with slight variations | Extract Method, Pull Up Method, Form Template Method |
| **Magic Numbers / Strings** | Hardcoded literals without named constants (`if (status == 3)`) | Extract named constants or enums |
| **Lazy Class** | Class/module doing too little to justify its existence | Inline Class, Collapse Hierarchy |
| **Data Class** | Only fields plus getters/setters, no meaningful behaviour | Move Method, Encapsulate Field, Encapsulate Collection |
| **Dead Code** | Unused imports, variables, functions, unreachable branches, commented-out code | Delete it (git history has it) |
| **Speculative Generality** | Unused abstract classes, hooks, parameters, or generics kept "for someday" | Inline Class, Collapse Hierarchy, Remove Parameter |

### Couplers

Classes that know too much about each other.

| Smell | Detection signal (candidate) | Primary refactoring |
|-------|------------------------------|-------------------|
| **Feature Envy** | A method calls another class's methods more than its own | Move Method, Extract Method + Move Method |
| **Inappropriate Intimacy** | Classes reach into each other's internals; tight bidirectional references | Move Method, Move Field, Replace Delegation with Hidden Delegate |
| **Message Chains** | `a.getB().getC().getD().doThing()` — client coupled to the whole object graph | Hide Delegate, Extract Method |
| **Middle Man** | A class whose methods only delegate to another class | Remove Middle Man, Inline Method |
| **Incomplete Library Class** | A third-party class lacks a method you need and cannot be modified | Introduce Foreign Method, Introduce Local Extension |

### Architecture-Level Smells

Above the five families; prose and remedies in [`architecture-smells.md`](architecture-smells.md).

| Smell | Detection signal (candidate) |
|-------|------------------------------|
| **Big Ball of Mud** | No clear directory structure; everything in one flat folder; no separation of concerns |
| **Missing Architecture** | No `src/`/`lib/`/`core/` separation; SQL inline with UI code; HTTP handlers mixed with business logic |
| **Violated Layer Boundaries** | Inner layers importing outer layers; infrastructure code in the domain/core layer |
| **Distributed Monolith** | Microservices sharing a database; services that cannot deploy independently |
| **Anemic Domain Model** | Model/entity classes with only getters/setters; all logic in services |
| **CQRS Without Need** | Separate read/write models for simple CRUD |
| **Over-Layered Architecture** | Pass-through layers that only forward calls; one read touches 6+ classes across 4 layers |
| **Over-Abstraction** | Interfaces, generics, factories, and indirection piled up until you cannot tell what runs |
| **Futuristic Architecture** | Extension points, plugin systems, or config knobs nothing uses |
| **Technology-Enthusiast Architecture** | Unproven technology in production because it is new, not because it fits |
| **Overkill Architecture** | Microservices, event sourcing, or k8s thrown at a CRUD app |
| **Cloud / Visio Architecture** | Diagrams disconnected from the code and runtime reality |

### Coupling & Cohesion Beyond Fowler

Prose and remedies in [`coupling-and-design-smells.md`](coupling-and-design-smells.md).

| Smell | Detection signal (candidate) |
|-------|------------------------------|
| **Circular Dependencies** | Module A imports B and B imports A (import-graph analysis) |
| **Content Coupling** | One module reads or writes another's internal/private members |
| **Common Coupling** | Excessive global variables or shared mutable state; singleton abuse |
| **Stamp Coupling** | Passing a large structure when only a few fields are used |

### Design-Level Smells

Prose in [`architecture-smells.md`](architecture-smells.md) and
[`coupling-and-design-smells.md`](coupling-and-design-smells.md); the principle evidence behind each is in
[`principles-and-severity.md`](principles-and-severity.md).

| Smell | Detection signal (candidate) |
|-------|------------------------------|
| **Leaky Abstractions** | Interface methods named after the implementation (`SaveToPostgres`); implementation exceptions or config leaking through |
| **Static Cling** | Excessive static methods or static state that blocks mocking and hides dependencies |
| **Service Locator Abuse** | A DI container passed around instead of constructor injection |
| **Violated SOLID** | SRP/OCP/ISP violations; record the specific lens rather than a second SOLID finding |

### Naming & Readability

Prose in [`code-and-testing-smells.md`](code-and-testing-smells.md).

| Smell | Detection signal (candidate) |
|-------|------------------------------|
| **Vague Names** | `Manager`, `Handler`, `Processor`, `Helper`, `Util`, `Service`, `Data`, `Info` without context |
| **Inconsistent Naming** | snake_case and camelCase mixed; different patterns for the same concept |
| **Deep Nesting (Arrow Anti-Pattern)** | Loops and conditionals nested > 3 levels; rightward-drifting arrow shape |

### Testing

Prose and remedies in [`code-and-testing-smells.md`](code-and-testing-smells.md).

| Smell | Detection signal (candidate) |
|-------|------------------------------|
| **No Tests** | Modules with zero coverage; business logic without unit tests |
| **Test-Implementation Coupling** | Tests asserting internal calls or private state; tests that break on refactoring |
| **Slow / Environment-Dependent Tests** | Real I/O, database, network, or clock without doubles; flaky tests |

### Complexity & Performance

Detection, impact, remedy, correctness checks, and the **Measure First** workflow are in
[`complexity-heuristics.md`](complexity-heuristics.md). Nested loops, N+1 queries, repeated linear scans,
sort-in-loop, render-path recompute, pairwise comparison, unnecessary recompute, and wrong data structure
are all candidates until a baseline establishes input size, call frequency, and impact.
