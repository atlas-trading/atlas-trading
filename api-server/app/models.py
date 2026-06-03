from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ArbAttempt(Base):
    __tablename__ = "arb_attempts"

    id: Mapped[str] = mapped_column(primary_key=True)
    strategy: Mapped[str]
    status: Mapped[str]
    expected_profit: Mapped[Decimal | None]
    actual_profit: Mapped[Decimal | None]
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
