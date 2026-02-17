"""
Paper Trading API 엔드포인트
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import redis

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.paper_trading import (
    PaperTradingSession,
    PaperTradingTrade,
    PaperTradingSnapshot,
    SessionStatus
)
from app.schemas.paper_trading import (
    PaperTradingSessionCreate,
    PaperTradingSessionUpdate,
    PaperTradingSessionResponse,
    PaperTradingTradeResponse,
    PaperTradingSnapshotResponse,
    PaperTradingStats,
    KlineData
)

router = APIRouter()


@router.post("/sessions", response_model=PaperTradingSessionResponse)
def create_session(
    session_in: PaperTradingSessionCreate,
    db: Session = Depends(get_db)
):
    """새 Paper Trading 세션 생성"""
    session = PaperTradingSession(
        name=session_in.name,
        symbol=session_in.symbol,
        strategy=session_in.strategy,
        initial_capital=session_in.initial_capital,
        current_balance=session_in.initial_capital,
        current_equity=session_in.initial_capital,
        max_equity=session_in.initial_capital,
        settings=session_in.settings,
        status=SessionStatus.ACTIVE
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.get("/sessions", response_model=List[PaperTradingSessionResponse])
def list_sessions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[SessionStatus] = None,
    db: Session = Depends(get_db)
):
    """Paper Trading 세션 목록"""
    query = db.query(PaperTradingSession)

    if status:
        query = query.filter(PaperTradingSession.status == status)

    sessions = query.order_by(PaperTradingSession.start_time.desc()).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}", response_model=PaperTradingSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Paper Trading 세션 상세"""
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.patch("/sessions/{session_id}", response_model=PaperTradingSessionResponse)
def update_session(
    session_id: int,
    session_update: PaperTradingSessionUpdate,
    db: Session = Depends(get_db)
):
    """Paper Trading 세션 업데이트 (상태 변경, 통계 업데이트)"""
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 업데이트
    for field, value in session_update.dict(exclude_unset=True).items():
        setattr(session, field, value)

    session.last_update = datetime.utcnow()

    # 상태가 STOPPED로 변경되면 end_time 설정
    if session_update.status == SessionStatus.STOPPED and not session.end_time:
        session.end_time = datetime.utcnow()

    db.commit()
    db.refresh(session)

    return session


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db)
):
    """Paper Trading 세션 삭제"""
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()

    return {"message": "Session deleted"}


@router.get("/sessions/{session_id}/trades", response_model=List[PaperTradingTradeResponse])
def get_session_trades(
    session_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """세션의 거래 히스토리"""
    trades = db.query(PaperTradingTrade).filter(
        PaperTradingTrade.session_id == session_id
    ).order_by(
        PaperTradingTrade.timestamp.desc()
    ).offset(skip).limit(limit).all()

    return trades


@router.get("/sessions/{session_id}/snapshots", response_model=List[PaperTradingSnapshotResponse])
def get_session_snapshots(
    session_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """세션의 상태 스냅샷 (Equity Curve용)"""
    query = db.query(PaperTradingSnapshot).filter(
        PaperTradingSnapshot.session_id == session_id
    )

    if start_time:
        query = query.filter(PaperTradingSnapshot.timestamp >= start_time)

    if end_time:
        query = query.filter(PaperTradingSnapshot.timestamp <= end_time)

    snapshots = query.order_by(PaperTradingSnapshot.timestamp).limit(limit).all()

    return snapshots


@router.get("/sessions/{session_id}/stats", response_model=PaperTradingStats)
def get_session_stats(
    session_id: int,
    db: Session = Depends(get_db)
):
    """세션 통계 (성과 지표)"""
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 승률 계산
    win_rate = (session.winning_trades / session.total_trades * 100) if session.total_trades > 0 else 0

    # 총 수익률
    total_return = ((session.current_balance - session.initial_capital) / session.initial_capital * 100)

    # Sharpe, Sortino 등은 snapshots에서 계산 (나중에 구현)

    return PaperTradingStats(
        session_id=session.id,
        total_trades=session.total_trades,
        winning_trades=session.winning_trades,
        losing_trades=session.losing_trades,
        win_rate=win_rate,
        total_pnl=session.total_pnl,
        total_commission=session.total_commission,
        total_return=total_return,
        max_drawdown=session.max_drawdown,
        sharpe_ratio=None,  # TODO
        sortino_ratio=None  # TODO
    )


@router.post("/sessions/{session_id}/control/{action}")
def control_session(
    session_id: int,
    action: str,  # start, pause, stop
    db: Session = Depends(get_db)
):
    """세션 제어 (시작/일시정지/중지)"""
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if action == "start":
        session.status = SessionStatus.ACTIVE
    elif action == "pause":
        session.status = SessionStatus.PAUSED
    elif action == "stop":
        session.status = SessionStatus.STOPPED
        session.end_time = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    db.commit()
    db.refresh(session)

    return {"message": f"Session {action}ed", "status": session.status}


@router.get("/sessions/{session_id}/klines", response_model=List[KlineData])
def get_session_klines(
    session_id: int,
    interval: str = "1m",
    limit: int = 500,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """
    세션의 K-line 데이터 반환 (차트용)
    Redis에서 실시간 데이터 가져오기
    interval이 1m이 아닌 경우 1m 데이터를 aggregation
    """
    # 1. 세션 확인
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Redis 스트림 키 생성 (symbol format: BTC/USDT -> BTCUSDT)
    symbol = session.symbol.replace("/", "")

    # Interval mapping (분 단위)
    interval_minutes = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440,
    }

    if interval not in interval_minutes:
        raise HTTPException(status_code=400, detail=f"Unsupported interval: {interval}")

    # 3. 1m 데이터를 항상 가져옴 (다른 interval은 aggregation)
    base_interval = '1m'
    stream_key = f"klines:{symbol}:{base_interval}"

    # 필요한 1m 캔들 개수 계산
    multiplier = interval_minutes[interval]
    fetch_limit = limit * multiplier * 2  # 여유있게 2배

    try:
        # 4. Redis XREVRANGE로 최근 데이터 가져오기 (최신순)
        messages = redis_client.xrevrange(stream_key, '+', '-', count=fetch_limit)

        # 5. 데이터 파싱
        klines_1m = []
        for msg_id, msg_data in messages:
            try:
                if 'data' in msg_data:
                    kline_json = json.loads(msg_data['data'])
                    timestamp_ms = int(msg_data.get('timestamp', 0))

                    if timestamp_ms == 0 and 'open_time' in kline_json:
                        from datetime import datetime
                        dt = datetime.fromisoformat(kline_json['open_time'].replace('+09:00', '+09:00'))
                        timestamp_ms = int(dt.timestamp() * 1000)

                    klines_1m.append({
                        'time': timestamp_ms,
                        'open': float(kline_json.get('open', 0)),
                        'high': float(kline_json.get('high', 0)),
                        'low': float(kline_json.get('low', 0)),
                        'close': float(kline_json.get('close', 0)),
                        'volume': float(kline_json.get('volume', 0))
                    })
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        # 6. 시간순 정렬 (오래된 것부터)
        klines_1m.reverse()

        if not klines_1m:
            return []

        # 7. Aggregation (interval이 1m이 아닌 경우)
        if interval == '1m':
            result = [KlineData(**k) for k in klines_1m]
        else:
            import pandas as pd

            # DataFrame 생성
            df = pd.DataFrame(klines_1m)
            df['datetime'] = pd.to_datetime(df['time'], unit='ms')
            df.set_index('datetime', inplace=True)

            # Resample (aggregation)
            freq_map = {
                '5m': '5min',
                '15m': '15min',
                '1h': '1H',
                '4h': '4H',
                '1d': '1D',
            }
            freq = freq_map[interval]

            resampled = df.resample(freq).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()

            # 결과 변환
            result = []
            for idx, row in resampled.iterrows():
                result.append(KlineData(
                    time=int(idx.timestamp() * 1000),
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume']
                ))

            # limit 적용
            result = result[-limit:]

        return result

    except redis.exceptions.ResponseError as e:
        raise HTTPException(
            status_code=404,
            detail=f"No kline data found for {session.symbol}. Make sure the Go collector is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch kline data from Redis: {str(e)}"
        )
