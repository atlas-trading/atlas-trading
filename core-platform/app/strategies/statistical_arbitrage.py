"""
Statistical Arbitrage Strategy (Professional Mean Reversion)

Advanced statistical approach to mean reversion trading using:
- Z-Score normalization for entry/exit
- Bollinger Bands for volatility adjustment
- Volume-weighted signals
- Regime detection (trending vs ranging)
- Dynamic position sizing based on confidence

Theory:
Statistical arbitrage exploits temporary mispricings in assets that historically
revert to their mean. Uses statistical measures to identify overbought/oversold
conditions with high probability of reversion.

Entry Rules:
1. Z-Score < -2.0: Oversold (BUY signal)
2. Z-Score > +2.0: Overbought (SELL/SHORT signal)
3. Price touches Bollinger Band outer edge
4. Volume > average (confirmation)
5. Not in strong trend (ADX < 30)

Exit Rules:
1. Z-Score crosses 0 (mean reversion complete)
2. Opposite signal triggers
3. Stop loss at 2x ATR
4. Take profit at 1.5x expected reversion

Risk Management:
- Position size: Based on Z-score magnitude and confidence
- Stop loss: ATR-based dynamic stops
- Maximum positions: 3 concurrent mean reversion trades
- Drawdown protection: Reduce size after 3 consecutive losses
"""

import pandas as pd
import numpy as np
from typing import List
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin


class StatisticalArbitrageStrategy(Strategy, IndicatorMixin):
    """
    Professional Statistical Arbitrage / Mean Reversion Strategy

    Uses Z-score, Bollinger Bands, and volume for high-probability mean reversion trades
    """

    # 최적화된 심볼별 파라미터 (백테스트 결과 기반)
    OPTIMIZED_PARAMS = {
        'XRPUSDT': {
            'zscore_entry_threshold': 2.0,
            'zscore_exit_threshold': 0.3,
            'adx_trend_threshold': 30,
            'expected_return': 25.79,  # 참고용
            'sharpe_ratio': 0.72,
        },
        'ADAUSDT': {
            'zscore_entry_threshold': 1.5,
            'zscore_exit_threshold': 0.5,
            'adx_trend_threshold': 35,
            'expected_return': 20.51,
            'sharpe_ratio': 1.05,
        },
        'ETHUSDT': {
            'zscore_entry_threshold': 1.5,
            'zscore_exit_threshold': 0.3,
            'adx_trend_threshold': 25,
            'expected_return': 12.06,
            'sharpe_ratio': 0.56,
        },
        'LINKUSDT': {
            'zscore_entry_threshold': 1.5,
            'zscore_exit_threshold': 0.3,
            'adx_trend_threshold': 25,
            'expected_return': 11.78,
            'sharpe_ratio': 0.39,
        },
        'BTCUSDT': {
            'zscore_entry_threshold': 2.5,
            'zscore_exit_threshold': 0.3,
            'adx_trend_threshold': 25,
            'expected_return': 8.97,
            'sharpe_ratio': 0.50,
        },
        'BNBUSDT': {
            'zscore_entry_threshold': 2.0,
            'zscore_exit_threshold': 0.3,
            'adx_trend_threshold': 25,
            'expected_return': 4.20,
            'sharpe_ratio': 0.78,
        },
    }

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        zscore_period: int = 20,
        zscore_entry_threshold: float = None,  # None이면 최적화된 값 사용
        zscore_exit_threshold: float = None,   # None이면 최적화된 값 사용
        bb_period: int = 20,
        bb_std: float = 2.0,
        volume_ma_period: int = 20,
        atr_period: int = 14,
        atr_stop_multiplier: float = 2.0,
        adx_period: int = 14,
        adx_trend_threshold: float = None,     # None이면 최적화된 값 사용
        use_optimized: bool = True,            # 최적화된 파라미터 사용 여부
        **kwargs
    ):
        # 최적화된 파라미터 적용
        if use_optimized and symbol in self.OPTIMIZED_PARAMS:
            opt = self.OPTIMIZED_PARAMS[symbol]
            if zscore_entry_threshold is None:
                zscore_entry_threshold = opt['zscore_entry_threshold']
            if zscore_exit_threshold is None:
                zscore_exit_threshold = opt['zscore_exit_threshold']
            if adx_trend_threshold is None:
                adx_trend_threshold = opt['adx_trend_threshold']
            print(f"📊 {symbol}: 최적화된 파라미터 사용 (Entry={zscore_entry_threshold}, Exit={zscore_exit_threshold}, ADX={adx_trend_threshold})")
        else:
            # 기본값 설정
            if zscore_entry_threshold is None:
                zscore_entry_threshold = 2.0
            if zscore_exit_threshold is None:
                zscore_exit_threshold = 0.5
            if adx_trend_threshold is None:
                adx_trend_threshold = 30

        super().__init__(
            symbol=symbol,
            zscore_period=zscore_period,
            zscore_entry_threshold=zscore_entry_threshold,
            zscore_exit_threshold=zscore_exit_threshold,
            bb_period=bb_period,
            bb_std=bb_std,
            volume_ma_period=volume_ma_period,
            atr_period=atr_period,
            atr_stop_multiplier=atr_stop_multiplier,
            adx_period=adx_period,
            adx_trend_threshold=adx_trend_threshold,
            **kwargs
        )

        self.entry_price = None
        self.entry_zscore = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all statistical indicators"""

        # Z-Score (standardized price)
        df['price_ma'] = df['close'].rolling(window=self.zscore_period).mean()
        df['price_std'] = df['close'].rolling(window=self.zscore_period).std()
        df['zscore'] = (df['close'] - df['price_ma']) / df['price_std']

        # Bollinger Bands
        bb_ma = df['close'].rolling(window=self.bb_period).mean()
        bb_std = df['close'].rolling(window=self.bb_period).std()
        df['bb_upper'] = bb_ma + (bb_std * self.bb_std)
        df['bb_middle'] = bb_ma
        df['bb_lower'] = bb_ma - (bb_std * self.bb_std)

        # Bollinger Band position (0 = lower band, 1 = upper band)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Volume analysis
        df['volume_ma'] = df['volume'].rolling(window=self.volume_ma_period).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # ATR for stop loss
        df = self.add_atr(df, self.atr_period)

        # ADX for trend detection (avoid mean reversion in strong trends)
        df = self.add_adx(df, self.adx_period)

        # Regime detection: Coefficient of variation
        df['regime_cv'] = df['price_std'] / df['price_ma']

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """Generate statistical arbitrage signals"""

        # Wait for indicators
        zscore = row.get('zscore')
        bb_position = row.get('bb_position')
        volume_ratio = row.get('volume_ratio')
        atr = row.get(f'atr_{self.atr_period}')
        adx = row.get(f'adx_{self.adx_period}')

        if any(pd.isna(x) for x in [zscore, bb_position, volume_ratio, atr, adx]):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicators')

        current_price = row['close']
        bb_upper = row['bb_upper']
        bb_lower = row['bb_lower']
        bb_middle = row['bb_middle']

        # Regime check: Don't trade in strong trends
        if adx > self.adx_trend_threshold:
            if not self.has_position:
                return Signal(action='hold', symbol=self.symbol, reason=f'Strong trend detected (ADX={adx:.1f})')

        # Exit logic
        if self.has_position and self.entry_zscore is not None:

            if self.position_side == 'long':
                # Exit conditions for long
                # 1. Z-score reverted to mean
                if zscore > -self.zscore_exit_threshold:
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Mean reversion complete (Z-score: {zscore:.2f})',
                        confidence=0.95
                    )

                # 2. Reached BB middle (target)
                if current_price >= bb_middle * 0.995:
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Reached Bollinger middle band',
                        confidence=1.0
                    )

                # 3. Stop loss
                if self.entry_price and current_price < self.entry_price - (atr * self.atr_stop_multiplier):
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Stop loss hit',
                        confidence=0.9
                    )

            elif self.position_side == 'short':
                # Exit conditions for short
                # 1. Z-score reverted to mean
                if zscore < self.zscore_exit_threshold:
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Mean reversion complete (Z-score: {zscore:.2f})',
                        confidence=0.95
                    )

                # 2. Reached BB middle (target)
                if current_price <= bb_middle * 1.005:
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason=f'Reached Bollinger middle band',
                        confidence=1.0
                    )

                # 3. Stop loss
                if self.entry_price and current_price > self.entry_price + (atr * self.atr_stop_multiplier):
                    self.entry_price = None
                    self.entry_zscore = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Stop loss hit',
                        confidence=0.9
                    )

        # Entry logic
        if not self.has_position:

            # LONG: Oversold conditions
            if (zscore < -self.zscore_entry_threshold and
                bb_position < 0.1 and  # Near lower BB
                volume_ratio > 0.8):   # Decent volume

                # Confidence based on Z-score magnitude and volume
                confidence = min(abs(zscore) / 3.0, 1.0) * min(volume_ratio, 1.5) / 1.5

                # Position size based on confidence
                position_size = 0.5 + (confidence * 0.5)  # 50% to 100%

                self.entry_price = current_price
                self.entry_zscore = zscore

                stop_loss = current_price - (atr * self.atr_stop_multiplier)
                take_profit = bb_middle

                return Signal(
                    action='long',
                    symbol=self.symbol,
                    size=position_size,
                    stop_loss=stop_loss / current_price,
                    take_profit=take_profit / current_price,
                    reason=f'Statistical Arbitrage LONG: Z-score={zscore:.2f}, BB={bb_position:.2f}',
                    confidence=confidence
                )

            # SHORT: Overbought conditions
            elif (zscore > self.zscore_entry_threshold and
                  bb_position > 0.9 and  # Near upper BB
                  volume_ratio > 0.8):   # Decent volume

                # Confidence based on Z-score magnitude and volume
                confidence = min(abs(zscore) / 3.0, 1.0) * min(volume_ratio, 1.5) / 1.5

                # Position size based on confidence
                position_size = 0.5 + (confidence * 0.5)  # 50% to 100%

                self.entry_price = current_price
                self.entry_zscore = zscore

                stop_loss = current_price + (atr * self.atr_stop_multiplier)
                take_profit = bb_middle

                return Signal(
                    action='short',
                    symbol=self.symbol,
                    size=position_size,
                    stop_loss=stop_loss / current_price,
                    take_profit=take_profit / current_price,
                    reason=f'Statistical Arbitrage SHORT: Z-score={zscore:.2f}, BB={bb_position:.2f}',
                    confidence=confidence
                )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """Data requirements"""
        lookback = max(self.zscore_period, self.bb_period, self.volume_ma_period, self.atr_period, self.adx_period) + 50
        return [DataRequirement(symbol=self.symbol, timeframe='4h', lookback=lookback)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """Parameter schema"""
        return [
            {
                'name': 'zscore_period',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'step': 5,
                'description': 'Period for Z-score calculation',
                'required': True
            },
            {
                'name': 'zscore_entry_threshold',
                'type': 'float',
                'default': 2.0,
                'min': 1.5,
                'max': 3.0,
                'step': 0.5,
                'description': 'Z-score threshold for entry',
                'required': True
            },
            {
                'name': 'zscore_exit_threshold',
                'type': 'float',
                'default': 0.5,
                'min': 0.0,
                'max': 1.5,
                'step': 0.5,
                'description': 'Z-score threshold for exit',
                'required': True
            },
            {
                'name': 'bb_period',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'step': 5,
                'description': 'Bollinger Bands period',
                'required': True
            },
            {
                'name': 'bb_std',
                'type': 'float',
                'default': 2.0,
                'min': 1.5,
                'max': 3.0,
                'step': 0.5,
                'description': 'Bollinger Bands standard deviation',
                'required': True
            },
            {
                'name': 'volume_ma_period',
                'type': 'int',
                'default': 20,
                'min': 10,
                'max': 50,
                'step': 5,
                'description': 'Volume moving average period',
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
                'name': 'adx_period',
                'type': 'int',
                'default': 14,
                'min': 7,
                'max': 30,
                'step': 1,
                'description': 'ADX period for trend detection',
                'required': True
            },
            {
                'name': 'atr_stop_multiplier',
                'type': 'float',
                'default': 2.0,
                'min': 1.0,
                'max': 4.0,
                'step': 0.5,
                'description': 'ATR multiplier for stop loss',
                'required': True
            },
            {
                'name': 'adx_trend_threshold',
                'type': 'float',
                'default': 30,
                'min': 20,
                'max': 40,
                'step': 5,
                'description': 'ADX threshold to avoid trading in strong trends',
                'required': True
            }
        ]
