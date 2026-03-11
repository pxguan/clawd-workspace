#!/bin/bash
# 新闻视频制作脚本 - 更新路径

WORKDIR="/home/node/.openclaw/workspace/memory/news-video"
TWITTER_DIR="/home/node/.openclaw/workspace/memory/twitter-summary"
mkdir -p "$WORKDIR"

LATEST_TWITTER=$(ls -t "$TWITTER_DIR"/*.md 2>/dev/null | head -1)

# ... 其余逻辑保持不变
echo "✅ 新闻视频脚本路径已更新"
