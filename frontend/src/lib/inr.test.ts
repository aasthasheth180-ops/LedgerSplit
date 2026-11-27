import { describe, expect, it } from "vitest";
import {
  parseMinor,
  minorToDecimal,
  formatMoney,
} from "./currency";
import { calculateSplits } from "./splits";

const people = [
  { userId: 1 },
  { userId: 2 },
  { userId: 3 },
];

describe("INR currency support", () => {
  it("parses rupees into paise", () => {
    expect(parseMinor("100.50", "INR")).toBe(10050);
  });

  it("converts paise into rupees", () => {
    expect(minorToDecimal(10050, "INR")).toBe("100.50");
  });

  it("formats Indian rupee amounts", () => {
    expect(formatMoney("100.50", "INR")).toBe("₹100.50");
  });

  it("rejects excess decimal precision", () => {
    expect(() => parseMinor("10.001", "INR")).toThrow();
  });

  it("allocates equal splits accurately", () => {
    const result = calculateSplits(
      "100.00", "INR", "Equal", people
    );

    expect(result.map(p => p.amount_owed)).toEqual([
      "33.34", "33.33", "33.33",
    ]);
  });

  it("supports exact INR splits", () => {
    const result = calculateSplits(
      "100.50",
      "INR",
      "Exact",
      [
        { userId: 1, value: "40.25" },
        { userId: 2, value: "60.25" },
      ]
    );

    expect(result.map(p => p.amount_owed)).toEqual([
      "40.25", "60.25",
    ]);
  });

  it("handles percentage rounding to paise", () => {
    const result = calculateSplits(
      "0.01",
      "INR",
      "Percent",
      [
        { userId: 1, value: "33.33" },
        { userId: 2, value: "33.33" },
        { userId: 3, value: "33.34" },
      ]
    );

    expect(result.map(p => p.amount_owed)).toEqual([
      "0.00", "0.00", "0.01",
    ]);
  });
});
