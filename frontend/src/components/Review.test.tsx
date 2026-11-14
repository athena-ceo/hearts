// Copyright (c) 2026 Athena Decision Systems SAS.
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { en } from "../i18n/en";
import { I18nProvider } from "../i18n";
import type { DealReview } from "../types";
import { headline, ReviewTable } from "./Review";

const REVIEW: DealReview = {
  number: 5, direction: "Left", dealt: [], passed: [],
  tricks: [
    { leader: 3, cards: ["D9", "D7", "SQ", "D6"], winner: 3 },
    { leader: 1, cards: ["S10", "D8", "C8", "DJ"], winner: 1 },
    { leader: 1, cards: ["S2", "S3", "S4", "S5"], winner: 4 },
  ],
  scores: [7, 19, 0, 0],
  thoughts: [],
  decisions: [
    {
      decision: "pass", trick: null, you: ["D5", "DA", "HK"],
      advice: { network: { answer: ["H10", "HK", "D5"], thought: null } },
    },
    {
      decision: "play", trick: 1, you: "SQ", advice: {
        expert: { answer: "SQ", thought: { text: "Min - dumping the maggie. Heh, heh.", rule: "dump.queen" } },
        network: { answer: "HA", thought: { shares: { HA: 1, SQ: 0 } } },
      },
    },
    {
      decision: "play", trick: 2, you: "S10", advice: {
        expert: { answer: "S2", thought: { text: "Leading lowest card.", rule: "lead.lowest" } },
        network: { answer: "S10", thought: { shares: { S10: 0.87, S2: 0.13 } } },
      },
    },
  ],
  what_if: { kind: "network", label: "Neural network", scores: [-26, 26, 26, 26] },
};

describe("the headline", () => {
  it("says what the score shows, and calls the replay close", () => {
    const [yours, theirs] = headline(en, REVIEW, 1);
    expect(yours).toBe("You took 7 points.");
    expect(theirs).toBe("From the same seat, in a close replay, the network shot the moon.");
  });

  it("claims no moon unless the score says so", () => {
    const [, theirs] = headline(en, { ...REVIEW, what_if: { ...REVIEW.what_if!, scores: [4, 22, 0, 0] } }, 1);
    expect(theirs).toBe("From the same seat, in a close replay, the network took 4.");
  });

  it("says nothing of the network without a what_if", () => {
    expect(headline(en, { ...REVIEW, what_if: null }, 1)).toEqual(["You took 7 points."]);
  });

  it("is plain for someone who wasn't playing", () => {
    expect(headline(en, REVIEW, null)).toEqual(["Deal 5"]);
  });
});

describe("the table of decisions", () => {
  beforeEach(() => { localStorage.setItem("hearts.lang", "en"); });

  const rows = () => {
    render(<I18nProvider><ReviewTable review={REVIEW} me={1} /></I18nProvider>);
    return screen.getAllByRole("row").slice(1);
  };

  it("shades rows where you and the network differ", () => {
    const [pass, first, second, third] = rows();
    expect(pass).toHaveClass("split");
    expect(first).toHaveClass("split");
    expect(second).not.toHaveClass("split");
    expect(third).not.toHaveClass("split");
  });

  it("quotes the Expert's reason for your card only when it chose that card", () => {
    const [, first, second] = rows();
    expect(first).toHaveTextContent("Q♠: Min - dumping the maggie. Heh, heh.");
    expect(first).toHaveTextContent("dump.queen");
    expect(second).toHaveTextContent("10♠. The Expert would play 2♠: Leading lowest card.");
  });

  it("shows the network's choice with its percentage, or that it agrees", () => {
    const [, first, second] = rows();
    expect(first).toHaveTextContent("100%");
    expect(second).toHaveTextContent("Same card, 87%");
  });

  it("outlines the winning card by who led", () => {
    rows();
    const winners = document.querySelectorAll(".winner [role=img]");
    expect(winners[0]).toHaveAttribute("aria-label", "9 of diamonds");
    expect(winners[1]).toHaveAttribute("aria-label", "10 of spades");
    expect(winners[2]).toHaveAttribute("aria-label", "5 of spades");
  });

  it("marks a trick where you had no choice", () => {
    const row = rows()[3];
    expect(row).toHaveTextContent("your only legal card");
    expect(row).toHaveTextContent("No choice");
  });
});
