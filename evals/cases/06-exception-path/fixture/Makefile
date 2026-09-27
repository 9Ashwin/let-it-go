# 库存服务 —— 门禁在 `make check`

# 本机的 go 可能只装在 mise 下、不在默认 PATH 里，所以先解析再调用：
# 被测仓库不该假设调用者的 PATH 长什么样，门禁要能自己找到工具链。
GO ?= $(shell command -v go 2>/dev/null \
	|| ls -d $$HOME/.local/share/mise/installs/go/*/bin/go 2>/dev/null | tail -1)

.DEFAULT_GOAL := help
.PHONY: help check build test lint

help:  ## 列出所有目标
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

check: build test lint  ## 门禁：构建 + 测试 + vet（改动之后必须绿）
build:  ## 编译
	$(GO) build ./...
test:  ## 单元测试
	$(GO) test ./...
lint:  ## go vet
	$(GO) vet ./...
