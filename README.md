# beclaw

`beclaw` is a project-local Bagakit workspace for experimenting with a
Feishu-to-long-run execution loop. The repository currently centers on Lobster
Shell v0, a small bridge that accepts inbound Feishu-style webhook payloads,
normalizes them into `.bagakit/long-run/ralph-msg.md`, and dispatches the
Bagakit long-run loop.

## Repository Shape

- `AGENTS.md` contains the local agent operating rules and managed Bagakit
  blocks.
- `.bagakit/lobster-shell/` contains the webhook daemon, local config example,
  persona overlay, and tests.
- `.bagakit/long-run/` contains the long-run runner prompts and orchestration
  scripts.
- `docs/must-*.md` contains mandatory local documentation rules for agents and
  maintainers.
- `Makefile` exposes the common local entrypoints.

## Quick Verification

Run the stable local checks before changing daemon behavior or packaging:

```sh
make lobster-shell-self-check
python3 -m unittest discover -s .bagakit/lobster-shell/tests -p 'test_*.py'
```

The self-check uses local files only. It may create ignored runtime artifacts
under `.bagakit/lobster-shell/state/`, `.bagakit/lobster-shell/runtime/`, and
`.bagakit/lobster-shell/outbox/`.

## Running Locally

Copy `.bagakit/lobster-shell/config.example.json` to
`.bagakit/lobster-shell/config.json` and replace placeholder values before
running the daemon. Use an obvious placeholder such as `replace-me` in examples;
do not commit real webhook secrets.

```sh
export BAGAKIT_AGENT_CMD="codex exec {prompt_text}"
make lobster-shell-daemon
```

Optional Makefile overrides:

```sh
make lobster-shell-daemon LOBSTER_SHELL_HOST=127.0.0.1 LOBSTER_SHELL_PORT=8765
```

For one-shot long-run execution without the webhook daemon:

```sh
make ralphloop
```

## Public Packaging Notes

Keep committed files portable and reviewable:

- Do not commit real secrets, tokens, passwords, credentials, Authorization
  headers, or bearer values.
- Do not commit machine-specific absolute paths, local usernames, generated
  logs, SQLite databases, or outbox records.
- Keep generated runtime state in ignored paths such as
  `.bagakit/lobster-shell/runtime/`, `.bagakit/lobster-shell/state/`, and
  `.bagakit/lobster-shell/outbox/`.
- Prefer standard-library tests and local fixtures for CI so the repository does
  not depend on live Feishu services or a locally installed coding agent.

## License and Distribution Boundary

This repository currently has no repository-level open source license. Do not
treat the full workspace as a reusable distribution by default. Scripts,
templates, or subpackages that should be reused elsewhere should be split out or
given an explicit license and distribution statement.

Agent state and workspace-specific materials are not default reusable assets.
This includes persona overlays, local config, mailbox, memory, session records,
archives, and harness artifacts. Review and separate any reusable runtime asset
before publishing or vendoring it outside this workspace.
