// Copyright (c) 2026 Athena Decisions Systems SAS.
import { useEffect, useState, type ReactNode } from "react";

import { api, ApiError } from "../api";
import { fmt, pointsText, useT, type Dict } from "../i18n";
import type { DealReview, ReviewAdvice, ReviewDecision, TableInfo, Thought } from "../types";
import { Card, InlineCard } from "./Card";
import { Scores } from "./Panels";
import { percent } from "./Thoughts";
import { directionText } from "./TableScreen";

const MOON = -26;

/** Only what the data shows: a score, and a moon only where the score says one was shot. */
export function headline(t: Dict, review: DealReview, me: number | null): string[] {
  if (!me) return [fmt(t.review.dealHeading, { n: review.number })];
  const yours = review.scores[me - 1];
  const lines = [yours === MOON ? t.review.youShot : fmt(t.review.youTook, { points: pointsText(t, yours) })];
  if (review.what_if) {
    const theirs = review.what_if.scores[me - 1];
    lines.push(theirs === MOON ? t.review.networkShot : fmt(t.review.networkTook, { n: theirs }));
  }
  return lines;
}

function sameCards(a: string | string[], b: string | string[]): boolean {
  const list = (x: string | string[]) => (Array.isArray(x) ? [...x].sort() : [x]);
  return list(a).join() === list(b).join();
}

function share(advice: ReviewAdvice | undefined): string | null {
  if (!advice || Array.isArray(advice.answer)) return null;
  const value = advice.thought?.shares?.[advice.answer];
  return value === undefined ? null : percent(value);
}

function ThoughtQuote({ thought }: { thought: Thought | null | undefined }) {
  if (!thought?.text) return null;
  return (
    <>
      {" "}{thought.text}
      {thought.rule && <span className="code block">{thought.rule}</span>}
    </>
  );
}

function YourColumn({ decision, advice }: { decision: ReviewDecision; advice: ReviewAdvice | undefined }) {
  const { t } = useT();
  const colon = t.common.colon;
  const you = decision.you;
  if (Array.isArray(you)) return null;
  const inline = <InlineCard code={you} />;
  // The review's reason is the Expert's for its own choice, so it's only ever shown as that.
  if (advice && !Array.isArray(advice.answer)) {
    if (advice.answer === you) return <>{inline}{colon}<ThoughtQuote thought={advice.thought} /></>;
    return (
      <>
        {inline}. {t.review.expertInstead} <InlineCard code={advice.answer} />{colon}
        <ThoughtQuote thought={advice.thought} />
      </>
    );
  }
  return <>{inline}{decision.thought?.text ? <>{colon}<ThoughtQuote thought={decision.thought} /></> : null}</>;
}

function NetworkColumn({ you, advice }: { you: string | string[]; advice: ReviewAdvice | undefined }) {
  const { t } = useT();
  if (!advice) return <span className="same">{t.review.noAdvice}</span>;
  const pct = share(advice);
  if (sameCards(you, advice.answer)) {
    return <span className="same">{pct ? fmt(t.review.sameCardPct, { pct }) : t.review.sameCard}</span>;
  }
  return (
    <div className="pick">
      <div className="cards">
        {(Array.isArray(advice.answer) ? advice.answer : [advice.answer]).map((c) => <Card key={c} code={c} small />)}
      </div>
      {pct && <span className="pct">{pct}</span>}
    </div>
  );
}

function Row({ label, split, played, said, network }: { label: ReactNode; split: boolean; played: ReactNode; said: ReactNode; network: ReactNode }) {
  return (
    <tr className={split ? "split" : undefined}>
      <th scope="row">{label}</th>
      <td>{played}</td>
      <td className="said">{said}</td>
      <td>{network}</td>
    </tr>
  );
}

export function ReviewTable({ review, me }: { review: DealReview; me: number | null }) {
  const { t } = useT();
  const passDecision = review.decisions.find((d) => d.decision === "pass");
  return (
    <div>
      <p className="table-title" id="decisions-title">{t.review.caption}</p>
      <div className="wrap">
      <table aria-labelledby="decisions-title">
        <thead>
          <tr>
            <th scope="col">{t.review.trick}</th>
            <th scope="col">{t.review.played}</th>
            <th scope="col">{t.review.youColumn}</th>
            <th scope="col">{t.review.networkColumn}</th>
          </tr>
        </thead>
        <tbody>
          {passDecision && Array.isArray(passDecision.you) && (
            <Row label={t.review.pass}
              split={Boolean(passDecision.advice.network) && !sameCards(passDecision.you, passDecision.advice.network!.answer)}
              played={<div className="cards">{passDecision.you.map((c) => <Card key={c} code={c} small />)}</div>}
              said={fmt(t.review.passedThese, { direction: directionText(t, review.direction) })}
              network={<NetworkColumn you={passDecision.you} advice={passDecision.advice.network} />} />
          )}
          {review.tricks.map((trick, index) => {
            const number = index + 1;
            const winnerAt = ((trick.winner - trick.leader) % 4 + 4) % 4;
            const decision = review.decisions.find((d) => d.decision === "play" && d.trick === number);
            const yourAt = me ? ((me - trick.leader) % 4 + 4) % 4 : -1;
            const yours = yourAt >= 0 ? trick.cards[yourAt] : null;
            const network = decision?.advice.network;
            return (
              <Row key={number} label={number}
                split={Boolean(decision && network && !sameCards(decision.you, network.answer))}
                played={(
                  <div className="cards">
                    {trick.cards.map((c, i) => (
                      <span key={c} className={i === winnerAt ? "winner" : undefined}><Card code={c} small /></span>
                    ))}
                  </div>
                )}
                said={decision
                  ? <YourColumn decision={decision} advice={decision.advice.expert} />
                  : yours ? <><InlineCard code={yours} />{t.common.colon} <span className="same">{t.review.onlyCard}</span></> : null}
                network={decision
                  ? <NetworkColumn you={decision.you} advice={network} />
                  : <span className="same">{yours ? t.review.noChoice : ""}</span>} />
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}

export function Review({ tableId, number }: { tableId: string; number: number }) {
  const { t } = useT();
  const [review, setReview] = useState<DealReview | null>(null);
  const [table, setTable] = useState<TableInfo | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    Promise.all([api.review(tableId, number), api.table(tableId)])
      .then(([r, info]) => { if (live) { setReview(r); setTable(info); } })
      .catch((e) => {
        if (!live) return;
        setError(e instanceof ApiError ? e.message : t.common.unreachable);
      });
    return () => { live = false; };
    // eslint-disable-next-line
  }, [tableId, number]);

  if (error) return <main className="message-page"><p>{error}</p><a className="primary" href={`#/table/${tableId}`}>{t.nav.backToTable}</a></main>;
  if (!review || !table) return <main className="message-page"><p>{t.review.working}</p></main>;

  const me = table.your_seat;
  const nameOf = (seat: number) => (seat === me ? t.common.you : table.seats[seat - 1]?.name ?? "");
  const whatIf = review.what_if;
  const whatIfName = (seat: number) => (seat === me ? t.review.networkShort : table.seats[seat - 1]?.name ?? "");

  return (
    <main className="review">
      <p className="eyebrow">{fmt(t.review.dealHeading, { n: review.number })}</p>
      <h1>{headline(t, review, me).join(" ")}</h1>
      <div className={`outcome${whatIf ? "" : " single"}`}>
        <section className="window" aria-labelledby="yours">
          <h2 id="yours">{t.review.asPlayed}</h2>
          <div className="body"><Scores me={me} values={review.scores} nameOf={nameOf} /></div>
        </section>
        {whatIf && (
          <section className="window" aria-labelledby="theirs">
            <h2 id="theirs">{t.review.withNetwork}</h2>
            <div className="body"><Scores me={me} values={whatIf.scores} nameOf={whatIfName} /></div>
          </section>
        )}
      </div>
      <ReviewTable review={review} me={me} />
      <p className="foot">{t.review.footNetwork}</p>
      {whatIf && <p className="foot">{t.review.footWhatIf}</p>}
    </main>
  );
}

