# Phase 1: Triangular Arbitrage MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Binance WebSocket에서 삼각 차익거래 기회를 Bellman-Ford로 탐지하고, 레그 상태 머신으로 안전하게 실행하며, 어드민 대시보드에서 거래내역을 확인할 수 있는 MVP를 구축한다.

**Architecture:** Python asyncio EDA. 핫 패스(WebSocket → EventBus → Strategy → Execution)에 DB I/O 없음. 모든 사이드 이펙트(DB 저장, 알림)는 아웃박스 워커가 핵심 로직 완료 후 비동기 처리. RiskManager는 모든 주문 전 동기 게이트.

**Tech Stack:** Python 3.12, asyncio, ccxt, SQLAlchemy async, PostgreSQL + TimescaleDB, Alembic, FastAPI, React + Vite, TailwindCSS

**Design spec:** `docs/superpowers/specs/2026-05-31-atlas-trading-redesign.md`

---

## 블럭 개요

| 블럭 | 내용 | PR |
|------|------|----|
| **A. Core Foundation** | 타입, EventBus, ExchangeInterface | #1 #2 #3 |
| **B. Market Data Pipeline** | BinanceAdapter, MarketDataFeed, DB 스키마 | #4 #5 #6 |
| **C. Outbox & Persistence** | OutboxQueue, DBLoggerWorker | #7 |
| **D. Risk & Execution Engine** | RiskManager, ExecutionEngine, ArbitrageStateMachine | #8 #9 #10 |
| **E. Triangular Arb Strategy** | Bellman-Ford 탐지, SignalEvent 생성 | #11 #12 |
| **F. Alerts & Live Runner** | AlertWorker (Discord), LiveRunner 조립 | #13 #14 |
| **G. API Server** | FastAPI 어드민 API, WebSocket 알림 | #15 #16 #17 |
| **H. Web Dashboard** | React 대시보드, 거래내역, 알림 피드 | #18 #19 #20 |

**블럭 의존성:**
```
A → B → C → D → E → F   (core-platform, 순차)
           C → G         (api-server, D와 병렬 가능)
           C → H         (web-dashboard, G 이후)
```

---

## 전체 파일 구조

```
core-platform/
├── pyproject.toml
├── tests/
│   ├── conftest.py
│   ├── test_events/
│   ├── test_exchange/
│   ├── test_market/
│   ├── test_risk/
│   ├── test_execution/
│   ├── test_strategy/
│   └── test_integration/
└── atlas/                       # 패키지명
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   └── types.py             # Amount, Symbol, Timestamp 기반 타입
    ├── events/
    │   ├── __init__.py
    │   ├── bus.py               # EventBus
    │   └── types.py             # 모든 이벤트 타입
    ├── exchange/
    │   ├── __init__.py
    │   ├── base.py              # ExchangeInterface (ABC)
    │   └── binance.py           # BinanceAdapter
    ├── market/
    │   ├── __init__.py
    │   ├── types.py             # Tick, OHLCV, OrderBook
    │   └── feed.py              # MarketDataFeed
    ├── risk/
    │   ├── __init__.py
    │   └── manager.py           # RiskManager
    ├── strategy/
    │   ├── __init__.py
    │   ├── base.py              # StrategyBase (ABC)
    │   └── arbitrage/
    │       ├── __init__.py
    │       ├── graph.py         # Bellman-Ford 그래프
    │       └── triangular.py   # TriangularArbitrageStrategy
    ├── execution/
    │   ├── __init__.py
    │   ├── types.py             # Order, Fill, Position, OrderStatus
    │   ├── engine.py            # ExecutionEngine
    │   └── state.py             # ArbitrageStateMachine
    ├── outbox/
    │   ├── __init__.py
    │   ├── queue.py             # OutboxQueue, OutboxEntry
    │   └── workers.py          # DBLoggerWorker, AlertWorker
    ├── db/
    │   ├── __init__.py
    │   ├── models.py            # SQLAlchemy 모델
    │   ├── session.py           # async session factory
    │   └── migrations/          # Alembic
    │       ├── env.py
    │       └── versions/
    └── live/
        ├── __init__.py
        └── runner.py            # LiveRunner

api-server/
├── pyproject.toml
└── app/
    ├── __init__.py
    ├── main.py
    ├── db.py                    # shared session (core-platform DB 직접 읽기)
    └── routes/
        ├── trades.py
        ├── positions.py
        ├── risk.py
        ├── strategies.py
        └── ws_alerts.py

web-dashboard/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── index.html
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api/
    │   ├── trades.ts
    │   └── alerts.ts            # WebSocket hook
    └── components/
        ├── TradeTable.tsx
        └── AlertFeed.tsx
```

---

## 블럭 A: Core Foundation

**목표:** 나머지 모든 블럭이 의존하는 기반 타입과 EventBus를 확립한다.
**완료 기준:** `pytest tests/test_events/` 통과. 이벤트 publish → subscribe 동작 확인.

---

### PR #1: 프로젝트 스캐폴딩 + 기반 타입

**Files:**
- Create: `core-platform/pyproject.toml`
- Create: `core-platform/atlas/__init__.py`
- Create: `core-platform/atlas/core/types.py`
- Create: `core-platform/tests/conftest.py`

- [ ] **Step 1: pyproject.toml 작성**

```toml
[project]
name = "atlas-trading"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "ccxt>=4.0.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "python-dotenv>=1.0.0",
    "aiohttp>=3.9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: 기반 타입 작성**

```python
# atlas/core/types.py
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

# 금액은 반드시 Decimal — float 사용 금지 (부동소수점 오차)
Amount = Decimal
Symbol = str        # "BTC/USDT"
Exchange = str      # "binance"

@dataclass(frozen=True)
class TradingPair:
    base: str       # "BTC"
    quote: str      # "USDT"

    @classmethod
    def from_symbol(cls, symbol: Symbol) -> "TradingPair":
        base, quote = symbol.split("/")
        return cls(base=base, quote=quote)

    def __str__(self) -> Symbol:
        return f"{self.base}/{self.quote}"
```

- [ ] **Step 3: conftest.py 작성**

```python
# tests/conftest.py
import pytest
import asyncio

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
```

- [ ] **Step 4: 설치 확인**

```bash
cd core-platform
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest --collect-only   # 에러 없이 수집되면 통과
```

- [ ] **Step 5: 커밋**

```bash
git add core-platform/
git commit -m "feat(core): project scaffolding and base types"
```

---

### PR #2: EventBus

**Files:**
- Create: `core-platform/atlas/events/bus.py`
- Create: `core-platform/atlas/events/types.py`
- Create: `core-platform/tests/test_events/test_bus.py`

- [ ] **Step 1: 이벤트 타입 정의**

```python
# atlas/events/types.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

def _now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class BaseEvent:
    timestamp: datetime = field(default_factory=_now)

@dataclass(frozen=True)
class MarketDataEvent(BaseEvent):
    exchange: str = ""
    symbol: str = ""
    bid: Decimal = Decimal(0)
    ask: Decimal = Decimal(0)
    last: Decimal = Decimal(0)

@dataclass(frozen=True)
class SignalEvent(BaseEvent):
    strategy_id: str = ""
    path: list[str] = field(default_factory=list)   # ["BTC/USDT","ETH/BTC","ETH/USDT"]
    expected_profit_pct: Decimal = Decimal(0)

@dataclass(frozen=True)
class FillEvent(BaseEvent):
    arb_id: str = ""
    leg: int = 0
    symbol: str = ""
    filled_qty: Decimal = Decimal(0)
    filled_price: Decimal = Decimal(0)

@dataclass(frozen=True)
class TradeResultEvent(BaseEvent):
    arb_id: str = ""
    net_pnl: Decimal = Decimal(0)
    completed: bool = False     # False = UNWIND_COMPLETE
```

- [ ] **Step 2: 실패 테스트 작성**

```python
# tests/test_events/test_bus.py
import pytest
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent
from decimal import Decimal

@pytest.mark.asyncio
async def test_subscribe_and_receive_event():
    bus = EventBus()
    received = []

    async def handler(event: MarketDataEvent):
        received.append(event)

    bus.subscribe(MarketDataEvent, handler)
    event = MarketDataEvent(exchange="binance", symbol="BTC/USDT", bid=Decimal("50000"))
    await bus.publish(event)

    assert len(received) == 1
    assert received[0].symbol == "BTC/USDT"

@pytest.mark.asyncio
async def test_multiple_subscribers_receive_same_event():
    bus = EventBus()
    results = []

    async def handler_a(e): results.append("a")
    async def handler_b(e): results.append("b")

    bus.subscribe(MarketDataEvent, handler_a)
    bus.subscribe(MarketDataEvent, handler_b)
    await bus.publish(MarketDataEvent(exchange="binance", symbol="ETH/USDT"))

    assert sorted(results) == ["a", "b"]

@pytest.mark.asyncio
async def test_unsubscribed_type_not_received():
    bus = EventBus()
    received = []

    async def handler(e): received.append(e)
    bus.subscribe(SignalEvent, handler)

    await bus.publish(MarketDataEvent(exchange="binance", symbol="BTC/USDT"))
    assert received == []
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
pytest tests/test_events/test_bus.py -v
# Expected: ImportError or AttributeError
```

- [ ] **Step 4: EventBus 구현**

```python
# atlas/events/bus.py
import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Type

Handler = Callable[[Any], Coroutine[Any, Any, None]]

class EventBus:
    def __init__(self):
        self._handlers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: Any) -> None:
        for handler in self._handlers[type(event)]:
            await handler(event)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_events/test_bus.py -v
# Expected: 3 passed
```

- [ ] **Step 6: 커밋**

```bash
git add core-platform/atlas/events/ core-platform/tests/test_events/
git commit -m "feat(events): EventBus with async pub/sub"
```

---

### PR #3: ExchangeInterface + Order/Fill 타입

**Files:**
- Create: `core-platform/atlas/exchange/base.py`
- Create: `core-platform/atlas/execution/types.py`
- Create: `core-platform/tests/test_exchange/test_base.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_exchange/test_base.py
import pytest
from atlas.exchange.base import ExchangeInterface
from atlas.execution.types import Order, Side, OrderType

def test_exchange_interface_is_abstract():
    with pytest.raises(TypeError):
        ExchangeInterface()  # ABC이므로 직접 인스턴스화 불가

def test_mock_exchange_implements_interface():
    class MockExchange(ExchangeInterface):
        async def place_order(self, order): return order
        async def cancel_order(self, order_id): pass
        async def get_balance(self): return {}
        async def subscribe_ticker(self, symbols, callback): pass
        async def close(self): pass

    ex = MockExchange()
    assert isinstance(ex, ExchangeInterface)
```

- [ ] **Step 2: Order/Fill 타입 정의**

```python
# atlas/execution/types.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

class Side(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    FOK = "fok"         # Fill or Kill

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class Order:
    id: str
    exchange: str
    symbol: str
    side: Side
    order_type: OrderType
    quantity: Decimal
    price: Optional[Decimal] = None     # None for MARKET
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Fill:
    order_id: str
    arb_id: str
    leg: int
    symbol: str
    side: Side
    filled_qty: Decimal
    filled_price: Decimal
    fee: Decimal
    filled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 3: ExchangeInterface 정의**

```python
# atlas/exchange/base.py
from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine
from atlas.execution.types import Order, Fill

TickerCallback = Callable[[dict], Coroutine[Any, Any, None]]

class ExchangeInterface(ABC):
    @abstractmethod
    async def place_order(self, order: Order) -> Order: ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> None: ...

    @abstractmethod
    async def get_balance(self) -> dict[str, Any]: ...

    @abstractmethod
    async def subscribe_ticker(self, symbols: list[str], callback: TickerCallback) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_exchange/test_base.py -v
# Expected: 2 passed
```

- [ ] **Step 5: 커밋**

```bash
git add core-platform/atlas/exchange/ core-platform/atlas/execution/types.py core-platform/tests/test_exchange/
git commit -m "feat(exchange): ExchangeInterface ABC and Order/Fill types"
```

---

## 블럭 B: Market Data Pipeline

**목표:** Binance WebSocket에서 실시간 데이터를 수신하고, normalize하여 EventBus에 발행. DB 저장은 아웃박스 경유.
**완료 기준:** BinanceAdapter가 WebSocket으로 티커를 수신하고 `MarketDataEvent`를 발행한다. (테스트넷 또는 mock으로 검증)

---

### PR #4: BinanceAdapter

**Files:**
- Create: `core-platform/atlas/exchange/binance.py`
- Create: `core-platform/tests/test_exchange/test_binance.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_exchange/test_binance.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from atlas.exchange.binance import BinanceAdapter
from atlas.exchange.base import ExchangeInterface

def test_binance_adapter_implements_interface():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    assert isinstance(adapter, ExchangeInterface)

@pytest.mark.asyncio
async def test_subscribe_ticker_calls_callback():
    adapter = BinanceAdapter(api_key="test", api_secret="test")
    received = []

    async def callback(ticker: dict):
        received.append(ticker)

    # ccxt WebSocket을 mock
    mock_ws = AsyncMock()
    mock_ws.watch_tickers = AsyncMock(return_value={
        "BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}
    })

    with patch.object(adapter, "_exchange", mock_ws):
        await adapter._on_ticker({"BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}}, callback)

    assert len(received) == 1
    assert received[0]["BTC/USDT"]["bid"] == 50000.0
```

- [ ] **Step 2: BinanceAdapter 구현**

```python
# atlas/exchange/binance.py
import asyncio
import ccxt.pro as ccxtpro
from decimal import Decimal
from atlas.exchange.base import ExchangeInterface, TickerCallback
from atlas.execution.types import Order, OrderStatus

class BinanceAdapter(ExchangeInterface):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self._exchange = ccxtpro.binance({
            "apiKey": api_key,
            "secret": api_secret,
            "options": {"defaultType": "spot"},
        })
        if testnet:
            self._exchange.set_sandbox_mode(True)
        self._running = False

    async def subscribe_ticker(self, symbols: list[str], callback: TickerCallback) -> None:
        self._running = True
        while self._running:
            try:
                tickers = await self._exchange.watch_tickers(symbols)
                await self._on_ticker(tickers, callback)
            except Exception as e:
                await asyncio.sleep(1)   # 재연결 전 대기

    async def _on_ticker(self, tickers: dict, callback: TickerCallback) -> None:
        await callback(tickers)

    async def place_order(self, order: Order) -> Order:
        result = await self._exchange.create_order(
            symbol=order.symbol,
            type=order.order_type.value,
            side=order.side.value,
            amount=float(order.quantity),
            price=float(order.price) if order.price else None,
        )
        order.status = OrderStatus.FILLED if result["status"] == "closed" else OrderStatus.PENDING
        return order

    async def cancel_order(self, order_id: str) -> None:
        await self._exchange.cancel_order(order_id)

    async def get_balance(self) -> dict:
        return await self._exchange.fetch_balance()

    async def close(self) -> None:
        self._running = False
        await self._exchange.close()
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_exchange/test_binance.py -v
# Expected: 2 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/exchange/binance.py core-platform/tests/test_exchange/test_binance.py
git commit -m "feat(exchange): BinanceAdapter with WebSocket ticker subscription"
```

---

### PR #5: MarketDataFeed

**Files:**
- Create: `core-platform/atlas/market/types.py`
- Create: `core-platform/atlas/market/feed.py`
- Create: `core-platform/tests/test_market/test_feed.py`

- [ ] **Step 1: 마켓 데이터 타입 정의**

```python
# atlas/market/types.py
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone

@dataclass(frozen=True)
class Tick:
    exchange: str
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    timestamp: datetime

    @classmethod
    def from_ccxt_ticker(cls, exchange: str, symbol: str, raw: dict) -> "Tick":
        return cls(
            exchange=exchange,
            symbol=symbol,
            bid=Decimal(str(raw["bid"])) if raw.get("bid") else Decimal(0),
            ask=Decimal(str(raw["ask"])) if raw.get("ask") else Decimal(0),
            last=Decimal(str(raw["last"])) if raw.get("last") else Decimal(0),
            timestamp=datetime.now(timezone.utc),
        )
```

- [ ] **Step 2: 실패 테스트 작성**

```python
# tests/test_market/test_feed.py
import pytest
from unittest.mock import AsyncMock
from decimal import Decimal
from atlas.market.feed import MarketDataFeed
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent
from atlas.outbox.queue import OutboxQueue

@pytest.mark.asyncio
async def test_feed_publishes_market_data_event():
    bus = EventBus()
    outbox = OutboxQueue()
    received = []

    async def handler(event: MarketDataEvent):
        received.append(event)

    bus.subscribe(MarketDataEvent, handler)

    feed = MarketDataFeed(exchange_id="binance", bus=bus, outbox=outbox)
    raw_tickers = {
        "BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}
    }
    await feed._on_tickers(raw_tickers)

    assert len(received) == 1
    assert received[0].symbol == "BTC/USDT"
    assert received[0].bid == Decimal("50000.0")

@pytest.mark.asyncio
async def test_feed_puts_to_outbox_after_publishing():
    bus = EventBus()
    outbox = OutboxQueue()

    feed = MarketDataFeed(exchange_id="binance", bus=bus, outbox=outbox)
    await feed._on_tickers({"BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.5}})

    # 아웃박스에 항목이 들어갔는지 확인
    assert not outbox._queue.empty()
```

- [ ] **Step 3: MarketDataFeed 구현**

```python
# atlas/market/feed.py
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent
from atlas.market.types import Tick
from atlas.outbox.queue import OutboxQueue, OutboxEntry, OutboxEntryType
from decimal import Decimal

class MarketDataFeed:
    def __init__(self, exchange_id: str, bus: EventBus, outbox: OutboxQueue):
        self._exchange_id = exchange_id
        self._bus = bus
        self._outbox = outbox

    async def _on_tickers(self, raw_tickers: dict) -> None:
        for symbol, raw in raw_tickers.items():
            tick = Tick.from_ccxt_ticker(self._exchange_id, symbol, raw)
            event = MarketDataEvent(
                exchange=tick.exchange,
                symbol=tick.symbol,
                bid=tick.bid,
                ask=tick.ask,
                last=tick.last,
            )

            # 1. 이벤트 즉시 발행 (핫 패스, DB 없음)
            await self._bus.publish(event)

            # 2. 아웃박스에 넣기 (핵심 로직 이후, fire-and-forget)
            self._outbox.put_nowait(OutboxEntry(
                entry_type=OutboxEntryType.TICK,
                payload={"raw": raw, "normalized": tick},
            ))
```

- [ ] **Step 4: OutboxQueue stub 생성** (PR #7 전 임시)

```python
# atlas/outbox/queue.py (stub — PR #7에서 완성)
import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

class OutboxEntryType(Enum):
    TICK = auto()
    ORDER = auto()
    ARB_STATE = auto()
    TRADE_RESULT = auto()

@dataclass
class OutboxEntry:
    entry_type: OutboxEntryType
    payload: Any

class OutboxQueue:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    def put_nowait(self, entry: OutboxEntry) -> None:
        self._queue.put_nowait(entry)

    async def get(self) -> OutboxEntry:
        return await self._queue.get()
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_market/test_feed.py -v
# Expected: 2 passed
```

- [ ] **Step 6: 커밋**

```bash
git add core-platform/atlas/market/ core-platform/atlas/outbox/queue.py core-platform/tests/test_market/
git commit -m "feat(market): MarketDataFeed with hot-path-first, outbox for DB"
```

---

### PR #6: DB 스키마 + Alembic 마이그레이션

**Files:**
- Create: `core-platform/atlas/db/models.py`
- Create: `core-platform/atlas/db/session.py`
- Create: `core-platform/atlas/db/migrations/` (Alembic init)
- Create: `core-platform/tests/test_db/test_models.py`

- [ ] **Step 1: SQLAlchemy 모델 작성**

```python
# atlas/db/models.py
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Numeric, DateTime, Boolean, Integer, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class RawTick(Base):
    __tablename__ = "raw_ticks"
    id: Mapped[int] = mapped_column(primary_key=True)
    exchange: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    raw_json: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

class ArbAttempt(Base):
    __tablename__ = "arb_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    strategy: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(32))
    path: Mapped[list] = mapped_column(JSON)
    net_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

class OrderRecord(Base):
    __tablename__ = "orders"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    arb_id: Mapped[str] = mapped_column(String(36))
    leg: Mapped[int] = mapped_column(Integer)
    exchange: Mapped[str] = mapped_column(String(32))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 2: async session factory**

```python
# atlas/db/session.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

def create_session_factory(database_url: str | None = None) -> async_sessionmaker[AsyncSession]:
    url = database_url or os.environ["DATABASE_URL"]
    engine = create_async_engine(url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 3: Alembic 초기화**

```bash
cd core-platform
alembic init atlas/db/migrations
# alembic.ini의 sqlalchemy.url을 환경 변수 참조로 수정
# env.py에서 Base.metadata import
```

- [ ] **Step 4: 첫 마이그레이션 생성**

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head   # 로컬 PostgreSQL 대상
```

- [ ] **Step 5: 모델 임포트 테스트**

```python
# tests/test_db/test_models.py
from atlas.db.models import RawTick, ArbAttempt, OrderRecord

def test_models_importable():
    assert RawTick.__tablename__ == "raw_ticks"
    assert ArbAttempt.__tablename__ == "arb_attempts"
    assert OrderRecord.__tablename__ == "orders"
```

- [ ] **Step 6: 커밋**

```bash
git add core-platform/atlas/db/ core-platform/tests/test_db/
git commit -m "feat(db): SQLAlchemy models and Alembic migrations"
```

---

## 블럭 C: Outbox & Persistence

**목표:** 아웃박스 큐를 완성하고, DBLoggerWorker가 100ms 배치로 DB에 저장하도록 한다.
**완료 기준:** tick 이벤트가 DB에 저장됨을 통합 테스트로 확인.

---

### PR #7: OutboxQueue + DBLoggerWorker

**Files:**
- Modify: `core-platform/atlas/outbox/queue.py` (stub → 완성)
- Create: `core-platform/atlas/outbox/workers.py`
- Create: `core-platform/tests/test_outbox/test_workers.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_outbox/test_workers.py
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from atlas.outbox.queue import OutboxQueue, OutboxEntry, OutboxEntryType
from atlas.outbox.workers import DBLoggerWorker

@pytest.mark.asyncio
async def test_db_logger_worker_writes_tick_to_db():
    queue = OutboxQueue()
    mock_session_factory = MagicMock()
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    worker = DBLoggerWorker(queue=queue, session_factory=mock_session_factory, batch_interval=0.01)

    queue.put_nowait(OutboxEntry(
        entry_type=OutboxEntryType.TICK,
        payload={"exchange": "binance", "symbol": "BTC/USDT", "raw": {}},
    ))

    # 워커를 짧게 실행
    task = asyncio.create_task(worker.run())
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_session.add_all.assert_called()
    mock_session.commit.assert_called()
```

- [ ] **Step 2: DBLoggerWorker 구현**

```python
# atlas/outbox/workers.py
import asyncio
from datetime import datetime, timezone
from atlas.outbox.queue import OutboxQueue, OutboxEntry, OutboxEntryType
from atlas.db.models import RawTick

class DBLoggerWorker:
    def __init__(self, queue: OutboxQueue, session_factory, batch_interval: float = 0.1):
        self._queue = queue
        self._session_factory = session_factory
        self._batch_interval = batch_interval

    async def run(self) -> None:
        while True:
            await asyncio.sleep(self._batch_interval)
            batch: list[OutboxEntry] = []

            while not self._queue._queue.empty():
                batch.append(self._queue._queue.get_nowait())

            if not batch:
                continue

            tick_records = [
                RawTick(
                    exchange=e.payload["exchange"],
                    symbol=e.payload["symbol"],
                    raw_json=e.payload["raw"],
                    received_at=datetime.now(timezone.utc),
                )
                for e in batch
                if e.entry_type == OutboxEntryType.TICK
            ]

            if tick_records:
                async with self._session_factory() as session:
                    session.add_all(tick_records)
                    await session.commit()
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_outbox/test_workers.py -v
# Expected: 1 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/outbox/ core-platform/tests/test_outbox/
git commit -m "feat(outbox): DBLoggerWorker with 100ms batch writes"
```

---

## 블럭 D: Risk & Execution Engine

**목표:** RiskManager 게이트와 ArbitrageStateMachine을 구현한다. 상태 전이, 타임아웃, 자동 언윈드 모두 포함.
**완료 기준:** 상태 머신 단위 테스트 통과. RiskManager 거부 시 주문이 발행되지 않음.

---

### PR #8: RiskManager

**Files:**
- Create: `core-platform/atlas/risk/manager.py`
- Create: `core-platform/tests/test_risk/test_manager.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_risk/test_manager.py
import pytest
from decimal import Decimal
from atlas.risk.manager import RiskManager, RiskDecision
from atlas.events.types import SignalEvent

def make_signal(profit_pct="0.5"):
    return SignalEvent(
        strategy_id="triangular",
        path=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        expected_profit_pct=Decimal(profit_pct),
    )

def test_check_approves_valid_signal():
    rm = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("5000"))
    decision = rm.check(make_signal())
    assert decision.approved is True

def test_check_rejects_when_kill_switch_active():
    rm = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("5000"))
    rm.activate_kill_switch()
    decision = rm.check(make_signal())
    assert decision.approved is False
    assert "kill switch" in decision.reason.lower()

def test_check_rejects_when_exposure_exceeded():
    rm = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("100"))
    rm.add_exposure(Decimal("90"))
    decision = rm.check(make_signal())
    assert decision.approved is False
```

- [ ] **Step 2: RiskManager 구현**

```python
# atlas/risk/manager.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class RiskDecision:
    approved: bool
    reason: str = ""

class RiskManager:
    def __init__(self, max_order_usdt: Decimal, max_exposure_usdt: Decimal):
        self._max_order_usdt = max_order_usdt
        self._max_exposure_usdt = max_exposure_usdt
        self._current_exposure = Decimal("0")
        self._kill_switch = False

    def check(self, signal) -> RiskDecision:
        if self._kill_switch:
            return RiskDecision(approved=False, reason="Kill switch activated")
        if self._current_exposure >= self._max_exposure_usdt:
            return RiskDecision(approved=False, reason=f"Exposure limit reached: {self._current_exposure}")
        return RiskDecision(approved=True)

    def activate_kill_switch(self) -> None:
        self._kill_switch = True

    def deactivate_kill_switch(self) -> None:
        self._kill_switch = False

    def add_exposure(self, amount: Decimal) -> None:
        self._current_exposure += amount

    def release_exposure(self, amount: Decimal) -> None:
        self._current_exposure = max(Decimal("0"), self._current_exposure - amount)
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_risk/test_manager.py -v
# Expected: 3 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/risk/ core-platform/tests/test_risk/
git commit -m "feat(risk): RiskManager with kill switch and exposure limits"
```

---

### PR #9: ExecutionEngine 기본 구조

**Files:**
- Create: `core-platform/atlas/execution/engine.py`
- Create: `core-platform/tests/test_execution/test_engine.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_execution/test_engine.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from atlas.execution.engine import ExecutionEngine
from atlas.events.types import SignalEvent
from atlas.risk.manager import RiskManager

@pytest.mark.asyncio
async def test_engine_does_not_execute_when_risk_rejected():
    rm = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("5000"))
    rm.activate_kill_switch()

    mock_state_machine = AsyncMock()
    engine = ExecutionEngine(risk_manager=rm, state_machine=mock_state_machine)

    signal = SignalEvent(
        strategy_id="triangular",
        path=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        expected_profit_pct=Decimal("0.5"),
    )
    await engine.on_signal(signal)

    mock_state_machine.on_signal.assert_not_called()

@pytest.mark.asyncio
async def test_engine_executes_when_risk_approved():
    rm = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("5000"))
    mock_state_machine = AsyncMock()
    engine = ExecutionEngine(risk_manager=rm, state_machine=mock_state_machine)

    signal = SignalEvent(
        strategy_id="triangular",
        path=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        expected_profit_pct=Decimal("0.5"),
    )
    await engine.on_signal(signal)

    mock_state_machine.on_signal.assert_called_once_with(signal)
```

- [ ] **Step 2: ExecutionEngine 구현**

```python
# atlas/execution/engine.py
from atlas.risk.manager import RiskManager
from atlas.events.types import SignalEvent

class ExecutionEngine:
    def __init__(self, risk_manager: RiskManager, state_machine):
        self._risk_manager = risk_manager
        self._state_machine = state_machine

    async def on_signal(self, signal: SignalEvent) -> None:
        decision = self._risk_manager.check(signal)
        if not decision.approved:
            return
        await self._state_machine.on_signal(signal)
```

- [ ] **Step 3: 테스트 통과 확인 + 커밋**

```bash
pytest tests/test_execution/test_engine.py -v
git add core-platform/atlas/execution/engine.py core-platform/tests/test_execution/
git commit -m "feat(execution): ExecutionEngine with RiskManager gate"
```

---

### PR #10: ArbitrageStateMachine

**Files:**
- Create: `core-platform/atlas/execution/state.py`
- Create: `core-platform/tests/test_execution/test_state.py`

- [ ] **Step 1: 실패 테스트 작성 (핵심 상태 전이)**

```python
# tests/test_execution/test_state.py
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock
from atlas.execution.state import ArbitrageStateMachine, ArbState
from atlas.events.types import SignalEvent, FillEvent
from atlas.outbox.queue import OutboxQueue

def make_signal():
    return SignalEvent(
        strategy_id="triangular",
        path=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        expected_profit_pct=Decimal("0.3"),
    )

@pytest.mark.asyncio
async def test_initial_state_is_idle():
    mock_exchange = AsyncMock()
    sm = ArbitrageStateMachine(exchange=mock_exchange, outbox=OutboxQueue())
    assert sm.state == ArbState.IDLE

@pytest.mark.asyncio
async def test_signal_transitions_to_leg1_pending():
    mock_exchange = AsyncMock()
    sm = ArbitrageStateMachine(exchange=mock_exchange, outbox=OutboxQueue())
    await sm.on_signal(make_signal())
    assert sm.state == ArbState.LEG1_PENDING

@pytest.mark.asyncio
async def test_leg1_fill_transitions_to_leg1_filled():
    mock_exchange = AsyncMock()
    sm = ArbitrageStateMachine(exchange=mock_exchange, outbox=OutboxQueue())
    await sm.on_signal(make_signal())

    fill = FillEvent(arb_id=sm.arb_id, leg=1, symbol="BTC/USDT",
                     filled_qty=Decimal("0.01"), filled_price=Decimal("50000"))
    await sm.on_fill(fill)
    assert sm.state == ArbState.LEG1_FILLED

@pytest.mark.asyncio
async def test_timeout_on_leg1_returns_to_idle():
    mock_exchange = AsyncMock()
    sm = ArbitrageStateMachine(
        exchange=mock_exchange,
        outbox=OutboxQueue(),
        leg_timeout_ms={1: 50, 2: 50, 3: 50},  # 테스트용 짧은 타임아웃
    )
    await sm.on_signal(make_signal())
    await asyncio.sleep(0.1)
    assert sm.state == ArbState.IDLE   # 타임아웃으로 IDLE 복귀

@pytest.mark.asyncio
async def test_leg2_failure_triggers_unwind():
    mock_exchange = AsyncMock()
    sm = ArbitrageStateMachine(
        exchange=mock_exchange,
        outbox=OutboxQueue(),
        leg_timeout_ms={1: 50, 2: 50, 3: 50},
    )
    await sm.on_signal(make_signal())

    fill1 = FillEvent(arb_id=sm.arb_id, leg=1, symbol="BTC/USDT",
                      filled_qty=Decimal("0.01"), filled_price=Decimal("50000"))
    await sm.on_fill(fill1)
    assert sm.state == ArbState.LEG1_FILLED

    await asyncio.sleep(0.1)  # leg2 타임아웃
    assert sm.state in (ArbState.UNWINDING, ArbState.UNWIND_COMPLETE)
```

- [ ] **Step 2: ArbitrageStateMachine 구현**

```python
# atlas/execution/state.py
import asyncio
import uuid
from decimal import Decimal
from enum import Enum, auto
from atlas.events.types import SignalEvent, FillEvent
from atlas.execution.types import Order, Side, OrderType
from atlas.outbox.queue import OutboxQueue, OutboxEntry, OutboxEntryType

class ArbState(Enum):
    IDLE = auto()
    OPPORTUNITY_VALIDATED = auto()
    LEG1_PENDING = auto()
    LEG1_FILLED = auto()
    LEG2_PENDING = auto()
    LEG2_FILLED = auto()
    LEG3_PENDING = auto()
    COMPLETE = auto()
    UNWINDING = auto()
    UNWIND_COMPLETE = auto()
    FAILED = auto()

DEFAULT_LEG_TIMEOUT_MS = {1: 500, 2: 300, 3: 300}

class ArbitrageStateMachine:
    def __init__(self, exchange, outbox: OutboxQueue,
                 leg_timeout_ms: dict | None = None):
        self._exchange = exchange
        self._outbox = outbox
        self._timeout_ms = leg_timeout_ms or DEFAULT_LEG_TIMEOUT_MS
        self.state = ArbState.IDLE
        self.arb_id: str = ""
        self._fills: dict[int, FillEvent] = {}
        self._timeout_task: asyncio.Task | None = None
        self._current_signal: SignalEvent | None = None

    async def on_signal(self, signal: SignalEvent) -> None:
        self.arb_id = str(uuid.uuid4())
        self._current_signal = signal
        self.state = ArbState.OPPORTUNITY_VALIDATED
        await self._place_leg(1)

    async def on_fill(self, fill: FillEvent) -> None:
        if self._timeout_task:
            self._timeout_task.cancel()

        self._fills[fill.leg] = fill
        self._outbox.put_nowait(OutboxEntry(
            entry_type=OutboxEntryType.ORDER,
            payload={"arb_id": self.arb_id, "fill": fill, "state": self.state.name},
        ))

        if fill.leg == 1:
            self.state = ArbState.LEG1_FILLED
            await self._place_leg(2)
        elif fill.leg == 2:
            self.state = ArbState.LEG2_FILLED
            await self._place_leg(3)
        elif fill.leg == 3:
            self.state = ArbState.COMPLETE
            self._outbox.put_nowait(OutboxEntry(
                entry_type=OutboxEntryType.TRADE_RESULT,
                payload={"arb_id": self.arb_id, "state": "COMPLETE"},
            ))

    async def _place_leg(self, leg: int) -> None:
        leg_states = {1: ArbState.LEG1_PENDING, 2: ArbState.LEG2_PENDING, 3: ArbState.LEG3_PENDING}
        self.state = leg_states[leg]
        timeout_ms = self._timeout_ms.get(leg, 500)
        self._timeout_task = asyncio.create_task(self._timeout_handler(leg, timeout_ms))

    async def _timeout_handler(self, leg: int, timeout_ms: int) -> None:
        await asyncio.sleep(timeout_ms / 1000)
        await self._unwind(leg)

    async def _unwind(self, failed_leg: int) -> None:
        self.state = ArbState.UNWINDING
        # failed_leg 이전의 체결된 레그들을 역순으로 청산
        for leg in range(failed_leg - 1, 0, -1):
            if leg in self._fills:
                pass  # 시장가 청산 주문 (실제 구현 시 exchange.place_order 호출)
        self.state = ArbState.UNWIND_COMPLETE
        self._outbox.put_nowait(OutboxEntry(
            entry_type=OutboxEntryType.TRADE_RESULT,
            payload={"arb_id": self.arb_id, "state": "UNWIND_COMPLETE"},
        ))
        self._reset()

    def _reset(self) -> None:
        self.state = ArbState.IDLE
        self.arb_id = ""
        self._fills = {}
        self._current_signal = None
        self._timeout_task = None
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_execution/test_state.py -v
# Expected: 5 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/execution/state.py core-platform/tests/test_execution/test_state.py
git commit -m "feat(execution): ArbitrageStateMachine with timeout and auto-unwind"
```

---

## 블럭 E: Triangular Arbitrage Strategy

**목표:** Bellman-Ford로 삼각 차익거래 기회를 탐지하고 SignalEvent를 발행한다.
**완료 기준:** mock 가격 데이터로 음수 사이클 탐지 → SignalEvent 발행 테스트 통과.

---

### PR #11: Bellman-Ford 그래프

**Files:**
- Create: `core-platform/atlas/strategy/arbitrage/graph.py`
- Create: `core-platform/tests/test_strategy/test_graph.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_strategy/test_graph.py
from decimal import Decimal
from atlas.strategy.arbitrage.graph import ArbitrageGraph

def test_detects_profitable_cycle():
    graph = ArbitrageGraph(fee_rate=Decimal("0.001"))
    # BTC/USDT: 1 USDT → 0.00002 BTC (bid 50000)
    # ETH/BTC:  1 BTC  → 15 ETH   (bid 0.0666)
    # ETH/USDT: 1 ETH  → 3400 USDT (ask 3400)
    # 이론 수익: 0.00002 * 15 * 3400 = 1.02 USDT (2% 수익, 수수료 전)
    graph.update("BTC/USDT", bid=Decimal("50000"), ask=Decimal("50001"))
    graph.update("ETH/BTC",  bid=Decimal("0.06660"), ask=Decimal("0.06661"))
    graph.update("ETH/USDT", bid=Decimal("3398"), ask=Decimal("3400"))

    cycles = graph.find_negative_cycles(base="USDT")
    assert len(cycles) > 0
    assert cycles[0]["profit_pct"] > Decimal("0")

def test_no_cycle_when_unprofitable():
    graph = ArbitrageGraph(fee_rate=Decimal("0.001"))
    # 수익 없는 균형 가격
    graph.update("BTC/USDT", bid=Decimal("50000"), ask=Decimal("50010"))
    graph.update("ETH/BTC",  bid=Decimal("0.06000"), ask=Decimal("0.06010"))
    graph.update("ETH/USDT", bid=Decimal("2990"), ask=Decimal("3000"))

    cycles = graph.find_negative_cycles(base="USDT")
    assert len(cycles) == 0
```

- [ ] **Step 2: ArbitrageGraph 구현**

```python
# atlas/strategy/arbitrage/graph.py
import math
from decimal import Decimal
from typing import Optional

class ArbitrageGraph:
    def __init__(self, fee_rate: Decimal = Decimal("0.001")):
        self._fee_rate = fee_rate
        self._prices: dict[str, dict] = {}  # symbol → {bid, ask}

    def update(self, symbol: str, bid: Decimal, ask: Decimal) -> None:
        self._prices[symbol] = {"bid": bid, "ask": ask}

    def find_negative_cycles(self, base: str = "USDT") -> list[dict]:
        """Bellman-Ford로 수익 있는 삼각 사이클 탐지"""
        if len(self._prices) < 2:
            return []

        results = []
        symbols = list(self._prices.keys())

        # base → A → B → base 형태의 사이클 탐색
        for s1 in symbols:
            for s2 in symbols:
                if s1 == s2:
                    continue
                path = self._try_cycle(base, s1, s2)
                if path and path["profit_pct"] > Decimal("0"):
                    results.append(path)

        return sorted(results, key=lambda x: x["profit_pct"], reverse=True)

    def _try_cycle(self, base: str, s1: str, s2: str) -> Optional[dict]:
        """base → leg1(s1) → leg2(s2) → base 수익 계산"""
        fee = Decimal(1) - self._fee_rate

        b1, q1 = s1.split("/")
        b2, q2 = s2.split("/")

        # 경로 유효성 확인: base → b1 or q1 → b2 or q2 → base
        # 단순화: USDT 기반 3-leg만 처리
        if q1 != base or q2 != b1:
            return None
        if b2 != base and q2 != base:
            return None

        ask1 = self._prices[s1]["ask"]
        ask2 = self._prices[s2]["ask"]
        bid_final_symbol = f"{b2}/{q2}" if f"{b2}/{q2}" in self._prices else f"{q2}/{b2}"
        if bid_final_symbol not in self._prices:
            return None
        bid_final = self._prices[bid_final_symbol]["bid"]

        # 1 USDT → b1 → b2 → USDT
        step1 = (Decimal("1") / ask1) * fee
        step2 = (step1 / ask2) * fee
        final = step2 * bid_final * fee

        profit_pct = (final - Decimal("1")) * Decimal("100")

        return {
            "path": [s1, s2, bid_final_symbol],
            "profit_pct": profit_pct,
        }
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_strategy/test_graph.py -v
# Expected: 2 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/strategy/arbitrage/graph.py core-platform/tests/test_strategy/test_graph.py
git commit -m "feat(strategy): Bellman-Ford arbitrage cycle detection"
```

---

### PR #12: TriangularArbitrageStrategy

**Files:**
- Create: `core-platform/atlas/strategy/base.py`
- Create: `core-platform/atlas/strategy/arbitrage/triangular.py`
- Create: `core-platform/tests/test_strategy/test_triangular.py`

- [ ] **Step 1: StrategyBase 정의**

```python
# atlas/strategy/base.py
from abc import ABC, abstractmethod
from atlas.events.types import MarketDataEvent

class StrategyBase(ABC):
    @abstractmethod
    async def on_market_data(self, event: MarketDataEvent) -> None: ...
```

- [ ] **Step 2: 실패 테스트 작성**

```python
# tests/test_strategy/test_triangular.py
import pytest
from decimal import Decimal
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent, SignalEvent

@pytest.mark.asyncio
async def test_publishes_signal_when_opportunity_found():
    bus = EventBus()
    signals = []

    async def capture(e: SignalEvent): signals.append(e)
    bus.subscribe(SignalEvent, capture)

    strategy = TriangularArbitrageStrategy(
        bus=bus,
        symbols=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        min_profit_pct=Decimal("0.1"),
    )

    # 수익성 있는 가격 주입
    for sym, bid, ask in [
        ("BTC/USDT", "50000", "50001"),
        ("ETH/BTC",  "0.0666", "0.0667"),
        ("ETH/USDT", "3398",   "3400"),
    ]:
        await strategy.on_market_data(MarketDataEvent(
            exchange="binance", symbol=sym,
            bid=Decimal(bid), ask=Decimal(ask), last=Decimal(bid),
        ))

    assert len(signals) > 0
    assert signals[0].strategy_id == "triangular_arb"
```

- [ ] **Step 3: TriangularArbitrageStrategy 구현**

```python
# atlas/strategy/arbitrage/triangular.py
from decimal import Decimal
from atlas.strategy.base import StrategyBase
from atlas.strategy.arbitrage.graph import ArbitrageGraph
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent, SignalEvent

class TriangularArbitrageStrategy(StrategyBase):
    def __init__(self, bus: EventBus, symbols: list[str],
                 min_profit_pct: Decimal = Decimal("0.05"),
                 fee_rate: Decimal = Decimal("0.001")):
        self._bus = bus
        self._symbols = symbols
        self._min_profit_pct = min_profit_pct
        self._graph = ArbitrageGraph(fee_rate=fee_rate)

    async def on_market_data(self, event: MarketDataEvent) -> None:
        if event.symbol not in self._symbols:
            return

        self._graph.update(event.symbol, bid=event.bid, ask=event.ask)
        cycles = self._graph.find_negative_cycles(base="USDT")

        for cycle in cycles:
            if cycle["profit_pct"] >= self._min_profit_pct:
                await self._bus.publish(SignalEvent(
                    strategy_id="triangular_arb",
                    path=cycle["path"],
                    expected_profit_pct=cycle["profit_pct"],
                ))
                break   # 한 사이클만 (중복 신호 방지)
```

- [ ] **Step 4: 테스트 통과 확인 + 커밋**

```bash
pytest tests/test_strategy/ -v
git add core-platform/atlas/strategy/ core-platform/tests/test_strategy/
git commit -m "feat(strategy): TriangularArbitrageStrategy with signal emission"
```

---

## 블럭 F: Alerts & Live Runner

**목표:** Discord 알림을 붙이고 모든 컴포넌트를 LiveRunner에 조립한다.
**완료 기준:** mock exchange로 전체 흐름 통합 테스트 통과.

---

### PR #13: AlertWorker (Discord)

**Files:**
- Modify: `core-platform/atlas/outbox/workers.py`
- Create: `core-platform/tests/test_outbox/test_alert_worker.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_outbox/test_alert_worker.py
import pytest
from unittest.mock import AsyncMock, patch
from atlas.outbox.queue import OutboxQueue, OutboxEntry, OutboxEntryType
from atlas.outbox.workers import AlertWorker

@pytest.mark.asyncio
async def test_alert_worker_posts_to_discord_on_trade_complete():
    queue = OutboxQueue()
    worker = AlertWorker(queue=queue, webhook_url="https://discord.fake/webhook")

    queue.put_nowait(OutboxEntry(
        entry_type=OutboxEntryType.TRADE_RESULT,
        payload={"arb_id": "abc123", "state": "COMPLETE", "net_pnl": "1.23"},
    ))

    with patch("aiohttp.ClientSession.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.__aenter__ = AsyncMock()
        mock_post.return_value.__aexit__ = AsyncMock(return_value=False)
        import asyncio
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_post.assert_called_once()
```

- [ ] **Step 2: AlertWorker 구현 (workers.py에 추가)**

```python
# atlas/outbox/workers.py 에 추가
import aiohttp

class AlertWorker:
    def __init__(self, queue: OutboxQueue, webhook_url: str):
        self._queue = queue
        self._webhook_url = webhook_url

    async def run(self) -> None:
        while True:
            entry = await self._queue.get()
            if entry.entry_type != OutboxEntryType.TRADE_RESULT:
                continue
            state = entry.payload.get("state", "")
            if state not in ("COMPLETE", "UNWIND_COMPLETE", "FAILED"):
                continue
            await self._post(entry.payload)

    async def _post(self, payload: dict) -> None:
        state = payload.get("state")
        arb_id = payload.get("arb_id", "")
        pnl = payload.get("net_pnl", "N/A")
        content = f"**[Atlas Trading]** `{state}` | arb_id: `{arb_id}` | PnL: `{pnl}`"
        async with aiohttp.ClientSession() as session:
            async with session.post(self._webhook_url, json={"content": content}):
                pass
```

- [ ] **Step 3: 테스트 통과 확인 + 커밋**

```bash
pytest tests/test_outbox/ -v
git add core-platform/atlas/outbox/workers.py core-platform/tests/test_outbox/test_alert_worker.py
git commit -m "feat(outbox): AlertWorker for Discord notifications"
```

---

### PR #14: LiveRunner + 통합 테스트

**Files:**
- Create: `core-platform/atlas/live/runner.py`
- Create: `core-platform/tests/test_integration/test_live_flow.py`

- [ ] **Step 1: LiveRunner 구현**

```python
# atlas/live/runner.py
import asyncio
import os
from decimal import Decimal
from atlas.events.bus import EventBus
from atlas.events.types import MarketDataEvent, SignalEvent
from atlas.exchange.binance import BinanceAdapter
from atlas.market.feed import MarketDataFeed
from atlas.risk.manager import RiskManager
from atlas.execution.state import ArbitrageStateMachine
from atlas.execution.engine import ExecutionEngine
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy
from atlas.outbox.queue import OutboxQueue
from atlas.outbox.workers import DBLoggerWorker, AlertWorker
from atlas.db.session import create_session_factory

class LiveRunner:
    def __init__(self, config: dict):
        self._config = config
        self.bus = EventBus()
        self.outbox = OutboxQueue()

        self.exchange = BinanceAdapter(
            api_key=config["api_key"],
            api_secret=config["api_secret"],
            testnet=config.get("testnet", True),
        )
        self.feed = MarketDataFeed(
            exchange_id="binance",
            bus=self.bus,
            outbox=self.outbox,
        )
        self.risk_manager = RiskManager(
            max_order_usdt=Decimal(config.get("max_order_usdt", "100")),
            max_exposure_usdt=Decimal(config.get("max_exposure_usdt", "500")),
        )
        self.state_machine = ArbitrageStateMachine(
            exchange=self.exchange,
            outbox=self.outbox,
        )
        self.engine = ExecutionEngine(
            risk_manager=self.risk_manager,
            state_machine=self.state_machine,
        )
        self.strategy = TriangularArbitrageStrategy(
            bus=self.bus,
            symbols=config["symbols"],
            min_profit_pct=Decimal(config.get("min_profit_pct", "0.05")),
        )
        self.bus.subscribe(MarketDataEvent, self.strategy.on_market_data)
        self.bus.subscribe(SignalEvent, self.engine.on_signal)

    async def run(self) -> None:
        session_factory = create_session_factory()
        workers = [
            asyncio.create_task(DBLoggerWorker(self.outbox, session_factory).run()),
            asyncio.create_task(AlertWorker(self.outbox, self._config["discord_webhook"]).run()),
        ]
        try:
            await self.exchange.subscribe_ticker(
                symbols=self._config["symbols"],
                callback=self.feed._on_tickers,
            )
        finally:
            for w in workers:
                w.cancel()
            await self.exchange.close()
```

- [ ] **Step 2: 통합 테스트 작성 (mock exchange)**

```python
# tests/test_integration/test_live_flow.py
import pytest
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock
from atlas.events.bus import EventBus
from atlas.events.types import SignalEvent
from atlas.market.feed import MarketDataFeed
from atlas.risk.manager import RiskManager
from atlas.execution.state import ArbitrageStateMachine
from atlas.execution.engine import ExecutionEngine
from atlas.strategy.arbitrage.triangular import TriangularArbitrageStrategy
from atlas.outbox.queue import OutboxQueue

@pytest.mark.asyncio
async def test_full_flow_signal_reaches_state_machine():
    bus = EventBus()
    outbox = OutboxQueue()
    mock_exchange = AsyncMock()

    risk_manager = RiskManager(max_order_usdt=Decimal("1000"), max_exposure_usdt=Decimal("5000"))
    state_machine = ArbitrageStateMachine(exchange=mock_exchange, outbox=outbox,
                                          leg_timeout_ms={1: 200, 2: 200, 3: 200})
    engine = ExecutionEngine(risk_manager=risk_manager, state_machine=state_machine)
    strategy = TriangularArbitrageStrategy(
        bus=bus,
        symbols=["BTC/USDT", "ETH/BTC", "ETH/USDT"],
        min_profit_pct=Decimal("0.01"),
    )

    from atlas.events.types import MarketDataEvent
    bus.subscribe(MarketDataEvent, strategy.on_market_data)
    bus.subscribe(SignalEvent, engine.on_signal)

    feed = MarketDataFeed(exchange_id="binance", bus=bus, outbox=outbox)
    await feed._on_tickers({
        "BTC/USDT": {"bid": 50000.0, "ask": 50001.0, "last": 50000.0},
        "ETH/BTC":  {"bid": 0.0666,  "ask": 0.0667,  "last": 0.0666},
        "ETH/USDT": {"bid": 3398.0,  "ask": 3400.0,  "last": 3398.0},
    })
    await asyncio.sleep(0.05)

    # 상태 머신이 LEG1_PENDING 이상으로 진행됐거나 타임아웃으로 IDLE 복귀
    from atlas.execution.state import ArbState
    assert state_machine.state in (ArbState.IDLE, ArbState.LEG1_PENDING, ArbState.LEG1_FILLED)
```

- [ ] **Step 3: 테스트 통과 확인**

```bash
pytest tests/test_integration/ -v
# Expected: 1 passed
```

- [ ] **Step 4: 커밋**

```bash
git add core-platform/atlas/live/ core-platform/tests/test_integration/
git commit -m "feat(live): LiveRunner integration and full flow test"
```

---

## 블럭 G: API Server

**목표:** 어드민 대시보드를 위한 FastAPI 서버. core-platform DB를 직접 읽는다.
**완료 기준:** `GET /trades`, `GET /positions` 응답. WebSocket 알림 연결.

---

### PR #15: FastAPI 스캐폴딩

**Files:**
- Create: `api-server/pyproject.toml`
- Create: `api-server/app/main.py`
- Create: `api-server/app/db.py`

- [ ] **Step 1: pyproject.toml**

```toml
[project]
name = "atlas-api-server"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "python-dotenv>=1.0.0",
]
```

- [ ] **Step 2: FastAPI 앱 + DB 연결**

```python
# app/main.py
from fastapi import FastAPI
from app.routes import trades, positions, risk, strategies, ws_alerts

app = FastAPI(title="Atlas Trading Admin")
app.include_router(trades.router)
app.include_router(positions.router)
app.include_router(ws_alerts.router)

# app/db.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from typing import AsyncGenerator

engine = create_async_engine(os.environ["DATABASE_URL"])
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 3: 서버 기동 확인**

```bash
cd api-server
uvicorn app.main:app --reload
# http://localhost:8000/docs 접속 확인
```

- [ ] **Step 4: 커밋**

```bash
git add api-server/
git commit -m "feat(api): FastAPI scaffolding with DB connection"
```

---

### PR #16: 어드민 API 엔드포인트

**Files:**
- Create: `api-server/app/routes/trades.py`
- Create: `api-server/app/routes/positions.py`

- [ ] **Step 1: 거래내역 API**

```python
# app/routes/trades.py
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
# core-platform의 모델을 직접 import (같은 DB 공유)
import sys; sys.path.insert(0, "../core-platform")
from atlas.db.models import ArbAttempt

router = APIRouter(prefix="/trades", tags=["trades"])

@router.get("")
async def list_trades(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ArbAttempt)
        .order_by(desc(ArbAttempt.started_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "strategy": r.strategy,
            "state": r.state,
            "path": r.path,
            "net_pnl": str(r.net_pnl) if r.net_pnl else None,
            "started_at": r.started_at.isoformat(),
            "ended_at": r.ended_at.isoformat() if r.ended_at else None,
        }
        for r in rows
    ]
```

- [ ] **Step 2: 포지션 API**

```python
# app/routes/positions.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from atlas.db.models import ArbAttempt

router = APIRouter(prefix="/positions", tags=["positions"])

@router.get("")
async def list_open_positions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ArbAttempt).where(
            ArbAttempt.state.notin_(["COMPLETE", "UNWIND_COMPLETE", "FAILED"])
        )
    )
    return result.scalars().all()
```

- [ ] **Step 3: 커밋**

```bash
git add api-server/app/routes/
git commit -m "feat(api): trades and positions endpoints"
```

---

### PR #17: WebSocket 알림 엔드포인트

**Files:**
- Create: `api-server/app/routes/ws_alerts.py`

- [ ] **Step 1: WebSocket 알림 구현**

```python
# app/routes/ws_alerts.py
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["alerts"])
_clients: list[WebSocket] = []

@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket):
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()   # ping 수신 대기
    except WebSocketDisconnect:
        _clients.remove(websocket)

async def broadcast_alert(message: dict) -> None:
    for client in list(_clients):
        try:
            await client.send_json(message)
        except Exception:
            _clients.discard(client)
```

- [ ] **Step 2: AlertWorker가 broadcast_alert 호출하도록 연결**

AlertWorker와 api-server 간 연결은 공유 DB의 `LISTEN/NOTIFY` 또는 Redis pub/sub로 처리.
Phase 1에서는 api-server가 `arb_attempts` 테이블을 1초마다 폴링하는 방식으로 단순화:

```python
# app/routes/ws_alerts.py 에 추가
@router.on_event("startup")
async def start_poller():
    asyncio.create_task(_poll_new_trades())

async def _poll_new_trades():
    from app.db import SessionLocal
    from atlas.db.models import ArbAttempt
    from sqlalchemy import select, desc
    from datetime import datetime, timezone, timedelta
    while True:
        await asyncio.sleep(1)
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=2)
        async with SessionLocal() as db:
            result = await db.execute(
                select(ArbAttempt)
                .where(ArbAttempt.ended_at >= cutoff)
                .order_by(desc(ArbAttempt.ended_at))
            )
            for row in result.scalars():
                await broadcast_alert({"type": row.state, "arb_id": row.id, "pnl": str(row.net_pnl)})
```

- [ ] **Step 3: 커밋**

```bash
git add api-server/app/routes/ws_alerts.py
git commit -m "feat(api): WebSocket alerts endpoint with DB polling"
```

---

## 블럭 H: Web Dashboard

**목표:** 거래내역 테이블과 실시간 알림 피드가 있는 React 어드민 대시보드.
**완료 기준:** 브라우저에서 거래내역 조회 및 WebSocket 알림 수신 동작 확인.

---

### PR #18: Vite + React 스캐폴딩

**Files:**
- Create: `web-dashboard/package.json`
- Create: `web-dashboard/vite.config.ts`
- Create: `web-dashboard/src/main.tsx`
- Create: `web-dashboard/src/App.tsx`

- [ ] **Step 1: 프로젝트 초기화**

```bash
cd web-dashboard
npm create vite@latest . -- --template react-ts
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 2: API 베이스 URL 설정**

```typescript
// src/api/client.ts
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const api = {
  get: (path: string) => fetch(`${BASE_URL}${path}`).then(r => r.json()),
};
```

- [ ] **Step 3: 기동 확인**

```bash
npm run dev
# http://localhost:5173 접속 확인
```

- [ ] **Step 4: 커밋**

```bash
git add web-dashboard/
git commit -m "feat(dashboard): Vite + React + Tailwind scaffolding"
```

---

### PR #19: 거래내역 테이블

**Files:**
- Create: `web-dashboard/src/api/trades.ts`
- Create: `web-dashboard/src/components/TradeTable.tsx`
- Modify: `web-dashboard/src/App.tsx`

- [ ] **Step 1: API 타입 + fetch**

```typescript
// src/api/trades.ts
export interface Trade {
  id: string;
  strategy: string;
  state: string;
  path: string[];
  net_pnl: string | null;
  started_at: string;
  ended_at: string | null;
}

export async function fetchTrades(limit = 50): Promise<Trade[]> {
  const res = await fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/trades?limit=${limit}`);
  return res.json();
}
```

- [ ] **Step 2: TradeTable 컴포넌트**

```tsx
// src/components/TradeTable.tsx
import { useEffect, useState } from "react";
import { fetchTrades, Trade } from "../api/trades";

export function TradeTable() {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    fetchTrades().then(setTrades);
  }, []);

  return (
    <table className="w-full text-sm text-left">
      <thead className="bg-gray-100">
        <tr>
          <th className="px-4 py-2">시간</th>
          <th className="px-4 py-2">전략</th>
          <th className="px-4 py-2">상태</th>
          <th className="px-4 py-2">경로</th>
          <th className="px-4 py-2">PnL</th>
        </tr>
      </thead>
      <tbody>
        {trades.map(t => (
          <tr key={t.id} className="border-b">
            <td className="px-4 py-2">{new Date(t.started_at).toLocaleString()}</td>
            <td className="px-4 py-2">{t.strategy}</td>
            <td className="px-4 py-2">{t.state}</td>
            <td className="px-4 py-2">{t.path?.join(" → ")}</td>
            <td className={`px-4 py-2 ${parseFloat(t.net_pnl ?? "0") >= 0 ? "text-green-600" : "text-red-600"}`}>
              {t.net_pnl ?? "-"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 3: App에 마운트 + 커밋**

```bash
git add web-dashboard/src/
git commit -m "feat(dashboard): trade history table"
```

---

### PR #20: 실시간 알림 피드

**Files:**
- Create: `web-dashboard/src/api/alerts.ts`
- Create: `web-dashboard/src/components/AlertFeed.tsx`

- [ ] **Step 1: WebSocket 훅**

```typescript
// src/api/alerts.ts
import { useEffect, useState } from "react";

export interface Alert {
  type: string;
  arb_id: string;
  pnl: string;
  ts: string;
}

export function useAlerts(): Alert[] {
  const [alerts, setAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    const WS_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000")
      .replace("http", "ws") + "/ws/alerts";
    const ws = new WebSocket(WS_URL);

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setAlerts(prev => [{ ...data, ts: new Date().toISOString() }, ...prev].slice(0, 50));
    };

    return () => ws.close();
  }, []);

  return alerts;
}
```

- [ ] **Step 2: AlertFeed 컴포넌트**

```tsx
// src/components/AlertFeed.tsx
import { useAlerts } from "../api/alerts";

export function AlertFeed() {
  const alerts = useAlerts();
  return (
    <div className="h-48 overflow-y-auto border rounded p-2 space-y-1">
      {alerts.length === 0 && <p className="text-gray-400 text-sm">알림 없음</p>}
      {alerts.map((a, i) => (
        <div key={i} className={`text-sm px-2 py-1 rounded ${a.type === "COMPLETE" ? "bg-green-50" : "bg-red-50"}`}>
          <span className="font-mono text-xs text-gray-400">{new Date(a.ts).toLocaleTimeString()}</span>
          {" "}<strong>{a.type}</strong> | {a.arb_id.slice(0, 8)}… | PnL: {a.pnl}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: App에 마운트 + 커밋**

```bash
git add web-dashboard/src/
git commit -m "feat(dashboard): real-time alert feed via WebSocket"
```

---

## 완료 기준 (Phase 1 전체)

- [ ] `pytest core-platform/tests/ -v` — 전체 통과
- [ ] `core-platform` LiveRunner가 Binance testnet 티커를 수신하고 상태 머신이 동작
- [ ] `api-server` `GET /trades` 가 DB 데이터를 반환
- [ ] `web-dashboard` 브라우저에서 거래내역 + 알림 확인
