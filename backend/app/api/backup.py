import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.dependencies import require_permission
from app.models import BackupRun, Loan, Member, SavingsAccount, Share, User
from app.schemas import BackupRunOut
from app.services.audit import audit

router = APIRouter()
BACKUP_DIR = Path("backups")


@router.get("/runs", response_model=list[BackupRunOut])
async def list_backups(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("backup.read")),
) -> list[BackupRun]:
    return list(await session.scalars(select(BackupRun).order_by(BackupRun.created_at.desc()).limit(100)))


@router.post("/runs", response_model=BackupRunOut)
async def create_backup_manifest(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("backup.write")),
) -> BackupRun:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    file_path = BACKUP_DIR / f"sahakari_backup_manifest_{timestamp}.json"
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "note": "Manifest backup record. Configure pg_dump encrypted backups for live production.",
        "counts": {
            "members": await session.scalar(select(func.count()).select_from(Member)) or 0,
            "savings_accounts": await session.scalar(select(func.count()).select_from(SavingsAccount)) or 0,
            "loans": await session.scalar(select(func.count()).select_from(Loan)) or 0,
            "shares": await session.scalar(select(func.count()).select_from(Share)) or 0,
        },
    }
    content = json.dumps(payload, indent=2).encode("utf-8")
    file_path.write_bytes(content)
    checksum = hashlib.sha256(content).hexdigest()
    record = BackupRun(
        backup_type="manifest",
        file_path=str(file_path),
        file_size=len(content),
        checksum=checksum,
        status="created",
        requested_by=user.id,
        notes="Production should replace manifest with encrypted pg_dump plus restore validation.",
    )
    session.add(record)
    await session.flush()
    await audit(session, user_id=user.id, action="backup.create", module="backup", record_id=str(record.id), diff={"file_path": str(file_path), "checksum": checksum})
    await session.commit()
    await session.refresh(record)
    return record


@router.post("/runs/{backup_id}/validate", response_model=BackupRunOut)
async def validate_backup(
    backup_id,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_permission("backup.write")),
) -> BackupRun:
    record = await session.get(BackupRun, backup_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Backup run not found")
    if not record.file_path or not Path(record.file_path).exists():
        record.status = "missing"
    else:
        content = Path(record.file_path).read_bytes()
        record.status = "validated" if hashlib.sha256(content).hexdigest() == record.checksum else "checksum_failed"
    await audit(session, user_id=user.id, action="backup.validate", module="backup", record_id=str(record.id), diff={"status": record.status})
    await session.commit()
    await session.refresh(record)
    return record
