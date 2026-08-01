# kalshi-bot

Kalshi 예측시장 구조적 차익거래 봇. 설계 문서:
[`docs/superpowers/specs/2026-08-01-kalshi-arb-bot-design.md`](../docs/superpowers/specs/2026-08-01-kalshi-arb-bot-design.md)

## 전략

| 종류 | 조건 | 자동 실행 |
|---|---|---|
| `single_market_complement` | YES ask + NO ask < $1 − 수수료 | O |
| `no_basket` | 상호배타 이벤트에서 Σ NO ask < (N−1) − 수수료 | O |
| `yes_sum_anomaly` | Σ YES ask < $1 − 수수료 | X (전수성 미보장 → 기록만) |

## 실행

```bash
cd kalshi-bot
uv sync --extra dev

# 측정 모드: prod 공개 데이터 1회 스캔, 기록만 (주문 없음)
uv run python -m kalshi_bot.runner --env prod --once

# 상시 폴링 (기본 5초 간격)
uv run python -m kalshi_bot.runner --env prod

# 실행 테스트: demo 계정에 실제 주문 (demo에서만 허용)
KALSHI_API_KEY_ID=... KALSHI_PRIVATE_KEY_PATH=... \
  uv run python -m kalshi_bot.runner --env demo --execute
```

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `KALSHI_ENV` | `prod` | `prod` / `demo` |
| `KALSHI_API_KEY_ID` | — | 주문 시 필수 |
| `KALSHI_PRIVATE_KEY_PATH` | — | RSA private key PEM 경로 |
| `KALSHI_DB_PATH` | `kalshi_bot.sqlite3` | 기회·주문 기록 SQLite |
| `KALSHI_POLL_INTERVAL` | `5` | 폴링 주기 (초) |
| `KALSHI_MIN_NET_EDGE` | `0.01` | 계약당 최소 순마진 ($) |
| `KALSHI_MAX_COUNT` | `10` | 기회당 최대 계약 수 |
| `KALSHI_MAX_EXPOSURE` | `100` | 누적 체결 비용 한도 ($) |
| `KALSHI_FEE_COEF` | `0.07` | taker 수수료 계수 |

## 테스트

```bash
uv run pytest              # 단위 테스트 (네트워크 제외)
uv run pytest -m network   # 실서버 공개 API 스모크
uv run ruff check .
```
