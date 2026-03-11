#!/bin/bash
#
# Twitter 技术/AI 博主监控脚本
# 安全特性：
# - 每小时检查一次（避免限流）
# - 去重逻辑（只推送新内容）
# - 无内容不推送
# - 手动维护大V列表（bird抓不到粉丝数）
#

INFLUENCERS_FILE="/home/node/.openclaw/workspace/data/twitter-tech-influencers.txt"
STATE_DIR="/home/node/memory/twitter-tech-monitor"
TRIGGER_FILE="/home/node/memory/twitter-tech-monitor/.send_trigger.txt"
LOG_FILE="$STATE_DIR/monitor.log"

# 创建目录
mkdir -p "$STATE_DIR"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查 bird 是否可用
if ! command -v bird &> /dev/null; then
    log "错误: bird CLI 不可用，请安装: npm install -g @steipete/bird"
    exit 1
fi

# 存储已处理过的 tweet ID
PROCESSED_IDS_FILE="$STATE_DIR/processed_ids.txt"
touch "$PROCESSED_IDS_FILE"

# 新 tweets 存储文件
NEW_TWEETS_FILE="$STATE_DIR/new_tweets.md"
> "$NEW_TWEETS_FILE"

echo "# Twitter 技术/AI 博主监控 - $(date '+%Y-%m-%d %H:%M:%S')" >> "$NEW_TWEETS_FILE"
echo "" >> "$NEW_TWEETS_FILE"

# 读取博主列表（跳过注释和空行）
while IFS='|' read -r username followers area notes; do
    # 跳过注释和空行
    if [[ "$username" =~ ^#.*$ ]] || [[ -z "$username" ]]; then
        continue
    fi
    
    # 去掉空格
    username=$(echo "$username" | xargs)
    
    # 跳过官方账号（可选）
    if [[ "$username" == *"官方"* ]]; then
        continue
    fi
    
    log "检查博主: $username"
    
    # 使用 bird 获取最近推文（只取最新 3 条）
    # --limit 3 减少抓取量
    while IFS= read -r tweet_data; do
        if [ -z "$tweet_data" ]; then
            continue
        fi
        
        # 提取 tweet ID
        tweet_id=$(echo "$tweet_data" | grep -oE '[0-9]{15,}' | head -1)
        
        if [ -z "$tweet_id" ]; then
            continue
        fi
        
        # 检查是否已处理过
        if grep -q "$tweet_id" "$PROCESSED_IDS_FILE"; then
            continue
        fi
        
        # 提取推文文本
        tweet_text=$(echo "$tweet_data" | sed 's/^[0-9]* //')
        
        # 新 tweet，添加到报告
        echo "## $username" >> "$NEW_TWEETS_FILE"
        echo "$tweet_text" >> "$NEW_TWEETS_FILE"
        echo "" >> "$NEW_TWEETS_FILE"
        
        # 记录已处理
        echo "$tweet_id" >> "$PROCESSED_IDS_FILE"
        
        log "新推文: $username - $tweet_id"
    done < <(npx @steipete/bird timeline "$username" --limit 3 --json 2>/dev/null | jq -r '.data[] | "\(.id) \(.text)"' 2>/dev/null || echo "")
    
    # 避免频繁请求，每个博主之间等待 15 秒
    sleep 15
done < <(grep -v "^#" "$INFLUENCERS_FILE" | grep -v "^$")

# 检查是否有新内容
if [ -s "$NEW_TWEETS_FILE" ] && [ $(wc -l < "$NEW_TWEETS_FILE") -gt 3 ]; then
    # 有新内容，创建触发文件
    echo "$NEW_TWEETS_FILE" > "$TRIGGER_FILE"
    log "有新推文，已创建触发文件: $NEW_TWEETS_FILE"
else
    # 无新内容，清理
    rm -f "$NEW_TWEETS_FILE"
    log "无新推文"
fi

# 清理旧的 processed_ids（只保留最近 2000 条）
if [ $(wc -l < "$PROCESSED_IDS_FILE") -gt 2000 ]; then
    tail -2000 "$PROCESSED_IDS_FILE" > "$PROCESSED_IDS_FILE.tmp"
    mv "$PROCESSED_IDS_FILE.tmp" "$PROCESSED_IDS_FILE"
    log "清理旧 ID 记录"
fi

log "检查完成"
