#!/bin/bash
# 简单的循环监控脚本
# 每15分钟运行一次监控

cd /home/node/clawd
while true; do
    bash /home/node/clawd/scripts/a-stock-monitor.sh
    sleep 900  # 15分钟
done
