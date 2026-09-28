# let-it-go — the commands you run while maintaining this skill set.
#
# Every target is a thin wrapper over scripts/, so the same thing works by hand, from CI,
# or from a shell alias. `make` with no target prints the list.
#
# The one you will actually use: `make vendor-update` — re-pin every vendored skill to its
# upstream default branch, copy it in, and re-validate.

SHELL := /bin/bash
PY ?= python3

# eval 的 harness 是 Go 写的（和它的 fixture 同一种语言，所以 `make eval-*` 只需要一套工具链）。
# 本机的 go 可能只装在 mise 下、不在默认 PATH 里，所以和 fixture 的 Makefile 一样先解析再调用。
GO ?= $(shell command -v go 2>/dev/null \
	|| ls -d $$HOME/.local/share/mise/installs/go/*/bin/go 2>/dev/null | tail -1)
EVAL := $(GO) -C evals/harness run .

.DEFAULT_GOAL := help
.PHONY: help deps check test link link-check vendor vendor-check vendor-update vendor-list vendor-add \
	eval-build eval-check eval-list

help:  ## List every target
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

deps:  ## Install the checkers' own dependencies (the skills need none)
	$(PY) -m pip install -r requirements.txt

check:  ## Validate the skill set: layout, frontmatter, cross-references, patch, installer manifest
	$(PY) scripts/check_skills.py
	$(MAKE) --no-print-directory eval-check

test: check  ## Run the bundled scripts' self-tests, then validate
	$(PY) skills/flow/loop-it/scripts/test_loop_state.py
	$(PY) skills/flow/graph/scripts/test_graph_state.py
	$(PY) skills/flow/graph/scripts/test_render_graph_html.py

link:  ## Symlink every skill into ~/.agents/skills (git pull keeps them current; no copies)
	$(PY) scripts/link_skills.py

link-check:  ## Report drift between this repo's skills and ~/.agents/skills
	$(PY) scripts/link_skills.py --check

eval-build:  ## Build the harness to evals/harness/evalctl — the name the docs use for it
	$(GO) -C evals/harness build -o evalctl .

eval-check:  ## Self-check the eval workspace (case structure, no .git in fixtures, tamper_guard paths)
	$(GO) -C evals/harness test ./...
	$(EVAL) selfcheck

eval-list:  ## List the eval cases
	$(EVAL) list


vendor:  ## Copy every vendored skill in at its pinned commit
	$(PY) scripts/sync_vendor.py

vendor-check:  ## Report vendored skills whose upstream has moved
	$(PY) scripts/sync_vendor.py --check

vendor-update:  ## Re-pin every vendored skill to upstream HEAD, sync, and validate
	$(PY) scripts/sync_vendor.py --update

vendor-list:  ## List vendored skills and the commit each is pinned to
	$(PY) scripts/sync_vendor.py --list

vendor-add:  ## Vendor new skills: make vendor-add URL=<git url> SKILL="name [name...]"
	@test -n "$(URL)" || { echo 'usage: make vendor-add URL=<git url> SKILL="name [name...]"'; exit 1; }
	@test -n "$(SKILL)" || { echo 'usage: make vendor-add URL=<git url> SKILL="name [name...]"'; exit 1; }
	$(PY) scripts/sync_vendor.py --add "$(URL)" $(foreach s,$(SKILL),--skill $(s))
