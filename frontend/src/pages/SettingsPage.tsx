
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import type { ReactNode } from "react";
import { useTheme } from "../context/ThemeContext";
import {
  Bell, ChevronRight, CircleUserRound,
  Download, Eye, EyeOff, LockKeyhole, LogOut,
  Save, Settings2, Shield, Trash2, Wallet,
} from "lucide-react";
import AppHeader from "../components/layout/AppHeader";
import AppSidebar from "../components/layout/AppSidebar";
import WavyBackground from "../components/background/WavyBackground";

type Tab = "profile" | "preferences" | "notifications" | "security" | "privacy";

const tabs: { id: Tab; label: string; icon: typeof CircleUserRound }[] = [
  { id: "profile", label: "Profile & Account", icon: CircleUserRound },
  { id: "preferences", label: "Preferences", icon: Settings2 },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: LockKeyhole },
  { id: "privacy", label: "Data & Privacy", icon: Shield },
];

const fieldClass =
  "w-full rounded-xl border border-[#e2e8df] dark:border-[#35483b] bg-[#f8f9f7] dark:bg-[#202922] px-4 py-3 text-sm text-[#22352a] dark:text-[#f3f5f2] outline-none transition focus:border-[#4a7856] focus:ring-2 focus:ring-[#4a7856]/15";

const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-[#4a7856] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#365e41] hover:-translate-y-0.5";

function Panel({ title, description, children }: {
  title: string; description: string; children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-[#e2e8df] dark:border-[#35483b] bg-white/95 dark:bg-[#1e2520] p-5 shadow-sm sm:p-8">
      <h2 className="text-xl font-bold text-[#22352a] dark:text-[#f3f5f2]">{title}</h2>
      <p className="mt-1 text-sm text-[#829487] dark:text-[#aab9ad]">{description}</p>
      <div className="mt-7 space-y-6">{children}</div>
    </section>
  );
}

function Field({ label, children, hint }: {
  label: string; children: ReactNode; hint?: string;
}) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-semibold text-[#34483b] dark:text-[#e3eee5]">{label}</span>
      {children}
      {hint && <span className="block text-xs text-[#829487] dark:text-[#aab9ad]">{hint}</span>}
    </label>
  );
}

function Toggle({ label, description, checked, onChange }: {
  label: string; description?: string; checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4">
      <span>
        <span className="block text-sm font-semibold">{label}</span>
        {description && <span className="mt-1 block text-xs text-[#829487] dark:text-[#aab9ad]">{description}</span>}
      </span>
      <input
        type="checkbox"
        className="h-5 w-5 shrink-0 accent-[#4a7856]"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();
  const { logout, isLoggingOut } = useAuth();
  const { theme, setTheme } = useTheme();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("profile");
  const [notice, setNotice] = useState("");

  const [profile, setProfile] = useState({
    firstName: "Elena",
    lastName: "Rostova",
    email: "elena.rostova@design.co",
    phone: "",
    bio: "",
    venmo: "",
    zelle: "",
  });

  const [currency, setCurrency] = useState("USD");
  const [dateFormat, setDateFormat] = useState("MMM DD, YYYY");
  const [weekStart, setWeekStart] = useState("Monday");
  const [numberFormat, setNumberFormat] = useState("1,234.56");

  const [notificationSettings, setNotificationSettings] = useState({
    requests: { email: true, push: true, sms: false },
    settlements: { email: true, push: true, sms: false },
    groups: { email: true, push: true, sms: false },
    weekly: { email: true, push: false, sms: false },
  });

  const [privacy, setPrivacy] = useState({
    discoverable: true,
    activityVisible: true,
  });

  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState({
    current: "",
    next: "",
    confirm: "",
  });

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");

  function demoSave() {
    setNotice("Demo preview only. These changes have not been saved to your account.");
  }
  async function handleSignOut() {
    setNotice("");

    try {
      await logout();

      navigate("/login", { replace: true });
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Unable to sign out. Please try again."
      );
    }
  }

  const notificationRows = [
    { id: "requests", label: "Payment Requests & Split Inquiries", description: "New requests and split confirmations." },
    { id: "settlements", label: "Settlement Confirmations", description: "Updates when shared balances are settled." },
    { id: "groups", label: "Group Invitations & Activity", description: "Invitations and shared group updates." },
    { id: "weekly", label: "Weekly Summary Digest", description: "A summary of balances and recent activity." },
  ] as const;

  return (
    <div className="relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] dark:bg-[#141715] text-[#22352a] dark:text-[#f3f5f2]">
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-40">
        <WavyBackground />
      </div>

      <AppHeader
        sidebarOpen={sidebarOpen}
        onMenuClick={() => setSidebarOpen(true)}
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Search settings..."
      />
      <AppSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="relative z-10 mx-auto max-w-[1600px] space-y-6 px-4 py-7 sm:px-8">
        <div>
          <span className="inline-flex rounded-full border border-[#e2e8df] dark:border-[#35483b] bg-white dark:bg-[#232b25] px-4 py-1.5 text-xs font-semibold text-[#4a7856] dark:text-[#a1d5ae]">
            ● Personal Account · Demo
          </span>
          <h1 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">Settings</h1>
          <p className="mt-1 text-sm text-[#829487] dark:text-[#aab9ad]">
            Manage your profile, preferences, and account security.
          </p>
        </div>

        {notice && (
          <div role="status" className="flex items-center justify-between gap-3 rounded-xl border border-[#d6e5d8] dark:border-[#48634f] bg-white dark:bg-[#232b25] px-4 py-3 text-sm text-[#4a7856] dark:text-[#a1d5ae]">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice("")} className="font-bold">×</button>
          </div>
        )}

        <div className="grid items-start gap-6 lg:grid-cols-[270px_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-[#e2e8df] dark:border-[#35483b] bg-white/95 dark:bg-[#1e2520] p-3 shadow-sm">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => { setTab(id); setNotice(""); }}
                className={`mb-1 flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm transition ${
                  tab === id
                    ? "bg-[#dcefe0] dark:bg-[#304b37] font-semibold text-[#376747] dark:text-[#b7e3bf]"
                    : "text-[#526457] hover:bg-[#f4f7f3] dark:hover:bg-[#304236]"
                }`}
              >
                <Icon size={18} />
                <span className="flex-1">{label}</span>
                <ChevronRight size={16} />
              </button>
            ))}
            <div className="mt-5 rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4">
              <p className="text-xs font-semibold text-[#829487] dark:text-[#aab9ad]">ACTIVE CIRCLE · DEMO</p>
              <p className="mt-2 text-sm font-bold">Sunset Loft Household</p>
              <p className="mt-1 text-xs text-[#829487] dark:text-[#aab9ad]">Sample shared group</p>
              <p className="mt-3 text-sm font-semibold text-[#4a7856] dark:text-[#a1d5ae]">+$1,420.50</p>
            </div>
          </aside>

          <div className="min-w-0 space-y-6">
            {tab === "profile" && (
              <Panel title="Profile & Account" description="Your personal details and preferred payout handles.">
                <div className="flex items-center gap-4">
                  <div className="flex h-20 w-20 items-center justify-center rounded-full bg-[#4a7856] text-2xl font-bold text-white">
                    {`${profile.firstName[0] ?? ""}${profile.lastName[0] ?? ""}`.toUpperCase() || "LS"}
                  </div>
                  <div>
                    <p className="font-semibold">Profile Avatar</p>
                    <p className="text-xs text-[#829487] dark:text-[#aab9ad]">Avatar uploads will be added during backend integration.</p>
                  </div>
                </div>

                <div className="grid gap-5 sm:grid-cols-2">
                  {([
                    ["firstName", "First Name"],
                    ["lastName", "Last Name"],
                    ["email", "Email Address"],
                    ["phone", "Phone Number (Optional)"],
                  ] as const).map(([key, label]) => (
                    <Field key={key} label={label}>
                      <input
                        className={fieldClass}
                        type={key === "email" ? "email" : key === "phone" ? "tel" : "text"}
                        value={profile[key]}
                        onChange={(e) => setProfile({ ...profile, [key]: e.target.value })}
                      />
                    </Field>
                  ))}
                </div>

                <Field label="Default Expense Bio / Settlement Memo">
                  <textarea
                    className={fieldClass}
                    rows={3}
                    value={profile.bio}
                    onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                  />
                </Field>

                <div className="border-t border-[#e2e8df] dark:border-[#35483b] pt-6">
                  <h3 className="mb-4 flex items-center gap-2 text-lg font-bold">
                    <Wallet size={20} className="text-[#4a7856]" /> Default Payout Handles
                  </h3>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Venmo Handle">
                      <input className={fieldClass} value={profile.venmo}
                        onChange={(e) => setProfile({ ...profile, venmo: e.target.value })} />
                    </Field>
                    <Field label="Zelle ID / Payee Tag">
                      <input className={fieldClass} value={profile.zelle}
                        onChange={(e) => setProfile({ ...profile, zelle: e.target.value })} />
                    </Field>
                  </div>
                </div>
                <div className="flex justify-end">
                  <button type="button" className={buttonClass} onClick={demoSave}>
                    <Save size={17} /> Save Changes
                  </button>
                </div>
              </Panel>
            )}

                {tab === "preferences" && (
                <Panel title="Regional & Ledger Preferences" description="Choose your display formats and calendar preferences.">
                    <Field label="Preferred Display Currency">
                    <select className={fieldClass} value={currency} onChange={(e) => setCurrency(e.target.value)}>
                        {["USD", "EUR", "GBP", "CAD", "JPY", "INR"].map((c) => (
                        <option key={c} value={c}>{c}</option>
                        ))}
                    </select>
                    </Field>
                    <p className="rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4 text-xs leading-relaxed text-[#718376] dark:text-[#aab9ad]">
                    Currency selection is a display preference only. No exchange-rate conversion is implemented.
                    </p>
                    <div className="grid gap-5 sm:grid-cols-2">
                    <Field label="Date Format">
                        <select className={fieldClass} value={dateFormat} onChange={(e) => setDateFormat(e.target.value)}>
                        {["MMM DD, YYYY", "DD/MM/YYYY", "YYYY-MM-DD"].map((f) => (
                            <option key={f}>{f}</option>
                        ))}
                        </select>
                    </Field>
                    <Field label="First Day of Week">
                        <select className={fieldClass} value={weekStart} onChange={(e) => setWeekStart(e.target.value)}>
                        <option>Monday</option><option>Sunday</option>
                        </select>
                    </Field>
                    <Field label="Number & Decimal Formatting">
                        <select className={fieldClass} value={numberFormat} onChange={(e) => setNumberFormat(e.target.value)}>
                        <option>1,234.56</option><option>1.234,56</option><option>1 234.56</option>
                        </select>
                    </Field>

                    </div>

                    {/* Appearance Preferences */}
                    <div className="border-t border-[#e2e8df] dark:border-[#35483b] pt-6">
                      <h3 className="mb-2 text-lg font-bold text-[#22352a] dark:text-[#f3f5f2]">
                        Appearance
                      </h3>

                      <p className="mb-5 text-sm text-[#829487] dark:text-[#aab9ad]">
                        Choose how LedgerSplit looks on your device.
                      </p>

                      <div className="grid gap-3 sm:grid-cols-3">
                        {(["light", "dark", "system"] as const).map((option) => (
                          <button
                            key={option}
                            type="button"
                            onClick={() => setTheme(option)}
                            aria-pressed={theme === option}
                            className={`rounded-xl border-2 p-4 text-left transition-all duration-200 hover:-translate-y-1 hover:shadow-lg ${
                              theme === option
                                ? "border-[#4a7856] bg-[#eef3ef] dark:bg-[#304236]"
                                : "border-[#e2e8df] dark:border-[#35483b] bg-white dark:bg-[#232b25]"
                            }`}
                          >
                            <div
                              className={`mb-3 h-16 rounded-lg border ${
                                option === "light"
                                  ? "border-[#e2e8df] dark:border-[#35483b] bg-[#f9f8f6] dark:bg-[#141715]"
                                  : option === "dark"
                                  ? "border-[#35483b] bg-[#141715]"
                                  : "border-[#aab5ad] bg-gradient-to-r from-[#f9f8f6] to-[#141715]"
                              }`}
                            />

                            <p className="text-sm font-semibold capitalize text-[#22352a] dark:text-[#f3f5f2]">
                              {option}
                            </p>

                            <p className="mt-1 text-xs text-[#829487] dark:text-[#aab9ad]">
                              {option === "system"
                                ? "Match device"
                                : `${option === "light" ? "Light" : "Dark"} theme`}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <button
                        type="button"
                        className={buttonClass}
                        onClick={demoSave}
                      >
                        Save Preferences
                      </button>
                    </div>
                </Panel>
                )}







            {tab === "notifications" && (
              <Panel title="Notification Channels" description="Choose how you would like to receive LedgerSplit alerts in the future.">
                <p className="rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4 text-xs text-[#718376] dark:text-[#aab9ad]">
                  Email, push, and SMS delivery are not active. These switches are frontend previews.
                </p>
                <div className="space-y-4">
                  {notificationRows.map(({ id, label, description }) => (
                    <div key={id} className="rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4">
                      <p className="text-sm font-semibold">{label}</p>
                      <p className="mt-1 text-xs text-[#829487] dark:text-[#aab9ad]">{description}</p>
                      <div className="mt-4 grid grid-cols-3 gap-3">
                        {(["email", "push", "sms"] as const).map((channel) => (
                          <label key={channel} className="flex items-center gap-2 text-xs font-semibold capitalize">
                            <input
                              type="checkbox"
                              className="accent-[#4a7856]"
                              checked={notificationSettings[id][channel]}
                              onChange={(e) =>
                                setNotificationSettings({
                                  ...notificationSettings,
                                  [id]: {
                                    ...notificationSettings[id],
                                    [channel]: e.target.checked,
                                  },
                                })
                              }
                            />
                            {channel === "push" ? "In-App" : channel.toUpperCase()}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end">
                  <button type="button" className={buttonClass} onClick={demoSave}>Save Notification Preferences</button>
                </div>
              </Panel>
            )}

            {tab === "security" && (
              <>
                <Panel title="Change Password" description="Password updates will require a secure authenticated backend endpoint.">
                  <div className="max-w-xl space-y-4">
                    {([
                      ["current", "Current Password"],
                      ["next", "New Password"],
                      ["confirm", "Confirm New Password"],
                    ] as const).map(([key, label]) => (
                      <Field key={key} label={label}>
                        <div className="relative">
                          <input
                            type={showPassword ? "text" : "password"}
                            className={fieldClass + " pr-12"}
                            value={password[key]}
                            onChange={(e) => setPassword({ ...password, [key]: e.target.value })}
                          />
                          <button type="button" onClick={() => setShowPassword(!showPassword)}
                            aria-label={showPassword ? "Hide passwords" : "Show passwords"}
                            className="absolute right-4 top-3 text-[#829487] dark:text-[#aab9ad]">
                            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                          </button>
                        </div>
                      </Field>
                    ))}
                    {password.next && (
                      <p className="text-xs text-[#829487] dark:text-[#aab9ad]">
                        {password.next.length >= 12 ? "Length: 12+ characters" : "Use at least 12 characters."}
                        {password.confirm && password.next !== password.confirm ? " Passwords do not match." : ""}
                      </p>
                    )}
                    <button type="button" disabled className={buttonClass + " cursor-not-allowed opacity-50"}>
                      Update Password · Backend Required
                    </button>
                  </div>
                </Panel>
                <Panel title="Current Active Session" description="Session details will be loaded from the authentication backend.">
                  <div className="flex items-center gap-3 rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4">
                    <LockKeyhole className="text-[#4a7856]" size={22} />
                    <div>
                      <p className="text-sm font-semibold">Session information unavailable in demo</p>
                      <p className="text-xs text-[#829487] dark:text-[#aab9ad]">Device, session expiry, and revocation are not connected.</p>
                    </div>
                  </div>
                  <button
                     type="button"
                     onClick={handleSignOut}
                     disabled={isLoggingOut}
                    className="flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-[#422b2b]"
>
                  <LogOut size={16} />

                   {isLoggingOut ? "Signing Out..." : "Sign Out"}
                  </button>
                  </Panel>
              </>
            )}

            {tab === "privacy" && (
              <>
                <Panel title="Data Portability & Export" description="Export your expenses, splits, and settlement records.">
                  <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-[#f6f8f5] dark:bg-[#263229] p-4">
                    <div>
                      <p className="text-sm font-semibold">Export My Expense & Balance Ledger</p>
                      <p className="mt-1 text-xs text-[#829487] dark:text-[#aab9ad]">Available after real records are connected.</p>
                    </div>
                    <div className="flex gap-2">
                      {["CSV", "JSON"].map((format) => (
                        <button key={format} type="button" disabled
                          className="flex items-center gap-2 rounded-lg border bg-white dark:bg-[#232b25] px-4 py-2 text-sm opacity-50">
                          <Download size={15} /> {format}
                        </button>
                      ))}
                    </div>
                  </div>
                </Panel>
                <Panel title="Privacy Controls" description="Choose how your profile and group activity should be visible.">
                  <Toggle
                    label="Search & Discovery Visibility"
                    description="Allow shared group members to find your profile."
                    checked={privacy.discoverable}
                    onChange={(value) => setPrivacy({ ...privacy, discoverable: value })}
                  />
                  <Toggle
                    label="Activity Feed Visibility"
                    description="Show your settlement activity to authorized group members."
                    checked={privacy.activityVisible}
                    onChange={(value) => setPrivacy({ ...privacy, activityVisible: value })}
                  />
                  <div className="flex justify-end">
                    <button type="button" className={buttonClass} onClick={demoSave}>Save Privacy Controls</button>
                  </div>
                </Panel>
                <section className="rounded-2xl border border-red-200 dark:border-red-900/60 bg-red-50 dark:bg-[#311e20] p-6 sm:p-8">
                  <h2 className="flex items-center gap-2 text-lg font-bold text-red-700 dark:text-red-300">
                    <Trash2 size={20} /> Danger Zone: Delete Account
                  </h2>
                  <p className="mt-3 text-sm text-red-700/80 dark:text-red-300/85">
                    Account deletion is irreversible. This operation is disabled until
                    authenticated deletion, unsettled-balance checks, and audit handling are implemented.
                  </p>
                  <button type="button" onClick={() => setDeleteModalOpen(true)}
                    className="mt-5 rounded-xl border border-red-200 dark:border-red-900/60 bg-white dark:bg-[#232b25] px-5 py-3 text-sm font-semibold text-red-700 dark:text-red-300">
                    Request Account Deletion
                  </button>
                </section>
              </>
            )}
          </div>
        </div>
      </main>

      {deleteModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4">
          <div role="dialog" aria-modal="true" aria-labelledby="delete-title"
            className="w-full max-w-md rounded-2xl bg-white dark:bg-[#232b25] p-6 shadow-xl">
            <h2 id="delete-title" className="text-xl font-bold text-red-700 dark:text-red-300">Delete Account</h2>
            <p className="mt-3 text-sm text-[#718376] dark:text-[#aab9ad]">
              This is a demonstration only. No account will be deleted.
            </p>
            <label className="mt-5 block text-sm font-semibold">
              Type DELETE to review this action
              <input className={fieldClass + " mt-2"} value={deleteConfirmation}
                onChange={(e) => setDeleteConfirmation(e.target.value)} />
            </label>
            <div className="mt-5 flex justify-end gap-3">
              <button type="button" onClick={() => { setDeleteModalOpen(false); setDeleteConfirmation(""); }}
                className="rounded-xl border px-4 py-2 text-sm">Cancel</button>
              <button type="button" disabled
                className="rounded-xl bg-red-600 px-4 py-2 text-sm text-white opacity-50">
                Delete · Backend Required
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
