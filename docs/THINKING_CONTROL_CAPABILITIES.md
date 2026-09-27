# Thinking Control：58 个正式 LLM 的交付矩阵

2026-09-28 更新，供 **0.0.9 正式发布准备**使用。以 `provider/moyu.yaml` 的精确模型 ID 为准。既有站点扩展记录保持原样；最后 12 候选受控首关口新增 **13** 次（国内 1、海外 12），脱敏记录见 `scripts/thinking_twelve_live_report.json`。该首关口无新增 verified 型号；原始记录不追溯修改，未用额度不自动延续。官方逐型号依据见 `THINKING_CONTROL_PHASE2_INVENTORY.md` 文末索引。

判定门槛：该精确 ID 在对应站点取得可靠结构化控制对照，才在该站点开放。官方原生协议和 HTTP 200 均不足以单独开放。公共 YAML 声明参数；SDK `get_model_schema` 按凭据站点过滤，生产 `_invoke` 再次拦截未验证站点的控制字段。`implemented-but-hidden` 不等于已经支持用户使用。新开放型号的 live verified 范围仅非流式普通聊天；流式和工具调用仅通过离线 SDK 合约。

缩写：Q＝顶层 `enable_thinking` 布尔；Z＝`thinking.type=enabled/disabled` 对象；E＝兼容接口候选 `reasoning_effort` 枚举；C＝Claude 原生 `thinking`／`budget_tokens` 或 adaptive／effort；B＝官方原生预算或等级；`—`＝公共 UI 不显示、实际请求不注入。候选形态不承诺 Moyu/Konjac 已接受。站点列“双”表示模型既有双站可用性，非思考控制实测。

| 精确模型 ID | 站点 | 状态 | Dify 思考参数 | 上游思考参数／候选协议 | 证据与限制 |
| --- | --- | --- | --- | --- | --- |
| `MiniMax-M3` | 双 | no-reliable-thinking-control-evidence | — | — | MM：有推理特性，控制字段未证 |
| `claude-fable-5` | 双 | no-reliable-thinking-control-evidence | — | — | C1：精确别名未证 |
| `claude-haiku-4-5-20251001` | 双 | blocked-needs-live-verification | — | C：`thinking.type=enabled`＋合法 `budget_tokens` | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发，仍未证实 |
| `claude-opus-4-1-20250805` | 双 | no-reliable-thinking-control-evidence | — | — | C3：精确控制未核、官方已退役 |
| `claude-opus-4-20250514` | 双 | no-reliable-thinking-control-evidence | — | — | C3：精确控制未核、官方已退役 |
| `claude-opus-4-5-20251101` | 双 | no-reliable-thinking-control-evidence | — | C：extended thinking 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发；中转控制证据不足 |
| `claude-opus-4-6` | 双 | no-reliable-thinking-control-evidence | — | C：adaptive＋summarized 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发；中转控制证据不足 |
| `claude-opus-4-7` | 双 | no-reliable-thinking-control-evidence | — | C：adaptive＋summarized 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发；中转控制证据不足 |
| `claude-opus-4-8` | 双 | no-reliable-thinking-control-evidence | — | C：adaptive＋summarized 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发；中转控制证据不足 |
| `claude-opus-5` | 双 | no-reliable-thinking-control-evidence | — | — | C1：精确别名未证 |
| `claude-sonnet-4-20250514` | 双 | no-reliable-thinking-control-evidence | — | — | C3：精确控制未核、官方已退役 |
| `claude-sonnet-4-5-20250929` | 双 | no-reliable-thinking-control-evidence | — | C：extended thinking 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发；中转控制证据不足 |
| `claude-sonnet-4-6` | 双 | blocked-needs-live-verification | — | C：adaptive＋summarized 离线候选 | 国内 HTTP 403；本轮海外开启 HTTP 200、SDK 解析，但无 thinking block/signature，关闭未发，仍未证实 |
| `claude-sonnet-5` | 双 | blocked-needs-live-verification | — | C：adaptive `thinking`＋`output_config.effort` | 国内首请求 HTTP 403；海外未运行，不能判定协议 |
| `deepseek-v4-flash` | 双 | implemented-and-exposed | 国内凭据显示思考模式：关闭／开启 | `thinking.type=disabled/enabled`；仅国内发送 | 国内 live verified: non-stream chat；海外 ReadTimeout 未证实，UI 隐藏 |
| `deepseek-v4-flash-0731` | 双 | no-reliable-thinking-control-evidence | — | — | DS：精确控制未证 |
| `deepseek-v4-pro` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | `thinking.type=disabled/enabled` | 双站 live verified: non-stream chat |
| `doubao-seed-2-1-pro-260628` | 双 | no-reliable-thinking-control-evidence | — | — | DB：精确字段未证 |
| `gemini-2.5-flash` | 双 | blocked-needs-live-verification | — | E：`reasoning_effort=low/none` 候选；官方原生 B `thinkingBudget` | 国内 HTTP 403；本轮海外 low/none 均 HTTP 200 且 SDK 解析，但两者 reasoning tokens 均为正数，不能证明关闭生效 |
| `gemini-2.5-flash-image-preview` | 双 | no-reliable-thinking-control-evidence | — | — | G1：精确图像预览控制未证 |
| `gemini-2.5-flash-lite` | 双 | blocked-needs-live-verification | — | E：`reasoning_effort=low/none` 候选；官方原生 B `thinkingBudget` | 国内 HTTP 403；本轮海外 low HTTP 200 且 SDK 解析，但 reasoning tokens 为 0，none 未发，仍未证实 |
| `gemini-2.5-pro` | 双 | blocked-needs-live-verification | — | E 候选；官方原生 B `thinkingBudget` | 国内首请求 HTTP 403；不可关闭；海外未运行 |
| `gemini-3-flash-preview` | 双 | blocked-needs-live-verification | — | E 候选；官方原生 B `thinkingLevel` | 国内首请求 HTTP 403，未判断协议；海外未运行 |
| `gemini-3-pro-image-preview` | 双 | no-reliable-thinking-control-evidence | — | — | G1：精确图像预览控制未证 |
| `gemini-3.1-flash-image-preview` | 双 | no-reliable-thinking-control-evidence | — | — | G1：精确图像预览控制未证 |
| `gemini-3.1-flash-lite-preview` | 双 | blocked-needs-live-verification | — | 待查，不构造候选请求 | G3：先补精确控制选项文档 |
| `gemini-3.1-pro-preview` | 双 | blocked-needs-live-verification | — | E 候选；官方原生 B `thinkingLevel` | 国内首请求 HTTP 403；海外未运行，不能判定协议 |
| `gemini-3.5-flash` | 双 | blocked-needs-live-verification | — | E 候选；官方原生 B `thinkingLevel` | 国内首请求 HTTP 403；海外未运行，不能判定协议 |
| `gemini-3.6-flash` | 双 | blocked-needs-live-verification | — | E 候选；官方原生 B `thinkingLevel` | 国内首请求 HTTP 403；海外未运行，不能判定协议 |
| `glm-5.1` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Z：disabled／enabled | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `glm-5.2` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Z：disabled／enabled | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `glm-5.3` | 双 | no-reliable-thinking-control-evidence | — | — | Z：固定思考，不显示虚假开关 |
| `gpt-5.5` | 双 | implemented-and-exposed | 海外凭据显示推理强度：none／low | `reasoning_effort=none/low`；仅海外发送 | 海外 live verified: non-stream chat；国内 HTTP 403，UI 隐藏 |
| `gpt-5.6-luna` | 双 | implemented-and-exposed | 海外凭据显示推理强度：none／low | `reasoning_effort=none/low`；仅海外发送 | 海外 live verified: non-stream chat；国内 HTTP 403，UI 隐藏 |
| `gpt-5.6-sol` | 双 | blocked-needs-live-verification | — | E：`reasoning_effort=low/none` 候选；官方 Responses `reasoning.effort` | 国内 HTTP 403；本轮海外 low HTTP 200 且 SDK 解析，但无 reasoning token 字段，none 未发，仍未证实 |
| `gpt-5.6-terra` | 双 | blocked-needs-live-verification | — | E：`reasoning_effort=low/none` 候选；官方 Responses `reasoning.effort` | 国内 HTTP 403；本轮海外 low HTTP 200 且 SDK 解析，但无 reasoning token 字段，none 未发，仍未证实 |
| `gpt-6-astra` | 双 | blocked-needs-live-verification | — | E 候选；官方 Responses `reasoning.effort` | 国内首请求 HTTP 403；海外未运行；无关闭选项 |
| `gpt-image-2(按次)` | 双 | no-reliable-thinking-control-evidence | — | — | O2：精确别名控制未证 |
| `kimi-k2.6` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Z：disabled／enabled | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `kimi-k2.7-code` | 双 | no-reliable-thinking-control-evidence | — | — | K：固定思考，未见可调项 |
| `kimi-k3` | 双 | implemented-but-hidden | — | E：`low/high/max` | 国内 low/high 均 HTTP 200，但单次 token／文本差异不足以证明强度生效；海外未运行 |
| `qwen3.6-27b` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | Q1,P1；双站四模式开关已实测，原失败历史保留 |
| `qwen3.6-35b-a3b` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `qwen3.6-flash` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `qwen3.6-plus` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | Q3,Phase 2；双站非流式聊天实测，其余模式仅离线合约 |
| `qwen3.7-max` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `qwen3.7-plus` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | live verified: dual-site non-stream chat；流式／FC 仅离线合约 |
| `qwen3.8-max` | 双 | implemented-and-exposed | 思考模式：关闭／开启 | Q：false／true | live verified: dual-site non-stream chat；预算／强度未实测 |
| `DeepSeek-R1-0528` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DS,FC：精确控制未证 |
| `DeepSeek-V3-0324` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DS,FC：精确控制未证 |
| `GLM-5` | 仅国内 | implemented-but-hidden | — | Z：`thinking.type=enabled/disabled` 候选 | 本轮国内开启 HTTP 200 且 SDK 解析，但无 `reasoning_content`，按停止规则未发送关闭；仍未证实 |
| `doubao-seed-2-0-code-preview-260215` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DB,FC：精确控制未证 |
| `doubao-seed-2-0-lite-260215` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DB,FC：精确控制未证 |
| `doubao-seed-2-0-mini-260215` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DB,FC：精确控制未证 |
| `doubao-seed-2-0-pro-260215` | 仅国内 | no-reliable-thinking-control-evidence | — | — | DB,FC：精确控制未证 |
| `qwen-plus` | 仅国内 | implemented-and-exposed | 国内凭据显示思考模式：关闭／开启 | Q：false／true，仅国内发送 | live verified: China non-stream chat；海外参数规则与发送由适配器隐藏／拦截，Dify UI 尚待人工验收 |
| `qwen3-max` | 仅国内 | implemented-and-exposed | 国内凭据显示思考模式：关闭／开启 | Q：false／true，仅国内发送 | live verified: China non-stream chat；海外参数规则与发送由适配器隐藏／拦截，Dify UI 尚待人工验收 |
| `qwen3-vl-plus` | 仅国内 | no-reliable-thinking-control-evidence | — | — | Q3,FC：精确控制未证 |

合计：`implemented-and-exposed` **16**（双站 11、仅国内 3、仅海外 2）；`implemented-but-hidden` **2**；`blocked-needs-live-verification` **14**；`no-reliable-thinking-control-evidence` **26**；共 **58**，不重复、不遗漏。此前站点扩展新增 4 个模型、5 个站点；最后 12 候选首关口没有新增开放。新型号 live verified 仅非流式普通聊天；流式／工具协议仍是离线合约，不冒称 live verified。0.0.9 保留 0.0.8 的 Function Calling 标签：41 `tool-call`、37 `stream-tool-call`、0 `multi-tool-call`。

## 站点级开放结果

下表中的 `verified` 仅表示所列站点的思考控制首关口通过，不等于流式或工具调用已经真实验证。参数面板还须在目标 Dify 安装环境人工验收。

| 精确模型 | Moyu | Konjac | UI／发送协议 |
| --- | --- | --- | --- |
| `qwen3.6-27b` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.6-plus` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.6-35b-a3b` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.6-flash` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.7-max` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.7-plus` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `qwen3.8-max` | verified | verified | 思考模式；`enable_thinking` 布尔 |
| `glm-5.1` | verified | verified | 思考模式；`thinking.type` 对象 |
| `glm-5.2` | verified | verified | 思考模式；`thinking.type` 对象 |
| `kimi-k2.6` | verified | verified | 思考模式；`thinking.type` 对象 |
| `deepseek-v4-pro` | verified | verified | 思考模式；`thinking.type` 对象 |
| `qwen-plus` | verified | unsupported-site | 思考模式；`enable_thinking` 布尔 |
| `qwen3-max` | verified | unsupported-site | 思考模式；`enable_thinking` 布尔 |
| `deepseek-v4-flash` | verified | unconfirmed (ReadTimeout) | 思考模式；`thinking.type` 对象 |
| `gpt-5.5` | blocked (HTTP 403) | verified | 推理强度：`none/low`；`reasoning_effort` |
| `gpt-5.6-luna` | blocked (HTTP 403) | verified | 推理强度：`none/low`；`reasoning_effort` |

其余 42 个模型在对应站点均未开放。国内 403 记录保持 blocked；只有 HTTP 200、用时或 token 数量差异而无可靠协议对照的站点保持 unconfirmed。`gemini-3.1-flash-lite-preview` 未取得精确合法值，没有请求；仅国内注册的型号在海外记为 unsupported-site，而非模型能力失败。

## 本轮后未开放的候选

- `implemented-but-hidden` 2 个：`kimi-k3` 国内及海外强度对照仍缺少协议级证据；仅国内 `GLM-5` 开／关无结构化对照。
- `blocked-needs-live-verification` 14 个：三款 Claude（Haiku 4.5、Sonnet 4.6、Sonnet 5）、七款 Gemini（2.5 Flash、2.5 Flash-Lite、2.5 Pro、3 Flash Preview、3.1 Pro Preview、3.5 Flash、3.6 Flash）、三款 GPT（5.6 Sol、5.6 Terra、6 Astra）国内 HTTP 403 且海外无可靠对照；另 `gemini-3.1-flash-lite-preview` 仍缺精确合法控制值。403 不等于参数错误、余额不足或模型不支持。
- `no-reliable-thinking-control-evidence` 26 个不开放；其中本轮七款新增 Claude 精确候选已测试，但国内 403、海外未取得正向结构化信号。

上一轮站点扩展上限 69 次，实际 52 次；其历史报告保持原样。已开放的站点专属型号通过 SDK `get_model_schema/get_parameter_rules` 按凭据站点过滤，并在 `_invoke` 拦截未验证站点的控制参数；目标 Dify 版本的参数面板仍须安装本地包后人工验收。公共 YAML 的静态文件本身不具备站点属性，不把离线合约冒称 UI 实测。

## 2026-09-27 十二候选首关口增量

本轮使用测试专用精确映射和原始响应结构观察器，通过插件 `MoyuLargeLanguageModel`、Dify SDK 0.9.0 构造请求；只发送非流式普通聊天。12 个候选中 **verified 0、blocked 0、unconfirmed 12**。HTTP 均为 200 且 SDK 均能解析，但没有一个形成所需开/关协议级对照；不得以 HTTP 成功推断参数生效。之前的国内 403 历史记录不改变。正式开放状态和 58 模型汇总数量不变。

| 模型 | 本轮站点 | 发送状态 | 安全观察结果 | 结论 |
| --- | --- | --- | --- | --- |
| `GLM-5` | Moyu | 开启 1 次 | 无 `reasoning_content` | unconfirmed；关闭未发 |
| `claude-haiku-4-5-20251001` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-sonnet-4-6` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-opus-4-5-20251101` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-opus-4-6` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-opus-4-7` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-opus-4-8` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `claude-sonnet-4-5-20250929` | Konjac | 开启 1 次 | 无 thinking block/signature | unconfirmed；关闭未发 |
| `gemini-2.5-flash` | Konjac | low、none 各 1 次 | 两状态 `reasoning_tokens` 均大于 0 | unconfirmed；无关闭对照 |
| `gemini-2.5-flash-lite` | Konjac | low 1 次 | `reasoning_tokens=0` | unconfirmed；none 未发 |
| `gpt-5.6-sol` | Konjac | low 1 次 | 缺 `reasoning_tokens` | unconfirmed；none 未发 |
| `gpt-5.6-terra` | Konjac | low 1 次 | 缺 `reasoning_tokens` | unconfirmed；none 未发 |

本轮上限 24 次，实际 **13** 次：Moyu 1、Konjac 12；服务端 usage 汇总分别为 Moyu prompt 23／completion 3／total 26，Konjac prompt 4618／completion 540／total 5158；13 次 usage 均有值。实际费用均未知，不从 token 反推扣费。未自动重试、换题或更换候选协议；原始回答、reasoning 和凭据不写入报告。脱敏记录：`scripts/thinking_twelve_live_report.json`。
