# Paper Trading Database Schema

## Overview
Paper Trading database schema has been successfully created with three main tables to support real-time paper trading functionality.

## Tables Created

### 1. paper_trading_sessions
Stores paper trading session information.

**Columns:**
- `id` (PK): Session ID
- `name`: User-defined session name
- `symbol`: Trading pair (e.g., BTC/USDT)
- `strategy`: Strategy name (e.g., Statistical Arbitrage)
- `initial_capital`: Starting capital
- `current_balance`: Current cash balance
- `current_equity`: Current total equity (balance + position value)
- `status`: Session status (ACTIVE, PAUSED, STOPPED, ERROR)
- `start_time`: Session start time
- `end_time`: Session end time (nullable)
- `last_update`: Last update timestamp
- `settings` (JSON): Risk limits and other settings
- `total_trades`: Total number of trades
- `winning_trades`: Number of winning trades
- `losing_trades`: Number of losing trades
- `total_pnl`: Total profit/loss
- `total_commission`: Total commission paid
- `max_equity`: Maximum equity reached
- `max_drawdown`: Maximum drawdown percentage

**Indexes:**
- Primary key on `id`
- Index on `status`
- Index on `symbol`

**Relationships:**
- One-to-many with `paper_trading_trades`
- One-to-many with `paper_trading_snapshots`

### 2. paper_trading_trades
Stores individual trade records.

**Columns:**
- `id` (PK): Trade ID
- `session_id` (FK): Reference to session
- `symbol`: Trading pair
- `side`: buy/sell
- `position_side`: open/close
- `quantity`: Trade quantity
- `entry_price`: Entry price (for opening positions)
- `exit_price`: Exit price (for closing positions)
- `commission`: Commission paid
- `slippage`: Slippage cost
- `pnl`: Profit/loss (for closed positions)
- `pnl_percent`: P&L percentage
- `position_type`: long/short
- `stop_loss`: Stop loss price
- `take_profit`: Take profit price
- `exit_reason`: Reason for exit (signal, stop_loss, take_profit)
- `timestamp`: Trade timestamp

**Indexes:**
- Primary key on `id`
- Index on `session_id`
- Index on `symbol`
- Index on `timestamp`

**Foreign Keys:**
- `session_id` references `paper_trading_sessions(id)`

### 3. paper_trading_snapshots
Stores periodic snapshots of account state (every 10 seconds).

**Columns:**
- `id` (PK): Snapshot ID
- `session_id` (FK): Reference to session
- `balance`: Cash balance
- `equity`: Total equity
- `unrealized_pnl`: Unrealized profit/loss
- `open_positions` (JSON): Array of open positions with details
- `market_price`: Current market price
- `timestamp`: Snapshot timestamp

**Indexes:**
- Primary key on `id`
- Index on `session_id`
- Index on `timestamp`

**Foreign Keys:**
- `session_id` references `paper_trading_sessions(id)`

## Session Status Enum
- `ACTIVE`: Session is running
- `PAUSED`: Session is paused
- `STOPPED`: Session has been stopped
- `ERROR`: Session encountered an error

## Files Created

1. **`/app/models/paper_trading.py`**
   - SQLAlchemy model definitions
   - Uses shared `Base` from `app.models.base`

2. **`/app/models/__init__.py`** (updated)
   - Added imports for paper trading models

3. **`create_paper_trading_tables.py`**
   - Script to create database tables

4. **`test_paper_trading_models.py`**
   - Test script to verify models work correctly

5. **`PAPER_TRADING_SCHEMA.md`** (this file)
   - Documentation of the schema

## Verification Steps Completed

1. ✓ Models import successfully
2. ✓ Tables created in PostgreSQL database
3. ✓ All columns and indexes are correct
4. ✓ Foreign key relationships work properly
5. ✓ CRUD operations tested successfully
6. ✓ Cascade delete works (deleting session removes trades and snapshots)

## Usage Example

```python
from app.models.base import SessionLocal
from app.models.paper_trading import (
    PaperTradingSession,
    PaperTradingTrade,
    PaperTradingSnapshot,
    SessionStatus,
)

# Create a session
db = SessionLocal()
session = PaperTradingSession(
    name="My Trading Session",
    symbol="BTC/USDT",
    strategy="Statistical Arbitrage",
    initial_capital=10000.0,
    current_balance=10000.0,
    current_equity=10000.0,
    status=SessionStatus.ACTIVE,
    settings={"risk_limit": 0.02},
)
db.add(session)
db.commit()
```

## Next Steps

To use these models in the API:

1. Create Pydantic schemas in `/app/schemas/paper_trading.py`
2. Create API endpoints in `/app/api/v1/paper_trading.py`
3. Implement paper trading engine logic
4. Add WebSocket support for real-time updates
5. Create frontend UI for paper trading dashboard

## Database Commands

Create tables:
```bash
cd /Users/jang-yeonghwan/atlas-trading/atlas-trading/api-server
python create_paper_trading_tables.py
```

Test models:
```bash
cd /Users/jang-yeonghwan/atlas-trading/atlas-trading/api-server
python test_paper_trading_models.py
```

View tables in PostgreSQL:
```sql
\dt paper_trading*
\d paper_trading_sessions
\d paper_trading_trades
\d paper_trading_snapshots
```
