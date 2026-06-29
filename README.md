# Moyu AI — Dify Model Provider Plugin

> Simplified Chinese README available at [`readme/README_zh_Hans.md`](readme/README_zh_Hans.md).

A Dify **model provider plugin** that lets any Dify workspace call the
[Moyu AI](https://www.moyu.info/) hosted model catalogue through a single
OpenAI-compatible endpoint. Users only need to enter their own Moyu AI
API Key — everything else (model list, request shape, streaming, tool calls)
is handled by the plugin.

---

## 1. Features

- Registers **Moyu AI** as a first-class model provider in any Dify workspace.
- Ships **100+ predefined, verified model YAMLs** across three model types:
  - **Text / LLM**: GPT / Claude / Gemini / Qwen / Kimi / GLM / Grok / DeepSeek /
    Doubao and more
  - **Vision / Multimodal** (accept image input): GPT-4o / Claude (all series) /
    Gemini (all series) / Qwen-VL & Qwen flash/plus/max / Doubao Seed series /
    Grok-4 / Kimi / MiniMax / Jimeng i2i / Wan i2v / MiniMax Hailuo Image and
    more — marked with Dify's `vision` feature so the image upload button
    appears in LLM nodes
  - **Text-embedding** (RAG vectors): `text-embedding-v4`, `text-embedding-v2`,
    `gemini-embedding-2-preview`, `gemini-embedding-001`
  - **Rerank** (RAG re-ranking): `qwen3-rerank`
- Uses Dify's official `OAICompatLargeLanguageModel`, `OAICompatEmbeddingModel`
  and `OAICompatRerankModel` base classes, so streaming, tool calls, batching,
  token usage reporting and error normalisation work out of the box.
- Single-field credential UI: the user only fills in `api_key`.
- Helper scripts for **syncing the model list** from Moyu AI and for
  **probing availability** across all models.
- **Preflight check script** that validates the whole package before release.
- Unit-test suite (`tests/`) covering credential patching and config integrity.

---

## 2. Supported model types

The plugin now registers three native Dify model types, each backed by the
matching Moyu AI OpenAI-compatible endpoint:

| Model type | Endpoint | Examples | Dify feature flag |
|------------|----------|----------|-------------------|
| `llm` (text) | `POST /v1/chat/completions` | GPT, Claude, Gemini, Qwen, DeepSeek, Kimi, GLM, Grok, Doubao… | `agent-thought` |
| `llm` (vision / multimodal, image input) | `POST /v1/chat/completions` | GPT-4o, Claude (all), Gemini (all), Qwen-VL & Qwen flash/plus/max, Doubao Seed (1.6/1.8/2.0), Grok-4, Kimi k2.5/k2.6, MiniMax M2.5/M2.7, Jimeng i2i/i2v, Wan i2v, MiniMax Hailuo Image… | `vision` + `agent-thought` |
| `llm` (image / video generation) | `POST /v1/chat/completions` | Jimeng t2i/t2v, Wan t2v/i2v, Veo 3 (where exposed via chat) | `agent-thought` / `vision` |
| `text-embedding` | `POST /v1/embeddings` | `text-embedding-v4` (1024), `text-embedding-v2` (1536), `gemini-embedding-2-preview` (3072), `gemini-embedding-001` | — |
| `rerank` | `POST /v1/rerank` | `qwen3-rerank` | — |

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

1. Obtain `test_01.difypkg` (built from this repository — see §5).
2. In your Dify workspace, go to **Plugins** → **Install plugin** →
   **Local file**.
3. Upload `test_01.difypkg`.
4. After installation, open **Settings → Model Providers**.
5. Find **Moyu AI** in the list and click **Set up**.

### Option B — install from the Dify Marketplace

Once the plugin has been submitted and approved, end users can install it
directly from the Marketplace. The configuration flow is identical to
Option A.

---

## 4. Configure your API Key

After the provider card appears in Dify:

1. Click **Set up** on the Moyu AI provider card.
2. In the credential form, paste your own **Moyu AI API Key**.
   - You can create one in the Moyu AI console at <https://www.moyu.info/>.
   - The key is stored encrypted by Dify; this plugin never writes it to disk.
3. Click **Save**.
4. Go to **Model list** and enable the models you want to expose to your
   workspace.

> **Important.** End users never need to edit `.env` or touch the plugin
> source code. The `.env` file in this repository is a *developer-only*
> file used for local remote-debug runs (see §6); it is excluded from the
> shipped `.difypkg` by `.difyignore`.

---

## 5. Build a `.difypkg` package

### Prerequisites

- Python 3.12 (matches `manifest.yaml > meta.runner.version`).
- `dify-plugin` CLI (download from the Dify release page and put it on your
  `PATH`, or drop `dify-plugin.exe` next to the project).

### Build command (PowerShell)

```powershell
# From the parent directory of this project folder:
dify-plugin.exe plugin package .\test_01
```

The command produces `test_01.difypkg` next to the project directory.

### Before you package, always run:

```powershell
python .\scripts\preflight_check.py
python -m pytest tests -q
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

1. Copy `.env.example` to `.env`.
2. Fill in the values issued by your Dify workspace's
   **Plugin → Debug** panel:
   ```
   INSTALL_METHOD=remote
   REMOTE_INSTALL_URL=debug.dify.ai:5003
   REMOTE_INSTALL_HOST=debug.dify.ai
   REMOTE_INSTALL_PORT=5003
   REMOTE_INSTALL_KEY=<your-personal-debug-key>
   ```
3. Run:
   ```powershell
   python .\main.py
   ```
4. Your locally-running plugin appears in the Dify workspace as if it were
   installed from a package. Changes in your source files are picked up
   when you restart `main.py`.

> **Never commit your real `.env` file.** `.difyignore` already excludes it
> from the package, and you should add it to your `.gitignore` too.

### Sync the model catalogue from Moyu AI

```powershell
# Generate YAMLs for every model currently exposed by the /v1/models endpoint
python .\scripts\sync_models.py --api-key "<your-moyu-api-key>" --clean

# Generate YAMLs only for models that pass a live 1-token ping (slow)
python .\scripts\sync_models.py --api-key "<your-moyu-api-key>" --clean --probe
```

Useful flags: `--limit N`, `--timeout 30`, `--probe-retries 2`,
`--base-url https://www.moyu.info/v1`.

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
- `provider/moyu.yaml` exposes **exactly** `api_key` as a `secret-input`;
- every `extra.python.provider_source` / `model_sources` path resolves;
- every model YAML has the required keys;
- `.difyignore` excludes `.env` — i.e. the debug key cannot leak into
  the shipped package;
- no source file hardcodes a debug key or an `sk-…` literal;
- English + Chinese README, `privacy.md`, `RELEASE_CHECKLIST.md` are present.

Run it with:

```powershell
python .\scripts\preflight_check.py
```

A machine-readable summary is written to `scripts/preflight_report.json`.

---

## 8. Repository layout

```
test_01/
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
│       ├── rerank.py             # OAI-compatible (Jina-style) rerank adapter
│       └── *.yaml                # Predefined rerank declarations
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
├── privacy.md                    # Privacy statement for Marketplace
└── RELEASE_CHECKLIST.md          # Pre-release sign-off checklist
```

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|--------|--------------|-----|
| `PluginInvokeError: [models] Error: 'endpoint_url'` | You are running an older build in which `_patch_credentials` used `openai_api_base`. | Re-package from the current source; the key mapping has been fixed (`endpoint_url`, `api_key`, `mode`). |
| `401 Invalid key` when running a model | Wrong or expired Moyu AI API Key. | Generate a new key in the Moyu console, paste it into the provider configuration in Dify, save. |
| `503 service_unavailable` on a specific model | Upstream model temporarily unhealthy. | Try another model; use `scripts/probe_all.py` to see current availability. |
| Icon does not show up | Cached UI, or the icon path does not resolve. | Hard-refresh the Dify page; confirm `icon.png` exists at the project root. |
| `dify-plugin.exe package` fails with `plugin icon not found` | `manifest.yaml > icon` points at a missing file. | Ensure `icon.png` exists at the project root and the path in `manifest.yaml` is `icon.png` (no directory prefix). |

---

## 10. Security notes

- The plugin only transmits user prompts and parameters to
  `https://www.moyu.info/v1/chat/completions` using the API Key the user
  configured in Dify.
- The plugin never persists the API Key; Dify manages storage and encryption.
- `.env` is for local debugging only and is excluded from the package via
  `.difyignore`. `scripts/preflight_check.py` enforces that rule.

See [`privacy.md`](privacy.md) for a user-facing privacy statement.

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

---

## 12. License

The license for this plugin has not been finalised yet. Pending the author's
decision, treat this repository as **All rights reserved** by its author
(`manifest.yaml > author: fdq-shrimp`). If you intend to redistribute the
code, please contact the author first.

A dedicated `LICENSE` file will be added in a future revision.

---

## 13. Author / maintainer

- Plugin author field: `fdq-shrimp` (see `manifest.yaml`).
- This plugin is a community integration with the Moyu AI service and is
  not operated by Moyu AI. Users must comply with Moyu AI's own terms of
  service and privacy policy when using the plugin.
