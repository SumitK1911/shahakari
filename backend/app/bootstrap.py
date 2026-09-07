import asyncio

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.core.database import Base, engine
from app.seed import main as seed_main
from app import models  # noqa: F401


MEMBER_SCHEMA_PATCHES = [
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS name_nepali VARCHAR(180)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS dob_bs VARCHAR(16)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS marital_status VARCHAR(32)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS nationality VARCHAR(80) NOT NULL DEFAULT 'Nepali'",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS secondary_phone VARCHAR(40)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS email VARCHAR(180)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS emergency_contact_name VARCHAR(180)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS emergency_contact_number VARCHAR(40)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS address_profile JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS documents JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS family_profile JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS guardian_profile JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS occupation_profile JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS income_sources JSONB",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS membership_type VARCHAR(80)",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS join_date DATE",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS risk_category VARCHAR(24) NOT NULL DEFAULT 'low'",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS is_pep BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS is_blacklisted BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS internal_notes TEXT",
    "ALTER TABLE members ADD COLUMN IF NOT EXISTS media_profile JSONB",
    "ALTER TABLE member_nominees ADD COLUMN IF NOT EXISTS citizenship_number VARCHAR(80)",
    "CREATE INDEX IF NOT EXISTS ix_members_risk_category ON members (risk_category)",
    "CREATE INDEX IF NOT EXISTS ix_members_is_pep ON members (is_pep)",
    "CREATE INDEX IF NOT EXISTS ix_members_is_blacklisted ON members (is_blacklisted)",
]

FIELD_COLLECTION_SCHEMA_PATCHES = [
    "ALTER TABLE field_collection_entries ADD COLUMN IF NOT EXISTS loan_installment_id UUID REFERENCES loan_installments(id)",
    "ALTER TABLE field_collection_entries ADD COLUMN IF NOT EXISTS share_units INTEGER",
    "ALTER TABLE field_collection_entries ADD COLUMN IF NOT EXISTS share_rate NUMERIC(14, 2)",
    "ALTER TABLE field_collection_entries ADD COLUMN IF NOT EXISTS fee_code VARCHAR(60)",
    "ALTER TABLE field_collection_entries ADD COLUMN IF NOT EXISTS metadata_json JSONB",
    "CREATE INDEX IF NOT EXISTS ix_field_collection_entries_loan_installment_id ON field_collection_entries (loan_installment_id)",
    "CREATE INDEX IF NOT EXISTS ix_field_collection_entries_fee_code ON field_collection_entries (fee_code)",
]


LOAN_SCHEMA_PATCHES = [
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS applied_by UUID REFERENCES users(id)",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS recommended_by UUID REFERENCES users(id)",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES users(id)",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS disbursed_by UUID REFERENCES users(id)",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS disbursed_at TIMESTAMP WITH TIME ZONE",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS approval_limit_level VARCHAR(40)",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS purpose TEXT",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS interest_method VARCHAR(32) NOT NULL DEFAULT 'flat_monthly'",
    "ALTER TABLE loans ADD COLUMN IF NOT EXISTS repayment_method VARCHAR(32) NOT NULL DEFAULT 'emi'",
]

async def ensure_current_schema() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ProgrammingError as exc:
        if "DuplicateTableError" not in str(exc):
            raise

    async with engine.begin() as conn:
        for statement in MEMBER_SCHEMA_PATCHES:
            await conn.execute(text(statement))
        for statement in FIELD_COLLECTION_SCHEMA_PATCHES:
            await conn.execute(text(statement))
        for statement in LOAN_SCHEMA_PATCHES:
            await conn.execute(text(statement))


async def main() -> None:
    await ensure_current_schema()
    await seed_main()


if __name__ == "__main__":
    asyncio.run(main())
