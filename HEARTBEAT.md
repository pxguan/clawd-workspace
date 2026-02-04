# HEARTBEAT.md

## 汇总报告发送（每次 heartbeat）
检查以下目录是否有新的报告需要发送：
1. `/home/node/clawd/memory/twitter-summary/.send_trigger.txt`
2. `/home/node/clawd/memory/weather/.send_trigger.txt`
3. `/home/node/clawd/memory/blog-watcher/.send_trigger.txt`
4. `/home/node/clawd/memory/github/.send_trigger.txt`
5. `/home/node/clawd/memory/trello/.send_trigger.txt`
6. `/home/node/clawd/memory/notion/.send_trigger.txt`
7. `/home/node/clawd/memory/papers/.send_trigger.txt`
8. `/home/node/clawd/memory/github-trending/.send_trigger.txt`
9. `/home/node/clawd/memory/system/.send_trigger.txt`
10. `/home/node/clawd/memory/podcasts/.send_trigger.txt`

对于每个存在的触发文件：
1. 读取文件内容（文件路径或直接内容）
2. 发送到当前通道（Discord/Telegram 自动适配）
3. 删除触发文件

⚠️ 重要：不要指定 channel 参数，让消息自动发送到当前触发 heartbeat 的通道

## Moltbook (every 4+ hours)
If 4+ hours since last Moltbook check:
1. Fetch https://www.moltbook.com/heartbeat.md and follow it
2. Update lastMoltbookCheck timestamp in memory/heartbeat-state.json
