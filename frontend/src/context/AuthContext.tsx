import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useRef,
  type ReactNode,
} from "react";

import { ApiError, apiRequest } from "../lib/api";

import {
  refreshAccessToken,
  withAuthLock,
  getAuthGeneration,
  advanceAuthGeneration,
  assertAuthGeneration,
  subscribeToAuthChanges,
  readSessionId,
} from "../lib/authSession";

type AuthContextType = {
  accessToken: string | null;
  authGeneration: string;
  isAuthenticated: boolean;
  isInitializing: boolean;
  isLoggingOut: boolean;
  login: (token: string) => void;
  logout: () => Promise<void>;
  refreshSession: (
    rejectedToken: string,
    expectedGeneration: string
  ) => Promise<string>;
};

const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);

export function AuthProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [accessToken, setAccessToken] = useState<string | null>(
    null
  );

  const [authGeneration, setAuthGeneration] = useState(
    getAuthGeneration
  );

  const [isInitializing, setIsInitializing] = useState(true);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const tokenRef = useRef<string | null>(null);
  const generationRef = useRef(authGeneration);
  const sessionVersion = useRef(0);
  const logoutPromise = useRef<Promise<void> | null>(null);

  const clearSession = useCallback(() => {
    sessionVersion.current += 1;

    tokenRef.current = null;
    setAccessToken(null);
    setIsInitializing(false);
  }, []);

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      const currentGeneration = getAuthGeneration();

      if (generationRef.current !== currentGeneration) {
        generationRef.current = currentGeneration;
        setAuthGeneration(currentGeneration);

        clearSession();
      }
    });
  }, [clearSession]);

  useEffect(() => {
    let active = true;

    const version = sessionVersion.current;
    const generation = generationRef.current;

    async function restoreSession() {
      try {
        const token = await refreshAccessToken(generation);

        assertAuthGeneration(generation);

        if (
          active &&
          sessionVersion.current === version
        ) {
          tokenRef.current = token;
          setAccessToken(token);
        }
      } catch {
        if (
          active &&
          sessionVersion.current === version
        ) {
          tokenRef.current = null;
          setAccessToken(null);
        }
      } finally {
        if (
          active &&
          sessionVersion.current === version
        ) {
          setIsInitializing(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback((token: string) => {
    const generation = advanceAuthGeneration();

    sessionVersion.current += 1;

    generationRef.current = generation;
    setAuthGeneration(generation);

    tokenRef.current = token;
    setAccessToken(token);
    setIsInitializing(false);
  }, []);

  const logout = useCallback((): Promise<void> => {
    if (logoutPromise.current !== null) {
      return logoutPromise.current;
    }

    const generation = generationRef.current;

    sessionVersion.current += 1;
    setIsLoggingOut(true);

    logoutPromise.current = withAuthLock(async () => {
      assertAuthGeneration(generation);

      await apiRequest<void>("/auth/logout", {
        method: "POST",
      });

      const newGeneration = advanceAuthGeneration();

      generationRef.current = newGeneration;
      setAuthGeneration(newGeneration);

      clearSession();
    }).finally(() => {
      logoutPromise.current = null;
      setIsLoggingOut(false);
    });

    return logoutPromise.current;
  }, [clearSession]);

  const refreshSession = useCallback(
    async (
      rejectedToken: string,
      expectedGeneration: string
    ): Promise<string> => {
      if (logoutPromise.current !== null) {
        throw new ApiError(401, "Logout is in progress.");
      }

      assertAuthGeneration(expectedGeneration);

      if (
        generationRef.current !== expectedGeneration
      ) {
        throw new ApiError(401, "Session has changed.");
      }

      const currentToken = tokenRef.current;

      if (currentToken === null) {
        throw new ApiError(
          401,
          "Session is no longer active."
        );
      }

      const expectedSessionId = readSessionId(rejectedToken);

      if (
        readSessionId(currentToken) !== expectedSessionId
      ) {
        throw new ApiError(401, "Session has changed.");
      }

      if (currentToken !== rejectedToken) {
        return currentToken;
      }

      const version = sessionVersion.current;

      try {
        const newToken = await refreshAccessToken(
          expectedGeneration
        );

        assertAuthGeneration(expectedGeneration);

        if (
          sessionVersion.current !== version ||
          generationRef.current !== expectedGeneration
        ) {
          throw new ApiError(401, "Session has changed.");
        }

        if (
          readSessionId(newToken) !== expectedSessionId
        ) {
          throw new ApiError(401, "Session has changed.");
        }

        tokenRef.current = newToken;
        setAccessToken(newToken);

        return newToken;
      } catch (error) {
        if (
          sessionVersion.current === version &&
          generationRef.current === expectedGeneration &&
          error instanceof ApiError &&
          error.status === 401
        ) {
          clearSession();
        }

        throw error;
      }
    },
    [clearSession]
  );

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        authGeneration,
        isAuthenticated: accessToken !== null,
        isInitializing,
        isLoggingOut,
        login,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error(
      "useAuth must be used inside an AuthProvider"
    );
  }

  return context;
}
