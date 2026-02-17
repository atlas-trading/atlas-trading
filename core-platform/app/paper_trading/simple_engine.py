#!/usr/bin/env python3
"""
Simple Paper Trading Engine
실제 매매와 동일한 플로우, 간단한 구현
"""
import redis
import json
import time
import random
from datetime import datetime
from typing import Dict, Optional

# 기본 로깅
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimplePaperTrading:
    """간단한 Paper Trading 엔진"""
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        symbol: str = "BTC/USDT",
        redis_host: str = "localhost",
        redis_port: int = 6379
    ):
        # 계좌
        self.initial_capital = initial_capital
        self.balance = initial_capital
        self.equity = initial_capital
        
        # 설정
        self.symbol = symbol
        self.symbol_normalized = symbol.replace('/', '')  # BTC/USDT -> BTCUSDT
        
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
        self.trades = []
        self.total_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        
        # 수수료 및 슬리피지
        self.maker_fee = 0.0002  # 0.02%
        self.taker_fee = 0.0004  # 0.04%
        self.base_slippage = 0.0005  # 0.05%
    
    def calculate_slippage(self, order_size_usd: float) -> float:
        """현실적인 슬리피지 계산"""
        base = self.base_slippage
        size_impact = min(order_size_usd / 50000, 0.001)  # 최대 0.1%
        random_factor = random.uniform(0.8, 1.2)
        return (base + size_impact) * random_factor
    
    def open_long(self, price: float, signal: Dict):
        """롱 포지션 진입"""
        if self.position:
            logger.warning("⚠️ Already in position")
            return
        
        # Stop Loss / Take Profit
        stop_loss = signal.get('stop_loss', price * 0.98)  # -2%
        take_profit = signal.get('take_profit', price * 1.04)  # +4%
        
        # 포지션 크기 (계좌의 90% 사용, 나머지는 수수료용)
        position_value = self.balance * 0.9
        quantity = position_value / price
        
        # 슬리피지 적용
        slippage = self.calculate_slippage(position_value)
        entry_price = price * (1 + slippage)
        
        # 수수료 계산
        commission = (quantity * entry_price) * self.taker_fee
        
        # 포지션 저장
        self.position = {
            'side': 'long',
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_paid': commission
        }
        
        logger.info("")
        logger.info(f"🟢 LONG {self.symbol} @ ${entry_price:,.2f} × {quantity:.4f}")
        logger.info(f"   Slippage: {slippage*100:.3f}% | Commission: ${commission:.2f}")
        logger.info(f"   Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")
    
    def open_short(self, price: float, signal: Dict):
        """숏 포지션 진입"""
        if self.position:
            logger.warning("⚠️ Already in position")
            return
        
        # Stop Loss / Take Profit
        stop_loss = signal.get('stop_loss', price * 1.02)  # +2%
        take_profit = signal.get('take_profit', price * 0.96)  # -4%
        
        # 포지션 크기
        position_value = self.balance * 0.9
        quantity = position_value / price
        
        # 슬리피지 적용
        slippage = self.calculate_slippage(position_value)
        entry_price = price * (1 - slippage)  # Short는 반대
        
        # 수수료
        commission = (quantity * entry_price) * self.taker_fee
        
        # 포지션 저장
        self.position = {
            'side': 'short',
            'quantity': quantity,
            'entry_price': entry_price,
            'entry_time': datetime.now(),
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'commission_paid': commission
        }
        
        logger.info("")
        logger.info(f"🔴 SHORT {self.symbol} @ ${entry_price:,.2f} × {quantity:.4f}")
        logger.info(f"   Slippage: {slippage*100:.3f}% | Commission: ${commission:.2f}")
        logger.info(f"   Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")
    
    def close_position(self, price: float, reason: str):
        """포지션 청산"""
        if not self.position:
            return
        
        pos = self.position
        
        # 슬리피지 적용
        slippage = self.calculate_slippage(pos['quantity'] * price)
        if pos['side'] == 'long':
            exit_price = price * (1 - slippage)  # 팔 때는 불리하게
        else:
            exit_price = price * (1 + slippage)  # 숏 청산은 살 때
        
        # 수수료
        commission = (pos['quantity'] * exit_price) * self.taker_fee
        
        # PnL 계산
        if pos['side'] == 'long':
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:  # short
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']
        
        # 수수료 차감
        total_commission = pos['commission_paid'] + commission
        net_pnl = pnl - total_commission
        
        # 계좌 업데이트
        self.balance += net_pnl
        self.total_pnl += net_pnl
        
        # 승/패 기록
        if net_pnl > 0:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        # 거래 기록
        self.trades.append({
            'symbol': self.symbol,
            'side': pos['side'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'quantity': pos['quantity'],
            'pnl': net_pnl,
            'pnl_percent': (net_pnl / (pos['entry_price'] * pos['quantity'])) * 100,
            'reason': reason,
            'timestamp': datetime.now()
        })
        
        # 로그
        emoji = "📈" if net_pnl > 0 else "📉"
        pnl_pct = (net_pnl / (pos['entry_price'] * pos['quantity'])) * 100
        logger.info("")
        logger.info(f"{emoji} CLOSE {self.symbol} @ ${exit_price:,.2f} ({reason})")
        logger.info(f"   PnL: ${net_pnl:+,.2f} ({pnl_pct:+.2f}%) | Commission: ${total_commission:.2f}")
        
        # 포지션 제거
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
        
        unrealized_pnl -= pos['commission_paid']  # 진입 수수료 차감
        self.equity = self.balance + unrealized_pnl
        
        # Stop Loss / Take Profit 체크
        if pos['side'] == 'long':
            if price <= pos['stop_loss']:
                self.close_position(price, 'stop_loss')
            elif price >= pos['take_profit']:
                self.close_position(price, 'take_profit')
        else:  # short
            if price >= pos['stop_loss']:
                self.close_position(price, 'stop_loss')
            elif price <= pos['take_profit']:
                self.close_position(price, 'take_profit')
    
    def print_status(self):
        """상태 출력"""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        return_pct = ((self.balance - self.initial_capital) / self.initial_capital) * 100
        
        logger.info("=" * 70)
        logger.info(f"💰 Balance: ${self.balance:,.2f} | Equity: ${self.equity:,.2f} | "
                   f"PnL: ${self.total_pnl:+,.2f} ({return_pct:+.2f}%)")
        logger.info(f"📊 Trades: {total_trades} | Win Rate: {win_rate:.1f}% | "
                   f"Current: ${self.current_price:,.2f}")
        
        if self.position:
            pos = self.position
            unrealized = (self.current_price - pos['entry_price']) * pos['quantity'] if pos['side'] == 'long' \
                        else (pos['entry_price'] - self.current_price) * pos['quantity']
            logger.info(f"📍 Position: {pos['side'].upper()} @ ${pos['entry_price']:,.2f} | "
                       f"Unrealized: ${unrealized:+,.2f}")
        
        logger.info("=" * 70)
    
    def run(self):
        """메인 실행 루프"""
        logger.info("=" * 70)
        logger.info("🚀 Simple Paper Trading Engine Started")
        logger.info(f"💰 Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"📈 Symbol: {self.symbol}")
        logger.info("=" * 70)
        logger.info("")
        
        # Redis Streams
        last_ids = {
            f'signals:Statistical Arbitrage': '0',
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
                
                # 10초마다 상태 출력
                if time.time() - last_status_time >= 10:
                    self.print_status()
                    last_status_time = time.time()
        
        except KeyboardInterrupt:
            logger.info("")
            logger.info("🛑 Stopping Paper Trading...")
            self.print_final_report()
    
    def print_final_report(self):
        """최종 보고서"""
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 FINAL REPORT")
        logger.info("=" * 70)
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Balance:   ${self.balance:,.2f}")
        logger.info(f"Total PnL:       ${self.total_pnl:+,.2f} ({((self.balance/self.initial_capital)-1)*100:+.2f}%)")
        logger.info("")
        
        total = self.win_count + self.loss_count
        logger.info(f"Total Trades:  {total}")
        logger.info(f"Winning:       {self.win_count}")
        logger.info(f"Losing:        {self.loss_count}")
        logger.info(f"Win Rate:      {(self.win_count/total*100) if total > 0 else 0:.1f}%")
        logger.info("=" * 70)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Paper Trading')
    parser.add_argument('--capital', type=float, default=10000, help='Initial capital')
    parser.add_argument('--symbol', type=str, default='BTC/USDT', help='Symbol to trade')
    
    args = parser.parse_args()
    
    engine = SimplePaperTrading(
        initial_capital=args.capital,
        symbol=args.symbol
    )
    
    engine.run()
