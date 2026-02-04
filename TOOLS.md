# TIPS.md - 实用经验记录

## Feishu 发送图片
- ❌ 不要用 `read` 返回的 base64（Feishu 不支持显示）
- ✅ 使用 `message` 工具：
  ```javascript
  message({
    action: "send",
    channel: "feishu",
    message: "图片说明",
    media: "/path/to/image.jpg"
  })
  ```

## Moltbot Cron 配置
- `everyMs` = 相对间隔，会 drift
- `cron` 表达式 = 绝对时间，固定整点
- `wakeMode: "now"` = 不依赖 heartbeat，立即执行
- `wakeMode: "next-heartbeat"` = 等待下一个 heartbeat 触发

## ModelScope Z-Image API
- 返回状态字段是 `task_status`，不是 `status`
- 成功状态是 `SUCCEED`，不是 `SUCCESS`
- 图片 URL 在 `output_images[0]`，不是 `outputs.result`
- 需要额外下载图片，不是 base64 直接返回

---
*最后更新: 2026-02-03*
