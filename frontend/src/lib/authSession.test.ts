import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  vi,
} from "vitest";

import { apiRequest } from "./api";

import {
  getAuthGeneration,
  advanceAuthGeneration,
  assertAuthGeneration,
  refreshAccessToken,
  readSessionId,
} from "./authSession";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();

  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

const mockApiRequest = vi.mocked(apiRequest);

describe("Authentication session coordination", () => {
  beforeEach(() => {
    localStorage.clear();
    mockApiRequest.mockReset();

    vi.stubGlobal("navigator", {
      locks: {
        request: async (
          _name: string,
          _options: unknown,
          operation: () => Promise<unknown>
        ) => operation(),
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the initial generation when none exists", () => {
    expect(getAuthGeneration()).toBe("initial");
  });

  it("creates and stores a new generation", () => {
    const generation = advanceAuthGeneration();

    expect(generation).not.toBe("initial");
    expect(getAuthGeneration()).toBe(generation);
  });

  it("creates a different generation for each session change", () => {
    const first = advanceAuthGeneration();
    const second = advanceAuthGeneration();

    expect(first).not.toBe(second);
  });

  it("accepts the current generation", () => {
    const generation = advanceAuthGeneration();

    expect(() =>
      assertAuthGeneration(generation)
    ).not.toThrow();
  });

  it("rejects a stale generation", () => {
    const oldGeneration = advanceAuthGeneration();

    advanceAuthGeneration();

    expect(() =>
      assertAuthGeneration(oldGeneration)
    ).toThrow("Session has changed.");
  });

  it("refreshes the current authentication session", async () => {
    const generation = advanceAuthGeneration();

    mockApiRequest.mockResolvedValue({
      access_token: "new-access-token",
      token_type: "bearer",
    });

    const token = await refreshAccessToken(generation);

    expect(token).toBe("new-access-token");

    expect(mockApiRequest).toHaveBeenCalledTimes(1);

    expect(mockApiRequest).toHaveBeenCalledWith(
      "/auth/refresh",
      { method: "POST" }
    );
  });

  it("shares one refresh operation across simultaneous requests", async () => {
    const generation = advanceAuthGeneration();

    mockApiRequest.mockResolvedValue({
      access_token: "shared-access-token",
      token_type: "bearer",
    });

    const first = refreshAccessToken(generation);
    const second = refreshAccessToken(generation);
    const third = refreshAccessToken(generation);

    expect(first).toBe(second);
    expect(second).toBe(third);

    const results = await Promise.all([
      first,
      second,
      third,
    ]);

    expect(results).toEqual([
      "shared-access-token",
      "shared-access-token",
      "shared-access-token",
    ]);

    expect(mockApiRequest).toHaveBeenCalledTimes(1);
  });

  it("rejects stale refresh before contacting the backend", async () => {
    const oldGeneration = advanceAuthGeneration();

    advanceAuthGeneration();

    await expect(
      refreshAccessToken(oldGeneration)
    ).rejects.toThrow("Session has changed.");

    expect(mockApiRequest).not.toHaveBeenCalled();
  });

  it("rejects a refresh response after the generation changes", async () => {
    const generation = advanceAuthGeneration();

    mockApiRequest.mockImplementationOnce(async () => {
      advanceAuthGeneration();

      return {
        access_token: "stale-access-token",
        token_type: "bearer",
      };
    });

    await expect(
      refreshAccessToken(generation)
    ).rejects.toThrow("Session has changed.");
  });

  it("rejects an invalid refresh response", async () => {
    const generation = advanceAuthGeneration();

    mockApiRequest.mockResolvedValue({
      access_token: "",
      token_type: "bearer",
    });

    await expect(
      refreshAccessToken(generation)
    ).rejects.toThrow(
      "Invalid session refresh response."
    );
  });

  it("allows another refresh after a failed operation", async () => {
    const generation = advanceAuthGeneration();

    mockApiRequest.mockRejectedValueOnce(
      new Error("Network failure")
    );

    await expect(
      refreshAccessToken(generation)
    ).rejects.toThrow("Network failure");

    mockApiRequest.mockResolvedValueOnce({
      access_token: "recovered-token",
      token_type: "bearer",
    });

    await expect(
      refreshAccessToken(generation)
    ).resolves.toBe("recovered-token");

    expect(mockApiRequest).toHaveBeenCalledTimes(2);
  });

  it("extracts the session ID from a JWT payload", () => {
    const payload = btoa(
      JSON.stringify({ sid: "123", sub: "1" })
    );

    const token = `header.${payload}.signature`;

    expect(readSessionId(token)).toBe("123");
  });

  it("rejects a malformed JWT", () => {
    expect(() =>
      readSessionId("invalid-token")
    ).toThrow("Invalid authentication session.");
  });

  it("rejects a JWT without a session ID", () => {
    const payload = btoa(
      JSON.stringify({ sub: "1" })
    );

    const token = `header.${payload}.signature`;

    expect(() =>
      readSessionId(token)
    ).toThrow("Invalid authentication session.");
  });
});
