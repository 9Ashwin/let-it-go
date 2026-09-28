# t1-serial-batch / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：45.1s
- token：158724
- 步数：12，工具调用：20

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡片已按依赖顺序做完，门禁通过。

## 做了什么

**issue-001 — `Slug`**
- 新增 `greeter/slug.go`：`strings.Fields(strings.ToLower(s))` 折成连字符，天然处理首尾空白与连续空白。
- 新增 `greeter/slug_test.go`：覆盖三条验收（`"Hello World"`、`"  Hello World  "`、`"a   b"`）。

**issue-002 — `JoinSlug`（依赖 `Slug`）**
- 新增 `greeter/join_slug.go`：逐个 `Slug`，跳过空结果，用 `/` 连接。
- 新增 `greeter/join_slug_test.go`：覆盖 `("Hello World","Big Day")` 与 `("a","","b")`；另加一条卡片标题点明的「纯空白被跳过」用例。

## 门禁结果

```
go build ./...   ✅
go test ./...    ok  example.com/greeter/greeter
```

- 冻结基线核对：`Makefile`、`greeter/greet_test.go` 的 `git diff` 为空 → **逐字节未变**。
- 改动全部是新增文件（`slug.go` / `slug_test.go` / `join_slug.go` / `join_slug_test.go`），未触碰既有代码。

未提交（你只要求做完并跑门禁）。需要我提交的话说一声。
