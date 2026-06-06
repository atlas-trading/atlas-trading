# Atlas Trading — TODO

설계 스펙: [docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md](docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md)

PR은 작은 단위로 쪼개어 직접 리뷰 후 머지.

---

## Phase 1: 삼각 차익거래 MVP ✅ 완료

### core-platform

- [x] **EventBus** — asyncio in-process pub/sub (`events/bus.py`)
- [x] **ExchangeInterface + Order 타입** — ccxt 기반 추상화 (`exchange/`, `execution/`)
- [x] **BinanceAdapter** — WebSocket 티커 구독 + 주문 실행 (`exchange/binance.py`)
- [x] **MarketDataFeed** — raw → normalize → EventBus 발행 (`market/feed.py`)
- [x] **DB 스키마 + 마이그레이션** — `arb_attempts`, `order_records` (SQLAlchemy + asyncpg)
- [x] **OutboxQueue + AlertWorker** — Discord Webhook 알림 (`outbox/`)
- [x] **RiskManager** — USDT 기준 주문 금액 / 노출액 한도 + Kill Switch (`risk/manager.py`)
- [x] **ExecutionEngine** — RiskManager 게이트 → StateMachine 연결 (`execution/engine.py`)
- [x] **ArbitrageStateMachine** — 3-레그 상태 전이, 타임아웃 자동 Unwind (`execution/state.py`)
- [x] **TriangularArbitrageStrategy** — Bellman-Ford 음수 사이클 탐지, 수수료 반영 (`strategy/arbitrage/`)
- [x] **LiveRunner** — 전체 컴포넌트 조립 + 실행 (`live/runner.py`)
- [x] **run_local.py** — Binance Testnet 로컬 실행 스크립트
- [x] **132개 테스트** — 단위 + 통합 (엣지케이스: 부분 체결, 네트워크 에러, 수수료 등)

### api-server

- [x] **FastAPI 스캐폴딩** — PostgreSQL 연결, health check
- [x] **거래 API** — `GET /trades`, `GET /positions`
- [x] **WebSocket 알림** — `WS /ws/alerts`, `POST /internal/alert`

### web-dashboard

- [x] **Vite + React 스캐폴딩** — TypeScript, TailwindCSS
- [x] **거래내역 + 인프라 모니터링 탭**
- [x] **실시간 알림 피드** — `/ws/alerts` WebSocket 연결

---

## 다음 단계: 프로덕션 모니터링

- [ ] **Prometheus + Grafana** — `infrastructure/docker-compose.yml`에 서비스 추가
- [ ] **애플리케이션 메트릭** — `atlas/metrics/prometheus.py` (신호 수, 체결 수, 수익, 레이턴시, 리스크 거부)
- [ ] **Discord 알림 연결** — `alert_queue`를 `ArbitrageStateMachine`에 연결
- [ ] **start.sh** — 인프라 + 엔진 일괄 시작 스크립트

---

## Phase 2: 확장

- [ ] BybitAdapter (`exchange/bybit.py`)
- [ ] BacktestEngine — `HistoricalFeed` (raw_ticks 재생)
- [ ] DBLoggerWorker — bulk insert (raw_ticks, ohlcv)
- [ ] 펀딩피 전략 (`strategy/funding_rate/`)
- [ ] 자본 사전 배치 기반 크로스 익스체인지 아비트라지

---

## 인프라 (완료)

- [x] k3d + ArgoCD GitOps 파이프라인
- [x] GitHub Actions CI/CD (linux/arm64, ghcr.io)
- [x] Blue-Green 배포
- [x] Sealed Secrets
- [x] macOS LaunchAgents 영구 port-forward
