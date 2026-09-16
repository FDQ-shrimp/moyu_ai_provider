# Privacy Statement — Moyu AI Dify Model Provider Plugin

_Last updated: 2026-04-21._
_Plugin name: `moyu_ai_provider` (see `manifest.yaml`)._

This document describes what information the **Moyu AI Dify model provider
plugin** ("the plugin") processes when a Dify user installs and uses it.
It is intended to satisfy the baseline privacy disclosure required by the
Dify Marketplace. It does **not** replace, and is explicitly subordinate to,
the privacy policy and terms of service of the upstream Moyu AI service.

中文版：本文件同时作为 Dify Marketplace 的隐私声明使用；所有向上游
魔芋AI 发送的数据均受魔芋AI 自身服务条款约束。

---

## 1. What the plugin collects

The plugin collects **the minimum information needed to call the Moyu AI
API on the user's behalf**. Specifically, from the user it only reads:

- **Moyu AI API Key** — entered by the user into the Dify provider
  configuration page. This field is declared as `secret-input` in
  `provider/moyu.yaml`. Dify stores it encrypted; the plugin never
  writes it to disk or logs.

The plugin **does not** collect:

- personal identifiers (name, email, phone number, IP address),
- telemetry about how the Dify workspace is being used,
- the contents of the user's other Dify apps or datasets beyond the
  specific prompt being executed.

---

## 2. What the plugin sends to Moyu AI

When a Dify app invokes a model provided by this plugin, the plugin sends
the following to `https://www.moyu.info/v1/chat/completions` over HTTPS:

- the configured API Key (as an `Authorization: Bearer …` header),
- the model identifier (e.g. `gpt-5.4`, `claude-opus-4-6`),
- the prompt messages, tool definitions, and generation parameters
  supplied by the calling Dify app,
- optional `stop` sequences, `stream` flag, and end-user id if the app
  passes one.

The plugin does not add any additional payload of its own. The response
from Moyu AI is forwarded back to Dify unchanged (beyond Dify's own
OAI-compatible normalisation).

**All content a user types into a Dify app that uses a Moyu AI model is
therefore processed by Moyu AI.** Users are responsible for making sure
they are allowed to send that content off-platform.

---

## 3. What the plugin stores locally

Nothing. The plugin has no database, no on-disk cache, and no local log
file of its own. Standard Dify runtime logs may record operational events
(e.g. "invoke started/failed"); these logs **do not include the API Key or
the raw prompt body**.

---

## 4. Third-party service

Moyu AI is operated independently of this plugin and of its author. When
you use this plugin, your data is processed by Moyu AI under Moyu AI's
own terms:

- Service homepage: <https://www.moyu.info/>
- You must consult Moyu AI's own terms of service and privacy policy for
  authoritative information about data retention, geographic location,
  sub-processors, etc.

The plugin author has no control over Moyu AI's data handling.

---

## 5. Children

The plugin does not knowingly process data from children. The API Key
must be obtained by an adult Moyu AI account holder who has accepted
Moyu AI's terms.

---

## 6. Security

- The API Key is passed only over HTTPS.
- The API Key is stored encrypted by Dify (not by the plugin).
- `.env` files used by plugin developers for remote-debug runs are
  explicitly excluded from the shipped `.difypkg` via `.difyignore`, and
  the repository's preflight script (`scripts/preflight_check.py`) fails
  the build if that rule is broken.

---

## 7. Your rights

Because the plugin itself does not persist personal data, data-subject
requests (access, erasure, rectification) must be addressed to **Moyu AI**
directly, via the channels listed on <https://www.moyu.info/>.

If you are a Dify workspace administrator and want to stop sharing any
prompt content with Moyu AI, simply remove the provider configuration
from the Dify UI and uninstall the plugin.

---

## 8. Maintainer contact

- Plugin author (per `manifest.yaml`): `fdq-shrimp`.
- The plugin author is a community contributor and is **not affiliated with
  or endorsed by Moyu AI**.
- For plugin-specific issues (installation, packaging, availability of
  model YAMLs), please file an issue in the plugin's source repository.
- For any data-handling question regarding the Moyu AI service itself,
  please contact Moyu AI.

> _Note._ This statement uses neutral language where a legal entity would
> normally be named. If and when this plugin is transferred to an
> organisation or an individual publishing under their legal name, this
> section should be updated accordingly before the next release.

---

## 9. Changes

Material changes to this privacy statement will be reflected in the
version bump of the plugin (`manifest.yaml > version`) and in the
updated revision date at the top of this file.
