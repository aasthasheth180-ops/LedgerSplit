import { apiRequest, ApiError } from "./api";

type RefreshResponse = {
  access_token: string;
  token_type: string;
};

const AUTH_LOCK_NAME = "ledgersplit-auth-session";
const AUTH_GENERATION_KEY = "ledgersplit-auth-generation";

const refreshPromises = new Map<string, Promise<string>>();

export function getAuthGeneration(): string {
  return localStorage.getItem(AUTH_GENERATION_KEY) ?? "initial";
}

export function advanceAuthGeneration(): string {
  const generation = crypto.randomUUID();

  localStorage.setItem(AUTH_GENERATION_KEY, generation);

  return generation;
}

export function assertAuthGeneration(expected: string): void {
  if (getAuthGeneration() !== expected) {
    throw new ApiError(401, "Session has changed.");
  }
}

export function subscribeToAuthChanges(
  listener: () => void
): () => void {
  function handleStorage(event: StorageEvent) {
    if (
      event.storageArea === localStorage &&
      (event.key === AUTH_GENERATION_KEY || event.key === null)
    ) {
      listener();
    }
  }

  window.addEventListener("storage", handleStorage);

  return () => {
    window.removeEventListener("storage", handleStorage);
  };
}

export async function withAuthLock<T>(
  operation: () => Promise<T>
): Promise<T> {
  if (typeof navigator.locks === "undefined") {
    throw new Error(
      "Secure session coordination is unavailable in this browser."
    );
  }

  return navigator.locks.request(
    AUTH_LOCK_NAME,
    { mode: "exclusive" },
    operation
  );
}

export function readSessionId(token: string): string {
  try {
    const payload = token.split(".")[1];

    const base64 = payload
      .replace(/-/g, "+")
      .replace(/_/g, "/");

    const decoded = JSON.parse(atob(base64));

    if (
      typeof decoded.sid !== "string" ||
      !decoded.sid
    ) {
      throw new Error("Invalid session ID.");
    }

    return decoded.sid;
  } catch {
    throw new ApiError(
      401,
      "Invalid authentication session."
    );
  }
}

async function performRefresh(
  expectedGeneration: string
): Promise<string> {
  return withAuthLock(async () => {
    assertAuthGeneration(expectedGeneration);

    const response = await apiRequest<RefreshResponse>(
      "/auth/refresh",
      {
        method: "POST",
      }
    );

    assertAuthGeneration(expectedGeneration);

    if (
      typeof response.access_token !== "string" ||
      !response.access_token
    ) {
      throw new Error(
        "Invalid session refresh response."
      );
    }

    return response.access_token;
  });
}

export function refreshAccessToken(
  expectedGeneration: string
): Promise<string> {
  const existing = refreshPromises.get(expectedGeneration);

  if (existing) {
    return existing;
  }

  const promise = performRefresh(expectedGeneration).finally(
    () => {
      refreshPromises.delete(expectedGeneration);
    }
  );

  refreshPromises.set(expectedGeneration, promise);

  return promise;
}
