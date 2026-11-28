
import { useEffect, useState, useRef } from "react";
import type { FormEvent } from "react";

import { useApi } from "../hooks/useApi";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

import AppHeader from "../components/layout/AppHeader";
import AppSidebar from "../components/layout/AppSidebar";
import WavyBackground from "../components/background/WavyBackground";

type Preferences = {
  preferred_currency: string;
  reminders_enabled: boolean;
};

type Profile = {
  full_name: string;
  email: string;
};

const field =
  "w-full rounded-xl border border-[#dce7db] bg-white p-3 " +
  "dark:bg-[#232b25] dark:border-[#35483b]";

const button =
  "rounded-xl bg-[#4a7856] px-5 py-3 font-semibold text-white " +
  "disabled:opacity-50";

const panel =
  "rounded-2xl border border-[#dce7db] bg-white/95 p-6 " +
  "space-y-4 dark:bg-[#1e2520] dark:border-[#35483b]";

export default function SettingsPage() {
  const { request } = useApi();
  const { logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  const [profile, setProfile] = useState<Profile | null>(null);
  const [prefs, setPrefs] = useState<Preferences | null>(null);

  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const lock = useRef(false);

  useEffect(() => {
    const controller = new AbortController();

    Promise.all([
      request<Profile>("/users/me", {
        signal: controller.signal,
      }),
      request<Preferences>("/users/me/preferences", {
        signal: controller.signal,
      }),
    ])
      .then(([userProfile, preferences]) => {
        if (!controller.signal.aborted) {
          setProfile(userProfile);
          setPrefs(preferences);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setNotice(
            error instanceof Error
              ? error.message
              : "Failed to load settings."
          );
        }
      });

    return () => controller.abort();
  }, [request]);

  async function save(
    event: FormEvent,
    action: () => Promise<void>
  ) {
    event.preventDefault();

    if (lock.current) return;

    lock.current = true;
    setBusy(true);
    setNotice("");

    try {
      await action();
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Request failed"
      );
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  const patch = (body: unknown) => ({
    method: "PATCH",
    body: JSON.stringify(body),
  });

  const changed = (detail: { name?: string; currency?: string }) => {
    window.dispatchEvent(
      new CustomEvent("ledgersplit-profile-updated", { detail })
    );

    setNotice("Changes saved.");
  };

  return (
    <div
      className="
        relative isolate min-h-screen overflow-hidden
        bg-[#f4f8f3] text-[#22352a]
        dark:bg-[#101713] dark:text-[#f3f5f2]
      "
    >
      {/* Animated background */}
      <WavyBackground />

      {/* Navigation */}
      <AppHeader
        onMenuClick={() => setOpen((value) => !value)}
        sidebarOpen={open}
        search={search}
        onSearchChange={setSearch}
      />

      <AppSidebar
        open={open}
        onClose={() => setOpen(false)}
      />

      {/* Main settings content */}
      <main className="relative z-10 mx-auto max-w-4xl space-y-5 p-5 sm:p-8">
        <h1 className="text-3xl font-bold">
          Settings
        </h1>

        {notice && (
          <p
            role="status"
            className="rounded-xl bg-white p-3 dark:bg-[#263229]"
          >
            {notice}
          </p>
        )}

        {/* PROFILE & ACCOUNT */}
        <form
          className={panel}
          onSubmit={(event) =>
            save(event, async () => {
              if (!profile) return;

              const updatedProfile =
                await request<Profile>(
                  "/users/me",
                  patch({
                    full_name: profile.full_name,
                  })
                );

              setProfile(updatedProfile);
              changed({ name: updatedProfile.full_name });
            })
          }
        >
          <h2 className="text-xl font-bold">
            Profile & Account
          </h2>

          <label className="block">
            Full name
            <input
              className={field}
              required
              maxLength={100}
              value={profile?.full_name ?? ""}
              disabled={!profile}
              onChange={(event) =>
                setProfile((previous) =>
                  previous
                    ? {
                        ...previous,
                        full_name: event.target.value,
                      }
                    : previous
                )
              }
            />
          </label>

          <label className="block">
            Email
            <input
              className={field}
              readOnly
              value={profile?.email ?? ""}
            />
          </label>

          <button
            className={button}
            disabled={busy || !profile}
          >
            Save profile
          </button>
        </form>

        {/* PREFERENCES & NOTIFICATIONS */}
        <form
          className={panel}
          onSubmit={(event) =>
            save(event, async () => {
              if (!prefs) return;

              const updatedPreferences =
                await request<Preferences>(
                  "/users/me/preferences",
                  patch(prefs)
                );

              setPrefs(updatedPreferences);
              changed({ currency: updatedPreferences.preferred_currency });
            })
          }
        >
          <h2 className="text-xl font-bold">
            Preferences & Notifications
          </h2>

          <label className="block">
            Preferred currency

            <select
              className={field}
              disabled={!prefs}
              value={prefs?.preferred_currency ?? ""}
              onChange={(event) =>
                setPrefs((previous) =>
                  previous
                    ? {
                        ...previous,
                        preferred_currency:
                          event.target.value,
                      }
                    : previous
                )
              }
            >
              {[
                "USD",
                "EUR",
                "GBP",
                "CAD",
                "JPY",
                "INR",
              ].map((currency) => (
                <option key={currency} value={currency}>
                  {currency}
                </option>
              ))}
            </select>
          </label>

          <p className="text-sm">
            Preference only; existing group balances
            are not converted.
          </p>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              disabled={!prefs}
              checked={prefs?.reminders_enabled ?? false}
              onChange={(event) =>
                setPrefs((previous) =>
                  previous
                    ? {
                        ...previous,
                        reminders_enabled:
                          event.target.checked,
                      }
                    : previous
                )
              }
            />

            In-app reminders every 48 hours
          </label>

          <button
            className={button}
            disabled={busy || !prefs}
          >
            Save preferences
          </button>

          <label className="block">
            Appearance

            <select
              className={field}
              value={theme}
              onChange={(event) =>
                setTheme(
                  event.target.value as typeof theme
                )
              }
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="system">System</option>
            </select>
          </label>
        </form>

        {/* SECURITY */}
        <form
          className={panel}
          onSubmit={(event) =>
            save(event, async () => {
              if (password !== confirm) {
                throw new Error(
                  "Passwords do not match"
                );
              }

              await request(
                "/users/me/change-password",
                {
                  method: "POST",
                  body: JSON.stringify({
                    current_password: current,
                    new_password: password,
                  }),
                }
              );

              setCurrent("");
              setPassword("");
              setConfirm("");

              await logout();
            })
          }
        >
          <h2 className="text-xl font-bold">
            Security
          </h2>

          <p className="text-sm">
            Changing your password signs you out
            of all sessions. Google-only accounts
            manage passwords through Google.
          </p>

          {[
            {
              label: "Current password",
              value: current,
              set: setCurrent,
              min: 1,
            },
            {
              label: "New password",
              value: password,
              set: setPassword,
              min: 12,
            },
            {
              label: "Confirm new password",
              value: confirm,
              set: setConfirm,
              min: 12,
            },
          ].map((inputField) => (
            <label
              key={inputField.label}
              className="block"
            >
              {inputField.label}

              <input
                className={field}
                type="password"
                required
                minLength={inputField.min}
                maxLength={128}
                autoComplete={
                  inputField.min === 1
                    ? "current-password"
                    : "new-password"
                }
                value={inputField.value}
                onChange={(event) =>
                  inputField.set(
                    event.target.value
                  )
                }
              />
            </label>
          ))}

          <button
            className={button}
            disabled={busy}
          >
            Change password
          </button>
        </form>
      </main>
    </div>
  );
}
