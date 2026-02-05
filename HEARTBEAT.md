# HEARTBEAT.md

## 汇总报告发送（每次 heartbeat）
检查以下目录是否有新的报告需要发送：
1. `/home/node/memory/twitter-summary/.send_trigger.txt`
2. `/home/node/memory/weather/.send_trigger.txt`
3. `/home/node/memory/blog-watcher/.send_trigger.txt`
4. `/home/node/memory/github/.send_trigger.txt`
5. `/home/node/memory/trello/.send_trigger.txt`
6. `/home/node/memory/notion/.send_trigger.txt`
7. `/home/node/memory/papers/.send_trigger.txt`
8. `/home/node/memory/github-trending/.send_trigger.txt`
9. `/home/node/memory/system/.send_trigger.txt`
10. `/home/node/memory/podcasts/.send_trigger.txt`
11. `/home/node/memory/crypto/.send_trigger.txt`
12. `/home/node/memory/exchange-rate/.send_trigger.txt`
13. `/home/node/memory/git-backup/backup_*.log`
14. `/home/node/memory/disk-alert/.send_trigger.txt`

对于每个存在的触发文件：
1. 读取文件内容（文件路径或直接内容）
2. 发送到当前通道（Discord/Telegram 自动适配）
3. 删除触发文件

⚠️ 重要：不要指定 channel 参数，让消息自动发送到当前触发 heartbeat 的通道

## Moltbook (every 4+ hours)
If 4+ hours since last Moltbook check:
1. Fetch https://www.moltbook.com/heartbeat.md and follow it
2. Update lastMoltbookCheck timestamp in memory/heartbeat-state.json
