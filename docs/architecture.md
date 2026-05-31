# 아키텍처 설계

## 시스템 개요

Atlas Trading은 asyncio 기반 이벤트 드리븐 아키텍처(EDA)로 구성된 암호화폐 자동매매 플랫폼입니다.
전략과 실행 엔진은 이벤트만 처리하며, 이벤트 소스가 라이브인지 백테스트인지 알지 못합니다.

## 컴포넌트 구조

```
core-platform/
├── events/          EventBus — asyncio in-process pub/sub
├── exchange/        ExchangeInterface + 거래소 어댑터 (ccxt 기반)
├── market/          MarketDataFeed — WebSocket 수신, normalize, 발행
├── risk/            RiskManager — 모든 주문의 동기 게이트
├── strategy/        StrategyBase + 구현체 (삼각 차익거래 등)
├── execution/       ExecutionEngine + ArbitrageStateMachine
├── outbox/          OutboxQueue + 워커 (DBLogger, Alert)
├── backtest/        BacktestEngine — HistoricalFeed로 이벤트 재생
└── live/            LiveRunner — 전체 컴포넌트 조립

api-server/          FastAPI — DB 직접 조회, 어드민 HTTP/WS
web-dashboard/       React — 거래내역, 알림, 전략 상태
```

## 이벤트 흐름

### 핫 패스 (DB I/O 없음)

```
거래소 WebSocket
    │
    ▼
MarketDataFeed
    ├─→ EventBus.publish(MarketDataEvent)    in-memory, 즉시
    └─→ outbox.put_nowait(raw, normalized)   fire-and-forget

    │ MarketDataEvent
    ▼
StrategyBase.on_market_data()
    └─→ 기회 감지 시 EventBus.publish(SignalEvent)

    │ SignalEvent
    ▼
ExecutionEngine.on_signal()
    ├─→ RiskManager.check()                  동기 게이트
    └─→ (통과) ArbitrageStateMachine
              ├─→ ExchangeInterface.place_order(leg)
              └─→ outbox.put_nowait(OutboxEntry)   핵심 로직 완료 직후
```

### 아웃박스 워커 (별도 asyncio task)

```
OutboxQueue
    ├─→ DBLoggerWorker   bulk insert → raw_ticks, ohlcv, orders, arb_attempts
    └─→ AlertWorker      Discord/Telegram → TRADE_COMPLETE, UNWIND 이벤트 시
```

사이드 이펙트 워커 실패는 트레이딩에 영향을 주지 않습니다.

## 삼각 차익거래 상태 머신

```
IDLE
  │ 기회 감지 + RiskManager 통과
  ▼
OPPORTUNITY_VALIDATED
  │
  ▼
LEG1_PENDING ──timeout/거절──→ IDLE
  │ 체결
  ▼
LEG1_FILLED
  │
  ▼
LEG2_PENDING ──실패──→ UNWINDING (Leg1 청산) ──→ UNWIND_COMPLETE
  │ 체결
  ▼
LEG2_FILLED
  │
  ▼
LEG3_PENDING ──실패──→ UNWINDING (Leg2→1 청산) ──→ UNWIND_COMPLETE
  │ 체결
  ▼
COMPLETE
```

UNWIND도 실패 시 `FAILED` 상태 → 자동 거래 중단 + 사람 개입 알림.

## RiskManager

모든 주문은 `RiskManager.check(signal)` 를 동기적으로 통과해야 합니다.

Phase 1 체크:
- 최대 단일 주문 금액
- 총 노출액 한도
- 거래소 연결 상태
- Kill Switch (Redis 플래그)

## Backtest / Live 통합

```python
# Live
LiveRunner(feed=WebSocketFeed(BinanceAdapter()), strategy=TriangularArb())

# Backtest — 동일한 전략 코드 사용
BacktestRunner(feed=HistoricalFeed(db, start, end), strategy=TriangularArb())
```

## 데이터 레이어

```
raw_ticks          WebSocket raw 메시지 (불변, append-only)
ohlcv              Normalized OHLCV (TimescaleDB hypertable)
orders             주문 lifecycle
arb_attempts       상태 머신 전체 이력
trade_results      완료된 거래 결과 + PnL
```

raw → normalized는 단방향. raw 재생으로 언제든 재계산 가능.

## 인프라

- **런타임**: Python 3.12, asyncio
- **거래소**: ccxt (BinanceAdapter, BybitAdapter)
- **DB**: PostgreSQL + TimescaleDB
- **캐시/Kill Switch**: Redis
- **컨테이너**: Docker (linux/arm64, Mac Mini M1)
- **오케스트레이션**: k3s + ArgoCD GitOps
- **모니터링**: Prometheus + Grafana (Tailscale: 100.110.86.86)
- **알림**: Discord Webhook
