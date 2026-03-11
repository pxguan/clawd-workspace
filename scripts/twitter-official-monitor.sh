#!/bin/bash
#
# Twitter 官方账号监控脚本
# 安全特性：
# - 每小时检查一次（避免限流）
# - 去重逻辑（只推送新内容）
# - 无内容不推送
# - 使用 bird CLI（建议小号）
#

# 配置
TWITTER_ACCOUNTS=(
    "@AnthropicAI"
    "@OpenAI"
    "@GoogleDeepMind"
    "@MetaAI"
    "@MistralAI"
)

STATE_DIR="/home/node/memory/twitter-monitor"
TRIGGER_FILE="/home/node/memory/twitter-monitor/.send_trigger.txt"
LOG_FILE="$STATE_DIR/monitor.log"

# 创建目录
mkdir -p "$STATE_DIR"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查 bird 是否可用
if ! command -v bird &> /dev/null; then
    log "错误: bird CLI 不可用"
    exit 1
fi

# 存储已处理过的 tweet ID
PROCESSED_IDS_FILE="$STATE_DIR/processed_ids.txt"
touch "$PROCESSED_IDS_FILE"

# 新 tweets 存储文件
NEW_TWEETS_FILE="$STATE_DIR/new_tweets.md"
> "$NEW_TWEETS_FILE"

echo "# Twitter 官方账号监控 - $(date '+%Y-%m-%d %H:%M:%S')" >> "$NEW_TWEETS_FILE"
echo "" >> "$NEW_TWEETS_FILE"

# 检查每个账号
for account in "${TWITTER_ACCOUNTS[@]}"; do
    log "检查账号: $account"

    # 使用 bird 获取最近推文（只取最新 5 条）
    # --limit 5 减少抓取量，避免限流
    while IFS= read -r tweet; do
        if [ -z "$tweet" ]; then
            continue
        fi

        # 提取 tweet ID（假设 bird 返回的格式包含 ID）
        # 这里需要根据 bird 实际输出格式调整
        tweet_id=$(echo "$tweet" | grep -oE '[0-9]{15,}' | head -1)

        if [ -z "$tweet_id" ]; then
            continue
        fi

        # 检查是否已处理过
        if grep -q "$tweet_id" "$PROCESSED_IDS_FILE"; then
            continue
        fi

        # 新 tweet，添加到报告
        echo "## $account" >> "$NEW_TWEETS_FILE"
        echo "$tweet" >> "$NEW_TWEETS_FILE"
        echo "" >> "$NEW_TWEETS_FILE"

        # 记录已处理
        echo "$tweet_id" >> "$PROCESSED_IDS_FILE"

        log "新推文: $account - $tweet_id"
    done < <(npx @steipete/bird timeline "$account" --limit 5 --json 2>/dev/null | jq -r '.data[] | "\(.id) \(.text)"' 2>/dev/null || echo "")

    # 避免频繁请求，每个账号之间等待
    sleep 10
done

# 检查是否有新内容
if [ -s "$NEW_TWEETS_FILE" ] && [ $(wc -l < "$NEW_TWEETS_FILE") -gt 3 ]; then
    # 有新内容，创建触发文件
    echo "$NEW_TWEETS_FILE" > "$TRIGGER_FILE"
    log "有新推文，已创建触发文件"
else
    # 无新内容，清理
    rm -f "$NEW_TWEETS_FILE"
    log "无新推文"
fi

# 清理旧的 processed_ids（只保留最近 1000 条）
if [ $(wc -l < "$PROCESSED_IDS_FILE") -gt 1000 ]; then
    tail -1000 "$PROCESSED_IDS_FILE" > "$PROCESSED_IDS_FILE.tmp"
    mv "$PROCESSED_IDS_FILE.tmp" "$PROCESSED_IDS_FILE"
    log "清理旧 ID 记录"
fi
