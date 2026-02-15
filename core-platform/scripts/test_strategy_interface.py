"""
Strategy 인터페이스 테스트

새로운 Strategy 인터페이스와 Signal 시스템이 제대로 작동하는지 확인
"""
import sys
from pathlib import Path

# core-platform 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
from app.strategies.base import Signal, DataRequirement


def test_rsi_strategy():
    """RSI 전략 테스트"""
    print("=" * 60)
    print("RSI Mean Reversion Strategy 테스트")
    print("=" * 60)

    # 전략 인스턴스 생성
    strategy = RSIMeanReversionStrategy(
        symbol="BTC/USDT",
        rsi_period=14,
        oversold_threshold=30,
        overbought_threshold=70
    )

    print(f"\n1. 전략 정보:")
    print(f"   - 이름: {strategy.get_name()}")
    print(f"   - 설명: {strategy.get_description()}")
    print(f"   - 파라미터: {strategy.get_parameters()}")

    # 파라미터 스키마 확인
    print(f"\n2. 파라미터 스키마:")
    schema = strategy.get_parameter_schema()
    for param in schema:
        print(f"   - {param['name']}: {param['type']} "
              f"(default={param['default']}, min={param.get('min')}, max={param.get('max')})")
        print(f"     {param['description']}")

    # 데이터 요구사항 확인
    print(f"\n3. 데이터 요구사항:")
    requirements = strategy.get_required_data()
    for req in requirements:
        print(f"   - Symbol: {req.symbol}, Timeframe: {req.timeframe}, Lookback: {req.lookback}")

    # 테스트 데이터 생성 (100일치)
    print(f"\n4. 테스트 데이터 생성 (100 bars)...")
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)  # Random walk
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.rand(100) * 1000
    })

    # 지표 추가
    df = strategy.prepare_data(df)
    print(f"   - RSI 컬럼 추가 완료: 'rsi_14' in columns = {'rsi_14' in df.columns}")

    # 시그널 생성 테스트
    print(f"\n5. 시그널 생성 테스트:")
    strategy.reset()

    signals = []
    for idx, row in df.iterrows():
        signal = strategy.on_bar(row)
        if signal.action != 'hold':
            signals.append({
                'timestamp': row['timestamp'],
                'price': row['close'],
                'rsi': row.get('rsi_14', None),
                'action': signal.action,
                'size': signal.size,
                'reason': signal.reason,
                'confidence': signal.confidence
            })

            # 포지션 상태 업데이트 (시뮬레이션)
            if signal.action == 'long':
                strategy.on_position_opened('long', row['close'], row['timestamp'])
            elif signal.action == 'close':
                strategy.on_position_closed(0, 0, row['timestamp'])

        strategy.on_bar_update()

    print(f"   - 총 {len(signals)}개 시그널 생성")
    for i, sig in enumerate(signals[:5], 1):  # 처음 5개만 출력
        print(f"   [{i}] {sig['timestamp']}: {sig['action'].upper()} @ ${sig['price']:.2f}")
        print(f"       RSI={sig['rsi']:.2f}, Size={sig['size']:.2f}, Confidence={sig['confidence']:.2f}")
        print(f"       Reason: {sig['reason']}")

    # 파라미터 검증 테스트
    print(f"\n6. 파라미터 검증 테스트:")

    # 유효한 파라미터
    valid_params = {'rsi_period': 20, 'oversold_threshold': 25, 'overbought_threshold': 75}
    errors = strategy.validate_parameters(valid_params)
    print(f"   - 유효한 파라미터: {valid_params}")
    print(f"     검증 결과: {'✓ 통과' if not errors else f'✗ 실패 - {errors}'}")

    # 무효한 파라미터 (범위 초과)
    invalid_params = {'rsi_period': 100, 'oversold_threshold': 50, 'overbought_threshold': 60}
    errors = strategy.validate_parameters(invalid_params)
    print(f"   - 무효한 파라미터: {invalid_params}")
    print(f"     검증 결과: {'✓ 통과' if not errors else f'✗ 실패 - {errors}'}")

    # 파라미터 업데이트 테스트
    print(f"\n7. 파라미터 업데이트 테스트:")
    new_params = {'rsi_period': 21, 'oversold_threshold': 35, 'overbought_threshold': 65}
    try:
        strategy.update_parameters(new_params)
        print(f"   - 새 파라미터: {strategy.get_parameters()}")
        print(f"     업데이트 성공 ✓")
    except Exception as e:
        print(f"     업데이트 실패 ✗: {e}")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


def test_signal_object():
    """Signal 객체 테스트"""
    print("\n" + "=" * 60)
    print("Signal 객체 테스트")
    print("=" * 60)

    # Signal 생성
    signal = Signal(
        action='long',
        symbol='BTC/USDT',
        size=0.5,
        stop_loss=0.95,
        take_profit=1.10,
        reason='RSI oversold',
        confidence=0.85,
        timestamp=datetime.now()
    )

    print(f"\n1. Signal 객체:")
    print(f"   - Action: {signal.action}")
    print(f"   - Symbol: {signal.symbol}")
    print(f"   - Size: {signal.size}")
    print(f"   - Stop Loss: {signal.stop_loss}")
    print(f"   - Take Profit: {signal.take_profit}")
    print(f"   - Reason: {signal.reason}")
    print(f"   - Confidence: {signal.confidence}")

    print(f"\n2. Signal to dict:")
    print(f"   {signal.to_dict()}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_rsi_strategy()
    test_signal_object()
