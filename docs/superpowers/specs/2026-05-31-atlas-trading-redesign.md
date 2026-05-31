# Atlas Trading — System Design Spec

**Date:** 2026-05-31  
**Status:** Approved

---

## Goals

오픈소스 자동매매 / 자산관리 플랫폼.

- 다양한 거래소/증권사 API를 인터페이스로 추상화 — 새 거래소는 어댑터만 추가
- 전략 설정 단순화
- Crypto 특화 전략: 삼각 차익거래 → 펀딩피 → 옵션 매매
- Mac Mini 홈서버 유저를 1차 타겟으로 설계

---

## Architecture Overview

```
core-platform/      트레이딩 엔진 (단일 프로세스, asyncio)
api-server/         FastAPI 어드민 서버 (read-mostly, DB 직접 조회)
web-dashboard/      React 어드민 대시보드
cluster-config/     K8s / ArgoCD (기존 유지)
infrastructure/     PostgreSQL + TimescaleDB, Redis, Prometheus
```

**핵심 원칙:**
- `core-platform`이 모든 비즈니스 로직을 소유. `api-server`는 그 결과를 HTTP로 노출하는 얇은 레이어.
- 실행 경로(핫 패스)에 DB I/O 없음.
- 로깅 / 알림 등 모든 사이드 이펙트는 아웃박스를 통해 핫 패스 이후에 처리.
- RiskManager는 모든 주문 전 동기 게이트. 우회 불가.
- 데이터는 raw와 normalized를 모두 보존. raw는 불변.

---

## Module Structure

```
core-platform/
├── events/
│   ├── bus.py          # EventBus (asyncio, in-process pub/sub)
│   └── types.py        # 모든 이벤트 타입 정의
│
├── exchange/
│   ├── base.py         # ExchangeInterface (abstract)
│   ├── binance.py      # BinanceAdapter
│   └── bybit.py        # BybitAdapter
│
├── market/
│   ├── types.py        # Tick, OHLCV, OrderBook (normalized 타입)
│   └── feed.py         # MarketDataFeed (WebSocket → EventBus + Outbox)
│
├── risk/
│   └── manager.py      # RiskManager (동기 게이트)
│
├── strategy/
│   ├── base.py         # StrategyBase (abstract)
│   └── arbitrage/
│       └── triangular.py  # TriangularArbitrageStrategy (Bellman-Ford)
│
├── execution/
│   ├── types.py        # Order, Fill, Position 타입
│   ├── engine.py       # ExecutionEngine
│   └── state.py        # ArbitrageStateMachine
│
├── outbox/
│   ├── queue.py        # OutboxQueue (in-memory asyncio.Queue)
│   └── workers.py      # DBLoggerWorker, AlertWorker
│
├── backtest/
│   └── engine.py       # BacktestEngine (HistoricalFeed → 동일 이벤트 재생)
│
└── live/
    └── runner.py       # LiveRunner (모든 컴포넌트 조립)
```

---

## Event Flow

### 핫 패스 (전략 실행 경로 — DB I/O 없음)

```
[거래소 WebSocket]
       │
       ▼
 MarketDataFeed.on_message(raw)
  ├─ normalized = normalize(raw)
  ├─ EventBus.publish(MarketDataEvent(normalized))   ← in-memory, 즉시
  └─ outbox.put_nowait((raw, normalized))             ← fire-and-forget

       │ MarketDataEvent
       ▼
 StrategyBase.on_market_data(event)
  └─ 기회 감지 시 → EventBus.publish(SignalEvent)

       │ SignalEvent
       ▼
 ExecutionEngine.on_signal(signal)
  ├─ RiskManager.check(signal)   ← 동기 게이트, 실패 시 즉시 중단
  └─ 통과 시 → ArbitrageStateMachine.on_signal(signal)
                  └─ ExchangeInterface.place_order(leg)
                  └─ outbox.put_nowait(OutboxEntry(...))  ← 핵심 로직 직후
```

### 아웃박스 워커 (별도 asyncio task — 사이드 이펙트)

```
OutboxQueue
  ├─ DBLoggerWorker    → bulk insert (raw_ticks, ohlcv, orders, arb_attempts)
  └─ AlertWorker       → Discord/Telegram 알림 (TRADE_COMPLETE, UNWIND 시)
```

**원칙:** 아웃박스 `put_nowait`은 핵심 로직 완료 직후 동기적으로 호출 (같은 이벤트 루프 틱). 워커 실패는 트레이딩에 영향 없음.

---

## Arbitrage State Machine

삼각 차익거래 실행 상태:

```
IDLE
  │ 기회 감지 + RiskManager 통과
  ▼
OPPORTUNITY_VALIDATED
  │ Leg 1 주문 전송
  ▼
LEG1_PENDING ──timeout/거절──────────────────────────→ IDLE
  │ Leg 1 체결
  ▼
LEG1_FILLED
  │ Leg 2 주문 전송
  ▼
LEG2_PENDING ──실패──→ UNWINDING ──→ UNWIND_COMPLETE
  │ Leg 2 체결            (Leg 1 시장가 청산)
  ▼
LEG2_FILLED
  │ Leg 3 주문 전송
  ▼
LEG3_PENDING ──실패──→ UNWINDING ──→ UNWIND_COMPLETE
  │ Leg 3 체결            (Leg 2→1 순차 청산)
  ▼
COMPLETE
```

**타임아웃:**
```python
LEG_TIMEOUT_MS = {
    "LEG1_PENDING": 500,
    "LEG2_PENDING": 300,  # 노출 있으므로 더 짧게
    "LEG3_PENDING": 300,
}
```

**실패 핸들러 매핑:**
```python
UNWIND_HANDLERS = {
    ArbitrageState.LEG1_PENDING: unwind_nothing,
    ArbitrageState.LEG1_FILLED:  unwind_leg1,
    ArbitrageState.LEG2_PENDING: unwind_leg1,
    ArbitrageState.LEG2_FILLED:  unwind_leg2_then_leg1,
    ArbitrageState.LEG3_PENDING: unwind_leg2_then_leg1,
}
```

`FAILED` 상태 (언윈드도 실패): 자동 거래 중단 + 사람 개입 알림.

---

## RiskManager Contract

모든 주문은 `RiskManager.check()` 를 동기적으로 통과해야 한다. 우회 불가.

```python
class RiskManager:
    def check(self, signal: Signal) -> RiskDecision:
        """
        Returns: RiskDecision(approved=True) or RiskDecision(approved=False, reason=...)
        Raises: never — 항상 RiskDecision 반환
        """
```

Phase 1 체크 목록:
- 최대 단일 주문 금액 초과 여부
- 현재 총 노출액 한도 초과 여부
- 거래소 연결 상태
- Kill Switch 활성 여부

---

## Data Layer

```sql
-- raw 수신 메시지 (불변, append-only)
raw_ticks (id, exchange, symbol, raw_json, received_at)

-- normalized OHLCV (TimescaleDB hypertable)
ohlcv (time, exchange, symbol, open, high, low, close, volume)

-- 주문 lifecycle
orders (id, arb_id, leg, status, exchange, symbol, side, qty, price, ...)

-- 상태 머신 전체 이력
arb_attempts (id, strategy, state, legs_json, pnl, started_at, ended_at)

-- 완료된 거래 결과
trade_results (id, arb_id, net_pnl, slippage, fees, duration_ms)
```

**원칙:** raw → normalized 는 단방향. raw를 재생하면 언제든 normalized 재계산 가능.

---

## Backtest / Live 통합

전략과 실행 엔진은 이벤트 소스가 무엇인지 모른다.

```python
# Live
LiveRunner(
    feed=WebSocketFeed(exchange=BinanceAdapter()),
    strategy=TriangularArbitrageStrategy(),
)

# Backtest
BacktestRunner(
    feed=HistoricalFeed(db=db, start="2025-01-01", end="2025-12-31"),
    strategy=TriangularArbitrageStrategy(),
)
```

`HistoricalFeed`는 DB의 `raw_ticks`를 시간순으로 재생. 동일한 `MarketDataEvent`를 발행.

---

## API Server

`api-server`는 `core-platform`의 DB를 직접 읽는 얇은 어드민 레이어.

```
GET  /trades                  거래내역 (trade_results)
GET  /positions               현재 오픈 포지션 (arb_attempts 진행 중)
GET  /risk/summary            RiskManager 현재 설정 + 상태
GET  /strategies              활성 전략 목록 + 설정
POST /strategies/{id}/toggle  전략 활성화/비활성화
WS   /ws/alerts               실시간 거래 알림 (아웃박스 AlertWorker 구독)
```

---

## Phase 1 Scope

### core-platform

| PR | 내용 |
|----|------|
| #1 | 프로젝트 스캐폴딩 (pyproject.toml, 패키지 구조, base 타입) |
| #2 | EventBus 구현 (events/bus.py, events/types.py) |
| #3 | ExchangeInterface abstract base + Order/Fill 타입 |
| #4 | BinanceAdapter — WebSocket 연결 + 메시지 수신 |
| #5 | MarketDataFeed — normalize + EventBus publish + Outbox put |
| #6 | DB 스키마 + TimescaleDB 마이그레이션 |
| #7 | OutboxQueue + DBLoggerWorker |
| #8 | RiskManager — Phase 1 체크 구현 |
| #9 | ExecutionEngine 기본 구조 |
| #10 | ArbitrageStateMachine (상태 전이 + 타임아웃 + 언윈드) |
| #11 | TriangularArbitrageStrategy — Bellman-Ford 기회 탐지 |
| #12 | TriangularArbitrageStrategy — SignalEvent 생성 |
| #13 | AlertWorker (Discord 알림) |
| #14 | LiveRunner — 전체 조립 + 통합 테스트 |

### api-server

| PR | 내용 |
|----|------|
| #15 | FastAPI 스캐폴딩 + DB 연결 |
| #16 | 거래내역 / 포지션 / 리스크 API |
| #17 | WebSocket 알림 엔드포인트 |

### web-dashboard

| PR | 내용 |
|----|------|
| #18 | Vite + React 스캐폴딩 |
| #19 | 거래내역 테이블 |
| #20 | 실시간 알림 피드 |

---

## Phase 2 Scope

- BybitAdapter
- BacktestEngine (HistoricalFeed + replay)
- 펀딩피 전략 (FundingRateStrategy)
- 자본 사전 배치 기반 크로스 익스체인지 아비트라지
- 데이터 분석 / DW 연동
