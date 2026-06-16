"""Payment service — database operations for manual payments."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging_config import get_logger
from app.models.payment import Payment, PaymentStatus
from app.models.subscriber import Subscriber, SubscriptionTier
from app.schemas.payment import PaymentCreate

log = get_logger(__name__)


class PaymentService:
    """Database interactions for the Payment model."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_payment(self, data: PaymentCreate) -> Payment:
        payment = Payment(**data.model_dump())
        self.db.add(payment)
        await self.db.flush()
        log.info("payment_created", telegram_id=data.telegram_id, amount=data.amount)
        return payment

    async def list_payments(
        self, page: int = 1, page_size: int = 50, status: PaymentStatus | None = None
    ) -> tuple[list[tuple[Payment, Subscriber | None]], int]:
        """Return paginated payments along with their associated subscriber."""
        # Using a join with Subscriber to get username/first_name
        stmt = select(Payment, Subscriber).outerjoin(
            Subscriber, Payment.telegram_id == Subscriber.telegram_id
        )
        if status:
            stmt = stmt.where(Payment.status == status)

        count_stmt = select(func.count(Payment.id))
        if status:
            count_stmt = count_stmt.where(Payment.status == status)
        
        total = (await self.db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Payment.created_at.desc()).offset(offset).limit(page_size)
        rows = (await self.db.execute(stmt)).all()
        return list(rows), total

    async def approve_payment(self, payment_id: uuid.UUID) -> tuple[Payment | None, Subscriber | None]:
        payment = await self.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return payment, None
            
        payment.status = PaymentStatus.APPROVED
        await self.db.flush()

        # Update subscriber tier
        stmt = select(Subscriber).where(Subscriber.telegram_id == payment.telegram_id)
        subscriber = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if subscriber:
            from dateutil.relativedelta import relativedelta
            now = datetime.now(timezone.utc)
            
            # Map plan to enum
            if payment.plan == "monthly":
                subscriber.subscription_tier = SubscriptionTier.MONTHLY
                subscriber.subscription_expiry = now + relativedelta(months=1)
            elif payment.plan == "yearly":
                subscriber.subscription_tier = SubscriptionTier.YEARLY
                subscriber.subscription_expiry = now + relativedelta(years=1)
            elif payment.plan == "lifetime":
                subscriber.subscription_tier = SubscriptionTier.LIFETIME
                subscriber.subscription_expiry = None
                
            await self.db.flush()
            
        log.info("payment_approved", payment_id=str(payment_id))
        return payment, subscriber

    async def reject_payment(self, payment_id: uuid.UUID) -> Payment | None:
        payment = await self.get_by_id(payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            return payment
            
        payment.status = PaymentStatus.REJECTED
        await self.db.flush()
        log.info("payment_rejected", payment_id=str(payment_id))
        return payment
