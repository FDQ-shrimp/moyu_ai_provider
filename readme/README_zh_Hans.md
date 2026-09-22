# 魔芋AI — Dify 模型供应商插件

> 中文 README。英文版见仓库根目录 [`README.md`](../README.md)。

> **0.0.8 正式发布版。** 公共精确允许清单中有 41 个
> 双站模型声明 `tool-call`，其中 37 个声明 `stream-tool-call`，详见
> `../docs/VERIFIED_TOOL_CAPABILITIES.md`。不声明任何模型支持 `multi-tool-call`。
> 另有 10 个仅国内模型已取得正向工具证据，但在实现站点专属可见性前，公共 YAML
> 继续不开放两个工具标签。国内、海外 Dify Agent 人工验收已通过；
> 部署环境的实际 SDK 版本未在界面中暴露。

本插件以 **模型供应商插件（Model Provider Plugin）** 的形式接入 Dify，
将[魔芋AI 国内站](https://www.moyu.cn/)与
[Konjac AI 海外站](https://www.konjac.ai/)的精选模型通过 OpenAI 兼容接口
对接到 Dify 工作区。当前注册 48 个双站实测 LLM、10 个明确标注的国内站
专属 LLM，以及 4 个 Embedding。
终端用户填写 API Key，并选择签发该 Key 的站点（国内站或海外站）；插件在
内部自动匹配 API 基础地址。其他工作（模型列表、请求格式、流式输出、工具
调用）都由插件负责。

---

## 1. 功能概览

- 在 Dify 工作区中注册一个名为 **魔芋AI / Moyu AI** 的模型供应商。
- 使用明确的模型白名单，覆盖两种模型类型：
  - **58 个 LLM/兼容聊天模型**：48 个双站共同模型，以及 10 个明确标注
    “仅国内站”的增强模型
  - **LLM 系列**：Claude、DeepSeek、Doubao、Gemini、GLM、GPT、Kimi、
    MiniMax 和 Qwen
  - **4 个文本向量 Embedding**（用于 RAG 检索）：
    - 双站可用：`gemini-embedding-001`、`gemini-embedding-2-preview`
    - 仅国内站：`text-embedding-v2`、`text-embedding-v4`
- 使用 Dify 官方 `OAICompatLargeLanguageModel` 和
  `OAICompatEmbeddingModel` 基类处理协议、批量嵌入、Token 用量统计和错误归一化。
  原生工具能力只对已明确验证的模型声明，不代表目录内所有模型都支持工具。
- 简化的凭据表单：用户填写 `api_key` 并选择国内站或海外站，不显示也不能
  手动编辑 API 基础地址。
- 附带两个运维脚本：
  - 从魔芋AI 拉取模型列表并生成 YAML；
  - 批量探活生成模型可用性报告。
- **发布前自检脚本** `scripts/preflight_check.py` 一次性校验整个插件包。
- `tests/` 单元测试覆盖凭据修补逻辑与配置完整性。

---

## 2. 支持的模型类型

插件现在原生注册两种 Dify 模型类型，分别对接魔芋AI 对应的
OpenAI 兼容端点：

| 模型类型 | 端点 | 典型模型 | Dify 特性标记 |
|----------|------|----------|--------------|
| `llm`（文本） | `POST /v1/chat/completions` | Claude、DeepSeek、Doubao、Gemini、GLM、GPT、Kimi、MiniMax、Qwen | 按模型声明 `agent-thought` |
| `llm`（视觉/多模态） | `POST /v1/chat/completions` | 已验证的 Claude、Gemini、Qwen、Doubao 模型 | 经验证后声明 `vision` |
| `llm`（图片兼容聊天） | `POST /v1/chat/completions` | `gpt-image-2(按次)` 与部分 Gemini image-preview 模型 | `vision` |
| `text-embedding` | `POST /v1/embeddings` | 双站：`gemini-embedding-2-preview`（3072 维）、`gemini-embedding-001`；仅国内：`text-embedding-v4`（1024 维）、`text-embedding-v2`（1536 维） | — |

当前不注册 Rerank；`qwen3-rerank` 在本轮验证中于国内、海外两站均返回
`model_not_found`。

> 上述 `vision` 标记均为**实测得出**：每个多模态系列都通过向
> `/v1/chat/completions` 发送图片内容块进行了实测。明确拒绝图片输入的
> 模型（如旧版 Doubao 1.5、GLM-5.1、qwen3.7-max）已刻意保持纯文本。

> **原生文件/视频理解（Advanced Inputs）**：**Gemini 2.5 系列**
> （`gemini-2.5-pro`、`gemini-2.5-flash`、`gemini-2.5-flash-lite`）已声明
> `document` 与 `video` 特性——经实测，魔芋中转层会把 PDF（`file`）和
> `video_url` 内容块转发给上游 Gemini（HTTP 200）。其他系列暂不声明，
> 因为中转层要么拒绝该内容块、要么崩溃（如 Claude 的 `file` → 500），
> 待与魔芋平台进一步确认后再加。

---

## 3. 在 Dify 中安装

你有两种方式：

### 方式 A：从本地 `.difypkg` 文件安装

1. 获取正式发布包 `moyu_ai_provider-0.0.8.difypkg`。
2. 打开 Dify 工作区 → **插件** → **安装插件** → **本地文件**。
3. 上传该包，确认安装后的实际插件版本为 `0.0.8`。
4. 安装成功后进入 **设置 → 模型供应商**。
5. 在列表中找到 **魔芋AI / Moyu AI**，点击 **设置**。

### 方式 B：从 Dify Marketplace 安装

当插件通过 Marketplace 审核后，用户可直接在 Marketplace 中安装。配置
流程与方式 A 相同。

---

## 4. 配置 API 凭据

在模型供应商卡片出现后：

1. 点击 **魔芋AI** 卡片的 **设置**。
2. 在凭据表单中粘贴你自己的 **魔芋AI API Key**。
   - 国内站 Key 在 <https://www.moyu.cn/> 创建。
   - 海外站 Key 在 <https://www.konjac.ai/> 创建。
   - Key 会由 Dify 加密保存，插件本身不会写入磁盘。
3. 在 **API Key 所属站点** 中选择 **国内站** 或 **海外站**，选择应与创建
   Key 的站点一致；插件会自动使用对应的 API 地址。
4. 点击 **保存**。
5. 进入 **模型列表**，按需启用要暴露给当前工作区的模型。

> **重要说明**：终端用户无需修改 `.env`，也无需动插件源码。开发者本地
> 调试时如使用 `.env`（见 §6），该文件会通过 `.difyignore` 从最终
> `.difypkg` 打包物中排除。

---

## 5. 构建 `.difypkg` 包

### 前置依赖

- Python 3.12（与 `manifest.yaml > meta.runner.version` 一致）。
- `dify-plugin` 官方 CLI：从 Dify Release 页面下载后放到 `PATH` 中，
  或者直接把 `dify-plugin.exe` 放在项目同级目录。

### 打包命令（PowerShell）

```powershell
# 在源码仓库根目录用独立环境执行
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/local_package.py stage '..\moyu-0.0.8-stage'
& '..\dify-plugin.exe' plugin package '..\moyu-0.0.8-stage' -o '..\moyu_ai_provider-0.0.8.difypkg'
```

使用新的暂存目录和输出路径，不覆盖旧版安装包。不要直接打包整个源码目录：
其中有未注册历史 YAML。暂存脚本只选取实际注册的 58 个 LLM、4 个 Embedding，
加上运行文件与对外说明。开发脚本位于源码仓库，不随安装包发布。

### 打包前务必先跑：

```powershell
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py --preflight
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

1. 按 Dify 工作区 **插件 → 调试** 面板显示的说明配置，并且只把该面板签发的
   信息保存在本地、未跟踪的 `.env` 文件中。
2. 启动：
   ```powershell
   python .\main.py
   ```
3. 本地启动的插件会像被安装过一样出现在 Dify 工作区，源码改动重启
   `main.py` 即可生效。

> **不要把远程调试凭据写进文档或源码。** `.env` 与 `.env.*` 已从发布包中排除。

### 同步魔芋AI 的模型列表

```powershell
# 拉取 /v1/models 的全部模型并生成 YAML
python .\scripts\sync_models.py --api-key "<你的魔芋API Key>" --clean

# 仅保留经 1-token 探活成功的模型（较慢）
python .\scripts\sync_models.py --api-key "<你的魔芋API Key>" --clean --probe
```

常用参数：`--limit N`、`--timeout 30`、`--probe-retries 2`、
`--base-url https://www.moyu.cn/v1`。

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
- `provider/moyu.yaml` 将 `api_key` 声明为 `secret-input`，并将
  `endpoint_url` 限制为国内站、海外站两个固定选项；
- `extra.python.provider_source` / `model_sources` 的路径都真实存在；
- 每个模型 YAML 的必填字段齐全；
- `.difyignore` 包含 `.env`，防止调试 key 泄漏到 `.difypkg`；
- 源码中没有硬编码的调试 key 或 `sk-…` 字面值；
- 中英文 README、`PRIVACY.md`、`LICENSE`、`RELEASE_CHECKLIST.md` 都已就位。

运行方式：

```powershell
python .\scripts\preflight_check.py
```

结构化结果会写入 `scripts/preflight_report.json`。

---

## 8. 目录结构

```
moyu_ai_provider/
├── manifest.yaml                 # Dify 读取的插件清单
├── main.py                       # 插件运行时入口
├── icon.png                      # 供应商图标
├── provider/
│   ├── moyu.yaml                 # 供应商 UI + 凭据 schema
│   └── moyu.py                   # 供应商级别凭据校验
├── models/
│   ├── llm/
│   │   ├── llm.py                # OAI 兼容 LLM 适配器
│   │   └── *.yaml                # 预置 LLM 声明
│   ├── text_embedding/
│   │   ├── text_embedding.py     # OAI 兼容 Embedding 适配器
│   │   └── *.yaml                # 预置 Embedding 声明
│   └── rerank/
│       ├── rerank.py             # 保留但当前未注册的旧适配器
│       └── *.yaml                # 仅作历史参考的旧声明
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
├── PRIVACY.md                    # Marketplace 隐私说明
├── LICENSE                       # MIT License
└── RELEASE_CHECKLIST.md          # 发布前清单
```

---

## 9. 常见问题与故障排查

| 现象 | 可能原因 | 解决方式 |
|------|----------|----------|
| `PluginInvokeError: [models] Error: 'endpoint_url'` | 跑的是老版本，`_patch_credentials` 还在用 `openai_api_base`。 | 基于当前源码重新打包，键名已修正为 `endpoint_url`、`api_key`、`mode`。 |
| `401 Invalid key` | Key 错误、失效，或被发往了不同于签发站点的域名。 | 在 **API Key 所属站点** 中选择与 Key 匹配的国内站或海外站，再重新保存凭据。 |
| 某模型返回 `503 service_unavailable` | 该模型上游短时不可用。 | 换其他模型；使用 `scripts/probe_all.py` 查看实时可用性。 |
| 图标不显示 | Dify 页面缓存，或图标路径错误。 | 强制刷新页面；确认 `icon.png` 存在于项目根目录。 |
| 打包报错 `plugin icon not found` | `manifest.yaml` 的 `icon` 路径不对。 | 确认 `icon.png` 在项目根目录，且 `manifest.yaml` 中写的是 `icon.png`（不带子目录前缀）。 |

---

## 10. 安全说明

- 插件仅将用户输入与参数发送到 **API Key 所属站点** 对应的国内或海外
  魔芋AI接口，并使用用户在 Dify 中配置的 API Key；凭据界面不开放地址编辑。
- 插件本身不会持久化 API Key，Key 的加密存储由 Dify 负责。
- `.env` 仅用于本地调试，已经被 `.difyignore` 从打包中排除；
  `scripts/preflight_check.py` 会强制校验这一点。

面向用户的隐私声明见 [`../PRIVACY.md`](../PRIVACY.md)。

---

## 11. 版本

版本号以 `manifest.yaml > version` 为准，每次发布前都要手动 bump。

- `0.0.1` — 初始发布候选：80 个 LLM 模型、流式输出、工具调用、
  preflight + 测试套件。
- `0.0.2` — 模型目录更新：140+ 个模型，新增视觉/多模态、图像生成、
  视频生成类模型；为接受图片输入的模型自动添加 `vision` 特性标记。
- `0.0.3` / `0.0.4` — 目录裁剪为实测可用模型；修复清单编码问题
  （无 BOM 的 UTF-8、修正中文元数据乱码）。
- `0.0.5` — 原生能力升级：
  - **VISION 回填** —— 基于图片输入实测，为 27 个多模态模型补充 `vision`
    特性（Doubao Seed 系列、Grok-4、Kimi k2.5/k2.6、MiniMax M2.5/M2.7、
    Qwen flash/plus/max 与 3.5/3.6 等）。
  - **新增文本向量 Embedding 模型类型**（`text-embedding-v4/v2`、
    `gemini-embedding-2-preview/001`），基于 `OAICompatEmbeddingModel`。
  - **新增重排序 Rerank 模型类型**（`qwen3-rerank`），基于
    `OAICompatRerankModel`，并针对魔芋 `/v1/rerank` 的 `top_n` 约束做了兜底。
  - **Advanced Inputs** —— 经实测 PDF（`file`）与 `video_url` 可透传，
    为 Gemini 2.5 系列声明 `document` + `video` 特性。
- `0.0.6` — 国内、海外双站版本：
  - 新增 **API Key 所属站点**选择，固定映射 `https://www.moyu.cn/v1`
    与 `https://www.konjac.ai/v1`；
  - 注册模型白名单更新为 48 个双站 LLM、10 个仅国内 LLM、
    2 个双站 Embedding 和 2 个仅国内 Embedding；
  - 所有国内专属模型均增加中英文“仅国内站”标识；
  - 因 `qwen3-rerank` 在双站实测均返回 `model_not_found`，暂时关闭 Rerank。
- `0.0.7` — 本地 Function Calling 现代工具协议修复及首批精确能力声明，未发布市场。
- `0.0.8` — 完成正式注册模型能力复核：41 个双站模型声明 `tool-call`、37 个声明
  `stream-tool-call`、0 个声明 `multi-tool-call`；10 个仅国内正向结果继续只记台账。

---

## 12. 许可

本项目采用 [MIT License](../LICENSE) 开源许可。

Copyright (c) 2026 fdq-shrimp。

---

## 13. 发布者、授权与支持

- 发布者及维护者：`fdq-shrimp`（个人发布者）。
- 技术支持：[fangdaq10@163.com](mailto:fangdaq10@163.com)。
- 源码与问题反馈：<https://github.com/FDQ-shrimp/moyu_ai_provider>。
- 本插件已获授权使用“**魔芋AI / Moyu AI**”名称发布此项集成。国内 API
  服务地址为 <https://www.moyu.cn/>，海外 API 服务地址为
  <https://www.konjac.ai/>；使用相应服务时仍须遵守该站点自身的服务条款
  和隐私政策。
