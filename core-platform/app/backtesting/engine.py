"""Backtesting engine core logic"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models import BacktestRun, BacktestTrade, BacktestEquity


class Position:
    """포지션 관리"""

    def __init__(self):
        self.side: Optional[str] = None  # 'long' or 'short'
        self.entry_price: float = 0.0
        self.entry_time: Optional[datetime] = None
        self.quantity: float = 0.0

    def is_open(self) -> bool:
        return self.side is not None

    def open(self, side: str, price: float, quantity: float, timestamp: datetime):
        self.side = side
        self.entry_price = price
        self.quantity = quantity
        self.entry_time = timestamp

    def close(self):
        self.side = None
        self.entry_price = 0.0
        self.quantity = 0.0
        self.entry_time = None


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,  # 0.1%
    ):
        """
        Args:
            initial_capital: 초기 자본금
            commission: 거래 수수료 (비율)
        """
        self.initial_capital = initial_capital
        self.commission = commission

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

        self.position.open("long", price, quantity, timestamp)
        self.cash -= capital_to_use

    def execute_short(self, price: float, timestamp: datetime, size_pct: float = 1.0):
        """
        숏 포지션 진입 (현재는 단순화를 위해 미구현)

        실제 구현시에는 마진, 펀딩 비용 등을 고려해야 함
        """
        pass

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

        # 매도 금액 계산
        sell_value = self.position.quantity * price
        commission_cost = sell_value * self.commission
        proceeds = sell_value - commission_cost

        # 손익 계산
        cost = self.position.quantity * self.position.entry_price
        pnl = proceeds - cost
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
        }

        self.trades.append(trade)

        # 현금 업데이트
        self.cash += proceeds

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
        strategy_func,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        백테스팅 실행

        Args:
            df: OHLCV 데이터 (지표 포함)
            strategy_func: 전략 함수 (row를 받아서 'long', 'close', None 반환)
            strategy_name: 전략 이름
            symbol: 거래쌍
            timeframe: 타임프레임
            parameters: 전략 파라미터

        Returns:
            백테스팅 결과 dict
        """
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
            signal = strategy_func(row)

            # 시그널 실행
            if signal == "long" and not self.position.is_open():
                self.execute_long(price, timestamp)
            elif signal == "close" and self.position.is_open():
                self.close_position(price, timestamp)

            # 자산 기록
            self.record_equity(timestamp, price)

        # 마지막에 포지션이 열려있으면 청산
        if self.position.is_open():
            last_row = df.iloc[-1]
            self.close_position(last_row["close"], last_row["timestamp"])

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
            sharpe_ratio = (
                equity_df["returns"].mean() / equity_df["returns"].std()
            ) * np.sqrt(252)  # 연율화
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
