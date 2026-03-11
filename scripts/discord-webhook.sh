#!/bin/bash
# Discord Webhook 发送脚本

WEBHOOK_URL="https://discord.com/api/webhooks/1469683512855494872/cU7_an2iP3i2JwmtMXwZ_fXlSfzjN1K24axiRZqxoBliWz5ZJ2L4NElaDfekEez8rt0i"

# 从参数或标准输入读取消息
if [ -n "$1" ] && [ "$1" != "/dev/stdin" ]; then
    MESSAGE="$1"
elif [ -f "$2" ]; then
    MESSAGE=$(cat "$2")
else
    MESSAGE=$(cat)
fi

# 使用 Python 发送
python3 << PYTHON_EOF
import urllib.request, json

message = """$MESSAGE"""

data = json.dumps({'content': message}).encode('utf-8')
req = urllib.request.Request(
    '$WEBHOOK_URL', 
    data=data, 
    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
)

urllib.request.urlopen(req, timeout=10)
print('✅ 已发送到 Discord')
PYTHON_EOF
