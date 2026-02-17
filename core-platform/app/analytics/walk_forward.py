"""
Walk-Forward Optimization

Prevents overfitting by using rolling train/test splits
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Callable, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    워크 포워드 최적화

    시계열 데이터를 훈련/테스트로 분할하고 순환시키면서
    과적합을 방지하고 실제 성능을 추정합니다.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        train_period_days: int = 365,
        test_period_days: int = 180,
        window_type: str = 'anchored'  # 'anchored' or 'rolling'
    ):
        """
        Args:
            data: OHLCV 데이터 (timestamp 컬럼 필요)
            train_period_days: 훈련 기간 (일)
            test_period_days: 테스트 기간 (일)
            window_type: 'anchored' (확장 윈도우) or 'rolling' (고정 윈도우)
        """
        self.data = data.sort_values('timestamp').reset_index(drop=True)
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.window_type = window_type

        # 날짜 범위 계산
        self.start_date = self.data['timestamp'].min()
        self.end_date = self.data['timestamp'].max()
        self.total_days = (self.end_date - self.start_date).days

    def generate_splits(self) -> List[Dict[str, Any]]:
        """
        훈련/테스트 분할 생성

        Returns:
            List of dicts with train_df, test_df, train_start, train_end, test_start, test_end
        """
        splits = []

        # 첫 훈련 기간 시작
        current_train_start = self.start_date
        current_train_end = current_train_start + timedelta(days=self.train_period_days)

        while True:
            # 테스트 기간 계산
            current_test_start = current_train_end
            current_test_end = current_test_start + timedelta(days=self.test_period_days)

            # 데이터가 충분하지 않으면 중단
            if current_test_end > self.end_date:
                break

            # 훈련/테스트 데이터 분할
            train_df = self.data[
                (self.data['timestamp'] >= current_train_start) &
                (self.data['timestamp'] < current_train_end)
            ].copy()

            test_df = self.data[
                (self.data['timestamp'] >= current_test_start) &
                (self.data['timestamp'] < current_test_end)
            ].copy()

            # 데이터가 충분한지 확인
            if len(train_df) < 30 or len(test_df) < 10:
                logger.warning(f"Insufficient data: train={len(train_df)}, test={len(test_df)}")
                break

            splits.append({
                'train_df': train_df,
                'test_df': test_df,
                'train_start': current_train_start,
                'train_end': current_train_end,
                'test_start': current_test_start,
                'test_end': current_test_end,
                'fold': len(splits) + 1
            })

            # 다음 윈도우로 이동
            if self.window_type == 'anchored':
                # Anchored: 훈련 시작은 고정, 끝만 확장
                current_train_end = current_test_end
            else:  # rolling
                # Rolling: 고정 크기 윈도우 이동
                current_train_start = current_test_end
                current_train_end = current_train_start + timedelta(days=self.train_period_days)

        logger.info(f"Generated {len(splits)} walk-forward splits")
        return splits

    def optimize_and_validate(
        self,
        optimize_func: Callable,
        backtest_func: Callable,
        parameter_ranges: Dict[str, List[Any]]
    ) -> Dict[str, Any]:
        """
        각 분할에서 최적화 후 검증

        Args:
            optimize_func: 파라미터 최적화 함수 (train_df, param_ranges) -> optimal_params
            backtest_func: 백테스트 함수 (df, params) -> metrics
            parameter_ranges: 파라미터 범위

        Returns:
            Dict with fold results and aggregated metrics
        """
        splits = self.generate_splits()
        results = []

        for split in splits:
            fold = split['fold']
            logger.info(f"Processing fold {fold}/{len(splits)}")

            # 훈련: 최적 파라미터 찾기
            try:
                optimal_params = optimize_func(split['train_df'], parameter_ranges)
            except Exception as e:
                logger.error(f"Optimization failed for fold {fold}: {e}")
                continue

            # 훈련 데이터에서 백테스트 (In-sample)
            train_metrics = backtest_func(split['train_df'], optimal_params)

            # 테스트 데이터에서 백테스트 (Out-of-sample)
            test_metrics = backtest_func(split['test_df'], optimal_params)

            results.append({
                'fold': fold,
                'train_start': split['train_start'].isoformat(),
                'train_end': split['train_end'].isoformat(),
                'test_start': split['test_start'].isoformat(),
                'test_end': split['test_end'].isoformat(),
                'optimal_params': optimal_params,
                'train_metrics': train_metrics,
                'test_metrics': test_metrics,
                'overfitting_ratio': self._calculate_overfitting_ratio(
                    train_metrics, test_metrics
                )
            })

        # 집계 메트릭
        aggregated = self._aggregate_results(results)

        return {
            'fold_results': results,
            'aggregated_metrics': aggregated,
            'n_folds': len(results),
            'window_type': self.window_type,
            'train_period_days': self.train_period_days,
            'test_period_days': self.test_period_days
        }

    def _calculate_overfitting_ratio(
        self,
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float]
    ) -> float:
        """
        과적합 비율 계산

        train 성능이 test보다 훨씬 좋으면 과적합

        Returns:
            Ratio: < 1 (underfitting), ~1 (good), > 1 (overfitting)
        """
        train_return = train_metrics.get('total_return', 0.0)
        test_return = test_metrics.get('total_return', 0.0)

        if abs(test_return) < 0.01:  # Avoid division by zero
            return 0.0

        return train_return / test_return

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """결과 집계"""
        if not results:
            return {}

        # 테스트 성능만 집계 (실제 성능 추정)
        test_returns = [r['test_metrics']['total_return'] for r in results]
        test_sharpes = [r['test_metrics'].get('sharpe_ratio', 0.0) for r in results]
        overfitting_ratios = [r['overfitting_ratio'] for r in results]

        return {
            'avg_test_return': float(np.mean(test_returns)),
            'std_test_return': float(np.std(test_returns)),
            'min_test_return': float(np.min(test_returns)),
            'max_test_return': float(np.max(test_returns)),
            'avg_test_sharpe': float(np.mean(test_sharpes)),
            'avg_overfitting_ratio': float(np.mean(overfitting_ratios)),
            'consistency_score': self._calculate_consistency(test_returns)
        }

    def _calculate_consistency(self, returns: List[float]) -> float:
        """
        일관성 점수 계산

        모든 fold에서 양수 수익이면 1.0, 모두 음수면 0.0

        Returns:
            Score: 0.0 (inconsistent) ~ 1.0 (consistent)
        """
        if not returns:
            return 0.0

        positive_count = sum(1 for r in returns if r > 0)
        return positive_count / len(returns)


def simple_grid_search_optimizer(
    train_df: pd.DataFrame,
    parameter_ranges: Dict[str, List[Any]],
    backtest_func: Callable,
    metric: str = 'sharpe_ratio'
) -> Dict[str, Any]:
    """
    간단한 그리드 서치 최적화

    Args:
        train_df: 훈련 데이터
        parameter_ranges: 파라미터 범위
        backtest_func: 백테스트 함수
        metric: 최적화할 메트릭

    Returns:
        최적 파라미터
    """
    from itertools import product

    param_names = list(parameter_ranges.keys())
    param_values = list(parameter_ranges.values())
    combinations = list(product(*param_values))

    best_params = None
    best_score = -np.inf

    for combo in combinations:
        params = dict(zip(param_names, combo))

        try:
            metrics = backtest_func(train_df, params)
            score = metrics.get(metric, 0.0)

            if score > best_score:
                best_score = score
                best_params = params
        except Exception as e:
            logger.warning(f"Backtest failed for {params}: {e}")
            continue

    return best_params if best_params else dict(zip(param_names, combinations[0]))
