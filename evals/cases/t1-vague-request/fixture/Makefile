# greeter —— 门禁在 `make check`

# 本机的 go 可能只装在 mise 下、不在默认 PATH 里，所以先解析再调用：
# 被测仓库不该假设调用者的 PATH 长什么样，门禁要能自己找到工具链。
GO ?= $(shell command -v go 2>/dev/null \
	|| ls -d $$HOME/.local/share/mise/installs/go/*/bin/go 2>/dev/null | tail -1)

check:
	$(GO) build ./...
	$(GO) test ./...

.PHONY: check
