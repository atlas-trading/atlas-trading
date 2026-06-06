# 아키텍처 설계

## 시스템 개요

Atlas Trading은 asyncio 기반 이벤트 드리븐 아키텍처(EDA)로 구성된 암호화폐 자동매매 플랫폼입니다.
전략과 실행 엔진은 이벤트만 처리하며, 이벤트 소스가 라이브인지 백테스트인지 알지 못합니다.

## 컴포넌트 구조

```
core-platform/
├── events/          EventBus — asyncio in-process pub/sub
├── core/            공통 타입 (TradingPair, Ticker, Quote, Exchange)
├── exchange/        ExchangeInterface + BinanceAdapter (ccxt 기반)
├── market/          MarketDataFeed — WebSocket 수신, normalize, 발행
├── risk/            RiskManager — 모든 주문의 동기 게이트
├── strategy/        StrategyBase + TriangularArbitrageStrategy (Bellman-Ford)
├── execution/       ExecutionEngine + ArbitrageStateMachine
├── outbox/          OutboxQueue + AlertWorker (Discord)
├── db/              SQLAlchemy 모델 + 비동기 세션 (arb_attempts, order_records)
└── live/            LiveRunner — 전체 컴포넌트 조립

api-server/          FastAPI — DB 직접 조회, 어드민 HTTP/WS
web-dashboard/       React + Vite — 거래내역, 알림, 인프라 모니터링
```

## 이벤트 흐름

### 핫 패스 (DB I/O 없음)

```
거래소 WebSocket
    │
    ▼
BinanceAdapter.subscribe_ticker()
    │
    ▼
LiveRunner.on_tickers()
    ├─→ ExecutionEngine.update_prices()   RiskManager USDT 가격 캐시 갱신
    ├─→ MarketDataFeed.on_tickers()       raw tick 저장 (비동기, 핫 패스 외)
    └─→ TriangularArbitrageStrategy.on_tickers()

    │ ArbSignal 리스트
    ▼
ExecutionEngine.on_signal()
    ├─→ RiskManager.check()               동기 게이트 (APPROVED / REJECTED)
    └─→ (통과) ArbitrageStateMachine.start()
              ├─→ ExchangeInterface.place_order(leg1)
              ├─→ ExchangeInterface.place_order(leg2)
              ├─→ ExchangeInterface.place_order(leg3)
              └─→ DB 업데이트 (arb_attempts, order_records)
```

### 아웃박스 워커 (별도 asyncio task)

```
OutboxQueue (asyncio.Queue)
    └─→ AlertWorker   Discord Webhook → COMPLETE, UNWIND_COMPLETE, FAILED 시 알림
```

사이드 이펙트 워커 실패는 트레이딩에 영향을 주지 않습니다.

> **미구현**: DBLoggerWorker (bulk insert for raw_ticks/ohlcv) — Phase 2 예정

## 삼각 차익거래 상태 머신

```
IDLE
  │ ArbSignal 수신 + RiskManager 통과
  ▼
LEG1_PENDING ──timeout(500ms)──→ IDLE
  │ 체결
  ▼
LEG1_FILLED
  │
  ▼
LEG2_PENDING ──timeout(300ms)──→ UNWINDING (Leg1 청산) ──→ UNWIND_COMPLETE ──→ IDLE
  │ 체결
  ▼
LEG2_FILLED
  │
  ▼
LEG3_PENDING ──timeout(300ms)──→ UNWINDING (Leg2→1 청산) ──→ UNWIND_COMPLETE ──→ IDLE
  │ 체결
  ▼
COMPLETE ──→ IDLE
```

예외 발생 시 남은 레그를 역순으로 Unwind 후 IDLE 복귀. Unwind도 실패하면 `FAILED` DB 기록.

## 수수료 반영 전략

Bellman-Ford 그래프에서 간선 가중치에 수수료를 포함합니다.

```python
fee_cost = -log(1 - taker_fee)   # 0.1% 기준 ≈ 0.0010005

# BUY 간선:  log(ask) + fee_cost
# SELL 간선: -log(bid) + fee_cost
```

음수 사이클 = 수수료 후에도 수익이 나는 차익 기회.

레그 수량 전파는 실제 체결 수량 기준으로 스케일:

```
leg2_qty = signal.leg2_quantity × (leg1.filled / signal.leg1_quantity)
leg3_qty = signal.leg3_quantity × ratio1 × ratio2
```

## RiskManager

모든 주문은 `RiskManager.check(signal)` 를 동기적으로 통과해야 합니다.

```python
RiskManager(max_order_size=Decimal("100"), max_exposure=Decimal("300"))
```

체크 항목:
- 레그별 USDT 환산 주문 금액 ≤ `max_order_size`
- 전체 3-레그 합산 ≤ `max_exposure`
- 거래소 연결 상태 (`set_connected(False)` 시 전체 거부)
- Kill Switch (`set_kill_switch(True)` 시 전체 거부)

USDT 가격은 LiveRunner가 각 틱마다 `update_prices()` 로 갱신합니다.
가격 미캐시 레그는 보수적으로 거부(Fail-Closed).

## 실제 수익 계산

`ArbitrageStateMachine._actual_profit(signal, r1, r2, r3)`:

- SELL로 시작하는 사이클: `start = r1.filled`, `end = r3.filled`
- BUY로 시작하는 사이클: `start = r1.cost`, `end = r3.cost`
- `profit = end - start if start > 0 else Decimal("0")`  (미체결 시 0 반환)

## 데이터 레이어

```
arb_attempts     상태 머신 전체 이력 (status, expected_profit, actual_profit)
order_records    레그별 주문 lifecycle (exchange, symbol, side, quantity)
```

raw_ticks / ohlcv 저장은 Phase 2에서 DBLoggerWorker로 추가 예정.

## 인프라

- **런타임**: Python 3.12, asyncio, uv
- **거래소**: ccxt (BinanceAdapter)
- **DB**: PostgreSQL + TimescaleDB (asyncpg + SQLAlchemy async)
- **컨테이너**: Docker Compose (로컬), k3s + ArgoCD GitOps (프로덕션)
- **모니터링**: Prometheus + Grafana (k3d 클러스터: Tailscale 100.110.86.86)
- **알림**: Discord Webhook (AlertWorker)
