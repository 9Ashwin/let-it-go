# let-it-go — the commands you run while maintaining this skill set.
#
# Every target is a thin wrapper over scripts/, so the same thing works by hand, from CI,
# or from a shell alias. `make` with no target prints the list.
#
# The one you will actually use: `make vendor-update` — re-pin every vendored skill to its
# upstream default branch, copy it in, and re-validate.

SHELL := /bin/bash
PY ?= python3

.DEFAULT_GOAL := help
.PHONY: help deps check test vendor vendor-check vendor-update vendor-list vendor-add

help:  ## List every target
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

deps:  ## Install the checkers' own dependencies (the skills need none)
	$(PY) -m pip install -r requirements.txt

check:  ## Validate the skill set: layout, frontmatter, cross-references, patch, installer manifest
	$(PY) scripts/check_skills.py

test: check  ## Run the bundled scripts' self-tests, then validate
	$(PY) skills/flow/loop-it/scripts/test_loop_state.py
	$(PY) skills/flow/graph/scripts/test_graph_state.py
	$(PY) skills/flow/graph/scripts/test_render_graph_html.py

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
