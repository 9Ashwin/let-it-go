# t1-single-unit / without_skill

- dsh：`/tmp/bin/dsh`
- 耗时：26.3s
- token：85301
- 步数：8，工具调用：9

同目录下的 `grading.json` 是从**外部**给这次运行打的分——不是臂自己声称的结果。
工作目录留在 `work/`，可以自己进去复核。

## 臂最后说了什么

做完了。

**改动**
- `greeter/greet.go`：新增 `Slug`，用 `strings.Fields` 切分（顺带完成去首尾空白 + 折叠连续空白），再用 `-` 连接并转小写。
- `greeter/greet_test.go`：新增 `TestSlug`，逐条覆盖卡片里的三个验收条件。

**门禁**
```
make check
ok  example.com/greeter/greeter  0.012s
```
build 和 test 都通过，没弄坏原有 `Greet`。
