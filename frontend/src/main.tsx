import React, { FormEvent, useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import {
  BadgeCheck,
  Banknote,
  BookOpenCheck,
  Building2,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  CircleDollarSign,
  Coins,
  DatabaseBackup,
  Download,
  FileText,
  HandCoins,
  Landmark,
  LayoutDashboard,
  Loader2,
  LockKeyhole,
  MapPin,
  Smartphone,
  PiggyBank,
  Plus,
  Play,
  RefreshCw,
  ReceiptText,
  Search,
  Settings2,
  ShieldCheck,
  Trash2,
  UserRound,
  UsersRound,
  Vault,
  Workflow,
  Activity,
  TrendingUp
} from "lucide-react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { fullDateLabel, todayBSString as getTodayNepali } from "./utils/nepali-date";
import "./styles.css";


if ("serviceWorker" in navigator && window.location.protocol !== "file:") {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => undefined);
  });
}

const API_BASE = window.sahakariDesktop || window.location.protocol === "file:" ? "http://127.0.0.1:8000/api/v1" : "/api/v1";

type Token = { access_token: string };
type Metrics = {
  total_members: number;
  active_savings_accounts: number;
  total_savings: string;
  active_loans: number;
  loan_outstanding: string;
  overdue_installments: number;
  pending_installments: number;
  penalty_receivable: string;
  collection_today: string;
  recent_transactions: { id: string; amount: string; type: string; date: string }[];
};
type Member = {
  id: string; member_no: string; name: string; name_nepali?: string; phone?: string;
  secondary_phone?: string; email?: string; kyc_status: string; status: string;
  risk_category?: string; dob?: string; dob_bs?: string; gender?: string;
  marital_status?: string; nationality?: string; membership_type?: string;
  join_date?: string; emergency_contact_name?: string; emergency_contact_number?: string;
  is_pep?: boolean; is_blacklisted?: boolean; internal_notes?: string;
};
type SavingsAccount = { id: string; member_id: string; account_no: string; account_type: string; interest_rate: string; balance: string; status: string };
type Loan = { id: string; member_id: string; loan_no: string; loan_type: string; amount: string; interest_rate: string; tenure_months: number; outstanding_principal: string; status: string };
type LoanInstallment = { id: string; loan_id: string; installment_no: number; due_date: string; principal: string; interest: string; penalty: string; total: string; status: string };
type Share = { id: string; member_id: string; total_share: number; rate: string; total_amount: string; status: string };
type MemberProfile = {
  member: Member;
  nominees: { name: string; relation: string; phone?: string; address?: string }[];
  shares: Share[];
  share_transactions: { trans_type: string; shares: number; rate: string; amount: string; trans_date: string; narration?: string }[];
  savings_accounts: SavingsAccount[];
  savings_transactions: { account_id: string; trans_type: string; amount: string; balance: string; trans_date: string; narration?: string }[];
  loans: Loan[];
  loan_installments: { loan_id: string; installment_no: number; due_date: string; principal: string; interest: string; penalty: string; total: string; status: string }[];
  loan_payments: { loan_id: string; payment_date: string; principal_paid: string; interest_paid: string; penalty_paid: string; total_paid: string; paid_by?: string }[];
  calculation_results: CalculationResult[];
};
type Account = { id: string; code: string; name: string; type: string; is_active: boolean };
type TrialBalanceRow = { account_code: string; account_name: string; debit: string; credit: string; balance: string };
type ReportSummary = { total_share_capital: string; total_savings_liability: string; loan_principal_outstanding: string; overdue_principal: string; active_members: number };
type RuleRecord = { id: string; scope_type: string; scope_code: string; method?: string; posting_frequency?: string; calculation_frequency?: string; annual_rate?: string; frequency?: string; fixed_amount?: string; percentage_rate?: string; accrual_type?: string; debit_account_code?: string; credit_account_code?: string; is_active: boolean; created_at: string };
type SchedulerJob = { id: string; name: string; job_type: string; cron_expression: string; timezone: string; status: string; last_run_at?: string; next_run_at?: string };
type CalculationResult = { id: string; result_type: string; target_type: string; calculation_date_ad: string; base_amount: string; rate: string; days: number; amount: string; status: string };
type DailyOperations = { cash_in: string; cash_out: string; share_cash_in: string; pending_kyc: number; high_risk_members: number; overdue_installments: number; day_closings: { closing_date_ad: string; closing_date_bs?: string; status: string }[] };
type ApprovalQueue = { pending_members: { id: string; member_no: string; name: string; phone?: string; risk_category?: string }[]; high_risk_members: { id: string; member_no: string; name: string; phone?: string; risk_category?: string }[]; overdue_installments: { id: string; loan_id: string; installment_no: number; due_date: string; total: string; penalty: string; status: string }[] };
type LiquiditySnapshot = { id: string; snapshot_date: string; cash_balance: string; liquid_assets: string; member_savings_liability: string; term_deposit_liability: string; pending_withdrawals: string; liquidity_ratio: string; status: string; notes?: string };
type ComplianceAlert = { id: string; rule_code: string; module: string; severity: string; title: string; description: string; status: string; created_at: string };
type WithdrawalRequest = { id: string; member_id: string; requested_amount: string; approved_amount?: string; requested_date: string; needed_by_date?: string; priority: string; status: string; reason?: string };
type SystemPolicy = { id: string; code: string; name: string; policy_type: string; config: Record<string, unknown>; status: string };
type GovernanceDecision = { id: string; decision_body: string; meeting_no?: string; decision_date?: string; title: string; decision_text: string; status: string };
type FieldVisit = { id: string; member_id: string; loan_id?: string; visit_date?: string; purpose: string; findings?: string; recommendation?: string };
type CollectorRoute = { id: string; name: string; area?: string; assigned_collector_id?: string; status: string };
type FieldCollectionBatch = { id: string; branch_id?: string; collector_id: string; route_id?: string; collection_date: string; opening_cash: string; expected_total: string; collected_total: string; submitted_at?: string; verified_by?: string; verified_at?: string; posted_by?: string; posted_at?: string; status: string; verification_note?: string };
type FieldCollectionEntry = { id: string; batch_id: string; member_id: string; savings_account_id?: string; loan_id?: string; loan_installment_id?: string; collection_type: string; payment_method: string; amount: string; share_units?: number; share_rate?: string; fee_code?: string; receipt_no: string; client_request_id: string; collected_at: string; device_id?: string; narration?: string; status: string };
type FieldCollectionDetail = { batch: FieldCollectionBatch; entries: FieldCollectionEntry[] };
type FieldCollectionSummary = { total_batches: number; draft_batches: number; submitted_batches: number; verified_batches: number; posted_batches: number; rejected_batches: number; collected_total: string; pending_total: string; posted_total: string; by_type: Record<string, string>; by_status: Record<string, string> };
type FieldTargets = { accounts: { id: string; account_no: string; account_type: string; balance: string }[]; loans: { id: string; loan_no: string; loan_type: string; outstanding_principal: string }[]; installments: { id: string; loan_id: string; installment_no: number; due_date: string; principal: string; interest: string; penalty: string; total: string; status: string }[] };
type OfflineFieldEntry = {
  id: string;
  batchId: string;
  body: Record<string, string>;
  createdAt: string;
  status: "queued" | "syncing" | "failed";
  attempts: number;
  lastError?: string;
};
type OrganizationPosition = { code: string; title: string; level: string; reports_to_code?: string; status: string };
type Investment = {
  id: string;
  investment_no: string;
  investment_type: string;
  institution_name: string;
  instrument_name?: string;
  amount: string;
  current_value: string;
  interest_rate: string;
  invested_date: string;
  maturity_date?: string;
  maturity_amount: string;
  status: string;
  notes?: string;
};
type InvestmentTransaction = {
  id: string;
  investment_id: string;
  trans_type: string;
  amount: string;
  trans_date: string;
  narration?: string;
};
type InvestmentSummary = {
  total_invested: string;
  total_current_value: string;
  total_interest_received: string;
  active_count: number;
  matured_count: number;
  maturing_within_30_days: number;
  by_type: Record<string, string>;
};
type ViewId = "dashboard" | "members" | "shares" | "savings" | "cash" | "field" | "loans" | "reports" | "automation" | "rules" | "accounting" | "investments" | "security";
type NavItem = { id: ViewId; label: string; icon: React.ElementType; helper: string };
type DesktopRole = "cashier" | "manager" | "accountant" | "admin";
type AutomationResult = {
  run_date: string;
  savings_interest_transactions: number;
  savings_interest_amount: string;
  auto_deducted_installments: number;
  auto_deducted_amount: string;
  overdue_installments: number;
  penalty_amount: string;
  period: string;
  message: string;
};
type AddressValues = { province: string; district: string; municipality: string; ward_no: string; tole: string };
type DocumentValues = { document_type: string; document_number: string; issue_date: string; issue_district: string; expiry_date: string; front_image: string; back_image: string };
type IncomeValues = { income_type: string; monthly_amount: string; description: string };
type PersonFormValues = {
  member_no: string;
  name: string;
  name_nepali: string;
  gender: string;
  dob: string;
  dob_bs: string;
  marital_status: string;
  nationality: string;
  phone: string;
  secondary_phone: string;
  email: string;
  emergency_contact_name: string;
  emergency_contact_number: string;
  permanent: AddressValues;
  temporary_same_as_permanent: boolean;
  temporary: AddressValues;
  family_profile: { father_name: string; mother_name: string; grandfather_name: string; spouse_name: string };
  guardian_profile: { name: string; relationship: string; citizenship_number: string; mobile_number: string; address: string };
  nominee: { name: string; relation: string; phone: string; address: string; citizenship_number: string };
  occupation_profile: { occupation_type: string; employer_name: string; job_position: string; work_address: string; monthly_income: string; annual_income: string };
  membership_type: string;
  join_date: string;
  risk_category: string;
  is_pep: boolean;
  is_blacklisted: boolean;
  internal_notes: string;
  media_profile: { profile_photo: string; signature_image: string; thumbprint: string };
};

const emptyMetrics: Metrics = {
  total_members: 0,
  active_savings_accounts: 0,
  total_savings: "0",
  active_loans: 0,
  loan_outstanding: "0",
  overdue_installments: 0,
  pending_installments: 0,
  penalty_receivable: "0",
  collection_today: "0",
  recent_transactions: []
};
const emptyAddress: AddressValues = { province: "", district: "", municipality: "", ward_no: "", tole: "" };
const emptyDocument: DocumentValues = { document_type: "Citizenship Certificate", document_number: "", issue_date: "", issue_district: "", expiry_date: "", front_image: "", back_image: "" };
const emptyIncome: IncomeValues = { income_type: "Salary Income", monthly_amount: "", description: "" };
const emptyPersonForm: PersonFormValues = {
  member_no: "",
  name: "",
  name_nepali: "",
  gender: "",
  dob: "",
  dob_bs: "",
  marital_status: "",
  nationality: "Nepali",
  phone: "",
  secondary_phone: "",
  email: "",
  emergency_contact_name: "",
  emergency_contact_number: "",
  permanent: emptyAddress,
  temporary_same_as_permanent: true,
  temporary: emptyAddress,
  family_profile: { father_name: "", mother_name: "", grandfather_name: "", spouse_name: "" },
  guardian_profile: { name: "", relationship: "", citizenship_number: "", mobile_number: "", address: "" },
  nominee: { name: "", relation: "", phone: "", address: "", citizenship_number: "" },
  occupation_profile: { occupation_type: "", employer_name: "", job_position: "", work_address: "", monthly_income: "", annual_income: "" },
  membership_type: "",
  join_date: "",
  risk_category: "low",
  is_pep: false,
  is_blacklisted: false,
  internal_notes: "",
  media_profile: { profile_photo: "", signature_image: "", thumbprint: "" }
};

const navItems: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, helper: "Overview" },
  { id: "members", label: "Members", icon: BadgeCheck, helper: "Onboarding and KYC" },
  { id: "shares", label: "Shares", icon: Coins, helper: "Capital and certificates" },
  { id: "savings", label: "Savings", icon: PiggyBank, helper: "Accounts and balances" },
  { id: "cash", label: "Cash Counter", icon: Vault, helper: "Deposit and withdraw" },
  { id: "field", label: "Field Collection", icon: Smartphone, helper: "Daily collector batches" },
  { id: "loans", label: "Loans", icon: HandCoins, helper: "Portfolio and disbursement" },
  { id: "reports", label: "Reports", icon: ReceiptText, helper: "Portfolio and trial balance" },
  { id: "automation", label: "Automation", icon: Workflow, helper: "Closing routines" },
  { id: "rules", label: "Rules", icon: Settings2, helper: "Interest and penalty" },
  { id: "accounting", label: "Accounting", icon: BookOpenCheck, helper: "Controls and ledgers" },
  { id: "investments", label: "Investments", icon: TrendingUp, helper: "FDs, bonds and equities" },
  { id: "security", label: "Security", icon: ShieldCheck, helper: "Access and audit" }
];

const viewTitles: Record<ViewId, { title: string; description: string }> = {
  dashboard: {
    title: "Operations Dashboard",
    description: "A clean control room for daily cooperative activity, balances, risk and recent records."
  },
  members: {
    title: "Member Management",
    description: "Register people, complete KYC details, and review member records without crowding the dashboard."
  },
  shares: {
    title: "Share Capital Desk",
    description: "Purchase shares, track member capital, and keep ownership records visible for dividend work."
  },
  savings: {
    title: "Savings Desk",
    description: "Open savings accounts and monitor active account balances from one focused workspace."
  },
  cash: {
    title: "Cash Counter",
    description: "Handle daily deposits and withdrawals with account selection, narration, and immediate balance refresh."
  },
  field: {
    title: "Field Collection",
    description: "Record door-to-door daily collections, submit collector batches, and verify cash before posting."
  },
  loans: {
    title: "Loan Desk",
    description: "Create loans, review outstanding principal, and keep repayment risk visible."
  },
  reports: {
    title: "Reports Room",
    description: "Review portfolio summary, share capital, liabilities, outstanding loans, and accounting balances."
  },
  automation: {
    title: "Automation Engine",
    description: "Run daily, monthly and fiscal closing routines with clear posting results."
  },
  rules: {
    title: "Financial Rules Engine",
    description: "Configure and inspect interest, penalty, accrual, scheduler, and calculation records."
  },
  accounting: {
    title: "Accounting Controls",
    description: "A visual summary of posting, reconciliation and close-control areas."
  },
  security: {
    title: "Security Center",
    description: "Track operational safeguards, audit posture and controlled access areas."
  },
  investments: {
    title: "Investments Portfolio",
    description: "Track the cooperative's external investments — Fixed Deposits, shares, bonds and more."
  }
};

declare global {
  interface Window {
    sahakariDesktop?: { role?: DesktopRole; platform?: string };
  }
}

const roleViews: Record<DesktopRole, ViewId[]> = {
  cashier: ["dashboard", "members", "savings", "cash", "field", "shares"],
  manager: ["dashboard", "members", "field", "loans", "reports", "automation", "rules", "security"],
  accountant: ["dashboard", "cash", "field", "accounting", "reports", "shares", "savings", "loans"],
  admin: ["dashboard", "members", "shares", "savings", "cash", "field", "loans", "reports", "automation", "rules", "accounting", "investments", "security"]
};

function desktopRole(): DesktopRole {
  const queryRole = new URLSearchParams(window.location.search).get("desktopRole") as DesktopRole | null;
  const role = window.sahakariDesktop?.role || queryRole || "admin";
  return ["cashier", "manager", "accountant", "admin"].includes(role) ? role : "admin";
}

function currency(value: string | number) {
  return `Rs. ${Number(value || 0).toLocaleString("en-NP", { maximumFractionDigits: 2 })}`;
}

function memberName(members: Member[], memberId: string) {
  const member = members.find((item) => item.id === memberId);
  return member ? `${member.member_no} - ${member.name}` : memberId.slice(0, 8);
}

function accountName(accounts: SavingsAccount[], accountId?: string) {
  if (!accountId) return "-";
  const account = accounts.find((item) => item.id === accountId);
  return account ? account.account_no : accountId.slice(0, 8);
}

function fieldEntryTarget(entry: FieldCollectionEntry, accounts: SavingsAccount[], loans: Loan[]) {
  if (entry.collection_type === "savings_deposit") return accountName(accounts, entry.savings_account_id);
  if (entry.collection_type === "loan_repayment") return loans.find((loan) => loan.id === entry.loan_id)?.loan_no || entry.loan_id?.slice(0, 8) || "-";
  if (entry.collection_type === "share_purchase") return `${entry.share_units || 0} shares`;
  if (entry.collection_type === "fee_collection") return entry.fee_code || "fee";
  return "-";
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-NP", { dateStyle: "medium", timeStyle: "short" });
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function compactObject<T extends Record<string, unknown>>(value: T) {
  return Object.fromEntries(Object.entries(value).filter(([, entry]) => entry !== "" && entry !== null && entry !== undefined)) as Partial<T>;
}

const FIELD_QUEUE_DB = "sahakari-field-queue";
const FIELD_QUEUE_STORE = "entries";

function openFieldQueueDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(FIELD_QUEUE_DB, 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(FIELD_QUEUE_STORE)) db.createObjectStore(FIELD_QUEUE_STORE, { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function fieldQueuePut(entry: OfflineFieldEntry) {
  const db = await openFieldQueueDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(FIELD_QUEUE_STORE, "readwrite");
    tx.objectStore(FIELD_QUEUE_STORE).put(entry);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function fieldQueueDelete(id: string) {
  const db = await openFieldQueueDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(FIELD_QUEUE_STORE, "readwrite");
    tx.objectStore(FIELD_QUEUE_STORE).delete(id);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

async function fieldQueueAll(): Promise<OfflineFieldEntry[]> {
  const db = await openFieldQueueDb();
  const items = await new Promise<OfflineFieldEntry[]>((resolve, reject) => {
    const tx = db.transaction(FIELD_QUEUE_STORE, "readonly");
    const request = tx.objectStore(FIELD_QUEUE_STORE).getAll();
    request.onsuccess = () => resolve(request.result as OfflineFieldEntry[]);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return items.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

function calculateAge(dob: string) {
  if (!dob) return null;
  const birthDate = new Date(`${dob}T00:00:00`);
  if (Number.isNaN(birthDate.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - birthDate.getFullYear();
  const monthDelta = now.getMonth() - birthDate.getMonth();
  if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birthDate.getDate())) age -= 1;
  return age;
}

function useApi(token: string | null) {
  return useMemo(() => {
    async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
      const response = await fetch(`${API_BASE}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...init.headers
        }
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed: ${response.status}`);
      }
      return response.json();
    }
    return { request };
  }, [token]);
}

function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [email, setEmail] = useState("admin@sahakari.local");
  const [password, setPassword] = useState("ChangeMe123!");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!response.ok) throw new Error("Login failed");
      const data = (await response.json()) as Token;
      localStorage.setItem("sahakari_token", data.access_token);
      onLogin(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not login");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submit}>
        <div className="brand compact">
          <div className="brand-mark">S</div>
          <div>
            <strong>Sahakari</strong>
            <span>Desktop operations core</span>
          </div>
        </div>
        <h1>Staff Login</h1>
        <label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <LockKeyhole />} Login</button>
      </form>
    </main>
  );
}

function App() {
  const appRole = desktopRole();
  const visibleNavItems = navItems.filter((item) => roleViews[appRole].includes(item.id));
  const [token, setToken] = useState(localStorage.getItem("sahakari_token"));
  const { request } = useApi(token);
  const [metrics, setMetrics] = useState<Metrics>(emptyMetrics);
  const [members, setMembers] = useState<Member[]>([]);
  const [accounts, setAccounts] = useState<SavingsAccount[]>([]);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [selectedLoan, setSelectedLoan] = useState<Loan | null>(null);
  const [loanInstallments, setLoanInstallments] = useState<LoanInstallment[]>([]);
  const [shares, setShares] = useState<Share[]>([]);
  const [memberProfile, setMemberProfile] = useState<MemberProfile | null>(null);
  const [memberTotal, setMemberTotal] = useState(0);
  const [memberSkip, setMemberSkip] = useState(0);
  const [chartAccounts, setChartAccounts] = useState<Account[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceRow[]>([]);
  const [portfolio, setPortfolio] = useState<ReportSummary | null>(null);
  const [interestRules, setInterestRules] = useState<RuleRecord[]>([]);
  const [penaltyRules, setPenaltyRules] = useState<RuleRecord[]>([]);
  const [accrualRules, setAccrualRules] = useState<RuleRecord[]>([]);
  const [schedulerJobs, setSchedulerJobs] = useState<SchedulerJob[]>([]);
  const [calculationResults, setCalculationResults] = useState<CalculationResult[]>([]);
  const [dailyOps, setDailyOps] = useState<DailyOperations | null>(null);
  const [approvalQueue, setApprovalQueue] = useState<ApprovalQueue | null>(null);
  const [liquidity, setLiquidity] = useState<LiquiditySnapshot | null>(null);
  const [complianceAlerts, setComplianceAlerts] = useState<ComplianceAlert[]>([]);
  const [withdrawalQueue, setWithdrawalQueue] = useState<WithdrawalRequest[]>([]);
  const [systemPolicies, setSystemPolicies] = useState<SystemPolicy[]>([]);
  const [governanceDecisions, setGovernanceDecisions] = useState<GovernanceDecision[]>([]);
  const [fieldVisits, setFieldVisits] = useState<FieldVisit[]>([]);
  const [organizationPositions, setOrganizationPositions] = useState<OrganizationPosition[]>([]);
  const [collectorRoutes, setCollectorRoutes] = useState<CollectorRoute[]>([]);
  const [fieldBatches, setFieldBatches] = useState<FieldCollectionBatch[]>([]);
  const [activeFieldBatch, setActiveFieldBatch] = useState<FieldCollectionDetail | null>(null);
  const [fieldSummary, setFieldSummary] = useState<FieldCollectionSummary | null>(null);
  const [automation, setAutomation] = useState<AutomationResult | null>(null);
  const [investments, setInvestments] = useState<Investment[]>([]);
  const [investmentSummary, setInvestmentSummary] = useState<InvestmentSummary | null>(null);
  const [selectedInvestment, setSelectedInvestment] = useState<Investment | null>(null);
  const [investmentTransactions, setInvestmentTransactions] = useState<InvestmentTransaction[]>([]);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [offlineEntries, setOfflineEntries] = useState<OfflineFieldEntry[]>([]);
  const [query, setQuery] = useState("");
  const [activeView, setActiveView] = useState<ViewId>(visibleNavItems[0]?.id || "dashboard");
  const currentView = viewTitles[activeView];

  async function loadData(search = query, skip = memberSkip) {
    if (!token) return;
    const memberParams = new URLSearchParams({ limit: "50", skip: `${skip}` });
    const countParams = new URLSearchParams();
    if (search.trim().length >= 2) {
      memberParams.set("q", search.trim());
      countParams.set("q", search.trim());
    }
    const [
      metricData,
      memberCountData,
      memberData,
      accountData,
      loanData,
      shareData,
      chartData,
      trialData,
      portfolioData,
      interestData,
      penaltyData,
      accrualData,
      schedulerData,
      calculationData,
      dailyData,
      queueData
    ] = await Promise.all([
      request<Metrics>("/dashboard/metrics"),
      request<{ total: number }>(`/members/count${countParams.toString() ? `?${countParams}` : ""}`),
      request<Member[]>(`/members?${memberParams}`),
      request<SavingsAccount[]>("/savings/accounts"),
      request<Loan[]>("/loans"),
      request<Share[]>("/shares"),
      request<Account[]>("/accounting/accounts"),
      request<TrialBalanceRow[]>("/accounting/trial-balance"),
      request<ReportSummary>("/reports/portfolio-summary"),
      request<RuleRecord[]>("/rules/interest-rules"),
      request<RuleRecord[]>("/rules/penalty-rules"),
      request<RuleRecord[]>("/rules/accrual-rules"),
      request<SchedulerJob[]>("/rules/scheduler-jobs"),
      request<CalculationResult[]>("/rules/calculation-results"),
      request<DailyOperations>("/reports/daily-operations"),
      request<ApprovalQueue>("/reports/approval-queue")
    ]);
    setMetrics(metricData);
    setMemberTotal(memberCountData.total);
    setMembers(memberData);
    setAccounts(accountData);
    setLoans(loanData);
    setShares(shareData);
    setChartAccounts(chartData);
    setTrialBalance(trialData);
    setPortfolio(portfolioData);
    setInterestRules(interestData);
    setPenaltyRules(penaltyData);
    setAccrualRules(accrualData);
    setSchedulerJobs(schedulerData);
    setCalculationResults(calculationData);
    setDailyOps(dailyData);
    setApprovalQueue(queueData);
    const [liquidityData, alertData, withdrawalData, policyData, decisionData, fieldVisitData, orgData, routeData, fieldBatchData, fieldSummaryData] = await Promise.all([
      request<LiquiditySnapshot | null>("/controls/liquidity/latest").catch(() => null),
      request<ComplianceAlert[]>("/controls/alerts").catch(() => []),
      request<WithdrawalRequest[]>("/controls/withdrawals?status=pending").catch(() => []),
      request<SystemPolicy[]>("/governance/policies").catch(() => []),
      request<GovernanceDecision[]>("/governance/decisions").catch(() => []),
      request<FieldVisit[]>("/governance/field-visits").catch(() => []),
      request<OrganizationPosition[]>("/governance/organization").catch(() => []),
      request<CollectorRoute[]>("/field-collections/routes").catch(() => []),
      request<FieldCollectionBatch[]>("/field-collections/batches").catch(() => []),
      request<FieldCollectionSummary>("/field-collections/summary").catch(() => null)
    ]);
    setLiquidity(liquidityData);
    setComplianceAlerts(alertData);
    setWithdrawalQueue(withdrawalData);
    setSystemPolicies(policyData);
    setGovernanceDecisions(decisionData);
    setFieldVisits(fieldVisitData);
    setOrganizationPositions(orgData);
    setCollectorRoutes(routeData);
    setFieldBatches(fieldBatchData);
    setFieldSummary(fieldSummaryData);
    // Investments
    const [invData, invSummary] = await Promise.all([
      request<Investment[]>("/investments").catch(() => []),
      request<InvestmentSummary>("/investments/summary").catch(() => null)
    ]);
    setInvestments(invData);
    setInvestmentSummary(invSummary);
  }

  useEffect(() => {
    loadData().catch((err) => {
      setMessage(err instanceof Error ? err.message : "Could not load data");
      if (`${err}`.includes("401")) setToken(null);
    });
  }, [token]);

  async function refreshOfflineEntries() {
    const entries = await fieldQueueAll().catch(() => []);
    setOfflineEntries(entries);
  }

  useEffect(() => {
    refreshOfflineEntries();
    const updateOnline = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    return () => {
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
    };
  }, []);

  useEffect(() => {
    if (isOnline && token && offlineEntries.some((entry) => entry.status !== "syncing")) {
      syncOfflineFieldEntries().catch((err) => setMessage(err instanceof Error ? err.message : "Offline sync failed"));
    }
  }, [isOnline, token]);

  async function submitJson(path: string, body: object, done: string) {
    setBusy(path);
    setMessage("");
    try {
      await request(path, { method: "POST", body: JSON.stringify(body) });
      setMessage(done);
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy("");
    }
  }


  async function runControlsScan() {
    setBusy("controls-scan");
    setMessage("");
    try {
      await request("/controls/alerts/scan", { method: "POST" });
      await request("/controls/liquidity/snapshot", { method: "POST" });
      setMessage("Risk and liquidity controls refreshed.");
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Controls scan failed");
    } finally {
      setBusy("");
    }
  }
  async function runAutomation(periodDate: string) {
    setBusy("automation");
    setMessage("");
    try {
      const result = await request<AutomationResult>("/automation/run", {
        method: "POST",
        body: JSON.stringify({ run_date: periodDate })
      });
      setAutomation(result);
      setMessage(result.message);
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Automation failed");
    } finally {
      setBusy("");
    }
  }

  async function postDividends(rate: number) {
    setBusy("automation-dividend");
    setMessage("");
    try {
      const result = await request<{paid_to_savings: number, paid_to_cash: number, total_dividend: string}>("/automation/post-dividends", {
        method: "POST",
        body: JSON.stringify({ dividend_rate_percent: rate })
      });
      setMessage(`Dividends distributed: ${result.paid_to_savings} to savings, ${result.paid_to_cash} to cash. Total: ${currency(result.total_dividend)}`);
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Dividend distribution failed");
    } finally {
      setBusy("");
    }
  }

  async function openMemberProfile(memberId: string) {
    setBusy(`member-profile-${memberId}`);
    setMessage("");
    try {
      const profile = await request<MemberProfile>(`/members/${memberId}/profile`);
      setMemberProfile(profile);
      setActiveView("members");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not load member profile");
    } finally {
      setBusy("");
    }
  }

  async function recalculateLoan(loanId: string, newRate: number) {
    if (!newRate || newRate <= 0) return;
    setBusy(`recalc-loan-${loanId}`);
    setMessage("");
    try {
      await request(`/loans/${loanId}/recalculate`, {
        method: "POST",
        body: JSON.stringify({ new_interest_rate: newRate })
      });
      setMessage("Loan future EMIs recalculated successfully.");
      if (selectedLoan) {
        await openLoanSchedule({ ...selectedLoan, interest_rate: newRate.toString() });
      }
      await loadData();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not recalculate loan");
    } finally {
      setBusy("");
    }
  }

  async function openLoanSchedule(loan: Loan) {
    setBusy(`loan-schedule-${loan.id}`);
    setMessage("");
    try {
      const installments = await request<LoanInstallment[]>(`/loans/${loan.id}/installments`);
      setSelectedLoan(loan);
      setLoanInstallments(installments);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not load loan schedule");
    } finally {
      setBusy("");
    }
  }

  async function payInstallment(installmentId: string) {
    if (!selectedLoan) return;
    setBusy(`pay-${installmentId}`);
    setMessage("");
    try {
      await request(`/loans/${selectedLoan.id}/payments`, { method: "POST", body: JSON.stringify({ installment_id: installmentId, paid_by: "Cash counter" }) });
      setMessage("Loan installment paid");
      await openLoanSchedule(selectedLoan);
      await loadData(query, memberSkip);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not post installment payment");
    } finally {
      setBusy("");
    }
  }


  async function openFieldBatch(batchId: string) {
    setBusy(`field-batch-${batchId}`);
    setMessage("");
    try {
      const detail = await request<FieldCollectionDetail>(`/field-collections/batches/${batchId}`);
      setActiveFieldBatch(detail);
      setActiveView("field");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not open field batch");
    } finally {
      setBusy("");
    }
  }

  async function fieldAction(path: string, body: object, done: string, batchId?: string) {
    setBusy(path);
    setMessage("");
    try {
      await request(path, { method: "POST", body: JSON.stringify(body) });
      setMessage(done);
      await loadData(query, memberSkip);
      if (batchId) await openFieldBatch(batchId);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Field collection action failed");
    } finally {
      setBusy("");
    }
  }


  async function queueFieldEntry(batchId: string, body: Record<string, string>) {
    const queuedBody = {
      ...body,
      client_request_id: body.client_request_id || `offline-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      collected_at: body.collected_at || new Date().toISOString()
    };
    const entry: OfflineFieldEntry = {
      id: queuedBody.client_request_id,
      batchId,
      body: queuedBody,
      createdAt: new Date().toISOString(),
      status: "queued",
      attempts: 0
    };
    await fieldQueuePut(entry);
    await refreshOfflineEntries();
    setMessage("Collection saved offline. It will sync when network returns.");
  }

  async function submitFieldEntry(batchId: string, body: Record<string, string>) {
    if (!isOnline) {
      await queueFieldEntry(batchId, body);
      return;
    }
    try {
      await fieldAction(`/field-collections/batches/${batchId}/entries`, body, "Collection entry saved", batchId);
    } catch {
      await queueFieldEntry(batchId, body);
    }
  }

  async function syncOfflineFieldEntries() {
    if (!token || !navigator.onLine) return;
    const entries = await fieldQueueAll();
    if (!entries.length) return;
    setBusy("offline-sync");
    let synced = 0;
    for (const entry of entries) {
      await fieldQueuePut({ ...entry, status: "syncing", attempts: entry.attempts + 1 });
      try {
        await request(`/field-collections/batches/${entry.batchId}/entries`, { method: "POST", body: JSON.stringify(entry.body) });
        await fieldQueueDelete(entry.id);
        synced += 1;
      } catch (err) {
        await fieldQueuePut({ ...entry, status: "failed", attempts: entry.attempts + 1, lastError: err instanceof Error ? err.message : "Sync failed" });
      }
    }
    await refreshOfflineEntries();
    await loadData(query, memberSkip);
    if (activeFieldBatch) await openFieldBatch(activeFieldBatch.batch.id);
    setBusy("");
    setMessage(synced ? `${synced} offline collection entries synced.` : "Offline entries could not sync yet.");
  }

  function runMemberSearch() {
    setMemberSkip(0);
    loadData(query, 0).catch((err) => setMessage(err instanceof Error ? err.message : "Could not search members"));
  }

  function changeMemberPage(nextSkip: number) {
    const normalized = Math.max(0, nextSkip);
    setMemberSkip(normalized);
    loadData(query, normalized).catch((err) => setMessage(err instanceof Error ? err.message : "Could not load members"));
  }

  if (!token) return <Login onLogin={setToken} />;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">S</div>
          <div>
            <strong>Sahakari</strong>
            <span>Management System</span>
          </div>
        </div>
        <div className="branch-card">
          <Building2 />
          <div>
            <strong>Main Branch</strong>
            <span>Operational workspace</span>
          </div>
        </div>
        <nav>
          {visibleNavItems.map(({ id, label, icon: Icon, helper }) => (
            <button key={id} className={activeView === id ? "active" : ""} title={label} onClick={() => setActiveView(id)}>
              <Icon />
              <span><strong>{label}</strong><small>{helper}</small></span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span>{appRole[0].toUpperCase()}{appRole.slice(1)} desktop</span>
          <strong>{getTodayNepali()}</strong>
          <small style={{display: 'block', color: 'var(--text-secondary)', fontSize: '0.8rem'}}>{today()}</small>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <span className="eyebrow">Sahakari core banking</span>
            <h1>{currentView.title}</h1>
            <p>{currentView.description}</p>
          </div>
          <div className="topbar-actions">
            <label className="search">
              <Search size={18} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === "Enter" && runMemberSearch()} placeholder="Search member no, name, phone" />
            </label>
            <button className="icon-button" onClick={() => loadData(query, memberSkip)} title="Refresh"><RefreshCw /> Refresh</button>
            <button onClick={() => { localStorage.removeItem("sahakari_token"); setToken(null); }} title="Logout">Logout</button>
          </div>
        </header>

        {message && <div className="notice">{message}</div>}

        <section className="metrics-grid">
          <Metric label="Members" value={metrics.total_members} detail="registered records" icon={UsersRound} />
          <Metric label="Savings" value={currency(metrics.total_savings)} detail={`${metrics.active_savings_accounts} active accounts`} icon={PiggyBank} />
          <Metric label="Loans" value={currency(metrics.loan_outstanding)} detail={`${metrics.active_loans} active loans`} icon={CircleDollarSign} />
          <Metric label="Collections" value={currency(metrics.collection_today)} detail="Collected today" icon={Banknote} />
        </section>

        {activeView === "dashboard" && (
          <section className="main-grid dashboard-grid">
            <Panel title="Daily Snapshot" icon={LayoutDashboard} className="hero-panel">
              <div className="snapshot">
                <div>
                  <span>Total savings</span>
                  <strong>{currency(metrics.total_savings)}</strong>
                  <p>{metrics.active_savings_accounts} savings accounts are active.</p>
                </div>
                <div>
                  <span>Loan exposure</span>
                  <strong>{currency(metrics.loan_outstanding)}</strong>
                  <p>{metrics.pending_installments} installments pending review.</p>
                </div>
                <div>
                  <span>Collection risk</span>
                  <strong>{metrics.overdue_installments}</strong>
                  <p>{currency(metrics.penalty_receivable)} penalty receivable.</p>
                </div>
                <div>
                  <span>Cash movement</span>
                  <strong>{currency(Number(dailyOps?.cash_in || 0) - Number(dailyOps?.cash_out || 0))}</strong>
                  <p>{currency(dailyOps?.cash_in || "0")} in, {currency(dailyOps?.cash_out || "0")} out.</p>
                </div>
              </div>
            </Panel>

            <Panel title="Recent Transactions" icon={Activity} className="hero-panel">
              <div className="table-panel">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Type</th>
                      <th>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.recent_transactions?.map((tx, idx) => (
                      <tr key={idx}>
                        <td>{tx.date.slice(0, 10)}</td>
                        <td><span className={`status-pill ${tx.type === "deposit" ? "success" : "warning"}`}>{tx.type}</span></td>
                        <td><strong>Rs. {tx.amount}</strong></td>
                      </tr>
                    ))}
                    {(!metrics.recent_transactions || metrics.recent_transactions.length === 0) && (
                      <tr><td colSpan={3} style={{textAlign: "center", padding: "16px"}}>No recent transactions</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Activity Trend" icon={Activity} className="hero-panel">
              <div style={{ width: '100%', height: 250 }}>
                <ResponsiveContainer>
                  <BarChart data={metrics.recent_transactions?.slice().reverse() || []}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tickFormatter={(val) => val.slice(5,10)} />
                    <YAxis />
                    <Tooltip cursor={{fill: 'var(--bg-tertiary)'}} contentStyle={{backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)', borderRadius: '8px'}} />
                    <Bar dataKey="amount" fill="var(--brand-primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>

            <Panel title="Quick Actions" icon={CheckCircle2}>
              <div className="quick-actions">
                <button onClick={() => setActiveView("members")}><UserRound /> New member</button>
                <button onClick={() => setActiveView("shares")}><Coins /> Buy shares</button>
                <button onClick={() => setActiveView("savings")}><PiggyBank /> Open savings</button>
                <button onClick={() => setActiveView("cash")}><Vault /> Cash counter</button>
                <button onClick={() => setActiveView("loans")}><HandCoins /> Disburse loan</button>
                <button onClick={() => setActiveView("reports")}><ReceiptText /> Reports</button>
                <button onClick={() => setActiveView("automation")}><Workflow /> Closing run</button>
              </div>
            </Panel>

            <Panel title="Recent Members" icon={BadgeCheck} className="table-panel wide-panel">
              <DataTable headers={["No", "Name", "Phone", "KYC", "Status"]} rows={members.slice(0, 6).map((item) => [item.member_no, item.name, item.phone || "-", item.kyc_status, item.status])} />
            </Panel>

            <Panel title="Portfolio Health" icon={ShieldCheck}>
              <ul className="check-list">
                <li><CheckCircle2 /> {currency(portfolio?.total_share_capital || "0")} share capital is tracked</li>
                <li><CheckCircle2 /> {metrics.active_savings_accounts} savings accounts are open</li>
                <li><CheckCircle2 /> {metrics.active_loans} active loans are being tracked</li>
                <li><CheckCircle2 /> {dailyOps?.pending_kyc || 0} KYC records need approval</li>
                <li><CheckCircle2 /> {dailyOps?.high_risk_members || 0} high-risk/PEP/blacklist cases are flagged</li>
                <li><CheckCircle2 /> {schedulerJobs.length} scheduler jobs are registered</li>
              </ul>
            </Panel>
          </section>
        )}

        {activeView === "members" && (
          <section className="main-grid focused-grid">
            <Panel title="Person Onboarding" icon={UserRound} className="onboarding-panel">
              <PersonOnboardingForm busy={busy === "/members"} request={request} reload={loadData} setBusy={setBusy} setMessage={setMessage} />
            </Panel>
            <Panel title="Members" icon={BadgeCheck} className="table-panel wide-panel">
              <MemberDirectory members={members} busy={busy} onOpen={openMemberProfile} />
              <div className="pager">
                <span>{memberTotal ? `${memberSkip + 1}-${Math.min(memberSkip + members.length, memberTotal)} of ${memberTotal} members` : "No members found"}</span>
                <div>
                  <button disabled={memberSkip === 0} onClick={() => changeMemberPage(memberSkip - 50)}>Previous</button>
                  <button disabled={memberSkip + members.length >= memberTotal} onClick={() => changeMemberPage(memberSkip + 50)}>Next</button>
                </div>
              </div>
            </Panel>
            {memberProfile && (
              <Panel title="Member 360 Profile" icon={ClipboardCheck} className="wide-panel">
                <MemberProfileView profile={memberProfile} />
              </Panel>
            )}
          </section>
        )}

        {activeView === "savings" && (
          <section className="main-grid focused-grid">
            <Panel title="Open Savings Account" icon={PiggyBank}>
              <SelectForm members={members} fields={["account_no", "account_type", "interest_rate"]} labels={["Account No", "Type", "Annual Interest %"]} submit="Open Account" busy={busy === "/savings/accounts"} onSubmit={(body) => submitJson("/savings/accounts", body, "Savings account opened")} />
            </Panel>
            <Panel title="Savings Accounts" icon={PiggyBank} className="table-panel wide-panel">
              <DataTable headers={["Account", "Type", "Interest", "Balance", "Status"]} rows={accounts.map((item) => [item.account_no, item.account_type, `${item.interest_rate}%`, currency(item.balance), item.status])} />
            </Panel>
          </section>
        )}

        {activeView === "shares" && (
          <section className="main-grid focused-grid">
            <Panel title="Share Purchase" icon={Coins}>
              <SelectForm members={members} fields={["shares", "rate", "narration"]} labels={["Number of Shares", "Rate Per Share", "Narration"]} submit="Post Share Purchase" busy={busy === "/shares/purchase"} onSubmit={(body) => submitJson("/shares/purchase", body, "Share capital posted")} />
            </Panel>
            <Panel title="Share Register" icon={Landmark} className="table-panel wide-panel">
              <DataTable headers={["Member", "Shares", "Rate", "Amount", "Status"]} rows={shares.map((item) => [memberName(members, item.member_id), `${item.total_share}`, currency(item.rate), currency(item.total_amount), item.status])} />
            </Panel>
          </section>
        )}

        {activeView === "cash" && (
          <section className="main-grid focused-grid">
            <Panel title="Deposit Cash" icon={Banknote}>
              <CashTransactionForm accounts={accounts} busy={busy.startsWith("deposit")} submit="Post Deposit" onSubmit={(accountId, body) => submitJson(`/savings/accounts/${accountId}/deposit`, body, "Deposit posted")} />
            </Panel>
            <Panel title="Withdraw Cash" icon={Vault}>
              <CashTransactionForm accounts={accounts} busy={busy.startsWith("withdraw")} submit="Post Withdrawal" onSubmit={(accountId, body) => submitJson(`/savings/accounts/${accountId}/withdraw`, body, "Withdrawal posted")} />
            </Panel>
            <Panel title="Counter Balances" icon={PiggyBank} className="table-panel wide-panel">
              <DataTable headers={["Account", "Member", "Type", "Balance", "Status"]} rows={accounts.map((item) => [item.account_no, memberName(members, item.member_id), item.account_type, currency(item.balance), item.status])} />
            </Panel>
          </section>
        )}


        {activeView === "field" && (
          <section className="main-grid focused-grid">
            <Panel title="Field Summary" icon={Smartphone} className="wide-panel">
              <div className="action-row">
                <span className={isOnline ? "status-pill" : "status-pill warning"}>{isOnline ? "Online" : "Offline"}</span>
                <button disabled={!isOnline || !offlineEntries.length || busy === "offline-sync"} onClick={syncOfflineFieldEntries}>{busy === "offline-sync" ? <Loader2 className="spin" /> : <RefreshCw />} Sync Offline Queue</button>
              </div>
              <div className="snapshot">
                <div><span>Collected</span><strong>{currency(fieldSummary?.collected_total || 0)}</strong><p>{fieldSummary?.total_batches || 0} collection batches.</p></div>
                <div><span>Pending Post</span><strong>{currency(fieldSummary?.pending_total || 0)}</strong><p>{fieldSummary?.submitted_batches || 0} submitted, {fieldSummary?.verified_batches || 0} verified.</p></div>
                <div><span>Offline Queue</span><strong>{offlineEntries.length}</strong><p>{offlineEntries.filter((entry) => entry.status === "failed").length} entries need retry.</p></div>
                <div><span>Posted</span><strong>{currency(fieldSummary?.posted_total || 0)}</strong><p>{fieldSummary?.posted_batches || 0} batches posted to ledgers.</p></div>
              </div>
            </Panel>
            <Panel title="Create Route" icon={MapPin}>
              <FieldRouteForm busy={busy === "/field-collections/routes"} onSubmit={(body) => fieldAction("/field-collections/routes", body, "Collection route created")} />
            </Panel>
            <Panel title="Collector Batch" icon={Smartphone}>
              <FieldBatchForm routes={collectorRoutes} busy={busy === "/field-collections/batches"} onSubmit={(body) => fieldAction("/field-collections/batches", body, "Field collection batch opened")} />
            </Panel>
            <Panel title="Record Collection" icon={Banknote}>
              <FieldEntryForm batch={activeFieldBatch?.batch || null} members={members} accounts={accounts} loans={loans} request={request} busy={busy.includes("/entries")} onSubmit={submitFieldEntry} />
            </Panel>
            <Panel title="Batch Controls" icon={ClipboardCheck}>
              <FieldBatchControls batch={activeFieldBatch?.batch || null} busy={busy} onSubmit={(batchId) => fieldAction(`/field-collections/batches/${batchId}/submit`, {}, "Batch submitted for cashier verification", batchId)} onVerify={(batchId) => fieldAction(`/field-collections/batches/${batchId}/verify`, { verification_note: "Physical cash verified at counter" }, "Batch verified", batchId)} onPost={(batchId) => fieldAction(`/field-collections/batches/${batchId}/post`, {}, "Verified field collection posted", batchId)} />
            </Panel>
            <Panel title="Field Batches" icon={ReceiptText} className="table-panel wide-panel">
              <FieldBatchTable batches={fieldBatches} routes={collectorRoutes} busy={busy} onOpen={openFieldBatch} onVerify={(batch) => fieldAction(`/field-collections/batches/${batch.id}/verify`, { verification_note: "Physical cash verified at counter" }, "Batch verified", batch.id)} onPost={(batch) => fieldAction(`/field-collections/batches/${batch.id}/post`, {}, "Verified field collection posted", batch.id)} />
            </Panel>
            {offlineEntries.length > 0 && (
              <Panel title="Offline Queue" icon={DatabaseBackup} className="table-panel wide-panel">
                <DataTable headers={["Created", "Type", "Amount", "Status", "Attempts", "Last Error"]} rows={offlineEntries.map((entry) => [formatDateTime(entry.createdAt), entry.body.collection_type || "collection", currency(entry.body.amount || 0), entry.status, `${entry.attempts}`, entry.lastError || "-"])} />
              </Panel>
            )}
            {activeFieldBatch && (
              <Panel title="Collection Entries" icon={ReceiptText} className="table-panel wide-panel">
                <DataTable headers={["Receipt", "Type", "Member", "Target", "Amount", "Method", "Status"]} rows={activeFieldBatch.entries.map((entry) => [entry.receipt_no, entry.collection_type, memberName(members, entry.member_id), fieldEntryTarget(entry, accounts, loans), currency(entry.amount), entry.payment_method, entry.status])} />
              </Panel>
            )}
          </section>
        )}

        {activeView === "loans" && (
          <section className="main-grid focused-grid">
            <Panel title="Loan Application" icon={HandCoins}>
              <SelectForm members={members} fields={["loan_no", "loan_type", "amount", "interest_rate", "tenure_months", "purpose"]} labels={["Loan No", "Type", "Amount", "Annual Interest %", "Tenure Months", "Purpose"]} submit="Create Application" busy={busy === "/loans"} onSubmit={(body) => submitJson("/loans", body, "Loan application created for review")} />
            </Panel>
            <Panel title="Guarantor" icon={UsersRound}>
              <Form fields={["loan_id", "name", "phone", "citizenship_number", "guarantee_amount"]} labels={["Loan ID", "Name", "Phone", "Citizenship No", "Guarantee Amount"]} submit="Attach Guarantor" busy={busy.includes("/guarantors")} onSubmit={({ loan_id, ...body }) => submitJson(`/loans/${loan_id}/guarantors`, body, "Guarantor attached")} />
            </Panel>
            <Panel title="Collateral" icon={Landmark}>
              <Form fields={["loan_id", "collateral_type", "description", "assessed_value", "document_ref"]} labels={["Loan ID", "Type", "Description", "Assessed Value", "Document Ref"]} submit="Attach Collateral" busy={busy.includes("/collaterals")} onSubmit={({ loan_id, ...body }) => submitJson(`/loans/${loan_id}/collaterals`, body, "Collateral attached")} />
            </Panel>
            <Panel title="Loan Portfolio" icon={CircleDollarSign} className="table-panel wide-panel">
              <LoanPortfolio loans={loans} busy={busy} onOpen={openLoanSchedule} onReview={(loan) => submitJson(`/loans/${loan.id}/reviews`, { stage: "credit_review", recommendation: "recommend", comments: "Recommended after document and member review" }, "Loan recommended for approval")} onApprove={(loan) => submitJson(`/loans/${loan.id}/approve`, { approval_limit_level: "branch_manager", comments: "Approved within delegated authority" }, "Loan approved; ready for disbursement")} onDisburse={(loan) => submitJson(`/loans/${loan.id}/disburse`, {}, "Loan disbursed and EMI schedule generated")} />
            </Panel>
            {selectedLoan && (
              <Panel title={`Repayment Schedule ${selectedLoan.loan_no}`} icon={ReceiptText} className="table-panel wide-panel">
                <div style={{ padding: '1rem', display: 'flex', gap: '1rem', alignItems: 'center', borderBottom: '1px solid var(--border-color)' }}>
                    <label>Floating Rate Update (%):</label>
                    <input id="new_rate_input" type="number" step="0.1" defaultValue={selectedLoan.interest_rate} style={{ width: '80px', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-card)' }} />
                    <button onClick={() => recalculateLoan(selectedLoan.id, parseFloat((document.getElementById('new_rate_input') as HTMLInputElement).value))} disabled={busy === `recalc-loan-${selectedLoan.id}`}><Settings2 /> Recalculate Future EMIs</button>
                </div>
                <LoanSchedule installments={loanInstallments} busy={busy} onPay={payInstallment} />
              </Panel>
            )}
          </section>
        )}

        {activeView === "reports" && (
          <section className="main-grid focused-grid">
            <Panel title="Portfolio Summary" icon={ReceiptText} className="wide-panel">
              <div className="snapshot">
                <div><span>Share capital</span><strong>{currency(portfolio?.total_share_capital || "0")}</strong><p>{portfolio?.active_members || 0} active members.</p></div>
                <div><span>Savings liability</span><strong>{currency(portfolio?.total_savings_liability || "0")}</strong><p>Member deposits and interest-bearing balances.</p></div>
                <div><span>Loan outstanding</span><strong>{currency(portfolio?.loan_principal_outstanding || "0")}</strong><p>{currency(portfolio?.overdue_principal || "0")} overdue principal.</p></div>
                <div><span>Excel export</span><strong>CSV</strong><p><a href="/api/v1/reports/portfolio-export.csv"><Download /> Download member portfolio</a></p></div>
              </div>
            </Panel>
            <Panel title="Approval Queue" icon={ClipboardCheck} className="table-panel wide-panel">
              <DataTable headers={["Member No", "Name", "Phone", "Risk"]} rows={(approvalQueue?.pending_members || []).map((item) => [item.member_no, item.name, item.phone || "-", item.risk_category || "-"])} />
            </Panel>
            <Panel title="High Risk Cases" icon={ShieldCheck} className="table-panel wide-panel">
              <DataTable headers={["Member No", "Name", "Phone", "Risk"]} rows={(approvalQueue?.high_risk_members || []).map((item) => [item.member_no, item.name, item.phone || "-", item.risk_category || "-"])} />
            </Panel>
            <Panel title="Overdue Collection Queue" icon={Banknote} className="table-panel wide-panel">
              <DataTable headers={["Due Date", "Installment", "Total", "Penalty", "Status"]} rows={(approvalQueue?.overdue_installments || []).map((item) => [item.due_date, `${item.installment_no}`, currency(item.total), currency(item.penalty), item.status])} />
            </Panel>
            <Panel title="Trial Balance" icon={BookOpenCheck} className="table-panel wide-panel">
              <DataTable headers={["Code", "Account", "Debit", "Credit", "Balance"]} rows={trialBalance.map((item) => [item.account_code, item.account_name, currency(item.debit), currency(item.credit), currency(item.balance)])} />
            </Panel>
          </section>
        )}

        {activeView === "automation" && (
          <section className="main-grid focused-grid">
            <Panel title="Automation Engine" icon={Workflow} className="automation-panel">
              <div className="action-row" style={{ marginTop: '1rem' }}>
                <button className="primary" disabled={busy === "automation"} onClick={() => runAutomation(today())}><Play /> Run Daily Close</button>
                <button onClick={() => runAutomation(`${today().slice(0, 8)}01`)}><CalendarClock /> Monthly Close</button>
              </div>
              
              <div className="action-row" style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>
                 <button onClick={() => postDividends(10)} disabled={busy === "automation-dividend"}><Banknote /> Distribute Share Dividends (10%)</button>
                 <button onClick={() => runAutomation(`${new Date().getFullYear()}-07-16`)}><CalendarClock /> Fiscal Year Run</button>
              </div>
              <ul className="check-list" style={{ marginTop: '1rem' }}>
                <li><CheckCircle2 /> Loan EMI Auto-deducted from active savings accounts.</li>
                <li><CheckCircle2 /> Savings interest calculated and posted.</li>
                <li><CheckCircle2 /> Overdue loans penalized (based on admin rules).</li>
                <li><CheckCircle2 /> Share dividends auto-deposited to primary savings.</li>
              </ul>
              {automation && (
                <div className="result-box">
                  <strong>{automation.period} on {automation.run_date}</strong>
                  <span>{automation.auto_deducted_installments} EMI auto-deductions: {currency(automation.auto_deducted_amount)} collected</span>
                  <span>{automation.savings_interest_transactions} interest postings: {currency(automation.savings_interest_amount)} paid</span>
                  <span>{automation.overdue_installments} overdue checks: {currency(automation.penalty_amount)} new penalty added</span>
                </div>
              )}
            </Panel>
            <Panel title="Scheduler Jobs" icon={CalendarClock} className="table-panel wide-panel">
              <DataTable headers={["Name", "Type", "Cron", "Status", "Next Run"]} rows={schedulerJobs.map((item) => [item.name, item.job_type, item.cron_expression, item.status, item.next_run_at ? formatDateTime(item.next_run_at) : "-"])} />
            </Panel>
            <Panel title="Closing Register" icon={DatabaseBackup} className="table-panel wide-panel">
              <DataTable headers={["AD Date", "BS Date", "Status"]} rows={(dailyOps?.day_closings || []).map((item) => [item.closing_date_ad, item.closing_date_bs || "-", item.status])} />
            </Panel>
            <Panel title="Calculation History" icon={ClipboardCheck} className="table-panel wide-panel">
              <DataTable headers={["Type", "Target", "Date", "Base", "Amount", "Status"]} rows={calculationResults.slice(0, 12).map((item) => [item.result_type, item.target_type, item.calculation_date_ad, currency(item.base_amount), currency(item.amount), item.status])} />
            </Panel>
          </section>
        )}

        {activeView === "rules" && (
          <section className="main-grid focused-grid">
            <Panel title="Create Interest Rule" icon={Settings2}>
              <Form fields={["scope_type", "scope_code", "method", "posting_frequency", "calculation_frequency", "annual_rate", "effective_from_ad"]} labels={["Scope Type", "Scope Code", "Method", "Posting Frequency", "Calculation Frequency", "Annual Rate", "Effective From AD"]} submit="Create Rule" busy={busy === "/rules/interest-rules"} onSubmit={(body) => submitJson("/rules/interest-rules", body, "Interest rule created")} />
            </Panel>
            <Panel title="Interest Rules" icon={Settings2} className="table-panel wide-panel">
              <DataTable headers={["Scope", "Method", "Posting", "Rate", "Active"]} rows={interestRules.map((item) => [`${item.scope_type}:${item.scope_code}`, item.method || "-", item.posting_frequency || "-", `${item.annual_rate || 0}%`, item.is_active ? "yes" : "no"])} />
            </Panel>
            <Panel title="Penalty Rules" icon={Banknote} className="table-panel wide-panel">
              <DataTable headers={["Scope", "Method", "Frequency", "Fixed", "Rate"]} rows={penaltyRules.map((item) => [`${item.scope_type}:${item.scope_code}`, item.method || "-", item.frequency || "-", currency(item.fixed_amount || "0"), `${item.percentage_rate || 0}%`])} />
            </Panel>
            <Panel title="Accrual Rules" icon={Workflow} className="table-panel wide-panel">
              <DataTable headers={["Scope", "Type", "Frequency", "Debit", "Credit"]} rows={accrualRules.map((item) => [`${item.scope_type}:${item.scope_code}`, item.accrual_type || "-", item.frequency || "-", item.debit_account_code || "-", item.credit_account_code || "-"])} />
            </Panel>
          </section>
        )}

        {activeView === "accounting" && (
          <section className="main-grid focused-grid">
            <Panel title="Chart of Accounts" icon={BookOpenCheck} className="table-panel wide-panel">
              <DataTable headers={["Code", "Name", "Type", "Active"]} rows={chartAccounts.map((item) => [item.code, item.name, item.type, item.is_active ? "yes" : "no"])} />
            </Panel>
            <Panel title="Trial Balance" icon={ReceiptText} className="table-panel wide-panel">
              <DataTable headers={["Code", "Account", "Debit", "Credit", "Balance"]} rows={trialBalance.map((item) => [item.account_code, item.account_name, currency(item.debit), currency(item.credit), currency(item.balance)])} />
            </Panel>
          </section>
        )}

        {activeView === "investments" && (
          <section className="main-grid focused-grid">
            {/* ── KPI Cards ── */}
            <Panel title="Investment Portfolio Summary" icon={TrendingUp} className="wide-panel">
              <div className="metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '1rem', padding: '1rem 0' }}>
                {[
                  { label: "Total Invested", value: currency(investmentSummary?.total_invested || "0"), color: "#6366f1" },
                  { label: "Current Value", value: currency(investmentSummary?.total_current_value || "0"), color: "#10b981" },
                  { label: "Interest Earned", value: currency(investmentSummary?.total_interest_received || "0"), color: "#f59e0b" },
                  { label: "Active", value: String(investmentSummary?.active_count || 0), color: "#3b82f6" },
                  { label: "Matured", value: String(investmentSummary?.matured_count || 0), color: "#8b5cf6" },
                  { label: "Maturing ≤ 30 days", value: String(investmentSummary?.maturing_within_30_days || 0), color: "#ef4444" },
                ].map(kpi => (
                  <div key={kpi.label} style={{ background: 'var(--bg-card)', border: `2px solid ${kpi.color}22`, borderRadius: '12px', padding: '1rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 700, color: kpi.color }}>{kpi.value}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>{kpi.label}</div>
                  </div>
                ))}
              </div>
              {investmentSummary?.by_type && Object.keys(investmentSummary.by_type).length > 0 && (
                <div style={{ padding: '0 1rem 1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', alignSelf: 'center' }}>By type:</span>
                  {Object.entries(investmentSummary.by_type).map(([t, v]) => (
                    <span key={t} style={{ background: 'var(--bg-hover)', borderRadius: '20px', padding: '3px 12px', fontSize: '0.8rem', fontWeight: 600 }}>
                      {t.toUpperCase()}: {currency(v)}
                    </span>
                  ))}
                </div>
              )}
            </Panel>

            {/* ── Add Investment Form ── */}
            <Panel title="Record New Investment" icon={Plus} className="form-panel">
              <SelectForm
                members={[]}
                fields={["investment_no", "investment_type", "institution_name", "instrument_name", "amount", "interest_rate", "invested_date", "maturity_date", "notes"]}
                labels={["Investment No.", "Type (fd/share/bond/mutual_fund/debenture/other)", "Institution Name", "Instrument Name", "Amount (Rs.)", "Annual Interest Rate (%)", "Invested Date (YYYY-MM-DD)", "Maturity Date (optional)", "Notes (optional)"]}
                submit="Record Investment"
                busy={busy === "/investments"}
                onSubmit={async (body) => {
                  setBusy("/investments");
                  setMessage("");
                  try {
                    await request("/investments", { method: "POST", body: JSON.stringify({
                      ...body,
                      amount: body.amount,
                      interest_rate: body.interest_rate || "0",
                      maturity_date: body.maturity_date || undefined,
                    })});
                    setMessage("Investment recorded successfully.");
                    await loadData();
                  } catch (err) {
                    setMessage(err instanceof Error ? err.message : "Could not save investment");
                  } finally {
                    setBusy("");
                  }
                }}
              />
            </Panel>

            {/* ── Investment Portfolio Table ── */}
            <Panel title="All Investments" icon={Landmark} className="table-panel wide-panel">
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>No.</th><th>Type</th><th>Institution</th><th>Invested</th><th>Rate</th>
                      <th>Maturity</th><th>Amount</th><th>Current Value</th><th>Status</th><th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {investments.length === 0 && (
                      <tr><td colSpan={10} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No investments recorded yet. Add one above.</td></tr>
                    )}
                    {investments.map(inv => {
                      const daysToMaturity = inv.maturity_date ? Math.ceil((new Date(inv.maturity_date).getTime() - Date.now()) / 86400000) : null;
                      const maturityColor = daysToMaturity !== null ? (daysToMaturity <= 0 ? "#ef4444" : daysToMaturity <= 30 ? "#f59e0b" : "#10b981") : "var(--text-secondary)";
                      const statusColor: Record<string, string> = { active: "#10b981", matured: "#8b5cf6", redeemed: "#6b7280", written_off: "#ef4444" };
                      return (
                        <tr key={inv.id} style={{ cursor: 'pointer' }} onClick={async () => {
                          setSelectedInvestment(inv);
                          const txs = await request<InvestmentTransaction[]>(`/investments/${inv.id}/transactions`).catch(() => []);
                          setInvestmentTransactions(txs);
                        }}>
                          <td><strong>{inv.investment_no}</strong></td>
                          <td><span style={{ background: 'var(--bg-hover)', borderRadius: '10px', padding: '2px 8px', fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: 600 }}>{inv.investment_type}</span></td>
                          <td>{inv.institution_name}{inv.instrument_name ? <><br/><small style={{color:'var(--text-secondary)'}}>{inv.instrument_name}</small></> : null}</td>
                          <td>{fullDateLabel(inv.invested_date)}</td>
                          <td>{inv.interest_rate}%</td>
                          <td style={{ color: maturityColor }}>
                            {inv.maturity_date ? <>
                              {fullDateLabel(inv.maturity_date)}
                              {daysToMaturity !== null && <><br/><small>{daysToMaturity > 0 ? `${daysToMaturity}d left` : daysToMaturity === 0 ? "Today!" : "Overdue"}</small></>}
                            </> : "–"}
                          </td>
                          <td style={{ textAlign: 'right' }}>{currency(inv.amount)}</td>
                          <td style={{ textAlign: 'right', fontWeight: 600 }}>{currency(inv.current_value)}</td>
                          <td><span style={{ color: statusColor[inv.status] || "inherit", fontWeight: 600, textTransform: 'capitalize' }}>{inv.status}</span></td>
                          <td>
                            <button style={{ fontSize: '0.75rem', padding: '4px 10px' }} onClick={async (e) => {
                              e.stopPropagation();
                              setSelectedInvestment(inv);
                              const txs = await request<InvestmentTransaction[]>(`/investments/${inv.id}/transactions`).catch(() => []);
                              setInvestmentTransactions(txs);
                            }}>View</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Panel>

            {/* ── Investment Detail / Transaction Panel ── */}
            {selectedInvestment && (
              <Panel title={`Transactions – ${selectedInvestment.investment_no} (${selectedInvestment.institution_name})`} icon={ReceiptText} className="table-panel wide-panel">
                <div style={{ padding: '1rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end', borderBottom: '1px solid var(--border-color)' }}>
                  <div>
                    <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px' }}>Transaction Type</label>
                    <select id="inv_tx_type" style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                      <option value="interest_received">Interest Received</option>
                      <option value="principal_redeemed">Principal Redeemed</option>
                      <option value="revaluation">Revaluation (New Value)</option>
                      <option value="maturity_payout">Maturity Payout</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px' }}>Amount (Rs.)</label>
                    <input id="inv_tx_amount" type="number" placeholder="e.g. 5000" style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', width: '120px' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px' }}>Date</label>
                    <input id="inv_tx_date" type="date" defaultValue={new Date().toISOString().slice(0,10)} style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.75rem', display: 'block', marginBottom: '4px' }}>Narration</label>
                    <input id="inv_tx_narration" type="text" placeholder="Optional note" style={{ padding: '0.5rem', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-card)', width: '100%' }} />
                  </div>
                  <button className="primary" disabled={busy === "inv_tx"} onClick={async () => {
                    const txType = (document.getElementById("inv_tx_type") as HTMLSelectElement).value;
                    const amount = (document.getElementById("inv_tx_amount") as HTMLInputElement).value;
                    const date = (document.getElementById("inv_tx_date") as HTMLInputElement).value;
                    const narration = (document.getElementById("inv_tx_narration") as HTMLInputElement).value;
                    if (!amount || !date) return;
                    setBusy("inv_tx");
                    try {
                      await request(`/investments/${selectedInvestment.id}/transactions`, {
                        method: "POST",
                        body: JSON.stringify({ trans_type: txType, amount, trans_date: date, narration: narration || undefined })
                      });
                      setMessage("Transaction recorded.");
                      const txs = await request<InvestmentTransaction[]>(`/investments/${selectedInvestment.id}/transactions`).catch(() => []);
                      setInvestmentTransactions(txs);
                      await loadData();
                    } catch (err) {
                      setMessage(err instanceof Error ? err.message : "Transaction failed");
                    } finally {
                      setBusy("");
                    }
                  }}><Plus /> Record</button>
                </div>
                <DataTable
                  headers={["Date", "Type", "Amount", "Narration"]}
                  rows={investmentTransactions.map(tx => [
                    fullDateLabel(tx.trans_date),
                    tx.trans_type.replace(/_/g, " "),
                    currency(tx.amount),
                    tx.narration || "–"
                  ])}
                />
                {investmentTransactions.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '1rem' }}>No transactions recorded for this investment yet.</p>
                )}
              </Panel>
            )}
          </section>
        )}

        {activeView === "security" && (
          <section className="main-grid focused-grid">
            <Panel title="Risk and Compliance Cockpit" icon={ShieldCheck} className="wide-panel">
              <div className="action-row">
                <button className="primary" disabled={busy === "controls-scan"} onClick={runControlsScan}>{busy === "controls-scan" ? <Loader2 className="spin" /> : <RefreshCw />} Run Controls Scan</button>
                <a className="mini-button" href={`${API_BASE}/controls/copomis/export.csv`}><Download /> COPOMIS CSV</a>
              </div>
              <div className="snapshot">
                <div><span>Liquidity Status</span><strong>{liquidity?.status || "not scanned"}</strong><p>{liquidity ? `${liquidity.liquidity_ratio}% liquid coverage` : "Run scan to create today's snapshot."}</p></div>
                <div><span>Liquid Assets</span><strong>{currency(liquidity?.liquid_assets || 0)}</strong><p>Cash and bank view for payout planning.</p></div>
                <div><span>Member Liabilities</span><strong>{currency(Number(liquidity?.member_savings_liability || 0) + Number(liquidity?.term_deposit_liability || 0))}</strong><p>Savings plus FD/RD exposure.</p></div>
                <div><span>Pending Withdrawals</span><strong>{currency(liquidity?.pending_withdrawals || 0)}</strong><p>{withdrawalQueue.length} requests waiting.</p></div>
              </div>
            </Panel>
            <Panel title="Open Compliance Alerts" icon={ClipboardCheck} className="wide-panel table-panel">
              <DataTable headers={["Severity", "Module", "Issue", "Status"]} rows={complianceAlerts.slice(0, 12).map((alert) => [alert.severity, alert.module, alert.title, alert.status])} />
            </Panel>
            <Panel title="Withdrawal Queue" icon={Vault} className="wide-panel table-panel">
              <DataTable headers={["Requested", "Amount", "Priority", "Status", "Reason"]} rows={withdrawalQueue.slice(0, 12).map((item) => [item.requested_date, currency(item.requested_amount), item.priority, item.status, item.reason || "-"])} />
            </Panel>
            <Panel title="Built-in Internal Controls" icon={DatabaseBackup} className="wide-panel">
              <ul className="check-list">
                <li><CheckCircle2 /> Maker-checker blocks one person from creating, approving, and disbursing the same loan</li>
                <li><CheckCircle2 /> Liquidity threshold alerts before members face cash denial</li>
                <li><CheckCircle2 /> Overdue/NPL alerts for collection follow-up</li>
                <li><CheckCircle2 /> Large savings transaction flags for maker-checker review</li>
                <li><CheckCircle2 /> High-risk, PEP, and blacklist member monitoring</li>
                <li><CheckCircle2 /> COPOMIS-style export for regulator/reporting preparation</li>
              </ul>
            </Panel>
            <Panel title="Organization Structure" icon={Building2} className="wide-panel table-panel">
              <DataTable headers={["Position", "Level", "Reports To", "Status"]} rows={organizationPositions.map((item) => [item.title, item.level, item.reports_to_code || "Board", item.status])} />
            </Panel>
            <Panel title="Dynamic Policies" icon={Settings2} className="wide-panel table-panel">
              <DataTable headers={["Code", "Name", "Type", "Value"]} rows={systemPolicies.map((item) => [item.code, item.name, item.policy_type, JSON.stringify(item.config)])} />
            </Panel>
            <Panel title="Member Initial State" icon={BadgeCheck}>
              <Form fields={["membership_fee", "required_share_units", "share_rate", "required_savings_deposit"]} labels={["Membership Fee", "Required Share Units", "Share Rate", "Required Savings Deposit"]} submit="Save Policy" busy={busy === "/governance/policies"} onSubmit={(body) => submitJson("/governance/policies", { code: "member_initial_state", name: "Member Initial Financial State", policy_type: "membership", status: "active", config: body }, "Member initial state policy saved")} />
            </Panel>
            <Panel title="Board or Committee Decision" icon={ClipboardCheck}>
              <Form fields={["decision_body", "meeting_no", "title", "decision_text", "related_module", "related_record_id"]} labels={["Decision Body", "Meeting No", "Title", "Decision Text", "Related Module", "Related Record ID"]} submit="Record Decision" busy={busy === "/governance/decisions"} onSubmit={(body) => submitJson("/governance/decisions", compactObject(body), "Governance decision recorded")} />
            </Panel>
            <Panel title="Field Visit" icon={MapPin}>
              <SelectForm members={members} fields={["loan_id", "purpose", "location", "findings", "recommendation"]} labels={["Loan ID", "Purpose", "Location", "Findings", "Recommendation"]} submit="Save Visit" busy={busy === "/governance/field-visits"} onSubmit={(body) => submitJson("/governance/field-visits", compactObject(body), "Field visit recorded")} />
            </Panel>
            <Panel title="Recent Decisions" icon={FileText} className="wide-panel table-panel">
              <DataTable headers={["Body", "Meeting", "Title", "Status"]} rows={governanceDecisions.slice(0, 12).map((item) => [item.decision_body, item.meeting_no || "-", item.title, item.status])} />
            </Panel>
            <Panel title="Recent Field Visits" icon={MapPin} className="wide-panel table-panel">
              <DataTable headers={["Date", "Member", "Purpose", "Recommendation"]} rows={fieldVisits.slice(0, 12).map((item) => [item.visit_date || "-", memberName(members, item.member_id), item.purpose, item.recommendation || "-"])} />
            </Panel>
          </section>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value, detail, icon: Icon }: { label: string; value: string | number; detail: string; icon: React.ElementType }) {
  return <section className="metric"><div><p>{label}</p><strong>{value}</strong><span>{detail}</span></div><Icon /></section>;
}

function Panel({ title, icon: Icon, className = "", children }: { title: string; icon: React.ElementType; className?: string; children: React.ReactNode }) {
  return <section className={`panel ${className}`}><div className="panel-head"><h2>{title}</h2><Icon /></div>{children}</section>;
}

function InfoView({ icon: Icon, title, items }: { icon: React.ElementType; title: string; items: string[] }) {
  return (
    <section className="info-view">
      <div className="info-hero">
        <Icon />
        <div>
          <h2>{title}</h2>
          <p>These areas are separated from daily dashboard work so staff can find controls quickly.</p>
        </div>
      </div>
      <div className="info-grid">
        {items.map((item, index) => (
          <div className="info-tile" key={item}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <strong>{item}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function PersonOnboardingForm({
  busy,
  request,
  reload,
  setBusy,
  setMessage
}: {
  busy: boolean;
  request: <T>(path: string, init?: RequestInit) => Promise<T>;
  reload: () => Promise<void>;
  setBusy: (value: string) => void;
  setMessage: (value: string) => void;
}) {
  const [values, setValues] = useState<PersonFormValues>(emptyPersonForm);
  const [documents, setDocuments] = useState<DocumentValues[]>([{ ...emptyDocument }]);
  const [incomeSources, setIncomeSources] = useState<IncomeValues[]>([{ ...emptyIncome }]);
  const age = calculateAge(values.dob);
  const isMinor = age !== null && age < 18;
  const isMarried = values.marital_status === "Married";

  function setField(field: keyof PersonFormValues, value: string | boolean) {
    setValues((current) => ({ ...current, [field]: value }));
  }

  function setGroup<T extends keyof PersonFormValues>(group: T, field: string, value: string) {
    setValues((current) => ({ ...current, [group]: { ...(current[group] as Record<string, string>), [field]: value } }));
  }

  function memberPayload() {
    const permanent = { ...compactObject(values.permanent), ward_no: values.permanent.ward_no ? Number(values.permanent.ward_no) : undefined };
    const temporary = { ...compactObject(values.temporary), ward_no: values.temporary.ward_no ? Number(values.temporary.ward_no) : undefined };
    const addressLine = [values.permanent.tole, values.permanent.municipality, values.permanent.district].filter(Boolean).join(", ");
    const annualIncome = values.occupation_profile.annual_income || (values.occupation_profile.monthly_income ? `${Number(values.occupation_profile.monthly_income) * 12}` : "");

    return compactObject({
      member_no: values.member_no,
      name: values.name,
      name_nepali: values.name_nepali,
      dob: values.dob,
      dob_bs: values.dob_bs,
      gender: values.gender,
      marital_status: values.marital_status,
      nationality: values.nationality,
      phone: values.phone,
      secondary_phone: values.secondary_phone,
      email: values.email,
      emergency_contact_name: values.emergency_contact_name,
      emergency_contact_number: values.emergency_contact_number,
      address: addressLine,
      address_profile: { permanent, temporary_same_as_permanent: values.temporary_same_as_permanent, temporary: values.temporary_same_as_permanent ? permanent : temporary },
      documents: documents.map((document) => compactObject(document)).filter((document) => document.document_number),
      family_profile: compactObject(values.family_profile),
      guardian_profile: isMinor ? compactObject(values.guardian_profile) : undefined,
      occupation_profile: compactObject({ ...values.occupation_profile, annual_income: annualIncome }),
      income_sources: incomeSources.map((income) => compactObject(income)).filter((income) => income.monthly_amount),
      membership_type: values.membership_type,
      join_date: values.join_date,
      risk_category: values.risk_category,
      is_pep: values.is_pep,
      is_blacklisted: values.is_blacklisted,
      internal_notes: values.internal_notes,
      media_profile: compactObject(values.media_profile)
    });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy("/members");
    setMessage("");
    try {
      const member = await request<Member>("/members", { method: "POST", body: JSON.stringify(memberPayload()) });
      if (values.nominee.name && values.nominee.relation) {
        await request(`/members/${member.id}/nominees`, { method: "POST", body: JSON.stringify(compactObject(values.nominee)) });
      }
      setValues(emptyPersonForm);
      setDocuments([{ ...emptyDocument }]);
      setIncomeSources([{ ...emptyIncome }]);
      setMessage("Person onboarding record created");
      await reload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not create onboarding record");
    } finally {
      setBusy("");
    }
  }

  return (
    <form className="onboarding-form" onSubmit={submit}>
      <div className="form-section">
        <h3><UserRound /> Basic personal information</h3>
        <div className="field-grid">
          <label>Membership Number<input required value={values.member_no} onChange={(event) => setField("member_no", event.target.value)} /></label>
          <label>Full Name English<input required value={values.name} onChange={(event) => setField("name", event.target.value)} /></label>
          <label>Full Name Nepali<input value={values.name_nepali} onChange={(event) => setField("name_nepali", event.target.value)} /></label>
          <label>Gender<Select value={values.gender} required options={["Male", "Female", "Other"]} onChange={(value) => setField("gender", value)} /></label>
          <label>Date of Birth AD<input required type="date" max={today()} value={values.dob} onChange={(event) => setField("dob", event.target.value)} /></label>
          <label>Date of Birth BS<input required placeholder="2080-01-01" value={values.dob_bs} onChange={(event) => setField("dob_bs", event.target.value)} /></label>
          <label>Marital Status<Select value={values.marital_status} required options={["Single", "Married", "Widowed", "Divorced"]} onChange={(value) => setField("marital_status", value)} /></label>
          <label>Nationality<input required value={values.nationality} onChange={(event) => setField("nationality", event.target.value)} /></label>
        </div>
      </div>

      <div className="form-section">
        <h3><FileText /> Contact and KYC</h3>
        <div className="field-grid">
          <label>Primary Mobile<input required pattern="^(\\+977)?9\\d{9}$" value={values.phone} onChange={(event) => setField("phone", event.target.value)} /></label>
          <label>Secondary Mobile<input pattern="^(\\+977)?9\\d{9}$" value={values.secondary_phone} onChange={(event) => setField("secondary_phone", event.target.value)} /></label>
          <label>Email<input type="email" value={values.email} onChange={(event) => setField("email", event.target.value)} /></label>
          <label>Emergency Contact Name<input required value={values.emergency_contact_name} onChange={(event) => setField("emergency_contact_name", event.target.value)} /></label>
          <label>Emergency Contact Number<input required value={values.emergency_contact_number} onChange={(event) => setField("emergency_contact_number", event.target.value)} /></label>
        </div>
        <RepeatingDocuments documents={documents} setDocuments={setDocuments} />
      </div>

      <AddressSection title="Permanent Address" icon={MapPin} address={values.permanent} onChange={(field, value) => setGroup("permanent", field, value)} />
      <div className="same-address-row">
        <label><input type="checkbox" checked={values.temporary_same_as_permanent} onChange={(event) => setField("temporary_same_as_permanent", event.target.checked)} /> Temporary address same as permanent</label>
      </div>
      {!values.temporary_same_as_permanent && <AddressSection title="Temporary Address" icon={MapPin} address={values.temporary} onChange={(field, value) => setGroup("temporary", field, value)} />}

      <div className="form-section">
        <h3><UsersRound /> Family, guardian and nominee</h3>
        <div className="field-grid">
          <label>Father Name<input required value={values.family_profile.father_name} onChange={(event) => setGroup("family_profile", "father_name", event.target.value)} /></label>
          <label>Mother Name<input required value={values.family_profile.mother_name} onChange={(event) => setGroup("family_profile", "mother_name", event.target.value)} /></label>
          <label>Grandfather Name<input value={values.family_profile.grandfather_name} onChange={(event) => setGroup("family_profile", "grandfather_name", event.target.value)} /></label>
          {isMarried && <label>Spouse Name<input required value={values.family_profile.spouse_name} onChange={(event) => setGroup("family_profile", "spouse_name", event.target.value)} /></label>}
        </div>
        {isMinor && (
          <div className="nested-band">
            <strong>Guardian required for minor{age !== null ? `, age ${age}` : ""}</strong>
            <div className="field-grid">
              <label>Guardian Name<input required value={values.guardian_profile.name} onChange={(event) => setGroup("guardian_profile", "name", event.target.value)} /></label>
              <label>Relationship<Select value={values.guardian_profile.relationship} required options={["Father", "Mother", "Grandfather", "Grandmother", "Brother", "Sister", "Other"]} onChange={(value) => setGroup("guardian_profile", "relationship", value)} /></label>
              <label>Citizenship Number<input required value={values.guardian_profile.citizenship_number} onChange={(event) => setGroup("guardian_profile", "citizenship_number", event.target.value)} /></label>
              <label>Mobile Number<input required value={values.guardian_profile.mobile_number} onChange={(event) => setGroup("guardian_profile", "mobile_number", event.target.value)} /></label>
              <label>Address<input required value={values.guardian_profile.address} onChange={(event) => setGroup("guardian_profile", "address", event.target.value)} /></label>
            </div>
          </div>
        )}
        <div className="field-grid">
          <label>Nominee Name<input required value={values.nominee.name} onChange={(event) => setGroup("nominee", "name", event.target.value)} /></label>
          <label>Nominee Relationship<input required value={values.nominee.relation} onChange={(event) => setGroup("nominee", "relation", event.target.value)} /></label>
          <label>Nominee Mobile<input required value={values.nominee.phone} onChange={(event) => setGroup("nominee", "phone", event.target.value)} /></label>
          <label>Nominee Citizenship<input value={values.nominee.citizenship_number} onChange={(event) => setGroup("nominee", "citizenship_number", event.target.value)} /></label>
          <label>Nominee Address<input required value={values.nominee.address} onChange={(event) => setGroup("nominee", "address", event.target.value)} /></label>
        </div>
      </div>

      <div className="form-section">
        <h3><Banknote /> Occupation, income and compliance</h3>
        <div className="field-grid">
          <label>Occupation Type<Select value={values.occupation_profile.occupation_type} required options={["Government Employee", "Private Employee", "Teacher", "Farmer", "Business Owner", "Student", "Foreign Employment", "Retired", "Housewife", "Other"]} onChange={(value) => setGroup("occupation_profile", "occupation_type", value)} /></label>
          <label>Employer Name<input value={values.occupation_profile.employer_name} onChange={(event) => setGroup("occupation_profile", "employer_name", event.target.value)} /></label>
          <label>Job Position<input value={values.occupation_profile.job_position} onChange={(event) => setGroup("occupation_profile", "job_position", event.target.value)} /></label>
          <label>Work Address<input value={values.occupation_profile.work_address} onChange={(event) => setGroup("occupation_profile", "work_address", event.target.value)} /></label>
          <label>Monthly Income<input required type="number" min="0" value={values.occupation_profile.monthly_income} onChange={(event) => setGroup("occupation_profile", "monthly_income", event.target.value)} /></label>
          <label>Annual Income<input type="number" min="0" value={values.occupation_profile.annual_income} onChange={(event) => setGroup("occupation_profile", "annual_income", event.target.value)} /></label>
          <label>Membership Type<Select value={values.membership_type} options={["Individual", "Women Group", "Farmer", "Youth", "Senior Citizen", "Institution", "Employee Group"]} onChange={(value) => setField("membership_type", value)} /></label>
          <label>Join Date<input type="date" value={values.join_date} onChange={(event) => setField("join_date", event.target.value)} /></label>
          <label>Risk Category<Select value={values.risk_category} required options={["low", "medium", "high"]} onChange={(value) => setField("risk_category", value)} /></label>
        </div>
        <RepeatingIncome incomeSources={incomeSources} setIncomeSources={setIncomeSources} />
        <div className="toggle-row">
          <label><input type="checkbox" checked={values.is_pep} onChange={(event) => setField("is_pep", event.target.checked)} /> Politically Exposed Person</label>
          <label><input type="checkbox" checked={values.is_blacklisted} onChange={(event) => setField("is_blacklisted", event.target.checked)} /> Blacklist Status</label>
        </div>
        <label>Internal Notes<input value={values.internal_notes} onChange={(event) => setField("internal_notes", event.target.value)} /></label>
      </div>

      <div className="form-section">
        <h3><FileText /> Media and biometric references</h3>
        <div className="field-grid">
          <label>Profile Photo File<input value={values.media_profile.profile_photo} placeholder="photo filename or path" onChange={(event) => setGroup("media_profile", "profile_photo", event.target.value)} /></label>
          <label>Signature Image File<input value={values.media_profile.signature_image} placeholder="signature filename or path" onChange={(event) => setGroup("media_profile", "signature_image", event.target.value)} /></label>
          <label>Thumbprint File<input value={values.media_profile.thumbprint} placeholder="optional" onChange={(event) => setGroup("media_profile", "thumbprint", event.target.value)} /></label>
        </div>
      </div>

      <button className="primary submit-wide" disabled={busy}>{busy ? <Loader2 className="spin" /> : <CheckCircle2 />} Create Person Record</button>
    </form>
  );
}

function Select({ value, options, required = false, onChange }: { value: string; options: string[]; required?: boolean; onChange: (value: string) => void }) {
  return <select required={required} value={value} onChange={(event) => onChange(event.target.value)}><option value="">Choose</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select>;
}

function AddressSection({ title, icon: Icon, address, onChange }: { title: string; icon: React.ElementType; address: AddressValues; onChange: (field: keyof AddressValues, value: string) => void }) {
  return (
    <div className="form-section">
      <h3><Icon /> {title}</h3>
      <div className="field-grid">
        <label>Province<input required value={address.province} onChange={(event) => onChange("province", event.target.value)} /></label>
        <label>District<input required value={address.district} onChange={(event) => onChange("district", event.target.value)} /></label>
        <label>Municipality / Rural Municipality<input required value={address.municipality} onChange={(event) => onChange("municipality", event.target.value)} /></label>
        <label>Ward Number<input required type="number" min="1" max="35" value={address.ward_no} onChange={(event) => onChange("ward_no", event.target.value)} /></label>
        <label>Tole / Area<input required value={address.tole} onChange={(event) => onChange("tole", event.target.value)} /></label>
      </div>
    </div>
  );
}

function RepeatingDocuments({ documents, setDocuments }: { documents: DocumentValues[]; setDocuments: React.Dispatch<React.SetStateAction<DocumentValues[]>> }) {
  return (
    <div className="repeating-block">
      <div className="inline-head"><strong>Identification Documents</strong><button type="button" title="Add document" onClick={() => setDocuments((items) => [...items, { ...emptyDocument }])}><Plus /></button></div>
      {documents.map((document, index) => (
        <div className="repeat-row" key={index}>
          <label>Type<Select value={document.document_type} required options={["Citizenship Certificate", "Birth Certificate", "Passport", "Driving License", "PAN Number"]} onChange={(value) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, document_type: value } : item))} /></label>
          <label>Number<input required value={document.document_number} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, document_number: event.target.value } : item))} /></label>
          <label>Issue Date<input type="date" value={document.issue_date} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, issue_date: event.target.value } : item))} /></label>
          <label>Issue District<input value={document.issue_district} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, issue_district: event.target.value } : item))} /></label>
          <label>Expiry Date<input type="date" value={document.expiry_date} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, expiry_date: event.target.value } : item))} /></label>
          <label>Front Image<input value={document.front_image} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, front_image: event.target.value } : item))} /></label>
          <label>Back Image<input value={document.back_image} onChange={(event) => setDocuments((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, back_image: event.target.value } : item))} /></label>
          <button type="button" title="Remove document" disabled={documents.length === 1} onClick={() => setDocuments((items) => items.filter((_, itemIndex) => itemIndex !== index))}><Trash2 /></button>
        </div>
      ))}
    </div>
  );
}

function RepeatingIncome({ incomeSources, setIncomeSources }: { incomeSources: IncomeValues[]; setIncomeSources: React.Dispatch<React.SetStateAction<IncomeValues[]>> }) {
  return (
    <div className="repeating-block">
      <div className="inline-head"><strong>Income Sources</strong><button type="button" title="Add income source" onClick={() => setIncomeSources((items) => [...items, { ...emptyIncome }])}><Plus /></button></div>
      {incomeSources.map((income, index) => (
        <div className="repeat-row income-row" key={index}>
          <label>Type<Select value={income.income_type} required options={["Salary Income", "Business Income", "Agriculture Income", "Foreign Income", "Rental Income", "Pension Income", "Other Income"]} onChange={(value) => setIncomeSources((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, income_type: value } : item))} /></label>
          <label>Monthly Amount<input required type="number" min="0" value={income.monthly_amount} onChange={(event) => setIncomeSources((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, monthly_amount: event.target.value } : item))} /></label>
          <label>Description<input value={income.description} onChange={(event) => setIncomeSources((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, description: event.target.value } : item))} /></label>
          <button type="button" title="Remove income source" disabled={incomeSources.length === 1} onClick={() => setIncomeSources((items) => items.filter((_, itemIndex) => itemIndex !== index))}><Trash2 /></button>
        </div>
      ))}
    </div>
  );
}

function Form({ fields, labels, submit, busy, onSubmit }: { fields: string[]; labels: string[]; submit: string; busy: boolean; onSubmit: (body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <form className="stack-form" onSubmit={(event) => { event.preventDefault(); onSubmit(values); setValues({}); }}>
      {fields.map((field, index) => <label key={field}>{labels[index]}<input required={!optionalField(field)} value={values[field] || ""} onChange={(event) => setValues({ ...values, [field]: event.target.value })} /></label>)}
      <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <CheckCircle2 />} {submit}</button>
    </form>
  );
}

function SelectForm({ members, fields, labels, submit, busy, onSubmit }: { members: Member[]; fields: string[]; labels: string[]; submit: string; busy: boolean; onSubmit: (body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <form className="stack-form" onSubmit={(event) => { event.preventDefault(); onSubmit(values); setValues({}); }}>
      <label>Member<select required value={values.member_id || ""} onChange={(event) => setValues({ ...values, member_id: event.target.value })}><option value="">Choose member</option>{members.map((member) => <option key={member.id} value={member.id}>{member.member_no} - {member.name}</option>)}</select></label>
      {fields.map((field, index) => <label key={field}>{labels[index]}<input required={!optionalField(field)} value={values[field] || ""} onChange={(event) => setValues({ ...values, [field]: event.target.value })} /></label>)}
      <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <CheckCircle2 />} {submit}</button>
    </form>
  );
}

function optionalField(field: string) {
  return ["phone", "address", "document_ref", "meeting_no", "related_module", "related_record_id", "location", "findings", "recommendation", "comments"].includes(field);
}

function CashTransactionForm({ accounts, submit, busy, onSubmit }: { accounts: SavingsAccount[]; submit: string; busy: boolean; onSubmit: (accountId: string, body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <form className="stack-form" onSubmit={(event) => { event.preventDefault(); onSubmit(values.account_id, { amount: values.amount, narration: values.narration }); setValues({}); }}>
      <label>Account<select required value={values.account_id || ""} onChange={(event) => setValues({ ...values, account_id: event.target.value })}><option value="">Choose account</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.account_no} - {account.account_type} - {currency(account.balance)}</option>)}</select></label>
      <label>Amount<input required type="number" min="1" step="0.01" value={values.amount || ""} onChange={(event) => setValues({ ...values, amount: event.target.value })} /></label>
      <label>Narration<input required value={values.narration || ""} onChange={(event) => setValues({ ...values, narration: event.target.value })} /></label>
      <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <CheckCircle2 />} {submit}</button>
    </form>
  );
}

function FieldRouteForm({ busy, onSubmit }: { busy: boolean; onSubmit: (body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  return (
    <form className="stack-form" onSubmit={(event) => { event.preventDefault(); onSubmit(compactObject(values) as Record<string, string>); setValues({}); }}>
      <label>Route Name<input required value={values.name || ""} onChange={(event) => setValues({ ...values, name: event.target.value })} /></label>
      <label>Area<input value={values.area || ""} onChange={(event) => setValues({ ...values, area: event.target.value })} /></label>
      <label>Collector User ID<input value={values.assigned_collector_id || ""} onChange={(event) => setValues({ ...values, assigned_collector_id: event.target.value })} /></label>
      <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <MapPin />} Create Route</button>
    </form>
  );
}

function FieldBatchForm({ routes, busy, onSubmit }: { routes: CollectorRoute[]; busy: boolean; onSubmit: (body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({ collection_date: today(), opening_cash: "0", expected_total: "0" });
  return (
    <form className="stack-form" onSubmit={(event) => { event.preventDefault(); onSubmit(compactObject(values) as Record<string, string>); setValues({ collection_date: today(), opening_cash: "0", expected_total: "0" }); }}>
      <label>Route<select value={values.route_id || ""} onChange={(event) => setValues({ ...values, route_id: event.target.value })}><option value="">No route assigned</option>{routes.map((route) => <option key={route.id} value={route.id}>{route.name}{route.area ? ` - ${route.area}` : ""}</option>)}</select></label>
      <label>Collection Date<input type="date" required value={values.collection_date || today()} onChange={(event) => setValues({ ...values, collection_date: event.target.value })} /></label>
      <label>Opening Cash<input type="number" min="0" step="0.01" value={values.opening_cash || "0"} onChange={(event) => setValues({ ...values, opening_cash: event.target.value })} /></label>
      <label>Expected Total<input type="number" min="0" step="0.01" value={values.expected_total || "0"} onChange={(event) => setValues({ ...values, expected_total: event.target.value })} /></label>
      <button className="primary" disabled={busy}>{busy ? <Loader2 className="spin" /> : <Plus />} Open Batch</button>
    </form>
  );
}

function FieldEntryForm({ batch, members, accounts, loans, request, busy, onSubmit }: { batch: FieldCollectionBatch | null; members: Member[]; accounts: SavingsAccount[]; loans: Loan[]; request: <T>(path: string, init?: RequestInit) => Promise<T>; busy: boolean; onSubmit: (batchId: string, body: Record<string, string>) => void }) {
  const [values, setValues] = useState<Record<string, string>>({ collection_type: "savings_deposit", payment_method: "cash" });
  const [targets, setTargets] = useState<FieldTargets | null>(null);
  const memberAccounts = targets?.accounts || accounts.filter((account) => !values.member_id || account.member_id === values.member_id);
  const memberLoans = targets?.loans || loans.filter((loan) => !values.member_id || loan.member_id === values.member_id);
  const memberInstallments = (targets?.installments || []).filter((item) => !values.loan_id || item.loan_id === values.loan_id);
  const isDraft = Boolean(batch && batch.status === "draft");
  const amountLabel = values.collection_type === "loan_repayment" ? "Exact Installment Amount" : values.collection_type === "share_purchase" ? "Share Amount" : "Amount";

  async function loadTargets(memberId: string) {
    setTargets(null);
    if (!memberId) return;
    const data = await request<FieldTargets>(`/field-collections/members/${memberId}/targets`).catch(() => null);
    setTargets(data);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!batch) return;
    const body = compactObject({
      ...values,
      client_request_id: values.client_request_id || `web-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      payment_method: values.payment_method || "cash"
    }) as Record<string, string>;
    onSubmit(batch.id, body);
    setValues({ collection_type: "savings_deposit", payment_method: "cash" });
  }

  return (
    <form className="stack-form" onSubmit={submit}>
      <label>Active Batch<input disabled value={batch ? `${batch.collection_date} - ${currency(batch.collected_total)} - ${batch.status}` : "Open a batch from the table"} /></label>
      <label>Collection Type<select required disabled={!isDraft} value={values.collection_type || "savings_deposit"} onChange={(event) => setValues({ collection_type: event.target.value, payment_method: values.payment_method || "cash" })}>
        <option value="savings_deposit">Savings Deposit</option>
        <option value="loan_repayment">Loan Repayment</option>
        <option value="share_purchase">Share Purchase</option>
        <option value="fee_collection">Fee Collection</option>
      </select></label>
      <label>Member<select required disabled={!isDraft} value={values.member_id || ""} onChange={(event) => { const memberId = event.target.value; setValues({ ...values, member_id: memberId, savings_account_id: "", loan_id: "", loan_installment_id: "" }); loadTargets(memberId); }}><option value="">Choose member</option>{members.map((member) => <option key={member.id} value={member.id}>{member.member_no} - {member.name}</option>)}</select></label>
      {values.collection_type === "savings_deposit" && <label>Savings Account<select required disabled={!isDraft} value={values.savings_account_id || ""} onChange={(event) => setValues({ ...values, savings_account_id: event.target.value })}><option value="">Choose account</option>{memberAccounts.map((account) => <option key={account.id} value={account.id}>{account.account_no} - {currency(account.balance)}</option>)}</select></label>}
      {values.collection_type === "loan_repayment" && <label>Loan<select required disabled={!isDraft} value={values.loan_id || ""} onChange={(event) => setValues({ ...values, loan_id: event.target.value, loan_installment_id: "", amount: "" })}><option value="">Choose loan</option>{memberLoans.map((loan) => <option key={loan.id} value={loan.id}>{loan.loan_no} - {currency(loan.outstanding_principal)}</option>)}</select></label>}
      {values.collection_type === "loan_repayment" && <label>Pending Installment<select required disabled={!isDraft} value={values.loan_installment_id || ""} onChange={(event) => { const installment = memberInstallments.find((item) => item.id === event.target.value); setValues({ ...values, loan_installment_id: event.target.value, amount: installment?.total || values.amount || "" }); }}><option value="">Choose installment</option>{memberInstallments.map((item) => <option key={item.id} value={item.id}>#{item.installment_no} due {item.due_date} - {currency(item.total)}</option>)}</select></label>}
      {values.collection_type === "share_purchase" && <label>Share Units<input required disabled={!isDraft} type="number" min="1" value={values.share_units || ""} onChange={(event) => setValues({ ...values, share_units: event.target.value })} /></label>}
      {values.collection_type === "share_purchase" && <label>Share Rate<input required disabled={!isDraft} type="number" min="1" step="0.01" value={values.share_rate || ""} onChange={(event) => setValues({ ...values, share_rate: event.target.value })} /></label>}
      {values.collection_type === "fee_collection" && <label>Fee Code<input required disabled={!isDraft} value={values.fee_code || ""} onChange={(event) => setValues({ ...values, fee_code: event.target.value })} /></label>}
      <label>{amountLabel}<input required disabled={!isDraft} type="number" min="1" step="0.01" value={values.amount || ""} onChange={(event) => setValues({ ...values, amount: event.target.value })} /></label>
      <label>Receipt No<input disabled={!isDraft} value={values.receipt_no || ""} placeholder="Auto if blank" onChange={(event) => setValues({ ...values, receipt_no: event.target.value })} /></label>
      <label>Narration<input disabled={!isDraft} value={values.narration || "Daily field collection"} onChange={(event) => setValues({ ...values, narration: event.target.value })} /></label>
      <button className="primary" disabled={!isDraft || busy}>{busy ? <Loader2 className="spin" /> : <Banknote />} Save Collection</button>
    </form>
  );
}

function FieldBatchControls({ batch, busy, onSubmit, onVerify, onPost }: { batch: FieldCollectionBatch | null; busy: string; onSubmit: (batchId: string) => void; onVerify: (batchId: string) => void; onPost: (batchId: string) => void }) {
  return (
    <div className="field-control-panel">
      <div className="result-box">
        <strong>{batch ? `${batch.collection_date} collection` : "No batch selected"}</strong>
        <span>Total: {currency(batch?.collected_total || 0)}</span>
        <span>Status: {batch?.status || "open a batch"}</span>
      </div>
      <div className="action-row">
        <button className="primary" disabled={!batch || batch.status !== "draft" || busy.includes("/submit")} onClick={() => batch && onSubmit(batch.id)}><ClipboardCheck /> Submit</button>
        <button disabled={!batch || batch.status !== "submitted" || busy.includes("/verify")} onClick={() => batch && onVerify(batch.id)}><CheckCircle2 /> Verify</button>
        <button disabled={!batch || batch.status !== "verified" || busy.includes("/post")} onClick={() => batch && onPost(batch.id)}><ReceiptText /> Post</button>
      </div>
    </div>
  );
}

function FieldBatchTable({ batches, routes, busy, onOpen, onVerify, onPost }: { batches: FieldCollectionBatch[]; routes: CollectorRoute[]; busy: string; onOpen: (batchId: string) => void; onVerify: (batch: FieldCollectionBatch) => void; onPost: (batch: FieldCollectionBatch) => void }) {
  const routeName = (routeId?: string) => routes.find((route) => route.id === routeId)?.name || "-";
  return (
    <table>
      <thead><tr><th>Date</th><th>Route</th><th>Total</th><th>Expected</th><th>Status</th><th>Controls</th></tr></thead>
      <tbody>
        {batches.length ? batches.map((batch) => (
          <tr key={batch.id}>
            <td>{batch.collection_date}</td>
            <td>{routeName(batch.route_id)}</td>
            <td>{currency(batch.collected_total)}</td>
            <td>{currency(batch.expected_total)}</td>
            <td>{batch.status}</td>
            <td className="button-cluster">
              <button className="mini-button" disabled={busy === `field-batch-${batch.id}`} onClick={() => onOpen(batch.id)}>{busy === `field-batch-${batch.id}` ? <Loader2 className="spin" /> : <Search />} Open</button>
              <button className="mini-button" disabled={batch.status !== "submitted" || busy.includes("/verify")} onClick={() => onVerify(batch)}><CheckCircle2 /> Verify</button>
              <button className="mini-button" disabled={batch.status !== "verified" || busy.includes("/post")} onClick={() => onPost(batch)}><ReceiptText /> Post</button>
            </td>
          </tr>
        )) : <tr><td colSpan={6}>No field collection batches yet</td></tr>}
      </tbody>
    </table>
  );
}

function MemberDirectory({ members, busy, onOpen }: { members: Member[]; busy: string; onOpen: (memberId: string) => void }) {
  return (
    <table>
      <thead><tr><th>No</th><th>Name</th><th>Phone</th><th>KYC</th><th>Status</th><th>View</th></tr></thead>
      <tbody>
        {members.length ? members.map((member) => (
          <tr key={member.id}>
            <td>{member.member_no}</td>
            <td>{member.name}</td>
            <td>{member.phone || "-"}</td>
            <td>{member.kyc_status}</td>
            <td>{member.status}</td>
            <td><button className="mini-button" disabled={busy === `member-profile-${member.id}`} onClick={() => onOpen(member.id)}>{busy === `member-profile-${member.id}` ? <Loader2 className="spin" /> : <Search />} Open</button></td>
          </tr>
        )) : <tr><td colSpan={6}>Search by member no, name, or phone to find a member</td></tr>}
      </tbody>
    </table>
  );
}

function LoanPortfolio({ loans, busy, onOpen, onReview, onApprove, onDisburse }: { loans: Loan[]; busy: string; onOpen: (loan: Loan) => void; onReview: (loan: Loan) => void; onApprove: (loan: Loan) => void; onDisburse: (loan: Loan) => void }) {
  return (
    <table>
      <thead><tr><th>Loan</th><th>Type</th><th>Amount</th><th>Outstanding</th><th>Status</th><th>Controls</th></tr></thead>
      <tbody>
        {loans.length ? loans.map((loan) => {
          const reviewable = ["application", "draft"].includes(loan.status);
          const approvable = ["application", "recommended", "reviewed"].includes(loan.status);
          const disbursable = loan.status === "approved";
          return (
            <tr key={loan.id}>
              <td><strong>{loan.loan_no}</strong><small>{loan.id}</small></td>
              <td>{loan.loan_type}</td>
              <td>{currency(loan.amount)}</td>
              <td>{currency(loan.outstanding_principal)}</td>
              <td>{loan.status}</td>
              <td className="button-cluster">
                <button className="mini-button" disabled={busy === `loan-schedule-${loan.id}`} onClick={() => onOpen(loan)}>{busy === `loan-schedule-${loan.id}` ? <Loader2 className="spin" /> : <ReceiptText />} Schedule</button>
                <button className="mini-button" disabled={!reviewable || busy === `/loans/${loan.id}/reviews`} onClick={() => onReview(loan)}><ClipboardCheck /> Review</button>
                <button className="mini-button" disabled={!approvable || busy === `/loans/${loan.id}/approve`} onClick={() => onApprove(loan)}><CheckCircle2 /> Approve</button>
                <button className="mini-button" disabled={!disbursable || busy === `/loans/${loan.id}/disburse`} onClick={() => onDisburse(loan)}><Banknote /> Disburse</button>
              </td>
            </tr>
          );
        }) : <tr><td colSpan={6}>No loan applications yet</td></tr>}
      </tbody>
    </table>
  );
}

function LoanSchedule({ installments, busy, onPay }: { installments: LoanInstallment[]; busy: string; onPay: (installmentId: string) => void }) {
  return (
    <table>
      <thead><tr><th>No</th><th>Due Date</th><th>Principal</th><th>Interest</th><th>Penalty</th><th>Total</th><th>Status</th><th>Action</th></tr></thead>
      <tbody>
        {installments.length ? installments.map((installment) => (
          <tr key={installment.id}>
            <td>{installment.installment_no}</td>
            <td>{installment.due_date}</td>
            <td>{currency(installment.principal)}</td>
            <td>{currency(installment.interest)}</td>
            <td>{currency(installment.penalty)}</td>
            <td>{currency(installment.total)}</td>
            <td>{installment.status}</td>
            <td><button className="mini-button" disabled={installment.status === "paid" || busy === `pay-${installment.id}`} onClick={() => onPay(installment.id)}>{busy === `pay-${installment.id}` ? <Loader2 className="spin" /> : <Banknote />} Pay</button></td>
          </tr>
        )) : <tr><td colSpan={8}>Open a loan schedule to view installments</td></tr>}
      </tbody>
    </table>
  );
}

function MemberProfileView({ profile }: { profile: MemberProfile }) {
  const [activeTab, setActiveTab] = React.useState<"overview"|"savings"|"loans"|"shares"|"nominees"|"kyc">("overview");

  const shareCapital = profile.shares.reduce((t, i) => t + Number(i.total_amount || 0), 0);
  const savingsBalance = profile.savings_accounts.reduce((t, i) => t + Number(i.balance || 0), 0);
  const loanOutstanding = profile.loans.reduce((t, i) => t + Number(i.outstanding_principal || 0), 0);
  const totalLoansGiven = profile.loans.reduce((t, i) => t + Number(i.amount || 0), 0);
  const overdueInstallments = profile.loan_installments.filter(i => i.status === "overdue").length;
  const pendingInstallments = profile.loan_installments.filter(i => i.status === "pending").length;
  const totalInterestPaid = profile.loan_payments.reduce((t, i) => t + Number(i.interest_paid || 0), 0);

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "savings", label: `Savings (${profile.savings_accounts.length})` },
    { id: "loans", label: `Loans (${profile.loans.length})` },
    { id: "shares", label: `Shares` },
    { id: "nominees", label: `Nominees (${profile.nominees.length})` },
    { id: "kyc", label: "KYC & Info" },
  ] as const;

  const riskColors: Record<string, string> = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };
  const riskColor = riskColors[profile.member.risk_category || "low"] || "#10b981";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>

      {/* ── Profile Header ── */}
      <div style={{
        background: "linear-gradient(135deg, var(--bg-card) 0%, var(--bg-hover) 100%)",
        border: "1px solid var(--border-color)",
        borderRadius: "16px",
        padding: "1.5rem 2rem",
        display: "flex",
        alignItems: "center",
        gap: "1.5rem",
        flexWrap: "wrap"
      }}>
        {/* Avatar */}
        <div style={{
          width: "64px", height: "64px", borderRadius: "50%",
          background: `linear-gradient(135deg, ${riskColor}44, ${riskColor}22)`,
          border: `3px solid ${riskColor}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.6rem", fontWeight: 700, color: riskColor, flexShrink: 0
        }}>
          {profile.member.name.charAt(0).toUpperCase()}
        </div>
        {/* Info */}
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap", marginBottom: "4px" }}>
            <h2 style={{ margin: 0, fontSize: "1.3rem", fontWeight: 700 }}>{profile.member.name}</h2>
            {profile.member.name_nepali && <span style={{ color: "var(--text-secondary)", fontSize: "1rem" }}>{profile.member.name_nepali}</span>}
            <span style={{
              background: `${riskColor}22`, color: riskColor,
              borderRadius: "20px", padding: "2px 12px", fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase"
            }}>{profile.member.risk_category || "low"} risk</span>
            <span style={{
              background: profile.member.status === "active" ? "#10b98122" : "#ef444422",
              color: profile.member.status === "active" ? "#10b981" : "#ef4444",
              borderRadius: "20px", padding: "2px 10px", fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase"
            }}>{profile.member.status}</span>
          </div>
          <div style={{ color: "var(--text-secondary)", fontSize: "0.85rem", display: "flex", gap: "1.25rem", flexWrap: "wrap" }}>
            <span>🪪 {profile.member.member_no}</span>
            {profile.member.phone && <span>📞 {profile.member.phone}</span>}
            {profile.member.email && <span>✉️ {profile.member.email}</span>}
            {profile.member.kyc_status && <span>KYC: <strong style={{ color: "var(--text-primary)" }}>{profile.member.kyc_status}</strong></span>}
          </div>
        </div>
        {/* Quick stats strip */}
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          {[
            { label: "Share Capital", value: currency(shareCapital), color: "#6366f1" },
            { label: "Savings Balance", value: currency(savingsBalance), color: "#10b981" },
            { label: "Loan Outstanding", value: currency(loanOutstanding), color: "#f59e0b" },
            { label: "Overdue EMIs", value: String(overdueInstallments), color: overdueInstallments > 0 ? "#ef4444" : "#10b981" },
          ].map(s => (
            <div key={s.label} style={{ textAlign: "center", minWidth: "110px" }}>
              <div style={{ fontSize: "1.1rem", fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: "0.68rem", color: "var(--text-secondary)", marginTop: "2px" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Tab bar ── */}
      <div style={{
        display: "flex", gap: "4px", background: "var(--bg-card)",
        padding: "4px", borderRadius: "10px", border: "1px solid var(--border-color)", flexWrap: "wrap"
      }}>
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            flex: 1, padding: "0.5rem 1rem", borderRadius: "7px", border: "none", cursor: "pointer",
            fontWeight: 600, fontSize: "0.8rem", transition: "all 0.15s",
            background: activeTab === tab.id ? "var(--accent, #0a6e3f)" : "transparent",
            color: activeTab === tab.id ? "#fff" : "var(--text-secondary)",
          }}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB: OVERVIEW ── */}
      {activeTab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
          {/* Financial Summary */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
            <h3 style={{ marginTop: 0, fontSize: "0.9rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Financial Summary</h3>
            {[
              { label: "Total Shares Invested", value: currency(shareCapital) },
              { label: "Total Savings Balance", value: currency(savingsBalance) },
              { label: "Total Loans Disbursed", value: currency(totalLoansGiven) },
              { label: "Loan Outstanding", value: currency(loanOutstanding) },
              { label: "Interest Paid (all time)", value: currency(totalInterestPaid) },
              { label: "Pending EMIs", value: `${pendingInstallments} installments` },
              { label: "Overdue EMIs", value: overdueInstallments > 0 ? `🔴 ${overdueInstallments} overdue` : "✅ None" },
            ].map(row => (
              <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border-color)", fontSize: "0.85rem" }}>
                <span style={{ color: "var(--text-secondary)" }}>{row.label}</span>
                <strong>{row.value}</strong>
              </div>
            ))}
          </div>
          {/* Recent Savings Transactions */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
            <h3 style={{ marginTop: 0, fontSize: "0.9rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Recent Savings Activity</h3>
            {profile.savings_transactions.length === 0
              ? <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>No transactions yet.</p>
              : profile.savings_transactions.slice(0, 8).map((tx, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border-color)", fontSize: "0.82rem" }}>
                  <span>
                    <span style={{ background: tx.trans_type === "deposit" || tx.trans_type === "interest" ? "#10b98122" : "#ef444422", color: tx.trans_type === "deposit" || tx.trans_type === "interest" ? "#10b981" : "#ef4444", borderRadius: "6px", padding: "1px 6px", fontSize: "0.7rem", marginRight: "6px" }}>{tx.trans_type}</span>
                    <span style={{ color: "var(--text-secondary)" }}>{fullDateLabel(tx.trans_date)}</span>
                  </span>
                  <strong style={{ color: tx.trans_type === "deposit" || tx.trans_type === "interest" ? "#10b981" : "#ef4444" }}>{currency(tx.amount)}</strong>
                </div>
              ))
            }
          </div>
          {/* Upcoming EMIs */}
          <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
            <h3 style={{ marginTop: 0, fontSize: "0.9rem", color: "var(--text-secondary)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>Upcoming / Overdue EMIs</h3>
            {profile.loan_installments.filter(i => i.status !== "paid").length === 0
              ? <p style={{ color: "#10b981", fontSize: "0.85rem" }}>✅ All installments paid!</p>
              : profile.loan_installments.filter(i => i.status !== "paid").slice(0, 8).map((ins, i) => {
                  const color = ins.status === "overdue" ? "#ef4444" : "#f59e0b";
                  return (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid var(--border-color)", fontSize: "0.82rem" }}>
                      <span>
                        <span style={{ background: `${color}22`, color, borderRadius: "6px", padding: "1px 6px", fontSize: "0.7rem", marginRight: "6px" }}>{ins.status}</span>
                        <span style={{ color: "var(--text-secondary)" }}>EMI #{ins.installment_no} · {fullDateLabel(ins.due_date)}</span>
                      </span>
                      <strong>{currency(ins.total)}</strong>
                    </div>
                  );
                })
            }
          </div>
        </div>
      )}

      {/* ── TAB: SAVINGS ── */}
      {activeTab === "savings" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {profile.savings_accounts.length === 0
            ? <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>No savings accounts found for this member.</div>
            : profile.savings_accounts.map(acc => {
                const accTxs = profile.savings_transactions.filter(tx => tx.account_id === acc.id);
                return (
                  <div key={acc.id} style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "1rem" }}>{acc.account_no}</div>
                        <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem", textTransform: "capitalize", marginTop: "2px" }}>{acc.account_type.replace(/_/g, " ")} · {acc.interest_rate}% p.a.</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#10b981" }}>{currency(acc.balance)}</div>
                        <span style={{ background: acc.status === "active" ? "#10b98122" : "#ef444422", color: acc.status === "active" ? "#10b981" : "#ef4444", borderRadius: "20px", padding: "2px 10px", fontSize: "0.7rem", fontWeight: 700 }}>{acc.status}</span>
                      </div>
                    </div>
                    <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>Transaction History ({accTxs.length})</h4>
                    <DataTable
                      headers={["Date (BS)", "Type", "Amount", "Balance", "Narration"]}
                      rows={accTxs.slice(0, 20).map(tx => [
                        fullDateLabel(tx.trans_date),
                        tx.trans_type,
                        currency(tx.amount),
                        currency(tx.balance),
                        tx.narration || "–"
                      ])}
                    />
                  </div>
                );
              })
          }
        </div>
      )}

      {/* ── TAB: LOANS ── */}
      {activeTab === "loans" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {profile.loans.length === 0
            ? <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>No loans found for this member.</div>
            : profile.loans.map(loan => {
                const installments = profile.loan_installments.filter(i => i.loan_id === loan.id);
                const payments = profile.loan_payments.filter(p => p.loan_id === loan.id);
                const paidCount = installments.filter(i => i.status === "paid").length;
                const overdueCount = installments.filter(i => i.status === "overdue").length;
                const progress = installments.length > 0 ? (paidCount / installments.length) * 100 : 0;
                const loanStatusColor: Record<string, string> = { active: "#10b981", closed: "#6b7280", overdue: "#ef4444", application: "#f59e0b", approved: "#3b82f6" };
                return (
                  <div key={loan.id} style={{ background: "var(--bg-card)", border: `1px solid ${loanStatusColor[loan.status] || "#6b7280"}44`, borderRadius: "12px", padding: "1.25rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "0.5rem", marginBottom: "1rem" }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "1rem" }}>{loan.loan_no} <span style={{ fontWeight: 400, color: "var(--text-secondary)", fontSize: "0.85rem", textTransform: "capitalize" }}>({loan.loan_type})</span></div>
                        <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem", marginTop: "2px" }}>{loan.interest_rate}% p.a. · {loan.tenure_months} months · Sanctioned: {currency(loan.amount)}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: "1.2rem", fontWeight: 700, color: loanStatusColor[loan.status] || "#6b7280" }}>{currency(loan.outstanding_principal)} <span style={{ fontSize: "0.75rem", fontWeight: 400 }}>outstanding</span></div>
                        <span style={{ background: `${loanStatusColor[loan.status] || "#6b7280"}22`, color: loanStatusColor[loan.status] || "#6b7280", borderRadius: "20px", padding: "2px 10px", fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase" }}>{loan.status}</span>
                        {overdueCount > 0 && <div style={{ color: "#ef4444", fontSize: "0.75rem", marginTop: "4px" }}>⚠️ {overdueCount} overdue EMIs</div>}
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div style={{ marginBottom: "1rem" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "4px" }}>
                        <span>{paidCount}/{installments.length} EMIs paid</span>
                        <span>{progress.toFixed(0)}% complete</span>
                      </div>
                      <div style={{ background: "var(--bg-hover)", borderRadius: "6px", height: "8px", overflow: "hidden" }}>
                        <div style={{ background: overdueCount > 0 ? "#ef4444" : "#10b981", height: "100%", width: `${progress}%`, borderRadius: "6px", transition: "width 0.3s" }} />
                      </div>
                    </div>
                    <h4 style={{ margin: "0 0 0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>EMI Schedule (next 10)</h4>
                    <DataTable
                      headers={["#", "Due Date (BS)", "Principal", "Interest", "Penalty", "Total", "Status"]}
                      rows={installments.filter(i => i.status !== "paid").slice(0, 10).map(i => [
                        `${i.installment_no}`,
                        fullDateLabel(i.due_date),
                        currency(i.principal),
                        currency(i.interest),
                        currency(i.penalty),
                        currency(i.total),
                        i.status
                      ])}
                    />
                    {payments.length > 0 && <>
                      <h4 style={{ margin: "1rem 0 0.5rem", fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>Recent Payments ({payments.length})</h4>
                      <DataTable
                        headers={["Date", "Principal", "Interest", "Penalty", "Total"]}
                        rows={payments.slice(0, 8).map(p => [
                          fullDateLabel(p.payment_date),
                          currency(p.principal_paid),
                          currency(p.interest_paid),
                          currency(p.penalty_paid),
                          currency(p.total_paid)
                        ])}
                      />
                    </>}
                  </div>
                );
              })
          }
        </div>
      )}

      {/* ── TAB: SHARES ── */}
      {activeTab === "shares" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {profile.shares.length === 0
            ? <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)" }}>No shares issued to this member yet.</div>
            : <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "1rem" }}>
                  {profile.shares.map(sh => (
                    <div key={sh.id} style={{ background: "var(--bg-card)", border: "2px solid #6366f144", borderRadius: "12px", padding: "1.25rem", textAlign: "center" }}>
                      <div style={{ fontSize: "2rem", fontWeight: 800, color: "#6366f1" }}>{sh.total_share}</div>
                      <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>Shares @ Rs. {sh.rate}</div>
                      <div style={{ fontWeight: 700, marginTop: "0.5rem", fontSize: "1.1rem" }}>{currency(sh.total_amount)}</div>
                      <span style={{ background: sh.status === "active" ? "#10b98122" : "#ef444422", color: sh.status === "active" ? "#10b981" : "#ef4444", borderRadius: "20px", padding: "2px 10px", fontSize: "0.7rem", fontWeight: 700 }}>{sh.status}</span>
                    </div>
                  ))}
                </div>
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
                  <h4 style={{ marginTop: 0, fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase" }}>Share Transaction History</h4>
                  <DataTable
                    headers={["Date (BS)", "Type", "Shares", "Rate", "Amount", "Note"]}
                    rows={profile.share_transactions.map(tx => [
                      fullDateLabel(tx.trans_date),
                      tx.trans_type,
                      `${tx.shares}`,
                      `Rs. ${tx.rate}`,
                      currency(tx.amount),
                      tx.narration || "–"
                    ])}
                  />
                </div>
              </>
          }
        </div>
      )}

      {/* ── TAB: NOMINEES ── */}
      {activeTab === "nominees" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
          {profile.nominees.length === 0
            ? <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-secondary)", gridColumn: "1/-1" }}>No nominees registered for this member.</div>
            : profile.nominees.map((n, i) => (
                <div key={i} style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
                    <div style={{ width: "40px", height: "40px", borderRadius: "50%", background: "#6366f122", border: "2px solid #6366f1", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, color: "#6366f1", fontSize: "1.1rem" }}>
                      {n.name.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight: 700 }}>{n.name}</div>
                      <div style={{ color: "var(--text-secondary)", fontSize: "0.8rem" }}>{n.relation}</div>
                    </div>
                  </div>
                  {n.phone && <div style={{ fontSize: "0.85rem", marginBottom: "4px" }}>📞 {n.phone}</div>}
                  {n.address && <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>📍 {n.address}</div>}
                </div>
              ))
          }
        </div>
      )}

      {/* ── TAB: KYC & INFO ── */}
      {activeTab === "kyc" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
          {[
            { title: "Personal Details", rows: [
              ["Full Name", profile.member.name],
              ["Nepali Name", profile.member.name_nepali || "–"],
              ["Date of Birth (AD)", profile.member.dob || "–"],
              ["Date of Birth (BS)", profile.member.dob_bs || "–"],
              ["Gender", profile.member.gender || "–"],
              ["Marital Status", profile.member.marital_status || "–"],
              ["Nationality", profile.member.nationality || "Nepali"],
            ]},
            { title: "Contact Details", rows: [
              ["Primary Phone", profile.member.phone || "–"],
              ["Secondary Phone", profile.member.secondary_phone || "–"],
              ["Email", profile.member.email || "–"],
              ["Emergency Contact", profile.member.emergency_contact_name || "–"],
              ["Emergency Phone", profile.member.emergency_contact_number || "–"],
            ]},
            { title: "Membership", rows: [
              ["Member No.", profile.member.member_no],
              ["Membership Type", profile.member.membership_type || "–"],
              ["Join Date", profile.member.join_date ? fullDateLabel(profile.member.join_date) : "–"],
              ["KYC Status", profile.member.kyc_status],
              ["Status", profile.member.status],
              ["Risk Category", profile.member.risk_category || "low"],
              ["PEP", profile.member.is_pep ? "🚨 Yes" : "No"],
              ["Blacklisted", profile.member.is_blacklisted ? "🚨 Yes" : "No"],
            ]},
          ].map(card => (
            <div key={card.title} style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)", borderRadius: "12px", padding: "1.25rem" }}>
              <h3 style={{ marginTop: 0, fontSize: "0.8rem", color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 700 }}>{card.title}</h3>
              {card.rows.map(([label, value]) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "0.35rem 0", borderBottom: "1px solid var(--border-color)", fontSize: "0.83rem", gap: "0.5rem" }}>
                  <span style={{ color: "var(--text-secondary)", flexShrink: 0 }}>{label}</span>
                  <strong style={{ textAlign: "right", wordBreak: "break-all" }}>{value}</strong>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <table>
      <thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead>
      <tbody>{rows.length ? rows.map((row, index) => <tr key={`${row[0]}-${index}`}>{row.map((cell) => <td key={cell}>{cell}</td>)}</tr>) : <tr><td colSpan={headers.length}>No records yet</td></tr>}</tbody>
    </table>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<App />);








