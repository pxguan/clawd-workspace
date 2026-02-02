#!/bin/bash
# 自动 Git 备份脚本 - 每次更新内存文件时自动提交并推送

WORKSPACE="/home/node/clawd"
cd "$WORKSPACE" || exit 1

# 检查是否有变更
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ 没有变更，无需提交"
    exit 0
fi

# 添加所有变更
git add -A

# 提交（自动生成提交信息）
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S UTC')
COMMIT_MSG="Auto-commit: $TIMESTAMP"

git commit -m "$COMMIT_MSG"

# 推送到远程（需要配置 GitHub 认证）
git push origin main

echo "✅ 已备份到 GitHub: $TIMESTAMP"
