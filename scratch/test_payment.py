import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.payment import Payment, PaymentPlan, PaymentStatus
from app.database import Base

async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        payment = Payment(telegram_id=123, plan=PaymentPlan.MONTHLY, amount=2)
        db.add(payment)
        await db.commit()
        await db.refresh(payment)
        print("Payment created:", payment.id, payment.status, payment.plan)

asyncio.run(main())
