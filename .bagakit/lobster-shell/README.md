# Lobster Shell v0

Lobster Shell v0 is an execution shell around bagakit-long-run + bagakit-living-docs.

## Goal
- Accept async inbound messages (for example Feishu events).
- Inject identity + recalled memory into `.bagakit/long-run/ralph-msg.md`.
- Trigger one-shot long-run execution.
- Capture result into outbox + living-docs inbox.

## Components
- `scripts/feishu_longrun_daemon.py`: Feishu webhook listener + dispatcher.
- `scripts/run_once.sh`: one-shot wrapper over `ralphloop-runner.sh`.
- `scripts/bagakit_env.sh`: local skill path bootstrap.
- `identity.md`: injected identity prompt.
- Optional persona overlay:
  - set `LOBSTER_PERSONA_WORKSPACE=/Users/bytedance/.openclaw/workspace`
  - daemon will auto-load `IDENTITY.md` + `SOUL.md` + `USER.md` from that workspace.

## Quick Start
1. Export a non-interactive agent command (required by long-run):
   - `export BAGAKIT_AGENT_CMD="codex exec {prompt_text}"`
2. Start daemon:
   - `python3 .bagakit/lobster-shell/scripts/feishu_longrun_daemon.py --root . --host 127.0.0.1 --port 8765 --secret <token>`
3. Send POST JSON to `/feishu/event`.

## Event Contract (normalized)
The daemon tries to normalize Feishu payload into:
- `msg_id`
- `chat_id`
- `user_id`
- `text`
- `source`

Duplicate `msg_id` is ignored.

## Output Paths
- Runtime logs: `.bagakit/lobster-shell/runtime/`
- Outbox records: `.bagakit/lobster-shell/outbox/results.jsonl`
- Dedup DB: `.bagakit/lobster-shell/state/dedup.sqlite`
- Memory note: `docs/.bagakit/inbox/howto-lobster-shell-*.md`
