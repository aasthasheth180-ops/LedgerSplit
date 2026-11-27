import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
} from "vitest";

import {
  renderHook,
  act,
  waitFor,
  cleanup,
} from "@testing-library/react";

import {
  AuthProvider,
  useAuth,
} from "./AuthContext";

import { apiRequest } from "../lib/api";

import {
  advanceAuthGeneration,
  getAuthGeneration,
  withAuthLock,
} from "../lib/authSession";

vi.mock("../lib/api", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../lib/api")>();

  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

const mockApiRequest = vi.mocked(apiRequest);

function createToken(sessionId: string): string {
  const payload = btoa(
    JSON.stringify({
      sid: sessionId,
      sub: "1",
    })
  );

  return `header.${payload}.signature`;
}

function dispatchStorageChange() {
  window.dispatchEvent(
    new StorageEvent("storage", {
      key: "ledgersplit-auth-generation",
      storageArea: localStorage,
      newValue: getAuthGeneration(),
    })
  );
}

describe("AuthContext session concurrency", () => {
  beforeEach(() => {
    localStorage.clear();
    mockApiRequest.mockReset();

    let queue: Promise<unknown> = Promise.resolve();

    vi.stubGlobal("navigator", {
      locks: {
        request: (
          _name: string,
          _options: unknown,
          operation: () => Promise<unknown>
        ) => {
          const result = queue.then(operation);

          queue = result.catch(() => undefined);

          return result;
        },
      },
    });

    mockApiRequest.mockResolvedValue({
      access_token: createToken("100"),
      token_type: "bearer",
    });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  async function initializeAuth() {
    const hook = renderHook(() => useAuth(), {
      wrapper: AuthProvider,
    });

    await waitFor(() => {
      expect(
        hook.result.current.isInitializing
      ).toBe(false);
    });

    expect(
      hook.result.current.isAuthenticated
    ).toBe(true);

    mockApiRequest.mockClear();

    return hook;
  }

  it("restores an authenticated session on startup", async () => {
    const { result } = await initializeAuth();

    expect(result.current.accessToken).toBe(
      createToken("100")
    );
  });

  it("keeps the initiating tab authenticated after login", async () => {
    const { result } = await initializeAuth();

    act(() => {
      result.current.login(createToken("200"));
    });

    expect(result.current.isAuthenticated).toBe(true);

    expect(result.current.accessToken).toBe(
      createToken("200")
    );
  });

  it("clears the previous session after an external session change", async () => {
    const { result } = await initializeAuth();

    act(() => {
      advanceAuthGeneration();
      dispatchStorageChange();
    });

    expect(result.current.isAuthenticated).toBe(false);

    expect(result.current.accessToken).toBeNull();
  });

  it("ignores delayed storage events for the current generation", async () => {
    const { result } = await initializeAuth();

    const oldGeneration = getAuthGeneration();

    act(() => {
      result.current.login(createToken("200"));
    });

    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: "ledgersplit-auth-generation",
          storageArea: localStorage,
          newValue: oldGeneration,
        })
      );
    });

    expect(result.current.isAuthenticated).toBe(true);

    expect(result.current.accessToken).toBe(
      createToken("200")
    );
  });

  it("rejects refresh requests from a previous login", async () => {
    const { result } = await initializeAuth();

    const oldToken = result.current.accessToken!;
    const oldGeneration = result.current.authGeneration;

    act(() => {
      result.current.login(createToken("200"));
    });

    await expect(
      result.current.refreshSession(
        oldToken,
        oldGeneration
      )
    ).rejects.toThrow("Session has changed.");

    expect(mockApiRequest).not.toHaveBeenCalled();

    expect(result.current.accessToken).toBe(
      createToken("200")
    );
  });

  it("rejects a refreshed token belonging to another session", async () => {
    const { result } = await initializeAuth();

    mockApiRequest.mockResolvedValueOnce({
      access_token: createToken("999"),
      token_type: "bearer",
    });

    await act(async () => {
      await expect(
        result.current.refreshSession(
          result.current.accessToken!,
          result.current.authGeneration
        )
      ).rejects.toThrow("Session has changed.");
    });

    expect(result.current.isAuthenticated).toBe(false);
  });

  it("prevents a queued stale logout from reaching the backend", async () => {
    const { result } = await initializeAuth();

    let releaseLock!: () => void;

    const blocker = withAuthLock(
      () =>
        new Promise<void>((resolve) => {
          releaseLock = resolve;
        })
    );

    await waitFor(() => {
      expect(releaseLock).toBeDefined();
    });

    let logoutPromise!: Promise<void>;

    act(() => {
      logoutPromise = result.current.logout();
    });

    const rejection = expect(
      logoutPromise
    ).rejects.toThrow("Session has changed.");

    act(() => {
      advanceAuthGeneration();
      dispatchStorageChange();
    });

    await act(async () => {
      releaseLock();

      await blocker;
      await rejection;
    });

    expect(mockApiRequest).not.toHaveBeenCalled();

    expect(result.current.isAuthenticated).toBe(false);

    expect(result.current.isLoggingOut).toBe(false);
  });

  it("prevents a queued stale refresh from reaching the backend", async () => {
    const { result } = await initializeAuth();

    let releaseLock!: () => void;

    const blocker = withAuthLock(
      () =>
        new Promise<void>((resolve) => {
          releaseLock = resolve;
        })
    );

    await waitFor(() => {
      expect(releaseLock).toBeDefined();
    });

    const refreshPromise =
      result.current.refreshSession(
        result.current.accessToken!,
        result.current.authGeneration
      );

    const rejection = expect(
      refreshPromise
    ).rejects.toThrow("Session has changed.");

    act(() => {
      advanceAuthGeneration();
      dispatchStorageChange();
    });

    await act(async () => {
      releaseLock();

      await blocker;
      await rejection;
    });

    expect(mockApiRequest).not.toHaveBeenCalled();

    expect(result.current.isAuthenticated).toBe(false);
  });

  it("clears authentication after successful logout", async () => {
    const { result } = await initializeAuth();

    const oldGeneration = getAuthGeneration();

    mockApiRequest.mockResolvedValueOnce(undefined);

    await act(async () => {
      await result.current.logout();
    });

    expect(mockApiRequest).toHaveBeenCalledWith(
      "/auth/logout",
      { method: "POST" }
    );

    expect(result.current.isAuthenticated).toBe(false);

    expect(result.current.accessToken).toBeNull();

    expect(getAuthGeneration()).not.toBe(
      oldGeneration
    );
  });
});
