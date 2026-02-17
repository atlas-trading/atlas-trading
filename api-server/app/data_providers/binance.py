"""
Binance Data Provider

Fetches real OHLCV data from Binance using CCXT
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List


class BinanceDataProvider:
    """Binance 거래소에서 OHLCV 데이터를 가져오는 클래스"""

    def __init__(self, testnet: bool = False):
        """
        Args:
            testnet: True면 Binance Testnet 사용, False면 실제 거래소 사용
        """
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future' if testnet else 'spot',
            }
        })

        if testnet:
            self.exchange.set_sandbox_mode(True)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1d',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 가져오기

        Args:
            symbol: 거래쌍 (예: 'BTC/USDT', 'BTCUSDT')
            timeframe: 타임프레임 ('1m', '5m', '15m', '1h', '4h', '1d', '1w')
            start_date: 시작 날짜 (기본값: 1년 전)
            end_date: 종료 날짜 (기본값: 현재)
            limit: 최대 캔들 수 (기본값: 1000, 최대: 1000)

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        # 심볼 형식 정규화 (BTCUSDT -> BTC/USDT)
        if '/' not in symbol:
            # BTCUSDT, ETHUSDT 등을 BTC/USDT, ETH/USDT로 변환
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                symbol = f"{base}/USDT"
            elif symbol.endswith('BUSD'):
                base = symbol[:-4]
                symbol = f"{base}/BUSD"

        # 기본 날짜 설정
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # 타임스탬프 변환 (밀리초)
        since = int(start_date.timestamp() * 1000)
        until = int(end_date.timestamp() * 1000)

        all_candles = []
        current_since = since

        # CCXT는 한 번에 최대 1000개까지만 가져올 수 있으므로 반복해서 가져옴
        while current_since < until:
            try:
                candles = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=limit
                )

                if not candles:
                    break

                all_candles.extend(candles)

                # 다음 요청의 시작 시간 업데이트
                last_timestamp = candles[-1][0]
                if last_timestamp >= until:
                    break

                current_since = last_timestamp + 1

                # 모든 데이터를 가져왔으면 종료
                if len(candles) < limit:
                    break

            except ccxt.NetworkError as e:
                print(f"Network error: {e}")
                break
            except ccxt.ExchangeError as e:
                print(f"Exchange error: {e}")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                break

        if not all_candles:
            raise ValueError(f"No data retrieved for {symbol}")

        # DataFrame으로 변환
        df = pd.DataFrame(
            all_candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        # 타임스탬프를 datetime으로 변환
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # 종료 날짜 필터링
        df = df[df['timestamp'] <= end_date]

        # 중복 제거 (같은 타임스탬프가 있을 수 있음)
        df = df.drop_duplicates(subset=['timestamp'], keep='last')

        # 정렬
        df = df.sort_values('timestamp').reset_index(drop=True)

        return df

    def get_available_symbols(self) -> List[str]:
        """
        거래 가능한 심볼 목록 가져오기

        Returns:
            List of trading pairs (e.g., ['BTC/USDT', 'ETH/USDT', ...])
        """
        try:
            markets = self.exchange.load_markets()
            return [symbol for symbol in markets.keys() if '/USDT' in symbol]
        except Exception as e:
            print(f"Error loading markets: {e}")
            return []


def test_binance_provider():
    """테스트 함수"""
    provider = BinanceDataProvider(testnet=False)

    # BTC/USDT 최근 30일 데이터
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    df = provider.fetch_ohlcv(
        symbol='BTC/USDT',
        timeframe='1d',
        start_date=start_date,
        end_date=end_date
    )

    print(f"Fetched {len(df)} candles")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Price range: ${df['close'].min():.2f} to ${df['close'].max():.2f}")
    print("\nFirst 5 rows:")
    print(df.head())


if __name__ == "__main__":
    test_binance_provider()
