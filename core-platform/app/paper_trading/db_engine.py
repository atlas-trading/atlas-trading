#!/usr/bin/env python3
"""
Paper Trading Engine with Database Integration
API 서버와 연동되는 DB 저장 버전
"""
import redis
import json
import time
import random
import sys
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

# API 서버 경로 추가
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "api-server"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.paper_trading import (
    PaperTradingSession,
    PaperTradingTrade,
    PaperTradingSnapshot,
    SessionStatus
)

# 기본 로깅
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DBPaperTrading:
    """DB 연동 Paper Trading 엔진"""

    def __init__(
        self,
        session_id: int,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        db_url: str = "postgresql+psycopg://jang-yeonghwan@localhost/atlas_trading"
    ):
        # DB 연결
        self.db_engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(bind=self.db_engine)

        # 세션 로드
        with self.SessionLocal() as db:
            self.db_session_id = session_id
            db_session = db.query(PaperTradingSession).filter(
                PaperTradingSession.id == session_id
            ).first()

            if not db_session:
                raise ValueError(f"Session {session_id} not found")

            if db_session.status != SessionStatus.ACTIVE:
                raise ValueError(f"Session {session_id} is not active")

            # 설정 로드
            self.initial_capital = db_session.initial_capital
            self.balance = db_session.current_balance
            self.equity = db_session.current_equity
            self.symbol = db_session.symbol
            self.symbol_normalized = db_session.symbol.replace('/', '')
            self.strategy = db_session.strategy

        # Redis
        self.redis = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )

        # 포지션
        self.position: Optional[Dict] = None
        self.current_price = 0.0

        # 통계
        self.total_pnl = 0.0

        # 수수료 및 슬리피지
        self.maker_fee = 0.0002
        self.taker_fee = 0.0004
        self.base_slippage = 0.0005

        # 스냅샷 주기
        self.last_snapshot_time = time.time()
        self.snapshot_interval = 10  # 10초마다

    def calculate_slippage(self, order_size_usd: float) -> float:
        """슬리피지 계산"""
        base = self.base_slippage
        size_impact = min(order_size_usd / 50000, 0.001)
        random_factor = random.uniform(0.8, 1.2)
        return (base + size_impact) * random_factor

    def save_trade(self, trade_data: Dict, db: Session):
        """거래를 DB에 저장"""
        trade = PaperTradingTrade(
            session_id=self.db_session_id,
            symbol=trade_data['symbol'],
            side=trade_data['side'],
            position_side=trade_data['position_side'],
            quantity=trade_data['quantity'],
            entry_price=trade_data.get('entry_price'),
            exit_price=trade_data.get('exit_price'),
            commission=trade_data['commission'],
            slippage=trade_data.get('slippage', 0.0),
            pnl=trade_data.get('pnl'),
            pnl_percent=trade_data.get('pnl_percent'),
            position_type=trade_data.get('position_type'),
            stop_loss=trade_data.get('stop_loss'),
            take_profit=trade_data.get('take_profit'),
            exit_reason=trade_data.get('exit_reason'),
            timestamp=datetime.utcnow()
        )

        db.add(trade)

    def save_snapshot(self, db: Session):
        """상태 스냅샷 저장"""
        snapshot = PaperTradingSnapshot(
            session_id=self.db_session_id,
            balance=self.balance,
            equity=self.equity,
            unrealized_pnl=self.equity - self.balance,
            open_positions=[self.position] if self.position else [],
            market_price=self.current_price,
            timestamp=datetime.utcnow()
        )

        db.add(snapshot)

    def update_session(self, db: Session):
        """세션 통계 업데이트"""
        session = db.query(PaperTradingSession).filter(
            PaperTradingSession.id == self.db_session_id
        ).first()

        if session:
            session.current_balance = self.balance
            session.current_equity = self.equity
            session.last_update = datetime.utcnow()

            # max_equity 업데이트
            if session.max_equity is None or self.equity > session.max_equity:
                session.max_equity = self.equity

            # max_drawdown 계산
            if session.max_equity and session.max_equity > 0:
                current_dd = (session.max_equity - self.equity) / session.max_equity
                if current_dd > session.max_drawdown:
                    session.max_drawdown = current_dd

    def open_long(self, price: float, signal: Dict):
        """롱 포지션 진입 (DB 저장 포함)"""
        if self.position:
            logger.warning("Already in position")
            return

        stop_loss = signal.get('stop_loss', price * 0.98)
        take_profit = signal.get('take_profit', price * 1.04)

        position_value = self.balance * 0.9
        quantity = position_value / price

        slippage = self.calculate_slippage(position_value)
        entry_price = price * (1 + slippage)
        commission = (quantity * entry_price) * self.taker_fee

        self.position = {
            'side': 'long',
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.utcnow(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_paid': commission
        }

        # DB 저장
        with self.SessionLocal() as db:
            # 거래 기록
            self.save_trade({
                'symbol': self.symbol,
                'side': 'buy',
                'position_side': 'open',
                'quantity': quantity,
                'entry_price': entry_price,
                'commission': commission,
                'slippage': slippage,
                'position_type': 'long',
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }, db)

            # 세션 통계 업데이트
            session = db.query(PaperTradingSession).filter(
                PaperTradingSession.id == self.db_session_id
            ).first()
            session.total_commission += commission

            db.commit()

        logger.info("")
        logger.info(f"LONG {self.symbol} @ ${entry_price:,.2f} x {quantity:.4f}")
        logger.info(f"   Slippage: {slippage*100:.3f}% | Commission: ${commission:.2f}")
        logger.info(f"   Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")

    def open_short(self, price: float, signal: Dict):
        """숏 포지션 진입 (DB 저장 포함)"""
        if self.position:
            logger.warning("Already in position")
            return

        stop_loss = signal.get('stop_loss', price * 1.02)
        take_profit = signal.get('take_profit', price * 0.96)

        position_value = self.balance * 0.9
        quantity = position_value / price

        slippage = self.calculate_slippage(position_value)
        entry_price = price * (1 - slippage)
        commission = (quantity * entry_price) * self.taker_fee

        self.position = {
            'side': 'short',
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.utcnow(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_paid': commission
        }

        # DB 저장
        with self.SessionLocal() as db:
            # 거래 기록
            self.save_trade({
                'symbol': self.symbol,
                'side': 'sell',
                'position_side': 'open',
                'quantity': quantity,
                'entry_price': entry_price,
                'commission': commission,
                'slippage': slippage,
                'position_type': 'short',
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }, db)

            # 세션 통계 업데이트
            session = db.query(PaperTradingSession).filter(
                PaperTradingSession.id == self.db_session_id
            ).first()
            session.total_commission += commission

            db.commit()

        logger.info("")
        logger.info(f"SHORT {self.symbol} @ ${entry_price:,.2f} x {quantity:.4f}")
        logger.info(f"   Slippage: {slippage*100:.3f}% | Commission: ${commission:.2f}")
        logger.info(f"   Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")

    def close_position(self, price: float, reason: str):
        """포지션 청산 (DB 저장 포함)"""
        if not self.position:
            return

        pos = self.position

        slippage = self.calculate_slippage(pos['quantity'] * price)
        if pos['side'] == 'long':
            exit_price = price * (1 - slippage)
        else:
            exit_price = price * (1 + slippage)

        commission = (pos['quantity'] * exit_price) * self.taker_fee

        # PnL 계산
        if pos['side'] == 'long':
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']

        total_commission = pos['commission_paid'] + commission
        net_pnl = pnl - total_commission

        self.balance += net_pnl
        self.total_pnl += net_pnl

        # DB 저장
        with self.SessionLocal() as db:
            # 청산 거래 기록
            self.save_trade({
                'symbol': self.symbol,
                'side': 'sell' if pos['side'] == 'long' else 'buy',
                'position_side': 'close',
                'quantity': pos['quantity'],
                'exit_price': exit_price,
                'commission': commission,
                'slippage': slippage,
                'pnl': net_pnl,
                'pnl_percent': (net_pnl / (pos['entry_price'] * pos['quantity'])) * 100,
                'exit_reason': reason
            }, db)

            # 세션 통계 업데이트
            session = db.query(PaperTradingSession).filter(
                PaperTradingSession.id == self.db_session_id
            ).first()

            session.total_trades += 1
            session.total_pnl += net_pnl
            session.total_commission += total_commission

            if net_pnl > 0:
                session.winning_trades += 1
            else:
                session.losing_trades += 1

            self.update_session(db)

            db.commit()

        emoji = "UP" if net_pnl > 0 else "DOWN"
        pnl_pct = (net_pnl / (pos['entry_price'] * pos['quantity'])) * 100
        logger.info("")
        logger.info(f"{emoji} CLOSE {self.symbol} @ ${exit_price:,.2f} ({reason})")
        logger.info(f"   PnL: ${net_pnl:+,.2f} ({pnl_pct:+.2f}%) | Commission: ${total_commission:.2f}")

        self.position = None

    def update_price(self, price: float):
        """실시간 가격 업데이트"""
        self.current_price = price

        if not self.position:
            self.equity = self.balance
            return

        # 미실현 손익 계산
        pos = self.position
        if pos['side'] == 'long':
            unrealized_pnl = (price - pos['entry_price']) * pos['quantity']
        else:
            unrealized_pnl = (pos['entry_price'] - price) * pos['quantity']

        unrealized_pnl -= pos['commission_paid']
        self.equity = self.balance + unrealized_pnl

        # Stop Loss / Take Profit 체크
        if pos['side'] == 'long':
            if price <= pos['stop_loss']:
                self.close_position(price, 'stop_loss')
            elif price >= pos['take_profit']:
                self.close_position(price, 'take_profit')
        else:
            if price >= pos['stop_loss']:
                self.close_position(price, 'stop_loss')
            elif price <= pos['take_profit']:
                self.close_position(price, 'take_profit')

    def print_status(self):
        """상태 출력"""
        return_pct = ((self.balance - self.initial_capital) / self.initial_capital) * 100

        logger.info("=" * 70)
        logger.info(f"Balance: ${self.balance:,.2f} | Equity: ${self.equity:,.2f} | "
                   f"PnL: ${self.total_pnl:+,.2f} ({return_pct:+.2f}%)")
        logger.info(f"Current Price: ${self.current_price:,.2f}")

        if self.position:
            pos = self.position
            unrealized = (self.current_price - pos['entry_price']) * pos['quantity'] if pos['side'] == 'long' \
                        else (pos['entry_price'] - self.current_price) * pos['quantity']
            logger.info(f"Position: {pos['side'].upper()} @ ${pos['entry_price']:,.2f} | "
                       f"Unrealized: ${unrealized:+,.2f}")

        logger.info("=" * 70)

    def save_periodic_snapshot(self):
        """주기적 스냅샷 저장"""
        current_time = time.time()
        if current_time - self.last_snapshot_time >= self.snapshot_interval:
            with self.SessionLocal() as db:
                self.save_snapshot(db)
                self.update_session(db)
                db.commit()

            self.last_snapshot_time = current_time

    def run(self):
        """메인 실행 루프"""
        logger.info("=" * 70)
        logger.info("DB Paper Trading Engine Started")
        logger.info(f"Session ID: {self.db_session_id}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Symbol: {self.symbol}")
        logger.info(f"Strategy: {self.strategy}")
        logger.info("=" * 70)
        logger.info("")

        # Redis Streams
        last_ids = {
            f'signals:{self.strategy}': '0',
            f'trades:{self.symbol_normalized}': '0',
        }

        last_status_time = time.time()

        try:
            while True:
                # 데이터 읽기 (100ms timeout)
                results = self.redis.xread(last_ids, block=100, count=10)

                for stream_name, messages in results:
                    for message_id, data in messages:
                        last_ids[stream_name] = message_id

                        try:
                            parsed = json.loads(data['data'])

                            if 'signals:' in stream_name:
                                # 신호 처리
                                action = parsed.get('action', '')
                                symbol = parsed.get('symbol', '').replace('/', '')
                                price = parsed.get('price', 0.0)

                                if symbol == self.symbol_normalized:
                                    if action == 'long' and not self.position:
                                        self.open_long(price, parsed)
                                    elif action == 'short' and not self.position:
                                        self.open_short(price, parsed)
                                    elif action == 'close' and self.position:
                                        self.close_position(price, 'signal')

                            elif 'trades:' in stream_name:
                                # 가격 업데이트
                                symbol = parsed.get('symbol', '').replace('/', '')
                                price = parsed.get('price', 0.0)

                                if symbol == self.symbol_normalized:
                                    self.update_price(price)

                        except (json.JSONDecodeError, KeyError) as e:
                            pass

                # 주기적 스냅샷 저장
                self.save_periodic_snapshot()

                # 10초마다 상태 출력
                if time.time() - last_status_time >= 10:
                    self.print_status()
                    last_status_time = time.time()

        except KeyboardInterrupt:
            logger.info("")
            logger.info("Stopping Paper Trading...")
            self.print_final_report()

    def print_final_report(self):
        """최종 보고서"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Balance:   ${self.balance:,.2f}")
        logger.info(f"Total PnL:       ${self.total_pnl:+,.2f} ({((self.balance/self.initial_capital)-1)*100:+.2f}%)")
        logger.info("=" * 70)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='DB Paper Trading')
    parser.add_argument('--session-id', type=int, required=True, help='Session ID from API')
    parser.add_argument('--db-url', type=str,
                       default='postgresql+psycopg://jang-yeonghwan@localhost/atlas_trading',
                       help='Database URL')

    args = parser.parse_args()

    engine = DBPaperTrading(
        session_id=args.session_id,
        db_url=args.db_url
    )

    engine.run()
