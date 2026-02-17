"""Backtest API Endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.models.backtest import BacktestRun, BacktestTrade, BacktestEquity
from app.core.database import get_db
from app.schemas.backtest import (
    BacktestRunSummaryResponse,
    BacktestRunDetailResponse,
    BacktestRunFullResponse,
    TradeResponse,
    EquityPointResponse,
    StatsResponse,
    AdvancedMetricsResponse,
    TradeAnalysisResponse,
    MonteCarloResponse,
    CostStressResponse,
)

router = APIRouter()


def _orm_to_summary(obj: BacktestRun) -> BacktestRunSummaryResponse:
    """ORM 객체를 Summary dataclass로 변환"""
    return BacktestRunSummaryResponse(
        id=obj.id,
        strategy_name=obj.strategy_name,
        symbol=obj.symbol,
        timeframe=obj.timeframe,
        start_date=obj.start_date,
        end_date=obj.end_date,
        initial_capital=obj.initial_capital,
        commission=obj.commission,
        final_capital=obj.final_capital,
        total_return=obj.total_return,
        total_trades=obj.total_trades,
        win_rate=obj.win_rate,
        max_drawdown=obj.max_drawdown,
        sharpe_ratio=obj.sharpe_ratio,
        created_at=obj.created_at,
    )


def _orm_to_detail(obj: BacktestRun) -> BacktestRunDetailResponse:
    """ORM 객체를 Detail dataclass로 변환"""
    return BacktestRunDetailResponse(
        id=obj.id,
        strategy_name=obj.strategy_name,
        symbol=obj.symbol,
        timeframe=obj.timeframe,
        start_date=obj.start_date,
        end_date=obj.end_date,
        initial_capital=obj.initial_capital,
        commission=obj.commission,
        final_capital=obj.final_capital,
        total_return=obj.total_return,
        total_trades=obj.total_trades,
        winning_trades=obj.winning_trades,
        losing_trades=obj.losing_trades,
        win_rate=obj.win_rate,
        max_drawdown=obj.max_drawdown,
        sharpe_ratio=obj.sharpe_ratio,
        parameters=obj.parameters,
        created_at=obj.created_at,
    )


def _trade_to_response(obj: BacktestTrade) -> TradeResponse:
    """Trade ORM 객체를 dataclass로 변환"""
    return TradeResponse(
        id=obj.id,
        backtest_run_id=obj.backtest_run_id,
        entry_time=obj.entry_time,
        exit_time=obj.exit_time,
        side=obj.side,
        entry_price=obj.entry_price,
        exit_price=obj.exit_price,
        quantity=obj.quantity,
        pnl=obj.pnl,
        pnl_pct=obj.pnl_pct,
        commission_paid=obj.commission_paid,
    )


def _equity_to_response(obj: BacktestEquity) -> EquityPointResponse:
    """Equity ORM 객체를 dataclass로 변환"""
    return EquityPointResponse(
        timestamp=obj.timestamp,
        equity=obj.equity,
        cash=obj.cash,
        position_value=obj.position_value,
    )


@router.get("/", response_model=list[BacktestRunSummaryResponse])
def list_backtests(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    strategy_name: str | None = None,
    symbol: str | None = None,
    db: Session = Depends(get_db),
) -> list[BacktestRunSummaryResponse]:
    """
    백테스트 실행 목록 조회

    Parameters:
    - skip: 건너뛸 개수 (페이지네이션)
    - limit: 조회할 최대 개수
    - strategy_name: 전략 이름 필터
    - symbol: 심볼 필터
    """
    query = db.query(BacktestRun)

    if strategy_name:
        query = query.filter(BacktestRun.strategy_name == strategy_name)
    if symbol:
        query = query.filter(BacktestRun.symbol == symbol)

    query = query.order_by(BacktestRun.created_at.desc())
    backtests = query.offset(skip).limit(limit).all()

    return [_orm_to_summary(bt) for bt in backtests]


@router.get("/{backtest_id}", response_model=BacktestRunDetailResponse)
def get_backtest(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> BacktestRunDetailResponse:
    """백테스트 실행 상세 조회 (거래 및 자산 곡선 제외)"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    return _orm_to_detail(backtest)


@router.get("/{backtest_id}/full", response_model=BacktestRunFullResponse)
def get_backtest_full(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> BacktestRunFullResponse:
    """백테스트 실행 전체 조회 (거래 + 자산 곡선 포함)"""
    backtest = (
        db.query(BacktestRun)
        .options(
            joinedload(BacktestRun.trades),
            joinedload(BacktestRun.equity_curve),
        )
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    trades = [_trade_to_response(t) for t in backtest.trades]
    equity_curve = [_equity_to_response(e) for e in backtest.equity_curve]

    return BacktestRunFullResponse(
        id=backtest.id,
        strategy_name=backtest.strategy_name,
        symbol=backtest.symbol,
        timeframe=backtest.timeframe,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        initial_capital=backtest.initial_capital,
        commission=backtest.commission,
        final_capital=backtest.final_capital,
        total_return=backtest.total_return,
        total_trades=backtest.total_trades,
        winning_trades=backtest.winning_trades,
        losing_trades=backtest.losing_trades,
        win_rate=backtest.win_rate,
        max_drawdown=backtest.max_drawdown,
        sharpe_ratio=backtest.sharpe_ratio,
        parameters=backtest.parameters,
        created_at=backtest.created_at,
        trades=trades,
        equity_curve=equity_curve,
    )


@router.get("/{backtest_id}/trades", response_model=list[TradeResponse])
def get_backtest_trades(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> list[TradeResponse]:
    """백테스트 거래 내역 조회"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    trades = (
        db.query(BacktestTrade)
        .filter(BacktestTrade.backtest_run_id == backtest_id)
        .order_by(BacktestTrade.entry_time)
        .all()
    )

    return [_trade_to_response(t) for t in trades]


@router.get("/{backtest_id}/equity", response_model=list[EquityPointResponse])
def get_backtest_equity(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> list[EquityPointResponse]:
    """백테스트 자산 곡선 조회"""
    backtest = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    equity_curve = (
        db.query(BacktestEquity)
        .filter(BacktestEquity.backtest_run_id == backtest_id)
        .order_by(BacktestEquity.timestamp)
        .all()
    )

    return [_equity_to_response(e) for e in equity_curve]


@router.get("/stats/summary", response_model=StatsResponse)
def get_stats_summary(db: Session = Depends(get_db)) -> StatsResponse:
    """전체 백테스트 통계 요약"""
    total_runs = db.query(func.count(BacktestRun.id)).scalar() or 0

    avg_return = db.query(func.avg(BacktestRun.total_return)).scalar()
    max_return = db.query(func.max(BacktestRun.total_return)).scalar()
    min_return = db.query(func.min(BacktestRun.total_return)).scalar()

    strategy_stats = (
        db.query(
            BacktestRun.strategy_name,
            func.count(BacktestRun.id).label("count"),
            func.avg(BacktestRun.total_return).label("avg_return"),
        )
        .group_by(BacktestRun.strategy_name)
        .all()
    )

    return StatsResponse(
        total_runs=total_runs,
        avg_return=float(avg_return) if avg_return else 0.0,
        max_return=float(max_return) if max_return else 0.0,
        min_return=float(min_return) if min_return else 0.0,
        strategy_stats=[
            {
                "strategy_name": stat.strategy_name,
                "count": stat.count,
                "avg_return": float(stat.avg_return) if stat.avg_return else 0.0,
            }
            for stat in strategy_stats
        ],
    )


@router.get("/{backtest_id}/metrics/advanced", response_model=AdvancedMetricsResponse)
def get_advanced_metrics(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> AdvancedMetricsResponse:
    """고급 성과 지표 조회"""
    from app.analytics.summary import calculate_advanced_metrics

    # 백테스트 데이터 조회
    backtest = (
        db.query(BacktestRun)
        .options(
            joinedload(BacktestRun.trades),
            joinedload(BacktestRun.equity_curve),
        )
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # 데이터 변환
    equity_curve = [
        {
            'timestamp': e.timestamp,
            'equity': e.equity,
            'cash': e.cash,
            'position_value': e.position_value,
        }
        for e in backtest.equity_curve
    ]

    trades = [
        {
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'side': t.side,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'quantity': t.quantity,
            'pnl': t.pnl or 0,
            'pnl_pct': t.pnl_pct or 0,
            'commission_paid': t.commission_paid or 0,
        }
        for t in backtest.trades
    ]

    # 고급 지표 계산
    metrics = calculate_advanced_metrics(
        equity_curve=equity_curve,
        trades=trades,
        total_return=backtest.total_return or 0,
        max_drawdown=backtest.max_drawdown or 0,
        initial_capital=backtest.initial_capital,
        start_date=str(backtest.start_date),
        end_date=str(backtest.end_date),
    )

    return AdvancedMetricsResponse(
        sortino_ratio=metrics['sortino_ratio'],
        calmar_ratio=metrics['calmar_ratio'],
        profit_factor=metrics['profit_factor'],
        expectancy=metrics['expectancy'],
        win_loss_ratio=metrics['win_loss_ratio'],
        recovery_factor=metrics['recovery_factor'],
        max_consecutive_wins=metrics['max_consecutive_wins'],
        max_consecutive_losses=metrics['max_consecutive_losses'],
        net_profit=metrics['net_profit'],
        net_profit_pct=metrics['net_profit_pct'],
        total_commission_paid=metrics['total_commission_paid'],
        avg_trade_duration_hours=metrics['avg_trade_duration_bars'],
    )


@router.get("/{backtest_id}/analysis/trades", response_model=TradeAnalysisResponse)
def get_trade_analysis(
    backtest_id: int,
    db: Session = Depends(get_db),
) -> TradeAnalysisResponse:
    """거래 분석 조회"""
    from app.analytics.trade_analysis import analyze_trades
    import pandas as pd

    # 백테스트 데이터 조회
    backtest = (
        db.query(BacktestRun)
        .options(
            joinedload(BacktestRun.trades),
            joinedload(BacktestRun.equity_curve),
        )
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    # 데이터 변환
    trades = [
        {
            'entry_time': t.entry_time,
            'exit_time': t.exit_time,
            'side': t.side,
            'entry_price': t.entry_price,
            'exit_price': t.exit_price,
            'quantity': t.quantity,
            'pnl': t.pnl or 0,
            'pnl_pct': t.pnl_pct or 0,
            'commission_paid': t.commission_paid or 0,
        }
        for t in backtest.trades
    ]

    # 간단한 OHLCV 데이터프레임 생성 (equity curve 기반)
    df = pd.DataFrame([
        {
            'timestamp': e.timestamp,
            'close': e.equity,  # 간단히 equity를 close로 사용
            'high': e.equity,
            'low': e.equity,
            'open': e.equity,
        }
        for e in backtest.equity_curve
    ])

    # 거래 분석
    analysis = analyze_trades(
        trades=trades,
        df=df,
        initial_capital=backtest.initial_capital,
    )

    holding = analysis.get('holding_periods', {})
    distribution = analysis.get('distribution', {})
    quality = analysis.get('quality', {})
    mae_mfe = analysis.get('mae_mfe', {})

    return TradeAnalysisResponse(
        # Holding periods
        avg_holding_hours=holding.get('avg_holding_hours', 0),
        median_holding_hours=holding.get('median_holding_hours', 0),
        min_holding_hours=holding.get('min_holding_hours', 0),
        max_holding_hours=holding.get('max_holding_hours', 0),
        # Distribution
        avg_pnl=distribution.get('avg_pnl', 0),
        median_pnl=distribution.get('median_pnl', 0),
        largest_win=distribution.get('largest_win', 0),
        largest_loss=distribution.get('largest_loss', 0),
        avg_win=distribution.get('avg_win', 0),
        avg_loss=distribution.get('avg_loss', 0),
        # Quality
        small_wins_count=quality.get('small_wins_count', 0),
        medium_wins_count=quality.get('medium_wins_count', 0),
        large_wins_count=quality.get('large_wins_count', 0),
        small_losses_count=quality.get('small_losses_count', 0),
        medium_losses_count=quality.get('medium_losses_count', 0),
        large_losses_count=quality.get('large_losses_count', 0),
        # MAE/MFE
        avg_mae=mae_mfe.get('avg_mae'),
        avg_mfe=mae_mfe.get('avg_mfe'),
        avg_efficiency=mae_mfe.get('avg_efficiency'),
    )


@router.post("/{backtest_id}/monte-carlo")
def run_monte_carlo(
    backtest_id: int,
    n_simulations: int = 1000,
    db: Session = Depends(get_db),
):
    """
    Monte Carlo 시뮬레이션 실행

    거래 순서를 랜덤하게 섞어서 전략의 신뢰도를 검증합니다.

    Args:
        backtest_id: 백테스트 ID
        n_simulations: 시뮬레이션 횟수 (기본값: 1000)
    """
    from app.analytics.monte_carlo import monte_carlo_simulation, analyze_monte_carlo_risk

    # 백테스트 데이터 조회
    backtest = (
        db.query(BacktestRun)
        .options(joinedload(BacktestRun.trades))
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if not backtest.trades:
        raise HTTPException(status_code=400, detail="No trades found for this backtest")

    # 거래 데이터 변환
    trades = [
        {
            'pnl': t.pnl or 0,
            'pnl_pct': t.pnl_pct or 0,
        }
        for t in backtest.trades
    ]

    # Monte Carlo 시뮬레이션 실행
    result = monte_carlo_simulation(
        trades=trades,
        initial_capital=backtest.initial_capital,
        n_simulations=n_simulations,
        n_sample_curves=min(20, n_simulations // 50),
    )

    # 리스크 분석
    risk_analysis = analyze_monte_carlo_risk(result)

    # Convert dataclass to dict and merge with risk analysis
    from dataclasses import asdict
    result_dict = asdict(result)
    result_dict.update({
        'probability_of_loss': risk_analysis['probability_of_loss'],
        'value_at_risk_5': risk_analysis['value_at_risk_5'],
        'conditional_var_5': risk_analysis['conditional_var_5'],
        'confidence_interval_95': risk_analysis['confidence_interval_95'],
        'volatility_ratio': risk_analysis['volatility_ratio'],
        'risk_grade': risk_analysis['risk_grade'],
    })
    return result_dict


@router.post("/{backtest_id}/cost-stress")
def run_cost_stress_test(
    backtest_id: int,
    db: Session = Depends(get_db),
):
    """
    Cost Stress Test - Critical for Strategy Validation

    Tests strategy robustness under realistic cost assumptions:
    1. Commission 2x: Double the commission rate
    2. Slippage +1 tick: Add 1 tick slippage per trade
    3. Execution delay: Delay entry/exit by 1 bar

    If strategy fails these tests, it should be discarded.

    Args:
        backtest_id: 백테스트 ID
    """
    from app.analytics.cost_stress import run_cost_stress_test as run_stress

    # 백테스트 데이터 조회
    backtest = (
        db.query(BacktestRun)
        .options(joinedload(BacktestRun.trades))
        .filter(BacktestRun.id == backtest_id)
        .first()
    )

    if not backtest:
        raise HTTPException(status_code=404, detail="Backtest not found")

    if not backtest.trades:
        raise HTTPException(status_code=400, detail="No trades found for this backtest")

    # Run stress test
    result = run_stress(
        trades=backtest.trades,
        initial_capital=backtest.initial_capital,
        commission_rate=backtest.commission,
        start_date=backtest.start_date,
        end_date=backtest.end_date,
        base_total_return=backtest.total_return or 0.0,
        base_sharpe=backtest.sharpe_ratio or 0.0,
        base_max_drawdown=backtest.max_drawdown or 0.0,
    )

    # Convert dataclass to dict for JSON serialization
    from dataclasses import asdict
    return asdict(result)


@router.post("/run")
def run_backtest(
    strategy_name: str = Query(..., description="Strategy name (e.g., 'RSIMeanReversionStrategy')"),
    symbol: str = Query("BTCUSDT", description="Trading symbol"),
    initial_capital: float = Query(10000.0, description="Initial capital"),
    commission_rate: float = Query(0.001, description="Commission rate"),
    use_real_data: bool = Query(False, description="Use real data from Binance"),
    days_back: int = Query(365, description="Days of historical data (real data only)"),
    db: Session = Depends(get_db),
):
    """
    Run a new backtest with sample or real data

    Set use_real_data=true to fetch real data from Binance
    """
    import sys
    import os

    # Add core-platform to path BEFORE any imports
    core_platform_path = '/Users/jang-yeonghwan/atlas-trading/atlas-trading/core-platform'
    if core_platform_path not in sys.path:
        sys.path.insert(0, core_platform_path)

    # Now import from core-platform
    from datetime import datetime, timedelta
    from app.models.backtest import BacktestRun, BacktestTrade as DBTrade, BacktestEquity as DBEquityPoint

    # Import from api-server utils
    import sys
    api_server_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if api_server_path not in sys.path:
        sys.path.insert(0, api_server_path)

    from app.utils.sample_data import generate_sample_ohlcv

    # Import BacktestEngine from core-platform
    import importlib.util
    engine_path = os.path.join(core_platform_path, 'app', 'backtesting', 'engine.py')
    spec = importlib.util.spec_from_file_location("core_backtesting", engine_path)
    core_backtesting = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core_backtesting)
    BacktestEngine = core_backtesting.BacktestEngine

    # Import all strategies using symlink
    from app.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
    from app.strategies.funding_rate_arbitrage import FundingRateArbitrageStrategy
    from app.strategies.pairs_trading import PairsTradingStrategy
    from app.strategies.trend_following import TrendFollowingStrategy
    from app.strategies.breakout import BreakoutStrategy
    from app.strategies.golden_cross import GoldenCrossStrategy
    from app.strategies.ema_crossover_atr import EMACrossoverATRStrategy
    from app.strategies.mean_reversion_scalping import MeanReversionScalpingStrategy

    try:
        # Strategy registry
        strategy_map = {
            'RSIMeanReversionStrategy': RSIMeanReversionStrategy,
            'FundingRateArbitrageStrategy': FundingRateArbitrageStrategy,
            'PairsTradingStrategy': PairsTradingStrategy,
            'TrendFollowingStrategy': TrendFollowingStrategy,
            'BreakoutStrategy': BreakoutStrategy,
            'GoldenCrossStrategy': GoldenCrossStrategy,
            'EMACrossoverATRStrategy': EMACrossoverATRStrategy,
            'MeanReversionScalpingStrategy': MeanReversionScalpingStrategy,
            # Aliases
            'rsi': RSIMeanReversionStrategy,
            'funding': FundingRateArbitrageStrategy,
            'pairs': PairsTradingStrategy,
            'trend': TrendFollowingStrategy,
            'breakout': BreakoutStrategy,
            'golden cross': GoldenCrossStrategy,
            'ema': EMACrossoverATRStrategy,
            'ema_atr': EMACrossoverATRStrategy,
            'scalping': MeanReversionScalpingStrategy,
            'scalp': MeanReversionScalpingStrategy,
        }

        # Create strategy instance
        strategy_key = strategy_name.lower().replace(' ', '')
        strategy_class = None

        # Try exact match first
        if strategy_name in strategy_map:
            strategy_class = strategy_map[strategy_name]
        # Try lowercase match
        elif strategy_key in strategy_map:
            strategy_class = strategy_map[strategy_key]
        # Try case-insensitive match
        else:
            for key, cls in strategy_map.items():
                if key.lower() == strategy_key:
                    strategy_class = cls
                    break

        if strategy_class is None:
            available = list(set([k for k in strategy_map.keys() if not k.islower()]))
            raise HTTPException(
                status_code=400,
                detail=f"Unknown strategy: {strategy_name}. Available: {available}"
            )

        strategy = strategy_class(symbol=symbol)

        # Get market data
        if use_real_data:
            # Fetch real data from Binance
            from app.data_providers.binance import BinanceDataProvider
            provider = BinanceDataProvider(testnet=False)

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            try:
                df = provider.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch real data: {str(e)}"
                )
        else:
            # Generate sample data
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)

            df = generate_sample_ohlcv(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

        # Run backtest
        engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=commission_rate
        )

        result = engine.run(
            df=df,
            strategy=strategy,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe='1d'
        )

        # Save to database
        backtest = BacktestRun(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe='1d',
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=result.get('final_capital', initial_capital),
            total_return=result.get('total_return', 0.0),
            max_drawdown=result.get('max_drawdown', 0.0),
            sharpe_ratio=result.get('sharpe_ratio', 0.0),
            total_trades=result.get('total_trades', 0),
            winning_trades=result.get('winning_trades', 0),
            losing_trades=result.get('losing_trades', 0),
            win_rate=result.get('win_rate', 0.0),
            commission=commission_rate
        )
        db.add(backtest)
        db.flush()

        # Save trades
        for trade in result.get('trades', []):
            db_trade = DBTrade(
                backtest_run_id=backtest.id,
                entry_time=trade.get('entry_time'),
                exit_time=trade.get('exit_time'),
                side=trade.get('side'),
                entry_price=trade.get('entry_price'),
                exit_price=trade.get('exit_price'),
                quantity=trade.get('quantity'),
                pnl=trade.get('pnl'),
                pnl_pct=trade.get('pnl_pct'),
                commission_paid=trade.get('commission', 0.0)
            )
            db.add(db_trade)

        # Save equity curve
        for point in result.get('equity_curve', []):
            db_point = DBEquityPoint(
                backtest_run_id=backtest.id,
                timestamp=point.get('timestamp'),
                equity=point.get('equity'),
                cash=point.get('cash', point.get('equity')),  # Default to equity if cash not provided
                position_value=point.get('position_value', 0.0)
            )
            db.add(db_point)

        db.commit()

        return {"id": backtest.id, "status": "completed", "message": "Backtest completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
