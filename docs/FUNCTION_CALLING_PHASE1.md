# Function Calling 第一阶段：离线协议修复记录

日期：2026-09-21。状态：本地修复及离线验证完成，等待批准真实站点验证。

## 1. 结论与范围

- **源码已确认**：SDK 0.9.0 默认 `function_calling_type=no_call`。原适配器只转交
  `tools`，不足以开启现代工具请求、响应解析和工具历史转换。
- **离线测试已通过**：适配器在凭据副本中始终设置 `tool_call`，包括下一轮
  `tools=None` / `tools=[]`。真实 SDK 构造和解析链由传输边界模拟响应验证。
- **真实站点尚未验证**：本阶段真实模型请求为 0；没有任何模型因此被判定支持工具。
  正式模型 YAML 未增加 `tool-call`、`multi-tool-call` 或 `stream-tool-call`。
  当前改动不会单独使这些模型出现在 Dify FunctionCalling 的能力筛选列表中。
- 无版本、生产依赖范围、供应商表单、Embedding 或 Rerank 改动；未提交、推送、
  操作 PR、同步全量模型、打包或发布。未读取 `.env` 或使用真实密钥。

## 2. 源码、注册与既有正式包

当前分支：`release/v0.0.6-marketplace-hardening`，manifest 两处版本仍为 `0.0.6`。
开始时无已跟踪文件改动；已有未跟踪的交接文件和 `ci_checks.html`、
`scripts/check_ci*.py`。仅更新获授权的两份交接文件，其余历史排错文件保留。

| 范围 | 核对结果 |
| --- | --- |
| 源码 `models/llm/` | 122 个 YAML |
| provider 显式注册 | 58 个 LLM、4 个 Embedding |
| 未注册历史 LLM | 64 个，本阶段未纳入注册或发布 |
| Rerank | 本地有代码及 YAML，未注册、权限关闭 |
| 已有 0.0.6 正式包 | 76 个 ZIP 条目、58 个 LLM YAML、4 个 Embedding YAML，无 Rerank |

正式包 LLM 文件清单与 provider 白名单一致，不等于源码整个目录。
包路径：`C:/Users/fangd/Workspace/CodeX/Dify/DIFY插件/moyu_ai_provider-0.0.6.difypkg`。
SHA256：`0B7E2F188108F1A8BB09CF786C4964F4BB12BC7162BA1B4B8A1CDD2CB9545980`。
该包未改变，也**不包含本次尚未打包的源码修复**。

## 3. 实际测试环境与安全入口

manifest 要求 Python 3.12。使用已有 Python 3.12.14 创建项目独立 venv；
没有安装系统 Python，也没有修改、升级或卸载 Anaconda base 中的包。

- 解释器：`C:/Users/fangd/Workspace/CodeX/Dify/.venvs/moyu-fc-sdk090/Scripts/python.exe`
- Python：3.12.14
- SDK：`dify_plugin==0.9.0`
- SDK 加载路径：`C:/Users/fangd/Workspace/CodeX/Dify/.venvs/moyu-fc-sdk090/Lib/site-packages/dify_plugin/__init__.py`
- 其他实际版本：pytest 8.4.2、PyYAML 6.0.3、pydantic 2.13.5、
  pydantic-settings 2.15.0、requests 2.34.2、python-dotenv 1.2.3。
- 开发依赖入口：`scripts/requirements-fc-tests.txt`；生产 requirements.txt 未改。
- 环境依赖一致性检查：`pip check` 输出 `No broken requirements found.`

从 `test_01` 根目录运行：

```powershell
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py
& '..\..\.venvs\moyu-fc-sdk090\Scripts\python.exe' -I -B scripts/run_offline_checks.py --preflight
```

SDK 导入会实例化带 `env_file=.env` 的设置对象。因此安全入口先禁用 dotenv
及继承的进程环境设置源，安装拒绝打开 `.env` / `.env.*` 的审计钩子，再导入 SDK。
导入 SDK 后封锁 HTTP 发送、socket 连接/DNS，以及子进程执行路径；关闭 pytest
第三方插件自动加载、字节码与 pytest 缓存。测试只使用虚构密钥，未启动 main.py。
这些保护只作用于测试进程，没有修改已安装 SDK 源文件。

## 4. 先失败、后修复的证据

| 阶段 | 实际结果 | 含义 |
| --- | --- | --- |
| 新测试前，真实 SDK 安全入口跑原有测试 | 160 passed | 原有基线通过 |
| 新增合约测试，适配器修复前 | 10 failed、17 passed、2 warnings | 9 项暴露协议缺失，1 项暴露缺 content 的 SDK 问题 |
| 仅设置 `function_calling_type=tool_call` | 1 failed、26 passed、4 warnings | 协议类失败消除，仍剩缺 content |
| 加入窄范围响应兼容，跑完整测试 | 188 passed、4 warnings | 原有 160 + 新合约 27 + 能力声明保护 1 |
| 最终完整回归复跑 | 188 passed、4 warnings | 0 failed、0 skipped |
| 发布预检 | 143 passed、0 warnings、0 failed | 结构检查通过；不代表已可发布或真实模型能力通过 |

修复前失败来自行为断言或 SDK 的 `KeyError: content`，不是导入、环境或测试构造错误。
发布预检更新现有忽略文件 `scripts/preflight_report.json`，未生成安装包。

### 真实 SDK 合约覆盖

新增测试 `tests/test_llm_sdk_contract.py` 实例化真实 SDK 和测试专用模型配置，
只模拟 `requests.post` 网络边界，提供真实 `requests.Response` JSON/SSE 数据。
没有替换 SDK `_invoke`、`_generate`、消息转换或响应解析；流式生成器实际消费完毕。
既有凭据转发测试保留原有基类方法 mock，用途不同，不能冒充真实 SDK 集成测试。

1. 凭据副本固定现代协议，原字典不变，Key 去空格不变。
2. 国内默认地址、海外自定义地址及 `stop`、`user`、模型参数传递不变。
3. 完整工具定义实际进入请求；SDK 0.9.0 有工具时使用 `tool_choice=auto`，
   即使 model_parameters 提供 `required` 也会被 SDK 覆盖。本次不改变该行为。
4. 非流式工具 ID、函数名、JSON 参数及 usage 正确保留。
5. 工具执行结果回传中的 assistant tool_calls、role=tool、tool_call_id 匹配。
6. 后续 tools 为 None 和空列表时，历史仍正确发送，不附带新的工具定义。
7. 普通聊天的流式与非流式回归，不发送无关 tools/functions/tool_choice。
8. SSE 工具参数分片恢复为完整 JSON，并验证生成器终止、usage 和 finish_reason。
9. 分别验证非流式 content=null 和 content 缺失；SSE 包含 null 与缺 content 的分片。
10. 原 SDK 默认值/no_call/tool_call 对照覆盖请求、历史和流式/非流式解析。
11. 覆盖公开 SDK invoke 入口、畸形聊天仍报错、网络与 dotenv 打开保护。

## 5. SDK 额外问题及最小修复

SDK 0.9.0 的非流式解析直接读取 `message["content"]`。
响应含有效非空 tool_calls、但省略 content 时，原 SDK 抛出 `KeyError: content`。
`test_base_sdk_missing_content_limitation_is_reproducible` 使用预期异常明确保留复现；
对应适配器正向测试必须成功，不能用预期异常代替插件成功测试。

最小兼容只针对现代工具协议下非空 tool_calls 且 content 缺失的响应：
复制 Response，将缺失字段补为空字符串，再交原 SDK 解析。显式 null 不改，
原响应字节不变，畸形普通聊天继续报错。不复制大段 SDK、不吞异常、不跳过测试。

剩余 4 条警告来自 SDK 的 `openai_compatible/llm.py:979` 调用 Pydantic `.dict()`；
属于弃用警告，本轮未屏蔽，也未修改依赖范围或 SDK。

本轮覆盖的协议没有剩余阻塞，但验证边界包括：

- 只验证 SDK 0.9.0，不保证生产开放范围内所有新 SDK 版本相同行为。
- 单工具合约不证明并行、多工具交错分片等行为；不开放 multi-tool-call。
- 模拟响应带 usage；未证明所有缺 usage/异常上游响应形态兼容。
- 未进行 Dify 部署端 Agent 端到端验证，也未知客户确切 Dify/策略版本。

## 6. 修改文件与原因

| 文件 | 原因 |
| --- | --- |
| models/llm/llm.py | 无条件设置凭据副本现代协议；缺 content 纯工具响应的窄范围兼容 |
| tests/test_llm_sdk_contract.py | 真实 SDK 离线请求/解析合约与默认协议对照 |
| tests/test_config_integrity.py | 防止本阶段误开放正式模型工具能力 |
| tests/offline_safety.py、tests/conftest.py | 导入前隔离 dotenv，阻断真实网络；保留原有测试 |
| scripts/run_offline_checks.py | 强制独立 Python 3.12 / SDK 0.9.0 的安全验证入口 |
| scripts/requirements-fc-tests.txt | 与生产依赖分开的测试依赖入口 |
| AGENTS.md、CODEX_HANDOFF.md | 修正版本、注册数量、地址、测试覆盖和 SDK 导入风险等过时信息 |
| docs/FUNCTION_CALLING_PHASE1.md | 本记录及下一阶段待批准方案 |

## 7. 后续能力记录方案（仅设计，本阶段未实施）

独立能力台账以 **站点规范化 base URL + 精确模型 ID** 为复合键。
分别记录非流式单工具、流式单工具、多工具的 `untested/pass/fail/inconclusive`，
附日期、SDK/Python、请求模型与返回模型、finish_reason、工具 ID/函数/参数匹配、
回传结果闭环、脱敏证据摘要/哈希，必要时保留不敏感的请求追踪 ID。
禁止保存凭据、Authorization 或客户内容。HTTP 200 或普通聊天成功不算工具通过。

后续修改 sync_models.py 时，应从这个独立台账按精确键合并能力声明，而不是
根据名称关键词推断或盲目继承旧 YAML 标记。一个静态模型若承诺支持两站，相关
能力必须两站都有有效证据；站点专属模型也必须严格匹配自身站点范围。
缺失、过期或结果不一致时不自动开放能力，先人工复核。
为生成逻辑增加“已验证标记不丢失、未知标记不生成、跨站不混用”的测试。
本阶段未修改或运行同步脚本，更未运行 --clean。

## 8. 第二阶段真实验证提案（尚未授权执行）

以下仅为当前已注册目录中的候选，不代表支持工具或当前在线可用：

| 精确模型 ID | 拟测试站点 |
| --- | --- |
| claude-fable-5 | 国内、海外 |
| claude-sonnet-4-6 | 国内、海外 |
| qwen3.6-plus | 国内、海外 |
| qwen-plus | 国内 |
| doubao-seed-2-0-pro-260215 | 国内 |

共 8 个“站点 + 模型”组合，每组计划 4 次模型请求：
非流式请求工具 → 本地执行 add → 非流式回传结果；
流式请求工具 → 本地执行 add → 流式回传结果。
因此 **计划 32 次、含排错/重试硬上限 40 次 HTTP 请求尝试**。
不自动无限重试；额外模型列表/凭据验证请求若必须执行，也计入上限。
这不是费用上限，实际费用按站点模型计费；批准时一并确认费用接受范围。

步骤：

1. 人工批准模型、两站范围、请求及费用上限；另行提供安全凭据注入渠道。
   不读取 `.env`、不把旧聊天中的真实 Key 复制进代码/文档/日志。
2. 先用 qwen3.6-plus 在国内和海外各完成一组，再执行其余组合。
3. 工具只做本地确定性的两数相加，不访问第三方服务、不修改外部状态。
   沿用当前 SDK 的 auto 选择；没有产生工具调用时记录为未证实，不伪造结果。
4. 控制输入与输出长度（可从 max_tokens=256 起步）；截断、配额、认证或限流
   不能当成能力不支持。遇到系统性错误暂停；追加尝试占用剩余上限。
5. 对比线上响应与解析结果，完整核对 ID/函数/参数和工具结果闭环，记录能力台账。
6. 汇报证据与失败/不确定项，人工批准后才讨论 YAML 开放、测试包及 Dify Agent
   UI 端到端验收。本方案不测试或宣称多工具能力。

阶段一到此停止，不自动进入上述真实验证。
