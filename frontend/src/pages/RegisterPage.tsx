
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthLayout from "../components/auth/AuthLayout";
import { apiRequest, ApiError } from "../lib/api";
import { withAuthLock } from "../lib/authSession";
import { useAuthSubmission } from "../hooks/useAuthSubmission";
import GoogleSignIn from "../components/GoogleSignIn";
export default function RegisterPage() {
  const navigate = useNavigate();
  const {
          isLoading,
          beginSubmission,
          endSubmission,
        } = useAuthSubmission();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [error, setError] = useState("");

  const inputStyle =
    "w-full rounded-xl border border-[#dce5dc] bg-white/85 px-4 py-3 text-sm text-[#1f2421] placeholder:text-[#849088] outline-none transition focus:border-[#4a7856] focus:ring-2 focus:ring-[#4a7856]/20 dark:border-[#35483b] dark:bg-[#242e27] dark:text-[#edf3ed] dark:placeholder:text-[#9aaba0] dark:focus:border-[#a4d6ae] dark:focus:ring-[#a4d6ae]/20";


  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!beginSubmission()) return;

    setError("");

    try {
      if (fullName.trim().length < 2) {
        setError("Please enter your full name.");
        return;
      }

      if (password.length < 8) {
        setError("Password must contain at least 8 characters.");
        return;
      }

      if (password !== confirmPassword) {
        setError("Passwords do not match.");
        return;
      }

      if (!acceptedTerms) {
        setError("Please accept the terms before continuing.");
        return;
      }

      await withAuthLock(async () => {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            full_name: fullName.trim(),
            email: email.trim(),
            password,
          }),
        });
      });

      navigate("/login", { replace: true });

    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          setError(
            "An account with this email already exists. Please sign in."
          );
          return;
        }

        if (error.status === 422) {
          setError("Please check your name, email and password.");
          return;
        }
      }

      setError(
        error instanceof Error
          ? error.message
          : "Registration failed. Please try again."
      );

    } finally {
      endSubmission();
    }
}
  return (
    <AuthLayout>
      <div className="w-full text-[#1f2421] dark:text-[#edf3ed]">
        {/* Help link */}
        <div className="mb-6 flex flex-wrap justify-end gap-2 text-xs text-[#656a65] dark:text-[#b5c4b8]">
          <span>Need assistance?</span>
          <Link
            to="/faq"
            className="font-semibold text-[#4a7856] underline-offset-4 hover:underline dark:text-[#a4d6ae]"
          >
            Support & FAQ
          </Link>
        </div>

        {/* Heading */}
        <div className="mb-6">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-[#4a7856] dark:text-[#a4d6ae]">
            Get started with LedgerSplit
          </p>

          <h1 className="text-[28px] font-bold tracking-tight text-[#1f2421] dark:text-[#f3f5f2]">
            Create your account
          </h1>

          <p className="mt-2 text-sm leading-6 text-[#656a65] dark:text-[#b5c4b8]">
            Start organizing shared expenses and keeping
            everyone's balances clear.
          </p>
        </div>

        {/* Navigation tabs */}
        <div className="mb-6 grid grid-cols-2 border-b border-[#e8e6e1] dark:border-[#35483b]">
          <Link
            to="/login"
            className="pb-3 text-center text-sm text-[#656a65] transition hover:text-[#4a7856] dark:text-[#aab8ad] dark:hover:text-[#a4d6ae]"
          >
            Sign In
          </Link>

          <div className="border-b-2 border-[#4a7856] pb-3 text-center text-sm font-semibold text-[#1f2421] dark:border-[#a4d6ae] dark:text-[#edf3ed]">
            Create Account
          </div>
        </div>

        {/* Social authentication placeholders */}
        <div className="space-y-3">
          <div className="space-y-3">
            <GoogleSignIn
                rememberMe={false}
                acceptedTerms={acceptedTerms}
                disabled={isLoading || !acceptedTerms}
                beginSubmission={beginSubmission}
                endSubmission={endSubmission}
                onSuccess={() =>
                  navigate("/expenses", { replace: true })
                }
                onError={setError}
              />

            {!acceptedTerms && (
              <p className="text-center text-xs text-gray-500">
                Please accept the terms and privacy policy below
                to continue with Google.
              </p>
            )}
          </div>
        </div>

        {/* Divider */}
        <div className="my-5 flex items-center gap-4">
          <div className="h-px flex-1 bg-[#e8e6e1] dark:bg-[#35483b]" />
          <span className="text-[10px] font-medium uppercase tracking-wider text-[#849088] dark:text-[#aab8ad]">
            Or register with email
          </span>
          <div className="h-px flex-1 bg-[#e8e6e1] dark:bg-[#35483b]" />
        </div>

        {/* Registration form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="register-name"
              className="mb-1.5 block text-xs font-semibold uppercase tracking-wider"
            >
              Full name
            </label>

            <input
              id="register-name"
              type="text"
              autoComplete="name"
              required
              maxLength={100}
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Enter your full name"
              className={inputStyle}
            />
          </div>

          <div>
            <label
              htmlFor="register-email"
              className="mb-1.5 block text-xs font-semibold uppercase tracking-wider"
            >
              Email address
            </label>

            <input
              id="register-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              className={inputStyle}
            />
          </div>

          <div>
            <label
              htmlFor="register-password"
              className="mb-1.5 block text-xs font-semibold uppercase tracking-wider"
            >
              Password
            </label>

            <div className="relative">
              <input
                id="register-password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                required
                minLength={8}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                className={`${inputStyle} pr-16`}
              />

              <button
                type="button"
                onClick={() => setShowPassword((current) => !current)}
                className="absolute inset-y-0 right-4 text-xs font-semibold text-[#4a7856] dark:text-[#a4d6ae]"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          <div>
            <label
              htmlFor="register-confirm-password"
              className="mb-1.5 block text-xs font-semibold uppercase tracking-wider"
            >
              Confirm password
            </label>

            <input
              id="register-confirm-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Re-enter your password"
              className={inputStyle}
            />
          </div>

          {/* Terms and privacy */}
          <label className="flex items-start gap-2 text-xs leading-5 text-[#656a65] dark:text-[#b5c4b8]">
            <input
              type="checkbox"
              required
              checked={acceptedTerms}
              onChange={(event) =>
                setAcceptedTerms(event.target.checked)
              }
              className="mt-1 accent-[#4a7856]"
            />
            <span>
              I agree to the LedgerSplit terms and privacy policy.
            </span>
          </label>

          {/* Validation feedback */}
          {error && (
            <p
              role="status"
              className="rounded-xl bg-[#eef3ef] px-4 py-3 text-xs leading-5 text-[#365940] dark:bg-[#294832] dark:text-[#d2ead5]"
            >
              {error}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-xl bg-[#4a7856] px-5 py-3.5 text-sm font-bold text-white shadow-sm transition hover:bg-[#365940] disabled:cursor-not-allowed disabled:opacity-60 dark:bg-[#548866] dark:hover:bg-[#659b76]"
          >
            {isLoading ? "Creating Account..." : "Create Account →"}
        </button>
        </form>

        {/* Footer */}
        <div className="mt-6 border-t border-[#e8e6e1] pt-5 text-center text-xs text-[#656a65] dark:border-[#35483b] dark:text-[#b5c4b8]">
          Already have an account?{" "}
          <Link
            to="/login"
            className="font-semibold text-[#4a7856] hover:underline dark:text-[#a4d6ae]"
          >
            Sign In
          </Link>
        </div>
      </div>
    </AuthLayout>
  );
}
