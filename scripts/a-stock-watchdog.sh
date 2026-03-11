#!/bin/bash
# A股看门狗脚本 - 更新路径

WORKSPACE="/home/node/.openclaw/workspace"
cd "$WORKSPACE" || exit 1

bash "$WORKSPACE/scripts/a-stock-monitor.sh"
