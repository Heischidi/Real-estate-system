"""Payment ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

import enum
from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PaymentPlan(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Payment(Base):
    """Manual payment claim from a subscriber."""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    plan: Mapped[PaymentPlan] = mapped_column(
        Enum(PaymentPlan, name="payment_plan_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", values_callable=lambda e: [m.value for m in e]),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Payment telegram_id={self.telegram_id} plan={self.plan} status={self.status}>"
