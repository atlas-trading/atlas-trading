"""Main Paper Trading Engine with Redis integration."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Optional

import redis
import logging

from .models import Order, Position, Trade, AccountState
from .order_executor import OrderExecutor
from .position_manager import PositionManager
from .risk_manager import RiskManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class PaperTradingEngine:
    """Paper trading engine with realistic market simulation."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        risk_limits: Optional[RiskLimits] = None,
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.risk_per_trade = risk_per_trade

        # Components
        self.order_executor = OrderExecutor()
        self.position_manager = PositionManager()
        self.risk_manager = RiskManager(initial_capital, risk_limits)

        # Redis client
        self.redis_client: Optional[redis.Redis] = None

        # Market data cache
        self.market_prices: Dict[str, float] = {}
        self.market_volatility: Dict[str, float] = {}

        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.trade_history: list[Trade] = []

        # Performance tracking
        self.last_update_time = datetime.now()
        self.equity_curve: list[tuple[datetime, float]] = [(datetime.now(), initial_capital)]

    async def connect_redis(self) -> None:
        """Connect to Redis."""
        self.redis_client = redis.Redis(
            host=self.redis_host, port=self.redis_port, decode_responses=True
        )
        await self.redis_client.ping()
        logger.info("Connected to Redis", host=self.redis_host, port=self.redis_port)

    async def disconnect_redis(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def run(self, symbols: list[str], strategies: list[str]) -> None:
        """
        Main execution loop.

        Args:
            symbols: List of symbols to trade (e.g., ['BTCUSDT'])
            strategies: List of strategy names to follow (e.g., ['Statistical Arbitrage'])
        """
        await self.connect_redis()

        print("=" * 80)
        print("🚀 Paper Trading Engine Started")
        print(f"💰 Initial Capital: ${self.capital:,.2f}")
        print(f"📊 Symbols: {', '.join(symbols)}")
        print(f"🎯 Strategies: {', '.join(strategies)}")
        print(f"⚠️  Risk per Trade: {self.risk_per_trade * 100:.1f}%")
        print("=" * 80)
        print()

        # Redis stream IDs
        last_ids: Dict[str, str] = {}

        # Subscribe to strategy signals
        for strategy in strategies:
            last_ids[f"signals:{strategy}"] = "0"

        # Subscribe to market data for each symbol
        for symbol in symbols:
            last_ids[f"trades:{symbol}"] = "0"

        try:
            while True:
                # Read from Redis streams (100ms timeout)
                if self.redis_client:
                    results = await self.redis_client.xread(last_ids, block=100, count=10)

                    for stream_name, messages in results:
                        for message_id, data in messages:
                            last_ids[stream_name] = message_id

                            # Handle strategy signals
                            if stream_name.startswith("signals:"):
                                signal_data = json.loads(data.get("data", "{}"))
                                await self.handle_signal(signal_data)

                            # Handle market data updates
                            elif stream_name.startswith("trades:"):
                                market_data = json.loads(data.get("data", "{}"))
                                await self.update_market_price(market_data)

                # Monitor positions for exit conditions
                await self.monitor_positions()

                # Update equity curve every second
                await self.update_equity_curve()

                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            print("\n🛑 Stopping Paper Trading Engine...")
            await self.print_final_report()
        finally:
            await self.disconnect_redis()

    async def handle_signal(self, signal: dict) -> None:
        """
        Handle trading signal from strategy.

        Expected signal format:
        {
            "action": "long" | "short" | "close",
            "symbol": "BTCUSDT",
            "price": 67850.00,
            "timestamp": "2026-02-17T20:15:32",
            "confidence": 0.85,
            "stop_loss_pct": 0.02,  # 2%
            "take_profit_pct": 0.04  # 4%
        }
        """
        action = signal.get("action")
        symbol = signal.get("symbol")
        price = signal.get("price")

        if not all([action, symbol, price]):
            logger.warning("Incomplete signal received", signal=signal)
            return

        logger.info("Received signal", action=action, symbol=symbol, price=price)

        if action in ["long", "short"]:
            await self.handle_entry_signal(signal)
        elif action == "close":
            await self.handle_exit_signal(signal)

    async def handle_entry_signal(self, signal: dict) -> None:
        """Handle entry signal (open position)."""
        symbol = signal["symbol"]
        action = signal["action"]
        price = signal["price"]

        # Check if we already have a position
        if self.position_manager.has_position(symbol):
            logger.info("Position already exists for symbol", symbol=symbol)
            return

        # Check risk limits
        open_positions = self.position_manager.get_position_count()
        can_open, reason = self.risk_manager.can_open_position(
            self.capital, self.total_pnl, open_positions
        )

        if not can_open:
            print(f"⚠️  Risk limit: {reason}")
            return

        # Calculate position size
        stop_loss_pct = signal.get("stop_loss_pct", 0.02)
        take_profit_pct = signal.get("take_profit_pct", 0.04)

        side = "long" if action == "long" else "short"
        stop_loss = self.risk_manager.calculate_stop_loss(price, side, stop_loss_pct)
        take_profit = self.risk_manager.calculate_take_profit(
            price, stop_loss, side, take_profit_pct / stop_loss_pct
        )

        # Validate risk/reward
        if not self.risk_manager.validate_risk_reward(price, stop_loss, take_profit, side):
            print(f"⚠️  Risk/reward ratio too low for {symbol}")
            return

        # Calculate position size
        quantity = self.risk_manager.calculate_position_size(
            self.capital, self.risk_per_trade, price, stop_loss
        )

        if quantity <= 0:
            print(f"⚠️  Position size too small for {symbol}")
            return

        # Create and execute order
        order = Order(
            symbol=symbol, side="buy" if action == "long" else "sell", quantity=quantity, price=price
        )

        volatility = self.market_volatility.get(symbol, 0.02)
        trade = await self.order_executor.execute_order(order, price, volatility)

        # Open position
        position = self.position_manager.open_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=trade.price,
            commission=trade.commission,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Update capital
        position_value = trade.price * quantity
        self.capital -= position_value + trade.commission

        # Update stats
        self.total_trades += 1
        self.trade_history.append(trade)

        # Print entry
        slippage_pct = trade.slippage * 100
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{'🟢 LONG' if side == 'long' else '🔴 SHORT'} "
              f"{symbol} @ ${trade.price:,.2f} × {quantity:.6f}")
        print(f"  Entry: ${trade.price:,.2f} (slippage: {slippage_pct:.2f}%)")
        print(f"  Commission: ${trade.commission:.2f} ({trade.commission/position_value*100:.2f}%)")
        print(f"  Stop Loss: ${stop_loss:,.2f} ({(stop_loss/price-1)*100:.2f}%)")
        print(f"  Take Profit: ${take_profit:,.2f} ({(take_profit/price-1)*100:.2f}%)")
        print()

    async def handle_exit_signal(self, signal: dict) -> None:
        """Handle exit signal (close position)."""
        symbol = signal["symbol"]
        price = signal["price"]

        if not self.position_manager.has_position(symbol):
            logger.info("No position to close", symbol=symbol)
            return

        await self.close_position(symbol, price, "signal")

    async def close_position(self, symbol: str, price: float, reason: str) -> None:
        """Close a position."""
        position = self.position_manager.get_position(symbol)
        if not position:
            return

        # Execute closing order
        order = Order(
            symbol=symbol,
            side="sell" if position.side == "long" else "buy",
            quantity=position.quantity,
            price=price,
        )

        volatility = self.market_volatility.get(symbol, 0.02)
        closing_trade = await self.order_executor.execute_order(order, price, volatility)

        # Close position
        trade = self.position_manager.close_position(symbol, closing_trade.price, closing_trade.commission)

        if trade and trade.pnl is not None:
            # Update capital
            position_value = closing_trade.price * position.quantity
            self.capital += position_value - closing_trade.commission

            # Update stats
            self.total_pnl += trade.pnl
            self.risk_manager.update_daily_pnl(trade.pnl)

            if trade.pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1

            self.trade_history.append(trade)

            # Print exit
            pnl_pct = (trade.pnl / (position.entry_price * position.quantity)) * 100
            emoji = "✅" if trade.pnl > 0 else "❌"
            reason_text = {
                "stop_loss": "STOP LOSS",
                "take_profit": "TAKE PROFIT",
                "signal": "SIGNAL",
            }.get(reason, "CLOSE")

            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                  f"{emoji} {reason_text} {symbol} @ ${closing_trade.price:,.2f}")
            print(f"  Exit: ${closing_trade.price:,.2f}")
            print(f"  Commission: ${closing_trade.commission:.2f}")
            print(f"  Realized PnL: {'+' if trade.pnl >= 0 else ''}{trade.pnl:.2f} USD ({pnl_pct:+.2f}%)")
            print()

    async def update_market_price(self, market_data: dict) -> None:
        """
        Update market price from trade data.

        Expected format:
        {
            "symbol": "BTCUSDT",
            "price": 67850.00,
            "volume": 1.234,
            "timestamp": "2026-02-17T20:15:32"
        }
        """
        symbol = market_data.get("symbol")
        price = market_data.get("price")

        if not symbol or not price:
            return

        # Update price cache
        old_price = self.market_prices.get(symbol)
        self.market_prices[symbol] = price

        # Calculate volatility (simple method: % change)
        if old_price:
            price_change_pct = abs((price - old_price) / old_price)
            # Exponential moving average of volatility
            old_vol = self.market_volatility.get(symbol, 0.02)
            self.market_volatility[symbol] = old_vol * 0.9 + price_change_pct * 0.1

        # Update position prices
        self.position_manager.update_position_price(symbol, price)

    async def monitor_positions(self) -> None:
        """Monitor positions for stop loss and take profit triggers."""
        for symbol, position in list(self.position_manager.positions.items()):
            current_price = self.market_prices.get(symbol)
            if not current_price:
                continue

            # Check exit conditions
            exit_condition = self.position_manager.check_exit_conditions(symbol, current_price)
            if exit_condition:
                reason, description = exit_condition
                logger.info("Exit condition triggered", symbol=symbol, reason=reason, desc=description)
                await self.close_position(symbol, current_price, reason)

    async def update_equity_curve(self) -> None:
        """Update equity curve with current portfolio value."""
        now = datetime.now()
        if (now - self.last_update_time).total_seconds() >= 1.0:
            total_equity = self.capital + self.position_manager.get_total_unrealized_pnl()
            self.equity_curve.append((now, total_equity))
            self.last_update_time = now

            # Print status every 10 seconds
            if len(self.equity_curve) % 10 == 0:
                await self.print_status()

    async def print_status(self) -> None:
        """Print current status."""
        total_equity = self.capital + self.position_manager.get_total_unrealized_pnl()
        pnl = total_equity - self.initial_capital
        pnl_pct = (pnl / self.initial_capital) * 100

        win_rate = (
            (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        )

        print("=" * 80)
        print(f"💰 Balance: ${self.capital:,.2f} | "
              f"Total Equity: ${total_equity:,.2f} | "
              f"PnL: {'+' if pnl >= 0 else ''}{pnl:.2f} ({pnl_pct:+.2f}%)")
        print(f"📊 Trades: {self.total_trades} | "
              f"Win Rate: {win_rate:.1f}% ({self.winning_trades}W/{self.losing_trades}L) | "
              f"Positions: {self.position_manager.get_position_count()}")
        print("=" * 80)
        print()

    async def print_final_report(self) -> None:
        """Print final performance report."""
        total_equity = self.capital + self.position_manager.get_total_unrealized_pnl()
        total_pnl = total_equity - self.initial_capital
        total_return_pct = (total_pnl / self.initial_capital) * 100

        win_rate = (
            (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0.0
        )

        print("\n")
        print("=" * 80)
        print("📊 FINAL PERFORMANCE REPORT")
        print("=" * 80)
        print(f"Initial Capital:     ${self.initial_capital:>15,.2f}")
        print(f"Final Equity:        ${total_equity:>15,.2f}")
        print(f"Total PnL:           ${total_pnl:>15,.2f} ({total_return_pct:+.2f}%)")
        print(f"Total Trades:        {self.total_trades:>15}")
        print(f"Winning Trades:      {self.winning_trades:>15}")
        print(f"Losing Trades:       {self.losing_trades:>15}")
        print(f"Win Rate:            {win_rate:>14.2f}%")
        print(f"Open Positions:      {self.position_manager.get_position_count():>15}")
        print("=" * 80)


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Engine")
    parser.add_argument("--capital", type=float, default=10000.0, help="Initial capital")
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT"], help="Trading symbols")
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["Statistical Arbitrage"],
        help="Strategy names",
    )
    parser.add_argument("--risk", type=float, default=0.02, help="Risk per trade (0.02 = 2%)")
    parser.add_argument("--redis-host", default="localhost", help="Redis host")
    parser.add_argument("--redis-port", type=int, default=6379, help="Redis port")

    args = parser.parse_args()

    engine = PaperTradingEngine(
        initial_capital=args.capital,
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        risk_per_trade=args.risk,
    )

    await engine.run(symbols=args.symbols, strategies=args.strategies)


if __name__ == "__main__":
    asyncio.run(main())
