"""
Parameter Sensitivity Analysis

Analyzes how sensitive a strategy's performance is to parameter changes.
Helps identify overfitting and parameter robustness.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Callable, Optional
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)


class ParameterSensitivityAnalyzer:
    """
    파라미터 민감도 분석기

    전략의 성능이 특정 파라미터 값에 얼마나 민감한지 분석합니다.
    """

    def __init__(
        self,
        backtest_func: Callable,
        parameter_ranges: Dict[str, List[Any]],
        n_jobs: int = 4
    ):
        """
        Args:
            backtest_func: 백테스트 실행 함수 (params) -> metrics dict
            parameter_ranges: 테스트할 파라미터 범위
                예: {'rsi_period': [10, 14, 20], 'oversold': [20, 30, 40]}
            n_jobs: 병렬 실행 워커 수
        """
        self.backtest_func = backtest_func
        self.parameter_ranges = parameter_ranges
        self.n_jobs = n_jobs
        self.results = []

    def grid_search(self) -> pd.DataFrame:
        """
        그리드 서치: 모든 파라미터 조합을 테스트

        Returns:
            DataFrame with columns: param1, param2, ..., total_return, sharpe_ratio, etc.
        """
        # 모든 파라미터 조합 생성
        param_names = list(self.parameter_ranges.keys())
        param_values = list(self.parameter_ranges.values())
        combinations = list(product(*param_values))

        logger.info(f"Grid search: {len(combinations)} combinations")

        results = []

        # 병렬 실행
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            # 작업 제출
            future_to_params = {}
            for combo in combinations:
                params = dict(zip(param_names, combo))
                future = executor.submit(self._run_backtest_safe, params)
                future_to_params[future] = params

            # 결과 수집
            for future in as_completed(future_to_params):
                params = future_to_params[future]
                try:
                    metrics = future.result()
                    result = {**params, **metrics}
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed for params {params}: {e}")

        df = pd.DataFrame(results)
        self.results = df
        return df

    def _run_backtest_safe(self, params: Dict[str, Any]) -> Dict[str, float]:
        """안전한 백테스트 실행 (에러 핸들링)"""
        try:
            metrics = self.backtest_func(params)
            return metrics
        except Exception as e:
            logger.error(f"Backtest failed for {params}: {e}")
            return {
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0
            }

    def calculate_heatmap_data(
        self,
        param1: str,
        param2: str,
        metric: str = 'total_return'
    ) -> Dict[str, Any]:
        """
        2D 히트맵 데이터 생성

        Args:
            param1: X축 파라미터
            param2: Y축 파라미터
            metric: 표시할 메트릭 (total_return, sharpe_ratio 등)

        Returns:
            Dict with x_values, y_values, z_values (2D array)
        """
        if self.results is None or len(self.results) == 0:
            raise ValueError("No results. Run grid_search first.")

        # 파라미터 값 추출
        x_values = sorted(self.results[param1].unique())
        y_values = sorted(self.results[param2].unique())

        # 2D 그리드 생성
        z_values = np.full((len(y_values), len(x_values)), np.nan)

        for _, row in self.results.iterrows():
            x_idx = x_values.index(row[param1])
            y_idx = y_values.index(row[param2])
            z_values[y_idx, x_idx] = row[metric]

        return {
            'x_values': [float(v) for v in x_values],
            'y_values': [float(v) for v in y_values],
            'z_values': z_values.tolist(),
            'x_label': param1,
            'y_label': param2,
            'z_label': metric
        }

    def find_optimal_params(
        self,
        metric: str = 'total_return',
        maximize: bool = True
    ) -> Dict[str, Any]:
        """
        최적 파라미터 조합 찾기

        Args:
            metric: 최적화할 메트릭
            maximize: True면 최대화, False면 최소화

        Returns:
            Dict with optimal parameters and metrics
        """
        if self.results is None or len(self.results) == 0:
            raise ValueError("No results. Run grid_search first.")

        if maximize:
            best_idx = self.results[metric].idxmax()
        else:
            best_idx = self.results[metric].idxmin()

        best_row = self.results.loc[best_idx]

        # 파라미터와 메트릭 분리
        param_cols = list(self.parameter_ranges.keys())
        optimal_params = {col: best_row[col] for col in param_cols}

        metrics = {
            col: best_row[col]
            for col in self.results.columns
            if col not in param_cols
        }

        return {
            'parameters': optimal_params,
            'metrics': metrics
        }

    def calculate_parameter_stability(self) -> Dict[str, float]:
        """
        파라미터 안정성 점수 계산

        파라미터가 조금 바뀌었을 때 성능이 크게 변하지 않으면 안정적임

        Returns:
            Dict of {param_name: stability_score}
            stability_score: 0 (불안정) ~ 1 (안정)
        """
        if self.results is None or len(self.results) == 0:
            raise ValueError("No results. Run grid_search first.")

        stability_scores = {}

        for param in self.parameter_ranges.keys():
            # 파라미터별로 그룹화하여 성능 분산 계산
            grouped = self.results.groupby(param)['total_return'].agg(['mean', 'std'])

            # 표준편차가 작을수록 안정적
            # 정규화: 1 / (1 + std/mean)
            mean_return = grouped['mean'].mean()
            std_return = grouped['std'].mean()

            if abs(mean_return) > 0.01:
                stability = 1 / (1 + abs(std_return / mean_return))
            else:
                stability = 0.5  # 중립

            stability_scores[param] = float(stability)

        return stability_scores

    def calculate_parameter_importance(self) -> Dict[str, float]:
        """
        파라미터 중요도 계산

        파라미터 변화에 따른 성능 변화의 범위가 클수록 중요

        Returns:
            Dict of {param_name: importance_score}
        """
        if self.results is None or len(self.results) == 0:
            raise ValueError("No results. Run grid_search first.")

        importance_scores = {}

        for param in self.parameter_ranges.keys():
            grouped = self.results.groupby(param)['total_return']

            # 파라미터별 성능 범위
            return_range = grouped.mean().max() - grouped.mean().min()

            # 전체 성능 범위로 정규화
            total_range = self.results['total_return'].max() - self.results['total_return'].min()

            if total_range > 0:
                importance = abs(return_range / total_range)
            else:
                importance = 0.0

            importance_scores[param] = float(importance)

        return importance_scores


def bayesian_optimization(
    backtest_func: Callable,
    parameter_ranges: Dict[str, Tuple[float, float]],
    n_calls: int = 50,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    베이지안 최적화

    그리드 서치보다 효율적으로 최적 파라미터를 찾습니다.

    Args:
        backtest_func: 백테스트 실행 함수
        parameter_ranges: 파라미터 범위 (연속값)
            예: {'rsi_period': (5, 50), 'oversold': (10, 40)}
        n_calls: 시도 횟수
        random_state: 랜덤 시드

    Returns:
        Dict with optimal parameters and convergence history
    """
    try:
        from skopt import gp_minimize
        from skopt.space import Real, Integer
        from skopt.utils import use_named_args
    except ImportError:
        raise ImportError("scikit-optimize is required for Bayesian optimization")

    # 파라미터 공간 정의
    param_names = list(parameter_ranges.keys())
    space = []

    for name, (low, high) in parameter_ranges.items():
        if isinstance(low, int) and isinstance(high, int):
            space.append(Integer(low, high, name=name))
        else:
            space.append(Real(low, high, name=name))

    # 목적 함수 정의 (최대화 -> 최소화로 변환)
    @use_named_args(space)
    def objective(**params):
        metrics = backtest_func(params)
        # Sharpe ratio를 음수로 (최소화 문제로 변환)
        return -metrics.get('sharpe_ratio', 0.0)

    # 최적화 실행
    result = gp_minimize(
        objective,
        space,
        n_calls=n_calls,
        random_state=random_state,
        n_jobs=1,  # 베이지안 최적화는 순차 실행
        verbose=False
    )

    # 최적 파라미터
    optimal_params = dict(zip(param_names, result.x))

    # 수렴 히스토리
    convergence = {
        'iterations': list(range(len(result.func_vals))),
        'scores': [-val for val in result.func_vals],  # 다시 양수로
        'best_score': -result.fun
    }

    return {
        'optimal_parameters': optimal_params,
        'best_score': -result.fun,
        'convergence': convergence,
        'n_calls': n_calls
    }
