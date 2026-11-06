// Copyright (c) 2026 Athena Decisions Systems SAS.
// The server's messages, as backend/hearts/web.py, tables.py, game.py and review.py send them.

export type Direction = "Left" | "Across" | "Right" | null;
export type Phase = "pass" | "play" | "done";
export type TableStatus = "open" | "playing" | "finished" | "failed";

export interface Player { id: string; name: string; }
export interface Opponent { kind: string; label: string; }

export interface SeatInfo { kind: string; name: string | null; open: boolean; }

export interface TableInfo {
  id: string;
  status: TableStatus;
  study: boolean;
  time_limit: number | null;
  invite_only: boolean;
  seats: SeatInfo[];
  your_seat: number | null;
  your_turn: boolean;
  deal: number;
  totals: number[];
  waiting_for: (string | null)[];
}

export interface NewTable {
  seats: string[];
  study: boolean;
  invite_only: boolean;
  time_limit: number | null;
  fill_after: number | null;
}

/** Why a player chose: the Expert's text and rule, or a network's preferences. */
export interface Thought {
  text?: string;
  rule?: string;
  shares?: Record<string, number>;
}

export interface TrickView { leader: number | null; cards: string[]; }

/** What a seat may know. The server's `legal` is the only word on which cards may be played. */
export interface SeatView {
  seat: number;
  deal: number;
  direction: Direction;
  hand: string[];
  scores: number[];
  phase: Phase;
  decision: "pass" | "play";
  passed: string[];
  legal?: string[];
  trick?: TrickView;
  hearts_broken?: boolean;
  first_trick?: boolean;
  received?: string[];
  taken?: number[];
  to_play?: number | null;
}

export interface ThoughtEntry { seat: number; card: string; thought?: Thought | null; }

export interface AdviceEntry {
  kind: string;
  label: string;
  answer: string | string[];
  thought: Thought | null;
}

export interface SnapshotMessage {
  type: "snapshot";
  table: TableInfo;
  seq: number;
  seat: number | null;
  view: SeatView | null;
  number: number;
  direction: Direction;
  phase: Phase | null;
  waiting: number[];
  trick: TrickView | null;
  taken: number[];
  totals: number[];
  tricks_done: number;
  deadline: number | null;
  thoughts: ThoughtEntry[];
  finished: boolean;
}

export interface GameEvent { type: "game"; seq: number; }
export interface DealEvent { type: "deal"; seq: number; number: number; direction: Direction; hands: string[] | null; }
export interface PassedEvent { type: "passed"; seq: number; seat: number; cards?: string[]; }
export interface ReceivedEvent { type: "received"; seq: number; cards: string[] | null; }
export interface CardEvent { type: "card"; seq: number; seat: number; card: string; thought?: Thought; }
export interface TrickEvent { type: "trick"; seq: number; leader: number; cards: string[]; winner: number; points: number; }
export interface DealEndEvent { type: "deal_end"; seq: number; number: number; scores: number[]; }
export interface TotalsEvent { type: "totals"; seq: number; totals: number[]; }
export interface GameEndEvent { type: "game_end"; seq: number; totals: number[]; winners: number[]; }

export type SequencedEvent =
  | GameEvent | DealEvent | PassedEvent | ReceivedEvent | CardEvent
  | TrickEvent | DealEndEvent | TotalsEvent | GameEndEvent;

export interface TurnMessage { type: "turn"; waiting: number[]; deadline: number | null; view: SeatView | null; }
export interface AdviceMessage { type: "advice"; seat: number; number: number; tricks_done: number; entries: AdviceEntry[]; }
export interface RefusedMessage { type: "refused"; message: string; }
export interface ErrorMessage { type: "error"; message: string; }

/** What goes through the event queue, in the order it arrived. */
export type QueuedMessage = SequencedEvent | TurnMessage | AdviceMessage;

export type ServerMessage = SnapshotMessage | QueuedMessage | RefusedMessage | ErrorMessage;

// The deal review.

export interface ReviewAdvice { answer: string | string[]; thought: Thought | null; }

export interface ReviewDecision {
  decision: "pass" | "play";
  trick: number | null;
  you: string | string[];
  thought?: Thought | null;
  advice: Partial<Record<string, ReviewAdvice>>;
}

export interface ReviewTrick { leader: number; cards: string[]; winner: number; }

export interface WhatIf { kind: string; label: string; scores: number[]; }

export interface DealReview {
  number: number;
  direction: Direction;
  dealt: string[][];
  passed: string[][];
  tricks: ReviewTrick[];
  scores: number[];
  thoughts: { trick: number; seat: number; card: string; thought?: Thought | null }[];
  decisions: ReviewDecision[];
  what_if: WhatIf | null;
}
