GO ?= go
GOLANGCI_LINT ?= golangci-lint
PNPM ?= pnpm
LOBSTER_SHELL_DAEMON_FLAGS :=
ifneq ($(strip $(LOBSTER_SHELL_HOST)),)
LOBSTER_SHELL_DAEMON_FLAGS += --host $(LOBSTER_SHELL_HOST)
endif
ifneq ($(strip $(LOBSTER_SHELL_PORT)),)
LOBSTER_SHELL_DAEMON_FLAGS += --port $(LOBSTER_SHELL_PORT)
endif

export CODEX_HOME := $(PWD)/.codex

codex-locale:
	@echo "CODEX_HOME=$(CODEX_HOME)"
	@echo "Running codex with CODEX_HOME=$(CODEX_HOME)"
	codex -m gpt-5.3-codex -c model_reasoning_effort="xhigh" -c model_reasoning_summary_format=experimental --search --dangerously-bypass-approvals-and-sandbox

codex-locale-resume:
	@echo "CODEX_HOME=$(CODEX_HOME)"
	@echo "Running codex with CODEX_HOME=$(CODEX_HOME)"
	codex -m gpt-5.3-codex -c model_reasoning_effort="xhigh" -c model_reasoning_summary_format=experimental --search --dangerously-bypass-approvals-and-sandbox resume 


# BAGAKIT:LONGRUN:LAUNCHER:START
ralphloop:
	bash .bagakit/long-run/ralphloop-runner.sh
.PHONY: ralphloop
# BAGAKIT:LONGRUN:LAUNCHER:END


# BAGAKIT:LOBSTER-SHELL:START
lobster-shell-self-check:
	python3 .bagakit/lobster-shell/scripts/feishu_longrun_daemon.py --root . --self-check
.PHONY: lobster-shell-self-check

lobster-shell-test:
	python3 -m unittest discover -s .bagakit/lobster-shell/tests -p 'test_*.py'
.PHONY: lobster-shell-test

validate: lobster-shell-self-check lobster-shell-test
.PHONY: validate

lobster-shell-daemon:
	python3 .bagakit/lobster-shell/scripts/feishu_longrun_daemon.py --root . $(LOBSTER_SHELL_DAEMON_FLAGS)
.PHONY: lobster-shell-daemon
# BAGAKIT:LOBSTER-SHELL:END
