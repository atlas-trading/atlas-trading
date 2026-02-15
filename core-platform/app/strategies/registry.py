"""
전략 레지스트리

모든 사용 가능한 전략을 등록하고 관리하는 중앙 저장소
"""

from typing import Dict, Type, List, Any
from app.strategies.base import Strategy

# 전략 레지스트리 (전역 딕셔너리)
_strategy_registry: Dict[str, Type[Strategy]] = {}


def register_strategy(strategy_class: Type[Strategy]) -> None:
    """
    전략을 레지스트리에 등록

    Args:
        strategy_class: Strategy를 상속받은 클래스
    """
    strategy_name = strategy_class.__name__
    _strategy_registry[strategy_name] = strategy_class
    print(f"✓ Registered strategy: {strategy_name}")


def get_strategy_class(strategy_name: str) -> Type[Strategy]:
    """
    전략 클래스 가져오기

    Args:
        strategy_name: 전략 이름

    Returns:
        전략 클래스

    Raises:
        KeyError: 전략이 등록되지 않은 경우
    """
    if strategy_name not in _strategy_registry:
        raise KeyError(f"Strategy '{strategy_name}' not found in registry. "
                      f"Available strategies: {list(_strategy_registry.keys())}")
    return _strategy_registry[strategy_name]


def list_strategies() -> List[str]:
    """
    등록된 모든 전략 이름 반환

    Returns:
        전략 이름 리스트
    """
    return list(_strategy_registry.keys())


def get_strategy_info(strategy_name: str) -> Dict[str, Any]:
    """
    전략 정보 반환 (이름, 설명, 파라미터 스키마)

    Args:
        strategy_name: 전략 이름

    Returns:
        전략 정보 딕셔너리
    """
    strategy_class = get_strategy_class(strategy_name)
    return {
        'name': strategy_name,
        'description': strategy_class.get_description(strategy_class),
        'parameters': strategy_class.get_parameter_schema()
    }


def get_all_strategies_info() -> List[Dict[str, Any]]:
    """
    모든 전략 정보 반환

    Returns:
        전략 정보 리스트
    """
    return [get_strategy_info(name) for name in list_strategies()]


def create_strategy_instance(strategy_name: str, **kwargs) -> Strategy:
    """
    전략 인스턴스 생성

    Args:
        strategy_name: 전략 이름
        **kwargs: 전략 파라미터

    Returns:
        전략 인스턴스
    """
    strategy_class = get_strategy_class(strategy_name)
    return strategy_class(**kwargs)


# 전략 자동 등록
def register_all_strategies():
    """모든 전략을 레지스트리에 등록"""
    from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from app.strategies.funding_rate_arbitrage import FundingRateArbitrageStrategy
    from app.strategies.pairs_trading import PairsTradingStrategy
    from app.strategies.trend_following import TrendFollowingStrategy
    from app.strategies.breakout import BreakoutStrategy

    # 각 전략 등록
    register_strategy(RSIMeanReversionStrategy)
    register_strategy(FundingRateArbitrageStrategy)
    register_strategy(PairsTradingStrategy)
    register_strategy(TrendFollowingStrategy)
    register_strategy(BreakoutStrategy)

    print(f"✓ Total {len(_strategy_registry)} strategies registered")
