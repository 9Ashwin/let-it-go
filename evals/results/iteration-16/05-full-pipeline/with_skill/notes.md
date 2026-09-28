# 05-full-pipeline / with_skill

- dsh：`/tmp/ltg-bin/dsh`
- 耗时：1178.9s
- token：3443154
- 步数：42，工具调用：64

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。按 let-it-go 的流程走的：**`/prd` → `/to-issues` → `/loop-it`（单单元）→ `/review-it` → `/ship-it`**。

> 说明：你给的是「一句诉求 + 怎么落地你定」，`loop-it` 明确要求这种**未成形需求**先走规划半边（`prd`），所以加载的入口技能是 **`prd`**，再一路往下，而不是直接进 `loop-it`。

## 交付了什么

**行为**：`config/thresholds.json` 里按仓库配阈值，没配的走原来的默认值 5；改文件即生效，不用重新构建/重启。

```json
{ "chengdu": 2, "wuhan": 10 }
```

**实现**（`inventory/stock.go`）：
- 每次判定低库存时重新 `os.ReadFile` + `json.Unmarshal` 读配置——**无缓存、无锁、无文件监听**，天然并发安全，运维改完下一次调用就是新值。
- 未配置 / 文件缺失 / 非法 JSON / 值非整数 / 值为 `null` → 回退 `DefaultLowStockThreshold(5)`，不 panic。
- 公开 API（`LowStockThreshold` / `IsLowStock` / `LowStockWarehouses`）签名与「严格小于」语义不变。
- 出厂 `config/thresholds.json` 交付为 `{}`，`config/README.md` 写清格式与路径语义。

**需求资料**：`requirements/001-per-warehouse-thresholds/`（PRD、issue-001、README、走查件、交付记录），并登记到 `requirements/README.md`。

## 证据

- `make check`（build + test + vet）**退出码 0**；`go test ./... -race -count=1`、`-shuffle=on` 均绿。
- 新增 `inventory/thresholds_test.go`（10 条，新文件），覆盖配置覆盖、默认回退、**热加载**、缺失/非法/`null` 回退、严格小于、按仓库判定、真实文件端到端。冻结的 `inventory/stock_test.go` 未动，哈希与 HEAD 及 `origin/main` 一致（`3bc0a3e4…`）。
- 观测层级：L1 全部验收条件；L2 真实落盘配置的端到端；**L3/L4 不适用**——本仓库是纯后端库，无服务入口与外部系统，未起服务，如实记录。

## 评审（独立子代理，三轮）

评审抓到并已修的真实问题：
1. `{"仓库": null}` 会被 `map[string]int` 静默解成阈值 `0`（等于关掉该仓库的低库存检测）→ 改用 `map[string]*int`，`null` 按未配置回退默认值。
2. 默认路径测试无区分力（出厂 `{}` 与「文件缺失」退化同色）→ 换成在临时工作目录放真实文件、断言读到内容的测试，并已实测「路径写错必红」。
3. 文档/注释与实现的措辞不一致（类型错整份作废、是否允许负数）→ 已对齐，PRD 补 FR-8、issue 补一条 AC。
4. 交付记录悬空引用、测试计数过期 → 已补 `records/`、`notes/`，计数改正。

## 交付（本地模式）

`gh` 不可用，按技能走**本地模式**：功能分支 + `--no-ff` 合入，不建 PR。

- 实现：`1c36525`；合入：`a9b538f`；记录：`5d71de5`（当前 `main`）
- 已推 `origin` 的 `main` 与 `feat/001-per-warehouse-thresholds`，分支保留作留档，工作树干净。

## 待你确认（PRD 里标了 `[Assumption]`）

- 阈值是否要**拒绝负数**（当前原样接受，负值会让该仓库永不低库存）；非法配置是否要**告警/日志**（当前静默回退）。
- `config/README.md` 已注明路径**相对进程工作目录**——服务需从仓库根启动才命中 `config/thresholds.json`。
- PRD 评审状态仍是「待评审 @待指定」（本轮无人可问，按不阻塞处理，未伪造人工验收）。
