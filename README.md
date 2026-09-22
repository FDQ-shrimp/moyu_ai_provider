# Moyu AI — Dify Model Provider Plugin

> Simplified Chinese README available at [`readme/README_zh_Hans.md`](readme/README_zh_Hans.md).

> **0.0.8 release.** The exact
> public allowlist contains 41 shared models with `tool-call`, including 37 with
> `stream-tool-call`; see `docs/VERIFIED_TOOL_CAPABILITIES.md`. No model advertises
> `multi-tool-call`. Ten China-only models have positive tool evidence but keep
> both public flags disabled until site-specific visibility is available. Manual
> Dify Agent acceptance passed on both sites; the deployed SDK version was not exposed.

A Dify **model provider plugin** that lets any Dify workspace call the
[Moyu AI China](https://www.moyu.cn/) and
[Konjac AI overseas](https://www.konjac.ai/) model catalogues through their
OpenAI-compatible endpoints. Users enter their API Key and select the site that
issued it; the matching API Base URL is selected internally. Everything else
(model list, request shape, streaming, tool calls) is handled by the plugin.

---

## 1. Features

- Registers **Moyu AI** as a first-class model provider in any Dify workspace.
- Exposes an explicit, verified allowlist across two model types:
  - **58 LLM/chat models**: 48 verified on both sites plus 10 clearly labeled
    China-only additions
  - **LLM families**: Claude, DeepSeek, Doubao, Gemini, GLM, GPT, Kimi,
    MiniMax and Qwen
  - **4 text-embedding models** (RAG vectors):
    - Both sites: `gemini-embedding-001`, `gemini-embedding-2-preview`
    - China only: `text-embedding-v2`, `text-embedding-v4`
- Uses Dify's official `OAICompatLargeLanguageModel` and
  `OAICompatEmbeddingModel` base classes for protocol handling, batching,
  token usage reporting and error normalisation. Native tool capability is
  advertised only for explicitly verified models, not every model in the catalog.
- Simple credential UI: the user enters `api_key` and selects its China or
  overseas site; raw API Base URLs are not shown or editable.
- Helper scripts for **syncing the model list** from Moyu AI and for
  **probing availability** across all models.
- **Preflight check script** that validates the whole package before release.
- Unit-test suite (`tests/`) covering credential patching and config integrity.

---

## 2. Supported model types

The plugin registers two native Dify model types, each backed by the
matching Moyu AI OpenAI-compatible endpoint:

| Model type | Endpoint | Examples | Dify feature flag |
|------------|----------|----------|-------------------|
| `llm` (text) | `POST /v1/chat/completions` | Claude, DeepSeek, Doubao, Gemini, GLM, GPT, Kimi, MiniMax, Qwen | `agent-thought` where declared |
| `llm` (vision / multimodal) | `POST /v1/chat/completions` | Selected Claude, Gemini, Qwen and Doubao models | `vision` where verified |
| `llm` (image-compatible chat) | `POST /v1/chat/completions` | The per-use `gpt-image-2` variant and selected Gemini image-preview models | `vision` |
| `text-embedding` | `POST /v1/embeddings` | Both sites: `gemini-embedding-2-preview` (3072), `gemini-embedding-001`; China only: `text-embedding-v4` (1024), `text-embedding-v2` (1536) | — |

Rerank is intentionally not registered because `qwen3-rerank` returned
`model_not_found` on both sites during the current verification pass.

> The `vision` feature flags above are **evidence-based**: every multimodal
> family was live-probed by sending an image content block to
> `/v1/chat/completions`. Models that explicitly reject image input
> (e.g. legacy Doubao 1.5, GLM-5.1, qwen3.7-max) are intentionally kept
> text-only.

> **Native file / video understanding (Advanced Inputs)**: the **Gemini 2.5
> series** (`gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`)
> declares the `document` and `video` features — the Moyu relay was
> live-probed to forward PDF (`file`) and `video_url` blocks to upstream
> Gemini (HTTP 200). Other families are intentionally left without these
> flags because the relay either rejected the block or crashed
> (e.g. Claude `file` → 500); they may be added after further confirmation
> with the Moyu platform.

---

## 3. Install the plugin in Dify

You have two options:

### Option A — install from a local `.difypkg` file

1. Obtain the official `moyu_ai_provider-0.0.8.difypkg` release package.
2. In your Dify workspace, go to **Plugins** → **Install plugin** →
   **Local file**.
3. Upload it and confirm the installed version is `0.0.8`.
4. After installation, open **Settings → Model Providers**.
5. Find **Moyu AI** in the list and click **Set up**.

### Option B — install from the Dify Marketplace

Once the plugin has been submitted and approved, end users can install it
directly from the Marketplace. The configuration flow is identical to
Option A.

---

## 4. Configure your API credentials

After the provider card appears in Dify:

1. Click **Set up** on the Moyu AI provider card.
2. In the credential form, paste your own **Moyu AI API Key**.
   - China-site keys are issued at <https://www.moyu.cn/>.
   - Overseas-site keys are issued at <https://www.konjac.ai/>.
   - The key is stored encrypted by Dify; this plugin never writes it to disk.
3. Under **API Key Site**, select **China Site** or **Overseas Site** according
   to where the key was created. The plugin selects the matching API address
   automatically.
4. Click **Save**.
5. Go to **Model list** and enable the models you want to expose to your
   workspace.

> **Important.** End users never need to edit `.env` or touch the plugin
> source code. A local `.env` file, when used by a developer for remote-debug
> runs (see §6), is excluded from the shipped `.difypkg` by `.difyignore`.

---

## 5. Build a `.difypkg` package

### Prerequisites

- Python 3.12 (matches `manifest.yaml > meta.runner.version`).
- `dify-plugin` CLI (download from the Dify release page and put it on your
  `PATH`, or drop `dify-plugin.exe` next to the project).

### Build command (PowerShell)

```powershell
# From the source repository root, using the dedicated Python environment:
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/local_package.py stage '..\moyu-0.0.8-stage'
& '..\dify-plugin.exe' plugin package '..\moyu-0.0.8-stage' -o '..\moyu_ai_provider-0.0.8.difypkg'
```

Use a fresh staging directory and a new output path; never overwrite an older package.
Do not package the source directory directly: it contains unregistered historical
model YAMLs. The staging helper selects the 58 LLMs and 4 embeddings explicitly
registered by the provider, plus runtime files and public documentation.
These developer scripts are in the source repository, not the installed package.

### Before you package, always run:

```powershell
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py --preflight
```

Both must exit with code `0`. See §7 for details.

---

## 6. Local development & remote debug

This section is for contributors, not end users.

### Set up a local virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest pyyaml
```

### Enable remote debug against a hosted Dify workspace

1. Follow the values and instructions shown in your Dify workspace's
   **Plugin → Debug** panel, and keep all issued settings only in a local,
   untracked `.env` file.
2. Run:
   ```powershell
   python .\main.py
   ```
3. Your locally-running plugin appears in the Dify workspace as if it were
   installed from a package. Changes in your source files are picked up
   when you restart `main.py`.

> **Never paste remote-debug credentials into documentation or source files.**
> `.env` and `.env.*` are excluded from the release package.

### Sync the model catalogue from Moyu AI

```powershell
# Generate YAMLs for every model currently exposed by the /v1/models endpoint
python .\scripts\sync_models.py --api-key "<your-moyu-api-key>" --clean

# Generate YAMLs only for models that pass a live 1-token ping (slow)
python .\scripts\sync_models.py --api-key "<your-moyu-api-key>" --clean --probe
```

Useful flags: `--limit N`, `--timeout 30`, `--probe-retries 2`,
`--base-url https://www.moyu.cn/v1`.

### Produce a detailed availability report

```powershell
python .\scripts\probe_all.py --api-key "<your-moyu-api-key>"
```

Results are summarised on stdout and written to `scripts/probe_report.json`.

---

## 7. Preflight check

`scripts/preflight_check.py` performs a fully-offline audit:

- every critical file is present (manifest, provider, model YAMLs, icon…);
- every YAML parses;
- `manifest.yaml` references (`plugins.models`, `icon`, `meta.runner.entrypoint`)
  point to real files;
- `provider/moyu.yaml` exposes `api_key` as a `secret-input` and
  `endpoint_url` as a fixed two-option site selector;
- every `extra.python.provider_source` / `model_sources` path resolves;
- every model YAML has the required keys;
- `.difyignore` excludes `.env` — i.e. the debug key cannot leak into
  the shipped package;
- no source file hardcodes a debug key or an `sk-…` literal;
- English + Chinese README, `PRIVACY.md`, `LICENSE`, and
  `RELEASE_CHECKLIST.md` are present.

Run it with:

```powershell
python .\scripts\preflight_check.py
```

A machine-readable summary is written to `scripts/preflight_report.json`.

---

## 8. Repository layout

```
moyu_ai_provider/
├── manifest.yaml                 # Plugin manifest consumed by Dify
├── main.py                       # Plugin runtime entry point
├── icon.png                      # Provider icon (displayed in Dify UI)
├── provider/
│   ├── moyu.yaml                 # Provider UI + credential schema
│   └── moyu.py                   # Provider-level credential validator
├── models/
│   ├── llm/
│   │   ├── llm.py                # OAI-compatible LLM adapter
│   │   └── *.yaml                # Predefined LLM declarations
│   ├── text_embedding/
│   │   ├── text_embedding.py     # OAI-compatible embedding adapter
│   │   └── *.yaml                # Predefined embedding declarations
│   └── rerank/
│       ├── rerank.py             # Legacy adapter retained but not registered
│       └── *.yaml                # Legacy declaration retained for reference
├── scripts/
│   ├── sync_models.py            # Pull Moyu's /v1/models into local YAMLs
│   ├── probe_all.py              # Availability report across all models
│   └── preflight_check.py        # Release-time static audit
├── tests/                        # pytest unit / config tests
├── requirements.txt              # Runtime + tooling dependencies
├── .env.example                  # Template for the local-debug .env file
├── .difyignore                   # Paths excluded from .difypkg
├── README.md                     # English README (this file)
├── readme/README_zh_Hans.md      # Chinese README
├── PRIVACY.md                    # Privacy statement for Marketplace
├── LICENSE                       # MIT License
└── RELEASE_CHECKLIST.md          # Pre-release sign-off checklist
```

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|--------|--------------|-----|
| `PluginInvokeError: [models] Error: 'endpoint_url'` | You are running an older build in which `_patch_credentials` used `openai_api_base`. | Re-package from the current source; the key mapping has been fixed (`endpoint_url`, `api_key`, `mode`). |
| `401 Invalid key` when running a model | The key is invalid, expired, or was sent to a different Moyu site from the one that issued it. | Select the matching **API Key Site** (China or overseas), then save the credential again. |
| `503 service_unavailable` on a specific model | Upstream model temporarily unhealthy. | Try another model; use `scripts/probe_all.py` to see current availability. |
| Icon does not show up | Cached UI, or the icon path does not resolve. | Hard-refresh the Dify page; confirm `icon.png` exists at the project root. |
| `dify-plugin.exe package` fails with `plugin icon not found` | `manifest.yaml > icon` points at a missing file. | Ensure `icon.png` exists at the project root and the path in `manifest.yaml` is `icon.png` (no directory prefix). |

---

## 10. Security notes

- The plugin only transmits user prompts and parameters to the China or overseas
  Moyu AI API endpoint selected through **API Key Site**, using the API Key
  configured in Dify. The raw endpoint is not editable in the credential UI.
- The plugin never persists the API Key; Dify manages storage and encryption.
- `.env` is for local debugging only and is excluded from the package via
  `.difyignore`. `scripts/preflight_check.py` enforces that rule.

See [`PRIVACY.md`](PRIVACY.md) for a user-facing privacy statement.

---

## 11. Versioning

Version follows `manifest.yaml > version`. Bump it before every release.

- `0.0.1` — initial release candidate: 80 LLM models, streaming,
  tool-calling, preflight + test suite.
- `0.0.2` — model catalogue update: 140+ models including new vision/multimodal,
  image-generation and video-generation models; `vision` feature flag added to
  models that accept image input (GPT-4o, Claude, Gemini, Qwen-VL, Kling,
  Jimeng i2i/i2v, Wan i2v, Minimax Hailuo Image, HappyHorse i2v/r2v, etc.).
- `0.0.3` / `0.0.4` — catalogue pruned to verified-working models; manifest
  encoding fixes (no-BOM UTF-8, corrected Chinese metadata).
- `0.0.5` — native capability upgrade:
  - **VISION backfill** — 27 additional multimodal models relabeled with the
    `vision` feature based on live image-input probing (Doubao Seed series,
    Grok-4, Kimi k2.5/k2.6, MiniMax M2.5/M2.7, Qwen flash/plus/max & 3.5/3.6).
  - **Text-embedding** model type added (`text-embedding-v4/v2`,
    `gemini-embedding-2-preview/001`) via `OAICompatEmbeddingModel`.
  - **Rerank** model type added (`qwen3-rerank`) via `OAICompatRerankModel`,
    with a `top_n` guard for Moyu's `/v1/rerank` contract.
  - **Advanced Inputs** — Gemini 2.5 series declares `document` + `video`
    after live-probing PDF (`file`) and `video_url` passthrough via the relay.
- `0.0.6` — China/overseas dual-site release:
  - added a fixed **API Key Site** selector for `https://www.moyu.cn/v1` and
    `https://www.konjac.ai/v1`;
  - updated the registered allowlist to 48 dual-site LLMs, 10 China-only LLMs,
    2 dual-site embeddings and 2 China-only embeddings;
  - clearly labeled every China-only model in English and Chinese;
  - disabled Rerank because `qwen3-rerank` returned `model_not_found` on both
    sites during verification.
- `0.0.7` — local Function Calling protocol fix and initial exact capability
  declarations, without Marketplace publication.
- `0.0.8` — full registered-catalog capability review: 41 shared models expose
  `tool-call`, 37 expose `stream-tool-call`, none expose `multi-tool-call`; ten
  China-only positive results remain ledger-only because public YAML is shared.

---

## 12. License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 fdq-shrimp.

---

## 13. Publisher, authorization and support

- Publisher and maintainer: `fdq-shrimp` (individual publisher).
- Support: [fangdaq10@163.com](mailto:fangdaq10@163.com).
- Source and issues: <https://github.com/FDQ-shrimp/moyu_ai_provider>.
- This plugin is published with authorization to use the **Moyu AI**
  name for this integration. The China API service is available at
  <https://www.moyu.cn/> and the overseas API service at
  <https://www.konjac.ai/>. Use of either service remains subject to that
  service's own terms and privacy policy.
