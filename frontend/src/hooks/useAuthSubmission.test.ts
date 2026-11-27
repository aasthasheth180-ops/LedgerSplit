import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useAuthSubmission } from "./useAuthSubmission";

describe("useAuthSubmission", () => {
  it("starts in an idle state", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    expect(result.current.isLoading).toBe(false);
  });

  it("allows the first submission", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    act(() => {
      expect(
        result.current.beginSubmission()
      ).toBe(true);
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("rejects immediate duplicate submissions", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    act(() => {
      expect(
        result.current.beginSubmission()
      ).toBe(true);

      expect(
        result.current.beginSubmission()
      ).toBe(false);
    });
  });

  it("blocks Google while email submission is active", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    const emailSubmit = result.current.beginSubmission;
    const googleSubmit = result.current.beginSubmission;

    act(() => {
      expect(emailSubmit()).toBe(true);
      expect(googleSubmit()).toBe(false);
    });
  });

  it("blocks email while Google submission is active", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    const googleSubmit = result.current.beginSubmission;
    const emailSubmit = result.current.beginSubmission;

    act(() => {
      expect(googleSubmit()).toBe(true);
      expect(emailSubmit()).toBe(false);
    });
  });

  it("returns to idle after submission finishes", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    act(() => {
      result.current.beginSubmission();
    });

    act(() => {
      result.current.endSubmission();
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("allows retry after submission finishes", () => {
    const { result } = renderHook(
      () => useAuthSubmission()
    );

    act(() => {
      expect(
        result.current.beginSubmission()
      ).toBe(true);

      result.current.endSubmission();

      expect(
        result.current.beginSubmission()
      ).toBe(true);
    });
  });
});
