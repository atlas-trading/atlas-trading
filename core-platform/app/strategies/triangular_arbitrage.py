"""
Triangular Arbitrage Strategy (Simplified for Single Symbol)

Triangular arbitrage exploits price discrepancies between three currency pairs.
Since we're limited to single-symbol backtesting, this implementation uses
a simplified approach that detects mean reversion opportunities similar to
how triangular arbitrage would work.

True Triangular Arbitrage Example:
- BTC/USDT = 50,000
- ETH/USDT = 3,000
- BTC/ETH = 16.5
- Expected BTC/ETH = 50,000 / 3,000 = 16.67
- Discrepancy: 16.67 - 16.5 = 0.17 (1% profit opportunity)

Simplified Single-Symbol Approach:
We simulate arbitrage-like behavior by:
1. Tracking price efficiency (how far price is from theoretical value)
2. Detecting quick reversion opportunities
3. Ultra-short holding periods (minutes to hours)
4. High win rate, small profits

Entry Rules:
1. Price deviation from theoretical value > threshold
2. High volume (liquidity required for arbitrage)
3. Spread is tight (simulates arbitrage conditions)
4. Quick mean reversion expected

Exit Rules:
1. Price reverts to theoretical value
2. Time limit (arbitrage opportunities are brief)
3. Small stop loss (arbitrage shouldn't have large drawdowns)

Risk Management:
- Very tight stop loss (0.1-0.3%)
- High win rate target (70%+)
- Multiple small trades
- Quick exits
"""

import pandas as pd
import numpy as np
from typing import List
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin


class TriangularArbitrageStrategy(Strategy, IndicatorMixin):
    """
    Simplified Triangular Arbitrage Strategy

    Detects rapid mean reversion opportunities similar to arbitrage
    """

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        efficiency_period: int = 10,  # Short period for efficiency calculation
        efficiency_threshold: float = 0.003,  # 0.3% deviation threshold
        volume_threshold: float = 1.5,  # Require 1.5x average volume
        max_holding_bars: int = 5,  # Maximum holding period
        stop_loss_pct: float = 0.002,  # Tight 0.2% stop loss
        take_profit_pct: float = 0.004,  # Quick 0.4% take profit (2:1 RR)
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            efficiency_period=efficiency_period,
            efficiency_threshold=efficiency_threshold,
            volume_threshold=volume_threshold,
            max_holding_bars=max_holding_bars,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            **kwargs
        )

        self.entry_bar = None
        self.entry_price = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate efficiency and arbitrage-like indicators"""

        # Theoretical price (moving average as proxy)
        df['theoretical_price'] = df['close'].rolling(window=self.efficiency_period).mean()

        # Price efficiency (deviation from theoretical)
        df['efficiency'] = (df['close'] - df['theoretical_price']) / df['theoretical_price']

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Spread proxy (high-low range as percentage)
        df['spread_pct'] = (df['high'] - df['low']) / df['close']

        # Spread MA
        df['spread_ma'] = df['spread_pct'].rolling(window=20).mean()

        # Momentum (for quick reversions)
        df['momentum'] = df['close'].pct_change(3)

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """Generate arbitrage-like signals"""

        # Wait for indicators
        efficiency = row.get('efficiency')
        theoretical_price = row.get('theoretical_price')
        volume_ratio = row.get('volume_ratio')
        spread_pct = row.get('spread_pct')
        spread_ma = row.get('spread_ma')
        momentum = row.get('momentum')

        if any(pd.isna(x) for x in [efficiency, theoretical_price, volume_ratio, spread_ma]):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicators')

        current_price = row['close']
        current_bar_index = len(row) if hasattr(row, '__len__') else 0

        # Exit logic
        if self.has_position and self.entry_price is not None:

            # Time-based exit (arbitrage opportunities are brief)
            if self.entry_bar is not None:
                bars_held = current_bar_index - self.entry_bar
                if bars_held >= self.max_holding_bars:
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Time limit reached ({bars_held} bars)',
                        confidence=0.8
                    )

            if self.position_side == 'long':
                # Take profit
                if current_price >= self.entry_price * (1 + self.take_profit_pct):
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Take profit hit',
                        confidence=1.0
                    )

                # Stop loss
                if current_price <= self.entry_price * (1 - self.stop_loss_pct):
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Stop loss hit',
                        confidence=0.9
                    )

                # Price reverted to theoretical value
                if current_price >= theoretical_price * 0.999:
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Reverted to theoretical price',
                        confidence=0.95
                    )

            elif self.position_side == 'short':
                # Take profit
                if current_price <= self.entry_price * (1 - self.take_profit_pct):
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Take profit hit',
                        confidence=1.0
                    )

                # Stop loss
                if current_price >= self.entry_price * (1 + self.stop_loss_pct):
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Stop loss hit',
                        confidence=0.9
                    )

                # Price reverted to theoretical value
                if current_price <= theoretical_price * 1.001:
                    self.entry_price = None
                    self.entry_bar = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Reverted to theoretical price',
                        confidence=0.95
                    )

        # Entry logic
        if not self.has_position:

            # Tight spread required (simulates good arbitrage conditions)
            if not pd.isna(spread_pct) and spread_pct > spread_ma * 1.5:
                # Spread too wide, not favorable for arbitrage
                return Signal(action='hold', symbol=self.symbol, reason='Spread too wide')

            # LONG: Price below theoretical value (undervalued)
            if (efficiency < -self.efficiency_threshold and
                volume_ratio > self.volume_threshold and  # High volume (liquidity)
                not pd.isna(momentum) and momentum < -0.005):  # Recent downward momentum

                # Confidence based on deviation magnitude
                confidence = min(abs(efficiency) / (self.efficiency_threshold * 2), 1.0)

                self.entry_price = current_price
                self.entry_bar = current_bar_index

                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)

                return Signal(
                    action='long',
                    symbol=self.symbol,
                    size=1.0,  # Full size for arbitrage
                    stop_loss=stop_loss / current_price,
                    take_profit=take_profit / current_price,
                    reason=f'Arbitrage LONG: Price {efficiency*100:.2f}% below theoretical',
                    confidence=confidence
                )

            # SHORT: Price above theoretical value (overvalued)
            elif (efficiency > self.efficiency_threshold and
                  volume_ratio > self.volume_threshold and  # High volume (liquidity)
                  not pd.isna(momentum) and momentum > 0.005):  # Recent upward momentum

                # Confidence based on deviation magnitude
                confidence = min(abs(efficiency) / (self.efficiency_threshold * 2), 1.0)

                self.entry_price = current_price
                self.entry_bar = current_bar_index

                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)

                return Signal(
                    action='short',
                    symbol=self.symbol,
                    size=1.0,  # Full size for arbitrage
                    stop_loss=stop_loss / current_price,
                    take_profit=take_profit / current_price,
                    reason=f'Arbitrage SHORT: Price {efficiency*100:.2f}% above theoretical',
                    confidence=confidence
                )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """Data requirements"""
        lookback = max(self.efficiency_period, 50) + 50
        return [DataRequirement(symbol=self.symbol, timeframe='15m', lookback=lookback)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """Parameter schema"""
        return [
            {
                'name': 'efficiency_period',
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 20,
                'step': 5,
                'description': 'Period for efficiency calculation',
                'required': True
            },
            {
                'name': 'efficiency_threshold',
                'type': 'float',
                'default': 0.003,
                'min': 0.001,
                'max': 0.01,
                'step': 0.001,
                'description': 'Minimum efficiency deviation to trigger trade',
                'required': True
            },
            {
                'name': 'volume_threshold',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.5,
                'description': 'Minimum volume ratio (liquidity requirement)',
                'required': True
            },
            {
                'name': 'max_holding_bars',
                'type': 'int',
                'default': 5,
                'min': 2,
                'max': 10,
                'step': 1,
                'description': 'Maximum holding period in bars',
                'required': True
            },
            {
                'name': 'stop_loss_pct',
                'type': 'float',
                'default': 0.002,
                'min': 0.001,
                'max': 0.005,
                'step': 0.001,
                'description': 'Stop loss percentage',
                'required': True
            },
            {
                'name': 'take_profit_pct',
                'type': 'float',
                'default': 0.004,
                'min': 0.002,
                'max': 0.01,
                'step': 0.001,
                'description': 'Take profit percentage',
                'required': True
            }
        ]
