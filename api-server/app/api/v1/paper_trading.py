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
    """
    # 1. 세션 확인
    session = db.query(PaperTradingSession).filter(PaperTradingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Redis 스트림 키 생성 (symbol format: BTC/USDT -> BTCUSDT)
    symbol = session.symbol.replace("/", "")
    stream_key = f"klines:{symbol}:{interval}"

    try:
        # 3. Redis XREVRANGE로 최근 데이터 가져오기 (최신순)
        # XREVRANGE stream_key + - COUNT limit
        messages = redis_client.xrevrange(stream_key, '+', '-', count=limit)

        # 4. 데이터 파싱 및 변환
        klines = []
        for msg_id, msg_data in messages:
            try:
                # Redis Stream 데이터 형식: {'data': '<json>', 'timestamp': '<unix_ms>'}
                if 'data' in msg_data:
                    kline_json = json.loads(msg_data['data'])

                    # Go collector의 Kline 구조체 매핑
                    # type Kline struct { Time, Open, High, Low, Close, Volume, ... }
                    klines.append(KlineData(
                        time=kline_json.get('Time', kline_json.get('time', 0)),
                        open=float(kline_json.get('Open', kline_json.get('open', 0))),
                        high=float(kline_json.get('High', kline_json.get('high', 0))),
                        low=float(kline_json.get('Low', kline_json.get('low', 0))),
                        close=float(kline_json.get('Close', kline_json.get('close', 0))),
                        volume=float(kline_json.get('Volume', kline_json.get('volume', 0)))
                    ))
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # 개별 메시지 파싱 오류는 로그만 남기고 계속 진행
                continue

        # 5. 시간순 정렬 (오래된 것부터)
        klines.reverse()

        return klines

    except redis.exceptions.ResponseError as e:
        # Redis 스트림이 존재하지 않는 경우
        raise HTTPException(
            status_code=404,
            detail=f"No kline data found for {session.symbol} ({interval}). Make sure the Go collector is running."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch kline data from Redis: {str(e)}"
        )
