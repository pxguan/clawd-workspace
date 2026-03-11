#!/bin/bash
# 每日冥想脚本 - 修正路径

EVOLUTION_LOG="/home/node/.openclaw/workspace/evolution-log.md"
WORKSPACE="/home/node/.openclaw/workspace"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
BEIJING_TIME=$(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S')

# 确保 evolution-log.md 存在
mkdir -p "$(dirname "$EVOLUTION_LOG")"
if [ ! -f "$EVOLUTION_LOG" ]; then
    echo "# Evolution Log - 成长轨迹" > "$EVOLUTION_LOG"
    echo "" >> "$EVOLUTION_LOG"
    echo "> 记录每天的反思与成长" >> "$EVOLUTION_LOG"
    echo "" >> "$EVOLUTION_LOG"
fi

# 分析今天的活动
echo "## $BEIJING_TIME" >> "$EVOLUTION_LOG"
echo "" >> "$EVOLUTION_LOG"
echo "### 📅 今日概览" >> "$EVOLUTION_LOG"
echo "**UTC 时间:** $TIMESTAMP" >> "$EVOLUTION_LOG"
echo "" >> "$EVOLUTION_LOG"

# 检查今天的提交记录
TODAY_COMMITS=$(cd "$WORKSPACE" && git log --since="1 day ago" --oneline 2>/dev/null | wc -l)
if [ "$TODAY_COMMITS" -gt 0 ]; then
    echo "### ✨ 做得好的" >> "$EVOLUTION_LOG"
    echo "- 完成了 **$TODAY_COMMITS** 次代码提交" >> "$EVOLUTION_LOG"
    cd "$WORKSPACE" && git log --since="1 day ago" --oneline | head -5 | while read -r commit; do
        echo "  - $commit" >> "$EVOLUTION_LOG"
    done
    echo "" >> "$EVOLUTION_LOG"
fi

# 检查工作区变化
echo "### 🔧 文件变化" >> "$EVOLUTION_LOG"
CHANGED_FILES=$(cd "$WORKSPACE" && git status --porcelain 2>/dev/null | wc -l)
if [ "$CHANGED_FILES" -gt 0 ]; then
    echo "- 有 **$CHANGED_FILES** 个文件已修改但未提交" >> "$EVOLUTION_LOG"
else
    echo "- 工作区干净，无未提交变更" >> "$EVOLUTION_LOG"
fi
echo "" >> "$EVOLUTION_LOG"

# 每日反思
echo "### 💭 今日反思" >> "$EVOLUTION_LOG"
echo "- _等待填充..._" >> "$EVOLUTION_LOG"
echo "" >> "$EVOLUTION_LOG"
echo "---" >> "$EVOLUTION_LOG"
echo "" >> "$EVOLUTION_LOG"

echo "✅ 冥想记录已写入: $EVOLUTION_LOG"
