# admin —— 一个 Go 后台管理系统（刚起步）

仓库里现在**只有** `internal/version` 这一个包。要做什么还没定——本仓库没有既有的
API 契约、没有数据模型、没有前端。

## 门禁

```bash
make check
```

## 作用域根

需求资料落在**仓库根**下：`documents/`（PRD、SPEC、设计）、`issues/`（issue 卡片与检查点）、
`notes/`。目录名不变。

## 冻结基线

`Makefile` 与 `internal/version/version_test.go` 是**冻结的验收基线**：改动之后必须逐字节不变。
新行为的测试写进**新文件**。把基线改弱换绿不算完成。
