#!/bin/bash
# AI Team Platform 启动脚本
cd "$(dirname "$0")"

# 检查端口是否被占用
if lsof -i :8765 &>/dev/null; then
  echo "⚠️  端口 8765 已被占用，服务可能已在运行"
  echo "访问：http://localhost:8765"
  exit 0
fi

echo "🚀 启动 AI Team Platform..."
nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 8765 > /tmp/ai_team.log 2>&1 &
PID=$!
echo "PID: $PID"
sleep 2

if lsof -i :8765 &>/dev/null; then
  echo "✅ 启动成功！访问：http://localhost:8765"
else
  echo "❌ 启动失败，查看日志：tail -f /tmp/ai_team.log"
fi
