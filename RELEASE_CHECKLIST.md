# Release Checklist — Moyu AI Dify Model Provider Plugin

Use this checklist before every `.difypkg` build that will be published to
the Dify Marketplace or distributed to end users. Every item must be
ticked off in order.

---

## 0. Pre-flight principle

> The shipped plugin must work for a user who only installs the
> `.difypkg`, opens Dify, pastes their own API Key, and hits Save.
> **No `.env`, no source edits, no debug key.**

---

## 1. Version & metadata

- [ ] `manifest.yaml > version` bumped according to semver (patch / minor / major).
- [ ] `manifest.yaml > meta.version` matches `manifest.yaml > version`.
- [ ] `manifest.yaml > author` is the real publisher handle.
- [ ] `manifest.yaml > privacy`, `repo`, and `contact` point to the current
      privacy document, public source repository, and support address.
- [ ] `manifest.yaml > label` (en_US + zh_Hans) and
      `manifest.yaml > description` (en_US + zh_Hans) are accurate.
- [ ] `manifest.yaml > type` is `plugin`.
- [ ] `manifest.yaml > meta.runner.language` is `python` and
      `meta.runner.version` matches your development environment
      (currently `3.12`).

---

## 2. Icon

- [ ] `icon.png` exists at the project root.
- [ ] The file is a legitimate PNG (open it locally to verify).
- [ ] `manifest.yaml > icon` is `icon.png` (no directory prefix).
- [ ] `provider/moyu.yaml > icon_small[en_US,zh_Hans]` is `icon.png`.
- [ ] `provider/moyu.yaml > icon_large[en_US,zh_Hans]` is `icon.png`.

---

## 3. Provider configuration

- [ ] `provider/moyu.yaml > provider` is `moyu`.
- [ ] `supported_model_types` contains `llm` and only the types actually
      implemented.
- [ ] `configurate_methods` contains `predefined-model`.
- [ ] `provider_credential_schema.credential_form_schemas` contains
      `api_key` (`secret-input`, required) and the fixed `endpoint_url` site
      selector (China / overseas) only.
- [ ] No `.env` variables are ever surfaced to the end-user UI.
- [ ] `extra.python.provider_source` and every entry in
      `extra.python.model_sources` point at real `.py` files.
- [ ] The explicit LLM and text-embedding allowlist entries each resolve to
      one YAML file; rerank is not registered while no verified model exists.
- [ ] The fixed site selector maps only to `https://www.moyu.cn/v1` and
      `https://www.konjac.ai/v1`.

---

## 4. Models catalogue

- [ ] Every model YAML under `models/` is valid YAML and declares `model`,
      `label`, the correct `model_type`, and `model_properties`.
- [ ] Every LLM YAML declares `model_properties.mode: chat` and a sensible
      `model_properties.context_size`.
- [ ] Model IDs exactly match the IDs returned by
      `https://www.moyu.cn/v1/models` (or the selected overseas endpoint).
- [ ] Model YAMLs that are known to be permanently unavailable upstream
      have been removed (run `scripts/probe_all.py`; fold its
      `scripts/probe_report.json` back into a deliberate curation pass).

---

## 5. API Key path

- [ ] A fresh install **without a `.env` file** exposes a working
      credential form in the Dify UI.
- [ ] Pasting a valid Moyu AI API Key and clicking Save passes
      validation (because `MoyuProvider.validate_provider_credentials`
      only requires a non-empty string, and `MoyuLargeLanguageModel._invoke`
      succeeds with a real model).
- [ ] The code path never reads `MOYU_API_KEY` or any `.env` variable to
      obtain the credential at runtime (confirmed by the unit tests in
      `tests/test_provider_validation.py`).

---

## 6. Local-debug variables

- [ ] `.env` is **not** present in the root of the `.difypkg` after you
      build it. (Unzip the package and verify.)
- [ ] `.difyignore` lists `.env`, `scripts/`, `tests/`, and
      `*.difypkg`.
- [ ] No file under `main.py`, `provider/`, or `models/` contains a
      hardcoded `REMOTE_INSTALL_KEY` or an `sk-…` literal. The preflight
      script verifies this automatically.
- [ ] `.env.example` uses placeholders, is excluded from the package, and
      contains no real debug key.

---

## 7. Documentation

- [ ] `README.md` (English) is complete and matches the current behaviour.
- [ ] `readme/README_zh_Hans.md` (Chinese) is complete.
- [ ] `PRIVACY.md` exists and reflects the China/overseas data-flow.
- [ ] `LICENSE` exists and contains the approved MIT License text.
- [ ] The publisher, public repository, and support email are accurate.
- [ ] This `RELEASE_CHECKLIST.md` has been reviewed for this release.
- [ ] No broken links in any README.

---

## 8. Automated checks (must pass)

- [ ] `python scripts/preflight_check.py` exits with code `0`.
- [ ] `python -m pytest tests -q` exits with code `0`.
- [ ] `scripts/preflight_report.json` shows **zero `failed` entries**.

---

## 9. Package build

- [ ] Activate the project virtualenv.
- [ ] Run:
      ```powershell
      dify-plugin.exe plugin package . -o .\moyu_ai_provider-0.0.6.difypkg
      ```
- [ ] `moyu_ai_provider-0.0.6.difypkg` is produced in the repository root.
- [ ] Inspect the archive with a ZIP tool and confirm `.env` is absent.

---

## 10. Clean-workspace install verification

Perform this on a Dify workspace that has **no prior installation** of
this plugin.

1. [ ] **Install plugin → Local file → upload
       `moyu_ai_provider-0.0.6.difypkg`.**
2. [ ] In **Settings → Model providers**, confirm that `Moyu AI` appears
       with the correct icon and description in both English and 简体中文.
3. [ ] Click **Set up**, paste a real Moyu AI API Key, click Save — the
       save succeeds and no error toast appears.
4. [ ] Enable at least one registered model (e.g. `gpt-5.5`).
5. [ ] Create a simple Dify **Chatflow** or **LLM node** using that
       model. Send a test prompt ("ping"); confirm the response streams
       back and the run status is `SUCCESS`.
6. [ ] Disable the model, re-enable it: no errors.
7. [ ] Delete the provider configuration, re-configure with the same
       API Key: save succeeds.

### Upgrade compatibility

1. [ ] In a separate workspace, install the published `0.0.5` package and
       save an existing domestic credential.
2. [ ] Upgrade the plugin to `0.0.6` without deleting that credential.
3. [ ] Confirm the credential still works when the newly optional site field
       is absent; the adapter must fall back to the domestic API.
4. [ ] Edit and save the credential, select each site with a matching test
       account, and confirm the fixed site selector persists correctly.

---

## 11. Marketplace submission (when applicable)

- [ ] Release notes written (link to the bump in `manifest.yaml > version`).
- [ ] Screenshots of the provider card and model list prepared.
- [ ] Author contact verified.
- [ ] Privacy statement (`PRIVACY.md`) reviewed and, if needed, updated.
- [ ] Final upload to the Dify Marketplace.

---

_When every box above is ticked, the release is ready to publish._
