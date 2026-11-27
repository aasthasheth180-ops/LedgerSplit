import {
  Navigate,
  Outlet,
  useLocation,
} from "react-router-dom";

import { useAuth } from "../../context/AuthContext";

export default function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth();

  const location = useLocation();

  if (isInitializing) {
    return (
      <div
        className="flex min-h-screen items-center justify-center"
        role="status"
      >
        <div className="flex flex-col items-center gap-4">
          <div
            className="h-10 w-10 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600"
            aria-hidden="true"
          />

          <p className="text-sm text-gray-500">
            Restoring your session...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    );
  }

  return <Outlet />;
}
