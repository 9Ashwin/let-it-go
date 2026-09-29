# 05-full-pipeline / with_skill

- dsh：`/tmp/bin/dsh`
- 耗时：1234.3s
- token：3632487
- 步数：54，工具调用：71

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 `let-it-go` 的对应流程走完：`prd` → `to-issues` → `loop-it`（单单元内联）→ `review-it`（独立子代理两轴评审）→ `ship-it`（本地模式，无 `gh`）。

## 落地方式

配置载体 `config/thresholds.json`，扁平映射「仓库名 → 阈值」：

```json
{ "beijing": 10, "shanghai": 3 }
```

- `inventory/stock.go` 在**每次调用时**重新读文件，所以运维改完文件立即生效，**不需要重新构建**（也没缓存、没监听）。
- 文件里没列的仓库回退 `DefaultLowStockThreshold`（仍是 5）。
- 配置文件定位：从当前工作目录向上找 `config/thresholds.json`，**到含 `go.mod` 的仓库根即停**——兼容「从仓库根启动」和「`go test` 以包目录为 cwd」，又不会误读仓库外祖先目录的同名配置。
- 缺失文件、整体非法 JSON、单条值不是整数或为 `null`，都不 panic，按范围回退默认值。
- 公开 API 与语义未动，`inventory/stock_test.go` 逐字节未改（哈希与 seed 一致）。

## 证据

- 门禁：`make check`（build + test + vet）退出码 0。
- 新增 `inventory/thresholds_test.go`（新文件，未追加到冻结测试），覆盖配置生效/回退/热生效/坏值容错/发现边界。
- L3：仓库外编译**一次**探针，只改文件不重编译：`{"beijing":3}`→`threshold=3`，改 `{"beijing":7}`→`threshold=7`；非法 JSON→`5`；从 `inventory/` 子目录运行也能向上发现仓库根配置。
- 独立复审：Spec / Standards 两轴通过；边界回归测试经「删掉 go.mod 边界 → 变红、恢复 → 变绿」的变异验证。

## 交付

- 分支 `feat/per-warehouse-low-stock-threshold`（`main` 未动），两个 commit：
  - `8bb1d14` feat: 实现 + 测试 + 配置
  - `7f516b2` docs: 实现总结（写进了 issue 卡片）
- 需求资料在 `requirements/001-per-warehouse-low-stock-threshold/`（PRD、issue 契约、验收表），`requirements/README.md` 已登记顺序号。
- 仓库里的 `config/thresholds.json` 提交为 `{}`，默认行为与改动前完全一致；具体阈值由运维按需写入。格式说明补在 `config/README.md`。

合入归你：`git merge --no-ff feat/per-warehouse-low-stock-threshold`（本地模式无 PR，我没有合入）。

一个说明：`inventory/stock_test.go` 把 `chengdu`/`wuhan` 当成「永远未配置」的样本，所以运维**不要**把这两个仓库名写进 `config/thresholds.json`，否则那条冻结测试会红——这是 fixture 基线的既有约束，不是本次实现的问题。
