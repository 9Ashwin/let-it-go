---
name: to-design
description: "Write a Go-style design proposal from a PRD — Abstract / Background / Design / Rationale / Compatibility / Implementation, strong on the why; optionally render it as a self-contained house-style HTML page. Triggers: to-design, 设计文档, 设计提案, design doc, 生成设计文档."

---

# to-design — 需求 → 设计文档

Turn a PRD (or a rough idea) into a **design document** in the style of Go's official design proposals: plain language, concrete examples, and—above all—an honest account of *why this approach and not the alternatives*.

A design document is a **decision artifact**: it argues for an approach, surfaces the tradeoffs, and gets a team onto the same facts before anyone writes code. It is **not** an implementation contract — that lives in the **contract field block of an issue body**, produced by `/to-issues` (tables, endpoints, schemas an engineer builds against). Question is "*how should we build this and why*" → design doc. Question is "*give me the exact contract to implement*" → `/to-issues`.

**Markdown is the primary deliverable.** Rendering it as a self-contained HTML page is an optional presentation layer, never a requirement — see 可选：渲染成 HTML at the end.

> 设计哲学源自对 5 篇 Go 官方 proposal（泛型 / 错误包装 / loopvar / slog / try）的分析。核心信念：**文档的价值不取决于方案是否通过，而取决于它是否让讨论建立在同一套事实和取舍之上。**

---

## 何时用 / 何时不用

**用**：PRD 已存在，需要在动手前决定 *怎么建*；方案有真实取舍，且希望被记录、被讨论；变更风险高、破坏性强或难以回滚（设计文档逼你提前谈兼容性）；需要多人先对齐方向再分头开工；想要一份"为什么选 X、为什么不选 Y"的持久记录——即使方案最后被否。

**不用**：只要实现契约 → 直接 `/to-issues`，契约字段块写在 issue 正文里；纯增量、无取舍的小改动 → 跳过，直接开工；内容已定、只要一份视觉固定的 HTML → 见文末 HTML 一节。

---

## 第 1 步：找到输入

```
Provide the PRD (or idea) to design from:

A. File path (e.g., tasks/prd-priority-system.md)
B. GitHub Issue URL
C. Paste content directly
D. Just describe the idea — I'll design from the conversation
```

设计文档可以从半成形的想法起步，不必是打磨好的 PRD。输入越薄，第 2 步问得越多。

**（可选）扫一遍代码库**，把设计落在现实上：既有模式（命名、错误处理、模块边界）、前例（这里是否试过或否过类似方案）、约束（兼容承诺、公开 API、不能动的数据）、真实痛点（找到本次要修的 buggy/别扭代码，让 Background 能引用它）。最有说服力的 Background 引用**用户仓库里的真实代码**，不是假设的例子。

---

## 第 2 步：浮现决策

设计文档的成败在 Rationale。动笔前先找出**路上真正的岔口**——一个有能力的工程师可能合理走两个方向的地方——并解决它们。只问真岔口：

```
Design decisions to settle before I write the doc:

1. Where does this logic live?
   A. Extend the existing X
   B. New standalone component Y
   C. Let me recommend based on the codebase

2. Is this a breaking change for existing callers?
   A. Yes — needs a migration path
   B. No — purely additive
   C. Unsure — I'll analyze and flag it

3. What's the one promise this design must keep? (e.g. backward compatibility,
   latency budget, no new dependencies)
```

每个岔口都记下**你没选的那条路**——它就是 Rationale。没有备选方案时，强迫自己想"最朴素的做法是什么、为什么不够"：总有一个被否决的基线。

---

## 第 3 步：文档结构

从 5 篇 Go proposal 提炼的标准骨架。保留章节名；确实不适用的可以删（删得显眼就说明原因）。

```markdown
Title: <一句话说清"做什么" —— 标题就是结论，不是名词短语>
Author(s): <作者>
Last updated: <YYYY-MM-DD>
Discussion at <issue / PR / 文档链接>   # 让文档不孤立，永远附讨论入口
Status: Draft | Under review | Accepted | Rejected

## Abstract / 摘要
一段话讲完全文：做什么、大致怎么做、以及**最重要的那个承诺**（如"向后兼容""不引入新依赖"）。读者读完这段就该知道全貌。

## Background / 背景与动机
用**具体、可感的例子**说明"痛在哪"，不要抽象地说"现状不好"。能贴真实的 bug 代码/别扭调用就贴，先让读者"疼"起来；量化痛点（频率、踩坑次数、损失），别堆形容词。

## Design / Proposal / 设计
文档主体。三条：**从简单到复杂，渐进式教学**；**声明 + 示例 + 边界**三件套；**改造前 vs 改造后对照**。能用一段可运行代码说清的，绝不用一段文字描述。

## Rationale / 理由与取舍
> "为什么是这个方案，而不是别的"的论证。这是区分好文档和平庸文档的关键章节。
解释关键决策的动机；**主动列出被放弃的备选方案 + 放弃原因**（"我们没选 X，因为 Y"）——这比单方面论证更可信，也避免后人重复讨论；回应可预见的质疑。

## Compatibility / 兼容性
凡涉及破坏性变更，必须正面回应：**开门见山承认**是不是破坏性变更；**诚实列出**代价（性能、行为变化、迁移成本）；给出渐进迁移路径（按模块 opt-in、灰度、特性开关）；有先例佐证更好。

## Implementation / Transition / 实现与过渡
如何落地、分几步、配套什么工具。**用数据和工具支撑"可落地"**：实测失败率、灰度结果、自动化迁移工具，比"我们认为风险可控"管用；兼容老版本的过渡方案（如独立发布的兼容库）。

## Appendix / 附录（可选）
把打断主线的细节后置：完整 API、端到端示例、FAQ（"为什么叫这个名字""和 X 有何不同"）。
```

**PRD → 设计文档**：Problem → Background（找真实痛点并量化）；Goals → Abstract + Background（提炼"最重要的承诺"）；User Stories → Design（渐进式示例）；Technical Considerations → Design + Rationale（约束 → 决策 + 取舍）；Non-Goals → Rationale（"我们没做 X，因为 Y"）；Risks → Compatibility + Implementation（风险 → 兼容代价 + 迁移方案）；隐含的备选方案 → Rationale（显式列出并解释为何不选）。

**评审与保存**：把反馈引到关键章节——Rationale（被放弃的方案站得住吗、有无遗漏备选）、Compatibility（破坏性与代价说清了吗、迁移路径可行吗）、Background（痛点是否具体）、文风（标题是否结论、有无被动腔）。回复 OK 后保存到 `tasks/design-[feature].md`（紧挨 PRD，推荐）或 `docs/design/[feature].md`，自定义路径亦可。

---

## 文风（照搬 Go 文档）

- **主语**：决策用"我们 / We"（一群人可负责的选择，不是客观真理）；行为用代码本身当主语（"这段代码有 bug"）；说理对读者用"你 / you"。禁止无主语的被动腔（"据建议应当…"）。
- **句子**：判断用短句，论证用长句。先用极短的句子拍板（"这段代码有 bug。"），再用信息密集的长句铺开机制；长短交替制造节奏。
- **段落**：一段只讲一件事，观点放段首（结论先行）。小标题写成一句完整的论点，而不是名词短语——写 `老代码不受影响，编译结果与之前完全一致`，而不是 `兼容性`；读者光看标题就能读完整条论证链。
- **语气**：克制的诚实，甚至自嘲。承认代价、承认自己也踩过坑，比形容词更有说服力。强调要省着用，全文只在最关键处加粗一次，反而最醒目。

---

## 自检与常见错误

- [ ] 标题是一句"做什么"的结论，不是名词短语，且附了讨论链接
- [ ] 摘要里埋了最重要的承诺/约束
- [ ] Background 用了**具体例子或真实代码**讲痛点，而非形容词
- [ ] Design 遵循"声明 + 示例 + 边界"，并有渐进式教学
- [ ] **Rationale 主动列出了至少一个被放弃的方案及原因**（最关键的检查项）
- [ ] 凡破坏性变更，Compatibility 都正面承认并列出代价
- [ ] Implementation 用数据/工具支撑"可落地"，而非空喊"风险可控"
- [ ] 文风：决策用"我们"、行为用代码、无无主语被动腔；长短句交替；小标题是论点句
- [ ] 没有 "TBD / TODO"——要么解决，要么挪进 Open Questions

反模式：**只论证你选的方案**（不写被放弃的备选项，文档就少了一半价值）；**用形容词讲痛点**；**藏代价**；**把标题写成名词**；**用无主语的被动腔**；**写成 SPEC**（设计文档讲"为什么这么选"和取舍，不是字段级契约）；**因为方案可能被否就敷衍**（文档质量与提案是否通过无关）。

---

## 可选：渲染成 HTML

**HTML 只是可选的呈现层，Markdown 提案才是主产物。** 默认交付 Markdown；只有当用户明确要一份可分享、视觉固定的页面，或要把既有 `.md` 规格转成 HTML 时才渲染。不渲染完全不影响本技能成立——不要把 HTML 当成必经步骤。

### 工作流

1. **整份复制 `template.html`**（同目录），不要手搓 `<head>`/`<style>`。改标题、TOC 与各 `<section>` 内容，保留 `<style>` 原样。
2. **先取真实内容**：章节标题、字段名、SQL、`file:line`、protoIds 都必须来自真实需求文档与代码库。读代码，不要编造标识符；不知道的事实标 `<span class="pill todo">待确认</span>`，绝不猜。
3. **填骨架**：按功能重命名/重排 `<section>`，但保留章节种类：已对齐结论 → 业务规则 → 架构图 → 时序 → 数据模型 → 契约 → 清单 → 幂等降级 → 测试用例 → 代码索引 → 变更记录。不适用的删掉，特性专属的按同样风格加。
4. **TOC 与 section 保持同步**：每个 `<a href="#x">` 都要有对应的 `<section id="x">`，反之亦然。这是第一号破损点，最后必须校验。
5. **保存**为 `docs/<需求名>.html`。用户没要求就不要提交。

### House-style 规则（不可协商）

| 元素 | 规则 |
|---|---|
| `<style>` 块 | 原样复制，永不重设样式。颜色只来自 `:root` CSS 变量。 |
| 代码 / SQL / YAML | 一律用模板的 `<pre style="background:#f8fafc;...">`。**`<pre>` 内转义 `<`→`&lt;`、`>`→`&gt;`、`&`→`&amp;`**，未转义的 `<` 会静默吞掉内容。 |
| Callout | `.note`（橙，提醒/易错）、`.tip`（蓝，正向补充）、`.warn`（红，风险），按语义选色。 |
| 图表 | 手写内联 `<svg>` 放在 `<figure>` 里；文字用 `.svg-t`/`.svg-s`/`.svg-title`；节点填充用 `:root` 变量（`var(--new-bg)` 等），与 `.legend` 一致。 |
| 引言 | 每个 section 以一句 `<p class="lead">` 开头，说明它回答什么。 |
| Pills | `.pill.new/.old/.infra/.mq/.prod/.tech/.done/.todo` 状态标签，复用即可，不要新造 class。 |
| 表格 | 普通 `<table>`，CSS 已处理斑马纹与表头底色。 |
| 语言 | `<html lang="zh">`；正文用文档的语言（通常中文）。 |

### HTML 常见错误

- **重设 CSS**：整套风格的意义就是每次输出完全一致，别"改进"颜色、间距、字体。
- **`<pre>` 里未转义尖括号**：`List<String>` 会渲染成断标签，要写 `List&lt;String&gt;`。
- **TOC 死链**：加了 section 没加 TOC 条目（或改了 `id` 忘了 `href`）。务必交叉核对。
- **编造代码位置**：`file:line`、表名、protoIds 必须从仓库读出来；未知 → `待确认` pill，不是看起来合理的猜测。
- **写成提案**：HTML 版是 *设计文档*（what/how、已锁定的决策），不是说服性 pitch。

### 最终自检

```bash
f="docs/<需求名>.html"
# TOC hrefs vs section ids 必须完全一致（无输出 = 通过）：
diff <(grep -oE 'href="#[a-z0-9-]+"' "$f" | sed 's/.*#//;s/"//' | sort -u) \
     <(grep -oE '<section id="[a-z0-9-]+"' "$f" | sed 's/.*"//' | sort -u)
# 浏览器打开，肉眼确认图表与代码块渲染正常
```

---

## 边界情况

| 场景 | 处理 |
|------|------|
| PRD 含糊不全 | 在第 2 步多问，把缺失项写进 Open Questions / 假设 |
| 没有真实痛点代码可引 | 用最小可信的示例代码代替，并注明是构造的 |
| 不是破坏性变更 | Compatibility 一句话说明"纯增量、无破坏"，不必硬凑 |
| 方案最终被否决 | 照样写好——记录"这条路为什么走不通"本身就是高价值产物，Status 标 Rejected |
| 特性太大 | 拆成多篇 design doc（按边界），互相链接 |
| 用户只要实现契约 | 提示改用 `/to-issues`——契约字段块写在 issue 正文里 |

---

## 与其它技能的关系

`/prd`（需求 what）→ **`/to-design`**（决策与取舍 why/which，本 skill）→ `/to-issues`（拆成 agent-ready 的 issue，实现契约写在 issue 正文的契约字段块里）→ `/goal` → `/review-it` → `/ship-it`。

> 写设计文档的终极目的不是"说服别人同意你"，而是"让所有人在同一个事实和取舍基础上做决定"。
