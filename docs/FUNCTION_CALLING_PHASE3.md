# Function Calling 第三阶段：0.0.7 本地测试包交付

日期：2026-09-21。仅本地准备，不是市场发布或 Dify Agent 验收通过报告。

## 本阶段修改

- `models/llm/qwen3.6-plus.yaml`：在已有 `vision`、`agent-thought` 后新增
  `tool-call`、`stream-tool-call`；其他字段不变。没有任何模型新增 `multi-tool-call`。
- `manifest.yaml`：仅顶层发布 `version` 从 0.0.6 改为 0.0.7。
  `meta.version: 0.0.6` 是既有 manifest 格式版本，保留；
  `meta.runner.version: "3.12"` 是 Python 运行时版本，保留。
  author、name、权限和供应商凭据定义均未变化。
- `tests/test_config_integrity.py`：用显式允许清单替代阶段一的全面禁用工具标记检查，
  增加 qwen 原配置保留、能力记录与两份证据报告哈希/请求编号关联检查。
- `scripts/preflight_check.py`：修正旧版将发布版本与格式版本强制相等的错误规则；
  两者独立验证有效格式，测试另行固定本次各字段的期望值，没有取消版本检查。
- `docs/VERIFIED_TOOL_CAPABILITIES.yaml` 及配套说明：按站点＋精确模型 ID＋模式记录
  SDK 0.9.0 的实测证据，禁止按模型名称猜测能力。
- `scripts/local_package.py` 及 `tests/test_local_package_selection.py`：只暂存注册清单中的
  文件，检查范围、版本、凭据模式和基线差异；由现有 CLI 打包后解包逐字节核对。
- README 中英文、RELEASE_CHECKLIST、AGENTS、CODEX_HANDOFF 和人工验收说明同步更新。

版本字段含义参考 Dify 官方
[manifest 说明](https://github.com/langgenius/dify-docs/blob/main/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest.mdx)：
顶层 version 是插件版本；meta.version 是 manifest 格式版本；runner.version 是语言版本。
本次未迁移既有格式版本，也未机械地更新所有名为 version 的字段。

此前已完成的 `models/llm/llm.py` 修复随新包交付，但本阶段没有再修改适配器业务逻辑。
生产依赖范围未改，未改 Embedding/Rerank，未运行同步脚本或 `--clean`。

## 验证记录与历史保护

| 站点 | 精确模型 ID | 非流式单工具 | 流式单工具 | SDK |
| --- | --- | --- | --- | --- |
| 国内 | qwen3.6-plus | 第二阶段请求 1、2 通过 | 续测请求 7、8 通过 | 0.9.0 |
| 海外 | qwen3.6-plus | 第二阶段请求 3、4 通过 | 续测请求 9、10 通过 | 0.9.0 |

此表引用既有证据，不是本阶段的新请求。第 6 次仍为“未证实”，没有追溯改写。
原始文件复核 SHA256：

- `scripts/fc_phase2_round1_report.json`：
  `57f8ce5032733a7ea13b9ecffb383b3697ce04b61ac725ce1f98c2a0b7559d72`
- `scripts/fc_phase2_stream_resume_report.json`：
  `0dfdea601f90aafe93ed1cbcd33bca4991cecbab8326fd581cc6bda23727b43d`

后续重新生成模型时，当前 `sync_models.py` 不会自动读取能力记录。
必须另行授权，在独立暂存目录生成，按能力记录精确合并批准的标记，再运行允许清单测试。
具体流程见 [能力记录维护说明](VERIFIED_TOOL_CAPABILITIES.md)；本阶段没有运行模型同步。

## 离线验证

- 解释器：`C:\Users\fangd\Workspace\CodeX\Dify\.venvs\moyu-fc-sdk090\Scripts\python.exe`
- Python 3.12.14；SDK 0.9.0，来自该环境的 `Lib/site-packages/dify_plugin/__init__.py`。
- 使用 `scripts/run_offline_checks.py`，导入 SDK 前隔离 dotenv/设置源，阻断真实网络及子进程。
- 新配置测试在实施前出现预期的 3 处失败（旧发布版本/缺少获准能力标记），其余 140 项通过。
- 最终完整回归：**232 通过，0 失败，0 跳过**；22 条 SDK Pydantic `.dict()` 弃用警告，
  其中 live-runner 离线测试 18 条、SDK 合约测试 4 条。未隐藏或跳过这些警告。
- 发布预检：**143 通过，0 失败，0 警告**。
- 累计 Git diff 已审阅；`git diff --check` 通过。Git 提示 Windows 将 LF 转为 CRLF，
  未执行自动格式转换。已存在的未提交及未跟踪工作保留。

## 安装包核对

使用现有 `dify-plugin.exe` v0.5.5 从 76 文件允许清单暂存目录打包，未直接打包整个源码目录。

- 完整路径：`C:\Users\fangd\Workspace\CodeX\Dify\DIFY插件\moyu_ai_provider-0.0.7-local-test.difypkg`
- 包内发布版本：**0.0.7**，不是仅根据文件名推断。
- 大小：**198478 字节**。
- SHA256：`e749e0798512d8b63ae94aaddeaa914683782c15df1e1cad760ba2d9cb69c3ff`
- 解包目录：`C:\Users\fangd\Workspace\CodeX\Dify\DIFY插件\moyu-0.0.7-local-test-unpacked`
- 包内共 **76 文件、58 个 LLM YAML、4 个 Embedding YAML、0 个 Rerank 文件**，
  与 0.0.6 的文件及模型注册范围完全一致，没有额外历史 YAML。
- 包内每个文件与当前批准源码逐字节一致；ZIP CRC、重复条目和符号链接检查通过。
- 工具标记仅存在于 qwen3.6-plus，恰为获准两个标记；无 multi-tool-call。
- LLM 适配器 SHA256：`7430fbe87d779174c7a787a78521fcb43e7459dec6310e48774559f519cfaf89`。
- 包内保留运行必需文件、中英文 README、MIT LICENSE、PRIVACY.md 和图标。
  不含 `.env`、虚拟环境、测试、脚本、运行报告、内部交接文件；凭据字面量扫描通过。
- 相较旧包，仅五个文件字节不同：manifest、LLM 适配器、qwen3.6-plus YAML、中英文 README。
- 原 `moyu_ai_provider-0.0.6.difypkg` 保留，SHA256 仍为
  `0b7e2f188108f1a8bb09cf786c4964f4bb12bc7162ba1b4b8a1cdd2cb9545980`。

逐文件哈希和核对结果：[local_package_audit_0.0.7.json](../scripts/local_package_audit_0.0.7.json)。

## 待执行验收与未确认事项

操作步骤、加法工具代码及证据表见 [Dify Agent 人工验收说明](DIFY_AGENT_ACCEPTANCE_0.0.7.md)。
在隔离测试工作区安装并核对实际版本 → Function Calling → Moyu 的 qwen3.6-plus →
本地加法工具 → 检查工具请求、执行、结果回传及最终回答 → 双站分别验收 → 普通聊天回归。
单独看到答案 5 不算工具闭环成功。

- 尚未执行 Dify 安装或 Agent 测试，Dify 版本、策略插件版本、实际运行时 SDK 均为**未知**。
  生产依赖仍为 `dify_plugin>=0.9.0`，不保证 Dify 运行时恰好是本地测试的 0.9.0。
- Cloud 权限/本地插件签名策略可能限制安装；遇到限制先记录，不自动关闭安全策略。
- 未验证其他模型、多工具及所有响应变体；SDK 0.9.0 对 `content=null` 同时缺失 usage
  的工具响应仍有既有兼容风险，不能由本轮含用量的成功响应推断全部兼容。
- 不用适配器的流式 success 日志证明成功：它可能在生成器真正消费前产生。
- 前 10 次请求授权已用完，本阶段新增请求 **0**。未来 Dify 验收需另定请求及费用授权。

没有读取 `.env`，没有修改生产依赖或 Anaconda base，没有提交、推送、创建发布、提交市场，
没有安装到客户环境或自动执行 Dify 测试。到此停止，等待人工验收与后续指示。
