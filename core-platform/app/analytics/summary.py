"""
고급 성과 지표 계산

Sortino Ratio, Calmar Ratio, Profit Factor, Expectancy 등
프로 수준의 성과 평가 지표를 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


def calculate_sortino_ratio(
    equity_curve: List[Dict[str, Any]],
    risk_free_rate: float = 0.02
) -> float:
    """
    Sortino Ratio 계산

    샤프 비율과 유사하지만 하락 변동성만 고려합니다.
    양의 수익은 리스크로 보지 않습니다.

    Args:
        equity_curve: 자산 곡선 데이터
        risk_free_rate: 무위험 수익률 (연율, 기본값 2%)

    Returns:
        Sortino Ratio
    """
    if len(equity_curve) < 2:
        return 0.0

    df = pd.DataFrame(equity_curve)
    returns = df['equity'].pct_change().dropna()

    if len(returns) == 0:
        return 0.0

    # 평균 수익률
    mean_return = returns.mean()

    # 하락 편차 (downside deviation)
    # 무위험 수익률보다 낮은 수익률만 고려
    target_return = risk_free_rate / 252  # 일일 환산
    downside_returns = returns[returns < target_return]

    if len(downside_returns) == 0:
        return float('inf') if mean_return > 0 else 0.0

    downside_deviation = np.sqrt(np.mean((downside_returns - target_return) ** 2))

    if downside_deviation == 0:
        return 0.0

    # Sortino Ratio (연율화)
    sortino = (mean_return - target_return) / downside_deviation * np.sqrt(252)

    return float(sortino)


def calculate_calmar_ratio(
    total_return: float,
    max_drawdown: float,
    period_years: float = 1.0
) -> float:
    """
    Calmar Ratio 계산

    연율화된 수익률을 최대 낙폭으로 나눈 값입니다.
    리스크 대비 수익을 평가합니다.

    Args:
        total_return: 총 수익률 (%)
        max_drawdown: 최대 낙폭 (%, 음수)
        period_years: 백테스트 기간 (년)

    Returns:
        Calmar Ratio
    """
    if max_drawdown == 0 or period_years == 0:
        return 0.0

    # 연율화된 수익률
    annualized_return = ((1 + total_return / 100) ** (1 / period_years) - 1) * 100

    # Calmar Ratio = 연율 수익률 / abs(최대 낙폭)
    calmar = annualized_return / abs(max_drawdown)

    return float(calmar)


def calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
    """
    Profit Factor 계산

    총 이익 / 총 손실 비율입니다.
    1보다 크면 수익성 있는 전략입니다.

    Args:
        trades: 거래 내역 리스트

    Returns:
        Profit Factor
    """
    if not trades:
        return 0.0

    total_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    total_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))

    if total_loss == 0:
        return float('inf') if total_profit > 0 else 0.0

    return total_profit / total_loss


def calculate_expectancy(trades: List[Dict[str, Any]]) -> float:
    """
    Expectancy (기댓값) 계산

    거래당 평균 손익을 계산합니다.
    양수면 장기적으로 수익성 있는 전략입니다.

    Args:
        trades: 거래 내역 리스트

    Returns:
        거래당 평균 손익 ($)
    """
    if not trades:
        return 0.0

    total_pnl = sum(t['pnl'] for t in trades)
    return total_pnl / len(trades)


def calculate_win_loss_ratio(trades: List[Dict[str, Any]]) -> float:
    """
    Win/Loss Ratio 계산

    평균 승리 거래 크기 / 평균 손실 거래 크기

    Args:
        trades: 거래 내역 리스트

    Returns:
        Win/Loss Ratio
    """
    if not trades:
        return 0.0

    winning_trades = [t['pnl'] for t in trades if t['pnl'] > 0]
    losing_trades = [abs(t['pnl']) for t in trades if t['pnl'] < 0]

    if not winning_trades or not losing_trades:
        return 0.0

    avg_win = np.mean(winning_trades)
    avg_loss = np.mean(losing_trades)

    if avg_loss == 0:
        return 0.0

    return avg_win / avg_loss


def calculate_recovery_factor(
    total_return: float,
    max_drawdown: float
) -> float:
    """
    Recovery Factor 계산

    순이익 / 최대 낙폭
    전략이 손실을 얼마나 잘 회복하는지 평가합니다.

    Args:
        total_return: 총 수익률 (%)
        max_drawdown: 최대 낙폭 (%, 음수)

    Returns:
        Recovery Factor
    """
    if max_drawdown == 0:
        return 0.0

    return total_return / abs(max_drawdown)


def calculate_max_consecutive_wins(trades: List[Dict[str, Any]]) -> int:
    """최대 연속 승리 횟수"""
    if not trades:
        return 0

    max_wins = 0
    current_wins = 0

    for trade in trades:
        if trade['pnl'] > 0:
            current_wins += 1
            max_wins = max(max_wins, current_wins)
        else:
            current_wins = 0

    return max_wins


def calculate_max_consecutive_losses(trades: List[Dict[str, Any]]) -> int:
    """최대 연속 손실 횟수"""
    if not trades:
        return 0

    max_losses = 0
    current_losses = 0

    for trade in trades:
        if trade['pnl'] < 0:
            current_losses += 1
            max_losses = max(max_losses, current_losses)
        else:
            current_losses = 0

    return max_losses


def calculate_advanced_metrics(
    equity_curve: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    total_return: float,
    max_drawdown: float,
    initial_capital: float,
    start_date: str,
    end_date: str
) -> Dict[str, Any]:
    """
    고급 성과 지표 일괄 계산

    Args:
        equity_curve: 자산 곡선
        trades: 거래 내역
        total_return: 총 수익률 (%)
        max_drawdown: 최대 낙폭 (%)
        initial_capital: 초기 자본
        start_date: 시작 날짜
        end_date: 종료 날짜

    Returns:
        고급 지표 딕셔너리
    """
    # 백테스트 기간 계산 (년)
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    period_years = (end - start).days / 365.25

    # 순이익 계산
    net_profit = sum(t['pnl'] for t in trades) if trades else 0
    net_profit_pct = (net_profit / initial_capital) * 100 if initial_capital > 0 else 0

    return {
        # Risk-adjusted returns
        'sortino_ratio': calculate_sortino_ratio(equity_curve),
        'calmar_ratio': calculate_calmar_ratio(total_return, max_drawdown, period_years),

        # Profitability metrics
        'profit_factor': calculate_profit_factor(trades),
        'expectancy': calculate_expectancy(trades),
        'win_loss_ratio': calculate_win_loss_ratio(trades),
        'recovery_factor': calculate_recovery_factor(total_return, max_drawdown),

        # Streak statistics
        'max_consecutive_wins': calculate_max_consecutive_wins(trades),
        'max_consecutive_losses': calculate_max_consecutive_losses(trades),

        # Additional metrics
        'net_profit': net_profit,
        'net_profit_pct': net_profit_pct,
        'total_commission_paid': sum(t.get('commission_paid', 0) for t in trades),
        'avg_trade_duration_bars': np.mean([
            (pd.to_datetime(t['exit_time']) - pd.to_datetime(t['entry_time'])).total_seconds() / 3600
            for t in trades if t.get('exit_time')
        ]) if trades else 0,
    }
