// Copyright (c) 2026 Athena Decision Systems SAS.
// Words for what the server already decided. Legality comes only from view.legal; these read that list and say
// why a card isn't on it, so nothing here can ever allow or forbid a card.
import type { SeatView } from "../types";
import { suitOf, type Suit } from "./cards";

export type CardReason =
  | { kind: "follow"; suit: Suit }
  | { kind: "two-of-clubs" }
  | { kind: "hearts-unbroken" }
  | { kind: "no-points-first-trick" }
  | { kind: "other" };

export type TurnHint =
  | { kind: "lead" }
  | { kind: "two-of-clubs" }
  | { kind: "follow"; suit: Suit }
  | { kind: "void"; suit: Suit }
  | { kind: "void-first-trick"; suit: Suit };

function ledSuit(view: SeatView): Suit | null {
  const first = view.trick?.cards?.[0];
  return first ? suitOf(first) : null;
}

/** Why this card, which isn't in view.legal, can't be played. */
export function whyNot(card: string, view: SeatView): CardReason {
  const legal = view.legal ?? [];
  const led = ledSuit(view);
  if (led) {
    if (legal.some((c) => suitOf(c) === led) && suitOf(card) !== led) return { kind: "follow", suit: led };
    if (view.first_trick && (suitOf(card) === "H" || card === "SQ")) return { kind: "no-points-first-trick" };
    return { kind: "other" };
  }
  if (view.first_trick && legal.length === 1 && legal[0] === "C2") return { kind: "two-of-clubs" };
  if (suitOf(card) === "H" && !view.hearts_broken) return { kind: "hearts-unbroken" };
  return { kind: "other" };
}

/** A line for the top of a turn. */
export function turnHint(view: SeatView): TurnHint {
  const legal = view.legal ?? [];
  const led = ledSuit(view);
  if (!led) {
    return view.first_trick && legal.length === 1 && legal[0] === "C2" ? { kind: "two-of-clubs" } : { kind: "lead" };
  }
  if (legal.some((c) => suitOf(c) === led)) return { kind: "follow", suit: led };
  return legal.length < view.hand.length ? { kind: "void-first-trick", suit: led } : { kind: "void", suit: led };
}
