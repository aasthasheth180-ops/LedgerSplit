
import { useState } from "react";
import { Link } from "react-router-dom";

const faqs = [
  {
    question: "What is LedgerSplit?",
    answer:
      "LedgerSplit helps you organize shared expenses, track who paid, and calculate who owes whom.",
  },
  {
    question: "How do I create a group?",
    answer:
      "After signing in, go to your dashboard and select Create Group. Give your group a name and add members.",
  },
  {
    question: "How are expenses split?",
    answer:
      "You can record an expense and divide its amount among participating members. Equal splitting is our initial approach, with additional split methods planned.",
  },
  {
    question: "Can I edit an expense?",
    answer:
      "Expense editing is planned. Once available, you'll be able to correct expense details while keeping group balances accurate.",
  },
  {
    question: "Does LedgerSplit transfer money?",
    answer:
      "No. LedgerSplit is designed to track shared expenses and balances. It does not currently process payments.",
  },
  {
    question: "I forgot my password. What should I do?",
    answer:
      "Password recovery is not available yet. We're planning a secure reset process.",
  },
  {
    question: "Can I use LedgerSplit on my phone?",
    answer:
      "The website is being designed to work on mobile, tablet, and desktop browsers.",
  },
  {
    question: "Is LedgerSplit free?",
    answer:
      "LedgerSplit is currently being developed as a personal software project. Public availability and pricing have not been announced.",
  },
];

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <main className="min-h-screen bg-[#f9f8f6] px-5 py-8 text-[#1f2421] transition-colors duration-300 dark:bg-[#141715] dark:text-[#f3f5f2] sm:px-10">
      <div className="mx-auto max-w-4xl">
        {/* Header */}
        <header className="flex items-center justify-between gap-4">
          <Link
            to="/"
            className="text-xl font-bold text-[#4a7856] transition-colors dark:text-[#a1d5ae]"
          >
            LedgerSplit
          </Link>

          <Link
            to="/login"
            className="rounded-full border border-[#e8e6e1] px-5 py-2 text-sm font-semibold transition-colors hover:bg-[#eef3ef] dark:border-[#35483b] dark:bg-[#232b25] dark:text-[#e4eee6] dark:hover:bg-[#304236]"
          >
            Back to Sign In
          </Link>
        </header>

        {/* Page heading */}
        <section className="pb-10 pt-20 text-center">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#4a7856] dark:text-[#a1d5ae]">
            Help Center
          </p>

          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
            How can we help?
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-7 text-[#656a65] dark:text-[#b9cbbd]">
            Find answers to common questions about using LedgerSplit,
            splitting expenses, and managing groups.
          </p>
        </section>

        {/* FAQ accordion */}
        <section className="space-y-3 pb-20">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;

            return (
              <div
                key={faq.question}
                className={`overflow-hidden rounded-2xl border transition-all duration-300 ${
                  isOpen
                    ? "border-[#cbdccd] bg-white/95 shadow-sm dark:border-[#48634f] dark:bg-[#232b25]"
                    : "border-[#e8e6e1] bg-white/85 dark:border-[#35483b] dark:bg-[#1b201d]"
                }`}
              >
                <button
                  type="button"
                  aria-expanded={isOpen}
                  aria-controls={`faq-answer-${index}`}
                  onClick={() =>
                    setOpenIndex(isOpen ? null : index)
                  }
                  className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-[#f3f7f2] dark:text-[#f3f5f2] dark:hover:bg-[#29372e]"
                >
                  <span className="font-semibold">
                    {faq.question}
                  </span>

                  <span
                    aria-hidden="true"
                    className="text-xl font-semibold text-[#4a7856] dark:text-[#a1d5ae]"
                  >
                    {isOpen ? "−" : "+"}
                  </span>
                </button>

                {isOpen && (
                  <div
                    id={`faq-answer-${index}`}
                    className="border-t border-[#e8e6e1] px-6 py-5 text-sm leading-7 text-[#656a65] dark:border-[#35483b] dark:text-[#c1cec4]"
                  >
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </section>

        {/* Footer */}
        <footer className="border-t border-[#e8e6e1] py-6 text-center text-xs text-[#656a65] dark:border-[#35483b] dark:text-[#aab5ad]">
          © 2026 LedgerSplit
        </footer>
      </div>
    </main>
  );
}
