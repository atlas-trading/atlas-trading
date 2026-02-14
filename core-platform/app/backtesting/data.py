"""Data fetching and preprocessing"""
import ccxt
import pandas as pd
from datetime import datetime
from typing import Optional


class DataFetcher:
    """시장 데이터 다운로드"""

    def __init__(self, exchange_id: str = "binance"):
        """
        Args:
            exchange_id: CCXT exchange ID (default: binance)
        """
        self.exchange = getattr(ccxt, exchange_id)()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 다운로드

        Args:
            symbol: 거래쌍 (예: "BTC/USDT")
            timeframe: 타임프레임 (예: "1h", "1d")
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 한 번에 가져올 캔들 개수

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        since = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        all_ohlcv = []
        current_since = since

        while current_since < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=current_since, limit=limit
                )

                if not ohlcv:
                    break

                all_ohlcv.extend(ohlcv)

                # 다음 요청을 위한 timestamp 업데이트
                current_since = ohlcv[-1][0] + 1

                # API rate limit 고려
                self.exchange.sleep(self.exchange.rateLimit)

            except Exception as e:
                print(f"데이터 다운로드 오류: {e}")
                break

        if not all_ohlcv:
            return pd.DataFrame()

        # DataFrame 변환
        df = pd.DataFrame(
            all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        # timestamp를 datetime으로 변환
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # 중복 제거 및 정렬
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        # 날짜 범위 필터링
        df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]

        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        기술적 지표 계산 (이동평균선 등)

        Args:
            df: OHLCV DataFrame

        Returns:
            지표가 추가된 DataFrame
        """
        # Simple Moving Averages
        df["sma_50"] = df["close"].rolling(window=50).mean()
        df["sma_200"] = df["close"].rolling(window=200).mean()

        # Exponential Moving Averages
        df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()

        return df
