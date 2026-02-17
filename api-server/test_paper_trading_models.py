"""
Test Paper Trading Models
"""
from datetime import datetime
from app.models.base import SessionLocal
from app.models.paper_trading import (
    PaperTradingSession,
    PaperTradingTrade,
    PaperTradingSnapshot,
    SessionStatus,
)


def test_create_session():
    """Test creating a paper trading session"""
    db = SessionLocal()
    try:
        # Create a test session
        session = PaperTradingSession(
            name="Test Session",
            symbol="BTC/USDT",
            strategy="Statistical Arbitrage",
            initial_capital=10000.0,
            current_balance=10000.0,
            current_equity=10000.0,
            status=SessionStatus.ACTIVE,
            settings={"risk_limit": 0.02, "max_positions": 3},
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        print(f"✓ Created session: {session}")
        print(f"  ID: {session.id}")
        print(f"  Symbol: {session.symbol}")
        print(f"  Status: {session.status}")

        # Create a test trade
        trade = PaperTradingTrade(
            session_id=session.id,
            symbol="BTC/USDT",
            side="buy",
            position_side="open",
            quantity=0.1,
            entry_price=50000.0,
            position_type="long",
            commission=2.5,
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)

        print(f"\n✓ Created trade: {trade}")
        print(f"  ID: {trade.id}")
        print(f"  Side: {trade.side}")
        print(f"  Quantity: {trade.quantity}")

        # Create a test snapshot
        snapshot = PaperTradingSnapshot(
            session_id=session.id,
            balance=9997.5,
            equity=10000.0,
            unrealized_pnl=2.5,
            open_positions=[
                {
                    "symbol": "BTC/USDT",
                    "side": "long",
                    "quantity": 0.1,
                    "entry_price": 50000.0,
                }
            ],
            market_price=50025.0,
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        print(f"\n✓ Created snapshot: {snapshot}")
        print(f"  ID: {snapshot.id}")
        print(f"  Equity: {snapshot.equity}")
        print(f"  Unrealized PnL: {snapshot.unrealized_pnl}")

        # Query the session with relationships
        queried_session = (
            db.query(PaperTradingSession).filter_by(id=session.id).first()
        )
        print(f"\n✓ Queried session with relationships:")
        print(f"  Trades count: {len(queried_session.trades)}")
        print(f"  Snapshots count: {len(queried_session.snapshots)}")

        # Cleanup test data
        db.delete(snapshot)
        db.delete(trade)
        db.delete(session)
        db.commit()

        print("\n✓ All tests passed! Models are working correctly.")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_create_session()
