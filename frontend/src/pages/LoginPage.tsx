import { useState, type FormEvent } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import { withAuthLock } from "../lib/authSession";
import GoogleSignIn from "../components/GoogleSignIn";
import { apiRequest } from "../lib/api";
import AuthLayout from "../components/auth/AuthLayout";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = location.state?.from;
  const pathname = from?.pathname;

  const redirectTo =
    typeof pathname === "string" &&
    pathname.startsWith("/") &&
    !pathname.startsWith("//") &&
    !pathname.includes("\\")
      ? pathname + (from.search ?? "") + (from.hash ?? "")
      : "/expenses";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loginError, setLoginError] = useState("");

  const [isLinkingGoogle, setIsLinkingGoogle] = useState(false);
  const [linkPassword, setLinkPassword] = useState("");
  const [showLinkPassword, setShowLinkPassword] = useState(false);
  const [googleError, setGoogleError] = useState("");

  const {
    isLoading,
    beginSubmission,
    endSubmission,
  } = useAuthSubmission();

  const inputStyle =
    "w-full rounded-xl border border-[#dce5dc] bg-white/85 px-4 py-3 text-sm text-[#1f2421] placeholder:text-[#849088] outline-none transition focus:border-[#4a7856] focus:ring-2 focus:ring-[#4a7856]/20 dark:border-[#35483b] dark:bg-[#242e27] dark:text-[#edf3ed] dark:placeholder:text-[#9aaba0] dark:focus:border-[#a4d6ae] dark:focus:ring-[#a4d6ae]/20";

  function cancelGoogleLinking() {
    setIsLinkingGoogle(false);
    setLinkPassword("");
    setShowLinkPassword(false);
    setGoogleError("");
  }

  function handleGoogleError(message: string) {
    if (
      message ===
        "An account with this email already exists. Please use your original sign-in method." &&
      !isLinkingGoogle
    ) {
      setIsLinkingGoogle(true);
      setGoogleError("");
      setLoginError("");
      return;
    }

    setLinkPassword("");
    setShowLinkPassword(false);
    setGoogleError(message);
  }

  function handleGoogleSuccess() {
    setLinkPassword("");
    setPassword("");
    setIsLinkingGoogle(false);
    setShowLinkPassword(false);
    setGoogleError("");

    navigate(redirectTo, { replace: true });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!beginSubmission()) return;

    setLoginError("");
    cancelGoogleLinking();

    try {
      await withAuthLock(async () => {
        const data = await apiRequest<{
          access_token: string;
          token_type: string;
        }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({
            email: email,
            password: password,
            remember_me: rememberMe,
          }),
        });

        if (!data.access_token) {
          throw new Error(
            "Login response did not contain an access token."
          );
        }

        login(data.access_token);
      });

      setPassword("");
      navigate(redirectTo, { replace: true });

    } catch (error) {
      setLoginError(
        error instanceof Error
          ? error.message
          : "Something went wrong."
      );
    } finally {
      endSubmission();
    }
  }

  return (
    <AuthLayout>
      <div className="w-full text-[#1f2421] dark:text-[#edf3ed]">

        {/* Assistance link */}
        <div className="mb-8 flex flex-wrap justify-end gap-2 text-xs text-[#656a65] dark:text-[#b5c4b8]">
          <span>Need assistance?</span>

          <Link
            to="/faq"
            className="font-semibold text-[#4a7856] underline-offset-4 hover:underline dark:text-[#a4d6ae]"
          >
            Support & FAQ
          </Link>
        </div>

        {/* Heading */}
        <div className="mb-7">
          <h1 className="text-[28px] font-bold tracking-tight text-[#1f2421] dark:text-[#f3f5f2]">
            Welcome back to LedgerSplit
          </h1>

          <p className="mt-2 text-sm leading-6 text-[#656a65] dark:text-[#b5c4b8]">
            Log in to view your active groups, reconcile balances,
            and settle debts.
          </p>
        </div>

        {/* Sign In / Create Account tabs */}
        <div className="mb-5 grid grid-cols-2 border-b border-[#e8e6e1] dark:border-[#35483b]">
          <div className="border-b-2 border-[#4a7856] pb-3 text-center text-sm font-semibold text-[#1f2421] dark:border-[#a4d6ae] dark:text-[#edf3ed]">
            Sign In
          </div>

          <Link
            to="/register"
            className="pb-3 text-center text-sm text-[#656a65] transition hover:text-[#4a7856] dark:text-[#aab8ad] dark:hover:text-[#a4d6ae]"
          >
            Create Account
          </Link>
        </div>

        {/* Google sign-in and account linking */}
        <div className="space-y-3">

          {isLinkingGoogle && (
            <div className="space-y-3 rounded-xl border border-[#dce5dc] bg-white/60 p-4 dark:border-[#35483b] dark:bg-[#242e27]">

              <h3 className="text-sm font-semibold">
                Connect your Google account
              </h3>

              <p className="text-xs leading-5 text-[#656a65] dark:text-[#b5c4b8]">
                You already have a LedgerSplit account.
                Enter your existing password, then continue
                with the same Google account to securely connect it.
              </p>

              <label
                htmlFor="google-link-password"
                className="block text-xs font-semibold"
              >
                Current LedgerSplit password
              </label>

              <div className="relative">
                <input
                  id="google-link-password"
                  type={showLinkPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={linkPassword}
                  maxLength={128}
                  disabled={isLoading}
                  onChange={(event) => {
                    setLinkPassword(event.target.value);
                    setGoogleError("");
                  }}
                  placeholder="Enter your existing password"
                  className={`${inputStyle} pr-16`}
                />

                <button
                  type="button"
                  disabled={isLoading}
                  onClick={() =>
                    setShowLinkPassword((current) => !current)
                  }
                  className="absolute inset-y-0 right-4 text-xs font-semibold text-[#4a7856] dark:text-[#a4d6ae]"
                  aria-label={
                    showLinkPassword
                      ? "Hide account linking password"
                      : "Show account linking password"
                  }
                >
                  {showLinkPassword ? "Hide" : "Show"}
                </button>
              </div>

              <p className="text-xs leading-5 text-[#656a65] dark:text-[#b5c4b8]">
                Your existing groups, expenses and balances
                will remain unchanged.
              </p>

              <button
                type="button"
                disabled={isLoading}
                onClick={cancelGoogleLinking}
                className="text-xs font-semibold text-[#4a7856] underline underline-offset-4 dark:text-[#a4d6ae]"
              >
                Cancel account linking
              </button>

            </div>
          )}

          <GoogleSignIn
            key={isLinkingGoogle ? "link" : "login"}
            rememberMe={rememberMe}
            linkPassword={
              isLinkingGoogle ? linkPassword : undefined
            }
            disabled={
              isLoading ||
              (isLinkingGoogle && !linkPassword)
            }
            beginSubmission={beginSubmission}
            endSubmission={endSubmission}
            onSuccess={handleGoogleSuccess}
            onError={handleGoogleError}
          />

          {/* Google authentication errors */}
          {googleError && (
            <div
              role="alert"
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-[#442c2c] dark:text-[#ffb4b4]"
            >
              {googleError ===
              "Please accept the terms and privacy policy to create an account" ? (
                <>
                  <p>
                    You don't have a LedgerSplit account yet.
                    Please create an account and accept our terms
                    and privacy policy to continue with Google.
                  </p>

                  <Link
                    to="/register"
                    className="mt-2 inline-block font-semibold text-[#4a7856] underline underline-offset-4 dark:text-[#a4d6ae]"
                  >
                    Create your account →
                  </Link>
                </>
              ) : (
                <p>{googleError}</p>
              )}
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="my-7 flex items-center gap-4">
          <div className="h-px flex-1 bg-[#e8e6e1] dark:bg-[#35483b]" />

          <span className="text-[10px] font-medium uppercase tracking-wider text-[#849088] dark:text-[#aab8ad]">
            Or sign in with email
          </span>

          <div className="h-px flex-1 bg-[#e8e6e1] dark:bg-[#35483b]" />
        </div>

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-5">

          <div>
            <label
              htmlFor="login-email"
              className="mb-2 block text-xs font-semibold uppercase tracking-wider"
            >
              Email address
            </label>

            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              disabled={isLoading}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className={inputStyle}
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <label
                htmlFor="login-password"
                className="text-xs font-semibold uppercase tracking-wider"
              >
                Password
              </label>

              <span className="text-xs text-[#4a7856] dark:text-[#a4d6ae]">
                Forgot password?
              </span>
            </div>

            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                disabled={isLoading}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                className={`${inputStyle} pr-16`}
              />

              <button
                type="button"
                onClick={() =>
                  setShowPassword((current) => !current)
                }
                className="absolute inset-y-0 right-4 text-xs font-semibold text-[#4a7856] dark:text-[#a4d6ae]"
                aria-label={
                  showPassword ? "Hide password" : "Show password"
                }
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {/* Remember me */}
          <label className="flex cursor-pointer items-center gap-2 text-xs text-[#656a65] dark:text-[#b5c4b8]">
            <input
              type="checkbox"
              checked={rememberMe}
              disabled={isLoading}
              onChange={(event) =>
                setRememberMe(event.target.checked)
              }
              className="accent-[#4a7856]"
            />

            Keep me signed in
          </label>

          {/* Email login errors */}
          {loginError && (
            <div
              role="alert"
              className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-[#442c2c] dark:text-[#ffb4b4]"
            >
              <p>{loginError}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-[#4a7856] px-5 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#365940] disabled:cursor-not-allowed disabled:opacity-60 dark:bg-[#548866] dark:hover:bg-[#659b76]"
          >
            {isLoading
              ? "Signing In..."
              : "Sign In to Dashboard →"}
          </button>

        </form>

        {/* Footer */}
        <div className="mt-10 border-t border-[#e8e6e1] pt-5 text-center text-xs text-[#656a65] dark:border-[#35483b] dark:text-[#b5c4b8]">
          <p>
            New to LedgerSplit?{" "}

            <Link
              to="/register"
              className="font-semibold text-[#4a7856] hover:underline dark:text-[#a4d6ae]"
            >
              Create an account
            </Link>
          </p>

          <p className="mt-4">© 2026 LedgerSplit</p>
        </div>

      </div>
    </AuthLayout>
  );
}