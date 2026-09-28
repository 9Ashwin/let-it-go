# 参考材料的结论：采纳了什么、没采纳什么

不是读书笔记。这里只记**每条材料最终落到哪、以及为什么没落**，给下一轮调优技能时当输入用。
已经写进 `skills/flow/loop-it/CONTRACT.md` 或 `dsh-runtime.md` 的，只留指针。

## 1. OpenAI — Harness Engineering

**原文没读到**（openai.com 403，中文页只返回 JS 壳）。下面这条来自二手转述，按待核处理。

- **采纳**：单一记录系统，其余全是指针；根文件是地图不是手册。→ CONTRACT「维护层级」。
- **没采纳**：docs 树 / golden principles 的具体形态——原文没读到，不落笔。

## 2. Anthropic — Harness design for long-running application development

- **采纳**：生成者与评判者必须分离，逐条硬阈值，任一条不达标整体不通过 → CONTRACT §5。
- **采纳**：证据必须由**能操作真实运行物**的那一层产生；判据落在已拿到的观测上，不落在事前信心上 → §4。
- **采纳**：planner 刻意不写细粒度实现（写细了错误会级联进实现）→ `to-design` 的「Implementation 不写细粒度步骤」。
- **采纳**：复杂度按「模型单独可靠边界」增减，用 evals 的历史做判据 → AGENTS.md 已有那条硬规则。
- **没采纳**：Playwright MCP 那套真实浏览器点检——DSH 没有这个工具；L3 用 `make smoke` 代替。

## 3. ThoughtWorks / martinfowler.com — Maintainability sensors for coding agents

- **采纳**：**规则住在检查器的报错消息里**，不住在散文里（"a good kind of prompt injection"）→ CONTRACT「维护层级」。
- **采纳**：覆盖率不是证据；永远绿的门禁可疑；从不失败的传感器说明它不必要 → §4 + `evals/NEXT.md` 的第一刀。
- **采纳**：靠散文叮嘱（"记得跑门禁"）在无人值守时必然失效 → 同上。
- **没采纳**：具体 lint 格式化器的写法——那是每个仓库自己的事，技能里写不了。

## 4. Plan Mode 已死（原文 + 两篇中文讨论）

- **采纳**：planning 是**持续更新的状态**，不是一次性计划文档 → 工作状态对象（CONTRACT §1）。
- **采纳**：低风险、可回滚、验证条件明确的任务直接进行动回路 → 三个 profile 的仪式量差一个数量级（§3）。
- **采纳**：`human_checkpoint` 由**危险面**触发，不由阶段触发，判据写成固定清单 → §5。
- **采纳**：别把状态做成第二份长文档，也别加摘要层；"要不要规划"这个元问题不该抛回给人 → §1、§3。
- **采纳**：文档可以没有，判据不能没有（验收条件可证伪 + 回滚路径 + 要哪一层证据已知）→ §3。

## 5. Raven（V0.2.0）

- **采纳**：证据地板——只有真正发生过的动作算证据；**完成 ≠ 成功**（"跑了但 401"不算）；验收与复现步骤必须跑在**当前未改动的代码**上 → CONTRACT §4。
- **采纳**：**写在提示里的保证不是保证**——报告缺字段就打回并指名缺哪个；行动声明要由工具层的日志背书 → §5。
- **采纳**：跨回合续跑不能靠"模型记得下次回来"，那一腿由无判断的常驻循环兜住 → DSH 的 goal round driver 就是它，写进 §6。
- **采纳**：声明 + 索引，不引入额外状态文件；`unknown` 要指名 blocker，不伪造 ready → §1、§2。
- **没采纳（现在）**：每轮一次全量 reconcile 的 `step()`、重试换幂等键、ledger 原子写 + fsync、拒绝从空 ledger 启动。`loop_state.py` 已经有"合并旧状态、损坏文件报错拒绝覆盖"，但没做 fsync 与幂等键——**这是一条真实的差距**，改脚本时可以考虑。
- **没采纳**：ask 预算 / 静默时段那套"人的注意力"契约——DSH 没有对应的工具层闸门，写成技能是空话。

## 6. Codex Workspace Bot — Story → Delivered SOP

- **采纳**：Story 五态（Draft/Ready/In Development/Delivered/Superseded）+ 正文固定章节 → 契约五字段（issue 正文）+ 进度（检查点）；DoD 逐条必须有**当前证据**，证据不足就停在非终态。
- **采纳**：`/goal` 的权威终态只认 goal 本身，**绝不自己伪造 turn/start 循环**；一个 turn 完成 ≠ 完成 → CONTRACT §6。
- **采纳**：不要因为"存在某个机制"就创建 Skill / Hook / CI 关卡——只有形成稳定边界或可验证失败模式才创建，并指定负责人与验证路径 → AGENTS.md 的"假设会过期"那条。
- **没采纳**：云端 Test/Prod、发布审批、回滚演练、企业级安全架构——开源与个人自用的边界不需要。

## 7. 一条要更正的引用

issue #3 参考里写的「Anthropic ART / Harness of Harnesses」**对不上**：那篇是 Matt von Hippel 的客座文，
讲 Claude Science 算 N=4 SYM 九圈振幅，"harness" 只以"Claude Science 是个 harness"出现，ART 这个词不存在。
唯一可借鉴的是它的验证方式：同一结果用两条独立路线算出来，再由一个独立的人复核。
