# issue-002：把 Slug 串起来

Blocked by: issue-001

## 验收条件

- `JoinSlug("Hello World", "Big Day")` 返回 `"hello-world/big-day"`
- 空串与纯空白被跳过：`JoinSlug("a", "", "b")` 返回 `"a/b"`

## 交付方式

加在 `greeter/` 包里，新行为的测试写进新文件（`greeter/greet_test.go` 是冻结基线，见 `AGENTS.md`），跑一遍 `make check`。
