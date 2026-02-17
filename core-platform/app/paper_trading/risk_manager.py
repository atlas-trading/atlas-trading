"""Risk management for position sizing and limits."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskLimits:
    """Risk management limits."""

    max_position_size_pct: float = 0.10  # 10% of account per position
    max_daily_loss_pct: float = 0.05  # 5% daily loss limit
    max_drawdown_pct: float = 0.15  # 15% maximum drawdown
    max_open_positions: int = 3  # Maximum simultaneous positions
    min_risk_reward_ratio: float = 1.5  # Minimum 1.5:1 reward:risk


class RiskManager:
    """Manages risk limits and position sizing."""

    def __init__(self, initial_capital: float, limits: Optional[RiskLimits] = None):
        self.initial_capital = initial_capital
        self.limits = limits or RiskLimits()
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital

    def calculate_position_size(
        self,
        account_balance: float,
        risk_per_trade_pct: float,
        entry_price: float,
        stop_loss_price: float,
    ) -> float:
        """
        Calculate position size based on risk management.

        Uses fixed fractional position sizing:
        position_size = (account_balance * risk_pct) / (entry_price - stop_loss_price)

        Args:
            account_balance: Current account balance
            risk_per_trade_pct: Risk percentage per trade (e.g., 0.02 = 2%)
            entry_price: Planned entry price
            stop_loss_price: Stop loss price

        Returns:
            Position size (quantity)
        """
        # Calculate risk amount in USD
        risk_amount = account_balance * risk_per_trade_pct

        # Calculate price risk per unit
        price_risk = abs(entry_price - stop_loss_price)

        if price_risk == 0:
            return 0.0

        # Calculate position size
        position_size = risk_amount / price_risk

        # Apply maximum position size limit
        max_position_value = account_balance * self.limits.max_position_size_pct
        max_quantity = max_position_value / entry_price

        return min(position_size, max_quantity)

    def validate_risk_reward(
        self, entry_price: float, stop_loss: float, take_profit: float, side: str
    ) -> bool:
        """
        Validate risk/reward ratio meets minimum requirements.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            side: 'long' or 'short'

        Returns:
            True if risk/reward ratio is acceptable
        """
        if side == "long":
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # short
            risk = stop_loss - entry_price
            reward = entry_price - take_profit

        if risk <= 0:
            return False

        risk_reward_ratio = reward / risk
        return risk_reward_ratio >= self.limits.min_risk_reward_ratio

    def can_open_position(
        self, current_balance: float, current_pnl: float, open_positions: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if new position can be opened based on risk limits.

        Args:
            current_balance: Current account balance
            current_pnl: Total PnL
            open_positions: Number of open positions

        Returns:
            (can_open, reason) tuple. reason is None if allowed.
        """
        # Check position count limit
        if open_positions >= self.limits.max_open_positions:
            return False, f"Max positions reached ({self.limits.max_open_positions})"

        # Check daily loss limit
        daily_loss_pct = abs(self.daily_pnl) / self.initial_capital
        if self.daily_pnl < 0 and daily_loss_pct >= self.limits.max_daily_loss_pct:
            return False, f"Daily loss limit reached ({daily_loss_pct:.2%})"

        # Check maximum drawdown
        self.peak_capital = max(self.peak_capital, current_balance)
        drawdown_pct = (self.peak_capital - current_balance) / self.peak_capital
        if drawdown_pct >= self.limits.max_drawdown_pct:
            return False, f"Max drawdown reached ({drawdown_pct:.2%})"

        return True, None

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily PnL tracking."""
        self.daily_pnl += pnl

    def reset_daily_pnl(self) -> None:
        """Reset daily PnL (call at start of new trading day)."""
        self.daily_pnl = 0.0

    def get_max_position_value(self, account_balance: float) -> float:
        """Get maximum position value based on account balance."""
        return account_balance * self.limits.max_position_size_pct

    def calculate_stop_loss(
        self, entry_price: float, side: str, risk_pct: float = 0.02
    ) -> float:
        """
        Calculate stop loss price based on risk percentage.

        Args:
            entry_price: Entry price
            side: 'long' or 'short'
            risk_pct: Risk percentage (default 2%)

        Returns:
            Stop loss price
        """
        if side == "long":
            return entry_price * (1 - risk_pct)
        else:  # short
            return entry_price * (1 + risk_pct)

    def calculate_take_profit(
        self, entry_price: float, stop_loss: float, side: str, risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit price based on risk/reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: 'long' or 'short'
            risk_reward_ratio: Desired risk/reward ratio (default 2.0)

        Returns:
            Take profit price
        """
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio

        if side == "long":
            return entry_price + reward
        else:  # short
            return entry_price - reward
