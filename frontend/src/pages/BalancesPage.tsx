
import { useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";

import AppHeader from "../components/layout/AppHeader";
import AppSidebar from "../components/layout/AppSidebar";
import WavyBackground from "../components/background/WavyBackground";
import { useTheme } from "../context/ThemeContext";

import { useGroupFinances } from "../hooks/useGroupFinances";
import { useApi } from "../hooks/useApi";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import { createIdempotencyTracker, idempotentPost } from "../lib/idempotency";
import { parseMinor, minorToDecimal, formatMoney, currencyDigits } from "../lib/currency";
import type { GroupCurrency } from "../lib/groups";
import type { PaymentResponse } from "../lib/payments";
import { useNavigate } from "react-router-dom";
type Period = "7 Days" | "30 Days" | "90 Days";
function SummaryCard({
  label,
  value,
  subtitle,
  accent = "text-[#22352a] dark:text-[#d0ead6]",
}: {
  label: string;
  value: string;
  subtitle: string;
  accent?: string;
}) {
  return (

    <div className="rounded-2xl border border-[#e2e8df] bg-white/95 p-5 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.015] hover:shadow-xl dark:border-[#35483b] dark:bg-[#1b201d] dark:shadow-black/20">
      <p className="text-xs font-bold uppercase tracking-wider text-[#7c8d80] dark:text-[#b5c7b9]">
        {label}
      </p>
      <h3
        className={`mt-3 text-3xl font-extrabold tracking-tight tabular-nums ${accent}`}
      >
        {value}
      </h3>
      <p className="mt-2 text-xs leading-5 text-[#748675] dark:text-[#b9cbbd]">{subtitle}</p>
    </div>
  );
}

export default function BalancesPage() {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [period, setPeriod] = useState<Period>("30 Days");
  const [selectedGroup, setSelectedGroup] = useState("All Groups");

  const navigate = useNavigate();
  const { groups, currentUserId, isLoading, error, reload, reloadGroups } = useGroupFinances();
  const { request } = useApi();
  const submission = useAuthSubmission();
  const [tracker] = useState(() => createIdempotencyTracker());
  const [actionError, setActionError] = useState("");
  const [currencyChoice, setCurrencyChoice] = useState<GroupCurrency | "">("");
  const scoped = groups.filter(g => selectedGroup === "All Groups" || String(g.id) === selectedGroup);
  const currencies = [...new Set(scoped.map(g => g.currency))];
  const currency = currencies.includes(currencyChoice as GroupCurrency) ? currencyChoice as GroupCurrency : currencies[0] ?? "USD";
  const active = scoped.filter(g => g.currency === currency);
  const units = (v: string) => parseMinor(v,currency);
  const scale = 10 ** currencyDigits(currency);
  const money = (n: number) => formatMoney(minorToDecimal(Math.round(n * scale),currency),currency);
  const name = (g: typeof groups[number], id: number) => g.members.find(m => m.user_id === id)?.full_name || `Member ${id}`;
  const groupBalances = active.map(g => ({id:g.id,name:g.name,color:g.color,amount:units(g.balances.find(b=>b.user_id===currentUserId)?.net_balance ?? "0")/scale}));
  const groupChartData = groupBalances.map(g=>({...g,chartAmount:Math.abs(g.amount)}));
  const netUnits = active.map(g=>units(g.balances.find(b=>b.user_id===currentUserId)?.net_balance ?? "0"));
  const youAreOwed = netUnits.reduce((a,b)=>a+Math.max(0,b),0)/scale;
  const youOwe = netUnits.reduce((a,b)=>a+Math.max(0,-b),0)/scale;
  const netBalance = netUnits.reduce((a,b)=>a+b,0)/scale;
  const people = active.flatMap(g=>g.settlements.filter(t=>t.from_user_id===currentUserId||t.to_user_id===currentUserId).map(t=>{
    const incoming=t.to_user_id===currentUserId, userId=incoming?t.from_user_id:t.to_user_id;
    const person=name(g,userId);
    return {key:`${g.id}-${userId}-${incoming}`,groupId:g.id,userId,name:person,initials:person.split(" ").map(x=>x[0]).slice(0,2).join(""),group:g.name,amount:units(t.amount)/scale,incoming};
  })).filter(p=>`${p.name} ${p.group}`.toLowerCase().includes(search.trim().toLowerCase()));
  const filteredPeopleWhoOwe=people.filter(p=>p.incoming);
  const filteredPeopleYouOwe=people.filter(p=>!p.incoming);
  const history=active.flatMap(g=>g.payments.filter(p=>p.from_user_id===currentUserId||p.to_user_id===currentUserId).map(p=>({...p,person:name(g,p.from_user_id===currentUserId?p.to_user_id:p.from_user_id),group:g.name,direction:p.from_user_id===currentUserId?"Sent":"Received",date:new Date(p.confirmed_at??p.created_at).toLocaleDateString(),amountValue:units(p.amount)/scale})));
  const settledVolume=history.filter(p=>p.status==="confirmed").reduce((n,p)=>n+units(p.amount),0)/scale;
  const settlementHistory=history.filter(p=>`${p.person} ${p.group}`.toLowerCase().includes(search.trim().toLowerCase())).sort((a,b)=>b.created_at.localeCompare(a.created_at));
  // Reconstruct end-of-day net positions from recorded ledger events, not expense dates.
  const [today] = useState(() => new Date());
  const filteredHistory = (()=>{
    const selected=groups.filter(g=>(selectedGroup==="All Groups"||String(g.id)===selectedGroup)&&g.currency===currency);
    const days=period==="7 Days"?7:period==="30 Days"?30:90;
    const divisor=10**currencyDigits(currency);
    const events=selected.map(g=>[
      ...g.expenses.map(e=>({at:Date.parse(e.created_at),delta:(e.paid_by===currentUserId?parseMinor(e.amount,currency):0)-parseMinor(e.splits.find(s=>s.user_id===currentUserId)?.amount_owed??"0",currency)})),
      ...g.payments.filter(p=>p.status==="confirmed"&&p.confirmed_at).map(p=>({at:Date.parse(p.confirmed_at!),delta:(p.from_user_id===currentUserId?1:p.to_user_id===currentUserId?-1:0)*parseMinor(p.amount,currency)}))
    ]);
    return Array.from({length:days},(_,i)=>{const day=new Date(today);day.setDate(day.getDate()-days+1+i);day.setHours(23,59,59,999);const balances=events.map(es=>es.reduce((n,e)=>n+(e.at<=day.getTime()?e.delta:0),0));return {date:day.toLocaleDateString("en-CA"),owed:balances.reduce((n,b)=>n+Math.max(0,b),0)/divisor,owe:balances.reduce((n,b)=>n+Math.max(0,-b),0)/divisor};});
  })();
  async function record(person: typeof people[number]) {
    if (!window.confirm(`Record an external payment of ${money(person.amount)} to ${person.name}? No money is transferred.`) || !submission.beginSubmission()) return;
    setActionError("");
    const endpoint=`/groups/${person.groupId}/payments`;
    const payload={to_user_id:person.userId,amount:minorToDecimal(Math.round(person.amount*scale),currency)};
    try {await request<PaymentResponse>(endpoint,idempotentPost(payload,tracker.keyFor(endpoint,payload)));tracker.complete(endpoint,payload);reload();} catch(e){setActionError(e instanceof Error?e.message:"Unable to record payment.");} finally{submission.endSubmission();}
  }
  async function resolve(item: typeof history[number], action: "confirm"|"reject") {
    if(!window.confirm(`${action === "confirm" ? "Confirm receipt of" : "Reject"} this payment?`)||!submission.beginSubmission())return;
    setActionError("");
    try{await request<PaymentResponse>(`/groups/${item.group_id}/payments/${item.id}/${action}`,{method:"POST"});reload();}catch(e){setActionError(e instanceof Error?e.message:"Unable to update payment.");reload();}finally{submission.endSubmission();}
  }
  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] text-[#22352a] dark:bg-[#141715] dark:text-[#f3f5f2]">
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-40 dark:opacity-70">
        <WavyBackground />
      </div>

      <AppHeader
        sidebarOpen={sidebarOpen}
        onMenuClick={() => setSidebarOpen(true)}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search people and groups..."
      />

      <AppSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="relative z-10 mx-auto max-w-[1600px] space-y-6 px-4 py-7 sm:px-8">
        {/* Page heading */}
        <section className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-[#325f3f] dark:text-[#a4d5af] shadow-sm dark:bg-[#232b25]">
              <span className="h-2 w-2 rounded-full bg-[#4a7856]" />
              Financial Workspace
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl">
              Balances &amp; Settlements
            </h1>

            <p className="mt-2 text-sm text-[#748675] dark:text-[#b9cbbd]">
              Understand your shared balances and manage repayments.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedGroup}
              onChange={(event) => setSelectedGroup(event.target.value)}
              className="h-10 rounded-xl border border-[#dce7db] dark:border-[#35483b] bg-white px-4 text-sm text-[#22352a] outline-none dark:bg-[#232b25] dark:text-[#f3f5f2]"
            >
              <option>All Groups</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>{group.name}</option>
              ))}
            </select>

            <select aria-label="Currency" value={currency} onChange={e=>setCurrencyChoice(e.target.value as GroupCurrency)} className="rounded-xl border bg-background px-3 py-2">{currencies.map(c=><option key={c}>{c}</option>)}</select>
            <button type="button" onClick={reloadGroups} disabled={isLoading||submission.isLoading} className="rounded-xl border px-3 py-2">Refresh</button>
            <button
              type="button"
              onClick={() => window.print()}
              className="h-10 rounded-xl border border-[#dce7db] dark:border-[#35483b] bg-white px-4 text-sm font-semibold text-[#22352a] hover:bg-[#eef3ef] dark:bg-[#232b25] dark:text-[#f3f5f2] dark:hover:bg-[#304236]"
            >
              Export Report
            </button>
          </div>
        </section>

        {isLoading && <p role="status">Loading balances...</p>}
        {error && <p role="alert">{error}</p>}
        {actionError && <p role="alert">{actionError}</p>}
        {!isLoading && !error && <>
        <p className="text-sm">Showing {currency} only. No currency conversion. Payments are recorded, not transferred.</p>
        {/* Summary cards */}
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            label="Net Balance"
            value={money(netBalance)}
            subtitle="Your net balance in selected groups."
            accent="text-[#24694d] dark:text-[#6ee7b7]"
          />
          <SummaryCard
            label="You Are Owed"
            value={money(youAreOwed)}
            subtitle="Outstanding reimbursements."
            accent="text-[#315c99] dark:text-[#93c5fd]"
          />
          <SummaryCard
            label="You Owe"
            value={money(youOwe)}
            subtitle="Your outstanding obligations."
            accent="text-[#a33a35] dark:text-[#fda4af]"
          />
          <SummaryCard
            label="Settled Volume"
            value={money(settledVolume)}
            subtitle="Confirmed repayments involving you."
          />
        </section>

        {/* Financial insights */}
        <section className="rounded-2xl border border-[#e2e8df] dark:border-[#35483b] bg-white/95 dark:bg-[#1b201d] p-5 shadow-sm sm:p-6">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-extrabold tracking-tight">
                Financial Insights &amp; Analytics
              </h2>
              <p className="mt-1 text-sm text-[#748675] dark:text-[#b9cbbd]">
                Balance trends and distribution across your groups.
              </p>
            </div>

            <div className="flex rounded-xl bg-[#eef3ef] dark:bg-[#232b25] p-1">
              {(["7 Days", "30 Days", "90 Days"] as Period[]).map(
                (option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setPeriod(option)}
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                      period === option
                        ? "bg-white text-[#325f3f] dark:text-[#a4d5af] shadow-sm dark:bg-[#35483b]"
                        : "text-[#748675] hover:text-[#325f3f] dark:text-[#b9cbbd] dark:hover:text-[#f3f5f2]"
                    }`}
                  >
                    {option}
                  </button>
                )
              )}
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            {/* Area chart */}
            <div className="min-w-0 rounded-2xl border border-[#e8e6e1] dark:border-[#35483b] p-4">
              <h3 className="font-bold">Balance Trajectory</h3>
              <p className="mt-1 text-xs text-[#819084] dark:text-[#b9cbbd]">
                End-of-day balances reconstructed from recorded ledger events.
              </p>

              <div className="mt-5 h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={filteredHistory}>
                    <defs>
                      <linearGradient id="owedGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#4a7856" stopOpacity={0.25} />
                        <stop offset="100%" stopColor="#4a7856" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={isDark ? "#35483b" : "#e8e6e1"} strokeDasharray="3 3" />
                    <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: isDark ? "#b9cbbd" : "#748675" }}
                        tickFormatter={(value: string) =>
                            value
                        }
                        />
                    <YAxis tick={{ fontSize: 11, fill: isDark ? "#b9cbbd" : "#748675" }} />
                    <Tooltip contentStyle={{ backgroundColor: isDark ? "#232b25" : "#ffffff", borderColor: isDark ? "#35483b" : "#e2e8df", color: isDark ? "#f3f5f2" : "#22352a", borderRadius: 12 }} labelStyle={{ color: isDark ? "#f3f5f2" : "#22352a" }} itemStyle={{ color: isDark ? "#d0ead6" : "#325f3f" }} formatter={(value) => money(Number(value ?? 0))} />
                    <Legend wrapperStyle={{ color: isDark ? "#b9cbbd" : "#748675" }} />
                    <Area
                      name="You Are Owed"
                      type="monotone"
                      dataKey="owed"
                      stroke={isDark ? "#8dc99c" : "#4a7856"}
                      strokeWidth={3}
                      fill="url(#owedGradient)"
                    />
                    <Area
                      name="You Owe"
                      type="monotone"
                      dataKey="owe"
                      stroke={isDark ? "#fda4af" : "#d97957"}
                      strokeWidth={2}
                      fill="transparent"
                      strokeDasharray="5 4"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Group chart */}
            <div className="min-w-0 rounded-2xl border border-[#e8e6e1] dark:border-[#35483b] p-4">
              <h3 className="font-bold">Balances by Group</h3>
              <p className="mt-1 text-xs text-[#819084] dark:text-[#b9cbbd]">
                Share of outstanding balances by magnitude.
              </p>

              <div className="mt-5 grid items-center gap-3 md:grid-cols-2">
                <div className="h-[260px] min-w-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={groupChartData}
                        dataKey="chartAmount"
                        nameKey="name"
                        innerRadius={65}
                        outerRadius={95}
                        paddingAngle={3}
                        >
                            {groupChartData.map((group) => (
                            <Cell key={group.id} fill={group.color} />
                         ))}
                        </Pie>
                      <Tooltip contentStyle={{ backgroundColor: isDark ? "#232b25" : "#ffffff", borderColor: isDark ? "#35483b" : "#e2e8df", color: isDark ? "#f3f5f2" : "#22352a", borderRadius: 12 }} labelStyle={{ color: isDark ? "#f3f5f2" : "#22352a" }} itemStyle={{ color: isDark ? "#d0ead6" : "#325f3f" }} formatter={(value, _name, item) => { const originalAmount = item?.payload?.amount;

                        return [
                                        money(
                                            typeof originalAmount === "number"
                                            ? originalAmount
                                            : Number(value ?? 0)
                                        ),
                                        "Net balance",
                                        ];
                                    }}
                                    />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-4">
                  {groupBalances.map((group) => (
                    <div
                      key={group.id}
                      className="flex items-center justify-between gap-3 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2.5 w-2.5 rounded-sm"
                          style={{ backgroundColor: group.color }}
                        />
                        <span className="font-semibold">{group.name}</span>
                      </div>

                      <span
                        className={`font-bold tabular-nums ${
                          group.amount < 0
                            ? "text-[#a33a35] dark:text-[#fda4af]"
                            : "text-[#325f3f] dark:text-[#a4d5af]"
                        }`}
                      >
                        {group.amount > 0 ? "+" : ""}
                        {money(group.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* People balances */}
        <section className="grid gap-5 xl:grid-cols-2">
        <div className="rounded-2xl border border-[#e2e8df] bg-white/95 p-5 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.015] hover:shadow-xl dark:border-[#35483b] dark:bg-[#1b201d] dark:shadow-black/20">
            <h2 className="text-lg font-extrabold">People Who Owe You</h2>
            <p className="mt-1 text-xs text-[#748675] dark:text-[#b9cbbd]">
              Outstanding amounts others owe you.
            </p>

            <div className="mt-5 divide-y divide-[#edf0ea] dark:divide-[#35483b]">
              {filteredPeopleWhoOwe.map((person) => (
                <div
                  key={person.key}
                  className="flex flex-wrap items-center justify-between gap-3 py-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#e7f0e6] dark:bg-[#304236] text-xs font-bold text-[#456d50] dark:text-[#c4e4ca]">
                      {person.initials}
                    </span>
                    <div>
                      <p className="text-sm font-bold">{person.name}</p>
                      <p className="text-xs text-[#819084] dark:text-[#b9cbbd]">
                        {person.group} · Suggested settlement
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-extrabold text-[#24694d] dark:text-[#6ee7b7] tabular-nums">
                      +{money(person.amount)}
                    </p>
                    <button
                      type="button"
                      onClick={() => navigate("/payment-requests/new")}
                      className="mt-1 text-xs font-semibold text-[#4a7856] dark:text-[#a4d5af] opacity-60"
                    >
                      Request Payment
                    </button>
                  </div>
                </div>
              ))}

              {filteredPeopleWhoOwe.length === 0 && (
                <p className="py-6 text-sm text-[#748675] dark:text-[#b9cbbd]">
                  No matching balances found.
                </p>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-[#e2e8df] dark:border-[#35483b] bg-white/95 dark:bg-[#1b201d] p-5 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.015] hover:shadow-xl">
            <h2 className="text-lg font-extrabold">People You Owe</h2>
            <p className="mt-1 text-xs text-[#748675] dark:text-[#b9cbbd]">
              Outstanding amounts you need to repay.
            </p>

            <div className="mt-5 divide-y divide-[#edf0ea] dark:divide-[#35483b]">
              {filteredPeopleYouOwe.map((person) => (
                <div
                  key={person.key}
                  className="flex flex-wrap items-center justify-between gap-3 py-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#f9e9e3] dark:bg-[#44302b] text-xs font-bold text-[#a35a45] dark:text-[#fda4af]">
                      {person.initials}
                    </span>
                    <div>
                      <p className="text-sm font-bold">{person.name}</p>
                      <p className="text-xs text-[#819084] dark:text-[#b9cbbd]">
                        {person.group} · Suggested settlement
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <p className="font-extrabold text-[#a33a35] dark:text-[#fda4af] tabular-nums">
                      -{money(person.amount)}
                    </p>
                    <button
                      type="button"
                      disabled={submission.isLoading}
                      onClick={() => void record(person)}
                      className="mt-1 text-xs font-semibold text-[#4a7856] dark:text-[#a4d5af] opacity-60"
                    >
                      Record Settlement
                    </button>
                  </div>
                </div>
              ))}

              {filteredPeopleYouOwe.length === 0 && (
                <p className="py-6 text-sm text-[#748675] dark:text-[#b9cbbd]">
                  No matching balances found.
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Settlement history */}
        <section className="overflow-hidden rounded-2xl border border-[#e2e8df] dark:border-[#35483b] bg-white/95 dark:bg-[#1b201d] shadow-sm">
          <div className="border-b border-[#edf0ea] dark:border-[#35483b] p-5">
            <h2 className="text-lg font-extrabold">Settlement History</h2>
            <p className="mt-1 text-xs text-[#748675] dark:text-[#b9cbbd]">
              Recently recorded repayments.
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead className="bg-[#f7f9f6] dark:bg-[#232b25] text-xs uppercase tracking-wide text-[#748675] dark:text-[#b9cbbd]">
                <tr>
                  <th className="px-5 py-4">Person</th>
                  <th className="px-5 py-4">Group</th>
                  <th className="px-5 py-4">Date</th>
                  <th className="px-5 py-4">Amount</th>
                  <th className="px-5 py-4">Direction</th>
                  <th className="px-5 py-4">Status</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[#edf0ea] dark:divide-[#35483b]">
                {settlementHistory.map((item) => (
                  <tr key={item.id} className="hover:bg-[#f8faf7] dark:hover:bg-[#29372e]">
                    <td className="px-5 py-4 font-semibold">{item.person}</td>
                    <td className="px-5 py-4 text-[#748675] dark:text-[#b9cbbd]">{item.group}</td>
                    <td className="px-5 py-4 text-[#748675] dark:text-[#b9cbbd]">{item.date}</td>
                    <td className="px-5 py-4 font-bold tabular-nums">
                      {money(item.amountValue)}
                    </td>
                    <td className="px-5 py-4">{item.direction}</td>
                    <td className="px-5 py-4">
                      <span className="rounded-full bg-[#e8f5ec] px-3 py-1 text-xs font-semibold text-[#24694d] dark:bg-[#304236] dark:text-[#a4d5af]">
                        {item.status}
                      </span>
                      {item.status === "pending" && item.to_user_id === currentUserId && <div className="mt-2 flex gap-2"><button type="button" disabled={submission.isLoading} onClick={()=>void resolve(item,"confirm")} className="font-semibold text-green-700 dark:text-green-300">Confirm</button><button type="button" disabled={submission.isLoading} onClick={()=>void resolve(item,"reject")} className="font-semibold text-red-700 dark:text-red-300">Reject</button></div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        </>}
      </main>
    </div>
  );
}
