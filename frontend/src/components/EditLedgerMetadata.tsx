import { useState, type FormEvent } from "react";
import { useApi } from "../hooks/useApi";
import { useAuthSubmission } from "../hooks/useAuthSubmission";

type Props = { endpoint: string; description: string | null; date: string | null; category?: string; reference?: string | null; onChanged: () => void };
export default function EditLedgerMetadata(props: Props) {
  const { request } = useApi();
  const { isLoading, beginSubmission, endSubmission } = useAuthSubmission();
  const [open, setOpen] = useState(false);
  const [description, setDescription] = useState("");
  const [date, setDate] = useState("");
  const [category, setCategory] = useState("Other");
  const [reference, setReference] = useState("");
  const [error, setError] = useState("");
  const expense = props.category !== undefined;
  const field = "w-full rounded-lg border border-[#dce5dc] bg-white p-2 dark:bg-[#242e27] dark:border-[#35483b]";
  async function save(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); setError("");
    if (expense && !description.trim()) { setError("Description is required."); return; }
    if (!beginSubmission()) return;
    try {
      const payload = expense ? {description: description.trim(), category, expense_date: date || null, reference: reference.trim() || null} : {description: description.trim() || null, due_date: date || null};
      await request(props.endpoint, {method: "PATCH", body: JSON.stringify(payload)});
      setOpen(false); props.onChanged();
    } catch (err) { setError(err instanceof Error ? err.message : "Unable to save changes."); }
    finally { endSubmission(); }
  }
  return <div className="mt-2"><button type="button" className="font-semibold text-[#325f3f] dark:text-[#a4d5af]" onClick={() => {setDescription(props.description ?? ""); setDate(props.date ?? ""); setCategory(props.category ?? "Other"); setReference(props.reference ?? ""); setError(""); setOpen(true);}}>Edit {expense ? "expense" : "request"}</button>
    {open && <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/40 p-4"><form role="dialog" aria-modal="true" aria-label={expense ? "Edit expense" : "Edit request"} onSubmit={save} className="w-full max-w-md space-y-3 rounded-2xl bg-white p-6 text-foreground shadow-xl dark:bg-[#1b201d]">
      <h2 className="text-lg font-bold">Edit {expense ? "expense" : "payment request"}</h2>
      <fieldset disabled={isLoading} className="space-y-3">
      <label className="block">Description<input className={field} value={description} maxLength={255} required={expense} onChange={e=>setDescription(e.target.value)}/></label>
      {expense && <label className="block">Category<select className={field} value={category} onChange={e=>setCategory(e.target.value)}>{["Groceries","Dining","Home","Utilities","Travel","Rent","Other"].map(c=><option key={c}>{c}</option>)}</select></label>}
      <label className="block">{expense ? "Expense date" : "Due date"}<input className={field} type="date" value={date} onChange={e=>setDate(e.target.value)}/></label>
      {expense && <label className="block">Reference<input className={field} value={reference} maxLength={100} onChange={e=>setReference(e.target.value)}/></label>}
      <p className="text-xs">Amounts and balances remain unchanged.</p>
      {error && <p role="alert" className="text-red-700 dark:text-red-300">{error}</p>}
      <div className="flex gap-3"><button type="submit" className="rounded-lg bg-[#4a7856] px-4 py-2 text-white">{isLoading ? "Saving..." : "Save changes"}</button><button type="button" onClick={()=>setOpen(false)}>Cancel</button></div>
      </fieldset></form></div>}
  </div>;
}
