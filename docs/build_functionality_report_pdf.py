from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "Sahakari_Functionality_Report.pdf"

BLUE = colors.HexColor("#2E74B5")
DARK_BLUE = colors.HexColor("#1F4D78")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#617184")
LIGHT_BLUE = colors.HexColor("#E8EEF5")
LIGHT_GRAY = colors.HexColor("#F2F4F7")
PALE_GREEN = colors.HexColor("#EEF8F1")
GREEN = colors.HexColor("#126C43")


def styles():
    base = getSampleStyleSheet()
    base.add(ParagraphStyle(name="TitleBig", fontName="Helvetica-Bold", fontSize=24, leading=30, textColor=INK, spaceAfter=6))
    base.add(ParagraphStyle(name="Subtitle", fontName="Helvetica", fontSize=13, leading=17, textColor=MUTED, spaceAfter=18))
    base.add(ParagraphStyle(name="H1x", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=BLUE, spaceBefore=14, spaceAfter=8))
    base.add(ParagraphStyle(name="H2x", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=10, spaceAfter=6))
    base.add(ParagraphStyle(name="Bodyx", fontName="Helvetica", fontSize=9.6, leading=13, textColor=INK, spaceAfter=6))
    base.add(ParagraphStyle(name="Smallx", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK))
    base.add(ParagraphStyle(name="CalloutTitle", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=GREEN, spaceAfter=4))
    return base


S = styles()


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(text, S[style])


def bullet(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item), leftIndent=12) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=14,
        bulletFontSize=7,
    )


def table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[p(h, "Smallx") for h in headers]]
    data.extend([[p(str(cell), "Smallx") for cell in row] for row in rows])
    t = Table(data, colWidths=[w * inch for w in widths], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), DARK_BLUE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD6DF")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def callout(title: str, body: str, fill=PALE_GREEN) -> Table:
    content = [[p(title, "CalloutTitle")], [p(body)]]
    t = Table(content, colWidths=[6.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFD6C8")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return t


def section(story, title: str) -> None:
    story.append(p(title, "H1x"))


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(7.5 * inch, 0.5 * inch, f"Sahakari Functionality Report | Page {doc.page}")
    canvas.restoreState()


def build() -> None:
    story = []
    story.append(p("Sahakari Finance Application", "TitleBig"))
    story.append(p("Functionality Report and Comparison Checklist", "Subtitle"))
    story.append(
        callout(
            "Purpose",
            "This document summarizes the functionality currently implemented in the Sahakari cooperative finance application, how key workflows operate, what automation and reporting exist, and which production-grade features still need comparison against a real cooperative organization.",
        )
    )
    story.append(Spacer(1, 10))
    story.append(
        table(
            ["Field", "Value"],
            [
                ["Report date", date.today().isoformat()],
                ["Application type", "Local-network cooperative finance / sahakari operations system"],
                ["Frontend", "React + Vite desktop operations UI"],
                ["Backend", "FastAPI, SQLAlchemy, PostgreSQL-ready models, JWT/RBAC dependencies"],
                ["Current status", "Functional foundation with expanded operations UI; not yet complete for live regulated production"],
            ],
            [1.6, 4.9],
        )
    )
    story.append(PageBreak())

    section(story, "1. Executive Summary")
    story.append(callout("Current position", "The app is no longer only a small registration form. It now includes member onboarding, scalable member search, member 360 profile, shares, savings, cash counter, loans, repayments, accounting, rules, automation, reports, approval queues, Excel-ready export, security/compliance screens, and dashboard metrics."))
    story.append(bullet([
        "Suitable as a working prototype/foundation for a cooperative finance office.",
        "Backend includes members, nominees, shares, savings, loans, installments, payments, accounts, journals, ledgers, closings, scheduler jobs, calculations and audit logs.",
        "Frontend exposes operational workspaces instead of only a registration form.",
        "Main remaining gaps: full maker-checker approval, locked-period enforcement, richer product masters, true XLSX import/export, backup/restore UI, cashier session depth and formal financial statements.",
    ]))

    section(story, "2. Implemented Functionality Matrix")
    story.append(table(["Module", "What it does now", "Status"], [
        ["Authentication", "Staff login using email/password and JWT token storage.", "Implemented"],
        ["Dashboard", "Members, savings, loan exposure, risk, cash movement, pending KYC, high-risk cases.", "Implemented"],
        ["Member onboarding", "Detailed person form: KYC, address, documents, family, guardian, nominee, occupation, income, risk flags, media references.", "Implemented"],
        ["Member search", "Server-side search by member number, name, or phone with skip/limit paging and total count.", "Implemented"],
        ["Member 360 profile", "Member data, nominees, shares, share activity, savings accounts, savings ledger, loans, schedules, payments, calculations.", "Implemented"],
        ["Share capital", "Share purchase posting and share register display.", "Implemented"],
        ["Savings accounts", "Open savings account, list active balances, post deposit and withdrawal.", "Implemented"],
        ["Cash counter", "Deposit and withdrawal screens connected to savings transactions and ledger posting.", "Implemented"],
        ["Loans", "Loan disbursement, flat installment schedule generation, loan portfolio, schedule view, installment payment.", "Implemented"],
        ["Accounting", "Chart of accounts and trial balance endpoints/UI.", "Implemented"],
        ["Rules engine", "Interest, penalty, accrual rule CRUD/read views; calculation history.", "Implemented foundation"],
        ["Automation", "Manual automation run, daily interest trigger, overdue marking trigger, scheduler job list, calculation results.", "Implemented foundation"],
        ["Reports", "Portfolio summary, daily operations, approval queue, high-risk queue, overdue queue, trial balance.", "Implemented foundation"],
        ["Excel/export", "CSV member portfolio export, openable in Excel.", "Implemented basic"],
        ["Security/compliance", "RBAC dependencies, audit logging in services, security workspace, risk flags.", "Implemented foundation"],
        ["Closings", "Day/month/year closing models and closing register display.", "Foundation only"],
    ], [1.35, 4.55, 1.0]))

    section(story, "3. How Key Workflows Work")
    story.append(table(["Workflow", "Operational behavior"], [
        ["Member onboarding", "Staff enters personal, KYC, document, address, family, nominee, occupation, income and risk information. Backend stores the member, JSON profile sections, nominee records and audit entry."],
        ["Finding one member among 10k+", "Staff searches by member number, name or phone. Backend applies indexed search and returns paged results. Staff clicks Open to load the member 360 profile instead of scrolling thousands of rows."],
        ["Member 360 review", "The profile endpoint gathers the selected member's shares, savings accounts, savings transactions, loans, installments, payments, nominees and calculation results into one operational view."],
        ["Savings deposit", "Backend locks the account, increases balance, creates savings transaction, posts double-entry ledger lines, and writes audit log."],
        ["Savings withdrawal", "Backend checks active account and sufficient balance, decreases balance, posts transaction, ledger and audit."],
        ["Loan disbursement", "Backend creates active loan, generates flat monthly installments, posts loan disbursement ledger entry and audit log."],
        ["Loan repayment", "Staff opens loan schedule and pays an installment. Backend marks installment paid, reduces outstanding principal, posts principal and interest ledger entries, and audits the payment."],
        ["Automation run", "Admin/manager runs automation for a date. Backend calculates savings interest and overdue penalties through the rules engine, updates live records, stores calculation results and returns posting summary."],
        ["Reports/export", "Reports screen loads portfolio totals, queues and trial balance. CSV export downloads member portfolio data for Excel review."],
    ], [1.65, 4.85]))

    section(story, "4. Current Screens and API Coverage")
    story.append(p("Frontend Workspaces", "H2x"))
    story.append(table(["Screen", "Main capability"], [
        ["Dashboard", "Daily snapshot, quick actions, recent members, health signals."],
        ["Members", "Onboarding, search/paging, member 360 profile."],
        ["Shares", "Share purchase and share register."],
        ["Savings", "Open account and view account balances."],
        ["Cash Counter", "Post deposit/withdrawal and monitor counter balances."],
        ["Loans", "Disburse loan, view portfolio, open schedule, post repayment."],
        ["Reports", "Portfolio, approval queue, high-risk cases, overdue queue, trial balance, CSV export."],
        ["Automation", "Daily/monthly/fiscal automation buttons, scheduler jobs, closing register, calculations."],
        ["Rules", "Create interest rule and inspect interest/penalty/accrual rules."],
        ["Accounting", "Chart of accounts and trial balance."],
        ["Security", "Compliance controls, RBAC/audit/export/backup guidance."],
    ], [1.45, 5.05]))
    story.append(p("Backend API Groups", "H2x"))
    story.append(bullet([
        "/auth: login",
        "/dashboard: operational metrics",
        "/branches: branch list/create",
        "/members: list, count, profile, create, update, nominees",
        "/shares: list and purchase",
        "/savings: accounts, deposit, withdrawal",
        "/loans: list, create, installments, payments",
        "/accounting: chart of accounts, trial balance",
        "/reports: portfolio summary, daily operations, approval queue, CSV export",
        "/automation: manual run and async triggers",
        "/rules: interest, penalty, accrual, scheduler jobs, calculation results",
    ]))

    section(story, "5. Calculations, Ledgers and Automation")
    story.append(table(["Area", "Current behavior", "Notes"], [
        ["Savings interest", "Rules engine checks active interest rule by savings product/account type; falls back to account interest rate.", "Foundation implemented; product-level configuration should be expanded."],
        ["Penalty", "Rules engine calculates overdue installment penalty from configured rule or fallback rate.", "Supports fixed/percentage/compound concepts in rule schema."],
        ["Loan schedule", "Flat monthly principal plus monthly interest schedule generated at disbursement.", "EMI/reducing/diminishing variants are not yet fully implemented."],
        ["Double-entry ledger", "Savings, shares, loan disbursement and repayment services post journal/ledger entries.", "Needs stricter balancing audits and approval before live use."],
        ["Calculation records", "Automation stores calculation_results for traceability.", "Good foundation for explainable historical calculations."],
        ["Closings", "Models exist for day, month and year closings; UI displays closing register.", "Actual close/lock workflow needs more implementation."],
    ], [1.35, 3.35, 1.8]))

    section(story, "6. Excel and Reporting")
    story.append(callout("Excel recommendation", "Excel should be used for exports, imports, migration, audit sharing and offline review. It should not be used as the primary database for live cooperative finance records.", LIGHT_GRAY))
    story.append(bullet([
        "Available now: CSV member portfolio export at /api/v1/reports/portfolio-export.csv.",
        "CSV can be opened in Microsoft Excel and used for comparison or audit review.",
        "Recommended next step: true .xlsx exports with multiple sheets for members, savings, loans, shares, trial balance and daily cash.",
        "Recommended next step: bulk import with validation preview for opening balances and member migration.",
    ]))

    section(story, "7. Production Gap Checklist")
    story.append(table(["Feature", "Expected in real production", "Current"], [
        ["Maker-checker approval", "Formal approval screens for KYC, loan, withdrawal, adjustment, reversal, closing.", "Missing"],
        ["Locked-period enforcement", "Reject edits/postings after day/month/year close unless reversal workflow is used.", "Mostly missing"],
        ["Product masters", "Savings products, FD products, loan products, share products, fee products.", "Missing"],
        ["Advanced loan engine", "EMI, reducing balance, diminishing, partial payment, reschedule, collateral, guarantors.", "Partial"],
        ["Cashier session", "Opening cash, denomination count, handover, vault transfer, shortage/excess handling.", "Partial"],
        ["Backup/restore UI", "Encrypted backups, restore validation, backup schedule and status dashboard.", "Missing"],
        ["True XLSX reports", "Formatted multi-sheet Excel export and import validation.", "Basic CSV only"],
        ["Financial statements", "Balance sheet, profit/loss, ledger statement, cash book, member statement, regulatory reports.", "Partial"],
        ["Notifications", "SMS/email/reminder outbox for due loans, overdue, maturity, KYC expiry.", "Missing"],
        ["Session/rate limit", "Refresh tokens, session tracking, login rate limiting.", "Partial"],
        ["Branch scope", "Strict branch-scoped data access for all modules.", "Partial"],
        ["Audit viewer", "Searchable audit log UI with filters and export.", "Missing UI"],
        ["Backup of documents/media", "Real file upload/storage for photo, signature, thumbprint and KYC files.", "Reference fields only"],
    ], [1.55, 4.25, 0.7]))

    section(story, "8. Real-Organization Comparison Template")
    story.append(table(["Area to compare", "Questions for the cooperative office", "Mark"], [
        ["Membership", "What exact KYC fields, documents, nominees, guardian rules and membership types are required?", ""],
        ["Savings", "Which account products exist, interest methods, withdrawal limits, dormancy rules and fees?", ""],
        ["Loans", "What loan products, approval stages, guarantors, collateral, interest methods and penalty rules are used?", ""],
        ["Shares", "Share purchase limits, transfer/refund rules, certificate format and dividend process?", ""],
        ["Cash counter", "How many counters, cashier opening/closing process, vault movement and denomination requirements?", ""],
        ["Accounting", "Chart of accounts, voucher approval, fiscal year close, reserves and dividend postings?", ""],
        ["Reports", "Daily, monthly, annual, regulatory, board and member statement reports required?", ""],
        ["Excel", "Which data must be exported/imported, and what format does the office currently use?", ""],
        ["Security", "Roles, permissions, branch access, audit review and password/session policies?", ""],
        ["Backup", "Backup location, frequency, encryption, external drive/NAS and restore testing policy?", ""],
    ], [1.35, 4.75, 0.4]))

    section(story, "9. Recommended Next Development Phases")
    story.append(table(["Phase", "Goal", "Deliverables"], [
        ["Phase 1", "Approval and control", "Maker-checker queues, approval actions, locked-period checks, reversal workflow."],
        ["Phase 2", "Product depth", "Savings/FD/loan product masters, interest methods, fees, collateral and guarantors."],
        ["Phase 3", "Cash operations", "Cashier sessions, vault movement, denominations, handover and day close."],
        ["Phase 4", "Reports and Excel", "Member statement, passbook, cash book, balance sheet, P&L, XLSX export/import."],
        ["Phase 5", "Backup and production hardening", "Encrypted backups, restore UI, audit viewer, session/rate-limit, branch scope tests."],
    ], [0.8, 1.85, 3.85]))

    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title="Sahakari Functionality Report",
        author="Codex",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
