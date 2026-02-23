# Finding and Analyze: skill to make any coding agent capable as openclaw

- Status: complete

## Inputs Linked to Source
- Key source snippets:
  - openclaw 提供的是平台能力集合，不只是 prompt/skill（gateway、multi-agent routing、tools、channels、apps、runtime/safety）。
  - openclaw 声明支持 browser control、session model、skills registry、多渠道接入、sandbox 策略。
- Evidence quality note:
  - 证据来自 `openclaw/README.md` 公开能力描述，适合做边界判断；实现细节仍需后续代码级核验。

## Extracted Findings
| Finding | Evidence | Confidence (1-5) | Notes |
|---------|----------|------------------|-------|
| openclaw 是“平台+运行时”，不是单一 skill | README 的 Highlights / Core platform / Runtime + safety / Channels | 5 | 目标若是“全量等价”，会超出 skill 范畴 |
| 纯 skill 无法新增宿主不存在的系统工具 | 任意 agent 的工具集合由宿主决定 | 5 | skill 最多做 orchestration/策略，不是能力注入器 |
| “任意 coding agent”带来强异构适配成本 | 不同 agent 在工具协议、权限、沙箱、会话模型上差异巨大 | 4 | 必须先抽象 capability contract |
| 可行路径是“分层 + 适配器 + 逐级扩展” | 先锁定 coding 任务，再逐步接入 runtime 组件 | 4 | 避免一开始追求全量平台等价 |

## Option Set (3-7)
| Option | Summary | Expected Impact | Complexity | Risks |
|--------|---------|-----------------|------------|-------|
| O1: Prompt-only Mega Skill | 只靠 SKILL.md + 少量脚本模拟 openclaw 能力 | 启动快 | 低-中 | 真实能力缺口大，极易“看起来会、实际上做不到” |
| O2: Skill + Capability Contract + Host Adapters | 定义统一能力契约（exec/fs/net/session/tool-call），每个宿主实现 adapter | 中长期可扩展 | 高 | 适配器工程量大，兼容矩阵复杂 |
| O3: Skill + OpenClaw Sidecar Runtime | skill 统一调用 sidecar（网关/工具编排），宿主只做指挥 | 功能覆盖高 | 很高 | 部署复杂、运维和安全压力大 |
| O4: 先做 Coding Parity 子集（推荐） | 明确只追“coding 工作流等价”，将渠道/原生节点列为后续阶段 | 最快形成可用价值 | 中 | 需要严格定义“不在首期”范围，避免预期失控 |
| O5: 仅做 OpenClaw Compatibility Spec | 先产出规范与测试套件，不承诺立即功能齐平 | 降低盲目开发风险 | 中 | 短期用户感知价值较弱 |

## Decision Matrix
- 评分口径：`Score = Impact + Confidence - Effort - Risk`（值越大越优先）
| Option | Impact(1-5) | Effort(1-5) | Risk(1-5) | Confidence(1-5) | Score |
|--------|-------------|-------------|-----------|------------------|-------|
| O1 | 2 | 2 | 5 | 2 | -3 |
| O2 | 4 | 5 | 3 | 4 | 0 |
| O3 | 5 | 5 | 4 | 3 | -1 |
| O4 | 5 | 3 | 2 | 4 | 4 |
| O5 | 3 | 3 | 2 | 4 | 2 |

## Recommended Direction
- Primary:
  - O4（Coding Parity 子集）+ O2（能力契约与适配器）组合路线。
- Fallback:
  - O5（先规范后实现），用于团队资源不足或目标不稳定时。
- Why:
  - 在不否认终局愿景的前提下，先把“可交付、可验证、可演进”做出来。
  - 避免把平台级能力误判为 skill 能力，导致项目早期失败。

## Open Questions
- 是否允许引入 sidecar/runtime（若允许，O3 可作为中长期目标）。
- 首期“coding parity”的验收任务集如何定义（建议 20-50 个标准任务）。
- 许可证、依赖合规、第三方渠道 API 成本预算是否可接受。
- 安全模型选择：默认全权限还是强制沙箱/审批。

## Completion Gate
- [x] At least 3 materially different options were compared.
- [x] Primary and fallback choices are explicit.
- [x] Stage status updated before moving to handoff.
