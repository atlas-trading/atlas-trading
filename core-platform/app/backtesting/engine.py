"""Backtesting engine core logic"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Callable
from sqlalchemy.orm import Session

from app.models import BacktestRun, BacktestTrade, BacktestEquity
from app.strategies.base import Strategy, Signal


class Position:
    """포지션 관리"""

    def __init__(self):
        self.side: Optional[str] = None  # 'long' or 'short'
        self.entry_price: float = 0.0
        self.entry_time: Optional[datetime] = None
        self.quantity: float = 0.0
        self.position_size_pct: float = 1.0  # 포지션 크기 비율

    def is_open(self) -> bool:
        return self.side is not None

    def open(self, side: str, price: float, quantity: float, timestamp: datetime, position_size_pct: float = 1.0):
        self.side = side
        self.entry_price = price
        self.quantity = quantity
        self.entry_time = timestamp
        self.position_size_pct = position_size_pct

    def close(self):
        self.side = None
        self.entry_price = 0.0
        self.quantity = 0.0
        self.entry_time = None
        self.position_size_pct = 1.0


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1%
        use_kelly_sizing: bool = True,
        kelly_window: int = 20,
        kelly_fraction: float = 0.5,  # Half Kelly
    ):
        """
        Args:
            initial_capital: 초기 자본금
            commission: 거래 수수료 (비율)
            use_kelly_sizing: 켈리 지수 포지션 사이징 사용 여부
            kelly_window: 켈리 계산에 사용할 최근 거래 수
            kelly_fraction: 켈리 지수 조정 (0.5 = Half Kelly, 1.0 = Full Kelly)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.use_kelly_sizing = use_kelly_sizing
        self.kelly_window = kelly_window
        self.kelly_fraction = kelly_fraction

        # 상태 변수
        self.cash = initial_capital
        self.position = Position()
        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

    def calculate_position_value(self, current_price: float) -> float:
        """현재 포지션 가치 계산"""
        if not self.position.is_open():
            return 0.0
        return self.position.quantity * current_price

    def calculate_equity(self, current_price: float) -> float:
        """총 자산 계산"""
        return self.cash + self.calculate_position_value(current_price)

    def calculate_kelly_fraction(self) -> float:
        """
        켈리 지수 계산 (Kelly Criterion)

        f* = (p*b - q) / b
        - p = 승률
        - q = 패율 (1-p)
        - b = 평균 승리 / 평균 손실

        Returns:
            포지션 크기 비율 (0.0 ~ 1.0)
        """
        if not self.use_kelly_sizing:
            return 1.0  # Full position

        # 최소 거래 수 확인
        if len(self.trades) < 5:
            return 0.25  # 초기에는 보수적으로 25%

        # 최근 거래만 사용
        recent_trades = self.trades[-self.kelly_window:]

        # 승리/손실 분리
        wins = [t for t in recent_trades if t['pnl'] > 0]
        losses = [t for t in recent_trades if t['pnl'] < 0]

        if not wins or not losses:
            return 0.25  # 승리나 손실만 있으면 보수적으로

        # 승률 계산
        p = len(wins) / len(recent_trades)
        q = 1 - p

        # 평균 승리/손실 비율 (백분율 기준)
        avg_win_pct = sum(abs(t['pnl_pct']) for t in wins) / len(wins)
        avg_loss_pct = sum(abs(t['pnl_pct']) for t in losses) / len(losses)
        b = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else 1.0

        # 켈리 지수 계산
        kelly = (p * b - q) / b

        # Kelly fraction 적용 (Half Kelly = 0.5, Quarter Kelly = 0.25)
        kelly = kelly * self.kelly_fraction

        # 안전 범위로 제한 (10% ~ 50%)
        kelly = max(0.1, min(0.5, kelly))

        return kelly

    def execute_long(self, price: float, timestamp: datetime, size_pct: float = 1.0):
        """
        롱 포지션 진입

        Args:
            price: 진입 가격
            timestamp: 진입 시간
            size_pct: 자본금의 몇 %를 사용할지 (0.0 ~ 1.0)
        """
        if self.position.is_open():
            return

        # 사용할 금액 계산
        capital_to_use = self.cash * size_pct
        commission_cost = capital_to_use * self.commission
        quantity = (capital_to_use - commission_cost) / price

        self.position.open("long", price, quantity, timestamp, position_size_pct=size_pct)
        self.cash -= capital_to_use

    def execute_short(self, price: float, timestamp: datetime, size_pct: float = 1.0):
        """
        숏 포지션 진입

        Args:
            price: 진입 가격
            timestamp: 진입 시간
            size_pct: 자본금의 몇 %를 사용할지 (0.0 ~ 1.0)
        """
        if self.position.is_open():
            return

        # 사용할 금액 계산
        capital_to_use = self.cash * size_pct
        commission_cost = capital_to_use * self.commission
        quantity = (capital_to_use - commission_cost) / price

        self.position.open("short", price, quantity, timestamp, position_size_pct=size_pct)
        self.cash -= capital_to_use

    def close_position(self, price: float, timestamp: datetime) -> Optional[Dict[str, Any]]:
        """
        포지션 청산

        Args:
            price: 청산 가격
            timestamp: 청산 시간

        Returns:
            거래 정보 dict
        """
        if not self.position.is_open():
            return None

        # 초기 투자금
        cost = self.position.quantity * self.position.entry_price

        if self.position.side == "long":
            # 롱 포지션 청산
            sell_value = self.position.quantity * price
            commission_cost = sell_value * self.commission
            proceeds = sell_value - commission_cost
            pnl = proceeds - cost

        else:  # short
            # 숏 포지션 청산: 가격이 떨어지면 이익, 오르면 손실
            buy_back_value = self.position.quantity * price
            commission_cost = buy_back_value * self.commission
            # 숏은 진입 가격에 팔고, 청산 가격에 다시 사는 것
            # 진입 시 받은 돈 - 청산 시 다시 사는 비용 - 수수료
            proceeds = cost - buy_back_value - commission_cost
            pnl = proceeds

        pnl_pct = (pnl / cost) * 100

        # 거래 기록
        trade = {
            "entry_time": self.position.entry_time,
            "exit_time": timestamp,
            "side": self.position.side,
            "entry_price": self.position.entry_price,
            "exit_price": price,
            "quantity": self.position.quantity,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "commission_paid": cost * self.commission + commission_cost,
            "position_size_pct": self.position.position_size_pct,
        }

        self.trades.append(trade)

        # 현금 업데이트
        if self.position.side == "long":
            self.cash += proceeds
        else:  # short
            # 숏 청산: 처음 받은 금액에서 다시 사는 비용 차감
            self.cash += cost + pnl - (cost * self.commission)

        # 포지션 닫기
        self.position.close()

        return trade

    def record_equity(self, timestamp: datetime, current_price: float):
        """자산 곡선 기록"""
        equity = self.calculate_equity(current_price)
        position_value = self.calculate_position_value(current_price)

        self.equity_curve.append(
            {
                "timestamp": timestamp,
                "equity": equity,
                "cash": self.cash,
                "position_value": position_value,
            }
        )

    def run(
        self,
        df: pd.DataFrame,
        strategy: Union[Strategy, Callable],
        strategy_name: Optional[str] = None,
        symbol: str = "",
        timeframe: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        백테스팅 실행

        Args:
            df: OHLCV 데이터
            strategy: Strategy 객체 또는 전략 함수 (하위 호환)
            strategy_name: 전략 이름 (Strategy 객체 사용 시 자동)
            symbol: 거래쌍
            timeframe: 타임프레임
            parameters: 전략 파라미터 (Strategy 객체 사용 시 자동)

        Returns:
            백테스팅 결과 dict
        """
        # Strategy 객체인지 함수인지 확인
        is_strategy_object = isinstance(strategy, Strategy)

        if is_strategy_object:
            # Strategy 객체 사용
            strategy_name = strategy_name or strategy.get_name()
            parameters = parameters or strategy.get_parameters()

            # 데이터 전처리 (지표 추가)
            df = strategy.prepare_data(df.copy())

            # 전략 상태 초기화
            strategy.reset()

        # 초기화
        self.cash = self.initial_capital
        self.position = Position()
        self.trades = []
        self.equity_curve = []

        # 각 캔들에 대해 전략 실행
        for idx, row in df.iterrows():
            timestamp = row["timestamp"]
            price = row["close"]

            # 전략 시그널
            if is_strategy_object:
                signal = strategy.on_bar(row)
                strategy.on_bar_update()
            else:
                # 하위 호환: 함수 호출
                signal = strategy(row)

            # Signal 객체를 문자열로 변환 (하위 호환)
            signal_action = signal
            signal_size = 1.0
            if isinstance(signal, Signal):
                signal_action = signal.action
                signal_size = signal.size if signal.size else 1.0

            # 시그널 실행
            if signal_action == "long" and not self.position.is_open():
                # 켈리 지수 계산 또는 Signal에서 지정된 크기 사용
                if isinstance(signal, Signal) and signal.size:
                    # Signal 객체에서 size 사용
                    kelly_size = signal.size
                else:
                    # Kelly Criterion으로 계산
                    kelly_size = self.calculate_kelly_fraction()

                self.execute_long(price, timestamp, size_pct=kelly_size)
                if is_strategy_object:
                    strategy.on_position_opened('long', price, timestamp)

            elif signal_action == "short" and not self.position.is_open():
                # 향후 숏 포지션 지원
                if isinstance(signal, Signal) and signal.size:
                    kelly_size = signal.size
                else:
                    kelly_size = self.calculate_kelly_fraction()
                self.execute_short(price, timestamp, size_pct=kelly_size)
                if is_strategy_object:
                    strategy.on_position_opened('short', price, timestamp)

            elif signal_action == "close" and self.position.is_open():
                trade = self.close_position(price, timestamp)
                if is_strategy_object and trade:
                    strategy.on_position_closed(trade['pnl'], trade['pnl_pct'], timestamp)

            # 자산 기록
            self.record_equity(timestamp, price)

        # 마지막에 포지션이 열려있으면 청산
        if self.position.is_open():
            last_row = df.iloc[-1]
            self.close_position(last_row["close"], last_row["timestamp"])
            if is_strategy_object:
                pnl = self.trades[-1]["pnl"] if self.trades else 0
                pnl_pct = self.trades[-1]["pnl_pct"] if self.trades else 0
                strategy.on_position_closed(pnl, pnl_pct, last_row["timestamp"])

        # 성과 지표 계산
        results = self.calculate_metrics(df, strategy_name, symbol, timeframe, parameters)

        return results

    def calculate_metrics(
        self,
        df: pd.DataFrame,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        parameters: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """성과 지표 계산"""
        if not self.equity_curve:
            return {}

        equity_df = pd.DataFrame(self.equity_curve)
        final_equity = equity_df["equity"].iloc[-1]

        # 기본 지표
        total_return = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        total_trades = len(self.trades)

        if total_trades > 0:
            winning_trades = len([t for t in self.trades if t["pnl"] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades) * 100
        else:
            winning_trades = 0
            losing_trades = 0
            win_rate = 0.0

        # Maximum Drawdown
        equity_df["peak"] = equity_df["equity"].cummax()
        equity_df["drawdown"] = (
            (equity_df["equity"] - equity_df["peak"]) / equity_df["peak"]
        ) * 100
        max_drawdown = equity_df["drawdown"].min()

        # Sharpe Ratio (간단 계산)
        equity_df["returns"] = equity_df["equity"].pct_change()
        if len(equity_df) > 1 and equity_df["returns"].std() > 0:
            # 타임프레임별 연율화 계산
            annualization_factors = {
                '1m': np.sqrt(252 * 390),      # 252 trading days * 390 minutes per day
                '5m': np.sqrt(252 * 78),       # 252 * (390/5)
                '15m': np.sqrt(252 * 26),      # 252 * (390/15)
                '1h': np.sqrt(252 * 6.5),      # 252 * 6.5 trading hours
                '4h': np.sqrt(252 * 1.625),    # 252 * (6.5/4)
                '1d': np.sqrt(252),
            }
            annualization_factor = annualization_factors.get(timeframe, np.sqrt(252))

            sharpe_ratio = (
                equity_df["returns"].mean() / equity_df["returns"].std()
            ) * annualization_factor
        else:
            sharpe_ratio = 0.0

        return {
            "strategy_name": strategy_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": df["timestamp"].iloc[0],
            "end_date": df["timestamp"].iloc[-1],
            "initial_capital": self.initial_capital,
            "final_capital": final_equity,
            "commission": self.commission,
            "total_return": total_return,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "parameters": parameters,
            "trades": self.trades,
            "equity_curve": self.equity_curve,
        }

    def save_to_db(self, db: Session, results: Dict[str, Any]) -> BacktestRun:
        """
        백테스팅 결과를 데이터베이스에 저장

        Args:
            db: SQLAlchemy 세션
            results: calculate_metrics()의 결과

        Returns:
            저장된 BacktestRun 객체
        """
        import json

        # BacktestRun 생성
        backtest_run = BacktestRun(
            strategy_name=results["strategy_name"],
            symbol=results["symbol"],
            timeframe=results["timeframe"],
            start_date=results["start_date"],
            end_date=results["end_date"],
            initial_capital=results["initial_capital"],
            commission=results["commission"],
            final_capital=results["final_capital"],
            total_return=results["total_return"],
            total_trades=results["total_trades"],
            winning_trades=results["winning_trades"],
            losing_trades=results["losing_trades"],
            win_rate=results["win_rate"],
            max_drawdown=results["max_drawdown"],
            sharpe_ratio=results["sharpe_ratio"],
            parameters=json.dumps(results.get("parameters")),
        )

        db.add(backtest_run)
        db.flush()  # ID 생성

        # Trades 저장
        for trade in results["trades"]:
            backtest_trade = BacktestTrade(
                backtest_run_id=backtest_run.id,
                entry_time=trade["entry_time"],
                exit_time=trade["exit_time"],
                side=trade["side"],
                entry_price=trade["entry_price"],
                exit_price=trade["exit_price"],
                quantity=trade["quantity"],
                pnl=trade["pnl"],
                pnl_pct=trade["pnl_pct"],
                commission_paid=trade["commission_paid"],
                position_size_pct=trade.get("position_size_pct", 1.0),
            )
            db.add(backtest_trade)

        # Equity Curve 저장
        for equity in results["equity_curve"]:
            backtest_equity = BacktestEquity(
                backtest_run_id=backtest_run.id,
                timestamp=equity["timestamp"],
                equity=equity["equity"],
                cash=equity["cash"],
                position_value=equity["position_value"],
            )
            db.add(backtest_equity)

        db.commit()
        db.refresh(backtest_run)

        return backtest_run
