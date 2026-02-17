"""백테스트 결과를 데이터베이스에 저장하는 유틸리티"""
import json
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity


def save_backtest_to_db(
    strategy_name: str,
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    initial_capital: float,
    commission: float,
    result: Dict[str, Any],
    parameters: Dict[str, Any] = None,
) -> int:
    """
    백테스트 결과를 데이터베이스에 저장

    Args:
        strategy_name: 전략 이름
        symbol: 심볼
        timeframe: 타임프레임
        start_date: 시작 날짜
        end_date: 종료 날짜
        initial_capital: 초기 자본
        commission: 수수료
        result: 백테스트 결과 (BacktestEngine.run() 반환값)
        parameters: 전략 파라미터 (선택)

    Returns:
        생성된 백테스트 실행 ID
    """
    db = SessionLocal()
    try:
        # BacktestRun 생성
        backtest_run = BacktestRun(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            commission=commission,
            final_capital=result.get('final_capital'),
            total_return=result.get('total_return'),
            total_trades=result.get('total_trades', 0),
            winning_trades=result.get('winning_trades', 0),
            losing_trades=result.get('losing_trades', 0),
            win_rate=result.get('win_rate', 0),
            max_drawdown=result.get('max_drawdown'),
            sharpe_ratio=result.get('sharpe_ratio'),
            parameters=json.dumps(parameters) if parameters else None,
        )

        db.add(backtest_run)
        db.flush()  # ID 생성

        # BacktestTrade 생성
        trades = result.get('trades', [])
        if trades and len(trades) > 0:
            for trade in trades:
                backtest_trade = BacktestTrade(
                    backtest_run_id=backtest_run.id,
                    entry_time=trade.get('entry_time'),
                    exit_time=trade.get('exit_time'),
                    side=trade.get('side', 'long'),
                    entry_price=trade.get('entry_price'),
                    exit_price=trade.get('exit_price'),
                    quantity=trade.get('quantity', 0),
                    pnl=trade.get('pnl'),
                    pnl_pct=trade.get('pnl_pct'),
                    commission_paid=trade.get('commission_paid', 0),
                    position_size_pct=trade.get('position_size_pct', 1.0),
                )
                db.add(backtest_trade)

        # BacktestEquity 생성
        equity_curve = result.get('equity_curve', [])
        if equity_curve and len(equity_curve) > 0:
            for equity_point in equity_curve:
                backtest_equity = BacktestEquity(
                    backtest_run_id=backtest_run.id,
                    timestamp=equity_point.get('timestamp'),
                    equity=equity_point.get('equity'),
                    cash=equity_point.get('cash', equity_point.get('equity')),
                    position_value=equity_point.get('position_value', 0),
                )
                db.add(backtest_equity)

        db.commit()
        return backtest_run.id

    except Exception as e:
        db.rollback()
        print(f"❌ DB 저장 실패: {e}")
        raise
    finally:
        db.close()


def save_multiple_backtests(
    backtests: List[Dict[str, Any]]
) -> List[int]:
    """
    여러 백테스트 결과를 한 번에 저장

    Args:
        backtests: 백테스트 정보 딕셔너리 리스트
            각 딕셔너리는 save_backtest_to_db의 모든 인자를 포함해야 함

    Returns:
        생성된 백테스트 실행 ID 리스트
    """
    ids = []
    for bt in backtests:
        try:
            bt_id = save_backtest_to_db(
                strategy_name=bt['strategy_name'],
                symbol=bt['symbol'],
                timeframe=bt['timeframe'],
                start_date=bt['start_date'],
                end_date=bt['end_date'],
                initial_capital=bt['initial_capital'],
                commission=bt['commission'],
                result=bt['result'],
                parameters=bt.get('parameters'),
            )
            ids.append(bt_id)
            print(f"✅ {bt['strategy_name']} - {bt['symbol']} DB 저장 완료 (ID: {bt_id})")
        except Exception as e:
            print(f"❌ {bt['strategy_name']} - {bt['symbol']} DB 저장 실패: {e}")
            continue

    return ids
