import { useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";
import { assertAuthGeneration } from "../lib/authSession";

export function useApi() {
  const {
    accessToken,
    authGeneration,
    refreshSession,
  } = useAuth();

  const request = useCallback(
    async <T,>(
      endpoint: string,
      options: RequestInit = {}
    ): Promise<T> => {
      assertAuthGeneration(authGeneration);
      options.signal?.throwIfAborted();

      try {
        const result = await apiRequest<T>(
          endpoint,
          options,
          accessToken
        );

        assertAuthGeneration(authGeneration);
        options.signal?.throwIfAborted();

        return result;
      } catch (error) {
        if (
          !(error instanceof ApiError) ||
          error.status !== 401 ||
          accessToken === null ||
          endpoint.startsWith("/auth/") ||
          options.signal?.aborted
        ) {
          throw error;
        }

        assertAuthGeneration(authGeneration);

        const newToken = await refreshSession(
          accessToken,
          authGeneration
        );

        assertAuthGeneration(authGeneration);
        options.signal?.throwIfAborted();

        const result = await apiRequest<T>(
          endpoint,
          options,
          newToken
        );

        assertAuthGeneration(authGeneration);
        options.signal?.throwIfAborted();

        return result;
      }
    },
    [accessToken, authGeneration, refreshSession]
  );

  return { request };
}
