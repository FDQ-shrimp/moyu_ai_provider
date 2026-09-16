# 魔芋AI 0.0.6 — Dify Marketplace 发布准备指南

本文档用于准备现有 Marketplace 插件 `fdq-shrimp/moyu_ai_provider` 的
`0.0.6` 版本更新。它不授权自动提交、推送或发布；所有外部写操作都应由
发布者最终确认。

## 1. 固定发布信息

| 字段 | 值 |
|---|---|
| 发布类型 | Version update |
| Author | `fdq-shrimp` |
| Plugin name | `moyu_ai_provider` |
| Version | `0.0.6` |
| Source repository | <https://github.com/FDQ-shrimp/moyu_ai_provider> |
| Contact | `fangdaq10@163.com` |
| License | MIT |
| Privacy document | `PRIVACY.md` |
| Risk level | Medium risk |

正式包必须保持 `fdq-shrimp/moyu_ai_provider` 身份，不能使用本地测试版的
preview 名称，否则 Marketplace 会把它识别为另一个插件。

## 2. 发布前顺序

1. 让公开源码仓库的默认分支与准备打包的 `0.0.6` 源码完全一致。
2. 确认 `manifest.yaml` 同时满足：
   - `version` 与 `meta.version` 都是 `0.0.6`；
   - `privacy: PRIVACY.md`；
   - 正确的 `repo` 与 `contact`；
   - author/name 仍为 `fdq-shrimp/moyu_ai_provider`。
3. 运行离线测试与发布前自检：

   ```powershell
   python -m pytest tests -q
   python .\scripts\preflight_check.py
   ```

4. 使用安全的 staging 目录，仅复制运行和商店展示所需文件后打包。
5. 检查包内根目录精确包含大写 `PRIVACY.md`，并确认没有 `.env`、密钥、
   Git 元数据、测试、脚本、日志、缓存或内部交接文档。
6. 在干净的 Dify 工作区安装正式 `0.0.6` 包，完成国内站、海外站及
   `0.0.5 → 0.0.6` 升级兼容测试。
7. 更新 `docs/PR_BODY.md` 中的最终测试数字和包检查结果。
8. 在 `langgenius/dify-plugins` 的发布分支中只新增一个文件：

   ```text
   fdq-shrimp/moyu_ai_provider/moyu_ai_provider-0.0.6.difypkg
   ```

9. PR 正文使用英文，选择 **Version update** 和 **Medium risk**。

## 3. 为什么是 Medium risk

插件会把用户主动提交的提示词、对话、Embedding 文本、工具定义及受支持的
多模态输入发送到用户所选的外部模型服务，因此按当前 Marketplace 规则属于
Medium risk。插件只允许两个固定 HTTPS 站点，不提供自由填写的 URL，也不
执行用户控制的代码、命令、SQL、浏览器操作或本地文件访问。

## 4. 不得进入包或仓库的内容

- `.env`、真实 API Key、Dify 调试 Key；
- 含凭据的命令记录、日志或截图；
- `.git`、虚拟环境、缓存、IDE 配置；
- `AGENTS.md`、`CODEX_HANDOFF.md`、内部 CI 排错文件；
- 临时 probe 报告中的账号或请求标识。

API Key、GitHub 密码、Personal Access Token 和 Dify 登录凭据都不应写入
源码、PR 正文、Issue 或聊天转发内容。

## 5. 最终交付物

- 与默认分支一致的公开源码；
- `moyu_ai_provider-0.0.6.difypkg`；
- 已更新测试数字的英文 PR 正文；
- 包检查结果和 SHA256；
- 安装、双站与升级测试记录。
