# issue-002：给 counter 加一个 Max

## 验收条件

- `Max([]int{3, 9, 4})` 返回 `9`
- 空切片返回 `0`

## 交付方式

加在 `counter/` 包里，新行为的测试写进新文件（`counter/count_test.go` 是冻结基线，见 `AGENTS.md`），跑一遍 `make check`。

## 依赖

无。与 issue-001 不共享任何文件。
