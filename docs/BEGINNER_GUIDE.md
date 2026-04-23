# 零基础上线 Dify Marketplace — GitHub Desktop 完整教程

> 适用人群：有 GitHub 账号，但从没真正使用过 Git / GitHub。
> 本教程 **全程用图形界面**（GitHub Desktop 这款官方免费 GUI 工具），
> 不需要你打任何 git 命令。
>
> 总时长约 30–45 分钟（含软件下载安装）。跟着做即可，不要跳步。

---

## 📋 需要准备的东西

1. GitHub 账号 — 你已有 ✅
2. GitHub Desktop（免费 GUI 工具）— 下面会教你装
3. 浏览器（Chrome / Edge 都行）
4. 本插件的成品包：`C:\Users\fangd\Workspace\CURSOR\DIFY插件\moyu_ai_provider-0.0.1.difypkg`
   — 我们已经生成好 ✅

---

## 🗺️ 全流程鸟瞰图

整个上线过程分 6 大阶段：

```text
阶段 ①   安装 GitHub Desktop、登录账号
阶段 ②   安全准备（检查 .gitignore 防止 API Key 泄漏）      ← 最关键！
阶段 ③   把插件源码推到你自己的 GitHub（GitHub Desktop 一键完成）
阶段 ④   在网页上 Fork langgenius/dify-plugins
阶段 ⑤   在网页上把 .difypkg 上传到 fork 里
阶段 ⑥   在网页上发起 Pull Request，等审核
```

---

# 阶段 ① 安装 GitHub Desktop 并登录

## 1.1 下载

浏览器打开 <https://desktop.github.com/>，点绿色按钮 **Download for Windows**。

下载完的文件是 `GitHubDesktopSetup-x64.exe`，双击安装，**全默认**即可，
大约 2 分钟就装完，期间不需要管理员权限。

## 1.2 首次启动 + 登录

启动后会看到欢迎页：

1. 点 **Sign in to GitHub.com**
2. 会跳到浏览器登录 GitHub（输你的用户名 `FDQ-shrimp` 和密码 → 通过两步验证）
3. 浏览器会弹"授权 GitHub Desktop"，点 **Authorize desktop**
4. 浏览器会提示"要在 GitHub Desktop 中打开此链接吗？" → **打开**
5. 回到 GitHub Desktop，会看到 **Configure Git** 页面：
   - Name：**FDQ-shrimp**（已自动填好，保持）
   - Email：**用你 GitHub 账号绑定的那个邮箱**（一定要一致，否则提交作者会显示为陌生人）
   - 点 **Finish**

看到 **"Let's get started!"** 主界面就说明登录成功。

---

# 阶段 ② 安全准备（⚠️ 最关键，绝对不能跳）

## 2.1 为什么这一步关键

你的 `test_01` 目录里有一个 `.env` 文件，里面写着：

- 你的魔芋 AI 真实 API Key（sk-... 开头）
- Dify 本地调试用的 REMOTE_INSTALL_KEY（UUID 格式）

**如果这个文件被推到 GitHub 公开仓库，所有人都能看到你的密钥。**
别人可能用你的 Key 疯狂消耗额度，或冒充你。

> 好消息：我刚才已经在项目里创建了 `.gitignore`，里面写了 `.env`，
> GitHub Desktop 会自动忽略它。下面我们做一次"验货"确保真的生效。

## 2.2 验货步骤

回到 GitHub Desktop，主界面选 **Add an Existing Repository from your hard drive**：

1. 点 **File → Add local repository...**（菜单栏左上角）
2. Local path 点 **Choose...** → 选择：
   `C:\Users\fangd\Workspace\CURSOR\DIFY插件\test_01`
3. 这个目录目前还不是 git 仓库，GitHub Desktop 会提示：
   > This directory does not appear to be a Git repository. Would you like
   > to **create a repository** here instead?
4. 点蓝色链接 **create a repository**
5. 弹出 **Create a repository** 对话框，填写：
   - **Name**：`moyu_ai_provider`（⚠️ 不要有空格和中文）
   - **Description**：`Moyu AI model provider plugin for Dify`
   - **Local path**：已经是 `C:\Users\fangd\Workspace\CURSOR\DIFY插件` 前缀，
     下面的子目录会是 `test_01`。**这个不用管**，GitHub Desktop 只在该目录下
     建 `.git` 子文件夹而已，插件代码不会被移动。
   - **Initialize this repository with a README**：**不要勾**（我们已经有 README.md）
   - **Git ignore**：下拉选 **None**（我们已经有 `.gitignore` 文件，不要让它覆盖）
   - **License**：**None**
6. 点 **Create repository**

## 2.3 确认 .env 被忽略（关键验货）

创建后会进入仓库主视图，左侧列出所有待提交的改动。
**请用眼睛扫一遍左侧文件列表**，按这个清单核对：

**应该看到**（几百个文件）：
- `README.md`, `manifest.yaml`, `privacy.md`
- `main.py`, `provider/moyu.py`, `provider/moyu.yaml`
- `models/llm/llm.py` + 119 个 `models/llm/*.yaml`
- `icon.png`, `requirements.txt`
- `.difyignore`, `.gitignore`, `.env.example`
- `docs/BEGINNER_GUIDE.md`, `docs/PR_BODY.md`, `docs/SUBMISSION_GUIDE.md`,
  `docs/MODEL_AVAILABILITY.md`
- `readme/README_zh_Hans.md`
- `scripts/*.py`, `tests/*.py`, `RELEASE_CHECKLIST.md`

**⚠️ 绝对不能看到**：
- ❌ `.env` （不是 `.env.example`，是单纯的 `.env`）
- ❌ `.pytest_cache/`
- ❌ 任何 `__pycache__/` 目录
- ❌ `test_01.difypkg` 或 `moyu_ai_provider-0.0.1.difypkg`（这些不应在源码仓库）

**如果你看到 `.env` 出现在列表里**，**停下来**立刻联系我处理，不要继续！

如果列表正确，进入下一阶段。

---

# 阶段 ③ 把插件源码推到你自己的 GitHub

## 3.1 第一次提交

在 GitHub Desktop 左下角：

1. **Summary**（必填）：`Initial commit: Moyu AI model provider plugin v0.0.1`
2. **Description**（可选）留空
3. 点下方蓝色按钮 **Commit to main**

左侧文件列表会清空，顶部出现 "0 changed files"。
此时改动只是提交到了**本地**，还没上传 GitHub。

## 3.2 发布到 GitHub

顶部会出现蓝色按钮 **Publish repository**，点它：

1. 弹出 **Publish Repository** 对话框
2. **Name**：`moyu_ai_provider`（保持）
3. **Description**：`Moyu AI model provider plugin for Dify`
4. **Keep this code private**：**一定要取消勾选**（必须公开，否则 Dify 审核看不到）
5. **Organization**：保持 **None**（发到你自己账号下）
6. 点 **Publish Repository**

几秒钟后，右上角会出现 **"View on GitHub"** 按钮 — 点它，浏览器会打开：

```text
https://github.com/FDQ-shrimp/moyu_ai_provider
```

**这就是你的插件源码仓库地址**。记下这个 URL，一会儿 PR 要用。

## 3.3 再次肉眼复查（双保险）

在 GitHub 网页上打开你刚发布的仓库：

1. 看文件列表 — **不能** 有 `.env`、`.pytest_cache`、`test_01.difypkg`
2. 点 `.gitignore` 文件 — 里面应该有一行 `.env`
3. 打开 `manifest.yaml` — 确认 `author: FDQ-shrimp`

都对 → 可以进入阶段 ④。
**如果发现 `.env` 被推上去了**：
- 立刻登录 moyu.ai 撤销那个 API Key
- 告诉我，我教你清理 git 历史并重新发布

---

# 阶段 ④ Fork 官方仓库 `langgenius/dify-plugins`

全程在浏览器里做：

## 4.1 Fork

1. 登录 GitHub（已登录则跳过），浏览器打开：
   <https://github.com/langgenius/dify-plugins>
2. 右上角点 **Fork** 按钮
3. 在 Fork 对话框中：
   - **Owner**：`FDQ-shrimp`（你的账号）
   - **Repository name**：保持 `dify-plugins`
   - **Copy the `main` branch only**：**保持勾选**（只 fork 主分支就够）
4. 点 **Create fork**

5 秒后你会跳到自己账号下的 fork 页面：
`https://github.com/FDQ-shrimp/dify-plugins`

页面顶部会显示 **forked from langgenius/dify-plugins**。

---

# 阶段 ⑤ 把 `.difypkg` 上传到 fork 里

> 这是整个流程里最容易出错的一步，认真按顺序做。

## 5.1 创建目录结构

还在你 fork 的 dify-plugins 页面（`https://github.com/FDQ-shrimp/dify-plugins`）：

1. 看到文件列表上方有 **Add file ▼** 按钮，点它 → **Create new file**
2. 页面顶部会出现一个路径编辑框，像面包屑：
   `dify-plugins / Name your file...`
3. 在 "Name your file..." 输入框里**逐字符输入**：
   ```text
   FDQ-shrimp/moyu_ai_provider/.gitkeep
   ```
   输入 `/` 时，前面的部分会自动变成面包屑目录，例如：
   ```text
   dify-plugins / FDQ-shrimp / moyu_ai_provider / .gitkeep
   ```
   输入完整后应该看到三级面包屑，最后一段是 `.gitkeep`
4. **文件正文区域留空**（完全不写任何字符）
5. 页面下拉到底部的 **Commit changes** 区域：
   - Commit message 框会自动填好，保持即可：`Create .gitkeep`
   - 选择 **Commit directly to the `main` branch.**
6. 点绿色按钮 **Commit changes**

现在你的 fork 里有了空目录 `FDQ-shrimp/moyu_ai_provider/`（里面只有一个空的 `.gitkeep` 文件占位）。

## 5.2 上传 `.difypkg`

1. 进入刚创建的目录：浏览器地址栏会是：
   `https://github.com/FDQ-shrimp/dify-plugins/tree/main/FDQ-shrimp/moyu_ai_provider`
   （如果看不到，可以在 fork 根目录点 `FDQ-shrimp` → 再点 `moyu_ai_provider`）
2. 点 **Add file ▼** → **Upload files**
3. 打开**文件资源管理器**，导航到：
   `C:\Users\fangd\Workspace\CURSOR\DIFY插件\`
4. 找到文件 `moyu_ai_provider-0.0.1.difypkg`（大小约 209 KB）
5. **拖拽** 这个文件到网页上的虚线框里（或点 "choose your files" 选择）
6. 上传完成后页面下方：
   - Commit message：`Add moyu_ai_provider v0.0.1`
   - Extended description（可选）填：
     `First submission to Dify Marketplace. Source: https://github.com/FDQ-shrimp/moyu_ai_provider`
   - 选 **Commit directly to the `main` branch.**
7. 点绿色按钮 **Commit changes**

## 5.3 验证结构

浏览器地址栏访问：
`https://github.com/FDQ-shrimp/dify-plugins/tree/main/FDQ-shrimp/moyu_ai_provider`

你应该看到 2 个文件：
- `.gitkeep`  (0 Bytes) — 占位，可留可删
- `moyu_ai_provider-0.0.1.difypkg`  (~209 KB)

**（可选）清理 `.gitkeep`**：
点 `.gitkeep` → 右上角铅笔旁边的垃圾桶图标 → **Commit changes** → **Commit directly to main**。
保留不删也**不影响审核**。

---

# 阶段 ⑥ 发起 Pull Request

## 6.1 进入 PR 发起页

1. 浏览器打开你 fork 的主页：`https://github.com/FDQ-shrimp/dify-plugins`
2. 顶部会出现黄色横条：
   > This branch is 2 commits ahead of langgenius:main.
3. 横条右侧有 **Contribute ▼** 下拉按钮，点它 → **Open pull request**

## 6.2 确认分支对接方向

打开的 PR 页面顶部会显示：

```text
base repository: langgenius/dify-plugins   base: main
       ←  →
head repository: FDQ-shrimp/dify-plugins   compare: main
```

**一定要确认左侧 base repository 是 `langgenius/dify-plugins`**（官方），
**不是** `FDQ-shrimp/dify-plugins`。如果不对，点下拉框改过来。

## 6.3 填写标题

Title 输入框填（整段复制过去）：

```text
New: add Moyu AI model provider plugin v0.0.1 (FDQ-shrimp/moyu_ai_provider)
```

## 6.4 填写正文（重要）

1. 下面大的描述框 GitHub 会自动塞入一段 **空模板**（官方 PR 模板）
2. 在框内 **按 Ctrl+A 全选 → Delete 删除干净**
3. 打开电脑上的文件：
   `C:\Users\fangd\Workspace\CURSOR\DIFY插件\test_01\docs\PR_BODY.md`
   （用 VS Code / 记事本 / Cursor 都行）
4. Ctrl+A 全选，Ctrl+C 复制里面的**全部内容**
5. 回到浏览器 PR 描述框，Ctrl+V 粘贴

## 6.5 粘贴后再检查 2 个地方

- **第 1 节 Repository URL** 应该是：
  `https://github.com/FDQ-shrimp/moyu_ai_provider`
  （如果不是，手动改一下）
- 下半部分 **勾选框** 应该都已经是 `[x]` 状态（GitHub 会自动渲染成勾）

## 6.6 提交 PR

**拉到页面底部**，确认：
- Reviewers / Assignees / Labels 都**不要填**，让 Dify 官方自动处理
- 默认 **Create pull request** 按钮（不是 Draft）

点蓝色按钮 **Create pull request**。

## 6.7 提交成功

PR 一旦建立，你会看到：

- PR 编号（例如 #2200）
- 自动化机器人 `github-actions` 会在 1–3 分钟内跑完检查，大概会打上
  `no-lint` / `plugin-pr` / 之类的标签
- 可能会收到评论要求签 **CLA (Contributor License Agreement)**
  — 点评论里的链接，登录 → 勾"I agree" → 点提交，完成

把这条 PR 的 URL 复制下来，类似：
```text
https://github.com/langgenius/dify-plugins/pull/<编号>
```
发给我，我可以帮你盯评论动态。

---

# 阶段 ⑦ 后续跟进

## 时间线

| 时间 | 会发生什么 |
|---|---|
| T+0 | PR 已提交 |
| T+几分钟 | 机器人自动打标签、可能要签 CLA |
| T+1 周内 | 官方 reviewer 开始人工 review |
| 若 reviewer 留言 | 你 **14 天内** 要回复 / 修改，否则 PR 被标 stale |
| 若 30 天没回复 | PR 关闭，需要重开一个新的 |
| 审核通过 | 合并进 `main`，插件**自动上架**到 marketplace.dify.ai |

## 如何回复 reviewer

GitHub 会发邮件通知，也可以随时回到 PR 页面看评论。
如果要改代码：

1. 回到 Cursor 改源码
2. 跑 `python scripts/preflight_check.py` 确保预检仍全绿
3. 重新打包：在 `CURSOR\DIFY插件` 目录跑
   `.\dify-plugin.exe plugin package ./test_01`
4. 复制：`Copy-Item test_01.difypkg moyu_ai_provider-0.0.1.difypkg -Force`
   （如果只是小修小补，保持 0.0.1；较大改动则改 manifest.yaml 里的 version 为 0.0.2）
5. 回到 fork 的 `FDQ-shrimp/moyu_ai_provider/` 目录，**直接把新包拖进去
   覆盖**（GitHub 会识别为 Update commit，PR 会自动更新）
6. 在 PR 评论里回复 reviewer 说明修改了什么

## 完成后

审核通过合并的那一刻，你的插件就**自动出现**在 Dify 桌面客户端的
"安装模型供应商"面板里（也就是你截图看到的那个列表），和 Anthropic、
Azure OpenAI 那些一起展示。全球所有 Dify 用户都能点击 **安装**。

---

# ❓ 常见问题

### Q1: GitHub Desktop 登录一直失败？
答：先在浏览器登录 github.com 确认账号能进去；再确认没开阻止 GitHub 的代理/防火墙；如还不行，可以在 GitHub Desktop 里选 **File → Options → Sign in with your browser**。

### Q2: 上传 `.difypkg` 时提示文件太大？
答：GitHub 单文件上限 25 MB（网页上传），我们的包只有 209 KB，远远不到。如果真报这个错，先在资源管理器确认文件大小。

### Q3: 我 Fork 后发现目录结构不对想重来？
答：不怕。进 `https://github.com/FDQ-shrimp/dify-plugins/settings`，拉到最底 **Danger Zone** → **Delete this repository**，删掉后重新 fork 一次即可。

### Q4: 如果 PR 里不小心把 `.env` 推上去了？
答：**立刻**：
1. 登录 moyu.ai 作废那把 API Key
2. 关掉这个 PR 和你 fork 的 dify-plugins（或者至少删掉 `.env` 文件再提交）
3. 回来告诉我，我教你清理 git 历史

### Q5: 审核人说我的插件名和已有的重复？
答：不会。目前 Marketplace 里没有 Moyu AI 供应商。

### Q6: 审核人让我补什么东西？
答：常见要求：
- 加 LICENSE 文件（比如 MIT）
- README 里加截图
- 把某个模型的 YAML 元数据改正确
直接改完再传新包，PR 会自动更新。
