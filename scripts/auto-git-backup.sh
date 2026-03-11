#!/bin/bash
# 自动 Git 备份脚本 - 修正路径

WORKSPACE="/home/node/.openclaw/workspace"
cd "$WORKSPACE" || exit 1

# 检查是否有变更
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ 没有变更，无需提交"
    exit 0
fi

# 添加所有变更
git add -A

# 提交
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S UTC')
COMMIT_MSG="Auto-backup: $TIMESTAMP"

git commit -m "$COMMIT_MSG"

# 推送
git push origin $(git branch --show-current) 2>&1

echo "✅ 已备份到 GitHub: $TIMESTAMP"
