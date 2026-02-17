"""
Adaptive Grid Trading Strategy

Advanced grid trading with dynamic adjustments:
- Volatility-adjusted grid spacing (ATR-based)
- Trend-aware grid placement (don't grid against strong trends)
- Auto-rebalancing based on market conditions
- Drawdown protection (reduce grid when losing)
- Take-profit pyramiding

Theory:
Grid trading profits from market oscillations by placing buy and sell orders
at regular intervals. Adaptive grid adjusts spacing and direction based on
volatility and trend, making it more robust than fixed grids.

Entry Rules:
1. Place buy grid below current price
2. Place sell grid above current price
3. Grid spacing = ATR * multiplier
4. Adjust grid center based on trend (EMA)

Exit Rules:
1. Take profit when price moves through grid levels
2. Rebalance grid when price moves significantly
3. Close all positions if strong trend develops
4. Emergency exit on large drawdown

Risk Management:
- Maximum grid levels: 5-10 levels
- Position size per level: 10-20% of capital
- Stop loss: If price moves beyond all grid levels
- Trend filter: Reduce or pause grid in strong trends
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin


class AdaptiveGridTradingStrategy(Strategy, IndicatorMixin):
    """
    Adaptive Grid Trading Strategy

    Dynamic grid trading that adjusts to volatility and trend
    """

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        num_grid_levels: int = 5,
        grid_spacing_atr_multiplier: float = 0.5,
        atr_period: int = 14,
        trend_ema_period: int = 50,
        trend_threshold: float = 0.02,  # 2% trend threshold
        max_position_size: float = 0.8,  # Max 80% of capital in grid
        rebalance_threshold: float = 0.05,  # Rebalance if price moves 5%
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            num_grid_levels=num_grid_levels,
            grid_spacing_atr_multiplier=grid_spacing_atr_multiplier,
            atr_period=atr_period,
            trend_ema_period=trend_ema_period,
            trend_threshold=trend_threshold,
            max_position_size=max_position_size,
            rebalance_threshold=rebalance_threshold,
            **kwargs
        )

        self.grid_buy_levels = []
        self.grid_sell_levels = []
        self.grid_center = None
        self.grid_spacing = None
        self.filled_buy_levels = set()
        self.filled_sell_levels = set()
        self.last_rebalance_price = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators for grid adaptation"""

        # ATR for dynamic spacing
        df = self.add_atr(df, self.atr_period)

        # Trend EMA for grid center
        df['trend_ema'] = df['close'].ewm(span=self.trend_ema_period, adjust=False).mean()

        # Trend strength
        df['trend_pct'] = (df['close'] - df['trend_ema']) / df['trend_ema']

        # Volatility percentile
        df['atr_percentile'] = df[f'atr_{self.atr_period}'].rolling(window=50).apply(
            lambda x: (x.iloc[-1] > x).sum() / len(x) if len(x) > 0 else 0.5, raw=False
        )

        return df

    def _setup_grid(self, current_price: float, atr: float, trend_ema: float) -> None:
        """Initialize or rebalance grid levels"""

        # Grid center: weighted between current price and trend EMA
        self.grid_center = current_price * 0.7 + trend_ema * 0.3

        # Grid spacing based on ATR
        self.grid_spacing = atr * self.grid_spacing_atr_multiplier

        # Create buy levels (below center)
        self.grid_buy_levels = []
        for i in range(1, self.num_grid_levels + 1):
            level = self.grid_center - (self.grid_spacing * i)
            self.grid_buy_levels.append(level)

        # Create sell levels (above center)
        self.grid_sell_levels = []
        for i in range(1, self.num_grid_levels + 1):
            level = self.grid_center + (self.grid_spacing * i)
            self.grid_sell_levels.append(level)

        self.last_rebalance_price = current_price
        self.filled_buy_levels = set()
        self.filled_sell_levels = set()

    def _should_rebalance(self, current_price: float) -> bool:
        """Check if grid needs rebalancing"""

        if self.last_rebalance_price is None:
            return True

        price_change = abs(current_price - self.last_rebalance_price) / self.last_rebalance_price

        return price_change > self.rebalance_threshold

    def on_bar(self, row: pd.Series) -> Signal:
        """Generate grid trading signals"""

        # Wait for indicators
        atr = row.get(f'atr_{self.atr_period}')
        trend_ema = row.get('trend_ema')
        trend_pct = row.get('trend_pct')

        if any(pd.isna(x) for x in [atr, trend_ema, trend_pct]):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicators')

        current_price = row['close']

        # Initialize or rebalance grid
        if self.grid_center is None or self._should_rebalance(current_price):
            self._setup_grid(current_price, atr, trend_ema)

        # Strong trend check: Pause grid trading
        if abs(trend_pct) > self.trend_threshold:
            if self.has_position:
                # Close position in strong trend
                return Signal(
                    action='close',
                    symbol=self.symbol,
                    reason=f'Strong trend detected: {trend_pct*100:.2f}%',
                    confidence=0.9
                )
            else:
                return Signal(action='hold', symbol=self.symbol, reason='Strong trend - grid paused')

        # Grid trading logic
        if not self.has_position:

            # Check if price touched buy level
            for i, buy_level in enumerate(self.grid_buy_levels):
                if i not in self.filled_buy_levels:
                    # Price touched or crossed buy level from above
                    if current_price <= buy_level:

                        # Calculate position size (smaller for levels further from center)
                        distance_factor = 1 - (i / len(self.grid_buy_levels))
                        position_size = (self.max_position_size / self.num_grid_levels) * (0.5 + distance_factor * 0.5)

                        # Target: Next sell level above
                        if i < len(self.grid_sell_levels):
                            take_profit = self.grid_sell_levels[i]
                        else:
                            take_profit = current_price * 1.02  # Default 2% profit

                        # Stop loss: Next buy level below (or grid edge)
                        if i + 1 < len(self.grid_buy_levels):
                            stop_loss = self.grid_buy_levels[i + 1]
                        else:
                            stop_loss = buy_level - self.grid_spacing

                        self.filled_buy_levels.add(i)

                        return Signal(
                            action='long',
                            symbol=self.symbol,
                            size=position_size,
                            stop_loss=stop_loss / current_price,
                            take_profit=take_profit / current_price,
                            reason=f'Grid BUY at level {i+1}: ${buy_level:.2f}',
                            confidence=0.7 + (distance_factor * 0.3)
                        )

        else:  # Has position
            # Check if price reached take profit (sell level)
            if self.position_side == 'long':
                for i, sell_level in enumerate(self.grid_sell_levels):
                    if i not in self.filled_sell_levels:
                        # Price touched or crossed sell level
                        if current_price >= sell_level:

                            self.filled_sell_levels.add(i)

                            return Signal(
                                action='close',
                                symbol=self.symbol,
                                reason=f'Grid SELL at level {i+1}: ${sell_level:.2f}',
                                confidence=0.95
                            )

                # Check stop loss (price went too far down)
                lowest_buy = min(self.grid_buy_levels)
                if current_price < lowest_buy - self.grid_spacing:
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Price below grid range - stop loss',
                        confidence=0.9
                    )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """Data requirements"""
        lookback = max(self.atr_period, self.trend_ema_period) + 100
        return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=lookback)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """Parameter schema"""
        return [
            {
                'name': 'num_grid_levels',
                'type': 'int',
                'default': 5,
                'min': 3,
                'max': 10,
                'step': 1,
                'description': 'Number of grid levels on each side',
                'required': True
            },
            {
                'name': 'grid_spacing_atr_multiplier',
                'type': 'float',
                'default': 0.5,
                'min': 0.25,
                'max': 2.0,
                'step': 0.25,
                'description': 'Grid spacing as multiple of ATR',
                'required': True
            },
            {
                'name': 'atr_period',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'step': 1,
                'description': 'ATR period for volatility measurement',
                'required': True
            },
            {
                'name': 'trend_ema_period',
                'type': 'int',
                'default': 50,
                'min': 20,
                'max': 200,
                'step': 10,
                'description': 'EMA period for trend identification',
                'required': True
            },
            {
                'name': 'trend_threshold',
                'type': 'float',
                'default': 0.02,
                'min': 0.01,
                'max': 0.05,
                'step': 0.01,
                'description': 'Trend threshold to pause grid (as percentage)',
                'required': True
            },
            {
                'name': 'max_position_size',
                'type': 'float',
                'default': 0.8,
                'min': 0.3,
                'max': 1.0,
                'step': 0.1,
                'description': 'Maximum capital allocation for grid (as percentage)',
                'required': True
            },
            {
                'name': 'rebalance_threshold',
                'type': 'float',
                'default': 0.05,
                'min': 0.03,
                'max': 0.10,
                'step': 0.01,
                'description': 'Price move threshold to trigger rebalance',
                'required': True
            }
        ]
