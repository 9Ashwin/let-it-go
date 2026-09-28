# issue-001：给 greeter 加一个 Upper

## 验收条件

- `Upper("ada")` 返回 `"ADA"`
- 空字符串返回空字符串

## 交付方式

加在 `greeter/` 包里，新行为的测试写进新文件（`greeter/greet_test.go` 是冻结基线，见 `AGENTS.md`），跑一遍 `make check`。

## 依赖

无。与 issue-002 不共享任何文件。
