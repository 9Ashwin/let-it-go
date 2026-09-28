# 可选：渲染成 HTML

**HTML 只是可选的呈现层，Markdown 提案才是主产物。** 默认交付 Markdown；只有当用户明确要一份可分享、视觉固定的页面，或要把既有 `.md` 规格转成 HTML 时才渲染。不渲染完全不影响 `/to-design` 成立——不要把 HTML 当成必经步骤。

## 工作流

1. **整份复制 [`../template.html`](../template.html)**，不要手搓 `<head>`/`<style>`。改标题、TOC 与各 `<section>` 内容，保留 `<style>` 原样。
2. **先取真实内容**：章节标题、字段名、SQL、`file:line`、protoIds 都必须来自真实需求文档与代码库。读代码，不要编造标识符；不知道的事实标 `<span class="pill todo">待确认</span>`，绝不猜。
3. **填骨架**：按功能重命名/重排 `<section>`，但保留章节种类：已对齐结论 → 业务规则 → 架构图 → 时序 → 数据模型 → 契约 → 清单 → 幂等降级 → 测试用例 → 代码索引 → 变更记录。不适用的删掉，特性专属的按同样风格加。
4. **TOC 与 section 保持同步**：每个 `<a href="#x">` 都要有对应的 `<section id="x">`，反之亦然。这是第一号破损点，最后必须校验。
5. **保存**为 `<scope>/documents/<需求名>.html`。用户没要求就不要提交。

## House-style 规则（不可协商）

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

## 常见错误

- **重设 CSS**：整套风格的意义就是每次输出完全一致，别"改进"颜色、间距、字体。
- **`<pre>` 里未转义尖括号**：`List<String>` 会渲染成断标签，要写 `List&lt;String&gt;`。
- **TOC 死链**：加了 section 没加 TOC 条目（或改了 `id` 忘了 `href`）。务必交叉核对。
- **编造代码位置**：`file:line`、表名、protoIds 必须从仓库读出来；未知 → `待确认` pill，不是看起来合理的猜测。
- **写成提案**：HTML 版是 *设计文档*（what/how、已锁定的决策），不是说服性 pitch。

## 最终自检

```bash
f="<scope>/documents/<需求名>.html"
# TOC hrefs vs section ids 必须完全一致（无输出 = 通过）：
diff <(grep -oE 'href="#[a-z0-9-]+"' "$f" | sed 's/.*#//;s/"//' | sort -u) \
     <(grep -oE '<section id="[a-z0-9-]+"' "$f" | sed 's/.*"//' | sort -u)
# 浏览器打开，肉眼确认图表与代码块渲染正常
```
