# Changelog

## 0.0.9 — Thinking Control

- Expose Thinking Control for **16 of 58** registered LLMs, by exact model ID
  and verified credential site. The other 42 models do not show a thinking
  parameter in Dify.
- Show **思考模式：关闭／开启** for verified on/off protocols. Show
  **推理强度：none／low** for `gpt-5.5` and `gpt-5.6-luna`; do not present
  reasoning effort as a false boolean switch.
- On both sites: `qwen3.6-27b`, `qwen3.6-plus`, `qwen3.6-35b-a3b`,
  `qwen3.6-flash`, `qwen3.7-max`, `qwen3.7-plus`, `qwen3.8-max`,
  `glm-5.1`, `glm-5.2`, `kimi-k2.6`, `deepseek-v4-pro`.
- China site only: `qwen-plus`, `qwen3-max`, `deepseek-v4-flash`.
  Overseas site only: `gpt-5.5`, `gpt-5.6-luna`. Site-ineligible controls
  are hidden from the parameter schema and rejected in the runtime path.
- Keep the existing Function Calling capability allowlist unchanged:
  **41 `tool-call`**, **37 `stream-tool-call`**, **0 `multi-tool-call`**.

Verification scope: the new model/site Thinking Control evidence is primarily
non-stream ordinary chat; streaming and Function Calling have offline SDK
contract coverage, not blanket live verification. The 12 candidates tested in
the final gate remained unconfirmed and are not exposed. See
[`docs/THINKING_CONTROL_CAPABILITIES.md`](docs/THINKING_CONTROL_CAPABILITIES.md).

The top-level plugin version is `0.0.9`. The independent manifest format
version remains `meta.version: 0.0.6`; Python runner remains `3.12`.

## 0.0.8 — Function Calling

- 41 registered models expose `tool-call`; 37 expose `stream-tool-call`.
- No model exposes `multi-tool-call`. Ten China-only positive tool results
  remain ledger-only because the public tool-capability YAML is shared.
