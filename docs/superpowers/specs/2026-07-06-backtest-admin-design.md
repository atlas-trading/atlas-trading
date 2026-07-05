# Backtest Admin Screen — Design Spec

**Date:** 2026-07-06
**Status:** Approved

## Goal

백테스트 실행 결과를 DB에 영구 저장하고, 기존 web-dashboard에서 실행 이력·요약 지표·거래 내역을 조회할 수 있는 간단한 어드민 화면을 제공한다.

## Background

- 현재 백테스트 결과는 실행 시점의 메모리와 CSV 파일에만 존재한다.
- web-dashboard는 탭 없는 단일 페이지(실시간 알림 + 거래 내역), 순수 `<table>` + Tailwind, 상대경로 fetch + Vite dev proxy 패턴.
- api-server는 pydantic 없이 수동 dict 직렬화, SQLAlchemy async, `atlas.db.models` 재사용(editable path dep).
- DB 마이그레이션은 `core-platform/alembic/`에서 관리 (현재 0002까지).

## Decisions

| 결정 | 선택 | 이유 |
|---|---|---|
| 결과 저장 | 전용 DB 테이블 신설 | 실행 이력 영구 보관, 라이브 데이터(`arb_attempts`)와 분리 |
| 화면 위치 | 기존 web-dashboard에 탭 추가 | 기존 패턴·배포 파이프라인 재사용 |
| 탭 전환 | `useState` (라우터 미도입) | 단일 의존성 추가 없이 최소 구현 |
| 요약 지표 | 저장하지 않고 API에서 계산 | 원본만 저장, 파생값 중복 방지 |
| 차트 | 이번 범위에서 제외 | 차트 라이브러리 미도입 상태, YAGNI |

## Architecture

```
run_backtest.py ──(완료 후 저장)──▶ backtest_runs / backtest_trades (TimescaleDB)
                                          │
api-server: GET /backtests ◀──────────────┤
            GET /backtests/{run_id}/trades┘
                                          │
web-dashboard: [실시간 | 백테스트] 탭 ──▶ BacktestPanel
```

## Components

### 1. DB 스키마 (`core-platform/atlas/db/models.py` + alembic 0003)

**backtest_runs**
| column | type | note |
|---|---|---|
| id | Integer PK autoincrement | |
| start_date | DateTime(timezone=True) | 백테스트 구간 시작 (inclusive) |
| end_date | DateTime(timezone=True) | 구간 끝 (exclusive) |
| initial_balance | Numeric | USDT |
| final_balance | Numeric | USDT |
| order_qty | Numeric | leg1 주문 수량 |
| min_profit | Numeric | 전략 문턱값 |
| slippage | Numeric | BacktestExchange 슬리피지 |
| created_at | DateTime(timezone=True) server_default now | |

**backtest_trades**
| column | type | note |
|---|---|---|
| id | Integer PK autoincrement | |
| run_id | Integer FK → backtest_runs.id | 인덱스 |
| timestamp | DateTime(timezone=True) | 시그널 발생 시각 |
| arb_id | String | |
| leg1_pair / leg2_pair / leg3_pair | String | ccxt 심볼 |
| expected_profit | Numeric | |
| actual_profit | Numeric nullable | net PnL, 미완료 시 NULL |
| status | String | COMPLETE / UNWIND_COMPLETE / TIMEOUT / FAILED |

### 2. 결과 저장 (`core-platform/atlas/backtest/store.py` + `run_backtest.py`)

- `store.py`: `save_run(session_factory, summary, params) -> int` — run + trades를 저장하고 `run_id` 반환. dataclass에 로직을 두지 않는 service 함수.
- `run_backtest.py`: 백테스트 완료 후 항상 저장하고 `run_id`를 터미널에 출력.

### 3. API (`api-server/app/routes/backtests.py`)

- `GET /backtests` — 실행 목록 최신순. 각 항목에 run 컬럼 전체 + 계산된 요약(총 PnL, 거래 수, 승률) 포함. `limit` 쿼리 파라미터 (기본 50).
- `GET /backtests/{run_id}/trades` — 해당 런의 거래 내역 (timestamp 순). 존재하지 않는 run_id는 404.
- 기존 trades.py 패턴 준수: `Depends(get_db)`, 수동 dict 직렬화 (Decimal→str, datetime→isoformat).
- `app/main.py`에 라우터 등록, `web-dashboard/vite.config.ts` proxy에 `/backtests` 추가.

### 4. 화면 (`web-dashboard/src/`)

- `App.tsx`: `useState<'live' | 'backtest'>` 탭 상태. 상단에 탭 버튼 2개, 기존 두 섹션은 'live' 탭으로 이동.
- `api/backtests.ts`: `fetchBacktestRuns()`, `fetchBacktestTrades(runId)` — 기존 trades.ts 패턴.
- `components/BacktestPanel.tsx`: 좌측 실행 목록(기간, PnL, 거래 수) → 선택 시 우측에 요약 카드(총 PnL, 승률, 거래 수, 상태별 카운트) + 거래 테이블. 폴링 없음(마운트/선택 시 1회 fetch).

## Error Handling

- 저장 실패 시 백테스트 결과 자체는 이미 터미널/CSV로 출력된 후이므로, 에러 로그만 남기고 비정상 종료하지 않는다.
- API: 잘못된 run_id → 404. DB 연결 실패는 FastAPI 기본 500.
- 화면: fetch 실패 시 간단한 에러 문구 표시 (기존 TradeTable 패턴 준수).

## Testing

- core-platform: 모델 테이블명 검증(기존 test_models.py 패턴), `save_run` 단위 테스트 (aiosqlite in-memory).
- api-server: 기존 라우터 테스트 패턴 따라 `/backtests` 2개 엔드포인트 테스트.
- web-dashboard: 기존에 컴포넌트 테스트가 없으므로 신규 테스트는 추가하지 않고 수동 확인 (dev 서버 + 로컬 API).

## Out of Scope

- 차트/그래프 (equity curve 등)
- 백테스트 실행 트리거 UI (실행은 CLI로만)
- 인증/권한
