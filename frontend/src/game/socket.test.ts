// Copyright (c) 2026 Athena Decisions Systems SAS.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BACKOFF_MAX, BACKOFF_START, TableSocket, type ConnectionStatus } from "./socket";

class FakeSocket {
  static OPEN = 1;
  static all: FakeSocket[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onmessage: unknown = null;
  onclose: (() => void) | null = null;
  onerror: unknown = null;
  sent: string[] = [];
  constructor(readonly url: string) { FakeSocket.all.push(this); }
  send(data: string) { this.sent.push(data); }
  close() { this.readyState = 3; }
  open() { this.readyState = 1; this.onopen?.(); }
  drop() { this.readyState = 3; this.onclose?.(); }
}

const latest = () => FakeSocket.all[FakeSocket.all.length - 1];

describe("TableSocket", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    FakeSocket.all = [];
    vi.stubGlobal("WebSocket", FakeSocket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const make = () => {
    const statuses: ConnectionStatus[] = [];
    const onRefused = vi.fn();
    const socket = new TableSocket(() => "ws://x", { onMessage: () => {}, onStatus: (s) => statuses.push(s), onRefused });
    return { socket, statuses, onRefused };
  };

  it("doubles its wait up to a ceiling, and resets once connected", () => {
    make();
    const waits: number[] = [];
    for (let i = 0; i < 8; i++) {
      latest().drop();
      const count = FakeSocket.all.length;
      let waited = 0;
      while (FakeSocket.all.length === count) { vi.advanceTimersByTime(100); waited += 100; }
      waits.push(waited);
    }
    expect(waits.slice(0, 3)).toEqual([BACKOFF_START, BACKOFF_START * 2, BACKOFF_START * 4]);
    expect(waits[waits.length - 1]).toBe(BACKOFF_MAX);
    latest().open();
    latest().drop();
    vi.advanceTimersByTime(BACKOFF_START);
    latest().open();
    expect(FakeSocket.all.length).toBeGreaterThan(8);
  });

  it("reports a socket refused before opening", () => {
    const { onRefused } = make();
    latest().drop();
    expect(onRefused).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(BACKOFF_START);
    latest().open();
    latest().drop();
    expect(onRefused).toHaveBeenCalledTimes(1);
  });

  it("won't send while closed", () => {
    const { socket } = make();
    expect(socket.send({ a: 1 })).toBe(false);
    latest().open();
    expect(socket.send({ a: 1 })).toBe(true);
    expect(latest().sent).toEqual(['{"a":1}']);
  });

  it("stops for good when closed", () => {
    const { socket, statuses } = make();
    latest().open();
    socket.close();
    const count = FakeSocket.all.length;
    vi.advanceTimersByTime(BACKOFF_MAX * 2);
    expect(FakeSocket.all.length).toBe(count);
    expect(statuses[statuses.length - 1]).toBe("closed");
  });
});
