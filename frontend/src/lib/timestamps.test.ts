import { describe, expect, it } from "vitest";
import { parseTimestampToSeconds } from "./timestamps";

describe("parseTimestampToSeconds", () => {
  it("parses seconds", () => {
    expect(parseTimestampToSeconds("90")).toBe(90);
    expect(parseTimestampToSeconds("0")).toBe(0);
  });

  it("parses MM:SS", () => {
    expect(parseTimestampToSeconds("15:30")).toBe(930);
    expect(parseTimestampToSeconds("0:45")).toBe(45);
  });

  it("parses HH:MM:SS", () => {
    expect(parseTimestampToSeconds("01:30:00")).toBe(5400);
    expect(parseTimestampToSeconds("2:00:00")).toBe(7200);
  });

  it("returns null for invalid inputs", () => {
    expect(parseTimestampToSeconds("")).toBeNull();
    expect(parseTimestampToSeconds(null)).toBeNull();
    expect(parseTimestampToSeconds("abc")).toBeNull();
    expect(parseTimestampToSeconds("12:75")).toBeNull();
    expect(parseTimestampToSeconds("-5")).toBeNull();
  });
});
