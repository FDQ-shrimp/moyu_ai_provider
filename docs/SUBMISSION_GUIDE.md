# 魔芋 AI 模型供应商插件 — Dify Marketplace 上线全流程

> 目标：把当前这个 `moyu_ai_provider` 插件提交到
> [marketplace.dify.ai](https://marketplace.dify.ai/)，合并后自动出现在
> Dify 的"安装模型供应商"列表里。
>
> 本文档假设你已经完成开发与本地验证，只剩下 **提交审核** 这一步。
> 所有命令都是 Windows PowerShell，如果你用的是 git bash / cmd
> 可直接替换为等价命令。

---

## 0. 产物清单（我方已准备好的东西）

| 文件 / 目录 | 位置 | 作用 |
|---|---|---|
| `moyu_ai_provider-0.0.1.difypkg` | `CURSOR\DIFY插件\` | **上传到 dify-plugins 的二进制包** |
| `docs/PR_BODY.md` | 本插件项目内 | PR 描述文案（复制到 GitHub PR 编辑器） |
| `docs/MODEL_AVAILABILITY.md` | 本插件项目内 | 119 个模型实测可用性报告 |
| `docs/SUBMISSION_GUIDE.md` | 本文件 | 本文档 |
| `RELEASE_CHECKLIST.md` | 项目根 | 发布前 checklist |
| `README.md`, `readme/README_zh_Hans.md`, `privacy.md` | 项目根 | 已打进 `.difypkg`，无需单独提交 |

> ⚠ `docs/` 目录本身通过 `.difyignore` 排除在 `.difypkg` 之外，
> **不会**被打进用户端包，只存在于你的 GitHub 源码仓库里供审核人参考。

---

## 1. 关键概念（读 3 分钟再动手）

Dify Marketplace 的"发布"流程是 **GitHub PR 流程**：

```text
你的 GitHub 账号
 ├─ 源码仓库 moyu_ai_provider      ← 步骤 A：你先把源码公开到这里
 │    （审核人顺着 PR 里的 Repository URL 来看你的源码）
 │
 └─ fork 的 langgenius/dify-plugins  ← 步骤 B：你在这里提交 .difypkg
      └─ FDQ-shrimp/
           └─ moyu_ai_provider/
                └─ moyu_ai_provider-0.0.1.difypkg
                         ↓ 发起 PR 合并回上游
             langgenius/dify-plugins (官方仓库)
                         ↓ 合并进 main
             marketplace.dify.ai 自动上架
```

所以你一共要操作 **两个 GitHub 仓库**：自己的源码仓库 + fork 的 dify-plugins。

---

## 2. 步骤 A：把插件源码公开到你自己的 GitHub

官方 PR 模板里 **必填 Repository URL**，reviewer 会进你的源码仓库对照审。

### A-1. 在 GitHub 网页上创建一个新仓库

1. 打开 <https://github.com/new>
2. Repository name 填：`moyu_ai_provider`
3. Description 填：`Moyu AI model provider plugin for Dify`
4. **Public**（必须公开，不然审核看不到）
5. **不要** 勾 "Add a README" / "Add .gitignore" / "Choose a license"（我们本地已经有了）
6. 点 Create repository

GitHub 会给你一个地址：`https://github.com/FDQ-shrimp/moyu_ai_provider`

### A-2. 本地初始化 + 首次推送

打开 PowerShell，定位到插件根目录：

```powershell
cd C:\Users\fangd\Workspace\CURSOR\DIFY插件\test_01
```

首次配置 git 身份（如果你之前从没用过 git）：

```powershell
git config --global user.name  "FDQ-shrimp"
git config --global user.email "你的邮箱@example.com"
```

> 邮箱要和 GitHub 账号绑定的邮箱一致，否则提交人头像不会显示成你。

初始化仓库 + 提交：

```powershell
git init -b main
git add .
git status     # 肉眼检查：.env 必须不出现在清单里
git commit -m "Initial commit: Moyu AI model provider plugin v0.0.1"
```

> 如果 `git status` 里看到了 `.env`，**立刻停止**，先检查项目根目录的
> `.gitignore` 是否有 `.env` 这一行。我们已经在 `.difyignore` 里排除了，
> 但 git 用的是 `.gitignore`，两者不是同一个文件。检查命令：
> ```powershell
> Select-String -Path .gitignore -Pattern "^\.env"
> ```
> 如果没有匹配，先执行：
> ```powershell
> Add-Content -Path .gitignore -Value "`n.env`n.env.*`n"
> git rm --cached .env 2>$null
> git add .gitignore
> git commit --amend --no-edit
> ```

关联远端并推送：

```powershell
git remote add origin https://github.com/FDQ-shrimp/moyu_ai_provider.git
git push -u origin main
```

第一次推送时 GitHub 会弹出登录窗口，用 Personal Access Token（在
<https://github.com/settings/tokens> 申请一个 classic token，勾 `repo` 权限）
作为密码即可。

### A-3. 打 v0.0.1 标签（强烈推荐）

让审核人一眼能定位到"本次提交的 PR 对应哪个代码快照"：

```powershell
git tag -a v0.0.1 -m "Release v0.0.1 — first marketplace submission"
git push origin v0.0.1
```

到这里步骤 A 完成，你有了公开的源码仓库 URL：
`https://github.com/FDQ-shrimp/moyu_ai_provider`

---

## 3. 步骤 B：fork dify-plugins 并上传 `.difypkg`

### B-1. Fork 官方仓库

1. 打开 <https://github.com/langgenius/dify-plugins>
2. 点右上角 **Fork** 按钮
3. Owner 选 `FDQ-shrimp`，Repository name 保持 `dify-plugins`
4. **不要** 勾 "Copy the main branch only"（保持默认即可）
5. 点 Create fork

你现在拥有：`https://github.com/FDQ-shrimp/dify-plugins`

### B-2. 在 fork 里创建目录和上传包（网页版最简单）

1. 进入你 fork 的 dify-plugins 仓库页面
2. 点 **Add file → Create new file**
3. 在文件名输入框里输入：
   ```
   FDQ-shrimp/moyu_ai_provider/.gitkeep
   ```
   （输入 `/` 会自动创建嵌套目录；`.gitkeep` 是一个占位空文件）
4. 正文留空，翻到底部
5. Commit message 填：`Create folder for FDQ-shrimp/moyu_ai_provider`
6. 选 **Commit directly to the main branch** → **Commit new file**

现在你在 fork 里有了 `FDQ-shrimp/moyu_ai_provider/` 目录。

### B-3. 上传 `.difypkg`

1. 进入刚创建的 `FDQ-shrimp/moyu_ai_provider/` 目录
2. 点 **Add file → Upload files**
3. 把 `C:\Users\fangd\Workspace\CURSOR\DIFY插件\moyu_ai_provider-0.0.1.difypkg`
   从资源管理器 **拖进** 上传区
4. Commit message 填：`Add moyu_ai_provider v0.0.1`
5. 选 **Commit directly to the main branch** → **Commit changes**

可选清理：上一步留的 `.gitkeep` 可以删掉（编辑 `.gitkeep` 文件 → 右上角小垃圾桶图标），
保留也不影响审核。

### B-4. 确认目录结构

打开 `https://github.com/FDQ-shrimp/dify-plugins/tree/main/FDQ-shrimp/moyu_ai_provider`
应该看到：

```text
FDQ-shrimp/
└── moyu_ai_provider/
    └── moyu_ai_provider-0.0.1.difypkg   (~213 KB)
```

---

## 4. 步骤 C：提交 Pull Request

### C-1. 发起 PR

1. 回到 `https://github.com/FDQ-shrimp/dify-plugins`
2. 顶部应该看到黄色横条：
   `This branch is 1 commit ahead of langgenius:main`
3. 右边点 **Contribute → Open pull request**
4. PR 页面确认：
   - base repository: `langgenius/dify-plugins` base: `main`
   - head repository: `FDQ-shrimp/dify-plugins` compare: `main`
5. Title 填：
   ```text
   New: add Moyu AI model provider plugin v0.0.1 (FDQ-shrimp/moyu_ai_provider)
   ```

### C-2. 粘贴 PR 正文

1. GitHub 会自动把 `.github/pull_request_template.md` 的空模板塞进描述框
2. **全选删除** 那段空模板
3. 打开本仓库的 `docs/PR_BODY.md`
4. 全选复制里面的内容（**跳过最顶上 `<!-- ... -->` 注释块也行，带上也行**）
5. 粘贴到 GitHub 的 PR 描述框
6. 检查第 1 节 **Repository URL** 是否正确（`https://github.com/FDQ-shrimp/moyu_ai_provider`）
7. 所有 `- [x]` checkbox 会在 GitHub 上自动渲染成勾选状态

### C-3. 提交

1. 点页面底部 **Create pull request**
2. PR 提交后会出现在
   <https://github.com/langgenius/dify-plugins/pulls>
3. 自动化 bot（比如 CLA / check-label）会在几分钟内给你打标签。如果
   bot 留言要你"sign CLA"，按它给的链接签一次名即可。

---

## 5. 步骤 D：审核与跟进

### 时间线

| 节点 | 说明 |
|---|---|
| T + 0 | PR 提交完成 |
| T + 7 天内 | reviewer 开始看（first-come first-reviewed） |
| T + 14 天 | 如果 reviewer 留了评论但你一直没回 → 被标 stale（可再激活） |
| T + 30 天 | 仍未处理 → PR 关闭，必须重新开一个 |

### 常见 reviewer 要求（提前心里有数）

1. **Author 字段与你 GitHub 用户名一致**
   ✅ 我们已设为 `FDQ-shrimp`
2. **Icon 是自定义的，不是占位符**
   ✅ 已用魔芋 AI 的 PNG logo
3. **README 有完整的配置步骤、凭证获取方式、支持模型列表**
   ✅ `README.md` 已包含
4. **privacy.md 明确列出收集/传输给第三方的数据种类**
   ✅ 已有，并在 PR 正文第 6 节复述
5. **插件在 Community Edition 和 Cloud 都能跑**
   ✅ 你已在本地 Community 版跑通并提供截图
6. **如果不是"已有插件的简单改名"，要说明差异化价值**
   ✅ Moyu AI 是之前 Marketplace 没有的供应商

### 如果 reviewer 提意见

通常会以 GitHub PR 评论的形式出现。你每次修改后：

```powershell
# 在插件源码仓库里改代码 → 重新打包
cd C:\Users\fangd\Workspace\CURSOR\DIFY插件
.\dify-plugin.exe plugin package ./test_01
Copy-Item test_01.difypkg moyu_ai_provider-0.0.1.difypkg -Force

# 小版本号递增（可选，但推荐）
# 比如修正某个 YAML 后，把 manifest.yaml 里的 version 改为 0.0.2
# 重新打包命名为 moyu_ai_provider-0.0.2.difypkg
```

然后把**新包**推到 fork 的同一目录（可以保留旧包或覆盖），那条 PR 会
自动把新 commit 纳入审核，不需要另开 PR。

---

## 6. 提交前最后 5 分钟清单（可选但强烈建议）

```powershell
cd C:\Users\fangd\Workspace\CURSOR\DIFY插件\test_01

# ① 静态预检应全绿
python scripts\preflight_check.py

# ② 单测应全过
python -m pytest tests -q

# ③ 打包后包体检查：无 .env / scripts / tests / docs 泄漏
python -c "import zipfile; z=zipfile.ZipFile(r'..\moyu_ai_provider-0.0.1.difypkg'); names=z.namelist(); leaks=[n for n in names if n.startswith(('.env','scripts/','tests/','docs/','.pytest_cache/','__pycache__/')) or n.endswith('.pyc')]; print('entries:', len(names)); print('LEAKS:', leaks or 'none')"

# ④ 肉眼检查 manifest.yaml 里的 author 是 FDQ-shrimp
python -c "import zipfile; z=zipfile.ZipFile(r'..\moyu_ai_provider-0.0.1.difypkg'); print(z.read('manifest.yaml').decode('utf-8'))"
```

以上四项都 OK 才能去点那个 Create pull request。

---

## 7. 上线后的维护义务（官方要求）

审核通过合并后：

- **有用户报 bug 或提 feature request 时要响应**（通过 Issue / PR）
- **Dify SDK 有大版本变动时要配合迁移**（官方会提前发通知）
- **在 Marketplace Beta 期间避免 breaking change**（尽量保持凭证字段兼容）
- 发新版本只需要再开一个 PR，Submission Type 勾 "Version update"，
  `.difypkg` 名字里带新版本号即可。

---

完成以上流程后，你的插件就会出现在 Dify 的"安装模型供应商"列表里，
与截图里那些 Anthropic / Bedrock / Azure OpenAI 等供应商并列。
