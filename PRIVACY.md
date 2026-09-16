# Privacy Statement — Moyu AI Dify Model Provider Plugin

_Last updated: 2026-09-17._
_Plugin name: `moyu_ai_provider` (see `manifest.yaml`)._

This document describes what information the **Moyu AI Dify model provider
plugin** ("the plugin") processes when a Dify user installs and uses it.
It is intended to satisfy the baseline privacy disclosure required by the
Dify Marketplace. It does **not** replace, and is explicitly subordinate to,
the privacy policies and terms of service of the selected upstream service.

中文版：本文件同时作为 Dify Marketplace 的隐私声明使用；所有向国内站或
海外站上游服务发送的数据，均受用户所选站点自身的服务条款与隐私政策约束。

---

## 1. What the plugin collects

The plugin collects **the minimum information needed to call the selected API
on the user's behalf**. Specifically, from the user it reads:

- **API Key** — entered by the user into the Dify provider configuration page.
  This field is declared as `secret-input` in `provider/moyu.yaml`. Dify stores
  it encrypted; the plugin never writes it to disk or intentionally logs it.
- **API Key Site** — the user selects China or overseas according to where the
  key was issued. The plugin maps this selection to a fixed API Base URL
  internally; the raw URL is not shown or editable in the credential UI.

The plugin does not independently request a user's name, email address or
phone number, and it does not add its own product analytics or telemetry.
Depending on the calling Dify application, it may receive and forward an
optional end-user identifier. Network infrastructure operated by Dify or the
selected upstream service may also process ordinary connection metadata under
its own privacy policy.

The plugin does not access the contents of the user's other Dify apps or
datasets beyond the specific model request being executed.

---

## 2. What the plugin sends upstream

When a Dify app invokes a model provided by this plugin, the plugin sends data
over HTTPS to exactly one fixed API Base URL, according to the site selected
by the user:

- China site: `https://www.moyu.cn/v1`
- Overseas site: `https://www.konjac.ai/v1`

The request may include:

- the configured API Key (as an `Authorization: Bearer …` header),
- the model identifier (e.g. `gpt-5.5`, `claude-opus-4-6`),
- the prompt messages, tool definitions, and generation parameters supplied by
  the calling Dify app,
- text submitted for embedding and, where supported by the selected model,
  images, files, videos, or their URLs,
- optional `stop` sequences, `stream` flag, and end-user id if the app passes
  one.

The plugin does not add any additional user-content payload of its own. The
response from the selected upstream service is forwarded back to Dify
unchanged, beyond Dify's own OAI-compatible normalisation.

**All content submitted to a model through this plugin is therefore processed
by the selected China or overseas service.** Users are responsible for making
sure they are allowed to send that content off-platform.

---

## 3. What the plugin stores locally

The plugin maintains no database, persistent cache, or local log file of its
own and does not intentionally write API Keys or prompt bodies to its own
logs. Credential storage and platform/runtime logging are controlled by Dify
and the workspace administrator's deployment configuration.

---

## 4. Upstream services

This plugin is published with authorization to use the **Moyu AI / 魔芋AI**
name for this integration. The selected upstream service processes model
requests under its own terms and privacy policy:

- China service homepage: <https://www.moyu.cn/>
- Overseas service homepage: <https://www.konjac.ai/>
- Consult the selected service's terms of service and privacy policy for
  authoritative information about data retention, geographic location,
  sub-processors, and related matters.

The individual plugin publisher maintains the integration code but does not
control the upstream services' data-retention or processing practices.

---

## 5. Children

The plugin does not knowingly process data from children. The API Key must be
obtained by an account holder who is permitted to accept the selected
service's terms.

---

## 6. Security

- The API Key and model requests are transmitted only over HTTPS.
- The API Key is stored encrypted by Dify, not by the plugin.
- Local `.env` files used by plugin developers for remote-debug runs are
  explicitly excluded from the shipped `.difypkg` via `.difyignore`.
- The repository's preflight script (`scripts/preflight_check.py`) checks that
  no credential is hardcoded in runtime source files.

---

## 7. Your rights

Because the plugin itself does not persist personal data, data-subject
requests concerning upstream processing must be addressed directly to the
selected service through <https://www.moyu.cn/> or
<https://www.konjac.ai/>.

If you are a Dify workspace administrator and want to stop sharing prompt or
embedding content with the selected service, remove the provider configuration
from the Dify UI and uninstall the plugin.

---

## 8. Publisher and contact

- Publisher and maintainer: `fdq-shrimp` (individual publisher).
- Support email: [fangdaq10@163.com](mailto:fangdaq10@163.com).
- Source and issue tracker:
  <https://github.com/FDQ-shrimp/moyu_ai_provider>.
- The publisher is authorized to use the **Moyu AI / 魔芋AI** name for this
  integration.
- For questions about installation, packaging, or the plugin's model catalogue,
  contact the publisher or file a GitHub issue.
- For questions about upstream data handling, contact the operator of the
  selected China or overseas service.

---

## 9. Changes

Material changes to this privacy statement will be reflected in the plugin
version (`manifest.yaml > version`) and the revision date at the top of this
file.
