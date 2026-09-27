# eval fixture — 库存服务

这是一个**评测用的真实代码示例**：一个小而完整的 Python 服务，有自己的门禁、自己的约定、
自己的测试。eval 的用例把它复制到临时目录并 `git init` 之后，让 agent 在它里面干活。

## 约定

- **作用域根是 `requirements/<scope>/`**（不是技能默认的 `tasks/<feature>/`）。
  需求资料按 `requirements/<scope>/documents/`、`issues/`、`notes/`、`records/` 落位。
- **门禁是 `make check`**（= `make test` + `make lint`）。改动之后必须它绿。
- 只改本仓库内的文件。

## 结构

```
inventory/     业务代码
tests/         单元测试（unittest，标准库）
requirements/  需求资料（作用域根）
Makefile       门禁
```
