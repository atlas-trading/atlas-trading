#!/bin/bash

set -e

echo "🚀 Starting Paper Trading System"
echo "=================================="
echo ""

# Configuration
CAPITAL=${CAPITAL:-10000}
SYMBOLS=${SYMBOLS:-"BTCUSDT"}
STRATEGIES=${STRATEGIES:-"Statistical Arbitrage"}
RISK=${RISK:-0.02}
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}

# Check Redis is running
if ! redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
    echo "❌ Redis is not running at $REDIS_HOST:$REDIS_PORT"
    echo "Please start Redis first:"
    echo "  redis-server"
    exit 1
fi

echo "✅ Redis is running"
echo ""

# Start Go engine in background (data collection + strategies)
if [ -d "/Users/jang-yeonghwan/atlas-trading/go-engine" ]; then
    echo "🔧 Starting Go Real-time Engine..."
    cd /Users/jang-yeonghwan/atlas-trading/go-engine

    # Check if demo script exists
    if [ -f "./scripts/demo_live_trading.sh" ]; then
        ./scripts/demo_live_trading.sh &
        GO_ENGINE_PID=$!
        echo "✅ Go Engine started (PID: $GO_ENGINE_PID)"

        # Wait for Go engine to initialize
        sleep 5
    else
        echo "⚠️  Go engine demo script not found, skipping..."
    fi
else
    echo "⚠️  Go engine directory not found, skipping..."
fi

echo ""
echo "🐍 Starting Paper Trading Engine..."
echo "   Capital: \$$CAPITAL"
echo "   Symbols: $SYMBOLS"
echo "   Strategies: $STRATEGIES"
echo "   Risk per Trade: $(echo "$RISK * 100" | bc)%"
echo ""

# Start Paper Trading Engine
cd /Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform

python3 -m app.paper_trading.engine \
    --capital "$CAPITAL" \
    --symbols $SYMBOLS \
    --strategies "$STRATEGIES" \
    --risk "$RISK" \
    --redis-host "$REDIS_HOST" \
    --redis-port "$REDIS_PORT"

# Cleanup on exit
if [ -n "$GO_ENGINE_PID" ]; then
    echo ""
    echo "🛑 Stopping Go Engine..."
    kill $GO_ENGINE_PID 2>/dev/null || true
fi

echo ""
echo "✅ Paper Trading System stopped"
