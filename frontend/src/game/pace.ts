// Copyright (c) 2026 Athena Decisions Systems SAS.
// How long each message holds the table, in milliseconds.
import type { QueuedMessage } from "../types";
import type { Pace } from "./queue";
import type { TableState } from "./reducer";

export const PACE = {
  /** After a card lands, before the next can. */
  card: 800,
  /** Extra time to read a finished trick before it goes. */
  trickHold: 500,
  /** The sweep to the winner. */
  sweep: 550,
  deal: 800,
  passed: 150,
  /** The cards you received, in view before play begins. */
  received: 2400,
  /** The end-of-deal scores stay up this long unless you move on. */
  dealEnd: 9000,
  /** The same, where the clock is short and the next deal shouldn't eat your time. */
  dealEndShort: 3500,
};

const SHORT_LIMIT = 30;

export function paceOf(message: QueuedMessage, state: TableState): Pace {
  switch (message.type) {
    case "card": return { before: 0, after: PACE.card };
    case "trick": return { before: PACE.trickHold, after: PACE.sweep };
    case "passed": return { before: 0, after: PACE.passed };
    case "received": return { before: 0, after: PACE.received };
    case "deal": {
      if (!state.dealEnd) return { before: 0, after: PACE.deal };
      const limit = state.table?.time_limit;
      return { before: limit && limit <= SHORT_LIMIT ? PACE.dealEndShort : PACE.dealEnd, after: PACE.deal };
    }
    default: return { before: 0, after: 0 };
  }
}
