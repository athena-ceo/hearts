// Copyright (c) 2026 Athena Decisions Systems SAS.
import { describe, expect, it } from "vitest";

import { nextSeat, passSource, passTarget, positionOf, seatAt, seatsFrom } from "./seats";

describe("rotation", () => {
  it("puts you at the bottom, whichever seat you have", () => {
    for (const me of [1, 2, 3, 4]) expect(positionOf(me, me)).toBe("south");
  });

  it("puts your left neighbour, the next number, on your left", () => {
    expect(positionOf(2, 1)).toBe("west");
    expect(positionOf(3, 1)).toBe("north");
    expect(positionOf(4, 1)).toBe("east");
    expect(positionOf(1, 2)).toBe("east");
    expect(positionOf(4, 3)).toBe("west");
    expect(positionOf(1, 3)).toBe("north");
    expect(positionOf(1, 4)).toBe("west");
    expect(positionOf(3, 4)).toBe("east");
  });

  it("draws someone watching from seat 1", () => {
    expect(positionOf(1, null)).toBe("south");
    expect(positionOf(3, null)).toBe("north");
  });

  it("seatAt undoes positionOf", () => {
    for (const me of [1, 2, 3, 4]) {
      for (const seat of [1, 2, 3, 4]) expect(seatAt(positionOf(seat, me), me)).toBe(seat);
    }
  });

  it("lists seats clockwise from you", () => {
    expect(seatsFrom(3)).toEqual([3, 4, 1, 2]);
    expect(seatsFrom(null)).toEqual([1, 2, 3, 4]);
  });
});

describe("passing directions", () => {
  it("names who you pass to and who passes to you", () => {
    expect(passTarget(1, "Left")).toBe(2);
    expect(passSource(1, "Left")).toBe(4);
    expect(passTarget(1, "Across")).toBe(3);
    expect(passSource(1, "Across")).toBe(3);
    expect(passTarget(1, "Right")).toBe(4);
    expect(passSource(1, "Right")).toBe(2);
    expect(passTarget(4, "Left")).toBe(1);
    expect(passTarget(1, null)).toBeNull();
    expect(passSource(1, null)).toBeNull();
  });

  it("goes clockwise", () => {
    expect([1, 2, 3, 4].map(nextSeat)).toEqual([2, 3, 4, 1]);
  });
});
