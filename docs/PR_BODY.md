<!--
  This file is the ready-to-paste body for the Pull Request you submit to
  https://github.com/langgenius/dify-plugins
  When you open the PR, GitHub will auto-load the official template. Select
  all of that template and replace it with the content below. Then fill in
  the Repository URL with your own GitHub source-code repo link.

  The content below already matches the latest official PR template fields.
-->

# Plugin Submission Form

## 1. Metadata

- **Plugin Author**: FDQ-shrimp
- **Plugin Name**: moyu_ai_provider
- **Repository URL**: https://github.com/FDQ-shrimp/moyu_ai_provider   <!-- ← replace if your source repo lives at a different URL -->

## 2. Submission Type

- [x] New plugin submission
- [ ] Version update for existing plugin

## 3. Description

Moyu AI (moyu.ai) is a third-party LLM aggregation platform that exposes an
OpenAI-compatible chat/completions endpoint. This plugin packages that
platform as a Dify **Model Provider** so Dify users can plug in a Moyu AI
API key and call the full catalogue of 119 upstream text models
(OpenAI / Anthropic / Google / DeepSeek / Qwen / Kimi / Grok / …) from any
LLM node, chatflow or agent.

**Key facts**

- Type: Model Provider plugin (model.llm enabled, OpenAI-compat adapter)
- Author: community developer — not officially operated by Moyu AI
- Credentials: a single `api_key` entered in the Dify UI (secret-input),
  never hard-coded in the package
- Models: 119 predefined LLM YAMLs, generated directly from Moyu AI's
  `/v1/models` endpoint so label names match upstream exactly
- Endpoint: `https://api.moyu.ai/v1` (OpenAI-compatible `chat/completions`)
- Dependencies: `dify_plugin`, `requests`, `pyyaml` only — `openai` SDK is
  intentionally not required (the Dify OAI-compat base class is used)
- Package size: ~213 KB (135 entries, leak-free — scripts/tests/docs/.env
  excluded via `.difyignore`)

**Availability report (transparency)**

With the API key used for testing, 76 / 119 models returned `200 OK`, and
43 returned errors that come from upstream policy — mostly HTTP 429 (rate
limit on the test key) or HTTP 400 (image / video / TTS models that do not
speak the `chat/completions` protocol). These 43 YAMLs are intentionally
kept in the plugin because availability depends on the **user's own**
account tier and quota, not on the plugin code. A human-readable breakdown
lives inside the source repo at `docs/MODEL_AVAILABILITY.md`.

**Relation to Moyu AI**

This is a community integration. The plugin talks to Moyu AI's **public**
OpenAI-compatible API; users must sign up at moyu.ai and supply their own
API key. No Moyu AI credential or debug token is bundled in the package.

## 4. Checklist

- [x] I have read and followed the Publish to Dify Marketplace guidelines
- [x] I have read and comply with the Plugin Developer Agreement
- [x] I confirm my plugin works properly on both Dify Community Edition and Cloud Version
- [x] I confirm my plugin has been thoroughly tested for completeness and functionality
- [x] My plugin brings new value to Dify

## 5. Documentation Checklist

Please confirm that your plugin README includes all necessary information:

- [x] Step-by-step setup instructions
- [x] Detailed usage instructions
- [x] All required APIs and credentials are clearly listed
- [x] Connection requirements and configuration details
- [x] Link to the repository for the plugin source code

## 6. Privacy Protection Information

Based on Dify Plugin Privacy Protection
[Guidelines](https://docs.dify.ai/plugins/publish-plugins/publish-to-dify-marketplace/plugin-privacy-protection-guidelines):

### Data Collection

The plugin itself does **not** collect any personal data. Its only job is
to relay the chat messages that a Dify user explicitly sends to the Moyu
AI API, together with the user's API key taken from Dify's encrypted
credential storage.

However, because the plugin forwards traffic to a third-party service
(Moyu AI), the following data is unavoidably transmitted to that upstream:

- The API key the user configures in Dify (sent as the `Authorization:
  Bearer …` header, per OpenAI convention).
- The chat messages / prompts that the user sends from a Dify LLM node
  or agent. These may contain whatever content the user decides to put in
  the prompt, including — depending on the user's own use case — personal
  or business data.
- Standard HTTP metadata (User-Agent, timestamps, IP of the Dify runtime
  that forwards the request).

No analytics, telemetry, third-party trackers, or external logging are
added by the plugin. The plugin does not persist any of the above on its
own side; everything happens in-memory during a single request.

For Moyu AI's own data handling practices, users should consult the Moyu
AI Terms of Service and Privacy Policy directly on their website.

The full privacy statement (including what is collected, how it is used,
and what is not collected) is included in the plugin package as
`privacy.md`.

### Privacy Policy

- [x] I confirm that I have prepared and included a privacy policy in my plugin package based on the Plugin Privacy Protection Guidelines
