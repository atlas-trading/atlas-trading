# Kalshi 구조적 차익거래 봇 설계

날짜: 2026-08-01
상태: 승인됨 (구현 진행)

## 목표

Kalshi 예측시장 내부의 구조적 차익 기회를 탐지하고, 데모 환경에서 자동 실행하는
독립 경량 서비스(`kalshi-bot/`)를 만든다. 봇은 환경(`prod`/`demo`) 단위로 일관되게
동작한다 — 탐지와 실행이 같은 환경의 오더북을 본다:
- **측정 모드**: `env=prod` + dry-run. 실마켓 공개 데이터로 기회 빈도·마진 실측 (주문 없음).
- **실행 테스트 모드**: `env=demo` + `--execute`. 데모 마켓 데이터로 탐지하고 데모 계정에 주문.

성공 기준:
- 공개 API 폴링으로 실마켓에서 차익 후보를 탐지하고 SQLite에 기록한다.
- 수수료 반영 후 순마진 기준으로 진짜 기회만 판정한다.
- 데모 계정에서 N-레그 IOC 주문으로 실행하고 체결 결과를 기록한다.
- 수수료 모델·탐지 로직은 단위 테스트로 검증한다.

비목표 (이번 범위 아님):
- 크로스 플랫폼(Polymarket) 차익, WebSocket 실시간 오더북, 대시보드 UI,
  기존 atlas 인프라(TimescaleDB) 통합.

## 전략

가격은 바이너리 계약 기준 0~$1 (내부 표현은 Decimal 달러).

### S1. 단일 마켓 보완계약 차익
`yes_ask + no_ask < 1 − fees` 이면 YES/NO 동시 매수 → 정산 시 무조건 $1 수령.
Kalshi 오더북은 YES/NO가 한 북의 양면(no_ask = 1 − yes_bid)이라 정상 상태에서는
발생하지 않지만, 탐지 비용이 없으므로 이상 상태 감지용으로 유지한다.

### S2. 멀티아웃컴 NO 바스켓 차익 (핵심, 자동 실행 대상)
`mutually_exclusive=true` 인 이벤트의 활성 마켓 N개(N≥2)에 대해:

```
Σ no_ask_i < (N−1) × 1 − Σ fee(no_ask_i)
```

이면 전 마켓 NO 매수. 상호배타성에 의해 최대 1개만 YES 정산 → 최소 (N−1)개의
NO가 각 $1 지급. 이벤트가 전수적(exhaustive)이지 않아 아무 아웃컴도 안 터지면
N개 전부 지급되므로 오히려 이득 — **상호배타성만으로 하방이 보장된다.**

### S3. 멀티아웃컴 YES 합 괴리 (기록만, 실행 금지)
`Σ yes_ask_i < 1` 인 경우. 무위험이 되려면 이벤트가 전수적이어야 하는데
(아무 아웃컴도 안 터지면 YES 전량 손실), API `mutually_exclusive` 플래그는
전수성을 보장하지 않는다. 후보로 기록만 하고 자동 실행하지 않는다.

### 수수료 모델
Kalshi taker 수수료 (계약당, 달러): `ceil_to_cent(0.07 × P × (1−P))`.
maker 계수는 0.0175이지만 IOC로 유동성을 소모하므로 항상 taker 기준으로 판정.
계수는 설정으로 분리한다(일부 시리즈는 다른 계수 사용 가능).

### 판정 임계값
- 순마진(수수료 차감 후) ≥ 계약당 $0.01 (설정 가능)
- 실행 가능 수량 = 전 레그의 레벨1 호가 잔량 최소값 (MVP는 레벨1만 사용)

## 검증된 API 사실 (2026-08-01 실호출 확인)

- 공개 데이터 (인증 불필요, prod): `https://api.elections.kalshi.com/trade-api/v2`
  - `GET /events?status=open&with_nested_markets=true&limit=200&cursor=...`
    → 이벤트별 `mutually_exclusive`(bool)와 중첩 마켓 스냅샷
    (`yes_bid_dollars`, `yes_ask_dollars`, `no_bid_dollars`, `no_ask_dollars`,
    `yes_ask_size_fp` 등 달러 문자열 / fp 문자열)
  - `GET /markets/{ticker}/orderbook` → `orderbook_fp.yes_dollars / no_dollars`:
    각 사이드의 **매수 호가** [가격, 잔량] 배열 (잔량은 소수 계약 지원)
- 거래 (RSA 인증): demo `https://demo-api.kalshi.co/trade-api/v2`
  (`external-api.demo.kalshi.co` 별칭 확인), prod `https://external-api.kalshi.com/trade-api/v2`
- 인증: 헤더 `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`(ms),
  `KALSHI-ACCESS-SIGNATURE` = RSA-PSS(SHA256, MGF1-SHA256, salt=digest length)로
  `"{timestamp_ms}{METHOD}{path}"` 서명 후 base64. 경로는 쿼리스트링 제외.
- 주문 (V2, 레거시 `/portfolio/orders`는 2026-05-06 이후 폐기 예정):
  `POST /portfolio/events/orders`
  - `ticker`, `side`("bid"=YES 매수 / "ask"=YES 매도=NO 매수), `count`(문자열, 소수 2자리),
    `price`(달러 문자열, YES 가격 공간), `time_in_force`("immediate_or_cancel" 지원),
    `self_trade_prevention_type`, `client_order_id`(멱등키)
  - NO를 p에 매수 = `side="ask", price=str(1−p)`
  - 응답: `order_id`, `fill_count`, `remaining_count`, `average_fill_price`, `average_fee_paid`

## 아키텍처

```
kalshi-bot/
  pyproject.toml            # uv, requires-python >=3.12, aiohttp, pytest, ruff
  kalshi_bot/
    config.py               # BotConfig (env 로딩: KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH, ...)
    models/                 # frozen kw_only dataclass: MarketQuote, EventSnapshot,
                            #   Opportunity, OrderRequest, OrderResult
    fees.py                 # taker_fee(price, count) — ceil_to_cent(coef × P × (1−P)) × count
    client/
      public.py             # KalshiPublicClient: list_open_events(), get_orderbook()
      auth.py               # RsaRequestSigner
      trading.py            # KalshiTradingClient: create_order() (V2)
    scanner.py              # detect(event) → list[Opportunity] (S1/S2/S3)
    executor.py             # NO 바스켓 N-레그 IOC 실행, 부분체결 시 잔여 레그 1회 재시도
                            #   → 여전히 미체결이면 체결분 반대매도(IOC)로 언와인드 후 기록
    store.py                # SQLite: opportunities / orders 테이블
    runner.py               # 폴링 루프 (기본 dry-run; --execute 시 데모 주문)
  tests/
```

데이터 흐름: `runner` → `public.list_open_events()` → `scanner.detect()`
→ (dry-run) `store` 기록 / (--execute) `executor` → `trading.create_order()` → `store`.

기회 판정은 이벤트 스냅샷의 레벨1 가격으로 하되, 실행 직전 오더북을 재조회해
잔량·가격을 재확인한다(폴링 지연 대비 이중 확인).

## 리스크 처리

- **레그 리스크**: 전 레그 IOC 지정가 동시 발주. 부분 체결 시 잔여 레그 1회 재시도,
  실패 시 체결분을 IOC로 언와인드하고 손실 기록. (S2는 레그 일부만 체결돼도
  방향성 노출일 뿐 즉시 파산 리스크는 아님 — 언와인드 비용만 부담)
- **가짜 기회**: 수수료 반영 순마진 임계값 + 레벨1 잔량 확인 + 실행 직전 재확인.
- **자금 한도**: 기회당 최대 계약 수(기본 10), 총 노출 한도(기본 $100) 설정.
- **레이트리밋**: 폴링 주기 기본 5초, 이벤트 페이지네이션 200개/페이지,
  429 응답 시 지수 백오프.

## 테스트 계획

- `fees.py`: 공식·반올림 경계값 (P=0.50 → $0.0175/계약 → ceil $0.02 등)
- `scanner.py`: 합성 이벤트 스냅샷으로 S1/S2/S3 판정, 수수료 경계, 수량 산정
- `executor.py`: 모킹된 트레이딩 클라이언트로 전체 체결 / 부분 체결 / 언와인드 경로
- `client/auth.py`: 고정 키·타임스탬프로 서명 문자열 구성 검증
- 스모크: 실제 공개 API 1회 호출로 파싱 검증 (네트워크 테스트는 마커 분리)
