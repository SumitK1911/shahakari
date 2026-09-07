import asyncio
import uuid
import random
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from app.core.database import SessionLocal
from app.models import Member, Share, SavingsAccount, User

async def seed_data():
    async with SessionLocal() as session:
        # We will create 10 members
        for i in range(1, 11):
            member_no = f"TEST-{random.randint(1000, 9999)}"
            name = f"Test Member {i}"
            phone = f"98410000{i:02d}"
            
            # 1. Create Member
            member = Member(
                member_no=member_no,
                name=name,
                phone=phone,
                dob=date(1990, 1, 1),
                risk_category="low",
                status="active"
            )
            session.add(member)
            await session.flush()
            
            print(f"Created Member: {name} (ID: {member.id})")
            
            # 2. Issue Shares (100 shares at Rs 100 each = Rs 10000)
            share = Share(
                member_id=member.id,
                total_share=100,
                rate=Decimal("100.00"),
                total_amount=Decimal("10000.00"),
                status="active"
            )
            session.add(share)
            
            # 3. Open a Savings Account
            savings = SavingsAccount(
                member_id=member.id,
                account_no=f"SAV-{random.randint(10000, 99999)}",
                account_type="regular_savings",
                interest_rate=Decimal("6.5"), # 6.5% interest
                balance=Decimal("5000.00"),  # Start with 5000 balance
                status="active"
            )
            session.add(savings)
            
        await session.commit()
        print("Successfully seeded 10 members with shares and savings accounts!")

if __name__ == "__main__":
    asyncio.run(seed_data())
