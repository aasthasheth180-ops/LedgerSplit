
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useState } from "react";
type AppSidebarProps = {
  open: boolean;
  onClose: () => void;
};

const navigation = [
  { icon: "receipt_long", label: "Expenses", path: "/expenses" },
  {
    icon: "account_balance_wallet",
    label: "Balances & Settlements",
    path: "/balances",
  },
  {
    icon: "outbox",
    label: "Payment Requests",
    path: "/payment-requests",
  },
  { icon: "group", label: "Groups", path: "/groups" },
  { icon: "settings", label: "Settings", path: "/settings" },
];

export default function AppSidebar({
  open,
  onClose,
}: AppSidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, isLoggingOut } = useAuth();
  const [logoutError, setLogoutError] = useState("");

  async function handleLogout() {
    setLogoutError("");

    try {
      await logout();

      onClose();

      navigate("/login", { replace: true });
    } catch (error) {
      setLogoutError(
        error instanceof Error
          ? error.message
          : "Unable to log out. Please try again."
      );
    }
  }

  return (
    <>
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined"
      />

      <aside
        id="app-sidebar"
        aria-label="Main navigation"
        className={`fixed inset-y-0 left-0 z-50 w-64 p-3 transition-transform duration-300 ease-in-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-[#e2e9df] bg-[#fcfcf9]/95 shadow-[0_8px_30px_rgba(43,70,48,0.08)] backdrop-blur-xl transition-colors duration-300 dark:border-[#35483b] dark:bg-[#1b201d]/98 dark:shadow-[0_12px_40px_rgba(0,0,0,0.35)]">

          {/* LedgerSplit logo */}
          <div className="flex items-center gap-3 border-b border-[#e8ede6] px-4 py-5 dark:border-[#35483b]">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-[#4a7856] text-white dark:bg-[#548866]">
              <span className="material-symbols-outlined">
                account_balance_wallet
              </span>
            </span>

            <div className="min-w-0 flex-1">
              <p className="text-base font-bold tracking-tight text-[#23392a] dark:text-[#f3f5f2]">
                LedgerSplit
              </p>
              <p className="text-[10px] text-[#7a8a7d] dark:text-[#aab5ad]">
                Shared expenses, simplified
              </p>
            </div>

            <button
              type="button"
              aria-label="Close navigation"
              onClick={onClose}
              className="rounded-lg p-1 text-[#718273] transition-colors hover:bg-[#f0f5ef] dark:text-[#b9cbbd] dark:hover:bg-[#29372e]"
            >
              <span className="material-symbols-outlined">
                close
              </span>
            </button>
          </div>

          {/* Workspace navigation */}
          <div className="px-3 pt-7">
            <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-[#8b978c] dark:text-[#aab5ad]">
              Workspace
            </p>

            <nav className="space-y-1.5">
              {navigation.map((item) => {
                const active =
                  location.pathname === item.path ||
                  location.pathname.startsWith(item.path + "/");

                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={onClose}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-all duration-200 ${
                      active
                        ? "bg-[#e9f2e9] font-semibold text-[#365940] dark:bg-[#304236] dark:text-[#d4efda]"
                        : "text-[#718273] hover:bg-[#f0f5ef] hover:text-[#365940] dark:text-[#b9cbbd] dark:hover:bg-[#29372e] dark:hover:text-[#f3f5f2]"
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl">
                      {item.icon}
                    </span>

                    <span className="flex-1">{item.label}</span>

                    {active && (
                      <span className="h-5 w-1 rounded-full bg-[#4a7856] dark:bg-[#8dc99c]" />
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Bottom group information and Logout */}
          <div className="mt-auto p-3">

            {/* Logout button */}
            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="flex w-full items-center gap-3 rounded-xl border border-[#e2e9df] bg-white px-4 py-3 text-left text-sm font-semibold text-[#a64c4c] transition-all duration-200 hover:bg-[#fff1f1] disabled:cursor-not-allowed disabled:opacity-50 dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#f0a5a5] dark:hover:bg-[#422b2b]"
            >
              <span className="material-symbols-outlined text-xl">
                logout
              </span>

              <span>
                {isLoggingOut ? "Logging Out..." : "Log Out"}
              </span>
            </button>

            {logoutError && (
              <p role="alert" className="mt-2 text-xs text-red-600">
                {logoutError}
              </p>
            )}


          </div>
        </div>
      </aside>

      {/* Click outside to close */}
      {open && (
        <button
          type="button"
          aria-label="Close navigation overlay"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] dark:bg-black/60"
        />
      )}
    </>
  );
}
