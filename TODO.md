# Atlas Trading — TODO

설계 스펙: [docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md](docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md)

PR은 작은 단위로 쪼개어 직접 리뷰 후 머지.

---

## Phase 1: 삼각 차익거래 MVP

### core-platform

- [ ] **PR #1** — 프로젝트 스캐폴딩
  - `pyproject.toml` (uv, Python 3.12)
  - 패키지 디렉토리 구조
  - base 타입 (`Decimal` 기반 금액, 심볼 타입)

- [ ] **PR #2** — EventBus
  - `events/bus.py`: asyncio pub/sub, `subscribe(event_type)`, `publish(event)`
  - `events/types.py`: `MarketDataEvent`, `SignalEvent`, `FillEvent`, `TradeResultEvent`

- [ ] **PR #3** — ExchangeInterface + Order 타입
  - `exchange/base.py`: `ExchangeInterface` abstract
    - `place_order()`, `cancel_order()`, `get_balance()`, `subscribe_ticker()`
  - `execution/types.py`: `Order`, `Fill`, `Position`, `Side`, `OrderType`

- [ ] **PR #4** — BinanceAdapter (WebSocket)
  - `exchange/binance.py`: ccxt + WebSocket 티커 구독
  - WebSocket 재연결 로직

- [ ] **PR #5** — MarketDataFeed
  - `market/types.py`: `Tick`, `OHLCV`, `OrderBook` (normalized)
  - `market/feed.py`: raw → normalize → `EventBus.publish` + `outbox.put_nowait`
  - DB는 outbox 경유, 핫 패스에 없음

- [ ] **PR #6** — DB 스키마 + 마이그레이션
  - `raw_ticks`, `ohlcv` (TimescaleDB hypertable)
  - `orders`, `arb_attempts`, `trade_results`
  - Alembic 마이그레이션

- [ ] **PR #7** — OutboxQueue + DBLoggerWorker
  - `outbox/queue.py`: `asyncio.Queue` 기반 OutboxQueue
  - `outbox/workers.py`: `DBLoggerWorker` (100ms 배치 bulk insert)

- [ ] **PR #8** — RiskManager
  - `risk/manager.py`: 동기 `check(signal) → RiskDecision`
  - Phase 1 체크: 주문 금액 한도, 총 노출액 한도, 연결 상태, Kill Switch

- [ ] **PR #9** — ExecutionEngine 기본 구조
  - `execution/engine.py`: `on_signal()` → RiskManager → StateMachine 연결

- [ ] **PR #10** — ArbitrageStateMachine
  - `execution/state.py`: 상태 전이 (`IDLE` → `COMPLETE` / `UNWIND_COMPLETE`)
  - 레그별 타임아웃 (LEG1: 500ms, LEG2/3: 300ms)
  - 실패 핸들러 매핑 + 자동 언윈드
  - 상태 전이 직후 `outbox.put_nowait()`

- [ ] **PR #11** — TriangularArbitrageStrategy: 기회 탐지
  - `strategy/arbitrage/triangular.py`
  - Bellman-Ford로 음수 사이클 탐지
  - 수수료 반영 스프레드 계산

- [ ] **PR #12** — TriangularArbitrageStrategy: 시그널 생성
  - `SignalEvent` 발행 (레그 경로, 예상 수익, 주문 크기 포함)

- [ ] **PR #13** — AlertWorker
  - `outbox/workers.py`: `AlertWorker` — Discord Webhook
  - `TRADE_COMPLETE`, `UNWIND_COMPLETE`, `FAILED` 이벤트 시 알림

- [ ] **PR #14** — LiveRunner + 통합 테스트
  - `live/runner.py`: 모든 컴포넌트 조립 + 시작/종료 관리
  - 통합 테스트: mock exchange로 전체 흐름 검증

### api-server

- [ ] **PR #15** — FastAPI 스캐폴딩
  - `pyproject.toml`, PostgreSQL 연결 (SQLAlchemy async)
  - Health check 엔드포인트

- [ ] **PR #16** — 어드민 API
  - `GET /trades` — 거래내역
  - `GET /positions` — 현재 오픈 포지션
  - `GET /risk/summary` — RiskManager 상태
  - `GET /strategies`, `POST /strategies/{id}/toggle`

- [ ] **PR #17** — WebSocket 알림
  - `WS /ws/alerts` — AlertWorker 아웃박스 구독 → 클라이언트 push

### web-dashboard

- [ ] **PR #18** — Vite + React 스캐폴딩
  - TypeScript, TailwindCSS
  - 라우팅 구조

- [ ] **PR #19** — 거래내역 테이블
  - `/trades` API 연동
  - 페이지네이션, 상태별 필터

- [ ] **PR #20** — 실시간 알림 피드
  - `/ws/alerts` WebSocket 연결
  - 토스트 / 피드 UI

---

## Phase 2: 확장

- [ ] BybitAdapter (`exchange/bybit.py`)
- [ ] BacktestEngine — `HistoricalFeed` (raw_ticks 재생)
- [ ] 펀딩피 전략 (`strategy/funding_rate/`)
- [ ] 자본 사전 배치 기반 크로스 익스체인지 아비트라지
- [ ] 데이터 분석 / DW 연동

---

## 인프라 (기존 완료)

- [x] k3d + ArgoCD GitOps 파이프라인
- [x] GitHub Actions CI/CD (linux/arm64, ghcr.io)
- [x] Blue-Green 배포
- [x] Sealed Secrets
- [x] Prometheus + Grafana 모니터링
- [x] macOS LaunchAgents 영구 port-forward
