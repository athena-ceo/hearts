// Copyright (c) 2026 Athena Decisions Systems SAS.
// Drawing cards only: what they look like and how a hand is laid out. No rules of the game live here.
import type { Dict } from "../i18n";

export type Suit = "C" | "D" | "H" | "S";

export const SUIT_GLYPH: Record<Suit, string> = { C: "♣", D: "♦", H: "♥", S: "♠" };

const SUIT_ORDER: Suit[] = ["C", "D", "S", "H"];
const RANK_ORDER = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];

export function suitOf(card: string): Suit { return card[0] as Suit; }
export function rankOf(card: string): string { return card.slice(1); }
export function isRed(card: string): boolean { return card[0] === "H" || card[0] === "D"; }

/** Suits apart, colours alternating, low to high: how a person holds a hand. */
export function sortHand(cards: readonly string[]): string[] {
  const key = (c: string) => SUIT_ORDER.indexOf(suitOf(c)) * 20 + RANK_ORDER.indexOf(rankOf(c));
  return [...cards].sort((a, b) => key(a) - key(b));
}

function rankName(t: Dict, card: string): string {
  const rank = rankOf(card);
  return (t.cards.ranks as Record<string, string>)[rank] ?? rank;
}

/** "queen of spades" */
export function cardName(t: Dict, card: string): string {
  return t.cards.name.replace("{rank}", rankName(t, card)).replace("{suit}", t.cards.suits[suitOf(card)]);
}

/** "the queen of spades", with the article French needs for that rank. */
export function cardNameWithArticle(t: Dict, card: string): string {
  const article = (t.cards.articles as Record<string, string>)[rankOf(card)] ?? t.cards.articles.other;
  return article + cardName(t, card);
}

/** "Q♠" */
export function cardShort(card: string): string {
  return rankOf(card) + SUIT_GLYPH[suitOf(card)];
}
