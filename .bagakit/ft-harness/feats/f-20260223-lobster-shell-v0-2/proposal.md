# Feat Proposal: f-20260223-lobster-shell-v0-2

## Why
- Need a deterministic "lobster shell" execution layer around coding agents:
  - async inbox intake
  - long-run orchestration loop
  - memory recall/writeback via living-docs
  - result callback after each run
- Current brainstorm output exists, but it is not yet tracked in feat/task SSOT.

## Goal
- Convert current brainstorm into tracked feat and ship initial harness artifacts.

## Scope
- In scope:
  - bootstrap feat/task harness runtime in this repo
  - register a new feat for "lobster-shell-v0"
  - preserve brainstorm outputs as decision evidence for this feat
- Out of scope:
  - full implementation of feishu daemon / adapter runtime
  - production hardening for multi-agent compatibility matrix

## Impact
- Code paths:
  - `.bagakit/brainstorm/**`
  - `.bagakit/ft-harness/**`
  - `.codex/skills/bagakit-feat-task-harness/docs/**`
- Tests:
  - harness validation via `validate-harness`
- Rollout notes:
  - this commit is planning/bootstrap only; implementation happens in follow-up tasks
