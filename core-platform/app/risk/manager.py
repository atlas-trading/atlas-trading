"""
Risk Manager - 실거래 안전장치

리스크 관리 시스템으로 다음을 제한합니다:
- 일일 최대 손실 (Daily Loss Limit)
- 최대 낙폭 (Max Drawdown)
- 단일 포지션 크기 (Position Size Limit)
- 일일 거래 횟수 (Trade Frequency Limit)
- 긴급 정지 (Kill Switch)
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """리스크 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimits:
    """리스크 제한 설정"""

    # 손실 제한
    max_daily_loss_pct: float = 5.0  # 일일 최대 손실 (%)
    max_total_drawdown_pct: float = 30.0  # 최대 낙폭 (%)

    # 포지션 제한
    max_position_size_pct: float = 25.0  # 단일 포지션 최대 크기 (%)
    max_total_exposure_pct: float = 80.0  # 전체 노출도 (%)

    # 거래 빈도 제한
    max_trades_per_day: int = 50  # 일일 최대 거래 횟수
    max_trades_per_hour: int = 10  # 시간당 최대 거래 횟수

    # 연속 손실 제한
    max_consecutive_losses: int = 5  # 연속 손실 최대 횟수
    pause_after_consecutive_losses: bool = True  # 연속 손실 후 일시정지

    # 변동성 제한
    max_volatility_threshold: float = 10.0  # 최대 허용 변동성 (%)

    # 긴급 정지
    enable_kill_switch: bool = True  # Kill Switch 활성화
    kill_switch_loss_pct: float = 10.0  # Kill Switch 발동 손실 (%)


@dataclass
class RiskMetrics:
    """현재 리스크 지표"""

    # 계좌 정보
    initial_capital: float = 10000.0
    current_equity: float = 10000.0
    cash: float = 10000.0
    position_value: float = 0.0

    # 손익
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_pnl_pct: float = 0.0

    # 낙폭
    peak_equity: float = 10000.0
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0

    # 거래 통계
    trades_today: int = 0
    trades_this_hour: int = 0
    consecutive_losses: int = 0
    consecutive_wins: int = 0

    # 포지션 노출
    total_exposure_pct: float = 0.0

    # 상태
    last_trade_time: Optional[datetime] = None
    daily_reset_time: Optional[datetime] = None
    is_paused: bool = False
    is_killed: bool = False

    # 리스크 수준
    risk_level: RiskLevel = RiskLevel.LOW


@dataclass
class RiskViolation:
    """리스크 위반 사항"""

    rule: str  # 위반된 규칙
    severity: RiskLevel  # 심각도
    message: str  # 상세 메시지
    current_value: float  # 현재 값
    limit_value: float  # 제한 값
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"[{self.severity.value.upper()}] {self.rule}: {self.message} (현재: {self.current_value:.2f}, 제한: {self.limit_value:.2f})"


class RiskManager:
    """
    리스크 관리자

    실거래 전에 모든 시그널/주문을 검증하고 리스크 제한을 적용합니다.

    Usage:
        risk_manager = RiskManager(
            initial_capital=10000,
            limits=RiskLimits(max_daily_loss_pct=5.0)
        )

        # 시그널 검증
        if risk_manager.validate_signal(signal):
            execute_order(signal)
        else:
            logger.warning(f"Signal rejected: {risk_manager.get_violations()}")

        # 거래 후 업데이트
        risk_manager.update_after_trade(trade_result)
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        limits: Optional[RiskLimits] = None
    ):
        """
        Args:
            initial_capital: 초기 자본금
            limits: 리스크 제한 설정 (None이면 기본값 사용)
        """
        self.limits = limits or RiskLimits()

        self.metrics = RiskMetrics(
            initial_capital=initial_capital,
            current_equity=initial_capital,
            cash=initial_capital,
            peak_equity=initial_capital,
            daily_reset_time=self._get_next_reset_time()
        )

        self.violations: List[RiskViolation] = []
        self.trade_history_today: List[Dict[str, Any]] = []

    def _get_next_reset_time(self) -> datetime:
        """다음 일일 리셋 시간 계산 (자정)"""
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)

    def _check_daily_reset(self):
        """일일 리셋 확인 및 실행"""
        if datetime.now() >= self.metrics.daily_reset_time:
            logger.info("Daily reset - resetting daily metrics")

            # 일일 지표 초기화
            self.metrics.daily_pnl = 0.0
            self.metrics.daily_pnl_pct = 0.0
            self.metrics.trades_today = 0
            self.trade_history_today = []
            self.metrics.daily_reset_time = self._get_next_reset_time()

            # 일시정지 해제 (kill switch는 수동 해제)
            if self.metrics.is_paused and not self.metrics.is_killed:
                self.metrics.is_paused = False
                logger.info("Auto-resume after daily reset")

    def update_metrics(
        self,
        current_equity: float,
        cash: float,
        position_value: float
    ):
        """
        현재 메트릭 업데이트

        Args:
            current_equity: 현재 총 자산
            cash: 현금
            position_value: 포지션 가치
        """
        self._check_daily_reset()

        # 자산 업데이트
        self.metrics.current_equity = current_equity
        self.metrics.cash = cash
        self.metrics.position_value = position_value

        # 손익 계산
        self.metrics.total_pnl = current_equity - self.metrics.initial_capital
        self.metrics.total_pnl_pct = (self.metrics.total_pnl / self.metrics.initial_capital) * 100

        # 일일 손익 (오늘 시작 자산 기준)
        # TODO: daily_start_equity를 추적해야 정확함

        # 낙폭 계산
        if current_equity > self.metrics.peak_equity:
            self.metrics.peak_equity = current_equity

        self.metrics.current_drawdown_pct = (
            (self.metrics.current_equity - self.metrics.peak_equity) / self.metrics.peak_equity
        ) * 100

        if self.metrics.current_drawdown_pct < self.metrics.max_drawdown_pct:
            self.metrics.max_drawdown_pct = self.metrics.current_drawdown_pct

        # 노출도 계산
        self.metrics.total_exposure_pct = (position_value / current_equity) * 100

        # 리스크 수준 재계산
        self._update_risk_level()

    def _update_risk_level(self):
        """리스크 수준 업데이트"""
        if self.metrics.is_killed:
            self.metrics.risk_level = RiskLevel.CRITICAL
        elif abs(self.metrics.current_drawdown_pct) > self.limits.max_total_drawdown_pct * 0.8:
            self.metrics.risk_level = RiskLevel.HIGH
        elif abs(self.metrics.daily_pnl_pct) > self.limits.max_daily_loss_pct * 0.7:
            self.metrics.risk_level = RiskLevel.HIGH
        elif self.metrics.consecutive_losses >= self.limits.max_consecutive_losses - 1:
            self.metrics.risk_level = RiskLevel.MEDIUM
        else:
            self.metrics.risk_level = RiskLevel.LOW

    def validate_signal(
        self,
        signal: Dict[str, Any],
        current_price: float
    ) -> bool:
        """
        시그널 검증

        Args:
            signal: 전략 시그널 (action, size 등)
            current_price: 현재 가격

        Returns:
            True: 시그널 승인
            False: 시그널 거부
        """
        self.violations = []  # 이전 위반 기록 초기화

        # 진입 시그널만 검증 (청산은 항상 허용)
        if signal.get('action') not in ['long', 'short']:
            return True

        # Kill Switch 확인
        if self.metrics.is_killed:
            self.violations.append(RiskViolation(
                rule="Kill Switch",
                severity=RiskLevel.CRITICAL,
                message="Kill switch activated - all trading stopped",
                current_value=abs(self.metrics.total_pnl_pct),
                limit_value=self.limits.kill_switch_loss_pct
            ))
            return False

        # 일시정지 확인
        if self.metrics.is_paused:
            self.violations.append(RiskViolation(
                rule="Trading Paused",
                severity=RiskLevel.HIGH,
                message="Trading is paused due to risk limits",
                current_value=0,
                limit_value=0
            ))
            return False

        # 1. 일일 손실 제한
        if abs(self.metrics.daily_pnl_pct) >= self.limits.max_daily_loss_pct:
            self.violations.append(RiskViolation(
                rule="Daily Loss Limit",
                severity=RiskLevel.HIGH,
                message="Daily loss limit reached",
                current_value=abs(self.metrics.daily_pnl_pct),
                limit_value=self.limits.max_daily_loss_pct
            ))

        # 2. 최대 낙폭 제한
        if abs(self.metrics.current_drawdown_pct) >= self.limits.max_total_drawdown_pct:
            self.violations.append(RiskViolation(
                rule="Max Drawdown",
                severity=RiskLevel.CRITICAL,
                message="Maximum drawdown reached",
                current_value=abs(self.metrics.current_drawdown_pct),
                limit_value=self.limits.max_total_drawdown_pct
            ))

        # 3. 포지션 크기 제한
        position_size_pct = signal.get('size', 1.0) * 100
        if position_size_pct > self.limits.max_position_size_pct:
            self.violations.append(RiskViolation(
                rule="Position Size Limit",
                severity=RiskLevel.MEDIUM,
                message="Position size exceeds limit",
                current_value=position_size_pct,
                limit_value=self.limits.max_position_size_pct
            ))

        # 4. 전체 노출도 제한
        new_exposure = self.metrics.total_exposure_pct + position_size_pct
        if new_exposure > self.limits.max_total_exposure_pct:
            self.violations.append(RiskViolation(
                rule="Total Exposure Limit",
                severity=RiskLevel.MEDIUM,
                message="Total exposure would exceed limit",
                current_value=new_exposure,
                limit_value=self.limits.max_total_exposure_pct
            ))

        # 5. 거래 빈도 제한
        if self.metrics.trades_today >= self.limits.max_trades_per_day:
            self.violations.append(RiskViolation(
                rule="Daily Trade Limit",
                severity=RiskLevel.MEDIUM,
                message="Daily trade limit reached",
                current_value=self.metrics.trades_today,
                limit_value=self.limits.max_trades_per_day
            ))

        if self.metrics.trades_this_hour >= self.limits.max_trades_per_hour:
            self.violations.append(RiskViolation(
                rule="Hourly Trade Limit",
                severity=RiskLevel.LOW,
                message="Hourly trade limit reached",
                current_value=self.metrics.trades_this_hour,
                limit_value=self.limits.max_trades_per_hour
            ))

        # 6. 연속 손실 제한
        if (self.metrics.consecutive_losses >= self.limits.max_consecutive_losses and
            self.limits.pause_after_consecutive_losses):
            self.violations.append(RiskViolation(
                rule="Consecutive Loss Limit",
                severity=RiskLevel.HIGH,
                message="Too many consecutive losses - pausing trading",
                current_value=self.metrics.consecutive_losses,
                limit_value=self.limits.max_consecutive_losses
            ))
            self.metrics.is_paused = True

        # Kill Switch 자동 발동
        if (self.limits.enable_kill_switch and
            abs(self.metrics.total_pnl_pct) >= self.limits.kill_switch_loss_pct):
            self.violations.append(RiskViolation(
                rule="Kill Switch Auto-Trigger",
                severity=RiskLevel.CRITICAL,
                message="Kill switch auto-triggered due to large loss",
                current_value=abs(self.metrics.total_pnl_pct),
                limit_value=self.limits.kill_switch_loss_pct
            ))
            self.activate_kill_switch()

        # 위반 사항 로깅
        for violation in self.violations:
            logger.warning(str(violation))

        # 중요/치명적 위반이 있으면 거부
        critical_violations = [v for v in self.violations if v.severity in [RiskLevel.HIGH, RiskLevel.CRITICAL]]

        return len(critical_violations) == 0

    def update_after_trade(
        self,
        trade_result: Dict[str, Any]
    ):
        """
        거래 후 메트릭 업데이트

        Args:
            trade_result: 거래 결과 (pnl, pnl_pct, side 등)
        """
        self._check_daily_reset()

        # 거래 기록
        self.trade_history_today.append({
            'timestamp': datetime.now(),
            'pnl': trade_result.get('pnl', 0),
            'pnl_pct': trade_result.get('pnl_pct', 0),
            'side': trade_result.get('side')
        })

        # 카운터 업데이트
        self.metrics.trades_today += 1
        self.metrics.trades_this_hour += 1  # TODO: 시간당 리셋 로직 추가
        self.metrics.last_trade_time = datetime.now()

        # 연속 승/패 업데이트
        pnl = trade_result.get('pnl', 0)
        if pnl > 0:
            self.metrics.consecutive_wins += 1
            self.metrics.consecutive_losses = 0
        elif pnl < 0:
            self.metrics.consecutive_losses += 1
            self.metrics.consecutive_wins = 0

        # 일일 PnL 업데이트
        self.metrics.daily_pnl += pnl
        # daily_pnl_pct는 오늘 시작 equity 기준으로 계산해야 정확
        # 여기서는 간단히 current_equity 기준
        self.metrics.daily_pnl_pct = (self.metrics.daily_pnl / self.metrics.current_equity) * 100

        logger.info(f"Trade recorded: PnL={pnl:.2f}, Daily PnL={self.metrics.daily_pnl:.2f}, "
                   f"Consecutive losses={self.metrics.consecutive_losses}")

    def activate_kill_switch(self):
        """긴급 정지 활성화 (수동 해제 필요)"""
        self.metrics.is_killed = True
        self.metrics.risk_level = RiskLevel.CRITICAL
        logger.critical("🛑 KILL SWITCH ACTIVATED - All trading stopped")

    def deactivate_kill_switch(self):
        """긴급 정지 해제 (수동)"""
        self.metrics.is_killed = False
        self.metrics.is_paused = False
        self.metrics.risk_level = RiskLevel.LOW
        logger.info("Kill switch deactivated - trading resumed")

    def pause_trading(self):
        """거래 일시정지"""
        self.metrics.is_paused = True
        logger.warning("Trading paused")

    def resume_trading(self):
        """거래 재개"""
        if not self.metrics.is_killed:
            self.metrics.is_paused = False
            logger.info("Trading resumed")

    def get_violations(self) -> List[RiskViolation]:
        """현재 리스크 위반 목록 반환"""
        return self.violations

    def get_status(self) -> Dict[str, Any]:
        """현재 리스크 상태 반환"""
        return {
            'risk_level': self.metrics.risk_level.value,
            'is_paused': self.metrics.is_paused,
            'is_killed': self.metrics.is_killed,
            'current_equity': self.metrics.current_equity,
            'daily_pnl': self.metrics.daily_pnl,
            'daily_pnl_pct': self.metrics.daily_pnl_pct,
            'current_drawdown_pct': self.metrics.current_drawdown_pct,
            'max_drawdown_pct': self.metrics.max_drawdown_pct,
            'trades_today': self.metrics.trades_today,
            'consecutive_losses': self.metrics.consecutive_losses,
            'total_exposure_pct': self.metrics.total_exposure_pct,
            'violations': [str(v) for v in self.violations]
        }

    def get_metrics(self) -> RiskMetrics:
        """현재 리스크 메트릭 반환"""
        return self.metrics

    def reset(self):
        """리스크 매니저 초기화"""
        self.metrics = RiskMetrics(
            initial_capital=self.metrics.initial_capital,
            current_equity=self.metrics.initial_capital,
            cash=self.metrics.initial_capital,
            peak_equity=self.metrics.initial_capital,
            daily_reset_time=self._get_next_reset_time()
        )
        self.violations = []
        self.trade_history_today = []
        logger.info("Risk manager reset")
