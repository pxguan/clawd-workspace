#!/bin/bash
# Twitter 热点汇总脚本 - 使用 Webhook 发送

export AUTH_TOKEN="b5a2d38cc4cb703d373ff230ad19a16487cb099e"
export CT0="620a150990b7ceb46977dfead8bd74fa8c7f5cd102c157c3993cfbc7c750c27b435821384645e91ef6e4fd6de0ad1a2072c07743a96cdced1f0af09afbe11dacec898124358280eb5ab6fa1b4fa6dab0"

WEBHOOK_SCRIPT="$HOME/clawd/scripts/discord-webhook.sh"
OUTPUT_DIR="$HOME/node/memory/twitter-summary"
mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="$OUTPUT_DIR/tweets_$TIMESTAMP.md"

echo "# Twitter 热点汇总" | tee "$OUTPUT_FILE"
echo "**时间:** $(date '+%Y-%m-%d %H:%M:%S UTC') | $(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S 北京时间')" | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "## 🤖 AI & 科技" | tee -a "$OUTPUT_FILE"
echo '```' | tee -a "$OUTPUT_FILE"
echo "正在获取 AI & 科技趋势..." && sleep 2
timeout 30 npx -y @steipete/bird news --ai-only -n 10 2>&1 | grep -E "\[AI ·|Technology|Tech|科技|人工智能" >> "$OUTPUT_FILE" || echo "无数据" >> "$OUTPUT_FILE"
sleep 1
echo '```' | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "## 📈 股市 & 经济" | tee -a "$OUTPUT_FILE"
echo '```' | tee -a "$OUTPUT_FILE"
echo "正在获取股市与经济新闻..." && sleep 2
timeout 30 npx -y @steipete/bird news --ai-only -n 15 2>&1 | grep -iE "Bitcoin|Ethereum|Crypto|Stock|Market|DOW|NASDAQ|Gold|Silver|Plunges|Drops|Rally|Bank|Fed|Economy|经济|股市|比特币|黄金|白银" >> "$OUTPUT_FILE" || echo "无数据" >> "$OUTPUT_FILE"
sleep 1
echo '```' | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "## 🏛️ 政治 & 新闻" | tee -a "$OUTPUT_FILE"
echo '```' | tee -a "$OUTPUT_FILE"
echo "正在获取政治与新闻..." && sleep 2
timeout 30 npx -y @steipete/bird news --news-only -n 10 2>&1 | head -40 >> "$OUTPUT_FILE" || echo "无数据" >> "$OUTPUT_FILE"
sleep 1
echo '```' | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "## 🔥 搜索热门关键词" | tee -a "$OUTPUT_FILE"
echo '```' | tee -a "$OUTPUT_FILE"
echo "正在搜索 AI 相关推文..." && sleep 3
timeout 40 npx -y @steipete/bird search "AI OR artificial intelligence OR OpenAI OR Claude OR GPT" -n 3 2>&1 | head -20 >> "$OUTPUT_FILE" || echo "无数据" >> "$OUTPUT_FILE"
echo '```' | tee -a "$OUTPUT_FILE"
echo "" | tee -a "$OUTPUT_FILE"

echo "---" | tee -a "$OUTPUT_FILE"
echo "*汇总完成于: $(date '+%Y-%m-%d %H:%M:%S UTC') | $(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S 北京时间')*" | tee -a "$OUTPUT_FILE"

echo "✅ 热点汇总已保存到: $OUTPUT_FILE"
echo "📊 北京时间: $(date -d '+8 hour' '+%H:%M:%S')"

# 使用 Webhook 发送
cat "$OUTPUT_FILE" | bash "$WEBHOOK_SCRIPT" /dev/stdin
echo "📤 已发送到 Discord #daily"
