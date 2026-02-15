"""
전략 베이스 클래스

모든 트레이딩 전략은 이 클래스를 상속받아 구현합니다.
백테스팅과 실거래 모두에서 동일한 인터페이스로 사용 가능합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, TypedDict
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd


SignalType = Literal["long", "short", "close", "hold", None]


@dataclass
class Signal:
    """
    전략 시그널 데이터 구조

    ARCHITECTURE.md 명세에 따른 표준 시그널 포맷
    """
    action: Literal["long", "short", "close", "hold"]
    symbol: str
    size: float = 1.0  # Kelly fraction (0.0 ~ 1.0)
    stop_loss: Optional[float] = None  # 손절가 비율 (예: 0.98 = 2% 손절)
    take_profit: Optional[float] = None  # 익절가 비율 (예: 1.05 = 5% 익절)
    reason: str = ""  # 진입/청산 이유
    confidence: float = 1.0  # 신뢰도 (0.0 ~ 1.0)
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)


@dataclass
class DataRequirement:
    """
    전략 실행에 필요한 데이터 요구사항
    """
    symbol: str
    timeframe: str  # '1m', '5m', '1h', '1d' etc.
    lookback: int  # 필요한 과거 데이터 개수

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)


class ParameterSchema(TypedDict, total=False):
    """
    전략 파라미터 스키마 정의

    어드민 UI에서 파라미터 편집 폼을 자동 생성하는데 사용
    """
    name: str  # 파라미터 이름
    type: Literal["int", "float", "bool", "string", "select"]  # 데이터 타입
    default: Any  # 기본값
    min: Optional[float]  # 최소값 (숫자형)
    max: Optional[float]  # 최대값 (숫자형)
    step: Optional[float]  # 스텝 (숫자형)
    options: Optional[List[Any]]  # 선택 옵션 (select)
    description: str  # 설명
    required: bool  # 필수 여부


class Strategy(ABC):
    """
    트레이딩 전략 베이스 클래스

    백테스트와 실거래 모두에서 사용 가능한 공통 인터페이스를 제공합니다.

    사용 예시:
        class MyStrategy(Strategy):
            def __init__(self, fast_period=10, slow_period=30):
                super().__init__()
                self.fast_period = fast_period
                self.slow_period = slow_period

            def on_bar(self, row: pd.Series) -> Signal:
                if row['ma_fast'] > row['ma_slow']:
                    return Signal(
                        action='long',
                        symbol=self.symbol,
                        size=0.5,
                        stop_loss=0.98,
                        take_profit=1.05,
                        reason='MA crossover',
                        confidence=0.8
                    )
                elif self.has_position:
                    return Signal(action='close', symbol=self.symbol, reason='Exit signal')
                return Signal(action='hold', symbol=self.symbol)

            def get_required_data(self) -> List[DataRequirement]:
                return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=100)]

            @classmethod
            def get_parameter_schema(cls) -> List[ParameterSchema]:
                return [
                    {'name': 'fast_period', 'type': 'int', 'default': 10, 'min': 5, 'max': 50,
                     'description': 'Fast MA period', 'required': True},
                    {'name': 'slow_period', 'type': 'int', 'default': 30, 'min': 20, 'max': 200,
                     'description': 'Slow MA period', 'required': True}
                ]
    """

    def __init__(self, symbol: str = "BTC/USDT", **params):
        """
        전략 초기화

        Args:
            symbol: 거래 심볼 (기본값: BTC/USDT)
            **params: 전략별 파라미터
        """
        self.symbol = symbol
        self.has_position = False
        self.position_side: Optional[str] = None
        self.last_signal: Optional[Signal] = None
        self.bars_since_entry = 0

        # 파라미터 검증 및 설정
        self._apply_parameters(params)

    def _apply_parameters(self, params: Dict[str, Any]) -> None:
        """파라미터 검증 및 적용"""
        schema = self.get_parameter_schema()
        for param_def in schema:
            param_name = param_def['name']

            # 제공된 값 또는 기본값 사용
            value = params.get(param_name, param_def.get('default'))

            # 필수 파라미터 검증
            if param_def.get('required', False) and value is None:
                raise ValueError(f"Required parameter '{param_name}' is missing")

            # 범위 검증 (숫자형)
            if param_def['type'] in ['int', 'float'] and value is not None:
                if 'min' in param_def and value < param_def['min']:
                    raise ValueError(f"Parameter '{param_name}' must be >= {param_def['min']}")
                if 'max' in param_def and value > param_def['max']:
                    raise ValueError(f"Parameter '{param_name}' must be <= {param_def['max']}")

            # 타입 변환
            if param_def['type'] == 'int':
                value = int(value) if value is not None else None
            elif param_def['type'] == 'float':
                value = float(value) if value is not None else None
            elif param_def['type'] == 'bool':
                value = bool(value) if value is not None else None

            setattr(self, param_name, value)

    @abstractmethod
    def on_bar(self, row: pd.Series) -> Signal:
        """
        각 캔들마다 호출되는 전략 로직

        Args:
            row: 현재 캔들 데이터 (OHLCV + 지표)
                - timestamp: 타임스탬프
                - open, high, low, close: 가격
                - volume: 거래량
                - 기타 추가된 지표들

        Returns:
            Signal 객체:
                - action: 'long', 'short', 'close', 'hold'
                - symbol: 거래 심볼
                - size: 포지션 크기 (Kelly fraction, 0.0~1.0)
                - stop_loss: 손절가 비율 (선택)
                - take_profit: 익절가 비율 (선택)
                - reason: 진입/청산 이유
                - confidence: 신뢰도 (0.0~1.0)
        """
        pass

    @abstractmethod
    def get_required_data(self) -> List[DataRequirement]:
        """
        전략 실행에 필요한 데이터 요구사항 반환

        Returns:
            DataRequirement 리스트
                - symbol: 심볼
                - timeframe: 타임프레임
                - lookback: 필요한 과거 데이터 개수
        """
        pass

    @classmethod
    @abstractmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """
        전략 파라미터 스키마 반환 (어드민 UI용)

        Returns:
            파라미터 스키마 리스트
        """
        pass

    def on_position_opened(self, side: str, price: float, timestamp: Any) -> None:
        """
        포지션 진입 시 호출되는 콜백

        전략 내부 상태를 업데이트하거나 추가 로직을 실행할 수 있습니다.

        Args:
            side: 포지션 방향 ('long' or 'short')
            price: 진입 가격
            timestamp: 진입 시간
        """
        self.has_position = True
        self.position_side = side
        self.bars_since_entry = 0

    def on_position_closed(self, pnl: float, pnl_pct: float, timestamp: Any) -> None:
        """
        포지션 청산 시 호출되는 콜백

        Args:
            pnl: 손익 (절대값)
            pnl_pct: 손익률 (%)
            timestamp: 청산 시간
        """
        self.has_position = False
        self.position_side = None
        self.bars_since_entry = 0

    def on_bar_update(self) -> None:
        """각 캔들 업데이트 시 호출 (포지션 보유 중인 경우 카운터 증가 등)"""
        if self.has_position:
            self.bars_since_entry += 1

    def get_parameters(self) -> Dict[str, Any]:
        """
        전략 파라미터 반환 (저장/로깅용)

        Returns:
            전략 파라미터 딕셔너리
        """
        params = {'symbol': self.symbol}
        schema = self.get_parameter_schema()
        for param_def in schema:
            param_name = param_def['name']
            if hasattr(self, param_name):
                params[param_name] = getattr(self, param_name)
        return params

    def get_name(self) -> str:
        """
        전략 이름 반환

        Returns:
            전략 이름 (클래스명)
        """
        return self.__class__.__name__

    def get_description(self) -> str:
        """
        전략 설명 반환

        Returns:
            전략 설명 (클래스 docstring 첫 줄)
        """
        doc = self.__class__.__doc__
        if doc:
            return doc.strip().split('\n')[0]
        return ""

    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, str]:
        """
        파라미터 검증

        Args:
            params: 검증할 파라미터

        Returns:
            에러 메시지 딕셔너리 (키: 파라미터명, 값: 에러 메시지)
            빈 딕셔너리면 모두 유효
        """
        errors = {}
        schema = self.get_parameter_schema()

        for param_def in schema:
            param_name = param_def['name']
            value = params.get(param_name)

            # 필수 파라미터 체크
            if param_def.get('required', False) and value is None:
                errors[param_name] = "Required parameter"
                continue

            if value is None:
                continue

            # 타입 체크
            param_type = param_def['type']
            if param_type == 'int' and not isinstance(value, int):
                errors[param_name] = f"Must be integer"
            elif param_type == 'float' and not isinstance(value, (int, float)):
                errors[param_name] = f"Must be number"
            elif param_type == 'bool' and not isinstance(value, bool):
                errors[param_name] = f"Must be boolean"
            elif param_type == 'string' and not isinstance(value, str):
                errors[param_name] = f"Must be string"

            # 범위 체크
            if param_type in ['int', 'float'] and isinstance(value, (int, float)):
                if 'min' in param_def and value < param_def['min']:
                    errors[param_name] = f"Must be >= {param_def['min']}"
                if 'max' in param_def and value > param_def['max']:
                    errors[param_name] = f"Must be <= {param_def['max']}"

            # 선택 옵션 체크
            if param_type == 'select' and 'options' in param_def:
                if value not in param_def['options']:
                    errors[param_name] = f"Must be one of {param_def['options']}"

        return errors

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 전처리 및 지표 계산

        백테스트 시작 전에 한 번 호출됩니다.
        여기서 필요한 모든 지표를 계산할 수 있습니다.

        Args:
            df: 원본 OHLCV 데이터

        Returns:
            지표가 추가된 데이터프레임
        """
        # 기본 구현: 원본 그대로 반환
        # 서브클래스에서 오버라이드하여 지표 추가 가능
        return df

    def reset(self) -> None:
        """전략 상태 초기화 (새 백테스트 시작 시 호출)"""
        self.has_position = False
        self.position_side = None
        self.last_signal = None
        self.bars_since_entry = 0

    def update_parameters(self, params: Dict[str, Any]) -> None:
        """
        런타임에 파라미터 업데이트

        Args:
            params: 업데이트할 파라미터 딕셔너리

        Raises:
            ValueError: 파라미터 검증 실패 시
        """
        errors = self.validate_parameters(params)
        if errors:
            error_msg = ", ".join([f"{k}: {v}" for k, v in errors.items()])
            raise ValueError(f"Parameter validation failed: {error_msg}")

        self._apply_parameters(params)
        self.reset()  # 파라미터 변경 시 상태 초기화


class LegacyStrategyAdapter(Strategy):
    """
    기존 전략 코드를 새 인터페이스로 어댑트하는 클래스

    기존 전략들이 SignalType (str)을 반환하는 경우 Signal 객체로 변환
    """

    def __init__(self, symbol: str = "BTC/USDT", **params):
        super().__init__(symbol=symbol, **params)

    @abstractmethod
    def on_bar_legacy(self, row: pd.Series) -> SignalType:
        """
        기존 on_bar 메서드 (하위 호환성)

        Returns:
            'long', 'short', 'close', None
        """
        pass

    def on_bar(self, row: pd.Series) -> Signal:
        """SignalType을 Signal 객체로 변환"""
        signal_type = self.on_bar_legacy(row)

        if signal_type is None or signal_type == 'hold':
            return Signal(action='hold', symbol=self.symbol)

        return Signal(
            action=signal_type,
            symbol=self.symbol,
            size=1.0,  # 기본값
            reason=f"{signal_type.capitalize()} signal from legacy strategy",
            confidence=1.0
        )

    def get_required_data(self) -> List[DataRequirement]:
        """기본 데이터 요구사항"""
        return [DataRequirement(symbol=self.symbol, timeframe='1h', lookback=100)]

    @classmethod
    def get_parameter_schema(cls) -> List[ParameterSchema]:
        """기본 파라미터 스키마 (서브클래스에서 오버라이드)"""
        return []


class IndicatorMixin:
    """
    공통 지표 계산 메서드를 제공하는 Mixin 클래스

    Strategy 클래스와 함께 사용:
        class MyStrategy(Strategy, IndicatorMixin):
            ...
    """

    @staticmethod
    def add_sma(df: pd.DataFrame, period: int, column: str = 'close') -> pd.DataFrame:
        """단순 이동평균 추가"""
        df[f'sma_{period}'] = df[column].rolling(window=period).mean()
        return df

    @staticmethod
    def add_ema(df: pd.DataFrame, period: int, column: str = 'close') -> pd.DataFrame:
        """지수 이동평균 추가"""
        df[f'ema_{period}'] = df[column].ewm(span=period, adjust=False).mean()
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14, column: str = 'close') -> pd.DataFrame:
        """RSI 지표 추가"""
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def add_bollinger_bands(
        df: pd.DataFrame, period: int = 20, std_dev: float = 2.0, column: str = 'close'
    ) -> pd.DataFrame:
        """볼린저 밴드 추가"""
        df['bb_middle'] = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        df['bb_upper'] = df['bb_middle'] + (std * std_dev)
        df['bb_lower'] = df['bb_middle'] - (std * std_dev)
        return df

    @staticmethod
    def add_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        column: str = 'close'
    ) -> pd.DataFrame:
        """MACD 지표 추가"""
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ATR (Average True Range) 지표 추가"""
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df[f'atr_{period}'] = true_range.rolling(window=period).mean()
        return df

    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """ADX (Average Directional Index) 지표 추가"""
        # +DM, -DM 계산
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # ATR 계산 (이미 있으면 재사용)
        if f'atr_{period}' not in df.columns:
            df = IndicatorMixin.add_atr(df, period)

        atr = df[f'atr_{period}']

        # +DI, -DI 계산
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # DX, ADX 계산
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
        df[f'adx_{period}'] = dx.rolling(window=period).mean()
        df[f'plus_di_{period}'] = plus_di
        df[f'minus_di_{period}'] = minus_di

        return df

    @staticmethod
    def add_donchian_channel(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """Donchian Channel 지표 추가"""
        df[f'donchian_high_{period}'] = df['high'].rolling(window=period).max()
        df[f'donchian_low_{period}'] = df['low'].rolling(window=period).min()
        df[f'donchian_mid_{period}'] = (df[f'donchian_high_{period}'] + df[f'donchian_low_{period}']) / 2
        return df
