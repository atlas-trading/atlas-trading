"""
Risk Manager 테스트

리스크 관리 시스템의 핵심 기능을 검증합니다.
"""
import pytest
from datetime import datetime, timedelta

from app.risk.manager import (
    RiskManager,
    RiskLimits,
    RiskLevel,
    RiskViolation
)


class TestRiskLimits:
    """RiskLimits 테스트"""

    def test_default_limits(self):
        """기본 리스크 제한 테스트"""
        limits = RiskLimits()

        assert limits.max_daily_loss_pct == 5.0
        assert limits.max_total_drawdown_pct == 30.0
        assert limits.max_position_size_pct == 25.0
        assert limits.max_trades_per_day == 50
        assert limits.enable_kill_switch == True

    def test_custom_limits(self):
        """커스텀 리스크 제한 테스트"""
        limits = RiskLimits(
            max_daily_loss_pct=3.0,
            max_position_size_pct=10.0,
            max_trades_per_day=20
        )

        assert limits.max_daily_loss_pct == 3.0
        assert limits.max_position_size_pct == 10.0
        assert limits.max_trades_per_day == 20


class TestRiskManager:
    """RiskManager 테스트"""

    def test_initialization(self):
        """Risk Manager 초기화 테스트"""
        manager = RiskManager(initial_capital=10000)

        assert manager.metrics.initial_capital == 10000
        assert manager.metrics.current_equity == 10000
        assert manager.metrics.is_paused == False
        assert manager.metrics.is_killed == False
        assert manager.metrics.risk_level == RiskLevel.LOW

    def test_update_metrics(self):
        """메트릭 업데이트 테스트"""
        manager = RiskManager(initial_capital=10000)

        # 수익 발생
        manager.update_metrics(
            current_equity=11000,
            cash=6000,
            position_value=5000
        )

        assert manager.metrics.current_equity == 11000
        assert manager.metrics.total_pnl == 1000
        assert manager.metrics.total_pnl_pct == 10.0
        assert manager.metrics.total_exposure_pct == pytest.approx(45.45, rel=0.01)

        # Peak 업데이트 확인
        assert manager.metrics.peak_equity == 11000

    def test_drawdown_calculation(self):
        """낙폭 계산 테스트"""
        manager = RiskManager(initial_capital=10000)

        # 수익 발생 (Peak 설정)
        manager.update_metrics(12000, 12000, 0)
        assert manager.metrics.peak_equity == 12000

        # 손실 발생 (Drawdown)
        manager.update_metrics(10000, 10000, 0)

        expected_dd = ((10000 - 12000) / 12000) * 100
        assert manager.metrics.current_drawdown_pct == pytest.approx(expected_dd, rel=0.01)

    def test_validate_signal_normal(self):
        """정상 시그널 검증 테스트"""
        manager = RiskManager(initial_capital=10000)
        manager.update_metrics(10000, 10000, 0)

        signal = {
            'action': 'long',
            'size': 0.2,  # 20% (제한 25% 이내)
            'symbol': 'BTC/USDT'
        }

        result = manager.validate_signal(signal, current_price=50000)

        assert result == True
        assert len(manager.get_violations()) == 0

    def test_validate_signal_daily_loss_limit(self):
        """일일 손실 제한 테스트"""
        limits = RiskLimits(max_daily_loss_pct=5.0)
        manager = RiskManager(initial_capital=10000, limits=limits)

        # 일일 손실 6% 발생
        manager.metrics.daily_pnl = -600
        manager.metrics.daily_pnl_pct = -6.0

        signal = {'action': 'long', 'size': 0.5}
        result = manager.validate_signal(signal, current_price=50000)

        assert result == False
        assert len(manager.get_violations()) > 0
        assert any('Daily Loss Limit' in str(v) for v in manager.get_violations())

    def test_validate_signal_max_drawdown(self):
        """최대 낙폭 제한 테스트"""
        limits = RiskLimits(max_total_drawdown_pct=30.0)
        manager = RiskManager(initial_capital=10000, limits=limits)

        # 35% 낙폭
        manager.metrics.peak_equity = 10000
        manager.metrics.current_equity = 6500
        manager.metrics.current_drawdown_pct = -35.0

        signal = {'action': 'long', 'size': 0.5}
        result = manager.validate_signal(signal, current_price=50000)

        assert result == False
        assert any('Max Drawdown' in str(v) for v in manager.get_violations())

    def test_validate_signal_position_size_limit(self):
        """포지션 크기 제한 테스트"""
        limits = RiskLimits(max_position_size_pct=25.0)
        manager = RiskManager(initial_capital=10000, limits=limits)

        signal = {'action': 'long', 'size': 0.5}  # 50% (제한 초과)
        result = manager.validate_signal(signal, current_price=50000)

        # MEDIUM 위반이므로 경고만 하고 승인됨
        assert result == True
        assert any('Position Size Limit' in str(v) for v in manager.get_violations())

        # 하지만 위반 사항은 기록됨
        assert len(manager.get_violations()) > 0

    def test_validate_signal_trade_frequency_limit(self):
        """거래 빈도 제한 테스트"""
        limits = RiskLimits(max_trades_per_day=10)
        manager = RiskManager(initial_capital=10000, limits=limits)

        # 이미 10개 거래 완료
        manager.metrics.trades_today = 10

        signal = {'action': 'long', 'size': 0.2}
        result = manager.validate_signal(signal, current_price=50000)

        # MEDIUM 위반이므로 경고만 하고 승인됨
        assert result == True
        assert any('Daily Trade Limit' in str(v) for v in manager.get_violations())

    def test_update_after_winning_trade(self):
        """승리 거래 후 업데이트 테스트"""
        manager = RiskManager(initial_capital=10000)

        trade_result = {
            'pnl': 100,
            'pnl_pct': 1.0,
            'side': 'long'
        }

        manager.update_after_trade(trade_result)

        assert manager.metrics.trades_today == 1
        assert manager.metrics.consecutive_wins == 1
        assert manager.metrics.consecutive_losses == 0
        assert manager.metrics.daily_pnl == 100

    def test_update_after_losing_trade(self):
        """손실 거래 후 업데이트 테스트"""
        manager = RiskManager(initial_capital=10000)

        trade_result = {
            'pnl': -50,
            'pnl_pct': -0.5,
            'side': 'long'
        }

        manager.update_after_trade(trade_result)

        assert manager.metrics.trades_today == 1
        assert manager.metrics.consecutive_losses == 1
        assert manager.metrics.consecutive_wins == 0
        assert manager.metrics.daily_pnl == -50

    def test_consecutive_loss_pause(self):
        """연속 손실 후 일시정지 테스트"""
        limits = RiskLimits(
            max_consecutive_losses=3,
            pause_after_consecutive_losses=True
        )
        manager = RiskManager(initial_capital=10000, limits=limits)

        # 3번 연속 손실
        for _ in range(3):
            manager.update_after_trade({'pnl': -10, 'pnl_pct': -0.1, 'side': 'long'})

        assert manager.metrics.consecutive_losses == 3

        # 다음 시그널 거부되어야 함
        signal = {'action': 'long', 'size': 0.2}
        result = manager.validate_signal(signal, current_price=50000)

        assert result == False
        assert manager.metrics.is_paused == True

    def test_kill_switch_activation(self):
        """Kill Switch 활성화 테스트"""
        manager = RiskManager(initial_capital=10000)

        # Kill Switch 활성화
        manager.activate_kill_switch()

        assert manager.metrics.is_killed == True
        assert manager.metrics.risk_level == RiskLevel.CRITICAL

        # 모든 시그널 거부
        signal = {'action': 'long', 'size': 0.2}
        result = manager.validate_signal(signal, current_price=50000)

        assert result == False
        assert any('Kill Switch' in str(v) for v in manager.get_violations())

    def test_kill_switch_auto_trigger(self):
        """Kill Switch 자동 발동 테스트"""
        limits = RiskLimits(
            enable_kill_switch=True,
            kill_switch_loss_pct=10.0
        )
        manager = RiskManager(initial_capital=10000, limits=limits)

        # 11% 손실
        manager.update_metrics(8900, 8900, 0)

        signal = {'action': 'long', 'size': 0.2}
        result = manager.validate_signal(signal, current_price=50000)

        assert result == False
        assert manager.metrics.is_killed == True

    def test_kill_switch_deactivation(self):
        """Kill Switch 해제 테스트"""
        manager = RiskManager(initial_capital=10000)

        manager.activate_kill_switch()
        assert manager.metrics.is_killed == True

        manager.deactivate_kill_switch()
        assert manager.metrics.is_killed == False
        assert manager.metrics.is_paused == False

    def test_pause_and_resume(self):
        """일시정지 및 재개 테스트"""
        manager = RiskManager(initial_capital=10000)

        # 일시정지
        manager.pause_trading()
        assert manager.metrics.is_paused == True

        signal = {'action': 'long', 'size': 0.2}
        assert manager.validate_signal(signal, 50000) == False

        # 재개
        manager.resume_trading()
        assert manager.metrics.is_paused == False
        assert manager.validate_signal(signal, 50000) == True

    def test_close_signal_always_allowed(self):
        """청산 시그널은 항상 허용 테스트"""
        manager = RiskManager(initial_capital=10000)

        # Kill Switch 활성화 상태에서도
        manager.activate_kill_switch()

        # 청산 시그널은 허용
        close_signal = {'action': 'close'}
        result = manager.validate_signal(close_signal, 50000)

        assert result == True

    def test_get_status(self):
        """상태 조회 테스트"""
        manager = RiskManager(initial_capital=10000)
        manager.update_metrics(10500, 10500, 0)

        status = manager.get_status()

        assert 'risk_level' in status
        assert 'current_equity' in status
        assert 'daily_pnl' in status
        assert 'is_paused' in status
        assert 'violations' in status

    def test_reset(self):
        """리셋 테스트"""
        manager = RiskManager(initial_capital=10000)

        # 상태 변경
        manager.update_metrics(11000, 11000, 0)
        manager.update_after_trade({'pnl': 100, 'pnl_pct': 1.0, 'side': 'long'})
        manager.activate_kill_switch()

        # 리셋
        manager.reset()

        assert manager.metrics.current_equity == 10000
        assert manager.metrics.trades_today == 0
        assert manager.metrics.is_killed == False
        assert len(manager.violations) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
