#!/bin/bash
# Twitter 热点汇总脚本 - 使用 bird CLI

AUTH_TOKEN="AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
CT0="620a150990b7ceb46977dfead8bd74fa8c7f5cd102c157c3993cfbc7c750c27b435821384645e91ef6e4fd6de0ad1a2072c07743a96cdced1f0af09afbe11dacec898124358280eb5ab6fa1b4fa6dab0"

WEBHOOK_SCRIPT="$HOME/clawd/scripts/discord-webhook.sh"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

MESSAGE="# 🐦 X/Twitter 热点汇总
**时间:** $TIMESTAMP | $(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S 北京时间')

## 🤖 AI & 科技资讯

"

# 使用 bird CLI 搜索（带超时）
echo "正在搜索 Twitter AI 新闻..."
TWEETS=$(export AUTH_TOKEN="$AUTH_TOKEN" export CT0="$CT0" timeout 45 npx --yes @steipete/bird search "AI OR #AI OR #ArtificialIntelligence OR #MachineLearning OR #DeepLearning" --count 10 --json 2>&1)

if echo "$TWEETS" | grep -q '"id"'; then
    # 解析 JSON 并提取推文
    MESSAGE="$MESSAGE"$(echo "$TWEETS" | python3 -c "
import sys, json, urllib.parse, urllib.request

def translate_text(text, timeout=2):
    if not text or len(text) < 5:
        return text
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

try:
    data = json.load(sys.stdin)
    if isinstance(data, list):
        for tweet in data[:5]:
            text = tweet.get('text', '')
            # 移除 URL
            text_clean = ' '.join([w for w in text.split() if not w.startswith('http')])
            if text_clean:
                text_zh = translate_text(text_clean)
                tweet_id = tweet.get('id')
                url = f'https://twitter.com/i/status/{tweet_id}'
                print(f'- [{text_zh[:80]}...]({url})')
                print()
except Exception as e:
    print(f'解析错误: {e}', file=sys.stderr)
" 2>/dev/null)
else
    # bird CLI 失败
    ERROR_INFO=$(echo "$TWEETS" | head -c 300)
    MESSAGE="$MESSAGE

> ⚠️ **Twitter 搜索失败**

> 错误详情: \\\`$ERROR_INFO\\\`

> 暂时显示热门标签：
> - **#AI** - 人工智能
> - **#MachineLearning** - 机器学习
> - **#OpenAI** - OpenAI 相关
> - **#ChatGPT** - ChatGPT 讨论
> - **#DeepLearning** - 深度学习"
fi

MESSAGE="$MESSAGE""

---
*汇总完成于: $(date '+%Y-%m-%d %H:%M:%S UTC')*"

echo "$MESSAGE" | bash "$WEBHOOK_SCRIPT" /dev/stdin
echo "✅ Twitter 汇总完成"
