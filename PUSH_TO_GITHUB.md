# 推送到 GitHub —— 3 步操作说明

> 状态：本地仓库已初始化并完成首次提交（commit `00abc98`，26 个文件 / 4,652 行）。
> 只差「在 GitHub 上建一个空仓库」+「git push」两步。

---

## 第 1 步：在 GitHub 建空仓库（约 30 秒）

1. 打开 https://github.com/new
2. **Repository name** 填：

   ```
   overseas-program-dataset
   ```

3. **Description** 填（可直接复制）：

   ```
   Open dataset of overseas work / working-holiday / internship programs for Chinese students. Passport-first eligibility, official sources, weekly link validation.
   ```

4. 可见性选 **Public**（公开才有简历价值）
5. **不要**勾选 "Add a README file"、"Add .gitignore"、"Choose a license"
   —— 本地已经有这些文件，勾了会产生冲突
6. 点 **Create repository**

---

## 第 2 步：推送

建好后 GitHub 会显示一个页面，忽略页面上所有提示，直接打开 **PowerShell**，
把下面整段粘进去回车（已包含全部命令）：

```powershell
cd "F:\2026-09-17-20-35-22\overseas-program-dataset"
git remote remove origin 2>$null
git remote add origin https://github.com/eddieye1004/overseas-program-dataset.git
git push -u origin main
```

### 会弹窗要你登录

推送时会弹出 **Git Credential Manager** 窗口：

- 选 **Sign in with your browser**（用浏览器登录）
- 浏览器里点 **Authorize**
- 回到 PowerShell，推送会自动完成

> 只有第一次需要登录，之后不用再登。

---

## 第 3 步：验证

推送成功后，访问：

```
https://github.com/eddieye1004/overseas-program-dataset
```

应该能看到 README 首页。然后点顶部 **Actions** 标签页，
会看到名为 **Validate dataset** 的工作流正在运行（或已完成）。

- 绿色勾 = 数据校验通过
- 黄色/红色 = 把日志发我，我来修

---

## 如果推送报错

| 报错信息 | 原因 | 解决 |
|---|---|---|
| `remote: Repository not found` | 仓库名拼错，或没建成 | 回第 1 步确认仓库名完全一致 |
| `failed to push some refs` / `rejected` | 建仓库时勾了 README | 执行 `git pull --rebase origin main` 后再 push |
| `Authentication failed` | 登录失效 | 再执行一次 `git push`，重新走登录弹窗 |
| `Support for password authentication was removed` | 用了密码而非令牌 | 必须用弹窗的浏览器登录方式，不要手输密码 |

---

## 备选：完全不用命令行

如果不想碰终端，也可以在**纯浏览器**里上传：

1. 建好空仓库后，在仓库页点 **uploading an existing file**
2. 把 `overseas-program-dataset` 文件夹里的内容拖进去

**但这条路的代价很大**：浏览器上传会**忽略 `.github` 文件夹**，
导致 CI 自动校验工作流、3 个 Issue 模板、PR 模板**全部丢失**——
而这些恰好是你这个项目"来源可追溯 + 自动化校验"卖点的一半。
所以更推荐上面的命令行方式。

---

## 推送成功后立刻做的一件事

改 GitHub Bio（当前是 `ee student at TGU`，没有任何技术标签）。

访问 https://github.com/settings/profile ，把 **Bio** 改成：

```
EE student @ TGU · building open datasets for Chinese students
```

理由：别人（招生的老师、面试官、路过的开发者）点进你的主页只有约 15 秒耐心，
这 15 秒里他需要立刻知道"这个人在做什么"。`ee student at TGU` 只说明了身份，
没有说明**你在生产什么**。加上后半句，你的项目和你的人设就连起来了。
