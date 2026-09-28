# greeter

一个很小的 Go 模块，用来演示按仓库约定走的流程。

## 门禁

```bash
make check
```

## 作用域根

需求资料落在 `requirements/<scope>/` 下：`documents/`（PRD、SPEC、设计）、
`issues/`（issue 卡片与检查点）、`notes/`。目录名不变。

## 冻结基线

`Makefile` 与 `greeter/greet_test.go` 是**冻结的验收基线**：改动之后必须逐字节不变。
新行为的测试写进**新文件**（例如 `greeter/slug_test.go`）。把基线改弱换绿不算完成。
