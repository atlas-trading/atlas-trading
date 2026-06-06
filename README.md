# Atlas Trading

오픈소스 암호화폐 자동매매 / 자산관리 플랫폼.

거래소 API를 인터페이스로 추상화하여 어댑터만 추가하면 새 거래소를 지원합니다.
Mac Mini 홈서버를 1차 타겟으로 설계되었습니다.

## 아키텍처

```
atlas-trading/
├── core-platform/      트레이딩 엔진 (Python asyncio, EDA)
├── api-server/         FastAPI 어드민 서버
├── web-dashboard/      React 어드민 대시보드
├── cluster-config/     K8s / ArgoCD
├── infrastructure/     PostgreSQL + TimescaleDB docker-compose
└── docs/
```

### 핵심 설계 원칙

- **핫 패스 DB-free**: 전략 실행 경로에 DB I/O 없음. WebSocket → EventBus → 전략 → 주문이 in-memory로 흐름
- **아웃박스 패턴**: 로깅 / 알림 등 사이드 이펙트는 핵심 로직 완료 후 아웃박스 워커가 처리
- **RiskManager 게이트**: 모든 주문은 RiskManager를 반드시 통과. 우회 불가
- **Backtest = Live**: 이벤트 소스만 다를 뿐 전략과 실행 엔진은 동일한 코드
- **데이터 불변성**: raw 데이터는 append-only. normalized는 raw에서 파생

## 삼각 차익거래 StateMachine

삼각 차익거래(A→B→C→A) 실행 흐름. 각 레그는 타임아웃 내 미체결 시 자동 청산(Unwind).

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> LEG1_PENDING : 차익 신호 수신

    LEG1_PENDING --> LEG1_FILLED : 체결
    LEG1_PENDING --> IDLE : 타임아웃(500ms) / 거부

    LEG1_FILLED --> LEG2_PENDING : LEG2 주문 전송

    LEG2_PENDING --> LEG2_FILLED : 체결
    LEG2_PENDING --> UNWINDING : 타임아웃(300ms) / 거부\n→ LEG1 청산

    LEG2_FILLED --> LEG3_PENDING : LEG3 주문 전송

    LEG3_PENDING --> COMPLETE : 체결
    LEG3_PENDING --> UNWINDING : 타임아웃(300ms) / 거부\n→ LEG2+LEG1 순차 청산

    UNWINDING --> UNWIND_COMPLETE : 청산 완료
    COMPLETE --> IDLE : 다음 사이클 대기
    UNWIND_COMPLETE --> IDLE : 다음 사이클 대기

    note right of LEG1_PENDING : RiskManager 통과 후 주문
    note right of UNWINDING : 남은 레그를 역순으로 청산\n실패 시에도 IDLE 복귀
```

## 전략 로드맵

| 단계 | 전략 | 상태 |
|------|------|------|
| Phase 1 | 삼각 차익거래 (Bellman-Ford) | **구현 완료** |
| Phase 2 | 펀딩피 수익화 | 예정 |
| Phase 3 | 옵션 매매 | 예정 |

## 시작하기

### 의존성 설치

```bash
cd core-platform
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 테스트 실행

```bash
cd core-platform
uv run pytest          # 132개 테스트 (단위 + 통합)
uv run ruff check .    # 린트
```

### 로컬 실행 (Binance Testnet)

```bash
# 인프라 시작 (PostgreSQL)
cd infrastructure
docker compose up -d

# 트레이딩 엔진 실행
cd core-platform
BINANCE_TESTNET_API_KEY=<key> \
BINANCE_TESTNET_API_SECRET=<secret> \
DATABASE_URL=postgresql+asyncpg://atlas:atlas@localhost:5432/atlas \
DISCORD_WEBHOOK=<optional> \
uv run python run_local.py
```

주요 환경변수:
| 변수 | 필수 | 설명 |
|------|------|------|
| `BINANCE_TESTNET_API_KEY` | ✅ | Binance testnet API 키 |
| `BINANCE_TESTNET_API_SECRET` | ✅ | Binance testnet API secret |
| `DATABASE_URL` | 선택 | PostgreSQL URL (없으면 DB 저장 생략) |
| `DISCORD_WEBHOOK` | 선택 | Discord 알림 webhook URL |
| `ORDER_QUANTITY` | 선택 | 레그당 주문량 (기본: 0.001 BTC) |
| `MIN_PROFIT` | 선택 | 최소 수익 임계값 (기본: 0.5%) |
| `VERBOSE` | 선택 | 상세 로그 출력 (기본: 1) |

## 문서

- [아키텍처 설계](docs/architecture.md)
- [시스템 설계 스펙](docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md)
- [운영 가이드](docs/runbook.md)
- [보안 정책](docs/security.md)
- [모니터링](docs/MONITORING.md)

## 보안

- API 키는 Kubernetes Sealed Secrets로 관리 (평문 금지)
- 거래소 API 키에 출금 권한 절대 부여 금지
- RiskManager Kill Switch: `set_kill_switch(True)` 호출로 전체 거래 즉시 중단
- Fail-Closed: 불확실하면 거래 중단

---

**주의**: 이 시스템은 실제 자금을 다룹니다. 충분한 검증 없이 실전 운용을 절대 금지합니다.
