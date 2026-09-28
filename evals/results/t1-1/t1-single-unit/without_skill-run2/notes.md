# t1-single-unit / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：19.1s
- token：51698
- 步数：5，工具调用：6

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**（两个新文件，冻结基线零改动）：

- `greeter/slug.go` — `Slug` 用 `strings.Fields` 按空白切分，再 `ToLower` + `Join("-")`，一次覆盖去首尾空白、折连续空白、转小写三个验收条件。
- `greeter/slug_test.go` — 新行为测试，逐条对应 issue 里的三个用例。

**门禁**：`make check` 通过（build + test 全绿，exit 0）。`git status` 只有这两个新文件，`Makefile` 与 `greeter/greet_test.go` 逐字节未动。
