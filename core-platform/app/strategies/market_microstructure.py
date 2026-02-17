"""
Market Microstructure Strategy (Order Flow Analysis)

Professional strategy analyzing market microstructure and order flow:
- Volume Profile: Identify high-volume nodes (support/resistance)
- Delta Volume: Buy volume vs Sell volume imbalance
- Large Order Detection: Identify institutional activity
- Bid-Ask Spread Analysis: Market pressure direction
- Absorption: Large orders absorbing market pressure

Theory:
Market microstructure examines how orders are executed and how they impact
price formation. By analyzing volume distribution, delta, and large orders,
we can identify where institutions are active and trade with them.

Entry Rules:
1. Price approaches high-volume node (VPOC - Volume Point of Control)
2. Delta shows strong buying/selling pressure
3. Large order detected at support/resistance
4. Absorption occurs (price holds despite selling pressure)

Exit Rules:
1. Delta reverses (buying pressure turns to selling or vice versa)
2. Price breaks through high-volume node with strong delta
3. Stop loss at recent swing point
4. Take profit at next high-volume node

Risk Management:
- Position size: Based on delta strength
- Stop loss: Just beyond volume node
- Confluence trading: Multiple signals required
"""

import pandas as pd
import numpy as np
from typing import List
from app.strategies.base import Strategy, Signal, DataRequirement, ParameterSchema, IndicatorMixin


class MarketMicrostructureStrategy(Strategy, IndicatorMixin):
    """
    Market Microstructure / Order Flow Strategy

    Analyzes volume distribution and order flow for institutional activity
    """

    def __init__(
        self,
        symbol: str = 'BTCUSDT',
        volume_profile_period: int = 50,
        delta_sensitivity: float = 1.5,  # Threshold for delta signal
        large_order_threshold: float = 2.0,  # Threshold for detecting large orders (x average volume)
        atr_period: int = 14,
        atr_stop_multiplier: float = 1.5,
        **kwargs
    ):
        super().__init__(
            symbol=symbol,
            volume_profile_period=volume_profile_period,
            delta_sensitivity=delta_sensitivity,
            large_order_threshold=large_order_threshold,
            atr_period=atr_period,
            atr_stop_multiplier=atr_stop_multiplier,
            **kwargs
        )

        self.volume_nodes = []
        self.entry_node = None

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate market microstructure indicators"""

        # Estimate buy vs sell volume (simplified delta)
        # Green candle: more buying, Red candle: more selling
        df['price_change'] = df['close'] - df['open']
        df['is_bullish'] = df['price_change'] > 0

        # Delta approximation: Volume weighted by price direction
        df['delta'] = df['volume'] * np.where(df['is_bullish'], 1, -1)

        # Cumulative delta
        df['cumulative_delta'] = df['delta'].cumsum()

        # Delta MA for signal
        df['delta_ma'] = df['delta'].rolling(window=20).mean()

        # Volume MA for large order detection
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']

        # Large order detection
        df['large_order'] = df['volume_ratio'] > self.large_order_threshold

        # Volume-weighted price (approximate VWAP)
        df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).rolling(
            window=self.volume_profile_period
        ).sum() / df['volume'].rolling(window=self.volume_profile_period).sum()

        # ATR for stop loss
        df = self.add_atr(df, self.atr_period)

        # Identify volume clusters (support/resistance from volume)
        df = self._identify_volume_nodes(df)

        return df

    def _identify_volume_nodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Identify high-volume price levels (volume nodes)
        These act as support/resistance
        """

        df['volume_node'] = np.nan
        df['node_strength'] = np.nan

        # Calculate volume at each price level (simplified)
        period = self.volume_profile_period

        for i in range(period, len(df)):
            recent_data = df.iloc[i-period:i]

            # Group by price ranges and sum volume
            price_bins = 10
            price_min = recent_data['low'].min()
            price_max = recent_data['high'].max()

            if price_max > price_min:
                bins = np.linspace(price_min, price_max, price_bins)
                recent_data_copy = recent_data.copy()
                recent_data_copy['price_bin'] = pd.cut(recent_data_copy['close'], bins=bins, labels=False)

                volume_by_bin = recent_data_copy.groupby('price_bin')['volume'].sum()

                # Find highest volume bin (VPOC - Volume Point of Control)
                if len(volume_by_bin) > 0:
                    max_vol_bin = volume_by_bin.idxmax()
                    max_vol = volume_by_bin.max()

                    # Price at highest volume
                    vpoc_price = bins[int(max_vol_bin)] + (bins[1] - bins[0]) / 2

                    df.loc[df.index[i], 'volume_node'] = vpoc_price
                    df.loc[df.index[i], 'node_strength'] = max_vol / volume_by_bin.mean()

        return df

    def on_bar(self, row: pd.Series) -> Signal:
        """Generate order flow based signals"""

        # Wait for indicators
        delta = row.get('delta')
        delta_ma = row.get('delta_ma')
        vwap = row.get('vwap')
        volume_node = row.get('volume_node')
        node_strength = row.get('node_strength')
        large_order = row.get('large_order')
        atr = row.get(f'atr_{self.atr_period}')

        if any(pd.isna(x) for x in [delta, delta_ma, atr]):
            return Signal(action='hold', symbol=self.symbol, reason='Waiting for indicators')

        current_price = row['close']
        current_volume = row['volume']

        # Exit logic
        if self.has_position and self.entry_node is not None:

            if self.position_side == 'long':
                # Exit on delta reversal
                if delta < -delta_ma * self.delta_sensitivity:
                    self.entry_node = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Delta reversed to negative',
                        confidence=0.85
                    )

                # Take profit at next volume node above entry
                if not pd.isna(volume_node) and volume_node > self.entry_node * 1.005:
                    if abs(current_price - volume_node) < atr * 0.5:
                        self.entry_node = None
                        return Signal(
                            action='close',
                            symbol=self.symbol,
                            reason=f'Reached volume node: {volume_node:.2f}',
                            confidence=0.9
                        )

            elif self.position_side == 'short':
                # Exit on delta reversal
                if delta > delta_ma * self.delta_sensitivity:
                    self.entry_node = None
                    return Signal(
                        action='close',
                        symbol=self.symbol,
                        reason='Delta reversed to positive',
                        confidence=0.85
                    )

                # Take profit at next volume node below entry
                if not pd.isna(volume_node) and volume_node < self.entry_node * 0.995:
                    if abs(current_price - volume_node) < atr * 0.5:
                        self.entry_node = None
                        return Signal(
                            action='close',
                            symbol=self.symbol,
                            reason=f'Reached volume node: {volume_node:.2f}',
                            confidence=0.9
                        )

        # Entry logic
        if not self.has_position:

            # LONG: Strong buying delta + price at volume node support
            if (delta > delta_ma * self.delta_sensitivity and
                not pd.isna(volume_node) and
                not pd.isna(node_strength) and
                node_strength > 1.2):

                # Price approaching volume node from above (bouncing off support)
                distance_to_node = abs(current_price - volume_node) / current_price

                if distance_to_node < 0.005:  # Within 0.5% of node

                    # Confidence based on delta strength and node strength
                    delta_conf = min(abs(delta / delta_ma) / 3.0, 1.0)
                    node_conf = min(node_strength / 2.0, 1.0)
                    confidence = (delta_conf + node_conf) / 2

                    # Large order at support increases confidence
                    if large_order:
                        confidence = min(confidence * 1.2, 1.0)

                    self.entry_node = volume_node

                    stop_loss = volume_node - atr * self.atr_stop_multiplier
                    # Take profit at 2x risk
                    take_profit = current_price + (current_price - stop_loss) * 2

                    return Signal(
                        action='long',
                        symbol=self.symbol,
                        size=0.8,
                        stop_loss=stop_loss / current_price,
                        take_profit=take_profit / current_price,
                        reason=f'Order Flow LONG: Strong delta + volume node support',
                        confidence=confidence
                    )

            # SHORT: Strong selling delta + price at volume node resistance
            elif (delta < -delta_ma * self.delta_sensitivity and
                  not pd.isna(volume_node) and
                  not pd.isna(node_strength) and
                  node_strength > 1.2):

                # Price approaching volume node from below (rejecting at resistance)
                distance_to_node = abs(current_price - volume_node) / current_price

                if distance_to_node < 0.005:  # Within 0.5% of node

                    # Confidence based on delta strength and node strength
                    delta_conf = min(abs(delta / delta_ma) / 3.0, 1.0)
                    node_conf = min(node_strength / 2.0, 1.0)
                    confidence = (delta_conf + node_conf) / 2

                    # Large order at resistance increases confidence
                    if large_order:
                        confidence = min(confidence * 1.2, 1.0)

                    self.entry_node = volume_node

                    stop_loss = volume_node + atr * self.atr_stop_multiplier
                    # Take profit at 2x risk
                    take_profit = current_price - (stop_loss - current_price) * 2

                    return Signal(
                        action='short',
                        symbol=self.symbol,
                        size=0.8,
                        stop_loss=stop_loss / current_price,
                        take_profit=take_profit / current_price,
                        reason=f'Order Flow SHORT: Strong delta + volume node resistance',
                        confidence=confidence
                    )

        return Signal(action='hold', symbol=self.symbol)

    def get_required_data(self) -> List[DataRequirement]:
        """Data requirements"""
        lookback = max(self.volume_profile_period, self.atr_period) + 100
        return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=lookback)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """Parameter schema"""
        return [
            {
                'name': 'volume_profile_period',
                'type': 'int',
                'default': 50,
                'min': 20,
                'max': 100,
                'step': 10,
                'description': 'Period for volume profile calculation',
                'required': True
            },
            {
                'name': 'delta_sensitivity',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.5,
                'description': 'Delta threshold multiplier for signals',
                'required': True
            },
            {
                'name': 'large_order_threshold',
                'type': 'float',
                'default': 2.0,
                'min': 1.5,
                'max': 3.0,
                'step': 0.5,
                'description': 'Volume ratio threshold for large order detection',
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
                'name': 'atr_stop_multiplier',
                'type': 'float',
                'default': 1.5,
                'min': 1.0,
                'max': 3.0,
                'step': 0.5,
                'description': 'ATR multiplier for stop loss',
                'required': True
            }
        ]
