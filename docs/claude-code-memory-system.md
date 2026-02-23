# Claude Code 记忆系统设计方案

> 基于 Claude Code 实现持久化记忆架构
>
> **作者:** Jarvis
> **日期:** 2026-02-23
> **版本:** 1.0

---

## 🎯 设计目标

让 Claude Code 拥有持久化记忆，能在会话间保持上下文，避免每次会话"失忆"。

---

## 📐 架构设计

```
┌─────────────────────────────────────────────────────┐
│                   Claude Code                        │
│                  (每次会话启动)                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  Memory Loader  │  ← 自动加载记忆文件
        └────────┬───────┘
                 │
        ┌────────▼────────────────────────────┐
        │                                        │
        ▼                                        ▼
┌───────────────┐                    ┌────────────────┐
│  MEMORY.md    │                    │memory/YYYY-MM-  │
│ (长期记忆)     │                    │DD.md (短期)     │
└───────────────┘                    └────────────────┘
        ▲                                        ▲
        │                                        │
        │        ┌──────────────┐               │
        └────────│  Memory Core  │───────────────┘
                 │  (统一接口)   │
                 └──────┬───────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Search  │    │  Write  │    │ Maintain│
   └─────────┘    └─────────┘    └─────────┘
```

---

## 🛠️ 核心组件

### 1. 文件结构

```
.claude/
├── memory/
│   ├── MEMORY.md          # 长期记忆（精选内容）
│   ├── 2026-02-23.md      # 日记（原始记录）
│   └── heartbeat-state.json
└── skills/
    └── memory-core/
        ├── SKILL.md
        ├── memory.sh      # CLI 工具
        └── memory.py      # Python 库（可选）
```

---

## 📝 记忆格式规范

### MEMORY.md 结构

```markdown
# MEMORY.md

## 🔑 核心信息
- 姓名、时区、偏好

## 🔧 配置
- Token、API Key（脱敏存储）

## 📚 项目知识
- 项目背景、决策记录

## 💡 经验教训
- 踩过的坑、最佳实践

## 📅 重大事件
- 时间线记录
```

### 日记格式

```markdown
# 2026-02-23.md

## 09:30 - 配置 GitHub Token
- 问题：更新镜像后环境变量丢失
- 解决：重新配置 credential helper
```

---

## 🔧 Memory API (命令接口)

### 基础命令

```bash
# 写入记忆
memory write "今天学了 X，记住这个" --type daily

# 搜索记忆
memory search "GitHub token 配置"

# 提炼到长期记忆
memory refine --from "2026-02-23.md" --to MEMORY.md

# 列出最近记忆
memory recent --days 3
```

### CLI 实现 (`memory.sh`)

```bash
#!/bin/bash

MEMORY_DIR="$HOME/.claude/memory"
MEMORY_FILE="$MEMORY_DIR/MEMORY.md"
TODAY_FILE="$MEMORY_DIR/$(date +%Y-%m-%d).md"

mkdir -p "$MEMORY_DIR"

# 写入日记
write_daily() {
    local timestamp=$(date +"%H:%M")
    local content="$1"
    echo "## $timestamp - $content" >> "$TODAY_FILE"
}

# 搜索记忆
search_memory() {
    local query="$1"
    grep -r "$query" "$MEMORY_DIR" --include="*.md" -n
}

# 提炼到长期记忆
refine_memory() {
    # 从日报提取重要内容到 MEMORY.md
    # TODO: 实现 LLM 辅助提炼
}

case "$1" in
    write) write_daily "$2" ;;
    search) search_memory "$2" ;;
    refine) refine_memory ;;
    *) echo "Usage: memory {write|search|refine}" ;;
esac
```

---

## 🔄 自动加载机制

### Claude Code Prompt 模板

在项目根目录创建 `.claude/INSTRUCTIONS.md`：

```markdown
## Memory Protocol

每次会话启动时，自动执行：
1. 读取 `.claude/memory/MEMORY.md`
2. 读取最近 3 天的日记文件
3. 加载 heartbeat 状态

### 安全规则
- MEMORY.md 只在私人会话加载
- 群聊/公共会话不加载敏感信息
```

---

## 🔄 维护机制

### Heartbeat 集成

```bash
# 每 N 小时触发一次
memory heartbeat --actions \
  "search:未完成的任务" \
  "refine:提炼本周重要事件" \
  "cleanup:删除过期临时文件"
```

### 自动提炼算法

```python
# memory-core/refine.py
def should_promote_to_long_term(entry):
    """判断是否值得写入长期记忆"""
    score = 0
    if contains_decision(entry): score += 3
    if contains_lesson_learned(entry): score += 2
    if mentions_user_request(entry): score += 1
    return score >= 3
```

---

## 🔒 安全设计

### 敏感信息处理

```bash
# 自动脱敏
memory write "API key: sk-xxxx" --sanitize

# 输出时过滤
memory search --filter-secrets
```

### 上下文隔离

```
私人会话 → 加载 MEMORY.md + 日记
群聊会话 → 只加载非敏感摘要
公共会话 → 不加载任何记忆
```

---

## 📊 实现优先级

### Phase 1: 基础功能
- [x] 文件结构设计
- [ ] `memory.sh` 命令行工具
- [ ] 自动加载机制

### Phase 2: 增强
- [ ] 语义搜索（集成 embeddings）
- [ ] 自动提炼算法
- [ ] Claude Code Skill 封装

### Phase 3: 高级
- [ ] 跨会话记忆同步
- [ ] 记忆可视化 UI
- [ ] 自动归档过期内容

---

## 🚀 快速开始

```bash
# 1. 创建目录结构
mkdir -p ~/.claude/memory
mkdir -p ~/.claude/skills/memory-core

# 2. 初始化 MEMORY.md
cat > ~/.claude/memory/MEMORY.md << 'EOF'
# MEMORY.md

这里记录长期记忆...
EOF

# 3. 安装 memory.sh
chmod +x ~/.claude/skills/memory-core/memory.sh
export PATH="$PATH:~/.claude/skills/memory-core"
```

---

## 📚 参考资料

- Claude Code 文档: https://docs.anthropic.com/claude-code
- OpenClaw AGENTS.md: 记忆系统参考实现

---

## 💻 现有代码实现

### 记忆系统核心脚本

| 文件 | 功能 | 路径 |
|------|------|------|
| **每日冥想** | 回顾今日活动，记录到 evolution-log.md | `scripts/daily-meditation.sh` |
| **自动检查** | 检查空脚本和 TODO 项，报告到 Discord | `scripts/auto-inspect.sh` |
| **自动备份** | Git 自动提交和推送 | `scripts/auto-git-backup.sh` |

### 数据采集脚本

| 文件 | 功能 | 路径 |
|------|------|------|
| **Twitter 汇总** | 搜索 AI 相关推文，翻译并发送 | `scripts/twitter-trending-simple.sh` |
| **发送助手** | 格式化汇总输出 | `scripts/send-twitter-summary.sh` |
| **A股监控** | 每15分钟获取涨跌数据，推荐股票 | `scripts/a-stock-monitor.sh` |
| **A股看门狗** | 监控异常波动 | `scripts/a-stock-watchdog.sh` |
| **A股状态** | 查看当前监控状态 | `scripts/a-stock-status.sh` |

### 其他工具

| 文件 | 功能 | 路径 |
|------|------|------|
| **新闻视频制作** | 自动生成新闻视频 | `scripts/news-video-maker.sh` |
| **股票监控（Python）** | Python 版本监控 | `scripts/python/stock_monitor.py` |
| **获取推文** | 获取指定用户推文 | `scripts/fetch-tweets.sh` |
| **智能获取推文** | 带缓存的推文获取 | `scripts/fetch-tweets-smart.sh` |
| **监控 A 股列表** | 批量监控 | `scripts/monitor-a-stocks.sh` |

### 记忆文件结构

```
memory/
├── heartbeat-state.json       # Heartbeat 状态跟踪
├── twitter-summary/           # Twitter 汇总触发文件
├── weather/                   # 天气报告触发文件
├── blog-watcher/              # 博客监控触发文件
├── github/                    # GitHub 监控触发文件
├── trello/                    # Trello 提醒触发文件
├── notion/                    # Notion 监控触发文件
├── papers/                    # 论文监控触发文件
├── github-trending/           # GitHub Trending 触发文件
├── system/                    # 系统监控触发文件
├── podcasts/                  # 播客监控触发文件
├── crypto/                    # 加密货币监控触发文件
├── git-backup/                # Git 备份日志
├── disk-alert/                # 磁盘告警触发文件
└── a-stocks/                  # A股监控日志和状态
    ├── monitor.log
    └── latest_recommendations.json
```

### 状态文件

| 文件 | 用途 |
|------|------|
| `evolution-log.md` | 成长轨迹记录 |
| `.openclaw/workspace-state.json` | 工作区状态 |
| `memory/heartbeat-state.json` | Heartbeat 时间戳 |

---

## 🔗 脚本依赖关系

```
┌─────────────────────────────────────────────────────┐
│                   Heartbeat (每30分钟)               │
└────────────────┬────────────────────────────────────┘
                 │
        ┌────────▼────────────────────────────┐
        │                                       │
        ▼                                       ▼
┌───────────────┐                    ┌────────────────┐
│ 检查触发文件   │                    │ daily-meditation│
│ 发送汇总      │                    │ (每日凌晨)      │
└───────────────┘                    └────────────────┘
        │                                       │
        ▼                                       ▼
┌───────────────┐                    ┌────────────────┐
│ Twitter 汇总  │◄────────────────────│ 记录今日活动    │
│ A股监控       │    Cron 定时        │ Git 提交统计    │
│ 天气报告      │                    │ 系统状态检查    │
└───────────────┘                    └────────────────┘
```

---

*本文档持续更新中...*
