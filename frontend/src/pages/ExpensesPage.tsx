  import { useMemo, useState } from "react";
  import { useNavigate } from "react-router-dom";
  import WavyBackground from "../components/background/WavyBackground";
  import AppSidebar from "../components/layout/AppSidebar";
  import AppHeader from "../components/layout/AppHeader";
  import { useGroupFinances } from '../hooks/useGroupFinances';
  import { parseMinor, minorToDecimal, formatMoney } from '../lib/currency';
  import type { GroupCurrency } from '../lib/groups';
  type Expense = {id:number; title:string; category:string; group:string; groupId:number; date:string; payer:string; ownPayer:boolean; total:number; share:number; impact:number; status:string; reference:string; currency:GroupCurrency; splits:{name:string; amount:string}[]};
  const money = (n:number,c:GroupCurrency) => formatMoney(minorToDecimal(n,c),c);
  const card =
    "rounded-2xl border border-[#e1e9df] bg-white/90 shadow-[0_4px_20px_rgba(43,70,48,0.06)] backdrop-blur-sm " +
    "dark:border-[#35483b] dark:bg-[#1b201d]/95 dark:text-[#f3f5f2]";
  export default function ExpensesPage() {
    const navigate = useNavigate();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [category, setCategory] = useState("All Categories");
    const [payer, setPayer] = useState("All Payers");
    const [group, setGroup] = useState("All Groups");
    const [range, setRange] = useState("All Time");
    const [page, setPage] = useState(1);
    const [selected, setSelected] = useState<Expense | null>(null);
    const pageSize = 5;

    const {groups,currentUserId,isLoading,error,reload,reloadGroups}=useGroupFinances();
    const expenses = useMemo(() => groups.flatMap(g=>g.expenses.map(e=>{
      const name=(id:number)=>g.members.find(m=>m.user_id===id)?.full_name || `Member ${id}`;
      const total=parseMinor(e.amount,g.currency), share=parseMinor(e.splits.find(s=>s.user_id===currentUserId)?.amount_owed??'0',g.currency);
      const ownPayer=e.paid_by===currentUserId;
      return {id:e.id,title:e.description,category:e.category,group:g.name,groupId:g.id,date:e.expense_date??e.created_at.slice(0,10),payer:name(e.paid_by)+(ownPayer?' (You)':''),ownPayer,total,share,impact:(ownPayer?total:0)-share,status:'Recorded',reference:e.reference??'—',currency:g.currency,splits:e.splits.map(s=>({name:name(s.user_id),amount:s.amount_owed}))};
    })).sort((a,b)=>b.date.localeCompare(a.date)||b.id-a.id),[groups,currentUserId]);
    const summary = new Map<GroupCurrency,{net:number;owed:number;owe:number;settled:number}>();
    for(const g of groups.filter(g=>group==='All Groups'||String(g.id)===group)) {
      const v=summary.get(g.currency)??{net:0,owed:0,owe:0,settled:0};
      const balance=parseMinor(g.balances.find(b=>b.user_id===currentUserId)?.net_balance??'0',g.currency);
      v.net+=balance;v.owed+=Math.max(0,balance);v.owe+=Math.max(0,-balance);
      v.settled+=g.payments.filter(p=>p.status==='confirmed'&&(p.from_user_id===currentUserId||p.to_user_id===currentUserId)).reduce((n,p)=>n+parseMinor(p.amount,g.currency),0);summary.set(g.currency,v);
    }
    const summaryValue=(key:'net'|'owed'|'owe'|'settled')=>isLoading||error?'—':Array.from(summary,([c,v])=>`${c} ${money(v[key],c)}`).join(' · ')||'—';
    const [now] = useState(() => new Date());
    const filtered = useMemo(() => {
      return expenses.filter((e) => {
        const query = search.toLowerCase().trim();
        const matchText = !query || `${e.title} ${e.group} ${e.category} ${e.payer}`.toLowerCase().includes(query);
        const matchCategory = category === "All Categories" || e.category === category;
        const matchPayer = payer === "All Payers" || (payer === "You Paid" ? e.ownPayer : !e.ownPayer);
        const matchGroup = group === "All Groups" || String(e.groupId) === group;
        const date = new Date(`${e.date}T12:00:00`);
        const matchRange = range === "All Time" || (range === "This Month" ? date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear() : (now.getTime() - date.getTime()) / 86400000 <= 30 && date <= now);
        return matchText && matchCategory && matchPayer && matchGroup && matchRange;
      });
    }, [expenses, search, category, payer, group, range, now]);
    const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
    const shown = filtered.slice((Math.min(page, totalPages) - 1) * pageSize, Math.min(page, totalPages) * pageSize);
    const changeFilter = (setter: (value: string) => void, value: string) => { setter(value); setPage(1); };

    const exportCsv = () => {
      const rows = [["Expense", "Category", "Group", "Date", "Payer", "Total", "Your Share", "Net Impact", "Status", "Currency"], ...filtered.map(e => [e.title, e.category, e.group, e.date, e.payer, minorToDecimal(e.total,e.currency), minorToDecimal(e.share,e.currency), minorToDecimal(e.impact,e.currency), e.status, e.currency])];
      const csv = rows.map(row => row.map(value => `"${(/^[\s]*[=+@-]/.test(String(value)) && !/^-?\d+(\.\d+)?$/.test(String(value)) ? "'"+String(value) : String(value)).replace(/"/g, '""')}"`).join(",")).join("\r\n");
      const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "ledgersplit-expenses.csv";
      anchor.click();
      URL.revokeObjectURL(url);
    };


    return (
        <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] text-[#22352a] dark:bg-[#141715] dark:text-[#f3f5f2]">
        <div className="pointer-events-none fixed inset-0 -z-10 opacity-40 dark:opacity-70">
          <WavyBackground />
        </div>
        <AppHeader
          sidebarOpen={sidebarOpen}
          onMenuClick={() => setSidebarOpen(true)}
          search={search}
          onSearchChange={(value) => changeFilter(setSearch, value)}
          searchPlaceholder="Search expenses, merchants, groups..."
        />

      <AppSidebar
          open={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
      />
      <main className="mx-auto max-w-[1600px] space-y-6 px-4 py-7 sm:px-8">
        <section className="flex flex-col justify-between gap-5 lg:flex-row lg:items-center">
          <div><div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-[#325f3f] shadow-sm">
              <span className="h-2 w-2 rounded-full bg-[#4a7856]" />
               Multi-Ledger Active
              </div><h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">Expenses Overview</h1><p className="mt-2 text-sm text-[#748675] dark:text-[#b9cbbd]">Manage shared expenses across your groups.</p></div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex rounded-xl bg-[#edf3ec] p-1 dark:bg-[#232b25]">{["This Month", "Last 30 Days", "All Time"].map(item => <button type="button" key={item} onClick={() => changeFilter(setRange, item)} className={`rounded-lg px-3 py-2 text-xs ${range === item ? "bg-white font-semibold text-[#376247] shadow-sm dark:bg-[#35483b] dark:text-[#e4eee6]" : "text-[#667768] dark:text-[#b9cbbd]"}`}>{item}</button>)}</div>
            <select aria-label="Filter groups" value={group} onChange={e => changeFilter(setGroup, e.target.value)} className="rounded-xl border border-[#dce7db] bg-white px-3 py-2 text-xs"><option>All Groups</option>{groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select>

            <button
              type="button"
              onClick={exportCsv} disabled={isLoading || Boolean(error)}
              className="rounded-xl border border-[#dce7db] bg-white px-3 py-2 text-xs font-semibold text-[#22352a] transition-colors hover:bg-[#edf4ec] dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#e4eee6] dark:hover:bg-[#304236]"
            >
              ↓ Export CSV
            </button>

            <button type="button" onClick={() => navigate("/expenses/add")} className="rounded-xl bg-[#4a7856] px-4 py-2 text-sm font-semibold text-white hover:bg-[#3d6447]">+ Add Expense</button>
          </div>
        </section>

        {isLoading && <p role="status">Loading expenses…</p>}{error && <p role="alert">{error} <button onClick={()=>{reloadGroups();reload();}}>Retry</button></p>}<section aria-label="Financial summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[

            {label:'Net Balance',value:summaryValue('net'),badge:'Current',color:'text-emerald-800 dark:text-emerald-300',badgeColor:'bg-emerald-100 text-emerald-800',description:'Current group balances by currency',footer:'You are owed − You owe'},
            {label:'You Are Owed',value:summaryValue('owed'),badge:'Current',color:'text-blue-900 dark:text-blue-300',badgeColor:'bg-blue-100 text-blue-900',description:'Positive group balances',footer:'Selected groups'},
            {label:'You Owe',value:summaryValue('owe'),badge:'Current',color:'text-red-800 dark:text-rose-300',badgeColor:'bg-red-100 text-red-800',description:'Negative group balances',footer:'Selected groups'},
            {label:'Settled Volume',value:summaryValue('settled'),badge:'Confirmed',color:'text-[#263c2d] dark:text-[#c4e4ca]',badgeColor:'bg-slate-100 text-slate-700',description:'Your confirmed incoming and outgoing payments',footer:'All time · selected groups'},
          ].map((stat) => <article key={stat.label} className={`${card} flex min-h-48 flex-col justify-between p-5 transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_32px_rgba(43,70,48,0.1)]`}><div><div className="flex items-center justify-between gap-2"><h2 className="text-[11px] font-bold uppercase tracking-wider text-[#6f8273] dark:text-[#b0c5b5]">{stat.label}</h2><span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${stat.badgeColor}`}>{stat.badge}</span></div><p className={`mt-4 text-2xl font-extrabold tabular-nums ${stat.color}`}>{stat.value}</p><p className="mt-2 text-xs text-[#758776] dark:text-[#c0d0c4]">
{stat.description}</p></div><div className="mt-6 border-t border-[#e6eee4] pt-3 text-xs text-[#5e7965] dark:border-[#35483b] dark:text-[#b9cbbd]">{stat.footer}</div></article>)}
        </section>

        <section className={`${card} overflow-hidden`}>
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e6eee4] p-5"><div><h2 className="text-lg font-bold">Recent Expenses</h2><p className="text-xs text-[#748675]">Recorded expenses across your groups</p></div><div className="flex flex-wrap items-center gap-2"><input aria-label="Filter expenses" placeholder="Filter expenses..." value={search} onChange={e => changeFilter(setSearch, e.target.value)} className="rounded-xl border border-[#dce7db] bg-[#f7faf6] px-3 py-2 text-xs"/><select aria-label="Filter categories" value={category} onChange={e => changeFilter(setCategory, e.target.value)} className="rounded-xl border border-[#dce7db] bg-white px-3 py-2 text-xs"><option>All Categories</option>{[...new Set(expenses.map(e => e.category))].map(c => <option key={c}>{c}</option>)}</select><select aria-label="Filter payers" value={payer} onChange={e => changeFilter(setPayer, e.target.value)} className="rounded-xl border border-[#dce7db] bg-white px-3 py-2 text-xs"><option>All Payers</option><option>You Paid</option><option>Others Paid</option></select><button type="button" onClick={() => { setSearch(""); setCategory("All Categories"); setPayer("All Payers"); setGroup("All Groups"); setRange("All Time"); setPage(1); }} className="text-xs font-semibold text-[#4a7856]">Clear Filters</button></div></div>
          <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-[#f3f7f2] text-[11px] uppercase tracking-wider text-[#687c6c] dark:bg-[#232b25] dark:text-[#aab5ad]"><tr>{["Expense & Category", "Group", "Date", "Payer", "Total", "Your Share", "Net Impact", "Status", "Action"].map(h => <th key={h} className="px-4 py-4 font-semibold">{h}</th>)}</tr></thead><tbody className="divide-y divide-[#e6eee4] dark:divide-[#35483b]">{shown.map(e => <tr
  key={e.id}
  className="transition-colors hover:bg-[#f5faf4] dark:hover:bg-[#29372e]"
><td className="px-4 py-5"><div className="font-semibold">{e.title}</div><div className="mt-1 text-xs text-[#849587] dark:text-[#b9cbbd]">{e.category} · {e.reference}</div></td><td className="px-4 py-5">{e.group}</td><td className="px-4 py-5 whitespace-nowrap text-[#748675] dark:text-[#c0d0c4]">{e.date}</td><td className="px-4 py-5">{e.payer}</td><td className="px-4 py-5 tabular-nums font-semibold">{money(e.total,e.currency)}</td><td className="px-4 py-5 tabular-nums">{money(e.share,e.currency)}</td><td className={`px-4 py-5 tabular-nums font-bold ${e.impact >= 0 ? "text-emerald-700" : "text-rose-700"}`}>{e.impact >= 0 ? "+" : "−"}{money(Math.abs(e.impact),e.currency)}</td><td className="px-4 py-5 text-xs">{e.status}</td><td className="px-4 py-5"><button type="button" onClick={() => setSelected(e)} className="font-semibold text-[#4a7856] hover:underline">View Split</button></td></tr>)}</tbody></table>{!isLoading && !error && shown.length === 0 && <div className="p-12 text-center text-sm text-[#748675]">No expenses match these filters.</div>}</div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#e6eee4] bg-[#f8faf7] p-4 text-xs text-[#748675] dark:border-[#35483b] dark:bg-[#1b201d] dark:text-[#aab5ad]"><span>Showing {shown.length} of {filtered.length} expenses</span><div className="flex items-center gap-2"><button type="button" disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="rounded-lg border border-[#dce7db] px-3 py-2 disabled:opacity-40">Previous</button><span>Page {Math.min(page, totalPages)} of {totalPages}</span><button type="button" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="rounded-lg border border-[#dce7db] px-3 py-2 disabled:opacity-40">Next</button></div></div>
        </section>
      </main>

      {selected && <div role="presentation" className="fixed inset-0 z-[60] flex items-center justify-center bg-[#142319]/40 p-4" onMouseDown={e => { if (e.target === e.currentTarget) setSelected(null); }}><section role="dialog" aria-modal="true" aria-labelledby="expense-detail-title" className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-3xl bg-white dark:bg-[#1b201d] p-6 shadow-2xl"><div className="flex items-start justify-between"><div><p className="text-xs font-semibold text-[#4a7856]">{selected.category}</p><h2 id="expense-detail-title" className="mt-1 text-xl font-bold">{selected.title}</h2><p className="mt-1 text-sm text-[#748675]">{selected.group}</p></div><button type="button" onClick={() => setSelected(null)} aria-label="Close details" className="rounded-lg px-2 py-1 text-lg hover:bg-[#edf4ec]">✕</button></div><div className="mt-6 grid grid-cols-2 gap-3 rounded-xl bg-[#f2f7f1] p-4"><div><p className="text-xs text-[#748675]">Total</p><p className="font-bold">{money(selected.total,selected.currency)}</p></div><div><p className="text-xs text-[#748675]">Your Share</p><p className="font-bold">{money(selected.share,selected.currency)}</p></div></div><dl className="mt-5 space-y-3 text-sm"><div className="flex justify-between gap-4"><dt className="text-[#748675]">Paid by</dt><dd className="font-semibold">{selected.payer}</dd></div><div className="flex justify-between gap-4"><dt className="text-[#748675]">Your net impact</dt><dd className="font-semibold">{selected.impact >= 0 ? "+" : "−"}{money(Math.abs(selected.impact),selected.currency)}</dd></div><div className="flex justify-between gap-4"><dt className="text-[#748675]">Reference</dt><dd>{selected.reference}</dd></div></dl><p className="mt-5 text-xs text-[#748675]">Member-by-member breakdown</p><div className="mt-3 space-y-2">{selected.splits.map((s,i)=><div key={i} className="flex justify-between text-sm"><span>{s.name}</span><span>{formatMoney(s.amount,selected.currency)}</span></div>)}</div><button type="button" onClick={() => setSelected(null)} className="mt-5 w-full rounded-xl bg-[#4a7856] py-3 font-semibold text-white">Close Breakdown</button></section></div>}
    </div>
  );
}
