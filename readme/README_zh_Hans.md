# 魔芋AI — Dify 模型供应商插件

> 中文 README。英文版见仓库根目录 [`README.md`](../README.md)。

本插件以 **模型供应商插件（Model Provider Plugin）** 的形式接入 Dify，
将 [魔芋AI](https://www.moyu.info/) 平台上聚合的大语言模型通过一个
OpenAI 兼容的接口对接到 Dify 工作区。终端用户只需要填一次 API Key，
其他工作（模型列表、请求格式、流式输出、工具调用）都由插件负责。

---

## 1. 功能概览

- 在 Dify 工作区中注册一个名为 **魔芋AI / Moyu AI** 的模型供应商。
- 预置 100+ 个 LLM 模型 YAML 定义，覆盖 GPT、Claude、Gemini、Qwen、Kimi、
  GLM、Grok、Doubao、Moonshot、Jimeng、Kling、Minimax、Veo、Sora、Flux
  等系列（完整列表见 `models/llm/*.yaml`）。
- 使用 Dify 官方 `OAICompatLargeLanguageModel` 基类，天然支持流式输出、
  工具调用、Token 用量统计、错误归一化。
- 凭据表单只有一项：用户填 `api_key`，其余全部由插件内部处理。
- 附带两个运维脚本：
  - 从魔芋AI 拉取模型列表并生成 YAML；
  - 批量探活生成模型可用性报告。
- **发布前自检脚本** `scripts/preflight_check.py` 一次性校验整个插件包。
- `tests/` 单元测试覆盖凭据修补逻辑与配置完整性。

---

## 2. 支持的模型类型

| 模型类型 | 状态 |
|----------|------|
| `llm`（对话补全，含流式、工具调用） | 已支持 |
| `text-embedding` | 暂未支持，后续规划中 |
| `rerank` | 暂无计划 |
| `speech2text` / `tts` | 暂无计划 |

当前所有模型的调用都走
`POST https://www.moyu.info/v1/chat/completions`。

---

## 3. 在 Dify 中安装

你有两种方式：

### 方式 A：从本地 `.difypkg` 文件安装

1. 获取构建好的 `test_01.difypkg`（构建方式见 §5）。
2. 打开 Dify 工作区 → **插件** → **安装插件** → **本地文件**。
3. 上传 `test_01.difypkg`。
4. 安装成功后进入 **设置 → 模型供应商**。
5. 在列表中找到 **魔芋AI / Moyu AI**，点击 **设置**。

### 方式 B：从 Dify Marketplace 安装

当插件通过 Marketplace 审核后，用户可直接在 Marketplace 中安装。配置
流程与方式 A 相同。

---

## 4. 配置 API Key

在模型供应商卡片出现后：

1. 点击 **魔芋AI** 卡片的 **设置**。
2. 在凭据表单中粘贴你自己的 **魔芋AI API Key**。
   - 可在魔芋AI 控制台 <https://www.moyu.info/> 创建。
   - Key 会由 Dify 加密保存，插件本身不会写入磁盘。
3. 点击 **保存**。
4. 进入 **模型列表**，按需启用要暴露给当前工作区的模型。

> **重要说明**：终端用户无需修改 `.env`，也无需动插件源码。仓库中的
> `.env` 是面向贡献者的本地调试文件（见 §6），已通过 `.difyignore`
> 从最终 `.difypkg` 打包物中排除。

---

## 5. 构建 `.difypkg` 包

### 前置依赖

- Python 3.12（与 `manifest.yaml > meta.runner.version` 一致）。
- `dify-plugin` 官方 CLI：从 Dify Release 页面下载后放到 `PATH` 中，
  或者直接把 `dify-plugin.exe` 放在项目同级目录。

### 打包命令（PowerShell）

```powershell
# 在项目所在目录的上一级执行
dify-plugin.exe plugin package .\test_01
```

命令会在项目同级生成 `test_01.difypkg`。

### 打包前务必先跑：

```powershell
python .\scripts\preflight_check.py
python -m pytest tests -q
```

两者都应退出码为 `0`。详情见 §7。

---

## 6. 本地开发与远程调试

本节面向贡献者，终端用户不需要阅读。

### 初始化本地环境

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest pyyaml
```

### 配置远程调试

1. 把 `.env.example` 复制为 `.env`。
2. 把 Dify 工作区 **插件 → 调试** 面板给出的值填进去：
   ```
   INSTALL_METHOD=remote
   REMOTE_INSTALL_URL=debug.dify.ai:5003
   REMOTE_INSTALL_HOST=debug.dify.ai
   REMOTE_INSTALL_PORT=5003
   REMOTE_INSTALL_KEY=<你自己的调试 key>
   ```
3. 启动：
   ```powershell
   python .\main.py
   ```
4. 本地启动的插件会像被安装过一样出现在 Dify 工作区，源码改动重启
   `main.py` 即可生效。

> **真实的 `.env` 文件请勿提交到任何仓库。** `.difyignore` 已经把它
> 从打包中排除，请再把它加进你的 `.gitignore`。

### 同步魔芋AI 的模型列表

```powershell
# 拉取 /v1/models 的全部模型并生成 YAML
python .\scripts\sync_models.py --api-key "<你的魔芋API Key>" --clean

# 仅保留经 1-token 探活成功的模型（较慢）
python .\scripts\sync_models.py --api-key "<你的魔芋API Key>" --clean --probe
```

常用参数：`--limit N`、`--timeout 30`、`--probe-retries 2`、
`--base-url https://www.moyu.info/v1`。

### 生成可用性报告

```powershell
python .\scripts\probe_all.py --api-key "<你的魔芋API Key>"
```

终端会打印汇总表格，同时写入 `scripts/probe_report.json`。

---

## 7. 发布前自检脚本

`scripts/preflight_check.py` 做一次纯本地审计：

- 关键文件齐全（manifest、provider、模型 YAML、图标等）；
- 所有 YAML 可解析；
- `manifest.yaml` 内的引用（`plugins.models`、`icon`、
  `meta.runner.entrypoint`）都指向真实文件；
- `provider/moyu.yaml` **仅** 暴露 `api_key` 字段，且类型为 `secret-input`；
- `extra.python.provider_source` / `model_sources` 的路径都真实存在；
- 每个模型 YAML 的必填字段齐全；
- `.difyignore` 包含 `.env`，防止调试 key 泄漏到 `.difypkg`；
- 源码中没有硬编码的调试 key 或 `sk-…` 字面值；
- 中英文 README、`privacy.md`、`RELEASE_CHECKLIST.md` 都已就位。

运行方式：

```powershell
python .\scripts\preflight_check.py
```

结构化结果会写入 `scripts/preflight_report.json`。

---

## 8. 目录结构

```
test_01/
├── manifest.yaml                 # Dify 读取的插件清单
├── main.py                       # 插件运行时入口
├── icon.png                      # 供应商图标
├── provider/
│   ├── moyu.yaml                 # 供应商 UI + 凭据 schema
│   └── moyu.py                   # 供应商级别凭据校验
├── models/
│   └── llm/
│       ├── llm.py                # OAI 兼容 LLM 适配器
│       └── *.yaml                # 预置模型声明
├── scripts/
│   ├── sync_models.py            # 拉取魔芋AI /v1/models 并生成 YAML
│   ├── probe_all.py              # 批量探活 + 报告
│   └── preflight_check.py        # 发布前静态自检
├── tests/                        # pytest 单元 / 配置测试
├── requirements.txt              # 运行时与工具依赖
├── .env.example                  # 本地调试 .env 模板
├── .difyignore                   # 打包排除清单
├── README.md                     # 英文 README
├── readme/README_zh_Hans.md      # 中文 README（本文件）
├── privacy.md                    # Marketplace 隐私说明
└── RELEASE_CHECKLIST.md          # 发布前清单
```

---

## 9. 常见问题与故障排查

| 现象 | 可能原因 | 解决方式 |
|------|----------|----------|
| `PluginInvokeError: [models] Error: 'endpoint_url'` | 跑的是老版本，`_patch_credentials` 还在用 `openai_api_base`。 | 基于当前源码重新打包，键名已修正为 `endpoint_url`、`api_key`、`mode`。 |
| `401 Invalid key` | 魔芋AI API Key 错误或已失效。 | 到魔芋AI 控制台重新生成 Key，在 Dify 供应商配置中重新保存。 |
| 某模型返回 `503 service_unavailable` | 该模型上游短时不可用。 | 换其他模型；使用 `scripts/probe_all.py` 查看实时可用性。 |
| 图标不显示 | Dify 页面缓存，或图标路径错误。 | 强制刷新页面；确认 `icon.png` 存在于项目根目录。 |
| 打包报错 `plugin icon not found` | `manifest.yaml` 的 `icon` 路径不对。 | 确认 `icon.png` 在项目根目录，且 `manifest.yaml` 中写的是 `icon.png`（不带子目录前缀）。 |

---

## 10. 安全说明

- 插件仅将用户输入与参数发送到
  `https://www.moyu.info/v1/chat/completions`，使用用户在 Dify 中配置的
  API Key。
- 插件本身不会持久化 API Key，Key 的加密存储由 Dify 负责。
- `.env` 仅用于本地调试，已经被 `.difyignore` 从打包中排除；
  `scripts/preflight_check.py` 会强制校验这一点。

面向用户的隐私声明见 [`../privacy.md`](../privacy.md)。

---

## 11. 版本

版本号以 `manifest.yaml > version` 为准，每次发布前都要手动 bump。

- `0.0.1` — 初始发布候选：100+ LLM 模型、流式输出、工具调用、
  preflight + 测试套件。

---

## 12. 许可

项目 License 暂未确定。在作者（`manifest.yaml > author: fdq-shrimp`）
正式声明之前，请将本仓库视作 **保留所有权利**。如需二次分发，请先
联系作者。后续会补充 `LICENSE` 文件。

---

## 13. 维护者

- 作者字段：`fdq-shrimp`（见 `manifest.yaml`）。
- 本插件为社区性质的魔芋AI 集成，并非魔芋AI 官方运营。
  使用本插件即代表你同意遵循魔芋AI 自身的服务条款与隐私政策。
