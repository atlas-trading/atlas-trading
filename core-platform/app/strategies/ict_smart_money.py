"""
ICT (Inner Circle Trader) Smart Money Concepts Strategy

Professional institutional trading strategy based on:
- Order Blocks (OB): Areas where smart money placed large orders
- Fair Value Gaps (FVG): Imbalances in price action
- Liquidity Raids: Stop hunts before reversals
- Break of Structure (BOS): Trend continuation signals
- Change of Character (ChoCh): Trend reversal signals

This strategy identifies where institutional traders (smart money) are active
and trades in alignment with their positions.

Entry Rules:
1. Identify market structure (bullish/bearish)
2. Wait for liquidity raid (sweep of highs/lows)
3. Confirm with order block formation
4. Enter on FVG retest in the direction of market structure

Exit Rules:
1. Take profit at opposite liquidity pool
2. Trail stop using swing points
3. Exit on structure break against position

Risk Management:
- Position size: 1-2% risk per trade
- Stop loss: Below/above order block
- Risk-reward ratio: Minimum 1:2
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Tuple
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin


class ICTSmartMoneyStrategy(Strategy, IndicatorMixin):
    """
    ICT Smart Money Concepts Strategy

    Identifies institutional order flow and trades with smart money
    """

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        swing_lookback: int = 10,  # Bars to identify swing highs/lows
        fvg_min_size: float = 0.002,  # Minimum FVG size (0.2%)
        liquidity_raid_tolerance: float = 0.001,  # Tolerance for liquidity sweep (0.1%)
        atr_period: int = 14,
        risk_reward_ratio: float = 2.0,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            swing_lookback=swing_lookback,
            fvg_min_size=fvg_min_size,
            liquidity_raid_tolerance=liquidity_raid_tolerance,
            atr_period=atr_period,
            risk_reward_ratio=risk_reward_ratio,
            **kwargs
        )

        # Strategy state
        self.market_structure = None  # 'bullish' or 'bearish'
        self.last_swing_high = None
        self.last_swing_low = None
        self.active_order_block = None
        self.active_fvg = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators"""

        # ATR for stop loss
        df = self.add_atr(df, self.atr_period)

        # Identify swing highs and lows
        df = self._identify_swing_points(df)

        # Detect Fair Value Gaps (FVG)
        df = self._detect_fvg(df)

        # Detect Order Blocks
        df = self._detect_order_blocks(df)

        # Identify market structure
        df = self._identify_market_structure(df)

        return df

    def _identify_swing_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify swing highs and swing lows"""

        lookback = self.swing_lookback

        # Swing High: High that is higher than N bars before and after
        df['swing_high'] = df['high'].rolling(window=lookback*2+1, center=True).apply(
            lambda x: x[lookback] if len(x) == lookback*2+1 and x[lookback] == max(x) else np.nan,
            raw=True
        )

        # Swing Low: Low that is lower than N bars before and after
        df['swing_low'] = df['low'].rolling(window=lookback*2+1, center=True).apply(
            lambda x: x[lookback] if len(x) == lookback*2+1 and x[lookback] == min(x) else np.nan,
            raw=True
        )

        return df

    def _detect_fvg(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Fair Value Gaps (FVG)

        Bullish FVG: Gap between bar[0] high and bar[2] low (bar[1] is the impulse)
        Bearish FVG: Gap between bar[0] low and bar[2] high
        """

        df['fvg_bullish_top'] = np.nan
        df['fvg_bullish_bottom'] = np.nan
        df['fvg_bearish_top'] = np.nan
        df['fvg_bearish_bottom'] = np.nan

        for i in range(2, len(df)):
            # Bullish FVG: bar[i-2] high < bar[i] low
            if df['high'].iloc[i-2] < df['low'].iloc[i]:
                gap_size = (df['low'].iloc[i] - df['high'].iloc[i-2]) / df['close'].iloc[i]
                if gap_size >= self.fvg_min_size:
                    df.loc[df.index[i], 'fvg_bullish_top'] = df['low'].iloc[i]
                    df.loc[df.index[i], 'fvg_bullish_bottom'] = df['high'].iloc[i-2]

            # Bearish FVG: bar[i-2] low > bar[i] high
            if df['low'].iloc[i-2] > df['high'].iloc[i]:
                gap_size = (df['low'].iloc[i-2] - df['high'].iloc[i]) / df['close'].iloc[i]
                if gap_size >= self.fvg_min_size:
                    df.loc[df.index[i], 'fvg_bearish_top'] = df['low'].iloc[i-2]
                    df.loc[df.index[i], 'fvg_bearish_bottom'] = df['high'].iloc[i]

        return df

    def _detect_order_blocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect Order Blocks

        Bullish OB: Last down candle before strong up move
        Bearish OB: Last up candle before strong down move
        """

        df['bullish_ob_top'] = np.nan
        df['bullish_ob_bottom'] = np.nan
        df['bearish_ob_top'] = np.nan
        df['bearish_ob_bottom'] = np.nan

        for i in range(3, len(df)):
            # Bullish Order Block: Last red candle before 2+ green candles
            if (df['close'].iloc[i-2] < df['open'].iloc[i-2] and  # Red candle
                df['close'].iloc[i-1] > df['open'].iloc[i-1] and  # Green candle
                df['close'].iloc[i] > df['open'].iloc[i] and      # Green candle
                df['close'].iloc[i] > df['high'].iloc[i-2]):       # Strong move up

                df.loc[df.index[i], 'bullish_ob_top'] = df['high'].iloc[i-2]
                df.loc[df.index[i], 'bullish_ob_bottom'] = df['low'].iloc[i-2]

            # Bearish Order Block: Last green candle before 2+ red candles
            if (df['close'].iloc[i-2] > df['open'].iloc[i-2] and  # Green candle
                df['close'].iloc[i-1] < df['open'].iloc[i-1] and  # Red candle
                df['close'].iloc[i] < df['open'].iloc[i] and      # Red candle
                df['close'].iloc[i] < df['low'].iloc[i-2]):        # Strong move down

                df.loc[df.index[i], 'bearish_ob_top'] = df['high'].iloc[i-2]
                df.loc[df.index[i], 'bearish_ob_bottom'] = df['low'].iloc[i-2]

        return df

    def _identify_market_structure(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify market structure (Higher Highs/Higher Lows or Lower Highs/Lower Lows)
        """

        df['market_structure'] = None

        swing_highs = df['swing_high'].dropna()
        swing_lows = df['swing_low'].dropna()

        if len(swing_highs) >= 2 and len(swing_lows) >= 2:
            # Check if making higher highs and higher lows (bullish structure)
            recent_highs = swing_highs.tail(2).values
            recent_lows = swing_lows.tail(2).values

            if recent_highs[1] > recent_highs[0] and recent_lows[1] > recent_lows[0]:
                df['market_structure'] = 'bullish'
            elif recent_highs[1] < recent_highs[0] and recent_lows[1] < recent_lows[0]:
                df['market_structure'] = 'bearish'

        # Forward fill market structure
        df['market_structure'] = df['market_structure'].ffill()

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """Generate trading signals based on ICT concepts"""

        # Wait for indicators
        atr = row.get(f'atr_{self.atr_period}')
        if pd.isna(atr):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicators')

        current_price = row['close']
        current_high = row['high']
        current_low = row['low']

        # Get market structure
        market_structure = row.get('market_structure')

        # Update swing points
        if not pd.isna(row.get('swing_high')):
            self.last_swing_high = row['swing_high']
        if not pd.isna(row.get('swing_low')):
            self.last_swing_low = row['swing_low']

        # Exit logic
        if self.has_position:
            if self.position_side == 'long':
                # Exit on bearish structure break
                if market_structure == 'bearish':
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Market structure changed to bearish',
                        confidence=0.9
                    )

                # Take profit at swing high
                if self.last_swing_high and current_price >= self.last_swing_high * 0.99:
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Take profit near swing high: {self.last_swing_high:.2f}',
                        confidence=1.0
                    )

            elif self.position_side == 'short':
                # Exit on bullish structure break
                if market_structure == 'bullish':
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Market structure changed to bullish',
                        confidence=0.9
                    )

                # Take profit at swing low
                if self.last_swing_low and current_price <= self.last_swing_low * 1.01:
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Take profit near swing low: {self.last_swing_low:.2f}',
                        confidence=1.0
                    )

        # Entry logic
        if not self.has_position and market_structure:

            # Bullish setup
            if market_structure == 'bullish':
                # Check for liquidity raid (sweep of recent low)
                if self.last_swing_low and current_low < self.last_swing_low * (1 - self.liquidity_raid_tolerance):

                    # Check for bullish order block
                    if not pd.isna(row.get('bullish_ob_bottom')):
                        ob_bottom = row['bullish_ob_bottom']
                        ob_top = row['bullish_ob_top']

                        # Price retesting order block
                        if ob_bottom <= current_low <= ob_top:

                            stop_loss = ob_bottom - atr
                            take_profit = current_price + (current_price - stop_loss) * self.risk_reward_ratio

                            return Signal(
                                action='long',
                                symbol=self.symbol,
                                size=1.0,
                                stop_loss=stop_loss / current_price,
                                take_profit=take_profit / current_price,
                                reason=f'ICT Bullish: Liquidity raid + OB retest in bullish structure',
                                confidence=0.85
                            )

                    # Check for bullish FVG
                    if not pd.isna(row.get('fvg_bullish_bottom')):
                        fvg_bottom = row['fvg_bullish_bottom']
                        fvg_top = row['fvg_bullish_top']

                        # Price filling FVG
                        if fvg_bottom <= current_low <= fvg_top:

                            stop_loss = fvg_bottom - atr
                            take_profit = current_price + (current_price - stop_loss) * self.risk_reward_ratio

                            return Signal(
                                action='long',
                                symbol=self.symbol,
                                size=1.0,
                                stop_loss=stop_loss / current_price,
                                take_profit=take_profit / current_price,
                                reason=f'ICT Bullish: Liquidity raid + FVG fill in bullish structure',
                                confidence=0.8
                            )

            # Bearish setup
            elif market_structure == 'bearish':
                # Check for liquidity raid (sweep of recent high)
                if self.last_swing_high and current_high > self.last_swing_high * (1 + self.liquidity_raid_tolerance):

                    # Check for bearish order block
                    if not pd.isna(row.get('bearish_ob_top')):
                        ob_top = row['bearish_ob_top']
                        ob_bottom = row['bearish_ob_bottom']

                        # Price retesting order block
                        if ob_bottom <= current_high <= ob_top:

                            stop_loss = ob_top + atr
                            take_profit = current_price - (stop_loss - current_price) * self.risk_reward_ratio

                            return Signal(
                                action='short',
                                symbol=self.symbol,
                                size=1.0,
                                stop_loss=stop_loss / current_price,
                                take_profit=take_profit / current_price,
                                reason=f'ICT Bearish: Liquidity raid + OB retest in bearish structure',
                                confidence=0.85
                            )

                    # Check for bearish FVG
                    if not pd.isna(row.get('fvg_bearish_top')):
                        fvg_top = row['fvg_bearish_top']
                        fvg_bottom = row['fvg_bearish_bottom']

                        # Price filling FVG
                        if fvg_bottom <= current_high <= fvg_top:

                            stop_loss = fvg_top + atr
                            take_profit = current_price - (stop_loss - current_price) * self.risk_reward_ratio

                            return Signal(
                                action='short',
                                symbol=self.symbol,
                                size=1.0,
                                stop_loss=stop_loss / current_price,
                                take_profit=take_profit / current_price,
                                reason=f'ICT Bearish: Liquidity raid + FVG fill in bearish structure',
                                confidence=0.8
                            )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """Data requirements"""
        lookback = max(self.swing_lookback * 3, self.atr_period) + 100
        return [DataRequirement(symbol=self.symbol, timeframe='4h', lookback=lookback)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """Parameter schema"""
        return [
            {
                'name': 'swing_lookback',
                'type': 'int',
                'default': 10,
                'min': 5,
                'max': 20,
                'step': 5,
                'description': 'Bars to identify swing highs/lows',
                'required': True
            },
            {
                'name': 'fvg_min_size',
                'type': 'float',
                'default': 0.002,
                'min': 0.001,
                'max': 0.01,
                'step': 0.001,
                'description': 'Minimum Fair Value Gap size (as percentage)',
                'required': True
            },
            {
                'name': 'liquidity_raid_tolerance',
                'type': 'float',
                'default': 0.001,
                'min': 0.0005,
                'max': 0.005,
                'step': 0.0005,
                'description': 'Tolerance for liquidity sweep detection',
                'required': True
            },
            {
                'name': 'atr_period',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'step': 1,
                'description': 'ATR period for stop loss',
                'required': True
            },
            {
                'name': 'risk_reward_ratio',
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 5.0,
                'step': 0.5,
                'description': 'Minimum risk-reward ratio',
                'required': True
            }
        ]
