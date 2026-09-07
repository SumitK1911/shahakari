import React, { useState, useEffect, FormEvent } from "react";
import ReactDOM from "react-dom/client";
import { UserCircle, MapPin, Receipt, RefreshCw, WifiOff, LogOut, CheckCircle2 } from "lucide-react";
import "./mobile.css";

// Assume we share some types with main.tsx or define them locally for simplicity in this file.
const API_BASE = "/api/v1";

type Member = { id: string; member_no: string; name: string; phone?: string; status: string; risk_category?: string };
type SavingsAccount = { id: string; member_id: string; account_no: string; account_type: string; balance: string; status: string };
type FieldCollectionBatch = { id: string; route_id?: string; collection_date: string; status: string };
type OfflineFieldEntry = { id: string; batchId: string; body: Record<string, string>; createdAt: string; status: string; attempts: number; lastError?: string };

// IndexedDB Queue Logic
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

function MobileApp() {
  const [token, setToken] = useState<string | null>(localStorage.getItem("sahakari_token"));
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [queue, setQueue] = useState<OfflineFieldEntry[]>([]);
  const [toast, setToast] = useState("");
  
  // App State
  const [members, setMembers] = useState<Member[]>([]);
  const [accounts, setAccounts] = useState<SavingsAccount[]>([]);
  const [activeBatch, setActiveBatch] = useState<FieldCollectionBatch | null>(null);
  
  // Navigation State
  const [step, setStep] = useState<"dashboard" | "select_member" | "collect" | "success">("dashboard");
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<SavingsAccount | null>(null);
  
  // Collection Form State
  const [amount, setAmount] = useState("");

  useEffect(() => {
    const updateOnline = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateOnline);
    window.addEventListener("offline", updateOnline);
    refreshQueue();
    return () => {
      window.removeEventListener("online", updateOnline);
      window.removeEventListener("offline", updateOnline);
    };
  }, []);

  useEffect(() => {
    if (token && isOnline) {
      fetchInitialData();
      syncOfflineQueue();
    }
  }, [token, isOnline]);

  async function refreshQueue() {
    try {
      const entries = await fieldQueueAll();
      setQueue(entries);
    } catch (e) {
      console.error(e);
    }
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers
      }
    });
    if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    return response.json();
  }

  async function fetchInitialData() {
    try {
      const [membersData, accountsData, batchesData] = await Promise.all([
        request<Member[]>("/members?limit=200"),
        request<SavingsAccount[]>("/savings/accounts"),
        request<FieldCollectionBatch[]>("/field-collections/batches")
      ]);
      setMembers(membersData);
      setAccounts(accountsData);
      // For simplicity, grab the first draft batch or null
      const draftBatch = batchesData.find(b => b.status === "draft");
      setActiveBatch(draftBatch || null);
    } catch (err) {
      console.error("Failed to load initial data", err);
    }
  }

  async function syncOfflineQueue() {
    const entries = await fieldQueueAll();
    if (!entries.length) return;
    
    let synced = 0;
    for (const entry of entries) {
      try {
        await request(`/field-collections/batches/${entry.batchId}/entries`, {
          method: "POST",
          body: JSON.stringify(entry.body)
        });
        await fieldQueueDelete(entry.id);
        synced++;
      } catch (err) {
        await fieldQueuePut({ ...entry, status: "failed", attempts: entry.attempts + 1 });
      }
    }
    await refreshQueue();
    if (synced > 0) showToast(`Synced ${synced} entries to server.`);
  }

  async function handleLogin(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(fd))
      });
      if (!response.ok) throw new Error("Login failed");
      const data = await response.json();
      localStorage.setItem("sahakari_token", data.access_token);
      setToken(data.access_token);
    } catch (err) {
      showToast("Login failed. Check credentials.");
    }
  }

  function handleSelectMember(m: Member) {
    setSelectedMember(m);
    setStep("collect");
  }

  async function submitCollection(e: FormEvent) {
    e.preventDefault();
    if (!activeBatch || !selectedMember || !selectedAccount || !amount) return;

    const body = {
      member_id: selectedMember.id,
      savings_account_id: selectedAccount.id,
      collection_type: "savings_deposit",
      payment_method: "cash",
      amount: parseFloat(amount).toString(),
      receipt_no: `REC-M-${Date.now()}`,
      client_request_id: `offline-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      collected_at: new Date().toISOString()
    };

    if (isOnline) {
      try {
        await request(`/field-collections/batches/${activeBatch.id}/entries`, {
          method: "POST",
          body: JSON.stringify(body)
        });
        showToast("Collection recorded successfully!");
      } catch (err) {
        await queueEntry(activeBatch.id, body);
      }
    } else {
      await queueEntry(activeBatch.id, body);
    }

    setAmount("");
    setStep("success");
  }

  async function queueEntry(batchId: string, body: any) {
    await fieldQueuePut({
      id: body.client_request_id,
      batchId,
      body,
      createdAt: new Date().toISOString(),
      status: "queued",
      attempts: 0
    });
    await refreshQueue();
    showToast("Saved offline. Will sync when online.");
  }

  if (!token) {
    return (
      <div className="mobile-app" style={{ justifyContent: 'center', padding: '24px' }}>
        <h1 style={{ textAlign: 'center', color: 'var(--primary-color)', marginBottom: '24px' }}>Sahakari Collector</h1>
        <form className="card" onSubmit={handleLogin}>
          <div className="form-group">
            <label>Email</label>
            <input name="email" type="email" defaultValue="admin@sahakari.local" required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input name="password" type="password" defaultValue="ChangeMe123!" required />
          </div>
          <button type="submit" className="btn btn-primary">Login</button>
        </form>
      </div>
    );
  }

  return (
    <div className="mobile-app">
      {!isOnline && (
        <div className="offline-banner">
          <WifiOff size={16} style={{ verticalAlign: 'middle', marginRight: '8px' }} />
          You are offline. Collections will be saved locally.
        </div>
      )}

      <header className="header">
        <h1>{step === 'dashboard' ? 'Dashboard' : step === 'select_member' ? 'Select Member' : 'Collect'}</h1>
        {step === 'dashboard' ? (
          <button style={{ background: 'transparent', border: 'none', color: 'white' }} onClick={() => { localStorage.removeItem("sahakari_token"); setToken(null); }}>
            <LogOut size={20} />
          </button>
        ) : (
          <button style={{ background: 'transparent', border: 'none', color: 'white' }} onClick={() => setStep('dashboard')}>
            Back
          </button>
        )}
      </header>

      <main className="content">
        {step === 'dashboard' && (
          <>
            <div className="card">
              <div className="card-title">Daily Summary</div>
              <div className="summary-grid">
                <div className="summary-box">
                  <span>Queued Syncs</span>
                  <strong>{queue.length}</strong>
                </div>
                <div className="summary-box">
                  <span>Active Batch</span>
                  <strong>{activeBatch ? "Yes" : "None"}</strong>
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ marginTop: '16px' }}
                onClick={syncOfflineQueue}
                disabled={!isOnline || queue.length === 0}
              >
                <RefreshCw size={16} style={{ marginRight: '8px' }} /> Sync Now
              </button>
            </div>

            <button 
              className="btn btn-primary" 
              style={{ padding: '20px', fontSize: '1.1rem' }}
              onClick={() => setStep('select_member')}
              disabled={!activeBatch}
            >
              <MapPin size={24} style={{ marginRight: '12px' }} />
              Start Collection
            </button>
            {!activeBatch && <p style={{ color: 'var(--danger)', marginTop: '8px', textAlign: 'center' }}>No active collection batch found. Open a batch on Desktop first.</p>}
          </>
        )}

        {step === 'select_member' && (
          <div className="card" style={{ padding: 0 }}>
            {members.slice(0, 50).map(m => (
              <div key={m.id} className="list-item" onClick={() => handleSelectMember(m)}>
                <div className="list-item-content">
                  <h4>{m.name}</h4>
                  <p>{m.member_no} | {m.phone || "No phone"}</p>
                </div>
                <UserCircle color="var(--primary-color)" />
              </div>
            ))}
          </div>
        )}

        {step === 'collect' && selectedMember && (
          <form className="card" onSubmit={submitCollection}>
            <div className="card-title">Collect from {selectedMember.name}</div>
            
            <div className="form-group">
              <label>Select Account</label>
              <select 
                required 
                onChange={(e) => {
                  const acc = accounts.find(a => a.id === e.target.value);
                  setSelectedAccount(acc || null);
                }}
              >
                <option value="">-- Choose Account --</option>
                {accounts.filter(a => a.member_id === selectedMember.id).map(a => (
                  <option key={a.id} value={a.id}>{a.account_no} ({a.account_type}) - Rs.{a.balance}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Amount (Rs)</label>
              <input 
                type="number" 
                min="0" 
                step="0.01" 
                value={amount} 
                onChange={(e) => setAmount(e.target.value)} 
                required 
                placeholder="Enter amount"
              />
            </div>

            <button type="submit" className="btn btn-primary" disabled={!selectedAccount || !amount}>
              Save Collection
            </button>
          </form>
        )}

        {step === 'success' && (
          <div className="card" style={{ textAlign: 'center', padding: '32px 16px' }}>
            <CheckCircle2 size={64} color="var(--success)" style={{ margin: '0 auto 16px' }} />
            <h2 style={{ marginBottom: '8px' }}>Collection Saved!</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>The transaction has been recorded.</p>
            <button className="btn btn-primary" onClick={() => setStep('dashboard')}>Return to Dashboard</button>
          </div>
        )}
      </main>

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <MobileApp />
  </React.StrictMode>
);
