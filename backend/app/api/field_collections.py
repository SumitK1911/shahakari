from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import (
    CollectorRoute,
    FieldCollectionBatch,
    FieldCollectionEntry,
    Loan,
    LoanInstallment,
    Member,
    Permission,
    RolePermission,
    SavingsAccount,
    SavingsTransaction,
    ShareTransaction,
    User,
)
from app.schemas import (
    CollectorRouteCreate,
    CollectorRouteOut,
    FieldCollectionBatchCreate,
    FieldCollectionBatchDetail,
    FieldCollectionBatchOut,
    FieldCollectionEntryCreate,
    FieldCollectionEntryOut,
    FieldCollectionRejectIn,
    FieldCollectionSubmitIn,
    FieldCollectionSummaryOut,
    FieldCollectionVerifyIn,
)
from app.services.accounting import get_account_by_code, post_double_entry
from app.services.audit import audit
from app.services.loans import repay_installment
from app.services.savings import post_savings_transaction
from app.services.shares import purchase_shares

router = APIRouter()
SUPPORTED_COLLECTION_TYPES = {"savings_deposit", "loan_repayment", "share_purchase", "fee_collection"}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def has_permission(session: AsyncSession, user: User, permission_name: str) -> bool:
    if user.role_id is None:
        return False
    permission_id = await session.scalar(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id, Permission.name == permission_name)
    )
    return permission_id is not None


async def can_review_all_batches(session: AsyncSession, user: User) -> bool:
    return await has_permission(session, user, "field_collections.verify") or await has_permission(session, user, "field_collections.manage")


async def batch_total(session: AsyncSession, batch_id: UUID) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(FieldCollectionEntry.amount), 0)).where(
            FieldCollectionEntry.batch_id == batch_id,
            FieldCollectionEntry.status != "rejected",
        )
    )
    return Decimal(total or 0)


async def refresh_batch_total(session: AsyncSession, batch: FieldCollectionBatch) -> None:
    batch.collected_total = await batch_total(session, batch.id)


async def get_batch_or_404(session: AsyncSession, batch_id: UUID) -> FieldCollectionBatch:
    batch = await session.get(FieldCollectionBatch, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Field collection batch not found")
    return batch


async def assert_batch_visible(session: AsyncSession, user: User, batch: FieldCollectionBatch) -> None:
    if batch.collector_id == user.id:
        return
    if await can_review_all_batches(session, user):
        return
    raise HTTPException(status_code=403, detail="Field collection batch is not assigned to this user")


async def validate_entry_payload(session: AsyncSession, payload: FieldCollectionEntryCreate) -> None:
    if payload.collection_type not in SUPPORTED_COLLECTION_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported collection type")
    member = await session.get(Member, payload.member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    if payload.collection_type == "savings_deposit":
        if payload.savings_account_id is None:
            raise HTTPException(status_code=400, detail="Savings account is required")
        account = await session.get(SavingsAccount, payload.savings_account_id)
        if account is None or account.member_id != payload.member_id:
            raise HTTPException(status_code=404, detail="Savings account not found for member")
        if account.status != "active":
            raise HTTPException(status_code=409, detail="Savings account is not active")

    if payload.collection_type == "loan_repayment":
        if payload.loan_id is None or payload.loan_installment_id is None:
            raise HTTPException(status_code=400, detail="Loan and installment are required")
        loan = await session.get(Loan, payload.loan_id)
        installment = await session.get(LoanInstallment, payload.loan_installment_id)
        if loan is None or installment is None or installment.loan_id != loan.id or loan.member_id != payload.member_id:
            raise HTTPException(status_code=404, detail="Loan installment not found for member")
        if installment.status == "paid":
            raise HTTPException(status_code=409, detail="Installment is already paid")
        expected = installment.principal + installment.interest + installment.penalty
        if payload.amount != expected:
            raise HTTPException(status_code=409, detail=f"Installment amount must be {expected}")

    if payload.collection_type == "share_purchase":
        if payload.share_units is None or payload.share_rate is None:
            raise HTTPException(status_code=400, detail="Share units and rate are required")
        expected = Decimal(payload.share_units) * payload.share_rate
        if payload.amount != expected:
            raise HTTPException(status_code=409, detail=f"Share amount must be {expected}")

    if payload.collection_type == "fee_collection":
        if not payload.fee_code:
            raise HTTPException(status_code=400, detail="Fee code is required")


async def post_fee_collection(session: AsyncSession, entry: FieldCollectionEntry, user_id: UUID) -> UUID:
    cash = await get_account_by_code(session, "1000")
    fee_income = await get_account_by_code(session, "4200")
    journal = await post_double_entry(
        session,
        narration=entry.narration or f"Field fee collection {entry.receipt_no}",
        ref_type="field_collection_fee",
        ref_id=entry.id,
        debit_account_id=cash.id,
        credit_account_id=fee_income.id,
        amount=entry.amount,
        created_by=user_id,
    )
    await audit(
        session,
        user_id=user_id,
        action="field_collections.fee.post",
        module="field_collections",
        record_id=str(entry.id),
        diff={"member_id": str(entry.member_id), "fee_code": entry.fee_code, "amount": str(entry.amount)},
    )
    return journal.id


@router.get("/routes", response_model=list[CollectorRouteOut])
async def list_routes(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.read")),
) -> list[CollectorRoute]:
    stmt = select(CollectorRoute).order_by(CollectorRoute.name)
    if not await can_review_all_batches(session, user):
        stmt = stmt.where(CollectorRoute.assigned_collector_id == user.id)
    return list(await session.scalars(stmt))


@router.post("/routes", response_model=CollectorRouteOut)
async def create_route(
    payload: CollectorRouteCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.manage")),
) -> CollectorRoute:
    route = CollectorRoute(
        branch_id=payload.branch_id or user.branch_id,
        name=payload.name,
        area=payload.area,
        assigned_collector_id=payload.assigned_collector_id,
    )
    session.add(route)
    await session.flush()
    await audit(session, user_id=user.id, action="field_collections.route.create", module="field_collections", record_id=str(route.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(route)
    return route


@router.get("/summary", response_model=FieldCollectionSummaryOut)
async def collection_summary(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.read")),
) -> dict:
    batch_stmt = select(FieldCollectionBatch)
    entry_stmt = select(FieldCollectionEntry)
    if not await can_review_all_batches(session, user):
        batch_ids = select(FieldCollectionBatch.id).where(FieldCollectionBatch.collector_id == user.id)
        batch_stmt = batch_stmt.where(FieldCollectionBatch.collector_id == user.id)
        entry_stmt = entry_stmt.where(FieldCollectionEntry.batch_id.in_(batch_ids))
    batches = list(await session.scalars(batch_stmt))
    entries = list(await session.scalars(entry_stmt))
    by_type: dict[str, Decimal] = {}
    by_status: dict[str, Decimal] = {}
    for entry in entries:
        by_type[entry.collection_type] = by_type.get(entry.collection_type, Decimal("0")) + entry.amount
        by_status[entry.status] = by_status.get(entry.status, Decimal("0")) + entry.amount
    return {
        "total_batches": len(batches),
        "draft_batches": sum(1 for item in batches if item.status == "draft"),
        "submitted_batches": sum(1 for item in batches if item.status == "submitted"),
        "verified_batches": sum(1 for item in batches if item.status == "verified"),
        "posted_batches": sum(1 for item in batches if item.status == "posted"),
        "rejected_batches": sum(1 for item in batches if item.status == "rejected"),
        "collected_total": sum((entry.amount for entry in entries if entry.status != "rejected"), Decimal("0")),
        "pending_total": sum((entry.amount for entry in entries if entry.status == "pending"), Decimal("0")),
        "posted_total": sum((entry.amount for entry in entries if entry.status == "posted"), Decimal("0")),
        "by_type": by_type,
        "by_status": by_status,
    }


@router.get("/members/{member_id}/targets")
async def member_collection_targets(
    member_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.read")),
) -> dict:
    member = await session.get(Member, member_id)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    accounts = list(await session.scalars(select(SavingsAccount).where(SavingsAccount.member_id == member_id, SavingsAccount.status == "active").order_by(SavingsAccount.account_no)))
    loans = list(await session.scalars(select(Loan).where(Loan.member_id == member_id, Loan.status == "active").order_by(Loan.loan_no)))
    loan_ids = [loan.id for loan in loans]
    installments = []
    if loan_ids:
        installments = list(
            await session.scalars(
                select(LoanInstallment)
                .where(LoanInstallment.loan_id.in_(loan_ids), LoanInstallment.status != "paid")
                .order_by(LoanInstallment.due_date, LoanInstallment.installment_no)
                .limit(50)
            )
        )
    return {
        "accounts": [
            {"id": account.id, "account_no": account.account_no, "account_type": account.account_type, "balance": account.balance}
            for account in accounts
        ],
        "loans": [
            {"id": loan.id, "loan_no": loan.loan_no, "loan_type": loan.loan_type, "outstanding_principal": loan.outstanding_principal}
            for loan in loans
        ],
        "installments": [
            {
                "id": item.id,
                "loan_id": item.loan_id,
                "installment_no": item.installment_no,
                "due_date": item.due_date,
                "principal": item.principal,
                "interest": item.interest,
                "penalty": item.penalty,
                "total": item.principal + item.interest + item.penalty,
                "status": item.status,
            }
            for item in installments
        ],
    }


@router.get("/batches", response_model=list[FieldCollectionBatchOut])
async def list_batches(
    status: str | None = Query(default=None),
    mine: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.read")),
) -> list[FieldCollectionBatch]:
    stmt = select(FieldCollectionBatch).order_by(FieldCollectionBatch.collection_date.desc(), FieldCollectionBatch.created_at.desc()).limit(100)
    if status:
        stmt = stmt.where(FieldCollectionBatch.status == status)
    if mine or not await can_review_all_batches(session, user):
        stmt = stmt.where(FieldCollectionBatch.collector_id == user.id)
    return list(await session.scalars(stmt))


@router.post("/batches", response_model=FieldCollectionBatchOut)
async def create_batch(
    payload: FieldCollectionBatchCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.write")),
) -> FieldCollectionBatch:
    route = None
    if payload.route_id:
        route = await session.get(CollectorRoute, payload.route_id)
        if route is None:
            raise HTTPException(status_code=404, detail="Collector route not found")
        if route.assigned_collector_id and route.assigned_collector_id != user.id and not await has_permission(session, user, "field_collections.manage"):
            raise HTTPException(status_code=403, detail="Route is assigned to another collector")
    batch = FieldCollectionBatch(
        branch_id=user.branch_id,
        collector_id=user.id,
        route_id=payload.route_id,
        collection_date=payload.collection_date or date.today(),
        opening_cash=payload.opening_cash,
        expected_total=payload.expected_total,
    )
    session.add(batch)
    await session.flush()
    await audit(session, user_id=user.id, action="field_collections.batch.create", module="field_collections", record_id=str(batch.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(batch)
    return batch


@router.get("/batches/{batch_id}", response_model=FieldCollectionBatchDetail)
async def batch_detail(
    batch_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.read")),
) -> dict:
    batch = await get_batch_or_404(session, batch_id)
    await assert_batch_visible(session, user, batch)
    entries = list(await session.scalars(select(FieldCollectionEntry).where(FieldCollectionEntry.batch_id == batch_id).order_by(FieldCollectionEntry.collected_at.desc())))
    return {"batch": batch, "entries": entries}


@router.post("/batches/{batch_id}/entries", response_model=FieldCollectionEntryOut)
async def add_entry(
    batch_id: UUID,
    payload: FieldCollectionEntryCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.write")),
) -> FieldCollectionEntry:
    batch = await get_batch_or_404(session, batch_id)
    if batch.collector_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned collector can add entries")
    if batch.status != "draft":
        raise HTTPException(status_code=409, detail="Entries can only be added to draft batches")
    existing = await session.scalar(select(FieldCollectionEntry).where(FieldCollectionEntry.client_request_id == payload.client_request_id))
    if existing is not None:
        return existing
    await validate_entry_payload(session, payload)
    receipt_no = payload.receipt_no or f"FC-{date.today():%Y%m%d}-{str(uuid4())[:8].upper()}"
    entry = FieldCollectionEntry(
        batch_id=batch.id,
        member_id=payload.member_id,
        savings_account_id=payload.savings_account_id,
        loan_id=payload.loan_id,
        loan_installment_id=payload.loan_installment_id,
        collection_type=payload.collection_type,
        payment_method=payload.payment_method,
        amount=payload.amount,
        share_units=payload.share_units,
        share_rate=payload.share_rate,
        fee_code=payload.fee_code,
        receipt_no=receipt_no,
        client_request_id=payload.client_request_id,
        collected_at=payload.collected_at or now_utc(),
        gps_lat=payload.gps_lat,
        gps_lng=payload.gps_lng,
        device_id=payload.device_id,
        narration=payload.narration,
        metadata_json=payload.metadata_json,
    )
    session.add(entry)
    await session.flush()
    await refresh_batch_total(session, batch)
    await audit(session, user_id=user.id, action="field_collections.entry.create", module="field_collections", record_id=str(entry.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(entry)
    return entry


@router.post("/batches/{batch_id}/submit", response_model=FieldCollectionBatchOut)
async def submit_batch(
    batch_id: UUID,
    payload: FieldCollectionSubmitIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.submit")),
) -> FieldCollectionBatch:
    batch = await get_batch_or_404(session, batch_id)
    if batch.collector_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned collector can submit this batch")
    if batch.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft batches can be submitted")
    await refresh_batch_total(session, batch)
    if batch.collected_total <= 0:
        raise HTTPException(status_code=409, detail="Cannot submit an empty collection batch")
    batch.status = "submitted"
    batch.submitted_at = now_utc()
    batch.denomination_close = payload.denomination_close
    await audit(session, user_id=user.id, action="field_collections.batch.submit", module="field_collections", record_id=str(batch.id), diff={"collected_total": str(batch.collected_total)})
    await session.commit()
    await session.refresh(batch)
    return batch


@router.post("/batches/{batch_id}/verify", response_model=FieldCollectionBatchOut)
async def verify_batch(
    batch_id: UUID,
    payload: FieldCollectionVerifyIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.verify")),
) -> FieldCollectionBatch:
    batch = await get_batch_or_404(session, batch_id)
    if batch.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted batches can be verified")
    await refresh_batch_total(session, batch)
    batch.status = "verified"
    batch.verified_by = user.id
    batch.verified_at = now_utc()
    batch.denomination_close = payload.denomination_close
    batch.verification_note = payload.verification_note
    await audit(session, user_id=user.id, action="field_collections.batch.verify", module="field_collections", record_id=str(batch.id), diff={"collected_total": str(batch.collected_total), "note": payload.verification_note})
    await session.commit()
    await session.refresh(batch)
    return batch


@router.post("/batches/{batch_id}/reject", response_model=FieldCollectionBatchOut)
async def reject_batch(
    batch_id: UUID,
    payload: FieldCollectionRejectIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.verify")),
) -> FieldCollectionBatch:
    batch = await get_batch_or_404(session, batch_id)
    if batch.status not in {"submitted", "verified"}:
        raise HTTPException(status_code=409, detail="Only submitted or verified batches can be rejected")
    batch.status = "rejected"
    batch.verified_by = user.id
    batch.verified_at = now_utc()
    batch.verification_note = payload.verification_note
    await audit(session, user_id=user.id, action="field_collections.batch.reject", module="field_collections", record_id=str(batch.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(batch)
    return batch


@router.post("/batches/{batch_id}/post", response_model=FieldCollectionBatchOut)
async def post_batch(
    batch_id: UUID,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("field_collections.post")),
) -> FieldCollectionBatch:
    batch = await get_batch_or_404(session, batch_id)
    if batch.status != "verified":
        raise HTTPException(status_code=409, detail="Only verified batches can be posted")
    entries = list(await session.scalars(select(FieldCollectionEntry).where(FieldCollectionEntry.batch_id == batch.id, FieldCollectionEntry.status == "pending").order_by(FieldCollectionEntry.collected_at)))
    if not entries:
        raise HTTPException(status_code=409, detail="No pending entries to post")
    for entry in entries:
        if entry.collection_type == "savings_deposit":
            if entry.savings_account_id is None:
                raise HTTPException(status_code=400, detail="Savings account is required")
            await post_savings_transaction(
                session,
                account_id=entry.savings_account_id,
                trans_type="deposit",
                amount=entry.amount,
                narration=entry.narration or f"Field collection receipt {entry.receipt_no}",
                user_id=user.id,
            )
            posted_tx = await session.scalar(select(SavingsTransaction).where(SavingsTransaction.account_id == entry.savings_account_id, SavingsTransaction.created_by == user.id).order_by(SavingsTransaction.created_at.desc()).limit(1))
            entry.posted_transaction_id = posted_tx.id if posted_tx else None
        elif entry.collection_type == "loan_repayment":
            if entry.loan_id is None or entry.loan_installment_id is None:
                raise HTTPException(status_code=400, detail="Loan and installment are required")
            payment = await repay_installment(session, loan_id=entry.loan_id, installment_id=entry.loan_installment_id, paid_by=f"Field receipt {entry.receipt_no}", user_id=user.id)
            entry.posted_transaction_id = payment.id
        elif entry.collection_type == "share_purchase":
            if entry.share_units is None or entry.share_rate is None:
                raise HTTPException(status_code=400, detail="Share units and rate are required")
            await purchase_shares(session, member_id=entry.member_id, shares=entry.share_units, rate=entry.share_rate, narration=entry.narration or f"Field share receipt {entry.receipt_no}", user_id=user.id)
            posted_tx = await session.scalar(select(ShareTransaction).where(ShareTransaction.member_id == entry.member_id, ShareTransaction.created_by == user.id).order_by(ShareTransaction.created_at.desc()).limit(1))
            entry.posted_transaction_id = posted_tx.id if posted_tx else None
        elif entry.collection_type == "fee_collection":
            entry.posted_transaction_id = await post_fee_collection(session, entry, user.id)
        else:
            raise HTTPException(status_code=400, detail="Unsupported collection type")
        entry.status = "posted"
    await refresh_batch_total(session, batch)
    batch.status = "posted"
    batch.posted_by = user.id
    batch.posted_at = now_utc()
    await audit(session, user_id=user.id, action="field_collections.batch.post", module="field_collections", record_id=str(batch.id), diff={"entries": len(entries), "collected_total": str(batch.collected_total)})
    await session.commit()
    await session.refresh(batch)
    return batch
