# Backtest Engine — System Design Spec

**Date:** 2026-06-06
**Status:** Approved

---

## Goals

Binance 과거 bookTicker 데이터를 취득해 기존 삼각 차익거래 전략을 그대로 재실행하고, 수수료·슬리피지를 반영한 PnL 통계를 산출한다.

**성공 기준:**
- `python run_backtest.py --start 2025-03-01 --end 2025-05-31 --fetch` 한 번으로 데이터 취득부터 결과 출력까지 완결
- `TriangularArbitrageStrategy`, `ExecutionEngine`, `ArbitrageStateMachine`, `RiskManager` — 소스 수정 없이 재사용
- 터미널 요약 + CSV 파일 출력

---

## Architecture Overview

```
run_backtest.py  (CLI 진입점)
 ├── BinanceVisionFetcher   atlas/backtest/fetcher.py
 │     └── Binance Vision zip → 1초 다운샘플 → raw_ticks INSERT
 ├── HistoricalFeed         atlas/backtest/feed.py
 │     └── raw_ticks SELECT (스트리밍) → on_tickers() 재생
 ├── BacktestExchange       atlas/backtest/exchange.py
 │     └── ExchangeInterface 구현, 가상 체결, 잔고 추적
 ├── BacktestRunner         atlas/backtest/runner.py
 │     └── LiveRunner와 동일 구조, 거래 기록 수집
 └── BacktestReport         atlas/backtest/report.py
       └── 터미널 요약 + CSV 저장
```

**재사용 컴포넌트 (수정 없음):**

| 컴포넌트 | 역할 |
|---------|------|
| `TriangularArbitrageStrategy` | 기회 탐지, 시그널 생성 |
| `ExecutionEngine` | RiskManager 게이트 |
| `ArbitrageStateMachine` | 3-레그 실행 흐름 |
| `RiskManager` | 주문 크기·노출 한도 |

---

## File Layout

```
core-platform/
├── atlas/backtest/
│   ├── __init__.py
│   ├── fetcher.py      # BinanceVisionFetcher
│   ├── feed.py         # HistoricalFeed
│   ├── exchange.py     # BacktestExchange
│   ├── runner.py       # BacktestRunner
│   └── report.py       # BacktestReport
├── run_backtest.py
└── tests/test_backtest/
    ├── __init__.py
    ├── test_fetcher.py
    ├── test_feed.py
    ├── test_exchange.py
    └── test_runner.py
```

---

## Component Specs

### 1. BinanceVisionFetcher (`fetcher.py`)

**데이터 소스:**
```
https://data.binance.vision/data/spot/daily/bookTicker/{SYMBOL}/{SYMBOL}-bookTicker-{DATE}.zip
```

CSV 포맷: `update_id, best_bid_price, best_bid_qty, best_ask_price, best_ask_qty, transaction_time, event_time`

**동작:**
1. 날짜 범위 × 9 심볼 → (symbol, date) 목록 생성
2. `aiohttp` 병렬 다운로드 (최대 20 동시)
3. zip 압축 해제 → CSV 파싱
4. **1초 다운샘플링**: 각 1초 윈도우의 마지막 행만 보존
5. `raw_ticks` 배치 INSERT (1,000행 단위)
6. **멱등성**: 해당 (exchange, symbol, 날짜) 범위가 이미 존재하면 skip

**심볼 매핑:**

| ccxt 형식 | Binance Vision |
|-----------|---------------|
| BTC/USDT | BTCUSDT |
| ETH/USDT | ETHUSDT |
| ETH/BTC  | ETHBTC |
| BNB/USDT | BNBUSDT |
| BNB/BTC  | BNBBTC |
| BNB/ETH  | BNBETH |
| XRP/USDT | XRPUSDT |
| XRP/BTC  | XRPBTC |
| XRP/ETH  | XRPETH |

**에러 처리:**
- HTTP 404: 해당 날짜 데이터 없음 → 경고 로그 후 skip
- 네트워크 오류: 최대 3회 재시도 후 skip

---

### 2. HistoricalFeed (`feed.py`)

**동작:**

```python
async def stream(start: datetime, end: datetime) -> AsyncIterator[dict[str, dict]]:
    """1초 단위 tickers dict를 순서대로 yield."""
```

- `raw_ticks` WHERE timestamp BETWEEN start AND end, ORDER BY timestamp
- 청크 단위 스트리밍 (10,000행 chunk) — 전체 메모리 로드 금지
- 같은 timestamp의 여러 심볼을 묶어 ccxt `watch_tickers` 포맷으로 변환:
  ```python
  {
    "BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5},
    "ETH/BTC":  {"bid": 0.0666,  "ask": 0.0667,  "last": 0.0666},
    ...
  }
  ```
- 심볼이 부분적으로 없는 타임스탬프도 그대로 전달 (전략이 TTL 캐시로 처리)

---

### 3. BacktestExchange (`exchange.py`)

`ExchangeInterface` 구현. 실제 거래소에 접속하지 않음.

**내부 상태:**
```python
_balance: dict[str, Decimal]  # {"USDT": 1000, "BTC": 0, "ETH": 0, ...}
_prices: dict[TradingPair, tuple[Decimal, Decimal]]  # (bid, ask)
```

**`update_prices(tickers)`**: BacktestRunner가 on_tickers 직전에 호출해 현재가 캐시를 갱신.

**`place_order(order) → OrderResult`:**
- BUY: 체결가 = `ask × (1 + slippage)`. quote 잔고 차감, base 잔고 증가.
- SELL: 체결가 = `bid × (1 − slippage)`. base 잔고 차감, quote 잔고 증가.
- 잔고 부족 시 `InsufficientFunds` 예외 (언윈드 로직은 기존 state machine이 처리)
- 슬리피지 기본값: `0.0005` (0.05%)

**기타 메서드:** `subscribe_ticker()`, `cancel_order()`, `close()` → no-op. `health_check()` → `True`.

---

### 4. BacktestRunner (`runner.py`)

```python
class BacktestRunner:
    async def run(self, start: datetime, end: datetime) -> list[TradeRecord]:
        async for tickers in self._feed.stream(start, end):
            self._exchange.update_prices(tickers)
            self._engine.update_prices(_extract_usdt_prices(tickers))  # RiskManager용
            signals = self._strategy.on_tickers(tickers)
            for signal in signals:
                await self._engine.on_signal(signal)
                self._drain_outbox()  # 완료된 거래를 즉시 수집
        return self._trade_records
```

**거래 기록 수집:** `on_signal()` await 직후 `_outbox`(asyncio.Queue)를 drain해 TRADE_RESULT 항목을 `TradeRecord`로 변환·축적. 상태 머신은 `start()` 내부에서 동기적으로 `_enqueue_outbox()`를 호출하므로 drain 타이밍이 보장됨.

```python
@dataclass(frozen=True, kw_only=True)
class TradeRecord:
    timestamp: datetime
    arb_id: str
    leg1_pair: TradingPair
    leg2_pair: TradingPair
    leg3_pair: TradingPair
    expected_profit: Decimal
    actual_profit: Decimal | None
    status: str  # COMPLETE | UNWIND_COMPLETE | TIMEOUT | FAILED
```

---

### 5. BacktestReport (`report.py`)

**터미널 출력:**
```
=== Backtest: 2025-03-01 → 2025-05-31 ===
초기 잔고:   1000.00 USDT
최종 잔고:   1032.15 USDT
총 PnL:     +32.15 USDT (+3.22%)
거래 수:     47  (COMPLETE 38 / UNWIND 7 / TIMEOUT 2)
승률:        80.9%
평균 수익:  +0.85 USDT/거래
최대 낙폭:  -2.10 USDT
```

**CSV 컬럼:**
`timestamp, arb_id, leg1_pair, leg2_pair, leg3_pair, expected_profit, actual_profit, status`

---

## Execution Flow

```
run_backtest.py --start S --end E --fetch --qty Q --initial-balance B --output out.csv
  │
  ├─ [--fetch 플래그] BinanceVisionFetcher.fetch(S, E)
  │    └─ raw_ticks 적재
  │
  └─ BacktestRunner.run(S, E)
       ├─ HistoricalFeed.stream(S, E)  → tickers (1초 간격)
       ├─ BacktestExchange               가상 체결
       ├─ TriangularArbitrageStrategy    시그널 생성 (기존 코드)
       ├─ ExecutionEngine + StateMachine 실행 (기존 코드)
       └─ BacktestReport                 출력
```

---

## CLI Interface

```bash
# 1단계: 데이터 취득 (최초 1회, 이후 재실행 시 skip)
python run_backtest.py --start 2025-03-01 --end 2025-05-31 --fetch

# 2단계: 백테스트 실행 (DB에 데이터 있어야 함)
python run_backtest.py --start 2025-03-01 --end 2025-05-31 \
  --qty 0.001 \
  --initial-balance 1000 \
  --min-profit 0.002 \
  --output results.csv

# 한 번에 (취득 + 실행)
python run_backtest.py --start 2025-03-01 --end 2025-05-31 --fetch \
  --qty 0.001 --output results.csv
```

---

## Data Volume Estimate

| 항목 | 수치 |
|------|------|
| 기간 | 90일 |
| 심볼 수 | 9 |
| 다운샘플 후 rows/day/symbol | 86,400 (1초 1행) |
| 총 rows | ~70M |
| DB 예상 크기 | ~7 GB |
| 다운로드 파일 수 | 810개 zip |
| 예상 다운로드 시간 | ~2분 (20 동시) |

---

## Testing Strategy

| 테스트 | 내용 |
|--------|------|
| `test_fetcher.py` | zip 파싱, 1초 다운샘플, 멱등성 (mock HTTP) |
| `test_feed.py` | DB 스트리밍, tickers 포맷 변환 |
| `test_exchange.py` | BUY/SELL 체결 정확성, 잔고 추적, 잔고 부족 처리 |
| `test_runner.py` | 전체 플로우 통합 (mock feed + mock exchange) |

---

## Constraints

- `DATABASE_URL` 환경 변수 필수 (backtest는 DB 없이 실행 불가)
- Binance Vision은 공개 API — 인증 불필요
- 백테스트 중 실제 거래소 API 호출 없음
- `ArbitrageStateMachine` 타임아웃은 기본값 그대로 사용 (BacktestExchange가 즉시 응답하므로 타임아웃 발생하지 않음)
