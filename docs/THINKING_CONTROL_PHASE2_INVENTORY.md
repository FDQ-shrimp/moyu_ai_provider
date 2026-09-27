# Thinking Control Phase 2：58 个正式 LLM 的离线盘点

核对日期：2026-09-25。范围仅为 `provider/moyu.yaml` 的 58 条 LLM `predefined`；不是目录里的 122 个 YAML。本文是**接入候选盘点**，不是新增能力声明，也不是两站实测通过报告。没有发送 Phase 2 真实模型请求。

## Phase 1 交接状态

`qwen3.6-27b` 的两站非流式/流式普通聊天开关对照、两站非流式工具开关、国内流式工具开关、海外流式工具开启均有完整正向记录。原最后场景“海外流式工具、`enable_thinking=false`”在累计第 24 次请求的第一轮、等待响应头时发生 `ReadTimeout`（10.766 秒）；该原记录保持**未证实**，未被追溯改写。用户另行批准最后一次最多两请求的完整重测后，累计第 25、26 次均 HTTP 200；第一轮结构化 `add(a=2,b=3)` 与 SDK 解析一致，本地执行得 5，第二轮用相同 `tool_call_id` 回传并严格回答 `5`。因此 Phase 1 的 **16 个站点×模式×开关组合均已通过**，全模式验收完成。新报告为 `scripts/thinking_qwen36_27b_last_retest_report.json`（SHA256 `1B3A5998019712ACA83821C6605433721EB655368F903A330FDC2F665529BAE2`）；原第 24 次报告 SHA256 `52BB0527BF51C8C2444F2C0649C52DDF9A51B60EB194C0D7F029A982836E8076` 保持不变。更早的 401 历史只证明认证/权限类错误，不证明余额不足。

## 判定口径与当前源码

- “官方支持”只指**精确模型 ID** 的官方文档或模型卡证据；同系列、相似名称、供应商别名、退役型号均不自动继承。
- 官方原生接口、官方 OpenAI 兼容接口、Moyu/Konjac 转发接口是三层不同协议。官方参数存在不代表两个中转站透传或映射正确。**除了 `qwen3.6-27b` 已记录的模式，所有站点映射仍未验证。**该样板模型通过也不授权将参数批量复制给同系列模型。
- `支持控制` 可以是开/关、强度或预算之一；“模型会思考”不等于能控制。只支持强度的型号不得显示虚假的开/关选项。默认值只记录官方明确说明的行为，其余为“未核”。
- 当前 58 个正式 YAML 的 `parameter_rules`：57 个仅 `temperature/top_p/max_tokens`，`gpt-6-astra` 仅 `max_tokens`。**没有** `enable_thinking`、`thinking_budget`、`thinking_level`、`reasoning_effort` 等正式参数。`agent-thought` feature 不是用户可调开关。Dify SDK 0.9.0 会过滤未声明的模型参数；Phase 1 只在测试专用 YAML 副本里临时加入布尔规则。
- 下表“国内/海外”写的是**思考参数映射状态**，不是 Function Calling 能力；“国内可测/仅国内”站点属性沿用现有 Function Calling 台账。仅国内模型的海外列为“不适用”。

类别互斥：**A**＝精确型号有官方参数且已有两站同一参数形态的完整正向实测；**B**＝精确型号有官方控制证据，但其官方参数不是布尔 `enable_thinking`；**C**＝官方有思考能力/控制线索，但中转映射或精确控制细节未证实；**D**＝精确型号缺少可用于接入的可靠控制证据，或明确只有不可关闭且无可调强度的固定思考。A 是单模型技术证据，不等于正式接入或可发布；B/C 是待验证候选。

缩写：`待证`＝Moyu/Konjac 映射未实测；`仅内`＝国内站有该模型既往可用性证据，海外不适用；`实测`＝若以后接入，须按精确 ID、站点、普通/流式/工具模式分阶段验证；`查证`＝先补官方或站点文档，暂不发真实请求；`不接`＝现阶段不显示思考参数。官方来源编号见文末；`—` 表示没有找到能支持该精确 ID 接入的参数证据。

| 模型 | 类 | 是否支持思考控制 | 官方参数 | 参数类型/功能 | 默认行为 | 国内映射 | 海外映射 | 是否需要实测 | 建议接入方式 | 证据来源 |
| --- | :---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MiniMax-M3` | D | 推理特性有，控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | MM |
| `claude-fable-5` | D | 精确官方 ID/控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接；不可把 `claude-fable-5-1` 当同一 ID | C1 |
| `claude-haiku-4-5-20251001` | B | 是，extended thinking | `thinking.type=enabled`, `thinking.budget_tokens` | 对象＋数字预算；可选择启用 | 默认未核 | 待证 | 待证 | 实测 | 独立 Claude 映射及预算校验 | C1,C2 |
| `claude-opus-4-1-20250805` | D | 精确控制未核；官方已退役 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C3 |
| `claude-opus-4-20250514` | D | 精确控制未核；官方已退役 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C3 |
| `claude-opus-4-5-20251101` | D | 精确控制方式未核 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C3 |
| `claude-opus-4-6` | D | 精确控制方式未核 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C2,C4 |
| `claude-opus-4-7` | D | 精确控制方式未核 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C2,C4 |
| `claude-opus-4-8` | D | 精确控制方式未核 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C2,C4 |
| `claude-opus-5` | D | 精确 ID 未在当前官方型号清单核实 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接；不可把 `claude-opus-5-5` 当同一 ID | C1 |
| `claude-sonnet-4-20250514` | D | 精确控制未核；官方已退役 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C3 |
| `claude-sonnet-4-5-20250929` | D | 精确控制方式未核 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | C3 |
| `claude-sonnet-4-6` | B | 是，extended/adaptive | `thinking.type`, `thinking.budget_tokens`；adaptive 路径另核 | 对象＋数字预算/模式 | 未核 | 待证 | 待证 | 实测 | 独立 Claude 映射；先只测一种有据参数形态 | C2,C4 |
| `claude-sonnet-5` | B | 是，adaptive thinking/effort | `thinking.type=adaptive`, `output_config.effort` | 对象＋强度枚举；非简单关 | 官方表列 adaptive | 待证 | 待证 | 实测 | 独立 Claude 强度映射，不显示布尔关闭 | C1,C4 |
| `deepseek-v4-flash` | D | 旧别名可见，精确控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接；不套用 `deepseek-flash` 示例 | DS |
| `deepseek-v4-flash-0731` | D | 精确 ID 未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | DS |
| `deepseek-v4-pro` | D | 官方页提及型号，但未给出该 ID 的控制协议 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | DS |
| `doubao-seed-2-1-pro-260628` | D | 精确控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | DB |
| `gemini-2.5-flash` | B | 是，预算/关闭/强度 | 原生 `thinkingBudget`；兼容接口 `reasoning_effort` | 数字预算/枚举 | 官方默认开 | 待证 | 待证 | 实测 | 独立 Gemini 映射；先确认中转接口形态 | G1,G2 |
| `gemini-2.5-flash-image-preview` | D | 精确图像预览 ID 控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | G1 |
| `gemini-2.5-flash-lite` | B | 是，预算/开启/强度 | 原生 `thinkingBudget`；兼容接口 `reasoning_effort` | 数字预算/枚举 | 官方默认关 | 待证 | 待证 | 实测 | 独立 Gemini 映射 | G1,G2 |
| `gemini-2.5-pro` | B | 是，预算/强度；不可关闭 | 原生 `thinkingBudget`；兼容接口 `reasoning_effort` | 数字预算/枚举，禁用关选项 | 官方默认开 | 待证 | 待证 | 实测 | 独立 Gemini 映射，仅预算/强度 | G1,G2 |
| `gemini-3-flash-preview` | B | 是，思考强度 | 原生 `thinkingLevel`；兼容接口 `reasoning_effort` | 枚举；`minimal/low/medium/high` | 官方默认 high | 待证 | 待证 | 实测 | 独立 Gemini 3 映射；不预设可关 | G1,G2 |
| `gemini-3-pro-image-preview` | D | 精确图像预览 ID 控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | G1 |
| `gemini-3.1-flash-image-preview` | D | 精确图像预览 ID 控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | G1 |
| `gemini-3.1-flash-lite-preview` | C | 官方型号页仅证明有 Thinking，精确控制选项未核 | 待查 | 待查 | 未核 | 待证 | 待证 | 先查证 | 暂不接；先取得该 ID 的控制值证据 | G3 |
| `gemini-3.1-pro-preview` | B | 是，思考强度；不可关闭 | 原生 `thinkingLevel`；兼容接口 `reasoning_effort` | 枚举；`low/medium/high` | 官方默认 high | 待证 | 待证 | 实测 | 独立 Gemini 3 映射，仅强度 | G1,G2 |
| `gemini-3.5-flash` | B | 是，思考强度 | 原生 `thinkingLevel`；兼容接口 `reasoning_effort` | 枚举；`minimal/low/medium/high` | 官方默认 medium | 待证 | 待证 | 实测 | 独立 Gemini 3 映射；不预设可关 | G1,G2 |
| `gemini-3.6-flash` | B | 是，思考强度 | 原生 `thinkingLevel`；兼容接口 `reasoning_effort` | 枚举；`minimal/low/medium/high` | 官方默认 medium | 待证 | 待证 | 实测 | 独立 Gemini 3 映射；不预设可关 | G1,G2 |
| `glm-5.1` | B | 是，开/关 | `thinking.type=enabled/disabled` | 对象＋枚举 | 默认开 | 待证 | 待证 | 实测 | 独立 GLM 映射 | Z |
| `glm-5.2` | B | 是，开/关 | `thinking.type=enabled/disabled` | 对象＋枚举 | 默认开 | 待证 | 待证 | 实测 | 独立 GLM 映射 | Z |
| `glm-5.3` | D | 固定思考；官方明确不可关闭，未见其他可调项 | — | — | 默认开 | 待证 | 待证 | 先查证 | 不显示开/关 | Z |
| `gpt-5.5` | B | 是，推理强度/`none` 关闭 | 官方 Responses `reasoning.effort` | 枚举；`none/low/medium/high/xhigh` | 默认 medium | 待证 | 待证 | 实测 | 独立 GPT 映射；Chat Completions `reasoning_effort` 需另核 | O1,O2 |
| `gpt-5.6-luna` | B | 是，推理强度/`none` 关闭 | 官方 Responses `reasoning.effort` | 枚举；`none/low/medium/high/xhigh/max` | 默认 medium | 待证 | 待证 | 实测 | 独立 GPT 映射；Chat 参数另核 | O1,O2 |
| `gpt-5.6-sol` | B | 是，推理强度/`none` 关闭 | 官方 Responses `reasoning.effort` | 枚举；`none/low/medium/high/xhigh/max` | 默认 medium | 待证 | 待证 | 实测 | 独立 GPT 映射；Chat 参数另核 | O1,O2 |
| `gpt-5.6-terra` | B | 是，推理强度/`none` 关闭 | 官方 Responses `reasoning.effort` | 枚举；`none/low/medium/high/xhigh/max` | 默认 medium | 待证 | 待证 | 实测 | 独立 GPT 映射；Chat 参数另核 | O1,O2 |
| `gpt-6-astra` | B | 是，推理强度；不可关闭 | 官方 Responses `reasoning.effort` | 枚举；`low/medium/high/xhigh/max` | 未核 | 待证 | 待证 | 实测 | 独立 GPT 映射，仅强度 | O1,O2 |
| `gpt-image-2(按次)` | D | 供应商别名；精确控制未证 | — | — | 未核 | 待证 | 待证 | 先查证 | 不接 | O2 |
| `kimi-k2.6` | B | 是，开/关和 thinking 保留策略 | `thinking.type=enabled/disabled`; `thinking.keep` | 对象＋枚举 | 默认开 | 待证 | 待证 | 实测 | 独立 Moonshot 映射；先仅测 type | K |
| `kimi-k2.7-code` | D | 固定思考；官方称不能关闭，未见可调项 | — | — | 默认开 | 待证 | 待证 | 先查证 | 不显示开/关 | K |
| `kimi-k3` | B | 是，推理强度；不可关闭 | `reasoning_effort` | 枚举；`low/high/max` | 默认 max | 待证 | 待证 | 实测 | 独立 Moonshot 强度映射 | K |
| `qwen3.6-27b` | A | 是，开/关；两站全部约定模式实测 | 顶层 `enable_thinking`（阿里云）；自部署是 `chat_template_kwargs.enable_thinking` | boolean | 默认开 | 开/关聊天及工具模式通过 | 开/关聊天及工具模式通过；关闭流式工具引用受控重测 | 正式接入后仍需 Dify 验收 | 仅此精确 ID 可考虑顶层布尔规则；暂不改 YAML | Q1,P1 |
| `qwen3.6-35b-a3b` | C | 是，开/关、预算候选 | 顶层 `enable_thinking`, `thinking_budget`（阿里云） | boolean＋数字 | 默认开 | 待证 | 待证 | 实测 | 候选复用 `enable_thinking`，两站各自验证 | Q2,Q3 |
| `qwen3.6-flash` | C | 是，开/关、预算候选 | 顶层 `enable_thinking`, `thinking_budget` | boolean＋数字 | 默认开 | 待证 | 待证 | 实测 | 同上，仅此精确 ID | Q3 |
| `qwen3.6-plus` | C | 是，开/关、预算候选 | 顶层 `enable_thinking`, `thinking_budget` | boolean＋数字 | 默认开 | 待证 | 待证 | 实测 | 同上，仅此精确 ID | Q3 |
| `qwen3.7-max` | C | 是，开/关、预算候选 | 顶层 `enable_thinking`, `thinking_budget` | boolean＋数字 | 默认开 | 待证 | 待证 | 实测 | 同上，仅此精确 ID | Q3 |
| `qwen3.7-plus` | C | 是，开/关、预算候选 | 顶层 `enable_thinking`, `thinking_budget` | boolean＋数字 | 默认开 | 待证 | 待证 | 实测 | 同上，仅此精确 ID | Q3 |
| `qwen3.8-max` | C | 是，开/关、预算、强度候选 | 顶层 `enable_thinking`, `thinking_budget`, `reasoning_effort` | boolean＋数字＋枚举 | 默认开 | 待证 | 待证 | 实测 | 分开验证三种能力；不一次盲发 | Q3 |
| `DeepSeek-R1-0528` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DS,FC |
| `DeepSeek-V3-0324` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DS,FC |
| `GLM-5` | B | 是，开/关 | `thinking.type=enabled/disabled` | 对象＋枚举 | 默认开 | 仅内，映射未证 | 不适用 | 实测 | 仅国内独立 GLM 映射；公共参数须站点隔离 | Z,FC |
| `doubao-seed-2-0-code-preview-260215` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DB,FC |
| `doubao-seed-2-0-lite-260215` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DB,FC |
| `doubao-seed-2-0-mini-260215` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DB,FC |
| `doubao-seed-2-0-pro-260215` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | DB,FC |
| `qwen-plus` | C | 是，开/关 | 顶层 `enable_thinking` | boolean | 默认关 | 仅内，映射未证 | 不适用 | 实测 | 国内专属参数展示；公共 YAML 不开放 | Q3,FC |
| `qwen3-max` | C | 是，开/关 | 顶层 `enable_thinking` | boolean | 默认关 | 仅内，映射未证 | 不适用 | 实测 | 国内专属参数展示；公共 YAML 不开放 | Q3,FC |
| `qwen3-vl-plus` | D | 精确控制未证 | — | — | 未核 | 仅内，映射未证 | 不适用 | 先查证 | 不接 | Q3,FC |

## 分组与接入顺序

- **A（1）**：`qwen3.6-27b`。顶层布尔参数的普通聊天、非流式工具及流式工具开/关均有双站证据；海外关闭流式工具由第 25、26 次受控重测补齐，原第 24 次超时历史保留。A 不等于已正式接入或可发布。
- **B（20）**：`claude-haiku-4-5-20251001`, `claude-sonnet-4-6`, `claude-sonnet-5`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro`, `gemini-3-flash-preview`, `gemini-3.1-pro-preview`, `gemini-3.5-flash`, `gemini-3.6-flash`, `glm-5.1`, `glm-5.2`, `GLM-5`, `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-6-astra`, `kimi-k2.6`, `kimi-k3`。原生参数形态不应塞入统一布尔字段；全部站点映射待证。
- **C（9）**：`gemini-3.1-flash-lite-preview`, `qwen3.6-35b-a3b`, `qwen3.6-flash`, `qwen3.6-plus`, `qwen3.7-max`, `qwen3.7-plus`, `qwen3.8-max`, `qwen-plus`, `qwen3-max`。Qwen 八个精确 ID 有官方顶层参数依据，但 Moyu/Konjac 不自动继承 qwen3.6-27b 的实测；Gemini 型号还须补精确参数证据。
- **D（28）**：其余表内标 D 的精确 ID。无足够控制协议证据或只有固定思考，不显示控制参数；继续离线查证，不以家族推断。

核对：A 1＋B 20＋C 9＋D 28＝58；每个正式注册 ID 恰好出现一次。现阶段正式 YAML 新增思考参数数为 **0**。

建议下一批先选 4 个代表型号（需用户另行批准真实请求与预算，**此处没有执行**）：`qwen3.6-plus`（顶层布尔参数复用候选）、`glm-5.2`（对象型开/关）、`gemini-2.5-flash`（预算/兼容强度）、`gpt-5.5`（强度含 `none`）。每个模型先离线确认 SDK 请求形态，之后分别按站点及开/关或强度进行最小对照；两站均有可观测正向证据才推进流式，再推进工具闭环。`qwen-plus` 和 `GLM-5` 是后续仅国内专批，不发海外请求。Claude 与 Kimi 独立参数再分批验证。任何阶段不明确即停止该型号，不自动尝试其他参数位置。批次请求数量与费用需按所选协议重新计算、另行审批；不能直接套用 Phase 1 的 25 次额度。

## 官方与项目证据索引

- Q1：[Qwen3.6-27B 模型卡](https://huggingface.co/Qwen/Qwen3.6-27B/blob/main/README.md)：默认思考、关闭方式、阿里云顶层与自部署嵌套参数区别。
- Q2：[Qwen3.6-35B-A3B 模型卡](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/blob/main/README.md)。
- Q3：[阿里云百炼深度思考文档](https://help.aliyun.com/zh/model-studio/deep-thinking)：逐模型支持表、`enable_thinking`、预算及部分强度参数。其直供协议不等于两个中转站协议。
- C1：[Anthropic 当前模型总览](https://platform.claude.com/docs/en/about-claude/models/overview)：核对精确 Claude ID 与 Thinking 类型；`claude-fable-5-1`、`claude-opus-5-5` 不等于插件别名。
- C2：[Anthropic extended thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)：`thinking.type` 与 `budget_tokens`。
- C3：[Anthropic 模型退役表](https://platform.claude.com/docs/en/about-claude/model-deprecations)。
- C4：[Anthropic adaptive thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)：adaptive 与 effort 的版本差异。
- G1：[Gemini thinking](https://ai.google.dev/gemini-api/docs/thinking)：2.5 预算、3 系列 level、默认值与不可关闭限制。
- G2：[Gemini OpenAI 兼容接口](https://ai.google.dev/gemini-api/docs/openai)：`reasoning_effort` 映射；不可假定 Moyu/Konjac 等同该接口。
- G3：[Gemini 3.1 Flash-Lite Preview 型号页](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite-preview)：Thinking 能力存在，控制值仍待核。
- Z：[Z.ai Thinking Mode](https://docs.z.ai/guides/capabilities/thinking-mode)：GLM-5/5.1/5.2 开关及 GLM-5.3 固定思考。
- O1：[OpenAI reasoning guide](https://platform.openai.com/docs/guides/reasoning)：Responses `reasoning.effort`；Chat Completions 形态须另核。
- O2：OpenAI 精确型号页：[5.5](https://platform.openai.com/docs/models/gpt-5.5)、[5.6 Luna](https://platform.openai.com/docs/models/gpt-5.6-luna)、[5.6 Sol](https://platform.openai.com/docs/models/gpt-5.6-sol)、[5.6 Terra](https://platform.openai.com/docs/models/gpt-5.6-terra)、[6 Astra](https://platform.openai.com/docs/models/gpt-6-astra)。型号能力不证明供应商别名相等。
- K：[Moonshot Thinking Models](https://platform.moonshot.ai/docs/guide/use-thinking-models)：Kimi 2.6 开关/keep、2.7 Code 固定思考、K3 强度。
- DS：[DeepSeek 推理模型文档](https://api-docs.deepseek.com/guides/reasoning_model)：示例针对 `deepseek-flash`，旧别名和 Pro 的精确参数不可自动类推。
- MM：[MiniMax 型号说明](https://platform.minimax.io/docs/guides/models-intro)：能核实型号与推理特性，未取得控制协议。
- DB：[火山引擎相关入口](https://www.volcengine.com/docs/82379/1399008)：本轮未获取可引用的精确 Doubao 控制字段内容，故一律 D。
- FC：项目既有 `docs/VERIFIED_TOOL_CAPABILITIES.yaml` 的站点属性，仅用于标记仅国内模型，**不证明思考控制**。
- P1：项目脱敏 Phase 1 报告（`scripts/thinking_qwen36_27b_round1_report.json`、`scripts/thinking_qwen36_27b_auth_resume_report.json`、`scripts/thinking_qwen36_27b_final_pair_report.json`、`scripts/thinking_qwen36_27b_last_retest_report.json`）。

本文未修改模型 YAML、适配器、版本、安装包或旧报告；未 commit/push。下一步必须先由用户批准明确候选、站点、模式、请求数和预算，才可以启动任何新的真实模型请求。
