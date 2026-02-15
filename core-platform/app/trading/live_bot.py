"""
실거래 봇 (Live Trading Bot)

백테스트에서 사용한 동일한 Strategy 객체를 실거래에서도 사용 가능
"""

import ccxt
import pandas as pd
import time
from typing import Optional
from datetime import datetime

from app.strategies.base import Strategy


class LiveTradingBot:
    """
    실거래 봇

    백테스트와 동일한 Strategy 인터페이스를 사용하여
    전략을 실거래에 적용합니다.

    사용 예시:
        strategy = GoldenCrossStrategy(fast_period=10, slow_period=30)
        bot = LiveTradingBot(
            exchange='binance',
            api_key='your_key',
            api_secret='your_secret',
            strategy=strategy,
            symbol='BTC/USDT',
            timeframe='1h'
        )
        bot.start()
    """

    def __init__(
        self,
        exchange: str,
        api_key: str,
        api_secret: str,
        strategy: Strategy,
        symbol: str,
        timeframe: str = '1h',
        initial_capital: float = 10000.0,
        risk_per_trade: float = 0.02,  # 거래당 리스크 2%
    ):
        """
        Args:
            exchange: 거래소 이름 ('binance', 'bybit' 등)
            api_key: API 키
            api_secret: API 시크릿
            strategy: Strategy 객체 (백테스트와 동일)
            symbol: 거래쌍 (예: 'BTC/USDT')
            timeframe: 타임프레임 (예: '1h', '4h', '1d')
            initial_capital: 초기 자본
            risk_per_trade: 거래당 리스크 비율
        """
        # 거래소 연결
        exchange_class = getattr(ccxt, exchange)
        self.exchange = exchange_class({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })

        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade

        # 전략 초기화
        self.strategy.reset()

        # 상태 변수
        self.is_running = False
        self.last_bar_time = None

    def fetch_ohlcv(self, limit: int = 100) -> pd.DataFrame:
        """
        OHLCV 데이터 가져오기

        Args:
            limit: 가져올 캔들 수

        Returns:
            OHLCV 데이터프레임
        """
        ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)

        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 전략의 전처리 실행 (지표 추가)
        df = self.strategy.prepare_data(df)

        return df

    def get_current_position(self) -> Optional[dict]:
        """
        현재 포지션 조회

        Returns:
            포지션 정보 또는 None
        """
        try:
            balance = self.exchange.fetch_balance()
            positions = balance.get('info', {}).get('positions', [])

            for pos in positions:
                if pos['symbol'] == self.symbol.replace('/', ''):
                    if float(pos['positionAmt']) != 0:
                        return pos
            return None
        except Exception as e:
            print(f"포지션 조회 오류: {e}")
            return None

    def open_position(self, side: str, price: float) -> bool:
        """
        포지션 진입

        Args:
            side: 'long' or 'short'
            price: 현재 가격

        Returns:
            성공 여부
        """
        try:
            # 포지션 크기 계산 (자본의 risk_per_trade 비율)
            risk_amount = self.initial_capital * self.risk_per_trade
            quantity = risk_amount / price

            # 주문 실행
            if side == 'long':
                order = self.exchange.create_market_buy_order(self.symbol, quantity)
            else:  # short
                order = self.exchange.create_market_sell_order(self.symbol, quantity)

            print(f"[{datetime.now()}] {side.upper()} 포지션 진입: {quantity:.4f} @ ${price:.2f}")
            print(f"주문 ID: {order['id']}")

            # 전략 콜백 호출
            self.strategy.on_position_opened(side, price, datetime.now())

            return True

        except Exception as e:
            print(f"포지션 진입 오류: {e}")
            return False

    def close_position(self, price: float) -> bool:
        """
        포지션 청산

        Args:
            price: 현재 가격

        Returns:
            성공 여부
        """
        try:
            position = self.get_current_position()
            if not position:
                print("청산할 포지션이 없습니다.")
                return False

            quantity = abs(float(position['positionAmt']))
            side = 'sell' if float(position['positionAmt']) > 0 else 'buy'

            # 주문 실행
            if side == 'sell':
                order = self.exchange.create_market_sell_order(self.symbol, quantity)
            else:
                order = self.exchange.create_market_buy_order(self.symbol, quantity)

            # 손익 계산
            entry_price = float(position['entryPrice'])
            pnl = (price - entry_price) * quantity
            pnl_pct = ((price - entry_price) / entry_price) * 100

            print(f"[{datetime.now()}] 포지션 청산: {quantity:.4f} @ ${price:.2f}")
            print(f"손익: ${pnl:.2f} ({pnl_pct:+.2f}%)")
            print(f"주문 ID: {order['id']}")

            # 전략 콜백 호출
            self.strategy.on_position_closed(pnl, pnl_pct, datetime.now())

            return True

        except Exception as e:
            print(f"포지션 청산 오류: {e}")
            return False

    def process_bar(self, df: pd.DataFrame) -> None:
        """
        새 캔들 처리

        Args:
            df: OHLCV 데이터프레임
        """
        # 최신 캔들 가져오기
        latest_bar = df.iloc[-1]
        current_time = latest_bar['timestamp']

        # 같은 캔들이면 스킵 (이미 처리함)
        if self.last_bar_time == current_time:
            return

        self.last_bar_time = current_time

        # 전략 시그널 생성
        signal = self.strategy.on_bar(latest_bar)
        self.strategy.on_bar_update()

        # 현재 포지션 확인
        has_position = self.strategy.has_position
        current_price = float(latest_bar['close'])

        # 시그널 실행
        if signal == 'long' and not has_position:
            self.open_position('long', current_price)

        elif signal == 'short' and not has_position:
            self.open_position('short', current_price)

        elif signal == 'close' and has_position:
            self.close_position(current_price)

        else:
            # 시그널 없음
            pass

    def start(self, check_interval: int = 60) -> None:
        """
        봇 시작

        Args:
            check_interval: 체크 간격 (초)
        """
        print(f"=== 실거래 봇 시작 ===")
        print(f"전략: {self.strategy.get_name()}")
        print(f"파라미터: {self.strategy.get_parameters()}")
        print(f"거래쌍: {self.symbol}")
        print(f"타임프레임: {self.timeframe}")
        print(f"초기 자본: ${self.initial_capital}")
        print(f"체크 간격: {check_interval}초")
        print("=" * 40)

        self.is_running = True

        try:
            while self.is_running:
                # OHLCV 데이터 가져오기
                df = self.fetch_ohlcv()

                # 최신 캔들 처리
                self.process_bar(df)

                # 대기
                time.sleep(check_interval)

        except KeyboardInterrupt:
            print("\n봇 중지 중...")
            self.stop()

        except Exception as e:
            print(f"오류 발생: {e}")
            self.stop()

    def stop(self) -> None:
        """봇 중지"""
        self.is_running = False
        print("봇이 중지되었습니다.")


# 사용 예시
if __name__ == "__main__":
    from app.strategies import GoldenCrossStrategy, RSIStrategy

    # 전략 선택 (백테스트와 동일한 객체!)
    strategy = GoldenCrossStrategy(fast_period=10, slow_period=30)
    # 또는
    # strategy = RSIStrategy(rsi_period=14, oversold_level=30, overbought_level=70)

    # 실거래 봇 시작
    bot = LiveTradingBot(
        exchange='binance',
        api_key='YOUR_API_KEY',
        api_secret='YOUR_API_SECRET',
        strategy=strategy,  # 백테스트와 동일한 Strategy 객체
        symbol='BTC/USDT',
        timeframe='1h',
        initial_capital=10000.0,
    )

    bot.start(check_interval=60)
