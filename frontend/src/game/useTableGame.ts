// Copyright (c) 2026 Athena Decisions Systems SAS.
// One table: its socket, its event queue, and the state they build.
import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError, authToken, tableSocketUrl } from "../api";
import type { QueuedMessage, ServerMessage, SnapshotMessage } from "../types";
import { paceOf } from "./pace";
import { EventQueue } from "./queue";
import { canPass, canPlay, initialState, reduce, type Action, type TableState } from "./reducer";
import { TableSocket, type ConnectionStatus } from "./socket";

/** After a reconnection, what arrives in this window is applied without the usual pauses. */
const RECONNECT_DRAIN = 1500;

export type Before = (action: Action, state: TableState) => void;

export function useTableGame(tableId: string, before?: Before) {
  const [state, setState] = useState<TableState>(initialState);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [gone, setGone] = useState(false);
  const stateRef = useRef(state);
  const beforeRef = useRef(before);
  beforeRef.current = before;
  const socketRef = useRef<TableSocket | null>(null);
  const queueRef = useRef<EventQueue<QueuedMessage> | null>(null);

  const apply = useCallback((action: Action) => {
    beforeRef.current?.(action, stateRef.current);
    stateRef.current = reduce(stateRef.current, action);
    setState(stateRef.current);
  }, []);

  useEffect(() => {
    stateRef.current = initialState;
    setState(initialState);
    setGone(false);
    let live = true;
    let lastSeq = -1;
    let connections = 0;
    let awaitingFirstSnapshot = false;

    const queue = new EventQueue<QueuedMessage>(apply, (item) => paceOf(item, stateRef.current));
    queueRef.current = queue;

    const refreshSeats = () => {
      // A table filled by its timer announces no new seats, so ask, or they'd read as empty all game.
      if (stateRef.current.table?.seats.some((s) => s.open)) {
        api.table(tableId).then((table) => { if (live) apply({ type: "table-info", table }); }).catch(() => {});
      }
    };

    const onSnapshot = (message: SnapshotMessage) => {
      const reconnected = awaitingFirstSnapshot && connections > 1;
      awaitingFirstSnapshot = false;
      queue.clear();
      lastSeq = message.seq;
      apply(message);
      if (reconnected) queue.drain(RECONNECT_DRAIN);
    };

    const onMessage = (message: ServerMessage) => {
      switch (message.type) {
        case "snapshot":
          onSnapshot(message);
          return;
        case "refused":
        case "error":
          apply(message);
          return;
        case "turn":
        case "advice":
          queue.push(message);
          return;
        default:
          if (message.seq <= lastSeq) return;
          if (lastSeq >= 0 && message.seq > lastSeq + 1) {
            // We missed something: a fresh snapshot is the whole truth.
            socket.reconnect();
            return;
          }
          lastSeq = message.seq;
          if (message.type === "game" || message.type === "deal") refreshSeats();
          queue.push(message);
      }
    };

    const socket = new TableSocket(() => {
      const token = authToken();
      if (!token) return null;
      connections += 1;
      awaitingFirstSnapshot = true;
      return tableSocketUrl(tableId, token);
    }, {
      onMessage,
      onStatus: (s) => { if (live) setStatus(s); },
      onRefused: () => {
        // A server refusing a socket looks like any dropped connection, so ask over HTTP why.
        api.table(tableId).catch((e) => {
          if (live && e instanceof ApiError && e.status === 404) {
            setGone(true);
            socket.close();
          }
        });
      },
    });
    socketRef.current = socket;

    const onVisible = () => { if (!document.hidden) queue.drain(); };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      live = false;
      document.removeEventListener("visibilitychange", onVisible);
      socket.close();
      queue.destroy();
      socketRef.current = null;
      queueRef.current = null;
    };
  }, [tableId, apply]);

  const play = useCallback((card: string) => {
    if (!canPlay(stateRef.current) || !stateRef.current.view?.legal?.includes(card)) return false;
    if (!socketRef.current?.send({ type: "play", card })) return false;
    apply({ type: "sent-play", card });
    return true;
  }, [apply]);

  const pass = useCallback((cards: string[]) => {
    if (!canPass(stateRef.current)) return false;
    if (!socketRef.current?.send({ type: "pass", cards })) return false;
    apply({ type: "sent-pass", cards });
    return true;
  }, [apply]);

  const nextDeal = useCallback(() => {
    apply({ type: "dismiss-deal-end" });
    queueRef.current?.skip();
  }, [apply]);

  const reconnect = useCallback(() => socketRef.current?.reconnect(), []);

  return { state, status, gone, play, pass, nextDeal, reconnect };
}
