
import { useState } from "react";

const links = [
  { label: "Features", href: "#features" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Interactive Demo", href: "#interactive-demo" },
  { label: "Why LedgerSplit", href: "#story" },
];

export default function LandingNavbar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-[#e8e6e1] bg-[#f9f8f6]/95 backdrop-blur-xl transition-colors duration-300 dark:border-[#39483d] dark:bg-[#17221b]/95">
      <nav
        className="mx-auto flex h-18 max-w-[1320px] items-center justify-between gap-4 px-5 lg:px-10"
        aria-label="Main navigation"
      >
        {/* Logo */}
        <a
          href="/"
          className="flex items-center gap-2.5 text-xl font-bold tracking-tight text-[#1f2421] dark:text-[#edf3ed]"
        >
          <span className="grid size-10 place-items-center rounded-xl bg-[#4a7856] text-sm text-white">
            LS
          </span>
          LedgerSplit
        </a>

        {/* Desktop links */}
        <div className="hidden items-center gap-6 lg:flex">
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm font-medium text-[#656a65] transition-colors hover:text-[#4a7856] dark:text-[#b5c4b8] dark:hover:text-[#a4d6ae]"
            >
              {link.label}
            </a>
          ))}
        </div>

        {/* Account actions */}
        <div className="hidden items-center gap-3 md:flex">
          <a
            href="/login"
            className="rounded-xl px-4 py-2.5 text-sm font-semibold text-[#1f2421] transition-colors hover:bg-[#eef3ef] dark:text-[#edf3ed] dark:hover:bg-[#2c4032]"
          >
            Log In
          </a>

          <a
            href="/register"
            className="rounded-xl bg-[#4a7856] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#365940] dark:bg-[#548866] dark:hover:bg-[#659b76]"
          >
            Get Started Free
          </a>
        </div>

        {/* Mobile menu toggle */}
        <button
          type="button"
          className="rounded-lg border border-[#e8e6e1] px-3 py-2 text-[#1f2421] transition-colors dark:border-[#39483d] dark:text-[#edf3ed] md:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="landing-mobile-menu"
          onClick={() => setOpen((current) => !current)}
        >
          {open ? "✕" : "☰"}
        </button>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div
          id="landing-mobile-menu"
          className="space-y-1 border-t border-[#e8e6e1] bg-[#f9f8f6] p-5 text-[#1f2421] dark:border-[#39483d] dark:bg-[#17221b] dark:text-[#edf3ed] md:hidden"
        >
          {links.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="block rounded-lg px-3 py-2.5 text-sm transition-colors hover:bg-[#eef3ef] dark:hover:bg-[#2c4032]"
            >
              {link.label}
            </a>
          ))}

          <a
            href="/login"
            className="block rounded-lg px-3 py-2.5 text-sm hover:bg-[#eef3ef] dark:hover:bg-[#2c4032]"
          >
            Log In
          </a>

          <a
            href="/register"
            className="block rounded-lg bg-[#4a7856] px-3 py-3 text-center text-sm font-semibold text-white dark:bg-[#548866]"
          >
            Get Started Free
          </a>
        </div>
      )}
    </header>
  );
}
