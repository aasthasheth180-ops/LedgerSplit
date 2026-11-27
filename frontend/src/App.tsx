
import { BrowserRouter, Routes, Route } from "react-router-dom";

import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/auth/ProtectedRoute";

import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import FAQPage from "./pages/FAQPage";

import ExpensesPage from "./pages/ExpensesPage";
import AddExpensePage from "./pages/AddExpensePage";
import GroupsPage from "./pages/GroupsPage";
import CreateGroupPage from "./pages/CreateGroupPage";
import BalancesPage from "./pages/BalancesPage";
import PaymentRequestsPage from "./pages/PaymentRequestsPage";
import CreatePaymentRequestPage from "./pages/CreatePaymentRequestPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public pages */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/faq" element={<FAQPage />} />

          {/* Protected dashboard pages */}
          <Route element={<ProtectedRoute />}>
          <Route path="/expenses" element={<ExpensesPage />} />

            <Route
              path="/expenses/add"
              element={<AddExpensePage />}
            />

            <Route path="/groups" element={<GroupsPage />} />

            <Route
              path="/groups/new"
              element={<CreateGroupPage />}
            />

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
      </AuthProvider>
    </BrowserRouter>
  );
}
