import { useState } from 'react'
import { useNavigate } from "react-router-dom";
import WavyBackground from "../components/background/WavyBackground";
import { useGroups } from '../hooks/useGroups';
import { useApi } from '../hooks/useApi';
import { useAuthSubmission } from '../hooks/useAuthSubmission';
import { calculateSplits } from '../lib/splits';
import { parseMinor, minorToDecimal, formatMoney as formatCurrency } from '../lib/currency';
import { createIdempotencyTracker, idempotentPost } from '../lib/idempotency';
import type { ExpenseCreate, ExpenseResponse } from '../lib/expenses';
type SplitMode = 'equal' | 'exact' | 'percentage';
const categories = [
  { name: 'Groceries', icon: 'shopping_cart' },
  { name: 'Dining', icon: 'restaurant' },
  { name: 'Home', icon: 'home' },
  { name: 'Utilities', icon: 'bolt' },
  { name: 'Travel', icon: 'flight' },
  { name: 'Rent', icon: 'apartment' },
  { name: 'Other', icon: 'category' },
]
const segmentColors = ['#365940', '#75A483', '#A8C5A4', '#D5E4CF', '#9AB8B1', '#C9BDA5']
function Icon({ name, className = '' }: { name: string; className?: string }) {
  return <span aria-hidden="true" className={`material-symbols-outlined ${className}`}>{name}</span>
}

export default function AddExpensePage() {
  const navigate = useNavigate();
  const { groups, currentUserId, isLoading: groupsLoading, error: groupsError, reload } = useGroups();
  const { request } = useApi();
  const { isLoading, beginSubmission, endSubmission } = useAuthSubmission();
  const [tracker] = useState(() => createIdempotencyTracker());
  const [error, setError] = useState('');
  const [group, setGroup] = useState('');
  const selectedGroup = groups.find(g => String(g.id) === group);
  const currency = selectedGroup?.currency ?? 'USD';
  const members = (selectedGroup?.members ?? []).map(m => ({id: String(m.user_id), name: m.full_name || `Member ${m.user_id}`, initials: (m.full_name || '?').split(' ').map(x => x[0]).slice(0,2).join('').toUpperCase()}));
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const payerId = String(currentUserId);
  const [participants, setParticipants] = useState<string[]>([]);
  const [mode, setMode] = useState<SplitMode>('equal');
  const [exact, setExact] = useState<Record<string,string>>({});
  const [percentages, setPercentages] = useState<Record<string,string>>({});
  const [category, setCategory] = useState('Other');
  const [date, setDate] = useState(() => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; });
  const [reference, setReference] = useState('');
  const method = mode === 'equal' ? 'Equal' : mode === 'exact' ? 'Exact' : 'Percent';
  let total: number | null = null;
  try { total = parseMinor(amount,currency); } catch { /* invalid input */ }
  const calculation = (() => {
    try { return { splits: calculateSplits(amount,currency,method,participants.map(id => ({userId:Number(id),value:mode === 'exact' ? exact[id] : percentages[id]}))), error: '' }; }
    catch (err) { return { splits: [], error: err instanceof Error ? err.message : 'Invalid allocation' }; }
  })();
  const shares: Record<string,number|null> = Object.fromEntries(participants.map(id => [id,null]));
  calculation.splits.forEach(s => { shares[String(s.user_id)] = parseMinor(String(s.amount_owed),currency); });
  const allocated = Object.values(shares).reduce<number>((sum,v) => sum+(v??0),0);
  const remaining = total === null ? null : total-allocated;
  const valid = Boolean(!groupsLoading && !groupsError && selectedGroup && currentUserId && members.some(m=>m.id===payerId) && participants.every(id=>members.some(m=>m.id===id)) && description.trim() && description.trim().length<=255 && reference.length<=100 && date && !calculation.error);
  const payer = members.find(m=>m.id===payerId) ?? {name:'You',id:payerId,initials:'YOU'};
  const ownShare = shares[payerId] ?? 0;
  const netImpact = (total ?? 0)-ownShare;
  const personalImpact = netImpact;
  const percentageTotal = participants.reduce((sum,id)=>sum+(Number(percentages[id])||0),0);
  const money = (units:number) => formatCurrency(minorToDecimal(units,currency),currency);
  const formatMoney = money;
  const toggleParticipant = (id:string) => setParticipants(current=>current.includes(id)?current.filter(x=>x!==id):[...current,id]);
  function changeGroup(id:string) {
    const g=groups.find(g=>String(g.id)===id);
    setGroup(id); setParticipants(g?.members.map(m=>String(m.user_id))??[]);
    setMode(g?.default_split==='Exact'?'exact':g?.default_split==='Percent'?'percentage':'equal');
    setExact({}); setPercentages({}); setError('');
  }
  async function save() {
    if (!valid || !selectedGroup || total===null || !beginSubmission()) return;
    setError('');
    try {
      const payload: ExpenseCreate = {description:description.trim(),amount:minorToDecimal(total,currency),category:category as ExpenseCreate['category'],expense_date:date,reference:reference.trim()||null,split_method:method,splits:calculation.splits};
      const endpoint=`/groups/${selectedGroup.id}/expenses`;
      await request<ExpenseResponse>(endpoint,idempotentPost(payload,tracker.keyFor(endpoint,payload)));
      tracker.complete(endpoint,payload); navigate('/expenses');
    } catch(err) {setError(err instanceof Error?err.message:'Unable to save expense.');} finally {endSubmission();}
  }
  const field = 'w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground outline-none focus:border-primary focus:ring-2 focus:ring-primary/20'
  const card =
    'rounded-2xl border border-[#e8e6e1] bg-white/95 p-5 dark:border-[#35483b] dark:bg-[#1b201d]/95 dark:text-[#f3f5f2] ' +
    'shadow-[0_4px_20px_rgba(43,70,48,0.05)] ' +
    'transition-[box-shadow,transform] duration-300 ease-out ' +
    'hover:-translate-y-[2px] ' +
    'hover:shadow-[0_12px_32px_rgba(43,70,48,0.10)]'
  return (
    <div>
      <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] text-foreground dark:bg-[#141715]">
        <div className="pointer-events-none fixed inset-0 z-[-1] opacity-40 dark:opacity-70">
          <WavyBackground />
        </div>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" />
        <main className="mx-auto w-full max-w-[1280px] px-4 py-7 sm:px-8">

        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            {/* Back to Expenses */}
            <button
              type="button"
              onClick={() => navigate("/expenses")}
              className="mb-3 inline-flex items-center gap-2 rounded-xl border border-[#dce7dc] bg-white/80 px-4 py-2 text-sm font-medium text-[#426d4c] transition-all duration-200 hover:-translate-x-1 hover:bg-[#eaf2e9] dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#d4efda] dark:hover:bg-[#304236]"
            >
              <span aria-hidden="true">←</span>
              Back to Expenses
            </button>

            <p className="text-xs text-muted-foreground">
              Expenses / Add New Expense
            </p>

            <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
              Add New Expense
            </h1>

            <p className="mt-2 text-sm text-muted-foreground">
              Record a shared expense and divide it among your group.
            </p>
          </div>

          <span className="rounded-full bg-secondary px-3 py-1.5 text-xs font-semibold text-secondary-foreground">
            Single Payer Split
          </span>
        </div>

            <div className="mb-5 rounded-xl border border-primary/20 bg-secondary px-4 py-3 text-sm text-secondary-foreground">{valid ? `✓ Allocations balanced — ${formatMoney(total ?? 0)} assigned. Ready to record.` : "Check your allocations: all shares must equal the expense total."}</div>{groupsLoading && <p role="status">Loading groups…</p>}{groupsError && <p role="alert">{groupsError} <button onClick={reload}>Retry</button></p>}{!groupsLoading && !groupsError && !groups.length && <button onClick={()=>navigate("/groups/new")}>Create a group first</button>}{error && <p role="alert">{error}</p>}<fieldset disabled={isLoading} className="grid min-w-0 items-start gap-6 lg:grid-cols-12">
              <div className="space-y-5 lg:col-span-7">
                <section className={card}><div className="mb-3 flex items-center justify-between"><h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Target Group</h2><span className="text-xs text-muted-foreground">{members.length} members</span></div><label htmlFor="group" className="sr-only">Target group</label><select id="group" className={field} value={group} onChange={e => changeGroup(e.target.value)}><option value="">Select a group</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name} · {g.currency}</option>)}</select></section>
                <section className={card}><h2 className="mb-4 text-xs font-bold uppercase tracking-wider text-muted-foreground">Expense Details</h2><div className="grid gap-4 sm:grid-cols-3"><div className="sm:col-span-2"><label htmlFor="description" className="mb-2 block text-xs font-semibold">Description</label><input id="description" className={field} maxLength={255} value={description} onChange={e => setDescription(e.target.value)} placeholder="What was this expense for?" /></div><div><label htmlFor="amount" className="mb-2 block text-xs font-semibold">Total Amount ({currency})</label><input id="amount" inputMode="decimal" className={`${field} amount text-right font-semibold`} value={amount} onChange={e => setAmount(e.target.value)} placeholder="0.00" />{amount.trim() && (total === null || total <= 0) && <p role="alert" className="mt-2 text-xs text-negative">Enter a valid positive amount for this currency.</p>}</div></div><div className="mt-4"><p className="mb-2 text-xs font-semibold text-muted-foreground">Classification taxonomy</p><div className="flex flex-wrap gap-2">{categories.map(c => <button type="button" key={c.name} onClick={() => setCategory(c.name)} aria-pressed={category === c.name} className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs ${category === c.name ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-muted'}`}><Icon name={c.icon} className="text-base" />{c.name}</button>)}</div></div><div className="mt-4 grid gap-3 sm:grid-cols-2"><div><label htmlFor="expense-date" className="mb-2 block text-xs font-semibold">Expense date</label><input id="expense-date" type="date" className={field} value={date} onChange={e => setDate(e.target.value)} /></div><div><label htmlFor="expense-reference" className="mb-2 block text-xs font-semibold">Receipt / reference note</label><input id="expense-reference" className={field} maxLength={100} value={reference} onChange={e => setReference(e.target.value)} placeholder="Optional receipt or reference" /></div></div></section>
                <section className={card}><div className="mb-4 flex flex-wrap items-center justify-between gap-2"><h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Paid By (Single Payer)</h2><span className="text-xs text-muted-foreground">{payer.name.split(' ')[0]} paid {money(total ?? 0)}</span></div><div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{members.map(m => <button key={m.id} type="button" disabled={m.id !== payerId} className={`flex items-center gap-2 rounded-xl border p-2.5 text-left text-xs ${payerId === m.id ? 'border-primary bg-secondary font-semibold' : 'border-border bg-background'}`}><span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs text-primary">{m.initials}</span><span className="truncate">{m.name.split(' ')[0]}{m.id === payerId ? ' (You)' : ''}</span></button>)}</div></section>
                <section className={card}><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Participating Members & Split Method</h2><div className="flex rounded-lg bg-muted p-1">{(['equal','exact','percentage'] as SplitMode[]).map(m => <button key={m} onClick={() => setMode(m)} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${mode === m ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground'}`}>{m === 'equal' ? 'Split Equally' : m === 'exact' ? 'Exact Amounts' : 'Percentages'}</button>)}</div></div><div className="divide-y divide-border border-t border-border">{members.map(m => <div key={m.id} className="flex items-center justify-between gap-3 py-3"><label className="flex min-w-0 items-center gap-3 text-sm"><input type="checkbox" className="size-4 accent-primary" checked={participants.includes(m.id)} onChange={() => toggleParticipant(m.id)} /><span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-secondary-foreground">{m.initials}</span><span className="truncate font-medium">{m.name}{m.id === payerId && <span className="ml-1 text-xs text-muted-foreground">(You)</span>}</span></label><div className="w-28 shrink-0">{mode === 'equal' ? <div className="rounded-lg bg-muted px-3 py-2 text-right text-sm font-semibold amount">{participants.includes(m.id) ? money(shares[m.id] ?? 0) : '—'}</div> : mode === 'percentage' ? <div className="relative"><input aria-label={`${m.name} percentage`} disabled={!participants.includes(m.id)} inputMode="decimal" className={`${field} py-2 pr-7 text-right disabled:opacity-40`} value={percentages[m.id] ?? ''} onChange={e => setPercentages(current => ({...current, [m.id]: e.target.value}))} /><span className="absolute right-2 top-2.5 text-xs text-muted-foreground">%</span></div> : <input aria-label={`${m.name} share`} disabled={!participants.includes(m.id)} inputMode="decimal" className={`${field} amount py-2 text-right disabled:opacity-40`} value={exact[m.id] ?? ''} onChange={e => setExact(current => ({...current, [m.id]: e.target.value}))} />}</div></div>)}</div><div className={`mt-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-xs ${valid ? 'border-primary/30 bg-secondary' : 'border-border bg-muted'}`}><span className="font-semibold">{valid ? '✓ Allocations balanced. Ready to save.' : 'Adjust shares until they match the total.'}</span><span className="amount">Allocated: {money(allocated)} / {money(total ?? 0)} · {remaining === null ? 'Invalid amount' : `${money(Math.abs(remaining))} ${remaining < 0 ? 'over' : 'remaining'}`}</span></div>{mode === 'percentage' && <p className="mt-2 text-xs text-muted-foreground">Percentage allocated: {percentageTotal.toFixed(2)}% / 100%</p>}{participants.length === 0 && <p className="mt-2 text-xs text-negative">Select at least one participant.</p>}</section>
                <button className="rounded-lg border border-border bg-card px-4 py-2 text-sm font-semibold" onClick={() => {setDescription('');setAmount('');setParticipants(members.map(m => m.id));setExact({});setPercentages({});setReference('');setMode('equal')}}>Clear Form</button>
              </div>
              <div className="lg:sticky lg:top-5 lg:col-span-5"><section className={card}><div className="flex items-center justify-between border-b border-border pb-4"><div><h2 className="font-bold">Expense Summary</h2><p className="mt-1 text-xs text-muted-foreground">How this expense is split</p></div><span className="rounded-full bg-secondary px-2.5 py-1 text-xs font-semibold text-secondary-foreground">{valid ? 'Balanced' : 'Incomplete'}</span></div><div className="my-4 flex items-center justify-between rounded-lg bg-muted p-3"><div><p className="text-sm font-semibold">{payer.name}</p><p className="text-xs text-muted-foreground">Paid upfront</p></div><span className="amount font-bold">{money(total ?? 0)}</span></div><p className="mb-2 text-xs font-bold uppercase tracking-wider text-muted-foreground">Share Breakdown</p><div className="space-y-2">{members.filter(m => participants.includes(m.id)).map(m => <div key={m.id} className="flex justify-between gap-3 rounded-lg bg-muted px-3 py-2 text-xs"><span>{m.name}{m.id === payerId ? ' (payer)' : ''}</span><span className="amount font-semibold">{shares[m.id] === null ? 'Invalid' : money(shares[m.id] ?? 0)}</span></div>)}</div><div className="mt-5 rounded-xl border border-border bg-muted p-3"><div className="mb-2 flex items-center justify-between text-xs font-bold"><span>Math reconciliation</span><span role="status" className={`rounded-full px-2 py-1 text-[11px] font-bold ${valid ? 'bg-primary text-primary-foreground' : 'bg-background text-negative'}`}>{valid ? 'Ready to Post' : 'Needs Attention'}</span></div><div role="img" aria-label="Allocation share distribution" className="mb-2 flex h-3 w-full overflow-hidden rounded-full bg-border">
                  {members.filter(m => participants.includes(m.id)).map((m, index) => {
                    const share = shares[m.id]
                    const width = total !== null && total > 0 && share !== null && share !== undefined ? Math.min(100, Math.max(0, share / total * 100)) : 0
                    return <div key={m.id} title={`${m.name}: ${formatMoney(share ?? 0)}`} style={{ width: `${width}%`, backgroundColor: segmentColors[index % segmentColors.length] }} className="h-full shrink-0 border-r border-card/70 last:border-r-0" />
                  })}
                </div>
                <div className="mb-3 grid grid-cols-2 gap-x-3 gap-y-1.5">
                  {members.filter(m => participants.includes(m.id)).map((m, index) => <div key={m.id} className="flex items-center gap-1.5 text-[11px] text-muted-foreground"><span aria-hidden="true" className="inline-block size-2.5 shrink-0 rounded-sm" style={{ backgroundColor: segmentColors[index % segmentColors.length] }} /><span className="truncate">{m.name.split(' ')[0]}</span><span className="amount ml-auto text-foreground">{shares[m.id] === null ? '—' : formatMoney(shares[m.id] ?? 0)}</span></div>)}
                </div><div className="flex justify-between text-xs"><span>Allocated {formatMoney(allocated)} / {formatMoney(total ?? 0)}</span><span>{remaining === null ? 'Invalid' : `${formatMoney(Math.abs(remaining))} ${remaining < 0 ? 'over' : 'remaining'}`}</span></div></div><div className="mt-4 rounded-xl border border-primary/20 bg-secondary p-4"><p className="text-xs font-semibold text-secondary-foreground">Personal net balance projection</p><p className="mt-2 text-xs text-secondary-foreground">Impact on your balance from this expense (not your overall group balance)</p><p className={`amount mt-2 text-xl font-bold ${personalImpact >= 0 ? 'text-positive' : 'text-negative'}`}>{personalImpact >= 0 ? '+' : '−'}{formatMoney(Math.abs(personalImpact))}</p></div><div className="mt-4 rounded-xl border border-border bg-card p-4"><p className="mb-3 text-xs font-bold uppercase tracking-wider text-muted-foreground">Incoming receivables from this expense</p>{members.filter(m => participants.includes(m.id) && m.id !== payerId).map(m => <div key={m.id} className="flex justify-between gap-3 py-1.5 text-xs"><span>{m.name}</span><span className="amount font-semibold text-positive">+{formatMoney(shares[m.id] ?? 0)}</span></div>)}<div className="mt-2 flex justify-between border-t border-border pt-2 text-xs font-bold"><span>Total owed to {payer.name.split(' ')[0]}</span><span>{formatMoney(netImpact)}</span></div></div><div className="mt-5 rounded-xl border border-primary/20 bg-secondary p-4"><div className="flex justify-between gap-3"><span className="text-sm font-medium text-secondary-foreground">Payer's net impact</span><span className="amount font-bold text-positive">+{money(netImpact)}</span></div><p className="mt-2 text-xs text-secondary-foreground">{payer.name.split(' ')[0]} paid {money(total ?? 0)} and has a share of {money(ownShare)}. Other participants' shares total {money(netImpact)}.</p></div><button disabled={!valid || isLoading} onClick={() => void save()} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground disabled:cursor-not-allowed disabled:opacity-40"><Icon name="check" className="text-lg" />{isLoading ? "Saving…" : `Save & Record Expense (${money(total ?? 0)})`}</button><p className="mt-2 text-center text-xs text-muted-foreground">Expenses are recorded in the group currency. No currency conversion is performed.</p></section></div>
            </fieldset>
          </main>
        </div>
      </div>
  )
}
