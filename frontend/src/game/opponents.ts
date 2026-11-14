// Copyright (c) 2026 Athena Decision Systems SAS.
import { useEffect, useState } from "react";

import { api } from "../api";
import type { Dict } from "../i18n";
import type { Opponent } from "../types";

let cached: Opponent[] | null = null;

export function forgetOpponents() { cached = null; }

/** The bots the server offers now. Nothing else may appear in a seat menu. */
export function useOpponents(): { opponents: Opponent[] | null; failed: boolean; retry: () => void } {
  const [opponents, setOpponents] = useState<Opponent[] | null>(cached);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    api.opponents().then((r) => {
      cached = r.opponents;
      if (live) { setOpponents(r.opponents); setFailed(false); }
    }).catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [attempt]);

  return { opponents, failed, retry: () => setAttempt((a) => a + 1) };
}

/** A bot's name in the reader's language, or the server's label for a kind we don't know yet. */
export function kindLabel(t: Dict, kind: string, opponents?: Opponent[] | null): string {
  return (t.kinds as Record<string, string>)[kind]
    ?? opponents?.find((o) => o.kind === kind)?.label
    ?? cached?.find((o) => o.kind === kind)?.label
    ?? kind;
}

/** The same, short enough to sit in a list or a small table. */
export function shortKindLabel(t: Dict, kind: string): string {
  return (t.kindsShort as Record<string, string>)[kind] ?? kindLabel(t, kind);
}
