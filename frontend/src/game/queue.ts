// Copyright (c) 2026 Athena Decisions Systems SAS.
// Three bots answering at once still read one card at a time: every message waits its turn here.

export interface Pace { before: number; after: number; }

/** When this many items are waiting, something has fallen behind, and the pace quickens. */
const BACKLOG = 12;
const BACKLOG_SPEED = 0.25;

export class EventQueue<T> {
  private items: T[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;
  private resume: (() => void) | null = null;
  private waited = false;
  private drainUntil = 0;
  private draining = false;
  private destroyed = false;

  constructor(
    private readonly apply: (item: T) => void,
    private readonly pace: (item: T) => Pace,
  ) {}

  get length() { return this.items.length; }

  push(item: T) {
    this.items.push(item);
    this.pump();
  }

  /** Forget everything waiting: a snapshot has replaced it. */
  clear() {
    this.items = [];
    this.waited = false;
    this.cancelWait();
  }

  /**
   * Hurry: apply what's waiting with no pauses, and for `windowMs` more whatever arrives next too. For a
   * reconnection or a tab coming back, when the person isn't watching the cards go by anyway.
   */
  drain(windowMs = 0) {
    this.draining = true;
    this.drainUntil = Date.now() + windowMs;
    this.skip();
  }

  /** Cut the current pause short. */
  skip() {
    if (!this.resume) return;
    const resume = this.resume;
    this.cancelWait();
    resume();
  }

  destroy() {
    this.destroyed = true;
    this.clear();
  }

  private hurrying() {
    if (this.draining && this.items.length === 0 && Date.now() >= this.drainUntil) this.draining = false;
    return this.draining;
  }

  private scaled(ms: number) {
    if (this.hurrying()) return 0;
    return this.items.length >= BACKLOG ? ms * BACKLOG_SPEED : ms;
  }

  private cancelWait() {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.resume = null;
  }

  private wait(ms: number, then: () => void) {
    this.resume = then;
    this.timer = setTimeout(() => {
      this.timer = null;
      this.resume = null;
      then();
    }, ms);
  }

  private pump() {
    while (!this.destroyed && this.timer === null && this.items.length > 0) {
      const head = this.items[0];
      if (!this.waited) {
        const before = this.scaled(this.pace(head).before);
        if (before > 0) {
          this.waited = true;
          this.wait(before, () => this.pump());
          return;
        }
      }
      this.items.shift();
      this.waited = false;
      // Pace is asked for after applying, so it can see the state this item made.
      this.apply(head);
      const after = this.scaled(this.pace(head).after);
      if (after > 0) this.wait(after, () => this.pump());
    }
  }
}
