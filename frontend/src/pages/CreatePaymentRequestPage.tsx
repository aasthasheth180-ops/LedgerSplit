import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ShieldCheck, Send } from "lucide-react";
import WavyBackground from "../components/background/WavyBackground";
import { useGroupFinances } from "../hooks/useGroupFinances";
import { useApi } from "../hooks/useApi";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import { parseMinor, minorToDecimal, formatMoney } from "../lib/currency";
import { createIdempotencyTracker, idempotentPost } from "../lib/idempotency";
import type { PaymentRequestCreate, PaymentRequestResponse } from "../lib/payments";
const inputClass =
  "w-full rounded-xl border border-[#e8e6e1] dark:border-[#35483b] bg-[#f7f7f5] dark:bg-[#232b25] px-4 py-3 text-sm text-[#22352a] dark:text-[#f3f5f2] outline-none transition-all focus:border-[#4a7856] focus:ring-2 focus:ring-[#4a7856]/15";

export default function CreatePaymentRequestPage() {
 const navigate=useNavigate();
 const {groups,currentUserId,isLoading,error,reloadGroups,reload}=useGroupFinances();
 const {request}=useApi();
 const submission=useAuthSubmission();
 const [tracker]=useState(()=>createIdempotencyTracker());
 const [groupId,setGroupId]=useState("");
 const [debtorId,setDebtorId]=useState("");
 const [amount,setAmount]=useState("");
 const [dueDate,setDueDate]=useState("");
 const [note,setNote]=useState("");
 const [message,setMessage]=useState("");
 const group=groups.find(g=>String(g.id)===groupId);
 const currency=group?.currency ?? "USD";
 const own=Math.max(0,parseMinor(group?.balances.find(b=>b.user_id===currentUserId)?.net_balance ?? "0",currency));
 const eligible=(group?.members ?? []).filter(m=>m.user_id!==currentUserId && own>0 && parseMinor(group?.balances.find(b=>b.user_id===m.user_id)?.net_balance ?? "0",currency)<0 && !group?.paymentRequests.some(r=>r.requester_id===currentUserId && r.debtor_id===m.user_id && r.status==="pending"));
 const debtor=eligible.find(m=>String(m.user_id)===debtorId);
 const maximum=debtor ? Math.min(own,-parseMinor(group?.balances.find(b=>b.user_id===debtor.user_id)?.net_balance ?? "0",currency)):0;
 let units=0;
 try {units=parseMinor(amount,currency);} catch { /* invalid input */ }
 const valid=!!group && !!debtor && units>0 && units<=maximum && units<=(currency==="JPY"?9999999999:999999999999) && note.trim().length<=255 && !isLoading && !error;
 const money=(n:number)=>formatMoney(minorToDecimal(n,currency),currency);
 async function handleSubmit(event:FormEvent<HTMLFormElement>) {
  event.preventDefault();
  if(!valid || !group || !debtor || !submission.beginSubmission()) return;
  setMessage("");
  const endpoint=`/groups/${group.id}/payment-requests`;
  const payload:PaymentRequestCreate={debtor_id:debtor.user_id,amount:minorToDecimal(units,currency),description:note.trim()||null,due_date:dueDate||null};
  try {const key=tracker.keyFor(endpoint,payload);await request<PaymentRequestResponse>(endpoint,idempotentPost(payload,key));tracker.complete(endpoint,payload);navigate("/payment-requests");}
  catch(e){setMessage(e instanceof Error?e.message:"Unable to create request.");}
  finally{submission.endSubmission();}
 }
 return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] dark:bg-[#141715] px-4 py-8 text-[#22352a] dark:text-[#f3f5f2] sm:px-8">
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-40 dark:opacity-70">
        <WavyBackground />
      </div>

      <main className="relative z-10 mx-auto max-w-[1150px]">
        <Link
          to="/payment-requests"
          className="mb-6 inline-flex items-center gap-2 text-sm font-semibold text-[#4a7856] dark:text-[#a1d5ad] transition-colors hover:text-[#2f5b3b]"
        >
          <ArrowLeft size={18} />
          Back to Payment Requests
        </Link>

        <div className="overflow-hidden rounded-3xl border border-[#e8e6e1] dark:border-[#35483b] bg-white/95 dark:bg-[#1b201d] shadow-xl">
          <div className="border-b border-[#e8e6e1] dark:border-[#35483b] bg-[#f6f8f5] dark:bg-[#232b25] px-6 py-7 sm:px-9">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#e7f2e9] dark:bg-[#304236] px-3 py-1.5 text-xs font-semibold text-[#4a7856] dark:text-[#a1d5ad]">
              <ShieldCheck size={15} />
              LedgerSplit · In-app requests
            </div>

            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              Create New Payment Request
            </h1>
            <p className="mt-2 text-sm text-[#829386] dark:text-[#b9cbbd]">
              Request repayment of an outstanding group balance.
            </p>
          </div>

          {isLoading && <p role="status" className="p-6">Loading groups and balances...</p>}
          {error && <div className="p-6"><p role="alert">{error}</p><button type="button" onClick={()=>{reloadGroups();reload();}}>Retry</button></div>}
          {!isLoading && !error && <form onSubmit={handleSubmit}>
          <div className="grid gap-8 p-6 sm:p-9 lg:grid-cols-12">
          <fieldset disabled={submission.isLoading} className="space-y-5 lg:col-span-7 disabled:opacity-70">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#4a7856] dark:text-[#a1d5ad]">Request Details</h2>
          <label className="block text-sm font-semibold">Target Group<select className={`${inputClass} mt-2`} value={groupId} onChange={e=>{setGroupId(e.target.value);setDebtorId("");setAmount("");setMessage("");}} required><option value="">Select group</option>{groups.map(g=><option key={g.id} value={g.id}>{g.name} · {g.currency}</option>)}</select></label>
          {!groups.length && <p>No groups available. <Link to="/groups/new" className="underline">Create a group</Link>.</p>}
          <label className="block text-sm font-semibold">Recipient Member<select className={`${inputClass} mt-2`} value={debtorId} onChange={e=>{setDebtorId(e.target.value);setAmount("");setMessage("");}} required><option value="">Select member</option>{eligible.map(m=><option key={m.user_id} value={m.user_id}>{m.full_name ?? `User ${m.user_id}`}</option>)}</select></label>
          {group && !eligible.length && <p className="text-sm">No eligible debtors. A positive balance and a member with outstanding debt are required, with no existing pending request for that pair.</p>}
          <div className="grid gap-4 sm:grid-cols-2"><label className="block text-sm font-semibold">Requested Amount ({currency})<input className={`${inputClass} mt-2`} inputMode="decimal" required value={amount} onChange={e=>setAmount(e.target.value)}/></label><label className="block text-sm font-semibold">Due Date (optional)<input type="date" className={`${inputClass} mt-2`} value={dueDate} onChange={e=>setDueDate(e.target.value)}/></label></div>
          <p className="text-sm">Maximum request: {money(maximum)} <button type="button" disabled={!maximum} className="ml-2 underline disabled:opacity-50" onClick={()=>setAmount(minorToDecimal(maximum,currency))}>Use maximum</button></p>
          {amount && !valid && <p className="text-sm text-red-700 dark:text-red-300">Enter a positive amount within the outstanding balance and currency precision.</p>}
          <label className="block text-sm font-semibold">Optional description / reference<textarea className={`${inputClass} mt-2`} rows={3} maxLength={255} value={note} onChange={e=>setNote(e.target.value)}/></label>
          <p className="text-xs">{note.length}/255 characters. Requests apply to group balances, not individual expense shares.</p>
          </fieldset>
          <aside className="space-y-5 lg:col-span-5"><div className="rounded-2xl bg-[#f4f5f3] p-5 dark:bg-[#232b25]"><h2 className="font-bold">Request Preview</h2><p className="mt-3 text-sm">To: {debtor?.full_name ?? (debtor ? `User ${debtor.user_id}` : "Select a member")}</p><p className="mt-2 text-sm">Group: {group?.name ?? "Select a group"}</p><p className="mt-3 text-2xl font-bold">{valid?money(units):"—"}</p><p className="mt-2 text-sm">Due: {dueDate||"Not specified"}</p><p className="mt-2 break-words text-sm">{note}</p></div><div className="rounded-xl bg-[#eaf4ec] p-4 dark:bg-[#263e2e]"><h2 className="font-semibold">Current receivable balance</h2><p className="mt-2 text-xl font-bold">{money(own)}</p><p className="mt-2 text-xs">Creating a request does not change balances. Confirmed repayments reduce the outstanding balance.</p></div><div className="rounded-xl border border-[#e8e6e1] p-4 dark:border-[#35483b]"><h2 className="font-semibold">Delivery</h2><p className="mt-2 text-sm">The request appears in LedgerSplit. No email, SMS, automatic reminder or payment transfer is sent.</p></div></aside>
          </div><div className="flex flex-wrap items-center justify-between gap-4 border-t border-[#e8e6e1] p-6 dark:border-[#35483b]"><Link to="/payment-requests" className="text-sm font-semibold">Cancel</Link><button type="submit" disabled={!valid||submission.isLoading} className="flex items-center gap-2 rounded-xl bg-[#4a7856] px-5 py-3 text-sm font-semibold text-white disabled:opacity-50"><Send size={17}/>{submission.isLoading?"Creating...":"Create Payment Request"}</button></div>{message&&<p role="alert" className="p-6 text-red-700 dark:text-red-300">{message}</p>}</form>}
          </div></main></div>);
}
