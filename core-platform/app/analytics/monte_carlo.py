"""
Monte Carlo 시뮬레이션

거래 순서를 랜덤하게 섞어서 전략의 신뢰도를 검증합니다.
"운이 좋아서 수익이 난 건 아닐까?"에 대한 답을 제공합니다.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
import multiprocessing as mp
from functools import partial


@dataclass
class MonteCarloResult:
    """Monte Carlo 시뮬레이션 결과"""
    n_simulations: int
    initial_capital: float

    # 최종 자본 통계
    final_capital_mean: float
    final_capital_median: float
    final_capital_std: float
    final_capital_5th: float
    final_capital_95th: float
    final_capital_min: float
    final_capital_max: float

    # 수익률 통계
    total_return_mean: float
    total_return_median: float
    total_return_std: float
    total_return_5th: float
    total_return_95th: float

    # MDD 통계
    max_drawdown_mean: float
    max_drawdown_median: float
    max_drawdown_worst: float
    max_drawdown_best: float

    # 샤프 비율 통계
    sharpe_ratio_mean: float
    sharpe_ratio_median: float

    # 전체 시뮬레이션 결과 (샘플링)
    sample_equity_curves: List[List[float]]  # 일부 equity curve 샘플
    all_final_capitals: List[float]  # 모든 최종 자본


def calculate_dynamic_kelly(
    past_trades: List[Dict[str, Any]],
    kelly_window: int = 20,
    kelly_fraction: float = 0.5
) -> float:
    """
    과거 거래를 바탕으로 Kelly fraction 계산

    Args:
        past_trades: 과거 거래 목록
        kelly_window: 계산에 사용할 최근 거래 수
        kelly_fraction: Kelly 조정 비율

    Returns:
        Kelly fraction (0.1 ~ 0.5)
    """
    if len(past_trades) < 5:
        return 0.25  # 초기에는 보수적으로

    # 최근 거래만 사용
    recent = past_trades[-kelly_window:]

    # 승리/손실 분리
    wins = [t for t in recent if t['pnl_pct'] > 0]
    losses = [t for t in recent if t['pnl_pct'] < 0]

    if not wins or not losses:
        return 0.25

    # 승률 계산
    p = len(wins) / len(recent)
    q = 1 - p

    # 평균 승리/손실 비율
    avg_win_pct = sum(abs(t['pnl_pct']) for t in wins) / len(wins)
    avg_loss_pct = sum(abs(t['pnl_pct']) for t in losses) / len(losses)
    b = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else 1.0

    # Kelly 계산
    kelly = (p * b - q) / b
    kelly = kelly * kelly_fraction
    kelly = max(0.1, min(0.5, kelly))

    return kelly


def shuffle_trades_and_calculate_equity(
    trades: List[Dict[str, Any]],
    initial_capital: float,
    use_dynamic_kelly: bool = True,
    kelly_window: int = 20,
    kelly_fraction: float = 0.5,
    seed: int | None = None
) -> Tuple[float, float, float, List[float]]:
    """
    거래 순서를 섞고 equity curve를 계산합니다.

    Args:
        trades: 거래 목록
        initial_capital: 초기 자본
        use_dynamic_kelly: Kelly를 동적으로 재계산할지 여부
        kelly_window: Kelly 계산 윈도우
        kelly_fraction: Kelly 조정 비율
        seed: 랜덤 시드 (재현성)

    Returns:
        (최종 자본, 최대 낙폭, 샤프 비율, equity curve)
    """
    if seed is not None:
        np.random.seed(seed)

    # 거래 순서 섞기
    shuffled_trades = trades.copy()
    np.random.shuffle(shuffled_trades)

    # Equity curve 계산
    equity = initial_capital
    equity_curve = [equity]
    executed_trades = []

    for trade in shuffled_trades:
        pnl_pct = trade.get('pnl_pct', 0)

        if use_dynamic_kelly:
            # 과거 거래 기반으로 Kelly 재계산
            kelly_size = calculate_dynamic_kelly(executed_trades, kelly_window, kelly_fraction)
        else:
            # 원래 position_size 사용
            kelly_size = trade.get('position_size_pct', 1.0)

        # 포지션 크기만큼의 자본에 대한 수익률 적용
        position_capital = equity * kelly_size
        position_return = position_capital * (pnl_pct / 100)

        equity = equity + position_return
        equity_curve.append(equity)

        # 실행된 거래 기록 (Kelly 재계산용)
        executed_trades.append({
            'pnl_pct': pnl_pct,
            'position_size_pct': kelly_size
        })

    final_capital = equity_curve[-1]

    # 최대 낙폭 계산
    equity_series = pd.Series(equity_curve)
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak * 100
    max_drawdown = drawdown.min()

    # 샤프 비율 계산
    returns = equity_series.pct_change().dropna()
    if len(returns) > 1 and returns.std() > 0:
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe_ratio = 0.0

    return final_capital, max_drawdown, sharpe_ratio, equity_curve


def run_single_simulation(
    args: Tuple[List[Dict[str, Any]], float, bool, int, float, int]
) -> Tuple[float, float, float, List[float]]:
    """
    단일 시뮬레이션 실행 (병렬 처리용)

    Args:
        args: (trades, initial_capital, use_dynamic_kelly, kelly_window, kelly_fraction, seed)

    Returns:
        (최종 자본, MDD, 샤프, equity curve)
    """
    trades, initial_capital, use_dynamic_kelly, kelly_window, kelly_fraction, seed = args
    return shuffle_trades_and_calculate_equity(
        trades, initial_capital, use_dynamic_kelly, kelly_window, kelly_fraction, seed
    )


def monte_carlo_simulation(
    trades: List[Dict[str, Any]],
    initial_capital: float,
    n_simulations: int = 1000,
    n_workers: int | None = None,
    n_sample_curves: int = 10,
    use_dynamic_kelly: bool = True,
    kelly_window: int = 20,
    kelly_fraction: float = 0.5
) -> MonteCarloResult:
    """
    Monte Carlo 시뮬레이션 실행

    Args:
        trades: 백테스트 거래 내역
        initial_capital: 초기 자본
        n_simulations: 시뮬레이션 횟수 (기본값: 1000)
        n_workers: 병렬 처리 워커 수 (None이면 CPU 코어 수)
        n_sample_curves: 저장할 equity curve 샘플 수
        use_dynamic_kelly: Kelly를 동적으로 재계산할지 여부
        kelly_window: Kelly 계산 윈도우
        kelly_fraction: Kelly 조정 비율

    Returns:
        MonteCarloResult
    """
    if not trades:
        raise ValueError("거래 내역이 비어있습니다.")

    if n_simulations < 100:
        raise ValueError("시뮬레이션 횟수는 최소 100회 이상이어야 합니다.")

    # 병렬 처리 설정
    if n_workers is None:
        n_workers = max(1, mp.cpu_count() - 1)

    # 시뮬레이션 인자 준비
    args_list = [
        (trades, initial_capital, use_dynamic_kelly, kelly_window, kelly_fraction, i)
        for i in range(n_simulations)
    ]

    # 병렬 실행
    mode_str = "Dynamic Kelly" if use_dynamic_kelly else "Static"
    print(f"🎲 Monte Carlo 시뮬레이션 시작: {n_simulations}회, {n_workers} 워커 ({mode_str})")

    with mp.Pool(processes=n_workers) as pool:
        results = pool.map(run_single_simulation, args_list)

    # 결과 수집
    final_capitals = [r[0] for r in results]
    max_drawdowns = [r[1] for r in results]
    sharpe_ratios = [r[2] for r in results]
    equity_curves = [r[3] for r in results]

    # 수익률 계산
    total_returns = [(fc - initial_capital) / initial_capital * 100 for fc in final_capitals]

    # 통계 계산
    final_capital_mean = np.mean(final_capitals)
    final_capital_median = np.median(final_capitals)
    final_capital_std = np.std(final_capitals)
    final_capital_5th = np.percentile(final_capitals, 5)
    final_capital_95th = np.percentile(final_capitals, 95)
    final_capital_min = np.min(final_capitals)
    final_capital_max = np.max(final_capitals)

    total_return_mean = np.mean(total_returns)
    total_return_median = np.median(total_returns)
    total_return_std = np.std(total_returns)
    total_return_5th = np.percentile(total_returns, 5)
    total_return_95th = np.percentile(total_returns, 95)

    max_drawdown_mean = np.mean(max_drawdowns)
    max_drawdown_median = np.median(max_drawdowns)
    max_drawdown_worst = np.min(max_drawdowns)
    max_drawdown_best = np.max(max_drawdowns)

    sharpe_ratio_mean = np.mean(sharpe_ratios)
    sharpe_ratio_median = np.median(sharpe_ratios)

    # Equity curve 샘플링 (균등 간격)
    sample_indices = np.linspace(0, n_simulations - 1, n_sample_curves, dtype=int)
    sample_equity_curves = [equity_curves[i] for i in sample_indices]

    print(f"✅ Monte Carlo 시뮬레이션 완료")
    print(f"   평균 수익률: {total_return_mean:.2f}% (±{total_return_std:.2f}%)")
    print(f"   5%~95% 구간: {total_return_5th:.2f}% ~ {total_return_95th:.2f}%")

    return MonteCarloResult(
        n_simulations=n_simulations,
        initial_capital=initial_capital,
        final_capital_mean=final_capital_mean,
        final_capital_median=final_capital_median,
        final_capital_std=final_capital_std,
        final_capital_5th=final_capital_5th,
        final_capital_95th=final_capital_95th,
        final_capital_min=final_capital_min,
        final_capital_max=final_capital_max,
        total_return_mean=total_return_mean,
        total_return_median=total_return_median,
        total_return_std=total_return_std,
        total_return_5th=total_return_5th,
        total_return_95th=total_return_95th,
        max_drawdown_mean=max_drawdown_mean,
        max_drawdown_median=max_drawdown_median,
        max_drawdown_worst=max_drawdown_worst,
        max_drawdown_best=max_drawdown_best,
        sharpe_ratio_mean=sharpe_ratio_mean,
        sharpe_ratio_median=sharpe_ratio_median,
        sample_equity_curves=sample_equity_curves,
        all_final_capitals=final_capitals,
    )


def analyze_monte_carlo_risk(result: MonteCarloResult) -> Dict[str, Any]:
    """
    Monte Carlo 결과를 기반으로 리스크 분석

    Args:
        result: Monte Carlo 결과

    Returns:
        리스크 분석 딕셔너리
    """
    # 손실 확률 계산
    losing_scenarios = sum(1 for fc in result.all_final_capitals if fc < result.initial_capital)
    probability_of_loss = (losing_scenarios / result.n_simulations) * 100

    # VaR (Value at Risk) - 5% 최악의 경우
    var_5 = result.initial_capital - result.final_capital_5th

    # CVaR (Conditional VaR) - 하위 5%의 평균
    sorted_capitals = sorted(result.all_final_capitals)
    worst_5_pct = sorted_capitals[:int(result.n_simulations * 0.05)]
    cvar_5 = result.initial_capital - np.mean(worst_5_pct)

    # 신뢰 구간 (95%)
    confidence_interval = (result.final_capital_5th, result.final_capital_95th)

    # 변동성 비율
    volatility_ratio = result.final_capital_std / result.final_capital_mean if result.final_capital_mean > 0 else 0

    return {
        'probability_of_loss': probability_of_loss,
        'value_at_risk_5': var_5,
        'conditional_var_5': cvar_5,
        'confidence_interval_95': confidence_interval,
        'volatility_ratio': volatility_ratio,
        'risk_grade': _calculate_risk_grade(probability_of_loss, volatility_ratio),
    }


def _calculate_risk_grade(prob_loss: float, volatility: float) -> str:
    """리스크 등급 계산"""
    if prob_loss > 40 or volatility > 0.5:
        return 'HIGH'
    elif prob_loss > 25 or volatility > 0.3:
        return 'MEDIUM'
    else:
        return 'LOW'
