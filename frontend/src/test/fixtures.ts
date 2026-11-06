// Copyright (c) 2026 Athena Decisions Systems SAS.
// Messages shaped as the server sends them, for tests.
import type { SeatView, SnapshotMessage, TableInfo } from "../types";

export const TABLE: TableInfo = {
  id: "t1", status: "playing", study: false, time_limit: null, invite_only: false,
  seats: [
    { kind: "person", name: "Ana", open: false },
    { kind: "clown", name: "Kant", open: false },
    { kind: "network", name: "Proust", open: false },
    { kind: "expert", name: "Hegel", open: false },
  ],
  your_seat: 1, your_turn: false, deal: 1, totals: [0, 0, 0, 0], waiting_for: [],
};

export const HAND = ["C2", "C9", "D3", "D7", "S2", "SQ", "SA", "H3", "H9", "HK", "CA", "DK", "S10"];

export function passView(over: Partial<SeatView> = {}): SeatView {
  return {
    seat: 1, deal: 1, direction: "Left", hand: HAND, scores: [0, 0, 0, 0], phase: "pass", decision: "pass", passed: [],
    ...over,
  };
}

export function playView(over: Partial<SeatView> = {}): SeatView {
  return {
    seat: 1, deal: 1, direction: "Left", hand: HAND, scores: [0, 0, 0, 0], phase: "play", decision: "play", passed: [],
    legal: [], trick: { leader: 3, cards: [] }, hearts_broken: false, first_trick: false, received: [], taken: [0, 0, 0, 0],
    to_play: 1,
    ...over,
  };
}

export function snapshot(over: Partial<SnapshotMessage> = {}): SnapshotMessage {
  return {
    type: "snapshot", table: TABLE, seq: 2, seat: 1, view: passView(), number: 1, direction: "Left", phase: "pass",
    waiting: [1, 2, 3, 4], trick: { leader: null, cards: [] }, taken: [0, 0, 0, 0], totals: [0, 0, 0, 0],
    tricks_done: 0, deadline: null, thoughts: [], finished: false,
    ...over,
  };
}
