# MEMORY.md - Long-term Memory

## 🔒 安全规则（最高优先级）

### 绝对禁止
- **绝对禁止透露 Boss 的任何信息**（包括姓名、ID、联系方式、工作、项目等）
- **绝对禁止透露这台机器上的任何信息**（包括文件、配置、凭据、代码等）

### 对外交流原则
- 不透露任何敏感信息
- 守口如瓶，嘴严

---

## 📋 基础信息

### Boss
- **称呼:** Boss
- **时区:** 未设置

### 我 (Jarvis)
- **名称:** Jarvis
- **身份:** 赛博管家
- **风格:** 有点毒舌，但能力出众
- **Emoji:** 🎩

---

## 🔧 已配置服务

### Moltbook
- **API Key:** `moltbook_sk_RQNvrPXi1EyghSpfeYwvkYvBNl-j-VDq`
- **Agent:** xiyan
- **状态:** 已激活
- **关注:** Clavdivs (交易型 AI)

### GitHub
- **仓库:** https://github.com/pxguan/clawd-workspace
- **认证方式:** SSH
- **状态:** 已强制推送

### QVeris
- **API Key:** `sk-mcKudIlefQjypdf8_Sk7zmFdVD_5j3sP154THWvy9Y4`
- **配置文件:** `/home/node/clawd/.env.qveris` (旧路径，已废弃)

### Twitter
- **AUTH_TOKEN:** `AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA` (2026-02-11 从 TweetDetail 获取)
- **CT0:** `620a150990b7ceb46977dfead8bd74fa8c7f5cd102c157c3993cfbc7c750c27b435821384645e91ef6e4fd6de0ad1a2072c07743a96cdced1f0af09afbe11dacec898124358280eb5ab6fa1b4fa6dab0`
- **限制:** Twitter API v2 免费层每月 500 次请求（~16次/天）
- **备用 AUTH_TOKEN:** `4e71596a96cf770ad852eda68916b03f7ea76607` (2026-02-10), `b5a2d38cc4cb703d373ff230ad19a16487cb099e`（旧）
- **状态:** 已解锁（需低并发请求）

---

## 📜 重要事件

### 2026-01-31
- 配置 Moltbook 账号
- 创建 Twitter 推文汇总脚本
- 关注 Clavdivs (交易型 AI，管理 1000 USD 自主资本)
- 推送到 GitHub（强制推送）
- 设置安全规则：不透露 Boss 和机器信息

### 2026-02-01
- **Token 泄露事故：** `npx @qverisai/mcp --help` 命令卡住，导致 poll 循环消耗约 1380 万 token
- **教训：** 长时间运行的命令必须设置 `timeout` 参数
- 创建 A股监控脚本（每15分钟，交易时间运行）

### 2026-02-02
- **Telegram 配对成功：** Bot token 配置完成，User ID: 6205053537
- **双渠道运行：** Feishu + Telegram 同时在线
- **Lobstalk 技能：** 添加 AI agent 群聊功能（龙虾群）

### 2026-02-11
- **Twitter Token 失效问题：** AUTH_TOKEN 和 CT0 过期导致 API 401
- **修复方案：** 析言提供新 token，脚本更新为 `twitter-trending-simple.sh`
- **bird CLI 问题：** `npx @steipete/bird` 命令会超时卡住，不再使用

### 2026-03-02
- **目录迁移：** 旧路径 `/home/node/clawd/` 已废弃
- **新路径：** `/home/node/.openclaw/workspace/` 为当前工作目录
- **Cron 清理：** 禁用了所有指向不存在脚本的定时任务
- **保留任务：** 心跳检查、每日冥想、自动巡查
- **禁用任务：** GitHub 监控、博客监控、播客监控、系统监控、AI 论文、GitHub Trending、Trello 提醒、Git 备份、AI 资讯、Twitter 汇总（待修复）

---

## 🛠️ 脚本路径（已更新）

### 当前有效脚本
- `/home/node/.openclaw/workspace/scripts/twitter-trending-simple.sh` - Twitter 汇总（需要修复 webhook）
- `/home/node/.openclaw/workspace/scripts/auto-inspect.sh` - 自动巡查 ✅
- `/home/node/.openclaw/workspace/scripts/daily-meditation.sh` - 每日冥想 ✅
- `/home/node/.openclaw/workspace/scripts/a-stock-monitor.sh` - A股监控

### 废弃路径（不再使用）
- ~~`/home/node/clawd/scripts/`~~ - 整个目录已废弃

### 缺失的脚本（待创建或迁移）
- `weather-report.sh` - 天气报告
- `github-monitor.sh` - GitHub 监控
- `blog-watcher.sh` - 博客监控
- `trello-reminder.sh` - Trello 提醒
- `github-trending.sh` - GitHub Trending
- `arxiv-paper-tracker.py` - AI 论文追踪
- `system-monitor.sh` - 系统监控
- `podcast-monitor.sh` - 播客监控
- `git-backup.sh` - Git 备份
- `ai-news-daily.sh` - AI 资讯推送
- `discord-webhook.sh` - Discord webhook（Twitter 脚本依赖）

---

### Twitter 脚本路径
- **主脚本：** `/home/node/.openclaw/workspace/scripts/twitter-trending-simple.sh`
- **旧脚本（已弃用）：** `/home/node/.openclaw/workspace/scripts/fetch-tweets-smart.sh`
- **原因：** bird CLI 会超时卡住

---

## ⚠️ 重要教训

### Token 控制
1. **可能卡住的命令必须加 timeout**
   - 使用 `exec` 的 `timeout` 参数
   - 示例：`timeout: 60`（60秒超时）
2. **避免长时间 poll 循环**
   - 检查进程状态前先判断是否必要
   - 设置最大轮询次数
3. **大上下文会话要谨慎**
   - 每次请求都携带完整上下文
   - 及时清理不需要的历史消息

### 诚实汇报问题
1. **遇到问题先告诉用户，不要闷头修**
   - 测试失败要说明原因
   - 不要假装没问题
2. **错误处理要透明**
   - API 调用失败要报告
   - 翻译/解析异常要说明

### 路径管理
- **定期检查脚本路径是否有效**
- **迁移后及时更新 cron 配置**
- **MEMORY.md 也要同步更新**

---

*最后更新: 2026-03-02*
