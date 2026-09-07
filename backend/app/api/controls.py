from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import ComplianceAlert, ComplianceCase, LiquiditySnapshot, Member, SavingsAccount, Share, TermDeposit, User, WithdrawalRequest
from app.schemas import (
    ComplianceAlertOut,
    ComplianceCaseCreate,
    ComplianceCaseDecisionIn,
    ComplianceResolveIn,
    LiquiditySnapshotOut,
    WithdrawalDecisionIn,
    WithdrawalRequestCreate,
    WithdrawalRequestOut,
)
from app.services.audit import audit
from app.services.controls_monitoring import calculate_liquidity_snapshot, create_withdrawal_request, decide_withdrawal_request, run_compliance_scan

router = APIRouter()


@router.get("/withdrawals", response_model=list[WithdrawalRequestOut])
async def list_withdrawal_requests(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.read")),
) -> list[WithdrawalRequest]:
    stmt = select(WithdrawalRequest).order_by(WithdrawalRequest.requested_date.desc(), WithdrawalRequest.created_at.desc()).limit(300)
    if status:
        stmt = stmt.where(WithdrawalRequest.status == status)
    return list(await session.scalars(stmt))


@router.post("/withdrawals", response_model=WithdrawalRequestOut)
async def request_withdrawal(
    payload: WithdrawalRequestCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.write")),
) -> WithdrawalRequest:
    record = await create_withdrawal_request(session, **payload.model_dump(), user=user)
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/withdrawals/{request_id}/approve", response_model=WithdrawalRequestOut)
async def approve_withdrawal(
    request_id: UUID,
    payload: WithdrawalDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.decide")),
) -> WithdrawalRequest:
    record = await decide_withdrawal_request(session, request_id=request_id, status="approved", approved_amount=payload.approved_amount, decision_note=payload.decision_note, user=user)
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/withdrawals/{request_id}/reject", response_model=WithdrawalRequestOut)
async def reject_withdrawal(
    request_id: UUID,
    payload: WithdrawalDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.decide")),
) -> WithdrawalRequest:
    record = await decide_withdrawal_request(session, request_id=request_id, status="rejected", approved_amount=None, decision_note=payload.decision_note, user=user)
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/liquidity/latest", response_model=LiquiditySnapshotOut | None)
async def latest_liquidity_snapshot(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.read")),
) -> LiquiditySnapshot | None:
    return await session.scalar(select(LiquiditySnapshot).order_by(LiquiditySnapshot.created_at.desc()))


@router.post("/liquidity/snapshot", response_model=LiquiditySnapshotOut)
async def create_liquidity_snapshot(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.write")),
) -> LiquiditySnapshot:
    record = await calculate_liquidity_snapshot(session, branch_id=user.branch_id)
    await audit(session, user_id=user.id, action="controls.liquidity.snapshot", module="controls", record_id=str(record.id), diff={"ratio": str(record.liquidity_ratio)})
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/alerts", response_model=list[ComplianceAlertOut])
async def list_alerts(
    status: str | None = Query(default="open"),
    severity: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.read")),
) -> list[ComplianceAlert]:
    stmt = select(ComplianceAlert).order_by(ComplianceAlert.created_at.desc()).limit(500)
    if status:
        stmt = stmt.where(ComplianceAlert.status == status)
    if severity:
        stmt = stmt.where(ComplianceAlert.severity == severity)
    return list(await session.scalars(stmt))


@router.post("/alerts/scan")
async def scan_alerts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.write")),
) -> dict[str, int]:
    result = await run_compliance_scan(session)
    await audit(session, user_id=user.id, action="controls.alerts.scan", module="controls", diff=result)
    await session.commit()
    return result


@router.post("/alerts/{alert_id}/resolve", response_model=ComplianceAlertOut)
async def resolve_alert(
    alert_id: UUID,
    payload: ComplianceResolveIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.decide")),
) -> ComplianceAlert:
    alert = await session.get(ComplianceAlert, alert_id)
    if alert is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "resolved"
    alert.resolved_by = user.id
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolution_note = payload.resolution_note
    await audit(session, user_id=user.id, action="controls.alert.resolve", module="controls", record_id=str(alert.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    await session.refresh(alert)
    return alert


@router.get("/cases")
async def list_compliance_cases(
    status: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("compliance.cases.read")),
) -> list[dict]:
    stmt = select(ComplianceCase).order_by(ComplianceCase.created_at.desc()).limit(500)
    if status:
        stmt = stmt.where(ComplianceCase.status == status)
    rows = list(await session.scalars(stmt))
    return [{"id": str(row.id), "case_no": row.case_no, "member_id": str(row.member_id) if row.member_id else None, "alert_id": str(row.alert_id) if row.alert_id else None, "case_type": row.case_type, "risk_level": row.risk_level, "status": row.status, "narrative": row.narrative, "assigned_to": str(row.assigned_to) if row.assigned_to else None, "resolution_note": row.resolution_note, "reported_at": row.reported_at.isoformat() if row.reported_at else None} for row in rows]


@router.post("/cases")
async def create_compliance_case(
    payload: ComplianceCaseCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("compliance.cases.write")),
) -> dict:
    if payload.member_id and await session.get(Member, payload.member_id) is None:
        raise HTTPException(status_code=404, detail="Member not found")
    if payload.alert_id and await session.get(ComplianceAlert, payload.alert_id) is None:
        raise HTTPException(status_code=404, detail="Compliance alert not found")
    record = ComplianceCase(**payload.model_dump(), created_by=user.id)
    session.add(record)
    await session.flush()
    await audit(session, user_id=user.id, action="compliance.case.create", module="controls", record_id=str(record.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    return {"id": str(record.id), "case_no": record.case_no, "status": record.status}


@router.post("/cases/{case_id}/decision")
async def decide_compliance_case(
    case_id: UUID,
    payload: ComplianceCaseDecisionIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("compliance.cases.write")),
) -> dict:
    record = await session.get(ComplianceCase, case_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Compliance case not found")
    if payload.status not in {"under_review", "resolved", "reported"}:
        raise HTTPException(status_code=422, detail="Unsupported compliance case status")
    record.status = payload.status
    record.resolution_note = payload.resolution_note
    if payload.status == "resolved":
        record.resolved_at = datetime.now(timezone.utc)
    if payload.status == "reported":
        record.reported_at = datetime.now(timezone.utc)
    await audit(session, user_id=user.id, action="compliance.case.decision", module="controls", record_id=str(record.id), diff=payload.model_dump(mode="json"))
    await session.commit()
    return {"id": str(record.id), "case_no": record.case_no, "status": record.status}


@router.get("/copomis/export.csv")
async def copomis_export_csv(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("controls.read")),
) -> Response:
    members = list(await session.scalars(select(Member).order_by(Member.member_no).limit(10000)))
    savings = list(await session.scalars(select(SavingsAccount).order_by(SavingsAccount.account_no).limit(10000)))
    shares = list(await session.scalars(select(Share).limit(10000)))
    deposits = list(await session.scalars(select(TermDeposit).limit(10000)))
    lines = ["section,ref,name_or_type,status,amount,extra"]
    for member in members:
        lines.append(f"member,{member.member_no},{member.name},{member.status},0,{member.kyc_status}")
    for account in savings:
        lines.append(f"savings,{account.account_no},{account.account_type},{account.status},{account.balance},{account.member_id}")
    for share in shares:
        lines.append(f"share,{share.id},share_capital,{share.status},{share.total_amount},{share.member_id}")
    for deposit in deposits:
        lines.append(f"term_deposit,{deposit.deposit_no},{deposit.deposit_type},{deposit.status},{deposit.balance},{deposit.member_id}")
    return Response(content="\n".join(lines), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=sahakari-copomis-export.csv"})
