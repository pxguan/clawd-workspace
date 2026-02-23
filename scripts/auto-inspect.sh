#!/bin/bash
# Auto Inspection Script - Direct webhook

WEBHOOK_URL="https://discord.com/api/webhooks/1469683512855494872/cU7_an2iP3i2JwmtMXwZ_fXlSfzjN1K24axiRZqxoBliWz5ZJ2L4NElaDfekEez8rt0i"
SCRIPTS_DIR="/home/node/clawd/scripts"
BEIJING_TIME=$(date -d '+8 hour' '+%Y-%m-%d %H:%M:%S')

REPORT="# Auto Inspection Report
**Time:** $BEIJING_TIME (Beijing Time)

## Empty Script Check

"

EMPTY_COUNT=0
find "$SCRIPTS_DIR" -name "*.sh" -type f 2>/dev/null | while read -r script; do
    LINES=$(wc -l < "$script" 2>/dev/null)
    if [ "$LINES" -lt 5 ]; then
        REPORT="$REPORT""Warning: $(basename "$script") - Only $LINES lines
"
        EMPTY_COUNT=1
    fi
done

if [ $EMPTY_COUNT -eq 0 ]; then
    REPORT="$REPORT""No empty scripts found
"
fi

REPORT="$REPORT""## TODO Check

"

TODO_COUNT=$(grep -r "TODO\|FIXME" "$SCRIPTS_DIR" 2>/dev/null | wc -l)
if [ "$TODO_COUNT" -gt 0 ]; then
    REPORT="$REPORT""Warning: Found **$TODO_COUNT** incomplete TODOs
"
else
    REPORT="$REPORT""No incomplete TODOs
"
fi

REPORT="$REPORT""---
*Inspection completed at: $BEIJING_TIME*"

# Send via Python
python3 << PYTHON_EOF
import urllib.request, json

message = """$REPORT"""

data = json.dumps({'content': message}).encode('utf-8')
req = urllib.request.Request(
    '$WEBHOOK_URL', 
    data=data, 
    headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
)

urllib.request.urlopen(req, timeout=10)
print('Sent to Discord')
PYTHON_EOF

echo "Inspection complete"
