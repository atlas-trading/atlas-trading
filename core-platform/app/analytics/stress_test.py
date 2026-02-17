"""
Advanced Stress Testing

Tests strategy robustness under extreme market conditions
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StressTestEngine:
    """
    고급 스트레스 테스트 엔진

    슬리피지, 레이턴시, 역사적 위기 등 극한 상황에서 전략 성능 테스트
    """

    def __init__(self, backtest_func: Callable):
        """
        Args:
            backtest_func: 백테스트 실행 함수 (df, params, slippage, latency) -> metrics
        """
        self.backtest_func = backtest_func

    def test_slippage(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        slippage_levels: List[float] = [0.0, 0.001, 0.003, 0.005, 0.01]
    ) -> Dict[str, Any]:
        """
        슬리피지 스트레스 테스트

        실제 거래에서 체결가가 예상가와 다를 때의 영향 분석

        Args:
            df: 가격 데이터
            params: 전략 파라미터
            slippage_levels: 테스트할 슬리피지 수준 (0.001 = 0.1%)

        Returns:
            Dict with slippage test results
        """
        results = []

        for slippage in slippage_levels:
            try:
                metrics = self.backtest_func(df, params, slippage=slippage, latency_ms=0)

                results.append({
                    'slippage_pct': slippage * 100,
                    'total_return': metrics.get('total_return', 0.0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                    'total_trades': metrics.get('total_trades', 0),
                    'profit_factor': metrics.get('profit_factor', 0.0)
                })
            except Exception as e:
                logger.error(f"Slippage test failed at {slippage}: {e}")

        # 슬리피지 민감도 계산
        sensitivity = self._calculate_sensitivity(results, 'slippage_pct', 'total_return')

        return {
            'test_type': 'slippage',
            'results': results,
            'sensitivity_score': sensitivity,
            'interpretation': self._interpret_slippage_sensitivity(sensitivity)
        }

    def test_latency(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        latency_levels: List[int] = [0, 10, 50, 100, 500, 1000]
    ) -> Dict[str, Any]:
        """
        레이턴시 스트레스 테스트

        주문 실행 지연이 성능에 미치는 영향 분석

        Args:
            df: 가격 데이터
            params: 전략 파라미터
            latency_levels: 테스트할 레이턴시 (밀리초)

        Returns:
            Dict with latency test results
        """
        results = []

        for latency_ms in latency_levels:
            try:
                metrics = self.backtest_func(df, params, slippage=0.0, latency_ms=latency_ms)

                results.append({
                    'latency_ms': latency_ms,
                    'total_return': metrics.get('total_return', 0.0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                    'total_trades': metrics.get('total_trades', 0),
                    'missed_opportunities': metrics.get('missed_trades', 0)
                })
            except Exception as e:
                logger.error(f"Latency test failed at {latency_ms}ms: {e}")

        sensitivity = self._calculate_sensitivity(results, 'latency_ms', 'total_return')

        return {
            'test_type': 'latency',
            'results': results,
            'sensitivity_score': sensitivity,
            'interpretation': self._interpret_latency_sensitivity(sensitivity)
        }

    def test_historical_crisis(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        역사적 위기 시나리오 테스트

        과거 극심한 변동성 기간에서의 성능 분석

        Args:
            df: 전체 가격 데이터
            params: 전략 파라미터

        Returns:
            Dict with crisis period test results
        """
        # 주요 위기 시나리오
        crisis_periods = [
            {
                'name': 'COVID-19 Crash',
                'start': datetime(2020, 3, 1),
                'end': datetime(2020, 4, 30),
                'description': '2020년 코로나 팬데믹 초기 급락'
            },
            {
                'name': 'FTX Collapse',
                'start': datetime(2022, 11, 1),
                'end': datetime(2022, 12, 31),
                'description': '2022년 FTX 거래소 파산'
            },
            {
                'name': '2021 China Ban',
                'start': datetime(2021, 5, 1),
                'end': datetime(2021, 6, 30),
                'description': '2021년 중국 암호화폐 규제'
            }
        ]

        results = []

        for crisis in crisis_periods:
            # 해당 기간 데이터 추출
            crisis_df = df[
                (df['timestamp'] >= crisis['start']) &
                (df['timestamp'] <= crisis['end'])
            ].copy()

            if len(crisis_df) < 10:
                logger.warning(f"Insufficient data for {crisis['name']}")
                continue

            try:
                metrics = self.backtest_func(crisis_df, params, slippage=0.0, latency_ms=0)

                results.append({
                    'crisis_name': crisis['name'],
                    'description': crisis['description'],
                    'start_date': crisis['start'].isoformat(),
                    'end_date': crisis['end'].isoformat(),
                    'total_return': metrics.get('total_return', 0.0),
                    'max_drawdown': metrics.get('max_drawdown', 0.0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                    'total_trades': metrics.get('total_trades', 0),
                    'survival_score': self._calculate_survival_score(metrics)
                })
            except Exception as e:
                logger.error(f"Crisis test failed for {crisis['name']}: {e}")

        avg_survival = np.mean([r['survival_score'] for r in results]) if results else 0.0

        return {
            'test_type': 'historical_crisis',
            'results': results,
            'avg_survival_score': float(avg_survival),
            'interpretation': self._interpret_crisis_survival(avg_survival)
        }

    def test_extreme_volatility(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any],
        volatility_multipliers: List[float] = [1.0, 1.5, 2.0, 3.0, 5.0]
    ) -> Dict[str, Any]:
        """
        극한 변동성 시뮬레이션

        변동성을 인위적으로 증가시켜 극한 상황 테스트

        Args:
            df: 가격 데이터
            params: 전략 파라미터
            volatility_multipliers: 변동성 배수

        Returns:
            Dict with volatility stress test results
        """
        results = []

        for multiplier in volatility_multipliers:
            # 변동성 증폭
            stressed_df = self._amplify_volatility(df.copy(), multiplier)

            try:
                metrics = self.backtest_func(stressed_df, params, slippage=0.0, latency_ms=0)

                results.append({
                    'volatility_multiplier': multiplier,
                    'total_return': metrics.get('total_return', 0.0),
                    'max_drawdown': metrics.get('max_drawdown', 0.0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                    'total_trades': metrics.get('total_trades', 0),
                    'risk_adjusted_return': metrics.get('total_return', 0.0) / max(abs(metrics.get('max_drawdown', 1.0)), 1.0)
                })
            except Exception as e:
                logger.error(f"Volatility test failed at {multiplier}x: {e}")

        robustness = self._calculate_robustness(results)

        return {
            'test_type': 'extreme_volatility',
            'results': results,
            'robustness_score': robustness,
            'interpretation': self._interpret_volatility_robustness(robustness)
        }

    def run_comprehensive_stress_test(
        self,
        df: pd.DataFrame,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        종합 스트레스 테스트 실행

        모든 스트레스 테스트를 한 번에 실행
        """
        results = {
            'slippage': self.test_slippage(df, params),
            'latency': self.test_latency(df, params),
            'historical_crisis': self.test_historical_crisis(df, params),
            'extreme_volatility': self.test_extreme_volatility(df, params)
        }

        # 종합 점수 계산
        overall_score = self._calculate_overall_stress_score(results)

        return {
            'test_results': results,
            'overall_stress_score': overall_score,
            'recommendation': self._generate_recommendation(overall_score)
        }

    # Helper methods
    def _calculate_sensitivity(
        self,
        results: List[Dict[str, Any]],
        x_key: str,
        y_key: str
    ) -> float:
        """민감도 계산 (성능 변화율)"""
        if len(results) < 2:
            return 0.0

        x_values = [r[x_key] for r in results]
        y_values = [r[y_key] for r in results]

        # 선형 회귀 기울기
        x_range = max(x_values) - min(x_values)
        y_range = max(y_values) - min(y_values)

        if x_range == 0:
            return 0.0

        return abs(y_range / x_range)

    def _calculate_survival_score(self, metrics: Dict[str, float]) -> float:
        """위기 상황 생존 점수 (0-100)"""
        return_score = max(0, min(50, metrics.get('total_return', 0.0) + 50))
        dd_score = max(0, 50 + metrics.get('max_drawdown', -50))
        return float((return_score + dd_score) / 2)

    def _calculate_robustness(self, results: List[Dict[str, Any]]) -> float:
        """변동성 강건성 점수 (0-100)"""
        if not results:
            return 0.0

        # 변동성이 증가해도 성능이 유지되면 높은 점수
        base_return = results[0]['total_return']
        high_vol_return = results[-1]['total_return'] if len(results) > 1 else base_return

        if base_return <= 0:
            return 0.0

        retention_rate = high_vol_return / base_return
        return float(max(0, min(100, retention_rate * 100)))

    def _amplify_volatility(self, df: pd.DataFrame, multiplier: float) -> pd.DataFrame:
        """변동성 증폭"""
        # 수익률 계산
        returns = df['close'].pct_change()

        # 평균 회귀 후 변동성 증폭
        mean_return = returns.mean()
        df['close'] = df['close'].iloc[0] * (1 + ((returns - mean_return) * multiplier + mean_return)).cumprod()

        # OHLC 재조정
        df['high'] = df['close'] * (1 + abs(returns) * multiplier)
        df['low'] = df['close'] * (1 - abs(returns) * multiplier)
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])

        return df

    def _interpret_slippage_sensitivity(self, sensitivity: float) -> str:
        """슬리피지 민감도 해석"""
        if sensitivity < 0.5:
            return "Low sensitivity - strategy robust to slippage"
        elif sensitivity < 2.0:
            return "Moderate sensitivity - monitor execution quality"
        else:
            return "High sensitivity - slippage significantly impacts performance"

    def _interpret_latency_sensitivity(self, sensitivity: float) -> str:
        """레이턴시 민감도 해석"""
        if sensitivity < 0.01:
            return "Low sensitivity - latency not critical"
        elif sensitivity < 0.05:
            return "Moderate sensitivity - optimize execution speed"
        else:
            return "High sensitivity - requires low-latency infrastructure"

    def _interpret_crisis_survival(self, score: float) -> str:
        """위기 생존 점수 해석"""
        if score >= 70:
            return "Excellent crisis resilience"
        elif score >= 50:
            return "Moderate crisis resilience"
        else:
            return "Poor crisis performance - high risk"

    def _interpret_volatility_robustness(self, score: float) -> str:
        """변동성 강건성 해석"""
        if score >= 70:
            return "Highly robust to volatility changes"
        elif score >= 40:
            return "Moderately robust"
        else:
            return "Fragile under high volatility"

    def _calculate_overall_stress_score(self, results: Dict[str, Any]) -> float:
        """종합 스트레스 점수 (0-100)"""
        scores = []

        if 'slippage' in results:
            scores.append(100 - min(100, results['slippage']['sensitivity_score'] * 20))

        if 'latency' in results:
            scores.append(100 - min(100, results['latency']['sensitivity_score'] * 1000))

        if 'historical_crisis' in results:
            scores.append(results['historical_crisis']['avg_survival_score'])

        if 'extreme_volatility' in results:
            scores.append(results['extreme_volatility']['robustness_score'])

        return float(np.mean(scores)) if scores else 0.0

    def _generate_recommendation(self, score: float) -> str:
        """종합 점수에 따른 추천사항"""
        if score >= 75:
            return "✅ Strategy shows excellent resilience under stress. Suitable for production."
        elif score >= 50:
            return "⚠️ Strategy shows moderate resilience. Monitor closely in live trading."
        else:
            return "❌ Strategy shows poor stress performance. Not recommended for production without improvements."
