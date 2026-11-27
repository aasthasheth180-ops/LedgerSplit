
import { useState } from "react";
import { Link } from "react-router-dom";
import WavyBackground from "../components/background/WavyBackground";
import AppSidebar from "../components/layout/AppSidebar";
import AppHeader from "../components/layout/AppHeader";

import { useGroupFinances } from "../hooks/useGroupFinances";
import { parseMinor, minorToDecimal, formatMoney } from "../lib/currency";
import type { GroupCurrency } from "../lib/groups";
import GroupMembers from "../components/groups/GroupMembers";
import { getGroupCategoryLabel } from "../lib/groups";

const initials = (s: string) =>
  s.split(" ").filter(Boolean).map((x) => x[0])
    .slice(0, 2).join("").toUpperCase();

const typeIcon: Record<string, string> = {
  Home: "⌂",
  Trip: "✈",
  Friends: "♨",
  Work: "▣",
  Other: "◈",
};

export default function GroupsPage() {
  const [drawer, setDrawer] = useState(false);
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const { groups, currentUserId, isLoading, error, reloadGroups: reload } = useGroupFinances();
  const visible = groups.filter((g) =>
    `${g.name} ${getGroupCategoryLabel(g)} ${g.members.map(m => m.full_name ?? "").join(" ")}`
      .toLowerCase().includes(search.trim().toLowerCase())
  );
  const members = new Set(groups.flatMap(g => g.members.map(m => m.user_id))).size;

  const totals = new Map<GroupCurrency, number>();
  for (const g of groups) totals.set(g.currency, (totals.get(g.currency) ?? 0) + parseMinor(g.balances.find(b => b.user_id === currentUserId)?.net_balance ?? "0", g.currency));
  return (
    <div
      className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] text-foreground transition-colors dark:bg-[#141715]"
      style={{ fontFamily: '"Plus Jakarta Sans", system-ui, sans-serif' }}
    >
      <div className="pointer-events-none fixed inset-0 z-[-1] opacity-40">
        <WavyBackground />
      </div>

      <AppHeader
        sidebarOpen={drawer}
        onMenuClick={() => setDrawer(true)}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search groups and members..."
      />

      <AppSidebar
        open={drawer}
        onClose={() => setDrawer(false)}
      />

      <main className="relative z-10 mx-auto max-w-[1600px] px-4 pb-20 pt-9 sm:px-7">
        {/* Page badge */}
        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-[#325f3f] shadow-sm dark:border dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#c4e4ca]">
          <span className="h-2 w-2 rounded-full bg-[#4a7856] dark:bg-[#8dc99c]" />
          Group workspace
        </div>

        {/* Heading */}
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight text-[#325f3f] dark:text-[#f3f5f2] sm:text-5xl">
              Your Groups
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-[#717971] dark:text-[#b9cbbd] sm:text-base">
              Manage your shared spaces, trips, and expenses together.
            </p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <Link
              to="/groups/new"
              className="flex h-11 items-center justify-center rounded-xl bg-[#4a7856] px-5 text-sm font-bold text-white shadow-sm transition hover:bg-[#325f3f] dark:bg-[#548866] dark:hover:bg-[#679c77]"
            >
              ＋ Create Group
            </Link>
          </div>
        </div>

        <div className="mt-6 flex items-center justify-between gap-3">
          <span className="text-sm font-semibold text-[#325f3f] dark:text-[#d4efda]">All groups</span>
          <button type="button" onClick={reload} disabled={isLoading} className="rounded-xl bg-[#e3efe5] px-4 py-2 text-sm font-semibold text-[#325f3f] transition hover:bg-[#d1e5d5] dark:bg-[#304236] dark:text-[#d4efda] dark:hover:bg-[#405a47] disabled:opacity-50">Refresh</button>
        </div>
        {isLoading && <p role="status" className="mt-5">Loading groups...</p>}
        {error && <p role="alert" className="mt-5 text-red-700 dark:text-red-300">{error}</p>}
        {!isLoading && !error && <>
        {/* Summary metrics */}
        <section className="mt-7 grid grid-cols-1 gap-4 md:grid-cols-3">
          <Metric
            icon="♧"
            title="Your Groups"
            value={String(groups.length)}
            note="Groups you belong to"
          />
          <Metric
            icon="♙"
            title="Unique Members"
            value={String(members)}
            note="Across your groups"
          />
          <Metric
            icon="▣"
            title="Net Group Balance"
            value={Array.from(totals, ([c,n]) => `${c} ${formatMoney(minorToDecimal(n,c),c)}`).join(" · ") || "—"}
            note="Your net balance, separately by currency"
            accent
          />
        </section>

        {/* Group cards */}
        <section className="mt-6 grid grid-cols-1 gap-5 lg:grid-cols-2">
          {visible.map((g) => (
            <article
              key={g.id}
              className="flex min-h-[270px] flex-col justify-between rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-[#35483b] dark:bg-[#1b201d] dark:shadow-black/20 sm:p-6"
            >
              <div>
                <div className="flex items-start gap-3">
                  <div
                    className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-2xl text-white"
                    style={{ backgroundColor: g.color }}
                  >
                    {typeIcon[g.category] || "◈"}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-lg font-bold text-[#325f3f] dark:text-[#f3f5f2]">
                        {g.name}
                      </h2>
                      <span className="rounded-full bg-[#e3efe5] px-2 py-1 text-[11px] text-[#325f3f] dark:bg-[#304236] dark:text-[#c4d9c8]">
                        {getGroupCategoryLabel(g)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-[#717971] dark:text-[#b9cbbd]">
                      Created {new Date(g.created_at).toLocaleDateString()}
                    </p>
                  </div>

                </div>
                {g.description && <p className="mt-4 text-sm text-[#414941] dark:text-[#d0ddd2]">{g.description}</p>}
                <div className="mt-5 rounded-xl bg-[#eef4ef] p-4 dark:bg-[#232b25]">
                  <p className="text-xs font-bold uppercase tracking-wider text-[#325f3f] dark:text-[#b9cbbd]">Group preferences</p>
                  <p className="mt-2 text-sm text-[#325f3f] dark:text-[#e4eee6]">{g.currency} · {g.default_split} split</p>
                  <p className="mt-2 text-xs text-[#717971] dark:text-[#b9cbbd]">Your balance: {formatMoney(g.balances.find(b => b.user_id === currentUserId)?.net_balance ?? "0", g.currency)}</p>
                </div>
              </div>

              <Link to="/balances" className="mt-3 text-sm font-semibold text-[#4a7856] dark:text-[#a4d5af]">View balances →</Link>
              {/* Members and action */}
              <div className="mt-5 flex items-center justify-between">
                <div className="flex -space-x-2">
                  {g.members.slice(0, 4).map((m, i) => (
                    <span
                      key={m.id}
                      title={m.full_name ?? `User ${m.user_id}`}
                      className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white text-[10px] font-bold text-[#325f3f] dark:border-[#1b201d]"
                      style={{
                        background: [
                          "#c4eccd",
                          "#e4e1e5",
                          "#ffdbcc",
                          "#d9edda",
                        ][i],
                      }}
                    >
                      {initials(m.full_name ?? `User ${m.user_id}`)}
                    </span>
                  ))}

                  {g.members.length > 4 && (
                    <span className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-white bg-[#f0edf1] text-xs dark:border-[#1b201d] dark:bg-[#35483b] dark:text-[#e4eee6]">
                      +{g.members.length - 4}
                    </span>
                  )}
                </div>

                <button
                  type="button"
                  onClick={() => setExpanded(previous => previous === g.id ? null : g.id)}
                  aria-expanded={expanded === g.id}
                  className="rounded-xl bg-[#e3efe5] px-4 py-2 text-sm font-semibold text-[#325f3f] transition hover:bg-[#d1e5d5] dark:bg-[#304236] dark:text-[#d4efda] dark:hover:bg-[#405a47]"
                >
                  {expanded === g.id ? "Hide Members" : "View Members"}
                </button>
              </div>
              {expanded === g.id && (
                <GroupMembers
                  groupId={g.id}
                  members={g.members}
                  isOwner={currentUserId !== null && g.members.some(m => m.user_id === currentUserId && m.role === "owner")}
                  onChanged={reload}
                />
              )}
            </article>
          ))}
        </section>

        {/* Empty state */}
        {visible.length === 0 && (
          <div className="mt-6 rounded-2xl bg-white px-6 py-16 text-center shadow-sm dark:border dark:border-[#35483b] dark:bg-[#1b201d]">
            <div className="text-4xl">♧</div>
            <h2 className="mt-3 text-xl font-bold text-[#325f3f] dark:text-[#f3f5f2]">
              No groups found
            </h2>
            <p className="mt-2 text-sm text-[#717971] dark:text-[#b9cbbd]">
              Try a different search or create your first group.
            </p>
            <Link
              to="/groups/new"
              className="mt-5 inline-flex rounded-xl bg-[#4a7856] px-5 py-3 text-sm font-bold text-white"
            >
              Create Group
            </Link>
          </div>
        )}

        <p className="mt-8 text-xs text-[#717971] dark:text-[#b9cbbd]">
          Showing {visible.length} of {groups.length} groups
        </p>
        </>}
      </main>
    </div>
  );
}

function Metric({
  icon,
  title,
  value,
  note,
  accent = false,
}: {
  icon: string;
  title: string;
  value: string;
  note: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-[#ece9ec] bg-white p-5 shadow-sm transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-[1.015] hover:shadow-xl dark:border-[#35483b] dark:bg-[#1b201d] dark:shadow-black/20">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#c4eccd] text-2xl text-[#325f3f] dark:bg-[#304236] dark:text-[#b5e2bf]">
        {icon}
      </div>

      <p className="mt-4 text-xs font-bold uppercase tracking-wider text-[#4a7856] dark:text-[#b9cbbd]">
        {title}
      </p>

      <p
        className={`mt-1 text-3xl font-extrabold tabular-nums ${
          accent
            ? "text-[#325f3f] dark:text-[#8ed6a3]"
            : "text-[#325f3f] dark:text-[#f3f5f2]"
        }`}
      >
        {value}
      </p>

      <p className="mt-2 text-xs text-[#717971] dark:text-[#b9cbbd]">
        {note}
      </p>
    </div>
  );
}
