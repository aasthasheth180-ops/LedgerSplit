import { GoogleLogin } from "@react-oauth/google";
import {
  useEffect,
  useRef,
  useState,
} from "react";

import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../lib/api";
import { withAuthLock } from "../lib/authSession";

type GoogleSignInProps = {
  linkPassword?: string;
  rememberMe: boolean;
  acceptedTerms?: boolean;
  disabled?: boolean;
  beginSubmission: () => boolean;
  endSubmission: () => void;
  onSuccess: () => void;
  onError: (message: string) => void;
};

type GoogleAuthResponse = {
  access_token: string;
  token_type: string;
};

type GoogleChallengeResponse = {
  nonce: string;
  expires_in: number;
};

export default function GoogleSignIn({
  rememberMe,
  linkPassword,
  acceptedTerms = false,
  disabled = false,
  beginSubmission,
  endSubmission,
  onSuccess,
  onError,
}: GoogleSignInProps) {
  const { login } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [nonce, setNonce] = useState<string | null>(null);
  const [challengeError, setChallengeError] = useState("");
  const [challengeVersion, setChallengeVersion] = useState(0);

  const submissionRef = useRef(false);
  const activeNonceRef = useRef<string | null>(null);

  const clientConfigured = Boolean(
    import.meta.env.VITE_GOOGLE_CLIENT_ID
  );

  useEffect(() => {
    if (!clientConfigured || disabled || isLoading) {
      return;
    }

    let cancelled = false;
    let expiryTimer: ReturnType<typeof setTimeout> | undefined;

    async function loadChallenge() {
        activeNonceRef.current = null;
        setNonce(null);
        setChallengeError("");

      try {
        const response = await withAuthLock(async () =>
          apiRequest<GoogleChallengeResponse>(
            "/auth/google/challenge",
            {
              method: "POST",
            }
          )
        );

        if (cancelled) return;

        if (!response.nonce || response.expires_in <= 0) {
          throw new Error("Invalid Google challenge.");
        }

        activeNonceRef.current = response.nonce;
        setNonce(response.nonce);

        expiryTimer = setTimeout(() => {
            activeNonceRef.current = null;
            setNonce(null);
            setChallengeVersion((previous) => previous + 1);
            }, Math.max(1000, (response.expires_in - 15) * 1000));
      } catch (error) {
        if (cancelled) return;

        setChallengeError(
          error instanceof Error
            ? error.message
            : "Unable to prepare Google sign-in."
        );
      }
    }

    void loadChallenge();

    return () => {
      cancelled = true;
      activeNonceRef.current = null;

      if (expiryTimer !== undefined) {
        clearTimeout(expiryTimer);
      }
    };
  }, [
    clientConfigured,
    disabled,
    isLoading,
    challengeVersion,
  ]);

  async function handleCredential(credential?: string) {
    if (
        disabled ||
        submissionRef.current ||
        !nonce ||
        activeNonceRef.current !== nonce
        ) {
        return;
        }

    if (!credential) {
      onError("Google did not return a valid credential.");
      return;
    }
    if (!beginSubmission()) return;
    activeNonceRef.current = null;

    setIsLoading(true);
    setNonce(null);
    onError("");

    try {
      await withAuthLock(async () => {
        const response = await apiRequest<GoogleAuthResponse>(
          "/auth/google",
          {
            method: "POST",
            body: JSON.stringify({
                  credential,
                  remember_me: rememberMe,
                  accepted_terms: acceptedTerms,
                  ...(linkPassword ? { link_password: linkPassword } : {}),
                }),
          }
        );

        if (!response.access_token) {
          throw new Error("Invalid authentication response.");
        }

        login(response.access_token);
      });

      onSuccess();
    } catch (error) {
      onError(
        error instanceof Error
          ? error.message
          : "Google sign-in failed. Please try again."
      );
    } finally {
      submissionRef.current = false;
      setIsLoading(false);
      endSubmission();
    }
  }

  if (!clientConfigured) {
    return (
      <p className="text-sm text-center text-gray-500">
        Google sign-in is currently unavailable.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {challengeError && !disabled && !isLoading ? (
        <div className="space-y-2 text-center">
          <p className="text-sm text-red-600">
            {challengeError}
          </p>

          <button
            type="button"
            onClick={() =>
              setChallengeVersion((previous) => previous + 1)
            }
            className="text-sm underline"
          >
            Retry Google sign-in
          </button>
        </div>
      ) : disabled || isLoading || !nonce ? (
        <button
          type="button"
          disabled
          className="w-full rounded-lg border px-4 py-3 opacity-50 cursor-not-allowed"
        >
          {isLoading
            ? "Signing in with Google..."
            : disabled
              ? "Continue with Google"
              : "Preparing Google sign-in..."}
        </button>
      ) : (
        <div className="flex justify-center">
          <GoogleLogin
            key={nonce}
            nonce={nonce}
            onSuccess={(response) =>
              void handleCredential(response.credential)
            }
            onError={() => {
                    if (
                        submissionRef.current ||
                        !nonce ||
                        activeNonceRef.current !== nonce
                    ) {
                        return;
                    }

                    activeNonceRef.current = null;
                    onError("Google sign-in failed. Please try again.");
                    setNonce(null);
                    setChallengeVersion((previous) => previous + 1);
                    }}
            theme="outline"
            size="large"
            text="continue_with"
            shape="rectangular"
          />
        </div>
      )}
    </div>
  );
}
