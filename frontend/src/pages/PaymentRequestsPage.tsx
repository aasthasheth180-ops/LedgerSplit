import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send, Clock3, CheckCircle2, XCircle, Plus } from "lucide-react";
import AppHeader from "../components/layout/AppHeader";
import AppSidebar from "../components/layout/AppSidebar";
import WavyBackground from "../components/background/WavyBackground";
import { useGroupFinances } from "../hooks/useGroupFinances";
import { useApi } from "../hooks/useApi";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import { formatMoney, parseMinor, minorToDecimal } from "../lib/currency";
function SummaryCard({
  label,
  value,
  description,
  icon: Icon,
}: {
  label: string;
  value: string;
  description: string;
  icon: typeof Send;
}) {
  return (
    <div className="rounded-2xl border border-[#e8e6e1] dark:border-[#35483b] bg-white/95 dark:bg-[#1b201d] p-5 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.015] hover:shadow-xl">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-[#829386] dark:text-[#b9cbbd]">
          {label}
        </p>
        <div className="rounded-full bg-[#eef3ef] dark:bg-[#304236] p-2 text-[#4a7856] dark:text-[#a1d5ad]">
          <Icon size={18} />
        </div>
      </div>
      <h3 className="mt-3 text-3xl font-bold tracking-tight text-[#22352a] dark:text-[#f3f5f2]">
        {value}
      </h3>
      <p className="mt-2 text-xs text-[#829386] dark:text-[#b9cbbd]">{description}</p>
    </div>
  );
}

export default function PaymentRequestsPage() {
 const navigate = useNavigate();
 const [sidebarOpen,setSidebarOpen] = useState(false);
 const [search,setSearch] = useState("");
 const [status,setStatus] = useState("all");
 const [direction,setDirection] = useState("all");
 const [dateFilter,setDateFilter] = useState("all");
 const [groupFilter,setGroupFilter] = useState("all");
 const [message,setMessage] = useState("");
 const {groups,currentUserId,isLoading,error,reload,reloadGroups} = useGroupFinances();
 const {request} = useApi();
 const submission = useAuthSubmission();
 const rows = groups.flatMap(g => g.paymentRequests.filter(r => r.requester_id === currentUserId || r.debtor_id === currentUserId).map(r => ({...r, group:g, outgoing:r.requester_id === currentUserId, person:g.members.find(m => m.user_id === (r.requester_id === currentUserId ? r.debtor_id : r.requester_id))?.full_name ?? `User ${r.requester_id === currentUserId ? r.debtor_id : r.requester_id}`}))).sort((a,b)=>b.created_at.localeCompare(a.created_at));
 const [now] = useState(() => Date.now());
 const visible = rows.filter(r => (status === "all" || r.status === status) && (direction === "all" || (direction === "outgoing") === r.outgoing) && (groupFilter === "all" || String(r.group_id) === groupFilter) && (dateFilter === "all" || (now-new Date(r.created_at).getTime() <= Number(dateFilter)*86400000)) && `${r.person} ${r.group.name} ${r.description ?? ""} ${r.id}`.toLowerCase().includes(search.trim().toLowerCase()));
 const pending = visible.filter(r=>r.status === "pending");
 const fulfilled = visible.filter(r=>r.status === "fulfilled");
 const cancelled = visible.filter(r=>r.status === "cancelled");
 async function cancel(groupId:number,id:number) {
   if (!window.confirm("Cancel this payment request?")) return;
   if (!submission.beginSubmission()) return;
   setMessage("");
   try { await request(`/groups/${groupId}/payment-requests/${id}/cancel`,{method:"POST"}); reload(); }
   catch(e) {setMessage(e instanceof Error ? e.message : "Unable to cancel request."); reload();}
   finally {submission.endSubmission();}
 }
 const field="rounded-xl border border-[#e8e6e1] bg-white px-3 py-2 text-sm dark:border-[#35483b] dark:bg-[#232b25]";
 return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] dark:bg-[#141715] text-[#22352a] dark:text-[#f3f5f2]">
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-40 dark:opacity-70">
        <WavyBackground />
      </div>

      <AppHeader
        sidebarOpen={sidebarOpen}
        onMenuClick={() => setSidebarOpen(true)}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search payment requests..."
      />

      <AppSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="relative z-10 mx-auto max-w-[1600px] space-y-6 px-4 py-7 sm:px-8">
        <section className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#e1e8df] bg-white dark:bg-[#1b201d] px-3 py-1.5 text-xs font-semibold text-[#4a7856] dark:text-[#a1d5ad]">
              <span className="h-2 w-2 rounded-full bg-[#4a7856]" />
              Financial Workspace
            </div>

            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Payment Requests
            </h1>
            <p className="mt-2 text-sm text-[#829386] dark:text-[#b9cbbd]">
              Track settlement requests and
              follow up on shared balances.
            </p>
          </div>

          <button
            onClick={() => navigate("/payment-requests/new")}
            className="flex items-center gap-2 rounded-xl bg-[#4a7856] px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#3d6548] hover:shadow-lg"
          >
            <Plus size={18} />
            New Payment Request
          </button>
        </section>

        {isLoading && <p role="status">Loading payment requests...</p>}
        {error && <p role="alert">{error}</p>}
        {message && <p role="alert">{message}</p>}
        <button type="button" className={field} disabled={isLoading || submission.isLoading} onClick={()=>{reloadGroups();reload();}}>Refresh</button>
        {!isLoading && !error && <>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard label="Total Requests" value={String(visible.length)} description="Matching incoming and outgoing requests" icon={Send}/>
          <SummaryCard label="Pending Requests" value={String(pending.length)} description="Awaiting full settlement" icon={Clock3}/>
          <SummaryCard label="Fulfilled Requests" value={String(fulfilled.length)} description="Fully reconciled" icon={CheckCircle2}/>
          <SummaryCard label="Cancelled Requests" value={String(cancelled.length)} description="Cancelled by requester" icon={XCircle}/>
        </section>
        <section className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
          <div className="rounded-2xl border border-[#e8e6e1] bg-white/95 p-6 dark:border-[#35483b] dark:bg-[#1b201d]">
            <h2 className="text-lg font-bold">Request Status Breakdown</h2>
            <div className="mt-6 flex h-4 overflow-hidden rounded-full bg-[#eef3ef] dark:bg-[#304236]">{[pending,fulfilled,cancelled].map((items,i)=><div key={i} style={{width:`${items.length/Math.max(1,visible.length)*100}%`,backgroundColor:["#dc9a45","#4a7856","#d97862"][i]}}/>)}</div>
            <p className="mt-4 text-sm">{pending.length} Pending · {fulfilled.length} Fulfilled · {cancelled.length} Cancelled</p>
          </div>
          <div className="rounded-2xl border border-[#e8e6e1] bg-white/95 p-6 dark:border-[#35483b] dark:bg-[#1b201d]"><h2 className="text-lg font-bold">Request delivery</h2><p className="mt-2 text-sm">Requests are visible in LedgerSplit. Email, SMS and automatic reminders are not enabled.</p></div>
        </section>
        <section className="overflow-hidden rounded-2xl border border-[#e8e6e1] bg-white/95 dark:border-[#35483b] dark:bg-[#1b201d]">
          <div className="flex flex-wrap items-center gap-3 p-5"><h2 className="mr-auto text-lg font-bold">Settlement Activity</h2>
          <select aria-label="Request direction" className={field} value={direction} onChange={e=>setDirection(e.target.value)}><option value="all">All directions</option><option value="incoming">Incoming</option><option value="outgoing">Outgoing</option></select>
          <select aria-label="Request status" className={field} value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option><option value="pending">Pending</option><option value="fulfilled">Fulfilled</option><option value="cancelled">Cancelled</option></select>
          <select aria-label="Request date" className={field} value={dateFilter} onChange={e=>setDateFilter(e.target.value)}><option value="all">All time</option><option value="30">Last 30 days</option><option value="90">Last 90 days</option></select>
          <select aria-label="Request group" className={field} value={groupFilter} onChange={e=>setGroupFilter(e.target.value)}><option value="all">All groups</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[950px] text-left text-sm"><thead className="bg-[#f7f8f6] dark:bg-[#232b25]"><tr>{["Member","Description","Group","Requested","Fulfilled","Remaining","Due date","Status","Action"].map(h=><th key={h} className="p-4">{h}</th>)}</tr></thead><tbody className="divide-y divide-[#eef0ec] dark:divide-[#35483b]">{visible.map(r=><tr key={`${r.group_id}:${r.id}`}><td className="p-4 font-semibold">{r.person}<p className="text-xs font-normal">{r.outgoing?"Outgoing":"Incoming"}</p></td><td className="p-4">{r.description || "Settlement request"}<p className="text-xs">#{r.id} · {new Date(r.created_at).toLocaleDateString()}</p></td><td className="p-4">{r.group.name}</td><td className="p-4">{formatMoney(r.amount,r.group.currency)}</td><td className="p-4">{formatMoney(r.fulfilled_amount,r.group.currency)}</td><td className="p-4">{r.status === "cancelled" ? "—" : formatMoney(minorToDecimal(parseMinor(r.amount,r.group.currency)-parseMinor(r.fulfilled_amount,r.group.currency),r.group.currency),r.group.currency)}</td><td className="p-4">{r.due_date ?? "—"}</td><td className="p-4 capitalize">{r.status}</td><td className="p-4">{r.status === "pending" && (r.outgoing ? <button type="button" disabled={submission.isLoading} className="font-semibold text-red-700 dark:text-red-300 disabled:opacity-50" onClick={()=>void cancel(r.group_id,r.id)}>Cancel request</button> : <button type="button" className="font-semibold text-[#4a7856] dark:text-[#a1d5ad]" onClick={()=>navigate("/balances")}>View balances</button>)}</td></tr>)}</tbody></table>{!visible.length && <p className="p-10 text-center">No requests match your filters.</p>}</div>
        </section></>}
      </main></div>);
}
