# Plugin Submission

## Plugin information

- **Author**: fdq-shrimp
- **Plugin name**: moyu_ai_provider
- **Version**: 0.0.6
- **Source repository**: https://github.com/FDQ-shrimp/moyu_ai_provider
- **Contact**: fangdaq10@163.com

## Submission type

- [ ] New plugin
- [x] Version update

## What changed

- Added a fixed API Key Site selector for the China endpoint
  (`https://www.moyu.cn/v1`) and the overseas endpoint
  (`https://www.konjac.ai/v1`).
- Updated the predefined catalog to 58 LLMs and 4 text-embedding models:
  48 LLMs and 2 embeddings verified on both sites, plus 10 LLMs and
  2 embeddings clearly labeled as China-only.
- Disabled rerank registration because `qwen3-rerank` returned
  `model_not_found` on both sites during verification.
- Updated the English and Simplified Chinese documentation, privacy disclosure,
  publisher/contact metadata, and MIT license information.

Compatibility note: the visible model catalog has changed and rerank is no
longer registered. Existing workflows that reference a removed model or rerank
model may need to select a supported replacement.

## Risk level

- [ ] Low risk
- [x] Medium risk
- [ ] High risk

## Required checks

- [x] I have read and followed the [Marketplace submission requirements](https://github.com/langgenius/dify-plugins/blob/main/docs/plugin-submission-requirements.md).
- [x] I have read and comply with the Plugin Developer Agreement.
- [x] I tested this plugin on Dify Community Edition and Dify Cloud, or documented any limitation below.
- [x] The final package contains only files needed at runtime.
- [x] The final package does not contain secrets, local credentials, `.env` files, `.git` directories, virtual environments, caches, logs, or IDE files.
- [x] The final package does not contain executables or bundled binaries, or I explained why they are required below.
- [x] The plugin README includes setup steps, usage instructions, required APIs or credentials, connection requirements, and the source repository link.
- [x] The plugin includes `PRIVACY.md`, and `manifest.yaml` references it.
- [x] All user-facing text is primarily in English, with localized README files following the [i18n guidance](https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/multilingual-readme).

## Security and privacy notes

This model-provider plugin sends user-requested inference content to the
selected third-party service. Depending on the selected model and Dify
workflow, transmitted content may include prompts, conversation messages,
embedding input text, tool definitions, and supported multimodal input. The
API key is sent to the selected service for authentication.

The provider UI exposes only two fixed HTTPS API sites: `www.moyu.cn` and
`www.konjac.ai`, and `manifest.yaml` declares only those two outbound domains;
it does not expose a free-form endpoint field. The plugin does
not execute user-controlled code or commands, run SQL, access the local
filesystem, automate a browser, or proxy arbitrary user-provided URLs. It does
not persist API keys or inference content itself; credential storage is handled
by Dify. Data sent to either API site is governed by that service's terms and
privacy policy. These disclosures are also documented in `PRIVACY.md`.

## Local validation

- `python -m pytest tests -q`: 160 passed.
- `python scripts/preflight_check.py`: 143 passed, 0 warnings, 0 failed.
- Dify SDK manifest/provider parsing: 62 predefined models loaded successfully
  (58 LLMs and 4 text-embedding models).
- Package inspection: 76 entries; 58 LLM YAMLs and 4 text-embedding YAMLs;
  exact uppercase `PRIVACY.md`; no `.env`, credential patterns, caches, tests,
  development scripts, logs, bundled executables, unregistered models, or
  rerank files. SHA256:
  `0B7E2F188108F1A8BB09CF786C4964F4BB12BC7162BA1B4B8A1CDD2CB9545980`.
- Marketplace Toolkit validation: exit code 0, 0 blocking failures, and 0
  environment/check execution failures.
- Dify Cloud: the pre-hardening `0.0.6` package with the same runtime behavior
  was uploaded, installed, and tested successfully with the China/overseas site
  selector. The final package only adds the fixed-domain manifest declaration
  and removes a non-functional credential-length debug log; final installation
  revalidation is pending before Marketplace submission.

## Reviewer notes

- Dify Community Edition was not separately tested for this release; the Dify
  Cloud installation and functional test described above succeeded.
- The catalog was selected from live checks against both API sites. China-only
  entries are explicitly labeled in both supported UI languages.
- Rerank is intentionally disabled in version 0.0.6 because the advertised
  rerank model was unavailable on both sites during verification.
- This is an update to the existing Marketplace plugin
  `fdq-shrimp/moyu_ai_provider`, not a new plugin identity.
