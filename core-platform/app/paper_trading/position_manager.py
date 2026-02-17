"""Position management with PnL tracking and exit conditions."""

from datetime import datetime
from typing import Dict, Optional

from .models import Position, Trade


class PositionManager:
    """Manages trading positions with real-time PnL calculation."""

    def __init__(self) -> None:
        self.positions: Dict[str, Position] = {}

    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        commission: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Position:
        """
        Open a new position.

        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            quantity: Position size
            entry_price: Entry price
            commission: Commission paid on entry
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Created position
        """
        position = Position(
            symbol=symbol,
            side=side,  # type: ignore
            quantity=quantity,
            entry_price=entry_price,
            entry_time=datetime.now(),
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission_paid=commission,
        )

        self.positions[symbol] = position
        return position

    def close_position(
        self, symbol: str, exit_price: float, commission: float = 0.0
    ) -> Optional[Trade]:
        """
        Close an existing position.

        Args:
            symbol: Trading symbol
            exit_price: Exit price
            commission: Commission paid on exit

        Returns:
            Trade record with realized PnL, or None if position doesn't exist
        """
        position = self.positions.get(symbol)
        if not position:
            return None

        # Calculate realized PnL
        realized_pnl = self.calculate_realized_pnl(position, exit_price)
        realized_pnl -= position.commission_paid + commission  # subtract total commissions

        # Create closing trade record
        trade = Trade(
            symbol=symbol,
            side="sell" if position.side == "long" else "buy",
            quantity=position.quantity,
            price=exit_price,
            commission=commission,
            timestamp=datetime.now(),
            pnl=realized_pnl,
        )

        # Remove position
        del self.positions[symbol]

        return trade

    def update_position_price(self, symbol: str, current_price: float) -> None:
        """
        Update position with current market price.

        Args:
            symbol: Trading symbol
            current_price: Current market price
        """
        position = self.positions.get(symbol)
        if position:
            position.current_price = current_price
            position.unrealized_pnl = self.calculate_unrealized_pnl(position, current_price)

    def calculate_unrealized_pnl(self, position: Position, current_price: float) -> float:
        """
        Calculate unrealized PnL for a position.

        Formula:
        - Long: (current_price - entry_price) * quantity
        - Short: (entry_price - current_price) * quantity

        Args:
            position: Position to calculate
            current_price: Current market price

        Returns:
            Unrealized PnL in USD
        """
        if position.side == "long":
            pnl = (current_price - position.entry_price) * position.quantity
        else:  # short
            pnl = (position.entry_price - current_price) * position.quantity

        return pnl

    def calculate_realized_pnl(self, position: Position, exit_price: float) -> float:
        """
        Calculate realized PnL for a closing position (before commissions).

        Args:
            position: Position being closed
            exit_price: Exit price

        Returns:
            Realized PnL in USD (before commissions)
        """
        if position.side == "long":
            pnl = (exit_price - position.entry_price) * position.quantity
        else:  # short
            pnl = (position.entry_price - exit_price) * position.quantity

        return pnl

    def check_exit_conditions(
        self, symbol: str, current_price: float
    ) -> Optional[tuple[str, str]]:
        """
        Check if position should be closed due to stop loss or take profit.

        Args:
            symbol: Trading symbol
            current_price: Current market price

        Returns:
            (reason, description) tuple if exit triggered, None otherwise
            Reasons: 'stop_loss', 'take_profit'
        """
        position = self.positions.get(symbol)
        if not position:
            return None

        if position.side == "long":
            # Long position: stop loss below, take profit above
            if position.stop_loss and current_price <= position.stop_loss:
                return ("stop_loss", f"Price ${current_price:,.2f} <= SL ${position.stop_loss:,.2f}")
            if position.take_profit and current_price >= position.take_profit:
                return (
                    "take_profit",
                    f"Price ${current_price:,.2f} >= TP ${position.take_profit:,.2f}",
                )

        else:  # short
            # Short position: stop loss above, take profit below
            if position.stop_loss and current_price >= position.stop_loss:
                return ("stop_loss", f"Price ${current_price:,.2f} >= SL ${position.stop_loss:,.2f}")
            if position.take_profit and current_price <= position.take_profit:
                return (
                    "take_profit",
                    f"Price ${current_price:,.2f} <= TP ${position.take_profit:,.2f}",
                )

        return None

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self.positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        """Check if position exists for a symbol."""
        return symbol in self.positions

    def get_total_unrealized_pnl(self) -> float:
        """Calculate total unrealized PnL across all positions."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_position_count(self) -> int:
        """Get number of open positions."""
        return len(self.positions)
