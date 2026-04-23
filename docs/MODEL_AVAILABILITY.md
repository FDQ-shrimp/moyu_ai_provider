# 魔芋AI 模型可用性报告

> 生成时间：2026-04-23 05:02 UTC  
> 探活端点：`POST https://www.moyu.info/v1/chat/completions`  
> 探活请求：`{"messages":[{"role":"user","content":"ping"}], "max_tokens":1, "stream":false}`  
> 超时：30s × 最多 4 次重试

## 汇总

- 模型总数：**119**
- 可用（OK）：**76**
- 不可用（FAIL）：**43**

### 不可用原因分布

| 原因码 | 含义 | 数量 |
|--------|------|------|
| `server_error` | 上游服务器内部错误（500） | 16 |
| `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | 12 |
| `http_429` | 上游限流 / 额度不足 / 负载饱和 | 9 |
| `model_not_found` | 上游渠道不存在或已下线 | 5 |
| `timeout` | 超时无响应 | 1 |

## 可直接调用的模型（OK）

| # | 模型 ID | 平均耗时 |
|---|---------|----------|
| 1 | `GLM-5` | 7.0s |
| 2 | `GPT-4.1` | 6.7s |
| 3 | `GPT-4o` | 3.3s |
| 4 | `MiniMax-Hailuo-image-01` | 3.3s |
| 5 | `MiniMax-Hailuo-image-01-live` | 3.8s |
| 6 | `MiniMax-M2.5` | 2.5s |
| 7 | `MiniMax/MiniMax-M2.7` | 3.0s |
| 8 | `claude-haiku-4-5-20251001` | 4.6s |
| 9 | `claude-opus-4-1-20250805` | 3.6s |
| 10 | `claude-opus-4-20250514` | 3.8s |
| 11 | `claude-opus-4-5-20251101` | 7.5s |
| 12 | `claude-opus-4-6` | 24.3s |
| 13 | `claude-opus-4-7` | 5.4s |
| 14 | `claude-sonnet-4-20250514` | 3.5s |
| 15 | `claude-sonnet-4-5-20250929` | 13.5s |
| 16 | `claude-sonnet-4-6` | 5.7s |
| 17 | `deepseek-v3.2` | 2.3s |
| 18 | `doubao-1-5-lite-32k-250115` | 3.6s |
| 19 | `doubao-1-5-pro-32k-250115` | 2.3s |
| 20 | `doubao-seed-1-6-flash-250828` | 9.2s |
| 21 | `doubao-seed-1-6-lite-251015` | 4.2s |
| 22 | `doubao-seed-1-8-251228` | 6.6s |
| 23 | `doubao-seed-2-0-code-preview-260215` | 3.3s |
| 24 | `doubao-seed-2-0-lite-260215` | 5.4s |
| 25 | `doubao-seed-2-0-mini-260215` | 2.1s |
| 26 | `doubao-seed-2-0-pro-260215` | 3.0s |
| 27 | `doubao-seed-code-preview-251028` | 9.6s |
| 28 | `gemini-2.5-flash` | 3.4s |
| 29 | `gemini-2.5-flash-image-preview` | 3.4s |
| 30 | `gemini-2.5-flash-lite` | 2.5s |
| 31 | `gemini-2.5-pro` | 3.8s |
| 32 | `gemini-3-flash-preview` | 2.7s |
| 33 | `gemini-3-pro-image-preview` | 40.9s |
| 34 | `gemini-3-pro-preview` | 3.5s |
| 35 | `gemini-3.1-flash-image-preview` | 12.7s |
| 36 | `gemini-3.1-flash-lite-preview` | 4.2s |
| 37 | `gemini-3.1-pro-preview` | 4.4s |
| 38 | `glm-5.1` | 8.1s |
| 39 | `gpt-4o-2024-08-06` | 2.4s |
| 40 | `gpt-4o-2024-11-20` | 3.2s |
| 41 | `gpt-4o-mini-2024-07-18` | 2.6s |
| 42 | `gpt-5` | 4.8s |
| 43 | `gpt-5.1` | 2.9s |
| 44 | `gpt-5.4` | 4.8s |
| 45 | `grok-4-1-fast-reasoning` | 4.1s |
| 46 | `jimeng_i2i_v30` | 1.9s |
| 47 | `jimeng_i2v_first_tail_v30_1080` | 1.7s |
| 48 | `jimeng_i2v_first_v30` | 1.7s |
| 49 | `jimeng_i2v_recamera_v30` | 1.7s |
| 50 | `jimeng_t2i_v30` | 3.3s |
| 51 | `jimeng_t2i_v31` | 1.7s |
| 52 | `jimeng_t2i_v40` | 2.0s |
| 53 | `jimeng_t2v_v30` | 1.6s |
| 54 | `jimeng_t2v_v30_1080p` | 1.7s |
| 55 | `jimeng_ti2v_v30_pro` | 3.2s |
| 56 | `kimi-k2.6` | 3.2s |
| 57 | `kimi/kimi-k2.5` | 2.2s |
| 58 | `qwen-flash` | 2.5s |
| 59 | `qwen-max` | 1.8s |
| 60 | `qwen-plus` | 1.7s |
| 61 | `qwen3-max` | 2.0s |
| 62 | `qwen3-vl-flash` | 1.6s |
| 63 | `qwen3-vl-plus` | 1.7s |
| 64 | `qwen3.5-35b-a3b` | 3.7s |
| 65 | `qwen3.5-flash` | 6.3s |
| 66 | `qwen3.5-plus` | 12.5s |
| 67 | `qwen3.6-flash` | 3.3s |
| 68 | `qwen3.6-max-preview` | 13.3s |
| 69 | `qwen3.6-plus` | 10.1s |
| 70 | `vanchin/deepseek-v3.2-think` | 3.8s |
| 71 | `veo-3` | 13.9s |
| 72 | `veo-3-fast` | 12.7s |
| 73 | `wan2.5-i2v-preview` | 2.2s |
| 74 | `wan2.5-t2v-preview` | 1.8s |
| 75 | `wan2.6-i2v` | 1.6s |
| 76 | `wan2.6-t2v` | 1.6s |

## 当前不可用的模型（FAIL）

> 注意：这些模型也已写入插件。Dify 界面能看到并启用它们，
> 但在上游恢复之前调用会报错。当魔芋AI 修复对应渠道后，
> 无需重新打包插件即可恢复使用。

| # | 模型 ID | 原因码 | 含义 | 详情节选 |
|---|---------|--------|------|----------|
| 1 | `doubao-embedding-vision-250615` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 2 | `doubao-seed-translation-250915` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 3 | `doubao-seedream-3-0-t2i-250415` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 4 | `doubao-seedream-4-0-250828` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 5 | `doubao-seedream-4-5-251128` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 6 | `doubao-seedream-5-0-260128` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [InvalidParameter] The parameter `model` specified in the request are not valid: the requested model doubao… |
| 7 | `kling-v1-5` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [bad_response_status_code] mode std is not supported for model kling-v1-5 |
| 8 | `kling-v2` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [bad_response_status_code] model is not supported |
| 9 | `kling-v2-new` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [bad_response_status_code] model is not supported |
| 10 | `sora-2` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [prompt_required] prompt is required |
| 11 | `sora-2-openai` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [bad_response_status_code] openai_error |
| 12 | `sora-2-pro-openai` | `bad_request` | 请求参数被拒绝（该模型可能需要非 chat 协议，如图像/视频生成） | [bad_response_status_code] openai_error |
| 13 | `gemini-embedding-001` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | [400] Invalid JSON payload received. Unknown name "content": Cannot find field. (request id: 20260423124856… |
| 14 | `gemini-embedding-2-preview` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | [400] The content field must have at least one part. (request id: 20260423124905580796815sCLE4HC) |
| 15 | `gpt-5.2` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | Could not finish the message because max_tokens or model output limit was reached. Please try again with hi… |
| 16 | `gpt-5.3-codex` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | [shell_api_error] 当前分组上游负载已饱和，请稍后再试 (request id: 2026042312495594704509KfMdfp4L) |
| 17 | `gpt-5.4-mini` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | Could not finish the message because max_tokens or model output limit was reached. Please try again with hi… |
| 18 | `gpt-5.4-nano` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | Could not finish the message because max_tokens or model output limit was reached. Please try again with hi… |
| 19 | `grok-4` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | [shell_api_error] 当前分组上游负载已饱和，请稍后再试 (request id: 20260423125243591561595t5TnAM2r) |
| 20 | `grok-4.1` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | Stream aborted by server or connection error: Status { code: ResourceExhausted, message: "Admission denied … |
| 21 | `grok-4.2` | `http_429` | 上游限流 / 额度不足 / 负载饱和 | Stream aborted by server or connection error: Status { code: ResourceExhausted, message: "Admission denied … |
| 22 | `doubao-lite-32k-character-250228` | `model_not_found` | 上游渠道不存在或已下线 | [InvalidEndpointOrModel.NotFound] The model or endpoint doubao-lite-32k-character-250228 does not exist or … |
| 23 | `doubao-seedream-3-0-t2i-250415i` | `model_not_found` | 上游渠道不存在或已下线 | [InvalidEndpointOrModel.NotFound] The model or endpoint doubao-seedream-3-0-t2i-250415i does not exist or y… |
| 24 | `gemini-2.0-flash` | `model_not_found` | 上游渠道不存在或已下线 | [404] Publisher Model `projects/329711734610/locations/us-east4/publishers/google/models/gemini-2.0-flash` … |
| 25 | `veo-3.1` | `model_not_found` | 上游渠道不存在或已下线 | [404] Publisher Model `projects/powercube-474713/locations/global/publishers/google/models/veo-3.1-generate… |
| 26 | `veo-3.1-fast` | `model_not_found` | 上游渠道不存在或已下线 | [404] Publisher Model `projects/powercube-474713/locations/global/publishers/google/models/veo-3.1-fast-gen… |
| 27 | `FLUX.2-dev` | `server_error` | 上游服务器内部错误（500） | [bad_response_status_code] 模型信息关联关系不存在 |
| 28 | `Z-Image-Turbo` | `server_error` | 上游服务器内部错误（500） | [bad_response_status_code] 模型信息关联关系不存在 |
| 29 | `doubao-seedance-1-0-lite-i2v-250428` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 021776919610445ff7… |
| 30 | `doubao-seedance-1-0-pro-250528` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 021776919613922ff7… |
| 31 | `doubao-seedance-1-0-pro-fast-251015` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 02177691961873095d… |
| 32 | `doubao-seedance-1-5-pro-251215` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 021776919624661ff7… |
| 33 | `doubao-seedance-2-0-260128` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 021776919629209ff7… |
| 34 | `doubao-seedance-2-0-fast-260128` | `server_error` | 上游服务器内部错误（500） | [InternalServiceError] The service encountered an unexpected internal error. Request id: 021776919632769ff7… |
| 35 | `grok-4.1-fast` | `server_error` | 上游服务器内部错误（500） | {"error":{"code":8,"message":"Grok is under heavy usage right now. Please try again later, use a different … |
| 36 | `kling-v1` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 37 | `kling-v1-6` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 38 | `kling-v2-1` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 39 | `kling-v2-1-master` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 40 | `kling-v2-5-turbo` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 41 | `kling-v2-6` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 42 | `kling-v2-master` | `server_error` | 上游服务器内部错误（500） | [channel:param_override_invalid] operation copy failed: source path does not exist: duration (request id: 2… |
| 43 | `siliconflow/deepseek-r1-0528` | `timeout` | 超时无响应 | No response within 30s x 4 retries |

## 给用户的使用建议

1. 在 Dify 中配置魔芋AI API Key 后，先尝试上表「可直接调用」里的模型。
2. 部分 `http_429` 模型是账户当前额度被打满，换一把额度充足的 Key 可能立即恢复。
3. 大量 `bad_request` 的模型（`doubao-seedream-*`、`kling-*`、`sora-*`、`jimeng_*` 等）属于 **图像 / 视频生成类**，魔芋AI 的 `chat/completions` 接口不支持它们。插件保留其定义仅供 Dify 识别型号，若后续魔芋AI 推出对应的多模态接口，我们再在插件层适配。
4. `model_not_found` / `service_unavailable` / `server_error` 多为上游短期问题，过一段时间再试。

## 原始数据

完整 JSON：`scripts/probe_report.json`。
