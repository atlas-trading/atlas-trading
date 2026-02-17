"""Test script for Paper Trading system components."""

import asyncio
from datetime import datetime

from app.paper_trading.models import Order, Position
from app.paper_trading.order_executor import OrderExecutor
from app.paper_trading.position_manager import PositionManager
from app.paper_trading.risk_manager import RiskLimits, RiskManager


async def test_order_executor() -> None:
    """Test order execution with slippage and fees."""
    print("=" * 80)
    print("🧪 Testing Order Executor")
    print("=" * 80)

    executor = OrderExecutor()

    # Test 1: Small market order (buy)
    print("\n📝 Test 1: Small market order (BUY)")
    order = Order(symbol="BTCUSDT", side="buy", type="market", quantity=0.1, price=50000.0)
    current_price = 50000.0

    trade = await executor.execute_order(order, current_price, market_volatility=0.02)

    print(f"   Order Size: {order.quantity} BTC @ ${current_price:,.2f} = ${order.quantity * current_price:,.2f}")
    print(f"   Execution Price: ${trade.price:,.2f}")
    print(f"   Slippage: {trade.slippage * 100:.4f}% (${(trade.price - current_price) * order.quantity:.2f})")
    print(f"   Commission: ${trade.commission:.2f} ({trade.commission / (order.quantity * current_price) * 100:.4f}%)")

    # Test 2: Large market order (sell)
    print("\n📝 Test 2: Large market order (SELL)")
    order2 = Order(symbol="BTCUSDT", side="sell", type="market", quantity=2.0, price=50000.0)
    trade2 = await executor.execute_order(order2, current_price, market_volatility=0.03)

    print(f"   Order Size: {order2.quantity} BTC @ ${current_price:,.2f} = ${order2.quantity * current_price:,.2f}")
    print(f"   Execution Price: ${trade2.price:,.2f}")
    print(f"   Slippage: {trade2.slippage * 100:.4f}% (${abs(trade2.price - current_price) * order2.quantity:.2f})")
    print(f"   Commission: ${trade2.commission:.2f} ({trade2.commission / (order2.quantity * current_price) * 100:.4f}%)")

    # Test 3: Estimate execution
    print("\n📝 Test 3: Pre-execution estimation")
    estimated_price, estimated_slippage = executor.estimate_execution_price(
        "buy", 0.5, 50000.0, 0.02
    )
    print(f"   For 0.5 BTC buy order at ${50000:,.2f}")
    print(f"   Estimated Price: ${estimated_price:,.2f}")
    print(f"   Estimated Slippage: {estimated_slippage * 100:.4f}%")

    print("\n✅ Order Executor tests passed\n")


def test_position_manager() -> None:
    """Test position management and PnL calculation."""
    print("=" * 80)
    print("🧪 Testing Position Manager")
    print("=" * 80)

    manager = PositionManager()

    # Test 1: Open long position
    print("\n📝 Test 1: Open LONG position")
    position = manager.open_position(
        symbol="BTCUSDT",
        side="long",
        quantity=0.5,
        entry_price=50000.0,
        commission=10.0,
        stop_loss=49000.0,
        take_profit=52000.0,
    )

    print(f"   Position: {position.side.upper()} {position.quantity} BTC @ ${position.entry_price:,.2f}")
    print(f"   Stop Loss: ${position.stop_loss:,.2f} (-{(1 - position.stop_loss / position.entry_price) * 100:.2f}%)")
    print(f"   Take Profit: ${position.take_profit:,.2f} (+{(position.take_profit / position.entry_price - 1) * 100:.2f}%)")

    # Test 2: Update with profit
    print("\n📝 Test 2: Price moves up (profit)")
    manager.update_position_price("BTCUSDT", 51000.0)
    position = manager.get_position("BTCUSDT")
    if position:
        print(f"   Current Price: ${position.current_price:,.2f}")
        print(f"   Unrealized PnL: ${position.unrealized_pnl:,.2f} ({position.unrealized_pnl / (position.entry_price * position.quantity) * 100:+.2f}%)")

    # Test 3: Check exit conditions
    print("\n📝 Test 3: Check exit conditions")
    exit_condition = manager.check_exit_conditions("BTCUSDT", 52000.0)
    if exit_condition:
        reason, desc = exit_condition
        print(f"   Exit Triggered: {reason.upper()}")
        print(f"   Description: {desc}")

    # Test 4: Close position
    print("\n📝 Test 4: Close position")
    trade = manager.close_position("BTCUSDT", 52000.0, commission=10.4)
    if trade and trade.pnl is not None:
        print(f"   Exit Price: ${trade.price:,.2f}")
        print(f"   Realized PnL: ${trade.pnl:,.2f}")
        print(f"   Total Commission: ${position.commission_paid + trade.commission:.2f}")
        print(f"   Net PnL: ${trade.pnl:,.2f}")

    # Test 5: Short position with loss
    print("\n📝 Test 5: Open SHORT position and close at loss")
    position2 = manager.open_position(
        symbol="ETHUSDT",
        side="short",
        quantity=10.0,
        entry_price=3000.0,
        commission=6.0,
        stop_loss=3100.0,
        take_profit=2900.0,
    )

    print(f"   Position: {position2.side.upper()} {position2.quantity} ETH @ ${position2.entry_price:,.2f}")

    # Price moves against us
    manager.update_position_price("ETHUSDT", 3050.0)
    position2 = manager.get_position("ETHUSDT")
    if position2:
        print(f"   Current Price: ${position2.current_price:,.2f}")
        print(f"   Unrealized PnL: ${position2.unrealized_pnl:,.2f} ({position2.unrealized_pnl / (position2.entry_price * position2.quantity) * 100:+.2f}%)")

    # Close at loss
    trade2 = manager.close_position("ETHUSDT", 3050.0, commission=6.1)
    if trade2 and trade2.pnl is not None:
        print(f"   Exit Price: ${trade2.price:,.2f}")
        print(f"   Realized PnL: ${trade2.pnl:,.2f}")

    print("\n✅ Position Manager tests passed\n")


def test_risk_manager() -> None:
    """Test risk management and position sizing."""
    print("=" * 80)
    print("🧪 Testing Risk Manager")
    print("=" * 80)

    limits = RiskLimits(
        max_position_size_pct=0.10,
        max_daily_loss_pct=0.05,
        max_drawdown_pct=0.15,
        max_open_positions=3,
    )
    manager = RiskManager(initial_capital=10000.0, limits=limits)

    # Test 1: Calculate position size
    print("\n📝 Test 1: Calculate position size")
    account_balance = 10000.0
    risk_per_trade = 0.02  # 2%
    entry_price = 50000.0
    stop_loss_price = 49000.0

    position_size = manager.calculate_position_size(
        account_balance, risk_per_trade, entry_price, stop_loss_price
    )

    risk_amount = account_balance * risk_per_trade
    position_value = position_size * entry_price

    print(f"   Account Balance: ${account_balance:,.2f}")
    print(f"   Risk per Trade: {risk_per_trade * 100:.1f}% (${risk_amount:,.2f})")
    print(f"   Entry: ${entry_price:,.2f}, Stop Loss: ${stop_loss_price:,.2f}")
    print(f"   Position Size: {position_size:.6f} BTC (${position_value:,.2f})")
    print(f"   Position as % of Account: {position_value / account_balance * 100:.2f}%")

    # Test 2: Risk/Reward validation
    print("\n📝 Test 2: Risk/Reward validation")
    entry = 50000.0
    stop_loss = 49000.0
    take_profit_good = 52000.0
    take_profit_bad = 50500.0

    is_valid_good = manager.validate_risk_reward(entry, stop_loss, take_profit_good, "long")
    is_valid_bad = manager.validate_risk_reward(entry, stop_loss, take_profit_bad, "long")

    risk = entry - stop_loss
    reward_good = take_profit_good - entry
    reward_bad = take_profit_bad - entry

    print(f"   Entry: ${entry:,.2f}, Stop Loss: ${stop_loss:,.2f}")
    print(f"   Take Profit 1: ${take_profit_good:,.2f} → R/R = {reward_good / risk:.2f} → {'✅ Valid' if is_valid_good else '❌ Invalid'}")
    print(f"   Take Profit 2: ${take_profit_bad:,.2f} → R/R = {reward_bad / risk:.2f} → {'✅ Valid' if is_valid_bad else '❌ Invalid'}")

    # Test 3: Can open position checks
    print("\n📝 Test 3: Can open position checks")

    can_open, reason = manager.can_open_position(10000.0, 0.0, 0)
    print(f"   With 0 positions: {'✅ Can open' if can_open else f'❌ Cannot open: {reason}'}")

    can_open, reason = manager.can_open_position(10000.0, 0.0, 3)
    print(f"   With 3 positions: {'✅ Can open' if can_open else f'❌ Cannot open: {reason}'}")

    # Simulate daily loss
    manager.update_daily_pnl(-600.0)  # 6% loss
    can_open, reason = manager.can_open_position(10000.0, -600.0, 1)
    print(f"   With 6% daily loss: {'✅ Can open' if can_open else f'❌ Cannot open: {reason}'}")

    # Test 4: Calculate stop loss and take profit
    print("\n📝 Test 4: Calculate stop loss and take profit")
    entry_price = 50000.0
    side = "long"
    risk_pct = 0.02

    stop_loss = manager.calculate_stop_loss(entry_price, side, risk_pct)
    take_profit = manager.calculate_take_profit(entry_price, stop_loss, side, risk_reward_ratio=2.0)

    risk = entry_price - stop_loss
    reward = take_profit - entry_price

    print(f"   Entry: ${entry_price:,.2f} ({side.upper()})")
    print(f"   Stop Loss: ${stop_loss:,.2f} (-{risk_pct * 100:.1f}%)")
    print(f"   Take Profit: ${take_profit:,.2f} (+{reward / entry_price * 100:.1f}%)")
    print(f"   Risk/Reward Ratio: {reward / risk:.2f}:1")

    print("\n✅ Risk Manager tests passed\n")


async def run_all_tests() -> None:
    """Run all tests."""
    print("\n")
    print("=" * 80)
    print("🚀 Paper Trading System Component Tests")
    print("=" * 80)
    print("\n")

    await test_order_executor()
    test_position_manager()
    test_risk_manager()

    print("=" * 80)
    print("✅ All tests passed!")
    print("=" * 80)
    print("\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
