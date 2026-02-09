#!/bin/bash
# Twitter 热点汇总脚本 - 使用新的 cookies

AUTH_TOKEN="f63f57e2115832deb88e79a006668e3e03c564ec"
CT0="bc99fdb2d1dc0d0539cf27fe75b3cd19ba584cfcc99578557833f82cecfdabd67ac2df07186a78e0c0f809e205d106313245fb7ade44ad36b1fb7fdaf07b8f82fc45e8e067f773f46a63214493d5113b"

WEBHOOK_SCRIPT="$HOME/clawd/scripts/discord-webhook.sh"
OUTPUT_DIR="/home/node/memory/twitter-summary"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

MESSAGE="# 🐦 Twitter 热点汇总
**时间:** $TIMESTAMP

"

echo "正在获取 AI 新闻..." && sleep 2
AI_NEWS=$(npx -y @steipete/bird news --ai-only -n 5 --auth-token "$AUTH_TOKEN" --ct0 "$CT0" 2>&1)

if [ -n "$AI_NEWS" ]; then
    MESSAGE="$MESSAGE""## 🤖 AI & 科技
"
    MESSAGE="$MESSAGE""$AI_NEWS"
else
    MESSAGE="$MESSAGE""## 🤖 AI & 科技
暂无数据
"
fi

MESSAGE="$MESSAGE""---
*汇总完成于: $(date '+%Y-%m-%d %H:%M:%S UTC')*"

echo "$MESSAGE" | bash "$WEBHOOK_SCRIPT" /dev/stdin
echo "📤 已发送到 Discord #daily"
