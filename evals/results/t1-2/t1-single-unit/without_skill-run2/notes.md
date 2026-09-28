# t1-single-unit / without_skill

- dsh：`（--regrade：没重跑 dsh，只重新打分）`
- 耗时：26.7s
- token：64542
- 步数：6，工具调用：10

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

卡片做完了。

## 改动

- **`greeter/slug.go`（新增）**：实现 `Slug`
  ```go
  func Slug(s string) string {
      return strings.Join(strings.Fields(strings.ToLower(s)), "-")
  }
  ```
  `strings.Fields` 顺带处理了首尾空白与连续空白两件事——它按任意空白切分并丢弃空字段，所以"去首尾"和"折成一个连字符"是同一步，不需要额外写 trim 和正则。
- **`greeter/slug_test.go`（新增）**：表驱动测试，覆盖卡片的三条验收条件。

## 门禁

`make check` 通过（`go build ./...` + `go test ./...`，exit 0），`TestGreet` 与 `TestSlug` 都 PASS，`gofmt -l greeter/` 无输出。

## 冻结基线

`Makefile` 与 `greeter/greet_test.go` 未改动，sha256 与动手前一致：

```
3ba8f86e…5c3b  Makefile
de952bb1…6ae   greeter/greet_test.go
```

一点说明：实现只按验收条件做了 ASCII 空白 + 小写，没有加 Unicode 音译、标点处理之类的额外行为（没被要求，属于投机）。如果后续要 `Slug("Héllo, Wörld!")` 这类，需要另开卡片定义规则。
