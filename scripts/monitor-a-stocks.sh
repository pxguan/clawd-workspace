#!/bin/bash
# A股监控脚本 - 每15分钟运行
# 使用QVeris获取股票数据

API_KEY="sk-mcKudIlefQjypdf8_Sk7zmFdVD_5j3sP154THWvy9Y4"
QVERIS_BASE="https://api.qveris.ai/v1"
LOG_FILE="/home/node/clawd/memory/a-stock-monitor.log"
STATE_FILE="/home/node/clawd/memory/a-stock-state.json"

mkdir -p /home/node/clawd/memory

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 获取A股涨跌数据
get_stock_movers() {
    curl -s "$QVERIS_BASE/tools/execute" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "tool": "stock_market.get_movers",
            "params": {
                "market": "CN",
                "limit": 20
            }
        }'
}

# 分析股票潜力
analyze_potential() {
    local stock_data="$1"
    curl -s "$QVERIS_BASE/tools/execute" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"tool\": \"ai.analyze\",
            \"params\": {
                \"task\": \"分析以下A股数据，筛选出3只增长潜力最大的股票（考虑成交量、涨势持续性、板块热度等因素）：$stock_data\",
                \"output_format\": \"json\"
            }
        }"
}

# 主逻辑
log "=== 开始A股监控 ==="

# 获取涨跌数据
movers=$(get_stock_movers)
log "涨跌数据获取完成"

# 分析潜力股
recommendations=$(analyze_potential "$movers")

# 保存结果
echo "$recommendations" | jq '.' > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"

# 提取推荐股票
top_stocks=$(echo "$recommendations" | jq -r '.recommendations[]?.symbol // empty' 2>/dev/null | head -3)

if [ -n "$top_stocks" ]; then
    log "推荐股票: $top_stocks"
    echo "$recommendations" | jq -r '.recommendations[]?.reason // empty' 2>/dev/null >> "$LOG_FILE"
else
    log "未能获取推荐股票"
fi

log "=== 监控完成 ==="

# 返回推荐结果（供cron调用）
echo "$recommendations"
