
import "./AuthLayout.css";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import WavyBackground from "../background/WavyBackground";

type AuthLayoutProps = {
  children: ReactNode;
};

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="auth-page relative isolate min-h-screen overflow-hidden bg-[#f9f8f6] font-['Plus_Jakarta_Sans'] text-[#1f2421] transition-colors duration-300 dark:bg-[#141715] dark:text-[#f3f5f2]">

      {/* Animated background */}
      <div
        className="pointer-events-none absolute inset-0 z-0 overflow-hidden"
        aria-hidden="true"
      >
        <WavyBackground />
      </div>

      <div className="auth-page-content relative z-10 mx-auto flex min-h-screen w-full max-w-[1600px] flex-col lg:flex-row">

        {/* LEFT: Illustrated story */}
        <section className="auth-story-panel flex w-full flex-col justify-between border-b border-[#e8e6e1]/70 bg-white/10 px-6 py-8 dark:border-[#35483b] dark:bg-[#1b201d]/40 lg:min-h-screen lg:w-1/2 lg:border-b-0 lg:border-r lg:px-10 lg:py-10">

          {/* Logo */}
          <Link
            to="/"
            className="flex items-center gap-3 self-start"
          >
            <span className="grid size-10 place-items-center rounded-xl bg-[#4a7856] font-bold text-white dark:bg-[#548866]">
              LS
            </span>

            <span className="text-xl font-bold tracking-tight text-[#1f2421] dark:text-[#f3f5f2]">
              LedgerSplit
            </span>
          </Link>

          {/* Illustration and message */}
          <div className="flex w-full flex-1 flex-col items-center justify-center py-10">

            <div className="auth-story-image w-full max-w-[560px]">
              <img
                src="/animations/ledgersplit-friends-story.webp"
                alt="Four friends discovering an easier way to split expenses"
                width={508}
                height={508}
                className="block h-auto w-full rounded-2xl"
              />
            </div>

            <div className="mt-7 w-full max-w-xl text-center">
              <p className="text-xs font-bold uppercase tracking-[0.22em] text-[#4a7856] dark:text-[#a1d5ae]">
                A better way to split
              </p>

              <h2 className="auth-handwriting mt-4">
                <span>From confusion to clarity.</span>
              </h2>

              <p className="auth-handwriting-subtitle mt-3 text-[#656a65] dark:text-[#c1cec4]">
                Less calculating. More memories.
              </p>
            </div>
          </div>

          <p className="text-center text-xs text-[#656a65] dark:text-[#aab5ad]">
            Fair shares. Happy friendships.
          </p>
        </section>

        {/* RIGHT: Login or registration form */}
        <section className="auth-form-panel flex w-full flex-1 flex-col justify-center px-6 py-12 sm:px-12 lg:px-16">

          <div className="mx-auto w-full max-w-[480px] rounded-2xl border border-white/60 bg-white/85 p-6 shadow-[0_16px_60px_-35px_rgba(31,36,33,0.18)] backdrop-blur-md transition-colors duration-300 dark:border-[#35483b] dark:bg-[#1b201d]/95 dark:shadow-[0_16px_60px_-35px_rgba(0,0,0,0.55)] sm:p-8">
            {children}
          </div>

        </section>
      </div>
    </div>
  );
}
