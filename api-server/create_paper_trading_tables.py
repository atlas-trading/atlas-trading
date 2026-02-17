"""
Create Paper Trading tables in the database
"""
from app.models.base import init_db
from app.models.paper_trading import PaperTradingSession, PaperTradingTrade, PaperTradingSnapshot

if __name__ == "__main__":
    print("Creating Paper Trading tables...")

    # Import models to register them with Base
    # (Already done via imports above)

    # Create all tables
    init_db()

    print("✓ Paper Trading tables created successfully:")
    print("  - paper_trading_sessions")
    print("  - paper_trading_trades")
    print("  - paper_trading_snapshots")
