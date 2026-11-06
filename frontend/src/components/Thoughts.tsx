// Copyright (c) 2026 Athena Decisions Systems SAS.
// The Thoughts window. The reasons and rule names are quoted exactly as the server sends them: they're the 1986
// Expert's own words and are never translated.
import type { TableState } from "../game/reducer";
import { fmt, useT, type Dict } from "../i18n";
import type { AdviceEntry, Thought } from "../types";
import { Card } from "./Card";

export function percent(share: number): string {
  return `${Math.round(share * 100)}%`;
}

function preference(t: Dict, thought: Thought | null | undefined, card: string): string | null {
  const share = thought?.shares?.[card];
  return share === undefined ? null : fmt(t.thoughts.preference, { pct: percent(share) });
}

function ThoughtLines({ thought, card }: { thought?: Thought | null; card: string }) {
  const { t } = useT();
  const pref = preference(t, thought, card);
  return (
    <>
      {pref
        ? <p className="said">{pref}</p>
        : thought?.text ? <p className="said">{thought.text}</p> : null}
      {thought?.rule && <p className="code">{thought.rule}</p>}
    </>
  );
}

function wouldPlay(t: Dict, entry: AdviceEntry): string {
  const passing = Array.isArray(entry.answer);
  if (entry.kind === "expert") return passing ? t.thoughts.expertPasses : t.thoughts.expertPlays;
  if (entry.kind === "network") return passing ? t.thoughts.networkPasses : t.thoughts.networkPlays;
  return fmt(passing ? t.thoughts.otherPasses : t.thoughts.otherPlays, { who: entry.label });
}

function AdviceRow({ entry }: { entry: AdviceEntry }) {
  const { t } = useT();
  if (Array.isArray(entry.answer)) {
    return (
      <div className="why many">
        <p className="who">{wouldPlay(t, entry)}</p>
        <div className="cards">{entry.answer.map((c) => <Card key={c} code={c} small />)}</div>
        {entry.kind === "network"
          ? <p className="said">{t.thoughts.networkNoReasons}</p>
          : <ThoughtLines thought={entry.thought} card="" />}
      </div>
    );
  }
  return (
    <div className="why">
      <Card code={entry.answer} small />
      <p className="who">{wouldPlay(t, entry)}</p>
      <ThoughtLines thought={entry.thought} card={entry.answer} />
    </div>
  );
}

export function Thoughts({ state, nameOf, kindOf }: {
  state: TableState;
  nameOf: (seat: number) => string;
  kindOf: (seat: number) => string | null;
}) {
  const { t } = useT();
  const { advice, seat, number, tricksDone } = state;
  const showAdvice = advice && seat && advice.seat === seat && advice.number === number
    && advice.tricks_done === tricksDone && state.waiting.includes(seat);
  const yourTurn = seat !== null && state.waiting.includes(seat) && Boolean(state.view?.legal?.length || state.phase === "pass");
  let adviceMessage = t.thoughts.adviceWaits;
  if (yourTurn) adviceMessage = state.adviceExpected ? t.thoughts.adviceComing : t.thoughts.adviceMissed;
  return (
    <aside className="window thoughts" aria-label={t.thoughts.label}>
      <h2 className="title">{state.thoughtsFromLastTrick ? t.thoughts.lastTrick : t.thoughts.thisTrick}</h2>
      <div aria-live="polite">
        {state.thoughts.length === 0 && <p className="empty">{t.thoughts.none}</p>}
        {state.thoughts.map((entry) => (
          <div className="why" key={entry.card}>
            <Card code={entry.card} small />
            <p className="who">
              {nameOf(entry.seat)}
              {kindOf(entry.seat) && <span> {kindOf(entry.seat)}</span>}
            </p>
            <ThoughtLines thought={entry.thought} card={entry.card} />
          </div>
        ))}
      </div>
      {seat && !state.gameEnd && <h3>{t.thoughts.fromYourSeat}</h3>}
      {seat && !state.gameEnd && (showAdvice
        ? advice.entries.map((entry) => <AdviceRow key={entry.kind} entry={entry} />)
        : <p className="empty">{adviceMessage}</p>)}
    </aside>
  );
}
