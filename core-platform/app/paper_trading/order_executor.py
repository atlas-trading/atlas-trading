"""Order execution simulator with realistic slippage, fees, and latency."""

import asyncio
import random
from datetime import datetime
from typing import Optional

from .models import Order, Trade


class OrderExecutor:
    """Simulates realistic order execution with market conditions."""

    def __init__(
        self,
        base_slippage: float = 0.0005,  # 0.05%
        maker_fee: float = 0.0002,  # 0.02% Binance maker
        taker_fee: float = 0.0004,  # 0.04% Binance taker
    ):
        self.base_slippage = base_slippage
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee

    def calculate_slippage(
        self, order_size: float, market_volatility: float = 0.02
    ) -> float:
        """
        Calculate slippage based on order size and market volatility.

        Slippage ranges:
        - Small orders (<$10k): 0.02-0.05%
        - Medium orders ($10k-$50k): 0.05-0.10%
        - Large orders (>$50k): 0.10-0.20%

        Args:
            order_size: Order size in USD notional value
            market_volatility: Current market volatility (default 2%)

        Returns:
            Slippage percentage (e.g., 0.0008 = 0.08%)
        """
        # Base slippage
        slippage = self.base_slippage

        # Size impact: larger orders have more slippage
        if order_size < 10000:
            size_factor = order_size / 10000 * 0.0003  # up to 0.03%
        elif order_size < 50000:
            size_factor = 0.0003 + (order_size - 10000) / 40000 * 0.0005  # 0.03-0.08%
        else:
            size_factor = 0.0008 + min((order_size - 50000) / 100000, 1.0) * 0.0012  # 0.08-0.20%

        # Volatility impact
        volatility_factor = market_volatility * 0.02  # up to 0.04% for high volatility

        # Random noise to simulate market conditions
        noise = random.uniform(-0.0001, 0.0001)

        return slippage + size_factor + volatility_factor + noise

    def calculate_commission(self, quantity: float, price: float, order_type: str) -> float:
        """
        Calculate commission based on Binance fee structure.

        Args:
            quantity: Order quantity
            price: Execution price
            order_type: 'market' or 'limit'

        Returns:
            Commission in USD
        """
        notional = quantity * price
        fee_rate = self.maker_fee if order_type == "limit" else self.taker_fee
        return notional * fee_rate

    async def simulate_order_latency(self, order_type: str = "market") -> None:
        """
        Simulate realistic network and exchange latency.

        Latency components:
        - Signal generation → Order submission: 50-200ms
        - Order submission → Execution: 10-100ms
        - Limit orders have slightly longer matching time

        Args:
            order_type: 'market' or 'limit'
        """
        # Order submission latency
        order_latency = random.uniform(0.05, 0.20)  # 50-200ms

        # Execution latency
        if order_type == "market":
            fill_latency = random.uniform(0.01, 0.05)  # 10-50ms (fast)
        else:
            fill_latency = random.uniform(0.05, 0.15)  # 50-150ms (slower for matching)

        total_latency = order_latency + fill_latency
        await asyncio.sleep(total_latency)

    async def execute_order(
        self, order: Order, current_price: float, market_volatility: float = 0.02
    ) -> Trade:
        """
        Execute an order with realistic market simulation.

        Args:
            order: Order to execute
            current_price: Current market price
            market_volatility: Current market volatility

        Returns:
            Trade record
        """
        # Simulate order latency
        await self.simulate_order_latency(order.type)

        # Calculate order size in USD
        order_size = order.quantity * current_price

        # Calculate slippage
        slippage_pct = self.calculate_slippage(order_size, market_volatility)

        # Apply slippage based on order side
        if order.side == "buy":
            # Buying: price moves against us (higher)
            execution_price = current_price * (1 + slippage_pct)
        else:
            # Selling: price moves against us (lower)
            execution_price = current_price * (1 - slippage_pct)

        # For limit orders, use limit price if better
        if order.type == "limit" and order.price is not None:
            if order.side == "buy":
                execution_price = min(execution_price, order.price)
            else:
                execution_price = max(execution_price, order.price)

        # Calculate commission
        commission = self.calculate_commission(order.quantity, execution_price, order.type)

        # Update order status
        order.status = "filled"
        order.filled_at = datetime.now()
        order.filled_price = execution_price
        order.commission = commission
        order.slippage = slippage_pct

        # Create trade record
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=execution_price,
            commission=commission,
            slippage=slippage_pct,
            timestamp=datetime.now(),
        )

        return trade

    def estimate_execution_price(
        self,
        side: str,
        quantity: float,
        current_price: float,
        market_volatility: float = 0.02,
    ) -> tuple[float, float]:
        """
        Estimate execution price before submitting order.

        Returns:
            (estimated_price, estimated_slippage_pct)
        """
        order_size = quantity * current_price
        slippage_pct = self.calculate_slippage(order_size, market_volatility)

        if side == "buy":
            estimated_price = current_price * (1 + slippage_pct)
        else:
            estimated_price = current_price * (1 - slippage_pct)

        return estimated_price, slippage_pct
