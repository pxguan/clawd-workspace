#!/bin/bash
# A股监控脚本 - 每15分钟运行
# 使用东方财富免费API

LOG_DIR="/home/node/clawd/memory/a-stocks"
LOG_FILE="$LOG_DIR/monitor.log"
STATE_FILE="$LOG_DIR/latest_recommendations.json"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
TIME_HOUR=$(date '+%H')

mkdir -p "$LOG_DIR"

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

# 检查是否在交易时间
is_trading_time() {
    local hour=$1
    local weekday=$(date +%u)

    # 周末不监控
    if [ "$weekday" -gt 5 ]; then
        return 1
    fi

    # 9:00-15:30 交易时间
    if [ "$hour" -ge 9 ] && [ "$hour" -lt 16 ]; then
        return 0
    fi

    return 1
}

# 获取A股涨跌数据
get_stock_data() {
    # 获取涨幅榜（前30名）
    curl -s "http://push2.eastmoney.com/api/qt/clist/get" \
        --data-urlencode "pn=1" \
        --data-urlencode "pz=30" \
        --data-urlencode "po=1" \
        --data-urlencode "np=1" \
        --data-urlencode "fltt=2" \
        --data-urlencode "invt=2" \
        --data-urlencode "fid=f3" \
        --data-urlencode "fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:1+t:81" \
        --data-urlencode "fields=f12,f13,f14,f2,f3,f5,f6,f7,f15,f16,f17,f18" \
        --max-time 15
}

# 简单筛选逻辑（不用jq，用awk/sed）
analyze_stocks() {
    local json="$1"

    # 提取关键数据并用awk分析
    echo "$json" | sed 's/\],\[/\n/g' | sed 's/\[{/\[{/g' | sed 's/}]\{/}]\{/g' |
    grep -o '"f14":"[^"]*","f12":"[^"]*","f3":[0-9.-]*,"f7":[0-9.-]*,"f5":[0-9.-]*' |
    head -20
}

# 主流程
log "========== A股监控 =========="

# 检查交易时间
if ! is_trading_time "$TIME_HOUR"; then
    log "非交易时间，跳过监控"
    exit 0
fi

log "获取A股数据..."

# 获取数据
stock_data=$(get_stock_data)

# 检查数据有效性
if ! echo "$stock_data" | grep -q '"rc":0'; then
    log "数据获取失败"
    exit 1
fi

# 解析数据（手工处理JSON）
# f12=代码, f14=名称, f2=价格, f3=涨跌幅%, f5=成交量手, f7=振幅%

# 提取涨幅榜TOP10（涨幅适中3-8%优先）
top_stocks=$(echo "$stock_data" | sed 's/{"f2":/\n{"f2":/g' | grep '"f14":' |
    awk -v FPAT='[^,]*' '
    {
        for(i=1;i<=NF;i++) {
            if($i ~ /"f14":"/) { name=substr($i,8,length($i)-9) }
            if($i ~ /"f12":"/) { code=substr($i,8,length($i)-9) }
            if($i ~ /"f3":/) { change=substr($i,6); gsub(/[^0-9.-]/,"",change) }
            if($i ~ /"f7":/) { amp=substr($i,6); gsub(/[^0-9.-]/,"",amp) }
            if($i ~ /"f5":/) { vol=substr($i,6); gsub(/[^0-9.]/,"",vol) }
        }
        if(name != "" && change != "") {
            # 计算分数：3-8%涨幅加分，振幅大加分
            score=0
            if(change >= 3 && change <= 8) score = 50 + change * 5
            else if(change > 8) score = 30 + change * 2
            else if(change < 0 && change >= -5) score = 20  # 超跌机会

            score = score + amp * 2

            printf "%s|%s|%s|%s|%.1f\n", code, name, change, vol, score
            name=""; code=""; change=""; vol=""; amp=""
        }
    }' |
    sort -t'|' -k5 -nr |
    head -3 |
    awk -F'|' '{
        reason=""
        if($3+0 >= 3 && $3+0 <= 8) reason="涨幅适中(" $3 "%)，上涨动能充足"
        else if($3+0 > 8) reason="强势上涨(" $3 "%)，注意追高风险"
        else if($3+0 < 0) reason="超跌反弹机会，跌幅" $3 "%"

        printf "📈 %s (%s): %s\\n", $2, $1, reason
    }')

log "今日推荐（TOP3）："
echo "$top_stocks" | while IFS= read -r line; do
    log "  $line"
done

# 保存结果
cat > "$STATE_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "is_trading_time": true,
  "recommendations": [
$(echo "$top_stocks" | sed 's/^/    "/' | sed 's/$/",/' | sed '$ s/,$//')
  ]
}
EOF

log "结果已保存: $STATE_FILE"
log "========== 监控完成 =========="

# 输出给用户
echo ""
echo "📊 A股监控报告 - $TIMESTAMP"
echo "─────────────────────────────"
echo "$top_stocks"
