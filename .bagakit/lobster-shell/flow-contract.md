# Lobster Shell Stack Flow Contract

This file defines the stack-specific orchestration used by bagakit-lobster-shell.

## Stage Flow
1. Inbox intake (Feishu or other async source) normalizes inbound messages.
2. Brainstorm intake (optional path): unresolved requests are routed to `bagakit-brainstorm` artifacts.
3. Feat conversion: actionable work is tracked by `bagakit-feat-task-harness` feat/task SSOT.
4. Long-run dispatch: `bagakit-long-run` executes one item at a time.
5. Living memory: `bagakit-living-docs` recalls before run and writes notes after run.

## Strong Dependency Profile
- This flow expects these skills to be installed in the same stack profile:
  - `bagakit-long-run`
  - `bagakit-feat-task-harness`
  - `bagakit-living-docs`
  - `bagakit-brainstorm`

## Event to Execution Mapping
- Inbound message -> `.bagakit/long-run/ralph-msg.md`
- One-shot dispatch -> `.bagakit/lobster-shell/runtime/run-<id>.log`
- Result summary -> `.bagakit/lobster-shell/outbox/results.jsonl`
- Memory note -> `docs/.bagakit/inbox/howto-lobster-shell-<id>.md`
