
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";

const LandingPage = lazy(() => import("./pages/LandingPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));
const RegisterPage = lazy(() => import("./pages/RegisterPage"));
const FAQPage = lazy(() => import("./pages/FAQPage"));

const ExpensesPage = lazy(() => import("./pages/ExpensesPage"));
const AddExpensePage = lazy(() => import("./pages/AddExpensePage"));
const GroupsPage = lazy(() => import("./pages/GroupsPage"));
const CreateGroupPage = lazy(() => import("./pages/CreateGroupPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const PaymentRequestsPage = lazy(() => import("./pages/PaymentRequestsPage"));
const CreatePaymentRequestPage = lazy(
  () => import("./pages/CreatePaymentRequestPage")
);
const SettingsPage = lazy(() => import("./pages/SettingsPage"));

function PageLoader() {
  return (
    <div
      role="status"
      className="flex min-h-screen items-center justify-center bg-[#f9f8f6] text-[#4a7856] dark:bg-[#141715] dark:text-[#a1d5ae]"
    >
      <div className="flex flex-col items-center gap-4">
        <div
          aria-hidden="true"
          className="size-10 animate-spin rounded-full border-4 border-current border-r-transparent motion-reduce:animate-none"
        />
        <span className="text-sm font-medium">
          Loading LedgerSplit...
        </span>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/faq" element={<FAQPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/expenses" element={<ExpensesPage />} />
              <Route path="/expenses/add" element={<AddExpensePage />} />
              <Route path="/groups" element={<GroupsPage />} />
              <Route path="/groups/new" element={<CreateGroupPage />} />
              <Route path="/balances" element={<BalancesPage />} />
              <Route
                path="/payment-requests"
                element={<PaymentRequestsPage />}
              />
              <Route
                path="/payment-requests/new"
                element={<CreatePaymentRequestPage />}
              />
              <Route path="/settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </Suspense>
      </AuthProvider>
    </BrowserRouter>
  );
}
