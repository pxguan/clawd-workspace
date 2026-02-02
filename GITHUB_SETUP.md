# GitHub 自动推送配置

## 仓库信息

**仓库地址:** https://github.com/pxguan/clawd-workspace

## 认证方式

需要配置以下其中一种：

### 方式 1: SSH（推荐）

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "jarvis@clawd.local" -f ~/.ssh/id_ed25519 -N ""

# 查看公钥
cat ~/.ssh/id_ed25519.pub
# 复制公钥到 GitHub: Settings → SSH and GPG keys → New SSH key

# 测试连接
ssh -T git@github.com

# 更新远程地址为 SSH
git remote set-url origin git@github.com:pxguan/clawd-workspace.git
```

### 方式 2: Personal Access Token

1. 去 GitHub 创建 token: https://github.com/settings/tokens
2. 选择 `repo` 权限
3. 保存 token

```bash
# 设置 token（替换 YOUR_TOKEN）
git remote set-url origin https://YOUR_TOKEN@github.com/pxguan/clawd-workspace.git

# 或使用环境变量
export GIT_ASKPASS=/home/node/clawd/scripts/git-askpass.sh
```

### 方式 3: Git Credential Helper

```bash
# 配置 credential helper
git config --global credential.helper store

# 第一次 push 时输入用户名和 token
```

## 自动推送

配置好认证后，运行：

```bash
/home/node/clawd/scripts/auto-git-backup.sh
```

或设置定时任务自动执行。
