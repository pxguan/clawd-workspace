#!/bin/bash
# Twitter 汇总发送助手

OUTPUT_FILE="$1"

if [ -z "$OUTPUT_FILE" ] || [ ! -f "$OUTPUT_FILE" ]; then
    echo "用法: $0 <汇总文件路径>"
    exit 1
fi

# 提取北京时间
BEIJING_TIME=$(grep "北京时间" "$OUTPUT_FILE" | head -1 | sed 's/.*\([0-9][0-9]:[0-9][0-9]\) 北京时间.*/\1/')

# 读取完整内容
CONTENT=$(cat "$OUTPUT_FILE")

# 输出到 stdout，由 Moltbot 捕获并发送
echo "📊 **Twitter 热点汇总** ($BEIJING_TIME 北京时间)"
echo ""
echo "$CONTENT"
