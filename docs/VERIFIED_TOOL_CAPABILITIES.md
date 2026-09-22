# Function Calling 能力台账与重新生成规则

本文件描述 0.0.8 发布版采用的最终能力判定。机器可读的精确模型、站点、模式、
请求编号、报告路径和 SHA256 位于 `VERIFIED_TOOL_CAPABILITIES.yaml`。

## 最终范围

- 正式注册 LLM：58（双站 48、仅国内 10）。
- 公共 YAML 声明 `tool-call`：41。
- 公共 YAML 声明 `stream-tool-call`：37。
- 公共 YAML 声明 `multi-tool-call`：0。
- 仅国内模型：10 个已验证非流式与流式单工具协议，但公共 YAML 暂不开放。
- 双站暂不开放 `tool-call`：7。

能力准入以完整工具协议闭环为主：结构化 `tool_calls`、SDK 正确解析、有效函数与参数、
本地工具执行、相同 `tool_call_id`、`role: tool` 结果回传，以及第二轮正常模型响应。
最终文本是否严格等于 `5` 只作为指令遵循备注，不再单独否定协议能力；原始回答和思考
内容仍不写入台账。

## 只允许 `tool-call` 的双站模型

以下 4 个模型已通过双站非流式协议，但没有可批准的双站流式证据：

- `MiniMax-M3`：流式未测试。
- `claude-sonnet-4-5-20250929`：流式未测试。
- `gemini-3-pro-image-preview`：国内流式第一轮 `ReadTimeout`。
- `kimi-k2.7-code`：国内流式存在未解决的 SDK 映射歧义。

## 双站暂不开放任何工具标签

- `claude-opus-5`：海外非流式 HTTP 500，闭环未完成。
- `gemini-2.5-flash-image-preview`：两站均未产生结构化 `tool_calls`。
- `gemini-2.5-pro`：国内两次独立 `ReadTimeout`，海外未运行。
- `gemini-3.1-flash-image-preview`：国内未产生结构化 `tool_calls`。
- `gpt-6-astra`：两站均为 HTTP 400。
- `gpt-image-2(按次)`：两站均为 HTTP 400。
- `qwen3.8-max`：国内非流式异常终止。

## 仅国内能力

以下模型在国内站的非流式、流式单工具闭环均通过，但当前 Provider 对两个站点共用静态
模型 YAML，无法在海外凭据下隐藏工具标签，因此 0.0.8 不向其公共 YAML 写入工具能力：

- `DeepSeek-R1-0528`
- `DeepSeek-V3-0324`
- `GLM-5`
- `doubao-seed-2-0-code-preview-260215`
- `doubao-seed-2-0-lite-260215`
- `doubao-seed-2-0-mini-260215`
- `doubao-seed-2-0-pro-260215`
- `qwen-plus`
- `qwen3-max`
- `qwen3-vl-plus`

## 必须保留的历史证据

- Qwen 原报告第 6 次请求仍为未证实；后续恢复请求是独立证据，不追溯改写。
- GLM Batch 1 第 40 次请求仍为超时；海外流式能力来自单独受控重测。
- `gemini-2.5-pro` 两次国内 `ReadTimeout` 均保留，不进行第三次尝试。
- `gpt-5.5` 国内流式第二轮通过，但约 57,547 ms 才取得响应头，继续作为延迟观察项。
- 严格文本未精确等于 `5` 的结果保留原记录，但完整协议通过时不再据此否定能力。

## 同步与重新生成保护

`scripts/sync_models.py` 使用精确模型 ID 合并本台账批准的公共标签，不按 Claude、Qwen、
GPT 等系列名称推断。仅国内模型不在公共标签集合中。任何重新生成仍必须：

1. 在独立暂存目录执行，不扩大 `provider/moyu.yaml` 的 58 个 LLM 注册范围。
2. 不执行未经人工批准的 `--clean`。
3. 保留每个模型的非工具字段，只合并精确允许的 `tool-call` / `stream-tool-call`。
4. 运行允许清单测试，确认公共数量严格为 41 / 37 / 0。
5. 确认 10 个仅国内模型公共 YAML 无工具标签，全部 122 个 LLM YAML 无 `multi-tool-call`。

离线 SDK 合约测试证明插件请求和解析链路。2026-09-23 又在 Dify 测试工作区完成
国内、海外 Function Calling 工具闭环及普通聊天回归；部署环境实际 SDK 版本未暴露。
