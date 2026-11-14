// Copyright (c) 2026 Athena Decision Systems SAS.
import { describe, expect, it } from "vitest";

import { playView } from "../test/fixtures";
import { turnHint, whyNot } from "./reasons";
import { sortHand } from "./cards";

describe("why a card isn't legal", () => {
  it("says to follow suit", () => {
    const view = playView({ legal: ["D3", "D7"], trick: { leader: 3, cards: ["D9"] } });
    expect(whyNot("S2", view)).toEqual({ kind: "follow", suit: "D" });
    expect(turnHint(view)).toEqual({ kind: "follow", suit: "D" });
  });

  it("explains the two of clubs lead", () => {
    const view = playView({ legal: ["C2"], first_trick: true });
    expect(whyNot("SA", view)).toEqual({ kind: "two-of-clubs" });
    expect(turnHint(view)).toEqual({ kind: "two-of-clubs" });
  });

  it("explains unbroken hearts when you lead", () => {
    const view = playView({ legal: ["D3", "S2"], hearts_broken: false });
    expect(whyNot("H3", view)).toEqual({ kind: "hearts-unbroken" });
    expect(turnHint(view)).toEqual({ kind: "lead" });
  });

  it("explains no points on the first trick when you're void", () => {
    const view = playView({ legal: ["D3", "S2"], first_trick: true, trick: { leader: 3, cards: ["C5"] }, hand: ["D3", "S2", "SQ", "H3"] });
    expect(whyNot("SQ", view)).toEqual({ kind: "no-points-first-trick" });
    expect(whyNot("H3", view)).toEqual({ kind: "no-points-first-trick" });
    expect(turnHint(view)).toEqual({ kind: "void-first-trick", suit: "C" });
  });

  it("says you can play anything when you're void", () => {
    const hand = ["D3", "S2"];
    expect(turnHint(playView({ legal: hand, hand, trick: { leader: 3, cards: ["C5"] } }))).toEqual({ kind: "void", suit: "C" });
  });
});

describe("holding a hand", () => {
  it("sorts by suit with colours alternating, low to high", () => {
    expect(sortHand(["HA", "S10", "C2", "D3", "SQ", "S2", "H3"])).toEqual(["C2", "D3", "S2", "S10", "SQ", "H3", "HA"]);
  });
});
