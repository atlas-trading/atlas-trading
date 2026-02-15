#!/bin/bash
# Quick Dev Verification (타입 에러 무시, Dev 서버만 확인)

set -e
echo "⚡ Quick Dev Verification..."

# 1. Dev 서버 재시작
echo "🔄 Restarting dev server..."
pkill -f "vite" 2>/dev/null || true
sleep 1

nohup npm run dev > /tmp/vite-dev.log 2>&1 &
sleep 5

# 2. Health Check
echo "🏥 Checking server..."
for i in {1..10}; do
    if curl -s http://localhost:5173 > /dev/null; then
        echo "✅ Server is responding!"
        echo "🌐 http://localhost:5173"
        exit 0
    fi
    sleep 1
done

echo "❌ Server failed!"
tail -20 /tmp/vite-dev.log
exit 1
