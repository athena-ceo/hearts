// Copyright (c) 2026 Athena Decisions Systems SAS.
// A table's live connection, reconnecting by itself with backoff. Each new connection opens with a snapshot.
import type { ServerMessage } from "../types";

export type ConnectionStatus = "connecting" | "open" | "reconnecting" | "closed";

export const BACKOFF_START = 500;
export const BACKOFF_MAX = 15000;

interface Handlers {
  onMessage: (message: ServerMessage) => void;
  onStatus: (status: ConnectionStatus) => void;
  /** A connection failed without ever opening: the table or the token may be gone. */
  onRefused?: () => void;
}

export class TableSocket {
  private socket: WebSocket | null = null;
  private retry: ReturnType<typeof setTimeout> | null = null;
  private attempts = 0;
  private closed = false;

  constructor(private readonly url: () => string | null, private readonly handlers: Handlers) {
    this.connect();
  }

  send(message: unknown): boolean {
    if (this.socket?.readyState !== WebSocket.OPEN) return false;
    this.socket.send(JSON.stringify(message));
    return true;
  }

  /** Drop this connection and open another at once. */
  reconnect() {
    if (this.closed) return;
    this.detach();
    this.attempts = 0;
    this.connect();
  }

  close() {
    this.closed = true;
    if (this.retry !== null) clearTimeout(this.retry);
    this.detach();
    this.handlers.onStatus("closed");
  }

  private detach() {
    const socket = this.socket;
    this.socket = null;
    if (!socket) return;
    socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null;
    socket.close();
  }

  private connect() {
    const url = this.url();
    if (url === null) return;
    this.handlers.onStatus(this.attempts === 0 ? "connecting" : "reconnecting");
    const socket = new WebSocket(url);
    this.socket = socket;
    let opened = false;
    socket.onopen = () => {
      opened = true;
      this.attempts = 0;
      this.handlers.onStatus("open");
    };
    socket.onmessage = (event) => {
      this.handlers.onMessage(JSON.parse(event.data as string) as ServerMessage);
    };
    socket.onclose = () => {
      if (this.socket !== socket) return;
      this.socket = null;
      if (!opened) this.handlers.onRefused?.();
      this.scheduleRetry();
    };
  }

  private scheduleRetry() {
    if (this.closed) return;
    const delay = Math.min(BACKOFF_MAX, BACKOFF_START * 2 ** this.attempts);
    this.attempts += 1;
    this.handlers.onStatus("reconnecting");
    this.retry = setTimeout(() => {
      this.retry = null;
      if (!this.closed) this.connect();
    }, delay);
  }
}
