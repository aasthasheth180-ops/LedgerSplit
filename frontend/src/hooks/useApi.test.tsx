import {
  describe,
  it,
  expect,
  beforeEach,
  vi,
} from "vitest";

import { renderHook } from "@testing-library/react";
import { useApi } from "./useApi";
import { useAuth } from "../context/AuthContext";
import { apiRequest, ApiError } from "../lib/api";

import {
  advanceAuthGeneration,
  getAuthGeneration,
} from "../lib/authSession";

vi.mock("../context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("../lib/api", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../lib/api")>();

  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

const mockApiRequest = vi.mocked(apiRequest);
const mockUseAuth = vi.mocked(useAuth);
const mockRefreshSession = vi.fn();

function configureAuth(
  accessToken: string | null = "old-token"
) {
  mockUseAuth.mockReturnValue({
    accessToken,
    authGeneration: getAuthGeneration(),
    isAuthenticated: accessToken !== null,
    isInitializing: false,
    isLoggingOut: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshSession: mockRefreshSession,
  });
}

describe("Authenticated API requests", () => {
  beforeEach(() => {
    localStorage.clear();

    mockApiRequest.mockReset();
    mockRefreshSession.mockReset();
    mockUseAuth.mockReset();

    advanceAuthGeneration();

    configureAuth();
  });

  it("returns a successful API response", async () => {
    mockApiRequest.mockResolvedValueOnce({
      id: 1,
    });

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).resolves.toEqual({ id: 1 });

    expect(mockApiRequest).toHaveBeenCalledTimes(1);

    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it("refreshes and retries after a 401 response", async () => {
    mockApiRequest
      .mockRejectedValueOnce(
        new ApiError(401, "Expired token")
      )
      .mockResolvedValueOnce({ id: 1 });

    mockRefreshSession.mockResolvedValueOnce(
      "new-token"
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).resolves.toEqual({ id: 1 });

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);

    expect(mockApiRequest).toHaveBeenCalledTimes(2);

    expect(mockApiRequest).toHaveBeenNthCalledWith(
      2,
      "/users/me",
      {},
      "new-token"
    );
  });

  it("does not retry more than once", async () => {
    mockApiRequest.mockRejectedValue(
      new ApiError(401, "Unauthorized")
    );

    mockRefreshSession.mockResolvedValueOnce(
      "new-token"
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Unauthorized");

    expect(mockApiRequest).toHaveBeenCalledTimes(2);

    expect(mockRefreshSession).toHaveBeenCalledTimes(1);
  });

  it("does not refresh after a non-401 error", async () => {
    mockApiRequest.mockRejectedValueOnce(
      new ApiError(500, "Server error")
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Server error");

    expect(mockRefreshSession).not.toHaveBeenCalled();

    expect(mockApiRequest).toHaveBeenCalledTimes(1);
  });

  it("does not refresh authentication endpoints", async () => {
    mockApiRequest.mockRejectedValueOnce(
      new ApiError(401, "Invalid credentials")
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/auth/login")
    ).rejects.toThrow("Invalid credentials");

    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it("does not refresh an unauthenticated request", async () => {
    configureAuth(null);

    mockApiRequest.mockRejectedValueOnce(
      new ApiError(401, "Unauthorized")
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Unauthorized");

    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it("rejects stale requests before contacting the backend", async () => {
    const { result } = renderHook(() => useApi());

    advanceAuthGeneration();

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Session has changed.");

    expect(mockApiRequest).not.toHaveBeenCalled();

    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it("rejects successful responses from an old session", async () => {
    mockApiRequest.mockImplementationOnce(async () => {
      advanceAuthGeneration();

      return { id: 1 };
    });

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Session has changed.");

    expect(mockRefreshSession).not.toHaveBeenCalled();
  });

  it("does not retry after the session changes during refresh", async () => {
    mockApiRequest.mockRejectedValueOnce(
      new ApiError(401, "Expired token")
    );

    mockRefreshSession.mockImplementationOnce(
      async () => {
        advanceAuthGeneration();

        return "new-token";
      }
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Session has changed.");

    expect(mockApiRequest).toHaveBeenCalledTimes(1);
  });

  it("does not send an already cancelled request", async () => {
    const controller = new AbortController();

    controller.abort();

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me", {
        signal: controller.signal,
      })
    ).rejects.toMatchObject({
      name: "AbortError",
    });

    expect(mockApiRequest).not.toHaveBeenCalled();
  });

  it("does not retry a request cancelled during refresh", async () => {
    const controller = new AbortController();

    mockApiRequest.mockRejectedValueOnce(
      new ApiError(401, "Expired token")
    );

    mockRefreshSession.mockImplementationOnce(
      async () => {
        controller.abort();

        return "new-token";
      }
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me", {
        signal: controller.signal,
      })
    ).rejects.toMatchObject({
      name: "AbortError",
    });

    expect(mockApiRequest).toHaveBeenCalledTimes(1);
  });

  it("does not retry when session refresh fails", async () => {
    mockApiRequest.mockRejectedValueOnce(
      new ApiError(401, "Expired token")
    );

    mockRefreshSession.mockRejectedValueOnce(
      new ApiError(401, "Session expired")
    );

    const { result } = renderHook(() => useApi());

    await expect(
      result.current.request("/users/me")
    ).rejects.toThrow("Session expired");

    expect(mockApiRequest).toHaveBeenCalledTimes(1);
  });
});
