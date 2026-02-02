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
- **配置文件:** `/home/node/clawd/.env.qveris`

### Twitter
- **AUTH_TOKEN:** `b5a2d38cc4cb703d373ff230ad19a16487cb099e`
- **CT0:** `620a150990b7ceb46977dfead8bd74fa8c7f5cd102c157c3993cfbc7c750c27b435821384645e91ef6e4fd6de0ad1a2072c07743a96cdced1f0af09afbe11dacec898124358280eb5ab6fa1b4fa6dab0`
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

---

## ⚠️ 操作教训（重要）

### Token 消耗控制
1. **可能卡住的命令必须加 timeout**
   - 使用 `exec` 的 `timeout` 参数
   - 示例：`timeout: 60`（60秒超时）
2. **避免长时间 poll 循环**
   - 检查进程状态前先判断是否必要
   - 设置最大轮询次数
3. **大上下文会话要谨慎**
   - 每次请求都携带完整上下文
   - 及时清理不需要的历史消息

---

*最后更新: 2026-02-01 04:58 UTC*
