#!/bin/bash
# Twitter 热点汇总脚本 - 简化版（带翻译）
# 使用 bird CLI 获取 AI 新闻

AUTH_TOKEN="4e71596a96cf770ad852eda68916b03f7ea76607"
CT0="44bc6cf0949d676ebcf0b788df4478bf3e649017e0faa788a99c80a53adbdd4bb050ccb13b7bfd1d64fc6a7d294e3fcb617b5eccf6bf4d82cc2bc92172ba0c089dd81c8b706b8c5dfd9cd405ef29ea62"

WEBHOOK_SCRIPT="$HOME/clawd/scripts/discord-webhook.sh"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

MESSAGE="# 🐦 X/Twitter 热点汇总
**时间:** $TIMESTAMP | $(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S 北京时间')

## 🤖 AI & 科技资讯

"

# 使用 bird CLI 获取 AI 新闻（设置较短超时）
echo "正在获取 Twitter AI 新闻..."
AI_NEWS=$(timeout 30 npx -y @steipete/bird news --ai-only -n 5 --auth-token "$AUTH_TOKEN" --ct0 "$CT0" 2>&1)

if [ -n "$AI_NEWS" ] && ! echo "$AI_NEWS" | grep -qi "error\|fail\|timeout"; then
    # 使用 Python 处理输出并翻译
    MESSAGE="$MESSAGE"$(echo "$AI_NEWS" | python3 -c "
import sys, json, urllib.parse, urllib.request, re

def translate_text(text, timeout=2):
    '''翻译英文文本为中文'''
    if not text or len(text) < 5:
        return text
    # 检查是否包含中文
    if any('\u4e00' <= c <= '\u9fff' for c in text):
        return text
    try:
        encoded = urllib.parse.quote(text[:500])
        url = f'https://api.mymemory.translated.net/get?q={encoded}&langpair=en|zh-CN'
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = json.load(resp)
            return data.get('responseData', {}).get('translatedText', text)
    except:
        return text

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    
    # 提取推文内容（通常在 @user 之后的部分）
    # 格式类似: @user https://t.co/xxx Tweet content here
    if line.startswith('@'):
        parts = line.split(None, 2)
        if len(parts) >= 3:
            user = parts[0]
            link = parts[1] if parts[1].startswith('http') else ''
            content = parts[2] if len(parts) > 2 else ''
            
            if content:
                # 翻译内容
                content_zh = translate_text(content)
                print(f'{user} {link}')
                print(f'  {content_zh}')
                print()
            else:
                print(line)
        else:
            print(line)
    else:
        print(line)
" 2>/dev/null)
else
    MESSAGE="$MESSAGE""暂无数据或 API 超时
"
fi

MESSAGE="$MESSAGE""
---
*汇总完成于: $(date '+%Y-%m-%d %H:%M:%S UTC')*"

echo "$MESSAGE" | bash "$WEBHOOK_SCRIPT" /dev/stdin
echo "✅ Twitter 汇总完成"
