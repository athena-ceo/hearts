// Copyright (c) 2026 Athena Decisions Systems SAS.
// The table as this client knows it, built only from what the server sends. A snapshot rebuilds all of it, so
// reconnecting is the same code as joining.
import type {
  AdviceMessage, Direction, Phase, QueuedMessage, SeatView, SnapshotMessage, TableInfo, Thought, ThoughtEntry,
} from "../types";
import { nextSeat, passSource } from "./seats";

export interface PlayedCard {
  seat: number;
  card: string;
  /** Already on the table when we arrived, so it doesn't fly in. */
  still?: boolean;
}

export interface Sweep { id: number; winner: number; cards: PlayedCard[]; }

export type Pending = { kind: "play"; cards: string[] } | { kind: "pass"; cards: string[] };

export interface TableState {
  ready: boolean;
  table: TableInfo | null;
  seat: number | null;
  seq: number;
  number: number;
  direction: Direction;
  phase: Phase | null;
  hand: string[];
  view: SeatView | null;
  waiting: number[];
  deadline: number | null;
  trick: PlayedCard[];
  leader: number | null;
  sweep: Sweep | null;
  taken: number[];
  totals: number[];
  tricksDone: number;
  thoughts: ThoughtEntry[];
  /** The thoughts shown are from the trick that just ended. */
  thoughtsFromLastTrick: boolean;
  advice: AdviceMessage | null;
  /** A turn was announced while connected, so its advice is on the way. It isn't resent on reconnecting. */
  adviceExpected: boolean;
  passedSeats: number[];
  /** The cards you were just passed, and from whom. */
  received: string[];
  receivedFrom: number | null;
  /** How cards in hand arrived, so that only new ones are animated. */
  entering: "deal" | "received" | null;
  dealEnd: { number: number; scores: number[] } | null;
  gameEnd: { totals: number[]; winners: number[] } | null;
  /** The latest finished deal, for the review link. */
  lastDeal: number;
  pending: Pending | null;
  refused: string | null;
  failure: string | null;
  /** Your clock ran out and the server moved for you. */
  timedOut: boolean;
}

export type LocalAction =
  | { type: "sent-play"; card: string }
  | { type: "sent-pass"; cards: string[] }
  | { type: "refused"; message: string }
  | { type: "error"; message: string }
  | { type: "table-info"; table: TableInfo }
  | { type: "dismiss-deal-end" };

export type Action = SnapshotMessage | QueuedMessage | LocalAction;

export const initialState: TableState = {
  ready: false, table: null, seat: null, seq: 0, number: 0, direction: null, phase: null, hand: [], view: null,
  waiting: [], deadline: null, trick: [], leader: null, sweep: null, taken: [0, 0, 0, 0], totals: [0, 0, 0, 0],
  tricksDone: 0, thoughts: [], thoughtsFromLastTrick: false, advice: null, adviceExpected: false, passedSeats: [], received: [],
  receivedFrom: null, entering: null, dealEnd: null, gameEnd: null, lastDeal: 0, pending: null, refused: null,
  failure: null, timedOut: false,
};

const without = (cards: string[], gone: readonly string[]) => cards.filter((c) => !gone.includes(c));

/** The cards still yours: while passing, the server's hand includes what you've already passed. */
function handFromView(view: SeatView): string[] {
  return view.phase === "pass" ? without(view.hand, view.passed ?? []) : view.hand;
}

function lowestSeats(totals: number[]): number[] {
  const low = Math.min(...totals);
  return totals.flatMap((total, i) => (total === low ? [i + 1] : []));
}

function applySnapshot(state: TableState, m: SnapshotMessage): TableState {
  const cards = m.trick?.cards ?? [];
  const leader = m.trick?.leader ?? null;
  const trick: PlayedCard[] = leader === null ? [] : cards.map((card, i) => ({
    seat: ((leader - 1 + i) % 4) + 1, card, still: true,
  }));
  const done = m.phase === "done" || m.finished;
  return {
    ...initialState,
    ready: true,
    table: m.table,
    seat: m.seat,
    seq: m.seq,
    number: m.number,
    direction: m.direction,
    phase: m.phase,
    hand: m.view ? handFromView(m.view) : [],
    view: m.view,
    waiting: m.waiting,
    deadline: m.deadline,
    trick,
    leader,
    taken: m.taken,
    totals: m.totals,
    tricksDone: m.tricks_done,
    thoughts: m.thoughts ?? [],
    gameEnd: m.finished ? { totals: m.totals, winners: lowestSeats(m.totals) } : null,
    lastDeal: Math.max(done ? m.number : m.number - 1, state.lastDeal, 0),
    failure: m.table.status === "failed" ? state.failure : null,
  };
}

function applyCard(state: TableState, seat: number, card: string, thought: Thought | undefined): TableState {
  const mine = seat === state.seat;
  const startsTrick = state.trick.length === 0;
  const thoughts = state.thoughtsFromLastTrick ? [] : state.thoughts;
  const next: TableState = {
    ...state,
    trick: [...state.trick, { seat, card }],
    leader: startsTrick ? seat : state.leader,
    sweep: null,
    thoughts: [...thoughts, { seat, card, thought }],
    thoughtsFromLastTrick: false,
    waiting: state.trick.length < 3 ? [nextSeat(seat)] : [],
    deadline: null,
    refused: null,
  };
  if (!mine) return next;
  return {
    ...next,
    hand: without(state.hand, [card]),
    view: state.view ? { ...state.view, legal: [] } : null,
    advice: null,
    pending: null,
    timedOut: state.pending === null && Boolean(state.table?.time_limit),
    received: [],
    receivedFrom: null,
  };
}

export function reduce(state: TableState, action: Action): TableState {
  switch (action.type) {
    case "snapshot":
      return applySnapshot(state, action);

    case "game":
      return { ...state, seq: action.seq };

    case "deal":
      return {
        ...state,
        seq: action.seq,
        number: action.number,
        direction: action.direction,
        phase: action.direction ? "pass" : "play",
        hand: action.hands ?? [],
        view: null,
        waiting: action.direction ? [1, 2, 3, 4] : [],
        deadline: null,
        trick: [],
        leader: null,
        sweep: null,
        taken: [0, 0, 0, 0],
        tricksDone: 0,
        thoughts: [],
        thoughtsFromLastTrick: false,
        advice: null,
        passedSeats: [],
        received: [],
        receivedFrom: null,
        entering: "deal",
        dealEnd: null,
        pending: null,
        refused: null,
        timedOut: false,
      };

    case "passed": {
      const mine = action.seat === state.seat;
      return {
        ...state,
        seq: action.seq,
        passedSeats: [...state.passedSeats, action.seat],
        waiting: state.waiting.filter((s) => s !== action.seat),
        ...(mine ? {
          hand: action.cards ? without(state.hand, action.cards) : state.hand,
          pending: null,
          advice: null,
          timedOut: state.pending === null && Boolean(state.table?.time_limit),
          deadline: null,
        } : {}),
      };
    }

    case "received": {
      const cards = action.cards ?? [];
      return {
        ...state,
        seq: action.seq,
        phase: "play",
        hand: [...state.hand, ...cards],
        view: null,
        waiting: [],
        deadline: null,
        received: cards,
        receivedFrom: state.seat ? passSource(state.seat, state.direction) : null,
        entering: "received",
      };
    }

    case "card":
      return { ...applyCard(state, action.seat, action.card, action.thought), seq: action.seq };

    case "trick": {
      const taken = [...state.taken];
      taken[action.winner - 1] += action.points;
      const seats = state.trick;
      return {
        ...state,
        seq: action.seq,
        trick: [],
        leader: action.winner,
        sweep: { id: action.seq, winner: action.winner, cards: seats },
        taken,
        tricksDone: state.tricksDone + 1,
        thoughtsFromLastTrick: true,
        waiting: [action.winner],
        received: [],
        receivedFrom: null,
      };
    }

    case "deal_end":
      return {
        ...state,
        seq: action.seq,
        phase: "done",
        waiting: [],
        deadline: null,
        dealEnd: { number: action.number, scores: action.scores },
        lastDeal: action.number,
      };

    case "totals":
      return { ...state, seq: action.seq, totals: action.totals };

    case "game_end":
      return { ...state, seq: action.seq, totals: action.totals, gameEnd: { totals: action.totals, winners: action.winners } };

    case "turn": {
      const view = action.view;
      return {
        ...state,
        waiting: action.waiting,
        deadline: action.deadline,
        view: view ?? state.view,
        adviceExpected: true,
        hand: view ? handFromView(view) : state.hand,
        phase: view ? view.phase : state.phase,
        taken: view?.taken ?? state.taken,
      };
    }

    case "advice":
      return { ...state, advice: action };

    case "sent-play":
      return { ...state, pending: { kind: "play", cards: [action.card] }, refused: null, timedOut: false };

    case "sent-pass":
      return { ...state, pending: { kind: "pass", cards: action.cards }, refused: null, timedOut: false };

    case "refused":
      return { ...state, pending: null, refused: action.message };

    case "error":
      return { ...state, pending: null, failure: action.message };

    case "table-info":
      return { ...state, table: { ...action.table, your_seat: state.table?.your_seat ?? action.table.your_seat } };

    case "dismiss-deal-end":
      return { ...state, dealEnd: null };
  }
}

// What the screen asks of the state. None of it decides legality: that's view.legal.

export function canPass(state: TableState): boolean {
  const { view, seat } = state;
  return Boolean(view && seat && state.phase === "pass" && view.decision === "pass" && view.phase === "pass"
    && state.waiting.includes(seat) && !(view.passed?.length) && !state.pending);
}

export function canPlay(state: TableState): boolean {
  const { view, seat } = state;
  return Boolean(view && seat && view.decision === "play" && view.legal?.length
    && state.waiting.includes(seat) && !state.pending);
}
