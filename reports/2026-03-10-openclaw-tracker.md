# OpenClaw 每日追踪简报

**日期:** 2026-03-10 (周一)
**报告编号:** #001

---

## 📌 今日亮点 (3-5条)

### 1. 最新版本 v2026.3.8 发布 (2026-03-09)
- **新增备份功能:** `openclaw backup create` 和 `openclaw backup verify` 支持本地状态归档
- **远程网关令牌:** macOS 应用新增远程模式令牌字段，改进远程网关配置体验
- **Talk 模式增强:** 新增 `talk.silenceTimeoutMs` 配置，可自定义静默等待时间
- **Brave 搜索 LLM 上下文模式:** 新增 `tools.web.search.brave.mode: "llm-context"` 支持返回提取的引用片段

### 2. Context Engine 插件接口 (v2026.3.7)
- **插件化上下文管理引擎:** 新增 ContextEngine 插件槽位，支持生命周期钩子
  - bootstrap, ingest, assemble, compact, afterTurn, prepareSubagentSpawn, onSubagentEnded
- **替代压缩策略:** 插件如 lossless-claw 可提供无损上下文管理方案
- **零行为变更:** 未配置插件时保持原有行为

### 3. ACP (异步控制协议) 持久化绑定
- **Discord/Telegram 话题绑定:** ACP 线程目标现在可以持久化存储，重启后仍有效
- **Telegram 话题路由:** 支持按话题分配独立 agentId，实现话题级别的会话隔离

### 4. 多语言 Web UI 支持
- **西班牙语支持:** Control UI 新增 es (西班牙语) 语言环境

---

## 🆕 新玩法/技巧

### Subagent 自动完成机制
- **Push-based 完成通知:** 子任务完成时会自动宣布结果，无需轮询
- **避免轮询陷阱:** 不要循环调用 `subagents list`，仅在需要干预/调试时检查状态
- **适用场景:** 复杂任务、长时间运行的任务、需要不同模型/思考级别的任务

### Cron 配置最佳实践
- **固定时间任务:** 使用 `cron` 表达式（如 `"0 9 * * 1"` = 每周一早 9 点）
- **相对间隔:** 使用 `everyMs`（会 drift）
- **独立触发:** `wakeMode: "now"` 不依赖 heartbeat
- **Heartbeat 触发:** `wakeMode: "next-heartbeat"` 等待下一次心跳

### Heartbeat 智能响应
- **不要每次都回复 `HEARTBEAT_OK`:** 利用心跳做有用的背景工作
- **批量检查:** 将多个周期性检查（邮箱、日历、通知）合并到一个心跳中
- **Quiet Hours:** 深夜 (23:00-08:00) 除非紧急否则保持安静

---

## 📦 GitHub 更新

### 最新版本
- **v2026.3.8** (2026-03-09) - 稳定版
- **v2026.3.8-beta.1** (2026-03-09) - 测试版
- **v2026.3.7** (2026-03-08) - 稳定版

### 重要 PR/贡献者
- @shichangs - 备份功能实现
- @cgdusek - macOS 远程网关令牌
- @danodoesdesign - Talk 模式静默超时
- @thirumaleshp - Brave 搜索 LLM 上下文
- @jalehman - Context Engine 插件接口
- @dutifulbob - ACP 持久化绑定
- @DaoPromociones - 西班牙语 UI 支持

### Breaking Changes
- **v2026.3.7:** Gateway 认证现在需要明确设置 `gateway.auth.mode` (token 或 password)，当同时配置了 token 和 password 时

---

## 🛠️ 新发现的 Skill

### 本地已安装 Skills
1. **agent-browser** - 浏览器自动化 CLI
   - 支持: 导航、快照、交互、截图、PDF、Diff 对比
   - 特色: refs 系统 (@e1, @e2)、会话持久化、状态加密

2. **zimage-skill** - ModelScope 图像生成
   - API: 阿里云通义万相 Z-Image-Turbo
   - 需要: MODELSCOPE_API_KEY
   - 支持: 中英文提示词

3. **pdf-qa** - PDF 文档问答
   - RAG 架构
   - 混合搜索 (BM25 + 向量)

4. **remotion-server** - 视频渲染服务器

5. **lobstalk** - (具体功能待探索)

### ClawHub
- 官方 skill 注册中心: https://clawhub.ai/
- 当启用 ClawHub 时，agent 可以自动搜索并拉取新 skill

---

## 💬 社区讨论

### Discord
- 官方服务器: https://discord.gg/clawd
- 活跃频道: clawd

### 官方资源
- 文档: https://docs.openclaw.ai
- GitHub: https://github.com/openclaw/openclaw
- 网站: https://openclaw.ai

### Twitter/X
- @openclaw

---

## 📊 数据源说明

- **GitHub Releases:** 官方发布说明和变更日志
- **GitHub Commits:** 实时开发动态
- **ClawHub:** Skill 注册和发现
- **本地环境:** 已安装 skills 和配置
- **社区:** Discord、Twitter、文档更新

---

## 📝 备注

- 本报告基于 2026-03-10 可获得的信息整理
- 由于搜索 API 限制，部分信息来自本地环境和官方文档
- 建议配置 Brave Search API Key 以获得更全面的实时信息

---
*报告生成时间: 2026-03-10 15:06 UTC*
*下次更新: 2026-03-11*
