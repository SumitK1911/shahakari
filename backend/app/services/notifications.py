import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import IntegrationEndpoint, Loan, LoanInstallment, Member, NotificationMessage, TermDeposit, WithdrawalRequest

DEFAULT_CHANNELS = ["sms", "whatsapp"]


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    phone = value.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+977"):
        return phone
    if phone.startswith("977"):
        return f"+{phone}"
    if phone.startswith("9") and len(phone) == 10:
        return f"+977{phone}"
    if phone.startswith("+"):
        return phone
    return phone


async def queue_notification(
    session: AsyncSession,
    *,
    channel: str,
    recipient: str,
    body: str,
    subject: str | None = None,
    template_code: str | None = None,
    metadata_json: dict | None = None,
    scheduled_for: datetime | None = None,
) -> NotificationMessage:
    message = NotificationMessage(
        channel=channel,
        recipient=recipient,
        subject=subject,
        body=body,
        template_code=template_code,
        metadata_json=metadata_json,
        scheduled_for=scheduled_for,
        status="queued",
    )
    session.add(message)
    await session.flush()
    return message


async def queue_member_notification(
    session: AsyncSession,
    *,
    member: Member,
    body: str,
    template_code: str,
    metadata_json: dict | None = None,
    channels: list[str] | None = None,
) -> int:
    recipient = normalize_phone(member.phone)
    if recipient is None:
        return 0
    queued = 0
    for channel in channels or DEFAULT_CHANNELS:
        await queue_notification(
            session,
            channel=channel,
            recipient=recipient,
            body=body,
            template_code=template_code,
            metadata_json={"member_id": str(member.id), "member_no": member.member_no, **(metadata_json or {})},
        )
        queued += 1
    return queued


async def queue_operational_notifications(session: AsyncSession, *, due_days: int = 3) -> dict[str, int]:
    today = date.today()
    due_until = today + timedelta(days=due_days)
    queued = {"loan_due": 0, "loan_overdue": 0, "maturity": 0, "kyc": 0, "withdrawal": 0}

    due_installments = list(
        await session.scalars(
            select(LoanInstallment)
            .where(LoanInstallment.due_date >= today, LoanInstallment.due_date <= due_until, LoanInstallment.status == "pending")
            .limit(500)
        )
    )
    for installment in due_installments:
        loan = await session.get(Loan, installment.loan_id)
        if loan is None:
            continue
        member = await session.get(Member, loan.member_id)
        if member is None:
            continue
        body = (
            f"Dear {member.name}, your loan installment #{installment.installment_no} of Rs. {installment.total} "
            f"is due on {installment.due_date}. Please pay on time to avoid penalty. - Sahakari"
        )
        queued["loan_due"] += await queue_member_notification(
            session,
            member=member,
            body=body,
            template_code="loan_due_reminder",
            metadata_json={"loan_id": str(loan.id), "installment_id": str(installment.id), "due_date": installment.due_date.isoformat()},
        )

    overdue_installments = list(
        await session.scalars(
            select(LoanInstallment)
            .where(LoanInstallment.due_date < today, LoanInstallment.status.in_(["pending", "overdue"]))
            .limit(500)
        )
    )
    for installment in overdue_installments:
        loan = await session.get(Loan, installment.loan_id)
        if loan is None:
            continue
        member = await session.get(Member, loan.member_id)
        if member is None:
            continue
        body = (
            f"Dear {member.name}, your loan installment #{installment.installment_no} is overdue. "
            f"Total due is Rs. {installment.total + installment.penalty}. Please contact the Sahakari office."
        )
        queued["loan_overdue"] += await queue_member_notification(
            session,
            member=member,
            body=body,
            template_code="loan_overdue_alert",
            metadata_json={"loan_id": str(loan.id), "installment_id": str(installment.id), "due_date": installment.due_date.isoformat()},
        )

    deposits = list(
        await session.scalars(
            select(TermDeposit)
            .where(TermDeposit.maturity_date >= today, TermDeposit.maturity_date <= due_until, TermDeposit.status == "active")
            .limit(500)
        )
    )
    for deposit in deposits:
        member = await session.get(Member, deposit.member_id)
        if member is None:
            continue
        body = (
            f"Dear {member.name}, your {deposit.deposit_type.upper()} {deposit.deposit_no} matures on {deposit.maturity_date}. "
            f"Expected maturity amount is Rs. {deposit.maturity_amount}. - Sahakari"
        )
        queued["maturity"] += await queue_member_notification(
            session,
            member=member,
            body=body,
            template_code="deposit_maturity_reminder",
            metadata_json={"deposit_id": str(deposit.id), "maturity_date": deposit.maturity_date.isoformat()},
        )

    pending_kyc_members = list(await session.scalars(select(Member).where(Member.kyc_status == "pending", Member.phone.is_not(None)).limit(300)))
    for member in pending_kyc_members:
        body = f"Dear {member.name}, your Sahakari KYC is pending. Please visit the office with required documents."
        queued["kyc"] += await queue_member_notification(
            session,
            member=member,
            body=body,
            template_code="kyc_pending_reminder",
            metadata_json={"kyc_status": member.kyc_status},
            channels=["sms", "whatsapp"],
        )

    approved_withdrawals = list(await session.scalars(select(WithdrawalRequest).where(WithdrawalRequest.status == "approved").limit(300)))
    for withdrawal in approved_withdrawals:
        member = await session.get(Member, withdrawal.member_id)
        if member is None:
            continue
        amount = withdrawal.approved_amount or withdrawal.requested_amount
        body = f"Dear {member.name}, your withdrawal request of Rs. {amount} has been approved. Please visit the Sahakari counter."
        queued["withdrawal"] += await queue_member_notification(
            session,
            member=member,
            body=body,
            template_code="withdrawal_approved",
            metadata_json={"withdrawal_request_id": str(withdrawal.id)},
        )

    return queued


async def dispatch_queued_notifications(session: AsyncSession, *, limit: int = 100) -> dict[str, int]:
    messages = list(
        await session.scalars(
            select(NotificationMessage)
            .where(NotificationMessage.status == "queued")
            .order_by(NotificationMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )
    sent = 0
    failed = 0
    for message in messages:
        endpoint = await session.scalar(
            select(IntegrationEndpoint).where(
                IntegrationEndpoint.integration_type == message.channel,
                IntegrationEndpoint.status == "active",
            )
        )
        if endpoint is None:
            message.status = "failed"
            message.error_message = f"No active {message.channel} integration endpoint configured"
            failed += 1
            continue
        ok, provider_id, error = send_with_endpoint(endpoint, message)
        if ok:
            message.status = "sent"
            message.provider_message_id = provider_id or f"local-{message.id}"
            message.sent_at = datetime.now(timezone.utc)
            sent += 1
        else:
            message.status = "failed"
            message.error_message = error
            failed += 1
    return {"sent": sent, "failed": failed}


def send_with_endpoint(endpoint: IntegrationEndpoint, message: NotificationMessage) -> tuple[bool, str | None, str | None]:
    config = endpoint.config or {}
    if config.get("dry_run", True):
        return True, f"dry-run-{message.id}", None
    if message.channel == "whatsapp":
        return send_whatsapp_cloud(endpoint, message)
    return False, None, f"Live provider for {message.channel} is not configured; set dry_run=true or implement provider credentials"


def send_whatsapp_cloud(endpoint: IntegrationEndpoint, message: NotificationMessage) -> tuple[bool, str | None, str | None]:
    config = endpoint.config or {}
    token = config.get("access_token")
    phone_number_id = config.get("phone_number_id")
    api_version = config.get("api_version", "v20.0")
    if not token or not phone_number_id:
        return False, None, "WhatsApp Cloud API requires access_token and phone_number_id in integration config"
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": message.recipient.replace("+", ""),
        "type": "text",
        "text": {"preview_url": False, "body": message.body},
    }
    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
            messages = body.get("messages") or []
            return True, messages[0].get("id") if messages else None, None
    except HTTPError as exc:
        return False, None, exc.read().decode("utf-8", errors="ignore")
    except URLError as exc:
        return False, None, str(exc)
