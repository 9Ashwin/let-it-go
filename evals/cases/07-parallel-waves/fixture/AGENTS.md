# eval fixture — 零售后台

这是一个小而完整的 Go 服务：有自己的门禁、自己的约定、自己的测试。

## 约定

- **作用域根是 `requirements/<scope>/`**（不是技能默认的 `tasks/<feature>/`）。
  scope 目录**里面**怎么分，由写需求的那套流程自己定，定完写进 scope 自己的 README。
- **门禁是 `make check`**（= `make test` + `make lint`）。改动之后必须它绿。
- **验收基线冻结在现有的 `*_test.go` 里**：那些测试逐字节不许改（交付时会核对哈希）。
  你要为新行为写测试，**新建一个 `<name>_test.go` 文件**，不要往已有测试文件里追加——
  追加同样会改变那个文件的哈希，看起来就像把测试改弱了。
- 只改本仓库内的文件。

## 结构

```
inventory/     库存（package inventory）
pricing/       计价（package pricing）
report/        报表（package report）
requirements/  需求资料（作用域根）
Makefile       门禁
```

三个包互不重叠：`report` 依赖另外两个，`inventory` 与 `pricing` 之间没有依赖。
