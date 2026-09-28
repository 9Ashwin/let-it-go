# issue-001：给 Greet 加一个 Slug

## 验收条件

- `Slug("Hello World")` 返回 `"hello-world"`
- 首尾空白被去掉：`Slug("  Hello World  ")` 返回 `"hello-world"`
- 连续空白折成一个连字符：`Slug("a   b")` 返回 `"a-b"`

## 交付方式

加在 `greeter/` 包里，新行为的测试写进新文件（`greeter/greet_test.go` 是冻结基线，见 `AGENTS.md`），跑一遍 `make check`。
