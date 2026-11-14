// Copyright (c) 2026 Athena Decision Systems SAS.
import { describe, expect, it } from "vitest";

import { HAND, passView, playView, snapshot, TABLE } from "../test/fixtures";
import { canPass, canPlay, initialState, reduce, type TableState } from "./reducer";

const start = (over = {}) => reduce(initialState, snapshot(over));

function run(state: TableState, ...actions: Parameters<typeof reduce>[1][]): TableState {
  return actions.reduce(reduce, state);
}

describe("snapshot", () => {
  it("rebuilds everything, and places the trick's cards by seat from its leader", () => {
    const state = start({
      phase: "play", view: playView(), waiting: [1], taken: [3, 0, 13, 0], totals: [10, 20, 30, 40], tricks_done: 4, number: 3,
      trick: { leader: 3, cards: ["D3", "D9"] },
      thoughts: [{ seat: 3, card: "D3", thought: { text: "Min - dumping the maggie. Heh, heh." } }],
    });
    expect(state.ready).toBe(true);
    expect(state.trick).toEqual([{ seat: 3, card: "D3", still: true }, { seat: 4, card: "D9", still: true }]);
    expect(state.leader).toBe(3);
    expect(state.taken).toEqual([3, 0, 13, 0]);
    expect(state.totals).toEqual([10, 20, 30, 40]);
    expect(state.tricksDone).toBe(4);
    expect(state.lastDeal).toBe(2);
    expect(state.thoughts[0].thought?.text).toBe("Min - dumping the maggie. Heh, heh.");
  });

  it("forgets everything from before it, so a reconnection is clean", () => {
    const messy = run(start(), { type: "sent-pass", cards: ["C2", "C9", "D3"] }, { type: "refused", message: "no" });
    const state = reduce(messy, snapshot());
    expect(state.pending).toBeNull();
    expect(state.refused).toBeNull();
  });

  it("keeps cards already passed out of your hand while passing", () => {
    const state = start({ view: passView({ passed: ["C2", "C9", "D3"] }), waiting: [2] });
    expect(state.hand).toHaveLength(10);
    expect(state.hand).not.toContain("C2");
    expect(canPass(state)).toBe(false);
  });

  it("gives a finished game its end, with the lowest totals winning", () => {
    const state = start({ finished: true, phase: "done", totals: [104, 60, 60, 90], number: 7 });
    expect(state.gameEnd).toEqual({ totals: [104, 60, 60, 90], winners: [2, 3] });
    expect(state.lastDeal).toBe(7);
  });

  it("copes with a table that hasn't started", () => {
    const state = start({ table: { ...TABLE, status: "open", deal: 0 }, view: null, number: 0, direction: null, phase: null, waiting: [], trick: null });
    expect(state.hand).toEqual([]);
    expect(state.trick).toEqual([]);
    expect(state.lastDeal).toBe(0);
  });
});

describe("a deal", () => {
  it("starts afresh and animates the new hand in", () => {
    const state = reduce(start({ number: 1, taken: [1, 2, 3, 20] }), { type: "deal", seq: 3, number: 2, direction: "Across", hands: HAND });
    expect(state.number).toBe(2);
    expect(state.phase).toBe("pass");
    expect(state.direction).toBe("Across");
    expect(state.hand).toEqual(HAND);
    expect(state.taken).toEqual([0, 0, 0, 0]);
    expect(state.entering).toBe("deal");
  });

  it("goes straight to play on a deal with no passing", () => {
    expect(reduce(start(), { type: "deal", seq: 3, number: 4, direction: null, hands: HAND }).phase).toBe("play");
  });

  it("is hand-free for someone watching", () => {
    expect(reduce(start({ seat: null, view: null }), { type: "deal", seq: 3, number: 1, direction: "Left", hands: null }).hand).toEqual([]);
  });
});

describe("passing", () => {
  it("takes your cards when the server confirms, then adds what you received", () => {
    let state = start();
    expect(canPass(state)).toBe(true);
    state = reduce(state, { type: "sent-pass", cards: ["C2", "C9", "D3"] });
    expect(canPass(state)).toBe(false);
    expect(state.hand).toEqual(HAND);
    state = reduce(state, { type: "passed", seq: 3, seat: 1, cards: ["C2", "C9", "D3"] });
    expect(state.hand).toHaveLength(10);
    expect(state.passedSeats).toEqual([1]);
    expect(state.pending).toBeNull();
    state = reduce(state, { type: "received", seq: 4, cards: ["H2", "H4", "H5"] });
    expect(state.hand).toHaveLength(13);
    expect(state.hand).toEqual(expect.arrayContaining(["H2", "H4", "H5"]));
    expect(state.phase).toBe("play");
    expect(state.received).toEqual(["H2", "H4", "H5"]);
    // Left means you pass to seat 2 and receive from seat 4.
    expect(state.receivedFrom).toBe(4);
  });

  it("notes other seats passing without any cards", () => {
    const state = reduce(start(), { type: "passed", seq: 3, seat: 2 });
    expect(state.passedSeats).toEqual([2]);
    expect(state.waiting).toEqual([1, 3, 4]);
    expect(state.hand).toEqual(HAND);
  });
});

describe("playing", () => {
  const myTurn = () => reduce(start({ phase: "play", view: playView(), waiting: [3] }), {
    type: "turn", waiting: [1], deadline: 1000, view: playView({ legal: ["D3", "D7"], trick: { leader: 3, cards: ["D9", "DA"] } }),
  });

  it("lets you play only when the server's view offers cards", () => {
    expect(canPlay(start({ phase: "play", view: playView(), waiting: [1] }))).toBe(false);
    expect(canPlay(start({ phase: "play", view: playView({ legal: ["D3"] }), waiting: [3] }))).toBe(false);
    const state = myTurn();
    expect(canPlay(state)).toBe(true);
    expect(state.deadline).toBe(1000);
  });

  it("locks while your card is on its way, and unlocks if refused", () => {
    let state = reduce(myTurn(), { type: "sent-play", card: "D3" });
    expect(canPlay(state)).toBe(false);
    state = reduce(state, { type: "refused", message: "D3 isn't legal for seat 1" });
    expect(canPlay(state)).toBe(true);
    expect(state.refused).toBe("D3 isn't legal for seat 1");
  });

  it("moves a played card from your hand to the trick", () => {
    const state = run(myTurn(), { type: "sent-play", card: "D3" }, { type: "card", seq: 3, seat: 1, card: "D3" });
    expect(state.hand).not.toContain("D3");
    expect(state.trick[state.trick.length - 1]).toEqual({ seat: 1, card: "D3" });
    expect(canPlay(state)).toBe(false);
    expect(state.timedOut).toBe(false);
  });

  it("shows whose card is next, going clockwise, without touching legality", () => {
    const state = reduce(start({ phase: "play", view: playView() }), { type: "card", seq: 3, seat: 3, card: "D9" });
    expect(state.waiting).toEqual([4]);
    expect(state.leader).toBe(3);
    expect(canPlay(state)).toBe(false);
  });

  it("sweeps a finished trick to its winner and counts the points", () => {
    let state = start({ phase: "play", view: playView() });
    state = run(state,
      { type: "card", seq: 3, seat: 3, card: "D9" },
      { type: "card", seq: 4, seat: 4, card: "SQ" },
      { type: "card", seq: 5, seat: 1, card: "D3" },
      { type: "card", seq: 6, seat: 2, card: "DA" },
      { type: "trick", seq: 7, leader: 3, cards: ["D9", "SQ", "D3", "DA"], winner: 2, points: 13 });
    expect(state.trick).toEqual([]);
    expect(state.sweep?.winner).toBe(2);
    expect(state.sweep?.cards).toHaveLength(4);
    expect(state.taken).toEqual([0, 13, 0, 0]);
    expect(state.tricksDone).toBe(1);
    expect(state.waiting).toEqual([2]);
  });

  it("tells you when the clock played for you", () => {
    const limited = reduce(start({ table: { ...TABLE, time_limit: 30 }, phase: "play", view: playView({ legal: ["D3"] }), waiting: [1] }),
      { type: "card", seq: 3, seat: 1, card: "D3" });
    expect(limited.timedOut).toBe(true);
  });
});

describe("thoughts", () => {
  it("keeps the last trick's until the next card, then starts again", () => {
    let state = start({ phase: "play", view: playView() });
    state = run(state,
      { type: "card", seq: 3, seat: 3, card: "D9", thought: { text: "Leading my singleton club.", rule: "lead.single.club" } },
      { type: "trick", seq: 4, leader: 3, cards: ["D9", "D2", "D3", "D4"], winner: 3, points: 0 });
    expect(state.thoughts).toHaveLength(1);
    expect(state.thoughtsFromLastTrick).toBe(true);
    state = reduce(state, { type: "card", seq: 5, seat: 3, card: "C3" });
    expect(state.thoughts).toHaveLength(1);
    expect(state.thoughts[0].card).toBe("C3");
    expect(state.thoughtsFromLastTrick).toBe(false);
  });

  it("knows whether advice is coming: not after a snapshot, since it isn't resent", () => {
    const state = start({ phase: "play", view: playView({ legal: ["D3"] }), waiting: [1] });
    expect(state.adviceExpected).toBe(false);
    expect(reduce(state, { type: "turn", waiting: [1], deadline: null, view: playView({ legal: ["D3"] }) }).adviceExpected).toBe(true);
  });
});

describe("the end", () => {
  it("shows a deal's scores until the next deal, with totals", () => {
    let state = start({ phase: "play", view: playView() });
    state = run(state, { type: "deal_end", seq: 3, number: 1, scores: [3, 13, 0, 10] }, { type: "totals", seq: 4, totals: [3, 13, 0, 10] });
    expect(state.dealEnd).toEqual({ number: 1, scores: [3, 13, 0, 10] });
    expect(state.totals).toEqual([3, 13, 0, 10]);
    expect(state.lastDeal).toBe(1);
    expect(reduce(state, { type: "deal", seq: 5, number: 2, direction: "Across", hands: HAND }).dealEnd).toBeNull();
    expect(reduce(state, { type: "dismiss-deal-end" }).dealEnd).toBeNull();
  });

  it("records the game's end and winners", () => {
    const state = reduce(start(), { type: "game_end", seq: 3, totals: [104, 60, 61, 90], winners: [2] });
    expect(state.gameEnd).toEqual({ totals: [104, 60, 61, 90], winners: [2] });
  });

  it("keeps a table update from changing which seat you are", () => {
    const state = reduce(start(), { type: "table-info", table: { ...TABLE, your_seat: null, study: true } });
    expect(state.table?.your_seat).toBe(1);
    expect(state.table?.study).toBe(true);
  });
});
