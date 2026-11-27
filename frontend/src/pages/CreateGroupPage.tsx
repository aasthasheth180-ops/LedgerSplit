import { useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import WavyBackground from "../components/background/WavyBackground";
import { useApi } from "../hooks/useApi";
import {
  createIdempotencyTracker,
  idempotentPost,
} from "../lib/idempotency";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import type { GroupCreateRequest, GroupResponse, GroupCurrency } from "../lib/groups";
type Member = { id: number; email: string };
type GroupType = "Home" | "Trip" | "Friends" | "Work" | "Other";
type SplitMethod = "Equal" | "Exact" | "Percent";
const groupTypes: { name: GroupType; subtitle: string; icon: string }[] = [{ name: "Home", subtitle: "Roommates", icon: "⌂" }, { name: "Trip", subtitle: "Travel & Tour", icon: "✈" }, { name: "Friends", subtitle: "Social Circles", icon: "♨" }, { name: "Work", subtitle: "Projects & Team", icon: "▣" }, { name: "Other", subtitle: "Ad-hoc Split", icon: "◈" }];
const colors = ["#4a7856", "#2b635b", "#38627b", "#834526", "#7a5a22", "#585172"];
const initials = (s: string) => s.split(" ").filter(Boolean).map(x => x[0]).slice(0, 2).join("").toUpperCase() || "?";
export default function CreateGroupPage() {
  const navigate = useNavigate();
  const { request } = useApi();
  const { isLoading, beginSubmission, endSubmission } = useAuthSubmission();
  const [customCategory, setCustomCategory] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [type, setType] = useState<GroupType>("Home");
  const [members, setMembers] = useState<Member[]>([]);
  const [nextId, setNextId] = useState(1);
  const [currency, setCurrency] = useState<GroupCurrency>("USD");
  const [split, setSplit] = useState<SplitMethod>("Equal");
  const [accent, setAccent] = useState(colors[0]);
  const [error, setError] = useState("");
  const [idempotency] = useState(() => createIdempotencyTracker());
  const validMembers = useMemo(() => members.filter(m => m.email.trim()), [members]);
  const updateMember = (id: number, key: "email", value: string) => setMembers(old => old.map(m => m.id === id ? { ...m, [key]: value } : m));
  const addMember = () => { setMembers(old => [...old, { id: nextId, email: "" }]); setNextId(i => i + 1); };
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!beginSubmission()) return;
    setError("");
    try {
      if (!name.trim() || name.trim().length > 100) {
        throw new Error("Enter a group name of 1–100 characters.");
      }
      if (type === "Other" && (!customCategory.trim() || customCategory.trim().length > 50)) {
        throw new Error("Enter a custom category of 1–50 characters.");
      }
      const emails = validMembers.map(m => m.email.trim().toLowerCase());
      if (emails.length > 50 || emails.some(email => !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))) {
        throw new Error("Enter valid email addresses for up to 50 members.");
      }
      if (new Set(emails).size !== emails.length) {
        throw new Error("Member email addresses must be unique.");
      }
      const payload: GroupCreateRequest = {
        name: name.trim(),
        description: description.trim() || null,
        category: type,
        custom_category: type === "Other" ? customCategory.trim() : null,
        currency,
        default_split: split,
        color: accent,
        member_emails: emails,
      };
      const key = idempotency.keyFor("/groups", payload);
      await request<GroupResponse>(
        "/groups",
        idempotentPost(payload, key)
      );
      idempotency.complete("/groups", payload);
      navigate("/groups");
    } catch (error) {
      setError(error instanceof Error ? error.message : "Unable to create group.");
    } finally {
      endSubmission();
    }
  }
    return (
  <div
    className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] text-foreground dark:bg-[#141715]"
    style={{ fontFamily: '"Plus Jakarta Sans", system-ui, sans-serif' }}
  >
    <div className="pointer-events-none fixed inset-0 z-[-1] opacity-40 dark:opacity-70">
      <WavyBackground />
    </div>

<main className="relative z-10 mx-auto w-full max-w-[1280px] px-4 pb-28 pt-7 sm:px-8">

  <div className="mb-6">

    {/* Back to Groups */}
    <Link
      to="/groups"
      className="mb-3 inline-flex items-center gap-2 rounded-xl border border-[#dce7dc] bg-white/80 dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#d4efda] dark:hover:bg-[#304236] px-4 py-2 text-sm font-medium text-[#426d4c] transition-all duration-200 hover:-translate-x-1 hover:bg-[#eaf2e9]"
    >
      <span aria-hidden="true">←</span>
      Back to Groups
    </Link>

    {/* Breadcrumb */}
    <p className="text-xs text-[#748675] dark:text-[#b9cbbd]">
      Groups / Create Group
    </p>

    {/* Page label */}
    <div className="mt-5">
      <span className="rounded-full bg-[#c4eccd] px-3 py-1 text-xs font-semibold text-[#225031] dark:bg-[#304d38] dark:text-[#c4f0cd]">
        ⊕ Group Workspace Setup
      </span>
    </div>

    {/* Heading */}
    <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
      Create New Group
    </h1>

    <p className="mt-2 text-sm text-[#414941] dark:text-[#d0ddd2] sm:text-base">
      Bring everyone together and make shared expenses effortless.
    </p>

  </div>

      <form onSubmit={submit} noValidate><fieldset disabled={isLoading} className="min-w-0"><div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-12"><div className="space-y-5 lg:col-span-8">
        <section className="rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-sm dark:border-[#35483b] dark:bg-[#1b201d] sm:p-6"><SectionHeading icon="▣" title="Group Details" subtitle="Establish the primary identity for this shared ledger" /><div className="mt-5 space-y-4"><div><label htmlFor="group-name" className="mb-2 block text-sm font-semibold">Group Name <span className="text-[#ba1a1a]">*</span></label><input id="group-name" value={name} maxLength={100} onChange={e => setName(e.target.value)} placeholder="e.g., Sunset Loft Roommates" className="w-full rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[#a1d2aa]" /></div><div><div className="mb-2 flex justify-between gap-2"><label htmlFor="group-description" className="text-sm font-semibold">Group Description <span className="font-normal text-[#717971] dark:text-[#b9cbbd]">(optional)</span></label><span className="text-xs text-[#717971] dark:text-[#b9cbbd]">{description.length}/140</span></div><textarea id="group-description" value={description} onChange={e => setDescription(e.target.value)} maxLength={140} rows={2} placeholder="Shared rent, utilities, groceries..." className="w-full resize-none rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[#a1d2aa]" /></div><div><p className="mb-3 text-sm font-semibold">Select Group Type</p><div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-5">{groupTypes.map(g => <button type="button" key={g.name} onClick={() => setType(g.name)} aria-pressed={type === g.name} className={`flex min-h-[110px] flex-col items-center justify-center rounded-xl p-3 text-center transition ${type === g.name ? "bg-[#c4eccd] text-[#225031] ring-2 ring-[#a1d2aa]" : "bg-[#f5f3f6] dark:bg-[#232b25] text-[#414941] dark:text-[#d0ddd2] hover:bg-[#eef3ef] dark:hover:bg-[#304236]"}`}><span className="mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-white text-xl dark:bg-[#35483b] dark:text-[#e4eee6]">{g.icon}</span><span className="text-xs font-bold">{g.name}</span><span className="mt-1 text-[10px]">{g.subtitle}</span><span className="mt-1 text-xs">{type === g.name ? "✓" : " "}</span></button>)}</div>{type === "Other" && <div className="mt-4"><label htmlFor="custom-category" className="mb-2 block text-sm font-semibold">Custom Category</label><input id="custom-category" value={customCategory} maxLength={50} onChange={e => setCustomCategory(e.target.value)} placeholder="e.g., Research" className="w-full rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-[#a1d2aa]" /></div>}</div></div></section>
        <section className="rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-sm dark:border-[#35483b] dark:bg-[#1b201d] sm:p-6"><div className="flex flex-wrap items-start justify-between gap-3"><SectionHeading icon="♧" title="Add Your Members" subtitle="Add existing LedgerSplit users by their registered email addresses." /><span className="rounded-full bg-[#f0edf1] dark:bg-[#304236] px-3 py-1 text-xs font-semibold">{1 + validMembers.length} people</span></div><div className="mt-5 rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] p-4"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#325f3f] text-xs font-bold text-white">YOU</span><div><p className="text-sm font-bold">You <span className="rounded-full bg-[#c4eccd] px-2 py-0.5 text-[10px] text-[#225031]">Creator</span></p><p className="mt-1 text-xs text-[#717971] dark:text-[#b9cbbd]">Owner & Admin · Your account</p></div></div></div><div className="mt-3 space-y-2">{members.map(m => <div key={m.id} className="flex flex-col gap-2 rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] p-3 sm:flex-row sm:items-center"><span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#c4eccd] text-xs font-bold text-[#225031]">{initials(m.email)}</span><input aria-label="Member email" type="email" value={m.email} onChange={e => updateMember(m.id, "email", e.target.value)} placeholder="Email address" className="min-w-0 flex-1 rounded-lg bg-white px-3 py-2 text-sm dark:bg-[#1b201d] dark:text-[#f3f5f2] outline-none focus:ring-2 focus:ring-[#a1d2aa]" /><button type="button" aria-label={`Remove member ${m.email || m.id}`} onClick={() => setMembers(old => old.filter(x => x.id !== m.id))} className="self-end rounded-lg px-3 py-2 text-[#717971] dark:text-[#b9cbbd] hover:bg-[#ffdad6] hover:text-[#93000a] sm:self-auto">✕</button></div>)}</div><button type="button" onClick={addMember} disabled={members.length >= 50 || isLoading} className="mt-3 w-full rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] py-3 text-sm font-semibold text-[#325f3f] dark:text-[#a4d5af] hover:bg-[#eef3ef] dark:hover:bg-[#304236]">＋ Add Another Member</button></section>
        <section className="rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-sm dark:border-[#35483b] dark:bg-[#1b201d] sm:p-6"><SectionHeading icon="☷" title="Group Preferences & Rules" subtitle="Configure default currency, splits, and group appearance" /><div className="mt-5 grid gap-6 sm:grid-cols-2"><div><label htmlFor="currency" className="mb-2 block text-sm font-semibold">Default Group Currency</label><select id="currency" value={currency} onChange={e => setCurrency(e.target.value as GroupCurrency)} className="w-full rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-[#a1d2aa]"><option value="USD">$ USD — US Dollar</option><option value="EUR">€ EUR — Euro</option><option value="GBP">£ GBP — Pound</option><option value="CAD">$ CAD — Canadian Dollar</option><option value="JPY">¥ JPY — Yen</option><option value="INR">₹ INR — Indian Rupee</option></select><p className="mt-2 text-xs text-[#717971] dark:text-[#b9cbbd]">No automatic exchange-rate conversion.</p></div><div><p className="mb-2 text-sm font-semibold">Default Split Calculation</p><div className="flex rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] p-1">{(["Equal", "Exact", "Percent"] as SplitMethod[]).map(s => <button type="button" key={s} onClick={() => setSplit(s)} className={`flex-1 rounded-lg px-2 py-2 text-xs font-semibold ${split === s ? "bg-white text-[#325f3f] dark:text-[#a4d5af] shadow-sm dark:bg-[#35483b] dark:text-[#d4efda]" : "text-[#717971] dark:text-[#b9cbbd]"}`}>{s}</button>)}</div><p className="mt-2 text-xs text-[#717971] dark:text-[#b9cbbd]">Change the split method per expense later.</p></div><div><p className="mb-2 text-sm font-semibold">Group Privacy Level</p><div className="rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] p-4"><p className="text-sm font-bold">♧ Invite-only Workspace</p><p className="mt-2 text-xs leading-5 text-[#717971] dark:text-[#b9cbbd]">Only authorized members can access group expenses.</p></div></div><div><p className="mb-3 text-sm font-semibold">Color Accent Badge</p><div className="flex flex-wrap gap-2">{colors.map(c => <button type="button" key={c} onClick={() => setAccent(c)} aria-label={`Choose accent ${c}`} aria-pressed={accent === c} className={`flex h-9 w-9 items-center justify-center rounded-full text-sm text-white ${accent === c ? "ring-2 ring-[#325f3f] ring-offset-2" : ""}`} style={{ backgroundColor: c }}>{accent === c ? "✓" : ""}</button>)}</div><p className="mt-3 text-xs text-[#717971] dark:text-[#b9cbbd]">Used on your group card.</p></div></div></section>
      </div><div className="space-y-4 lg:sticky lg:top-6 lg:col-span-4"><div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[#325f3f] dark:text-[#a4d5af]"><span>◉ Live Preview</span><span className="font-normal normal-case text-[#717971] dark:text-[#b9cbbd]">Updates as you type</span></div><div className="rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-md dark:border-[#35483b] dark:bg-[#1b201d]"><div className="flex items-start justify-between gap-2"><div className="flex h-12 w-12 items-center justify-center rounded-xl text-2xl text-white" style={{ backgroundColor: accent }}>{groupTypes.find(g => g.name === type)?.icon}</div><span className="rounded-full bg-[#c4eccd] px-2 py-1 text-xs font-semibold text-[#225031]">{type === "Other" ? customCategory.trim() || "Other" : type}</span></div><h2 className="mt-5 break-words text-xl font-extrabold">{name.trim() || "Your New Group"}</h2><p className="mt-2 text-sm leading-5 text-[#717971] dark:text-[#b9cbbd]">{description.trim() || "Your group description will appear here."}</p><div className="mt-5 flex items-center justify-between gap-2"><div className="flex -space-x-2"><span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white dark:border-[#1b201d] bg-[#325f3f] text-[10px] font-bold text-white">YOU</span>{validMembers.slice(0, 3).map(m => <span key={m.id} className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white dark:border-[#1b201d] bg-[#c4eccd] text-[10px] font-bold text-[#225031]">{initials(m.email)}</span>)}{validMembers.length > 3 && <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white dark:border-[#1b201d] bg-[#f0edf1] dark:bg-[#304236] text-xs">+{validMembers.length - 3}</span>}</div><span className="text-xs text-[#717971] dark:text-[#b9cbbd]">{1 + validMembers.length} planned members</span></div><div className="mt-5 rounded-xl bg-[#f5f3f6] dark:bg-[#232b25] p-4"><p className="text-[11px] font-semibold uppercase tracking-wider text-[#717971] dark:text-[#b9cbbd]">Group balance</p><p className="mt-2 text-xl font-extrabold">{currency} 0</p><p className="mt-1 text-xs text-[#717971] dark:text-[#b9cbbd]">No expenses recorded</p></div><div className="mt-4 flex flex-wrap gap-2">{[currency, `${split} splits`, "Invite-only"].map(t => <span key={t} className="rounded-lg bg-[#f0edf1] dark:bg-[#304236] px-2 py-1 text-xs font-semibold">{t}</span>)}</div><p className="mt-5 text-xs text-[#717971] dark:text-[#b9cbbd]">Created by you · Preview</p></div><div className="rounded-xl bg-[#f0edf1] dark:bg-[#304236] p-4 text-sm leading-6 text-[#414941] dark:text-[#d0ddd2]"><strong>Group membership</strong><p className="mt-1 text-xs text-[#717971] dark:text-[#b9cbbd]">Groups are saved to your account. Members must already have a LedgerSplit account. No invitation emails are sent.</p></div></div></div>
      {error && <p role="alert" className="mt-5 rounded-xl border border-[#ffdad6] bg-[#fff1ef] p-4 text-sm text-[#93000a] dark:border-[#75453e] dark:bg-[#432723] dark:text-[#ffc0b5]">{error}</p>}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#ece9ec] bg-white p-4 shadow-sm dark:border-[#35483b] dark:bg-[#1b201d]"><Link to="/groups" className="rounded-xl px-4 py-3 text-sm font-semibold text-[#414941] dark:text-[#d0ddd2] hover:bg-[#f5f3f6] dark:hover:bg-[#304236] dark:bg-[#232b25]">Cancel</Link><div className="flex items-center gap-3"><span className="hidden text-xs text-[#717971] dark:text-[#b9cbbd] sm:block">{name.trim() ? "Ready to create group" : "Group name required"}</span><button type="submit" disabled={isLoading} className="rounded-xl bg-[#4a7856] px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#325f3f] disabled:opacity-60">{isLoading ? "Creating group…" : "Create Group →"}</button></div></div></fieldset></form>
    </main>
  </div>
    );
}
function SectionHeading({ icon, title, subtitle }: { icon: string; title: string; subtitle: string }) { return <div className="flex items-start gap-3"><div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[#c4eccd] text-xl text-[#325f3f] dark:text-[#a4d5af]">{icon}</div><div><h2 className="text-lg font-bold">{title}</h2><p className="mt-1 text-xs leading-5 text-[#717971] dark:text-[#b9cbbd]">{subtitle}</p></div></div>; }
