// Copyright (c) 2026 Athena Decisions Systems SAS.
// The pass and play flows, through the real socket, queue and reducer, with a fake server on the other end.
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HAND, passView, playView, snapshot, TABLE } from "../test/fixtures";
import { PACE } from "../game/pace";
import { BACKOFF_START } from "../game/socket";
import { I18nProvider } from "../i18n";
import type { ServerMessage } from "../types";
import { TableScreen } from "./TableScreen";

class FakeSocket {
  static OPEN = 1;
  static all: FakeSocket[] = [];
  readyState = 1;
  sent: unknown[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(readonly url: string) { FakeSocket.all.push(this); }
  send(data: string) { this.sent.push(JSON.parse(data)); }
  close() { this.readyState = 3; }
  open() { this.onopen?.(); }
  receive(message: ServerMessage) { this.onmessage?.({ data: JSON.stringify(message) }); }
  drop() { this.readyState = 3; this.onclose?.(); }
}

const latest = () => FakeSocket.all[FakeSocket.all.length - 1];

function serve(...messages: ServerMessage[]) {
  act(() => { for (const m of messages) latest().receive(m); });
}

function tick(ms: number) {
  act(() => { vi.advanceTimersByTime(ms); });
}

function connect(...messages: ServerMessage[]) {
  render(<I18nProvider><TableScreen tableId="t1" /></I18nProvider>);
  act(() => { latest().open(); });
  serve(...messages);
}

const card = (name: string | RegExp) => within(screen.getByRole("group", { name: "Your hand" })).getByRole("button", { name });
const handCards = () => within(screen.getByRole("group", { name: "Your hand" })).getAllByRole("button");

beforeEach(() => {
  vi.useFakeTimers();
  FakeSocket.all = [];
  localStorage.setItem("hearts.token", "tok");
  localStorage.setItem("hearts.lang", "en");
  vi.stubGlobal("WebSocket", FakeSocket);
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ opponents: [] }))));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("connecting", () => {
  it("opens the table's socket with the token", () => {
    connect(snapshot());
    expect(latest().url).toMatch(/\/api\/tables\/t1\/ws\?token=tok$/);
  });
});

describe("seats", () => {
  it("draws you at the bottom and others around you, when you aren't seat 1", () => {
    connect(snapshot({
      seat: 3, table: { ...TABLE, your_seat: 3 },
      view: passView({ seat: 3 }), totals: [1, 2, 3, 4],
    }));
    // Seat 4 is on your left, seat 1 across, seat 2 on your right.
    expect(document.querySelector(".seat.west h2")).toHaveTextContent("Hegel");
    expect(document.querySelector(".seat.north h2")).toHaveTextContent("Ana");
    expect(document.querySelector(".seat.east h2")).toHaveTextContent("Kant");
    expect(screen.getByText("You: 0 this deal, 3 in all")).toBeInTheDocument();
  });

  it("names the bot kinds, and sits people plainly", () => {
    connect(snapshot());
    expect(screen.getByText("Expert, 1986")).toBeInTheDocument();
    expect(screen.getByText("Neural network")).toBeInTheDocument();
  });
});

describe("the pass", () => {
  it("chooses three, sends them, and shows what arrives", () => {
    connect(snapshot());
    const pass = () => screen.getByRole("button", { name: /Choose .* more|Pass these/ });
    expect(pass()).toBeDisabled();
    expect(pass()).toHaveTextContent("Choose 3 more");

    fireEvent.click(card("2 of clubs"));
    fireEvent.click(card("queen of spades"));
    expect(pass()).toHaveTextContent("Choose 1 more");
    fireEvent.click(card("ace of spades"));
    expect(pass()).toHaveTextContent("Pass these to the left");

    // A fourth doesn't fit until one goes back.
    fireEvent.click(card("king of hearts"));
    expect(screen.getByText(/You can pass three/)).toBeInTheDocument();
    expect(card("king of hearts")).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(card("ace of spades"));
    fireEvent.click(card("ace of spades"));

    fireEvent.click(pass());
    expect(latest().sent).toEqual([{ type: "pass", cards: ["C2", "SQ", "SA"] }]);
    // Sent, not yet confirmed: it can't be sent twice.
    expect(screen.queryByRole("button", { name: /Pass these/ })).not.toBeInTheDocument();

    serve({ type: "passed", seq: 3, seat: 1, cards: ["C2", "SQ", "SA"] });
    expect(handCards()).toHaveLength(10);
    expect(screen.getByText(/Passed/)).toBeInTheDocument();

    tick(PACE.passed);
    serve({ type: "received", seq: 4, cards: ["H2", "H4", "H5"] });
    expect(handCards()).toHaveLength(13);
    expect(screen.getByText("You received these from Hegel.")).toBeInTheDocument();
    expect(card("2 of hearts").className).toContain("received");
  });

  it("holds what you received in view before play begins", () => {
    connect(snapshot());
    serve(
      { type: "received", seq: 3, cards: ["H2", "H4", "H5"] },
      { type: "turn", waiting: [1], deadline: null, view: playView({ legal: ["C2"], first_trick: true }) },
    );
    expect(screen.queryByText("Your turn.")).not.toBeInTheDocument();
    tick(PACE.received);
    expect(screen.getByText("Your turn.")).toBeInTheDocument();
  });

  it("offers nothing to choose on a deal with no pass", () => {
    connect(snapshot());
    tick(0);
    serve({ type: "deal", seq: 3, number: 4, direction: null, hands: HAND });
    expect(screen.queryByRole("button", { name: /Choose .* more/ })).not.toBeInTheDocument();
  });
});

describe("playing a card", () => {
  const legalView = () => playView({ legal: ["D3", "D7", "DK"], trick: { leader: 3, cards: ["D9", "DA"] } });
  const myTurn = () => snapshot({
    phase: "play", view: legalView(), waiting: [1],
    trick: { leader: 3, cards: ["D9", "DA"] },
  });

  it("dims illegal cards, with the reason, and won't play them", () => {
    connect(myTurn());
    const queen = card(/queen of spades/);
    expect(queen.className).toContain("dim");
    expect(queen).toHaveAttribute("title", "You must follow diamonds.");
    expect(queen).toHaveAttribute("aria-disabled", "true");
    fireEvent.click(queen);
    fireEvent.click(queen);
    expect(latest().sent).toEqual([]);
    expect(queen).toHaveAttribute("aria-pressed", "false");
    expect(card(/3 of diamonds/).className).not.toContain("dim");
  });

  it("takes legality only from the server's list", () => {
    connect(snapshot({ phase: "play", view: playView({ legal: ["H3"], trick: { leader: 3, cards: ["D9"] } }), waiting: [1] }));
    // Against the rules of hearts with diamonds in hand, but the server's word is final.
    expect(card("3 of hearts").className).not.toContain("dim");
    expect(card(/3 of diamonds/).className).toContain("dim");
  });

  it("plays by tapping twice", () => {
    connect(myTurn());
    fireEvent.click(card("3 of diamonds"));
    expect(card("3 of diamonds")).toHaveAttribute("aria-pressed", "true");
    expect(latest().sent).toEqual([]);
    fireEvent.click(card("3 of diamonds"));
    expect(latest().sent).toEqual([{ type: "play", card: "D3" }]);
  });

  it("plays with the button, naming the card", () => {
    connect(myTurn());
    expect(screen.getByRole("button", { name: "Choose a card" })).toBeDisabled();
    fireEvent.click(card("king of diamonds"));
    fireEvent.click(screen.getByRole("button", { name: "Play the king of diamonds" }));
    expect(latest().sent).toEqual([{ type: "play", card: "DK" }]);
  });

  it("plays by keyboard: arrows move, Enter chooses and plays", () => {
    connect(myTurn());
    const hand = screen.getByRole("group", { name: "Your hand" });
    const cards = handCards();
    cards[0].focus();
    fireEvent.keyDown(hand, { key: "ArrowRight" });
    expect(document.activeElement).toBe(cards[1]);
    fireEvent.keyDown(hand, { key: "End" });
    expect(document.activeElement).toBe(cards[cards.length - 1]);
    fireEvent.keyDown(hand, { key: "Home" });
    expect(document.activeElement).toBe(cards[0]);
    expect(cards.filter((c) => c.tabIndex === 0)).toHaveLength(1);
  });

  it("plays by dragging to the trick", () => {
    connect(myTurn());
    const target = card("3 of diamonds");
    fireEvent.pointerDown(target, { button: 0, clientX: 100, clientY: 500 });
    fireEvent.pointerMove(window, { clientX: 100, clientY: 300 });
    fireEvent.pointerUp(window, { clientX: 100, clientY: 300 });
    expect(latest().sent).toEqual([{ type: "play", card: "D3" }]);
  });

  it("won't drag an illegal card", () => {
    connect(myTurn());
    const target = card(/queen of spades/);
    fireEvent.pointerDown(target, { button: 0, clientX: 100, clientY: 500 });
    fireEvent.pointerMove(window, { clientX: 100, clientY: 300 });
    fireEvent.pointerUp(window, { clientX: 100, clientY: 300 });
    expect(latest().sent).toEqual([]);
  });

  it("shows a refusal plainly and lets you try again", () => {
    connect(myTurn());
    fireEvent.click(card("3 of diamonds"));
    fireEvent.click(card("3 of diamonds"));
    serve({ type: "refused", message: "D3 isn't legal for seat 1" });
    expect(screen.getByRole("alert")).toHaveTextContent("D3 isn't legal for seat 1");
    fireEvent.click(card("3 of diamonds"));
    fireEvent.click(card("3 of diamonds"));
    expect(latest().sent).toHaveLength(2);
  });

  it("reads bot moves one card at a time, and only then your turn", () => {
    connect(snapshot({ phase: "play", view: playView(), waiting: [3] }));
    serve(
      { type: "card", seq: 3, seat: 3, card: "D9" },
      { type: "card", seq: 4, seat: 4, card: "DA" },
      { type: "turn", waiting: [1], deadline: null, view: legalView() },
    );
    const onTrick = () => document.querySelectorAll(".trick .slot:not(.empty)").length;
    expect(onTrick()).toBe(1);
    expect(screen.queryByText("Your turn.")).not.toBeInTheDocument();
    tick(PACE.card);
    expect(onTrick()).toBe(2);
    expect(screen.queryByText("Your turn.")).not.toBeInTheDocument();
    tick(PACE.card);
    expect(screen.getByText("Your turn.")).toBeInTheDocument();
  });
});

describe("the end of a deal and of the game", () => {
  it("shows scores with a review link, then the next deal follows by itself", () => {
    connect(snapshot({ phase: "play", view: playView(), waiting: [] }));
    serve(
      { type: "deal_end", seq: 3, number: 1, scores: [3, 13, 0, 10] },
      { type: "totals", seq: 4, totals: [3, 13, 0, 10] },
      { type: "deal", seq: 5, number: 2, direction: "Across", hands: HAND },
    );
    expect(screen.getByRole("heading", { name: "Deal 1 is over" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review the deal" })).toHaveAttribute("href", "#/table/t1/review/1");
    tick(PACE.dealEnd + 1);
    expect(screen.queryByRole("heading", { name: "Deal 1 is over" })).not.toBeInTheDocument();
    expect(screen.getByText("Deal 2, passing across.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review deal 1" })).toBeInTheDocument();
  });

  it("moves on when you ask", () => {
    connect(snapshot({ phase: "play", view: playView(), waiting: [] }));
    serve(
      { type: "deal_end", seq: 3, number: 1, scores: [3, 13, 0, 10] },
      { type: "totals", seq: 4, totals: [3, 13, 0, 10] },
      { type: "deal", seq: 5, number: 2, direction: "Across", hands: HAND },
    );
    fireEvent.click(screen.getByRole("button", { name: "Next deal" }));
    expect(screen.getByText("Deal 2, passing across.")).toBeInTheDocument();
  });

  it("declares the winners clearly", () => {
    connect(snapshot({ number: 3, phase: "play", view: playView(), waiting: [] }));
    serve(
      { type: "deal_end", seq: 3, number: 3, scores: [3, 13, 0, 10] },
      { type: "totals", seq: 4, totals: [103, 60, 70, 80] },
      { type: "game_end", seq: 5, totals: [103, 60, 70, 80], winners: [2] },
    );
    expect(screen.getByRole("heading", { name: "Game over" })).toBeInTheDocument();
    expect(screen.getByText("Kant won, with 60 points.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review deal 3" })).toBeInTheDocument();
  });
});

describe("reconnecting", () => {
  it("reconnects with backoff and rebuilds from the new snapshot, dropping stale events", () => {
    connect(snapshot({ phase: "play", view: playView(), waiting: [3] }));
    serve(
      { type: "card", seq: 3, seat: 3, card: "D9" },
      { type: "card", seq: 4, seat: 4, card: "DA" },
    );
    act(() => { latest().drop(); });
    expect(screen.getByRole("status")).toHaveTextContent("Reconnecting");
    const before = FakeSocket.all.length;
    tick(BACKOFF_START - 1);
    expect(FakeSocket.all.length).toBe(before);
    tick(1);
    expect(FakeSocket.all.length).toBe(before + 1);
    // Fails again: the wait doubles.
    act(() => { latest().drop(); });
    tick(BACKOFF_START * 2);
    expect(FakeSocket.all.length).toBe(before + 2);

    act(() => { latest().open(); });
    serve(snapshot({
      seq: 9, phase: "play", view: playView({ hand: HAND.slice(1), legal: ["H3"] }), waiting: [1],
      trick: { leader: 2, cards: ["H9"] }, taken: [0, 4, 0, 0],
    }));
    expect(screen.queryByText("Reconnecting")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".trick .slot:not(.empty)")).toHaveLength(1);
    expect(screen.getByText("Your turn.")).toBeInTheDocument();
    tick(PACE.card * 3);
    expect(document.querySelectorAll(".trick .slot:not(.empty)")).toHaveLength(1);
  });

  it("asks for a fresh snapshot when an event is missed", () => {
    connect(snapshot({ phase: "play", view: playView(), waiting: [3] }));
    const before = FakeSocket.all.length;
    serve({ type: "card", seq: 5, seat: 3, card: "D9" });
    expect(FakeSocket.all.length).toBe(before + 1);
    expect(document.querySelectorAll(".trick .slot:not(.empty)")).toHaveLength(0);
  });

  it("ignores events it has already applied", () => {
    connect(snapshot({ seq: 5, phase: "play", view: playView(), waiting: [3] }));
    serve({ type: "card", seq: 5, seat: 3, card: "D9" });
    expect(document.querySelectorAll(".trick .slot:not(.empty)")).toHaveLength(0);
  });
});

describe("the Thoughts window", () => {
  const study = () => ({ table: { ...TABLE, study: true } });

  it("is hidden away from study tables", () => {
    connect(snapshot());
    expect(screen.queryByLabelText("Thoughts")).not.toBeInTheDocument();
  });

  it("quotes the 1986 reasons and rule names verbatim, in French too", () => {
    localStorage.setItem("hearts.lang", "fr");
    connect(snapshot({
      ...study(), phase: "play", view: playView(), waiting: [3], trick: { leader: 3, cards: ["SQ"] },
      thoughts: [{ seat: 3, card: "SQ", thought: { text: "Min - dumping the maggie. Heh, heh.", rule: "dump.queen" } }],
    }));
    expect(screen.getByText("Min - dumping the maggie. Heh, heh.")).toBeInTheDocument();
    expect(screen.getByText("dump.queen")).toBeInTheDocument();
    expect(screen.getByText("Raisonnements sur ce pli")).toBeInTheDocument();
  });

  it("shows advice from your seat, with the network's percentage from its shares", () => {
    connect(snapshot({ ...study(), phase: "play", view: playView({ legal: ["D3", "D7"] }), waiting: [1] }));
    serve({
      type: "advice", seat: 1, number: 1, tricks_done: 0, entries: [
        { kind: "expert", label: "Expert, 1986", answer: "D3", thought: { text: "Leading lowest card.", rule: "lead.lowest" } },
        { kind: "network", label: "Neural network", answer: "D7", thought: { text: "Its preference among the cards. It gives no reasons.", shares: { D3: 0.13, D7: 0.87 } } },
      ],
    });
    expect(screen.getByText("The Expert would play this")).toBeInTheDocument();
    expect(screen.getByText("Leading lowest card.")).toBeInTheDocument();
    expect(screen.getByText("lead.lowest")).toBeInTheDocument();
    expect(screen.getByText("The network would play this")).toBeInTheDocument();
    expect(screen.getByText("Its preference is 87% for this card. It gives no reasons.")).toBeInTheDocument();
  });

  it("ignores advice for another position", () => {
    connect(snapshot({ ...study(), phase: "play", view: playView({ legal: ["D3"] }), waiting: [1] }));
    serve({ type: "advice", seat: 1, number: 1, tricks_done: 5, entries: [{ kind: "expert", label: "Expert", answer: "D3", thought: null }] });
    expect(screen.queryByText("The Expert would play this")).not.toBeInTheDocument();
  });
});

describe("a table waiting for players", () => {
  const open = () => snapshot({
    table: { ...TABLE, status: "open", seats: [TABLE.seats[0], { kind: "person", name: null, open: true }, TABLE.seats[2], TABLE.seats[3]] },
    view: null, number: 0, direction: null, phase: null, waiting: [], trick: null,
  });

  it("says so, and offers the link", () => {
    connect(open());
    expect(screen.getByRole("heading", { name: "Waiting for players" })).toBeInTheDocument();
    expect((screen.getByLabelText(/Send this link/) as HTMLInputElement).value).toContain("#/table/t1");
  });

  it("only offers filling seats when the server has Experts to put in them", () => {
    connect(open());
    expect(screen.queryByRole("button", { name: /Fill the empty seats/ })).not.toBeInTheDocument();
  });
});
