// Copyright (c) 2026 Athena Decisions Systems SAS.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EventQueue, type Pace } from "./queue";

const FLAT: Pace = { before: 0, after: 100 };

function queueOf(pace: (item: string) => Pace = () => FLAT) {
  const applied: string[] = [];
  const queue = new EventQueue<string>((item) => applied.push(item), pace);
  return { queue, applied };
}

describe("EventQueue", () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); });

  it("applies the first item at once and paces the rest one at a time", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    queue.push("b");
    queue.push("c");
    expect(applied).toEqual(["a"]);
    vi.advanceTimersByTime(99);
    expect(applied).toEqual(["a"]);
    vi.advanceTimersByTime(1);
    expect(applied).toEqual(["a", "b"]);
    vi.advanceTimersByTime(100);
    expect(applied).toEqual(["a", "b", "c"]);
  });

  it("waits before an item that asks to, even when the queue was idle", () => {
    const { queue, applied } = queueOf(() => ({ before: 50, after: 0 }));
    queue.push("a");
    expect(applied).toEqual([]);
    vi.advanceTimersByTime(50);
    expect(applied).toEqual(["a"]);
  });

  it("passes items with no pause straight through", () => {
    const { queue, applied } = queueOf(() => ({ before: 0, after: 0 }));
    queue.push("a");
    queue.push("b");
    expect(applied).toEqual(["a", "b"]);
  });

  it("keeps the order when items arrive during a pause", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    vi.advanceTimersByTime(50);
    queue.push("b");
    vi.advanceTimersByTime(50);
    queue.push("c");
    vi.advanceTimersByTime(100);
    expect(applied).toEqual(["a", "b", "c"]);
  });

  it("clear forgets what's waiting and cancels the pause", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    queue.push("b");
    queue.clear();
    vi.advanceTimersByTime(1000);
    expect(applied).toEqual(["a"]);
    expect(queue.length).toBe(0);
    queue.push("c");
    expect(applied).toEqual(["a", "c"]);
  });

  it("drain applies everything waiting at once", () => {
    const { queue, applied } = queueOf();
    for (const item of ["a", "b", "c", "d"]) queue.push(item);
    queue.drain();
    expect(applied).toEqual(["a", "b", "c", "d"]);
  });

  it("drain with a window also hurries what arrives during it, then the pace returns", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    queue.drain(500);
    queue.push("b");
    queue.push("c");
    expect(applied).toEqual(["a", "b", "c"]);
    vi.advanceTimersByTime(501);
    queue.push("d");
    queue.push("e");
    expect(applied).toEqual(["a", "b", "c", "d"]);
    vi.advanceTimersByTime(100);
    expect(applied).toEqual(["a", "b", "c", "d", "e"]);
  });

  it("speeds up by itself when a backlog builds", () => {
    const { queue, applied } = queueOf();
    for (let i = 0; i < 20; i++) queue.push(`${i}`);
    expect(applied).toEqual(["0"]);
    vi.advanceTimersByTime(100);
    expect(applied.length).toBe(2);
    vi.advanceTimersByTime(25);
    expect(applied.length).toBe(3);
  });

  it("skip ends the current pause only", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    queue.push("b");
    queue.push("c");
    queue.skip();
    expect(applied).toEqual(["a", "b"]);
    vi.advanceTimersByTime(100);
    expect(applied).toEqual(["a", "b", "c"]);
  });

  it("does nothing after being destroyed", () => {
    const { queue, applied } = queueOf();
    queue.push("a");
    queue.push("b");
    queue.destroy();
    vi.advanceTimersByTime(1000);
    queue.push("c");
    expect(applied).toEqual(["a"]);
  });
});
