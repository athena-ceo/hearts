// Copyright (c) 2026 Athena Decisions Systems SAS.
// What floats over the table: waiting for players, the end of a deal, the end of the game.
import { seatsFrom } from "../game/seats";
import { fmt, pointsText, useT } from "../i18n";
import { reviewPath, tablePath } from "../route";

export function Scores({ me, values, nameOf }: { me: number | null; values: number[]; nameOf: (seat: number) => string }) {
  return (
    <div className="scores">
      {seatsFrom(me).map((seat) => (
        <div key={seat} className={seat === me ? "me" : undefined}>
          <b>{values[seat - 1]}</b><span>{nameOf(seat)}</span>
        </div>
      ))}
    </div>
  );
}

export function DealEndPanel({ tableId, number, scores, totals, me, nameOf, onNext }: {
  tableId: string; number: number; scores: number[]; totals: number[]; me: number | null;
  nameOf: (seat: number) => string; onNext: () => void;
}) {
  const { t } = useT();
  return (
    <section className="window panel" aria-labelledby="deal-end-title" role="status">
      <h2 id="deal-end-title">{fmt(t.table.dealOver, { n: number })}</h2>
      <div className="body">
        <Scores me={me} values={scores} nameOf={nameOf} />
        <p className="sub">{t.table.inAllSoFar}</p>
        <Scores me={me} values={totals} nameOf={nameOf} />
        <div className="actions">
          <a className="secondary" href={reviewPath(tableId, number)}>{t.table.reviewDeal}</a>
          <button type="button" className="primary" onClick={onNext}>{t.table.nextDeal}</button>
        </div>
      </div>
    </section>
  );
}

export function GameEndPanel({ tableId, totals, winners, lastDeal, me, nameOf }: {
  tableId: string; totals: number[]; winners: number[]; lastDeal: number; me: number | null;
  nameOf: (seat: number) => string;
}) {
  const { t } = useT();
  const youWon = me !== null && winners.includes(me);
  const points = pointsText(t, winners.length ? totals[winners[0] - 1] : 0);
  const names = winners.filter((s) => s !== me).map(nameOf);
  let headline: string;
  if (youWon && names.length) headline = fmt(t.table.youTied, { who: names.join(", "), points });
  else if (youWon) headline = fmt(t.table.youWon, { points });
  else if (names.length > 1) headline = fmt(t.table.theyTied, { who: names.join(", "), points });
  else headline = fmt(t.table.theyWon, { who: names[0] ?? "", points });
  return (
    <section className="window panel game-over" aria-labelledby="game-end-title" role="status">
      <h2 id="game-end-title">{t.table.gameOver}</h2>
      <div className="body">
        <p className="headline">{headline}</p>
        <Scores me={me} values={totals} nameOf={nameOf} />
        <p className="sub">{t.table.reviewAny}</p>
        <div className="deals">
          {Array.from({ length: lastDeal }, (_, i) => i + 1).map((n) => (
            <a key={n} className="secondary" href={reviewPath(tableId, n)} aria-label={fmt(t.table.reviewDealN, { n })}>{n}</a>
          ))}
        </div>
        <div className="actions">
          <a className="primary" href="#/">{t.table.backToLobby}</a>
        </div>
      </div>
    </section>
  );
}

export function WaitingPanel({ tableId, seated, canFill, onFill, error }: {
  tableId: string; seated: boolean; canFill: boolean; onFill: () => void; error: string | null;
}) {
  const { t } = useT();
  const link = `${window.location.origin}${window.location.pathname}${tablePath(tableId)}`;
  return (
    <section className="window panel" aria-labelledby="waiting-title">
      <h2 id="waiting-title">{t.table.waitingTitle}</h2>
      <div className="body">
        <p>{seated ? t.table.waitingBody : t.table.waitingWatch}</p>
        <label htmlFor="table-link" className="sub">{t.table.shareLink}</label>
        <input id="table-link" readOnly value={link} onFocus={(e) => e.target.select()} />
        {error && <p className="error" role="alert">{error}</p>}
        {seated && canFill && (
          <div className="actions">
            <button type="button" className="primary" onClick={onFill}>{t.table.fillNow}</button>
          </div>
        )}
      </div>
    </section>
  );
}
