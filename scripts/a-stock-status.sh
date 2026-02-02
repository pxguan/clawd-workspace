#!/bin/bash
# 查看最新推荐结果

STATE_FILE="/home/node/clawd/memory/a-stocks/latest_recommendations.json"

if [ -f "$STATE_FILE" ]; then
    echo "📊 最新A股推荐:"
    echo "─────────────────────────────"
    cat "$STATE_FILE"
    echo ""
    echo "─────────────────────────────"
    echo "更新时间: $(stat -c %y "$STATE_FILE" 2>/dev/null | cut -d'.' -f1)"
else
    echo "暂无推荐数据（等待交易时间）"
fi
