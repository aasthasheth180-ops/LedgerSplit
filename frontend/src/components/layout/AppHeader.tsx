import AccountHeader from "./AccountHeader";

import { Link } from "react-router-dom";

type AppHeaderProps = {
  onMenuClick: () => void;
  sidebarOpen: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
};

export default function AppHeader({
  onMenuClick,
  sidebarOpen,
  search,
  onSearchChange,
  searchPlaceholder = "Search expenses, merchants, groups...",
}: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-[#dfe9dd] bg-white/85 backdrop-blur-xl transition-colors duration-300 dark:border-[#35483b] dark:bg-[#141a16]/95">
      <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-4 py-3 sm:px-8">

        {/* Navigation menu */}
        <button
          type="button"
          aria-label="Open navigation"
          aria-controls="app-sidebar"
          aria-expanded={sidebarOpen}
          onClick={onMenuClick}
          className="rounded-xl px-3 py-2 text-xl text-[#466d50] transition-colors hover:bg-[#eaf2e9] dark:text-[#b9d5c0] dark:hover:bg-[#29372e]"
        >
          ☰
        </button>

        {/* LedgerSplit logo */}
        <Link
          to="/expenses"
          className="flex items-center gap-2 font-bold text-[#263c2d] transition-colors dark:text-[#f3f5f2]"
        >
          <span className="rounded-lg bg-[#4a7856] px-2 py-1 text-sm text-white dark:bg-[#548866]">
            LS
          </span>
          <span>LedgerSplit</span>
        </Link>

        {/* Search */}
        <div className="mx-auto hidden w-full max-w-md md:block">
          <input
            aria-label="Search"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full rounded-full border border-[#dce7db] bg-[#f5f8f4] px-4 py-2 text-sm text-[#22352a] outline-none transition-colors placeholder:text-[#8a9a8d] focus:border-[#4a7856] dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#f3f5f2] dark:placeholder:text-[#aab5ad] dark:focus:border-[#6ca27b]"
          />
        </div>

        <AccountHeader />
      </div>
    </header>
  );
}
