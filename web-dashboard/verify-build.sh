#!/bin/bash
# Web Build Verification Script
# 코드 변경 후 웹이 정상 작동하는지 자동 검증

set -e  # 에러 발생 시 중단

echo "🔍 Starting Web Verification..."

# 1. TypeScript 컴파일 체크
echo "📝 Checking TypeScript..."
npx tsc --noEmit || {
    echo "❌ TypeScript compilation failed!"
    exit 1
}
echo "✅ TypeScript OK"

# 2. 빌드 테스트
echo "🏗️  Testing build..."
npm run build > /tmp/build-test.log 2>&1 || {
    echo "❌ Build failed! Check /tmp/build-test.log"
    tail -20 /tmp/build-test.log
    exit 1
}
echo "✅ Build OK"

# 3. 개발 서버 시작 (백그라운드)
echo "🚀 Starting dev server..."
pkill -f "vite" 2>/dev/null || true
npm run dev > /tmp/vite-verify.log 2>&1 &
DEV_PID=$!
sleep 5

# 4. Health Check
echo "🏥 Health checking..."
MAX_RETRIES=10
for i in $(seq 1 $MAX_RETRIES); do
    if curl -s http://localhost:5173 > /dev/null; then
        echo "✅ Dev server is responding!"
        echo ""
        echo "🎉 All checks passed!"
        echo "🌐 Web: http://localhost:5173"
        echo "📊 API: http://localhost:8000"
        exit 0
    fi
    echo "   Retry $i/$MAX_RETRIES..."
    sleep 1
done

echo "❌ Dev server failed to respond!"
echo "📋 Last 20 lines of log:"
tail -20 /tmp/vite-verify.log
kill $DEV_PID 2>/dev/null || true
exit 1
