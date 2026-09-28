# t1-serial-batch / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：57.0s
- token：200565
- 步数：15，工具调用：22

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

两张卡按依赖顺序做完了，门禁通过。

## 做了什么

**issue-001 — `Slug`**
- `greeter/slug.go`：用 `strings.Fields` 去首尾空白并把连续空白折成一个连字符，再 `ToLower`，一次覆盖三条验收。
- `greeter/slug_test.go`（新文件）：三条验收 + 空串/纯空白两个边界。

**issue-002 — `JoinSlug`**（依赖 issue-001）
- `greeter/join_slug.go`：对每段调 `Slug`，跳过折成空串的段，用 `/` 拼接。
- `greeter/join_slug_test.go`（新文件）：两条验收 + 纯空白段跳过、无参数两个边界。

按红-绿推进：每张卡先写测试跑出门禁变红（`undefined: Slug` / `undefined: JoinSlug`），再补实现转绿。

## 门禁结果

```
make check
go build ./...   ✓
go test ./...    ok  example.com/greeter/greeter
[exit code: 0]
```

单测明细：`TestGreet`、`TestSlug`、`TestJoinSlug` 全 PASS。

## 冻结基线

`git diff --exit-code -- Makefile greeter/greet_test.go` 退出码 0——两个冻结文件逐字节未动。本次只新增 4 个文件，没有改任何既有文件：

```
?? greeter/join_slug.go
?? greeter/join_slug_test.go
?? greeter/slug.go
?? greeter/slug_test.go
```

改动未提交（你没要求 commit）；需要的话我可以按仓库约定提交。
