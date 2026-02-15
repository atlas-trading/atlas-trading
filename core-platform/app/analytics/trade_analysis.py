"""
거래 수준 분석

MAE (Maximum Adverse Excursion), MFE (Maximum Favorable Excursion),
보유 기간 분포 등 거래 품질을 평가합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple


def calculate_mae_mfe(
    trades: List[Dict[str, Any]],
    df: pd.DataFrame
) -> List[Dict[str, Any]]:
    """
    각 거래의 MAE/MFE 계산

    MAE (Maximum Adverse Excursion): 포지션 진입 후 최대 손실폭
    MFE (Maximum Favorable Excursion): 포지션 진입 후 최대 이익폭

    Args:
        trades: 거래 내역
        df: OHLCV 데이터프레임

    Returns:
        MAE/MFE가 추가된 거래 리스트
    """
    enriched_trades = []

    for trade in trades:
        entry_time = pd.to_datetime(trade['entry_time'])
        exit_time = pd.to_datetime(trade['exit_time']) if trade.get('exit_time') else None

        if not exit_time:
            continue

        # 진입~청산 구간의 가격 데이터
        mask = (df['timestamp'] >= entry_time) & (df['timestamp'] <= exit_time)
        position_bars = df[mask]

        if len(position_bars) == 0:
            continue

        entry_price = trade['entry_price']
        side = trade['side']

        if side == 'long':
            # Long 포지션
            # MAE: 진입가 대비 최저가 (손실폭)
            min_price = position_bars['low'].min()
            mae = ((min_price - entry_price) / entry_price) * 100

            # MFE: 진입가 대비 최고가 (이익폭)
            max_price = position_bars['high'].max()
            mfe = ((max_price - entry_price) / entry_price) * 100

        else:  # short
            # Short 포지션
            max_price = position_bars['high'].max()
            mae = ((entry_price - max_price) / entry_price) * 100

            min_price = position_bars['low'].min()
            mfe = ((entry_price - min_price) / entry_price) * 100

        enriched_trades.append({
            **trade,
            'mae': mae,
            'mfe': mfe,
            'mae_to_pnl_ratio': abs(mae / trade['pnl_pct']) if trade['pnl_pct'] != 0 else 0,
            'efficiency': (trade['pnl_pct'] / mfe * 100) if mfe != 0 else 0,  # 실현 효율
        })

    return enriched_trades


def analyze_holding_periods(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    거래 보유 기간 분석

    Args:
        trades: 거래 내역

    Returns:
        보유 기간 통계
    """
    if not trades:
        return {}

    durations = []
    for trade in trades:
        if trade.get('exit_time'):
            entry = pd.to_datetime(trade['entry_time'])
            exit = pd.to_datetime(trade['exit_time'])
            duration_hours = (exit - entry).total_seconds() / 3600
            durations.append(duration_hours)

    if not durations:
        return {}

    return {
        'avg_holding_hours': np.mean(durations),
        'median_holding_hours': np.median(durations),
        'min_holding_hours': np.min(durations),
        'max_holding_hours': np.max(durations),
        'std_holding_hours': np.std(durations),
    }


def analyze_trade_distribution(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    거래 손익 분포 분석

    Args:
        trades: 거래 내역

    Returns:
        손익 분포 통계
    """
    if not trades:
        return {}

    pnls = [t['pnl'] for t in trades]
    pnl_pcts = [t['pnl_pct'] for t in trades]

    winning_trades = [p for p in pnls if p > 0]
    losing_trades = [p for p in pnls if p < 0]

    return {
        # PnL 분포
        'avg_pnl': np.mean(pnls),
        'median_pnl': np.median(pnls),
        'std_pnl': np.std(pnls),
        'skewness': float(pd.Series(pnls).skew()) if len(pnls) > 2 else 0,
        'kurtosis': float(pd.Series(pnls).kurtosis()) if len(pnls) > 3 else 0,

        # 승/패 분포
        'largest_win': max(pnls) if pnls else 0,
        'largest_loss': min(pnls) if pnls else 0,
        'avg_win': np.mean(winning_trades) if winning_trades else 0,
        'avg_loss': np.mean(losing_trades) if losing_trades else 0,

        # 백분위수
        'pnl_25th_percentile': np.percentile(pnls, 25) if pnls else 0,
        'pnl_75th_percentile': np.percentile(pnls, 75) if pnls else 0,
    }


def analyze_trade_quality(
    trades: List[Dict[str, Any]],
    initial_capital: float
) -> Dict[str, Any]:
    """
    거래 품질 분석

    Args:
        trades: 거래 내역
        initial_capital: 초기 자본

    Returns:
        거래 품질 지표
    """
    if not trades:
        return {}

    # R-multiple 분석 (리스크 대비 수익)
    # 간단히 손익률 기준으로 계산
    pnl_pcts = [t['pnl_pct'] for t in trades]

    # 승률별 거래 수
    small_wins = len([p for p in pnl_pcts if 0 < p < 1])
    medium_wins = len([p for p in pnl_pcts if 1 <= p < 5])
    large_wins = len([p for p in pnl_pcts if p >= 5])

    small_losses = len([p for p in pnl_pcts if -1 < p < 0])
    medium_losses = len([p for p in pnl_pcts if -5 < p <= -1])
    large_losses = len([p for p in pnl_pcts if p <= -5])

    # 거래 크기 분석
    trade_sizes = [t['quantity'] * t['entry_price'] for t in trades]
    avg_trade_size = np.mean(trade_sizes) if trade_sizes else 0
    avg_trade_size_pct = (avg_trade_size / initial_capital * 100) if initial_capital > 0 else 0

    return {
        # 승률 분포
        'small_wins_count': small_wins,
        'medium_wins_count': medium_wins,
        'large_wins_count': large_wins,
        'small_losses_count': small_losses,
        'medium_losses_count': medium_losses,
        'large_losses_count': large_losses,

        # 거래 크기
        'avg_trade_size_usd': avg_trade_size,
        'avg_trade_size_pct': avg_trade_size_pct,
        'max_trade_size_usd': max(trade_sizes) if trade_sizes else 0,
        'min_trade_size_usd': min(trade_sizes) if trade_sizes else 0,
    }


def analyze_time_patterns(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    시간 패턴 분석 (요일별, 시간대별 성과)

    Args:
        trades: 거래 내역

    Returns:
        시간 패턴 통계
    """
    if not trades:
        return {}

    # 요일별 집계
    weekday_pnl = {i: [] for i in range(7)}  # 0=월요일, 6=일요일
    for trade in trades:
        entry_time = pd.to_datetime(trade['entry_time'])
        weekday = entry_time.weekday()
        weekday_pnl[weekday].append(trade['pnl'])

    weekday_stats = {
        f'weekday_{i}_avg_pnl': np.mean(pnls) if pnls else 0
        for i, pnls in weekday_pnl.items()
    }

    # 시간대별 집계 (4시간 단위)
    hour_buckets = {i: [] for i in range(0, 24, 4)}
    for trade in trades:
        entry_time = pd.to_datetime(trade['entry_time'])
        hour_bucket = (entry_time.hour // 4) * 4
        hour_buckets[hour_bucket].append(trade['pnl'])

    hour_stats = {
        f'hour_{h}_avg_pnl': np.mean(pnls) if pnls else 0
        for h, pnls in hour_buckets.items()
    }

    return {
        **weekday_stats,
        **hour_stats,
    }


def analyze_trades(
    trades: List[Dict[str, Any]],
    df: pd.DataFrame,
    initial_capital: float
) -> Dict[str, Any]:
    """
    거래 분석 일괄 실행

    Args:
        trades: 거래 내역
        df: OHLCV 데이터프레임
        initial_capital: 초기 자본

    Returns:
        종합 거래 분석 결과
    """
    # MAE/MFE 계산 (시간이 오래 걸릴 수 있음)
    enriched_trades = calculate_mae_mfe(trades, df)

    # MAE/MFE 통계
    mae_mfe_stats = {}
    if enriched_trades:
        maes = [t['mae'] for t in enriched_trades]
        mfes = [t['mfe'] for t in enriched_trades]
        efficiencies = [t['efficiency'] for t in enriched_trades]

        mae_mfe_stats = {
            'avg_mae': np.mean(maes),
            'avg_mfe': np.mean(mfes),
            'avg_efficiency': np.mean(efficiencies),
            'max_mae': min(maes),  # MAE는 음수이므로 min이 최대 손실
            'max_mfe': max(mfes),
        }

    return {
        'holding_periods': analyze_holding_periods(trades),
        'distribution': analyze_trade_distribution(trades),
        'quality': analyze_trade_quality(trades, initial_capital),
        'time_patterns': analyze_time_patterns(trades),
        'mae_mfe': mae_mfe_stats,
        'enriched_trades': enriched_trades,  # MAE/MFE가 추가된 거래 리스트
    }
