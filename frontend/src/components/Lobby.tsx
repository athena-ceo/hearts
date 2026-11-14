// Copyright (c) 2026 Athena Decision Systems SAS.
import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError } from "../api";
import { kindLabel, shortKindLabel, useOpponents } from "../game/opponents";
import { fmt, useT, type Dict } from "../i18n";
import { go, tablePath } from "../route";
import type { Opponent, SeatInfo, TableInfo } from "../types";

const POLL_MS = 4000;
const FILL_AFTER_SECONDS = 30;
const TIME_LIMITS = [30, 90, 86400];

// Strongest first, for choosing who to seat by default.
const PREFERRED = ["expert", "network", "conservative", "clown"];

/** The mockup's table where the server has those players, and otherwise the best it has. */
export function defaultSeats(opponents: Opponent[]): string[] {
  const kinds = opponents.map((o) => o.kind);
  const ranked = [...PREFERRED.filter((k) => kinds.includes(k)), ...kinds.filter((k) => !PREFERRED.includes(k))];
  const best = ranked[0] ?? "person";
  const second = ranked[1] ?? best;
  // Without an Expert to fill the seat, an open seat could wait for ever.
  return [kinds.includes("expert") ? "person" : second, best, second];
}

export function moveTime(t: Dict, seconds: number | null): string {
  if (!seconds) return t.lobby.noLimit;
  if (seconds >= 86400) return t.lobby.aDayAMove;
  if (seconds >= 3600) return fmt(t.lobby.hoursAMove, { n: Math.round(seconds / 3600) });
  if (seconds >= 120) return fmt(t.lobby.minutesAMove, { n: Math.round(seconds / 60) });
  return fmt(t.lobby.secondsAMove, { n: seconds });
}

/** Players a Medley offers to everyone, for one game at a time: they come and go. */
const isOffered = (kind: string) => kind.startsWith("medley:");

function StartGame({ opponents, refresh }: { opponents: Opponent[]; refresh: () => void }) {
  const { t } = useT();
  const [seats, setSeats] = useState<string[]>(() => defaultSeats(opponents));
  const [fill, setFill] = useState(true);
  const [study, setStudy] = useState(false);
  const [limit, setLimit] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const expertOffered = opponents.some((o) => o.kind === "expert");
  const someoneToFind = seats.includes("person");

  const setSeat = (index: number, kind: string) => setSeats((s) => s.map((old, i) => (i === index ? kind : old)));

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const table = await api.createTable({
        seats, study, invite_only: false, time_limit: limit,
        fill_after: someoneToFind && expertOffered && fill ? FILL_AFTER_SECONDS : null,
      });
      go(tablePath(table.id));
    } catch (e) {
      if (seats.some(isOffered) && e instanceof ApiError && e.status === 400) {
        // Someone took the Medley's players first: show who can be chosen now.
        setError(t.lobby.medleyTaken);
        setSeats((s) => s.map((kind, i) => (isOffered(kind) ? defaultSeats(opponents.filter((o) => !isOffered(o.kind)))[i] : kind)));
        refresh();
      } else {
        setError(e instanceof Error ? e.message : t.common.unreachable);
      }
      setBusy(false);
    }
  };

  const menu = (id: string, label: string, index: number, area: string) => (
    <div className={area}>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={seats[index]} onChange={(e) => setSeat(index, e.target.value)}>
        <option value="person">{t.lobby.findPerson}</option>
        {opponents.map((o) => <option key={o.kind} value={o.kind}>{kindLabel(t, o.kind, opponents)}</option>)}
      </select>
    </div>
  );

  return (
    <div className="body start-body">
      <div className="seats">
        {menu("seat-across", t.lobby.across, 1, "n")}
        {menu("seat-left", t.lobby.left, 0, "w")}
        <div className="t" aria-hidden="true" />
        {menu("seat-right", t.lobby.right, 2, "e")}
        <div className="s"><p>{t.common.you}</p></div>
      </div>
      <div className="choices">
        <button type="button" className="primary" onClick={start} disabled={busy}>{t.lobby.dealMeIn}</button>
        {error && <p className="error" role="alert">{error}</p>}
        {expertOffered && someoneToFind && (
          <label className="check">
            <input type="checkbox" checked={fill} onChange={(e) => setFill(e.target.checked)} />
            {t.lobby.fillWithExpert}
          </label>
        )}
        <label className="check">
          <input type="checkbox" checked={study} onChange={(e) => setStudy(e.target.checked)} />
          {t.lobby.studyTable}
        </label>
        <div>
          <label htmlFor="time-limit">{t.lobby.timeLimit}</label>
          <select id="time-limit" value={limit ?? ""} onChange={(e) => setLimit(e.target.value ? Number(e.target.value) : null)}>
            <option value="">{t.lobby.noLimit}</option>
            {TIME_LIMITS.map((s) => <option key={s} value={s}>{moveTime(t, s)}</option>)}
          </select>
        </div>
      </div>
    </div>
  );
}

function Strength({ opponents }: { opponents: Opponent[] }) {
  const { t } = useT();
  const known = t.strength.rows as Record<string, { how: string; points: string }>;
  const order = Object.keys(known);
  const rows = opponents.filter((o) => !isOffered(o.kind)).sort((a, b) => {
    const rank = (o: Opponent) => { const i = order.indexOf(o.kind); return i < 0 ? order.length : i; };
    return rank(a) - rank(b);
  });
  return (
    <div className="body strength">
      <h3>{t.strength.title}</h3>
      <p className="how">{t.strength.how}</p>
      <table>
        <thead>
          <tr><th scope="col">{t.strength.opponent}</th><th scope="col">{t.strength.plays}</th><th scope="col" className="num">{t.strength.points}</th></tr>
        </thead>
        <tbody>
          {rows.map((o) => (
            <tr key={o.kind}>
              <td>{kindLabel(t, o.kind, opponents)}</td>
              <td>{known[o.kind]?.how ?? ""}</td>
              <td className="num">{known[o.kind]?.points ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function seatLabel(t: Dict, seat: SeatInfo): string {
  return seat.kind === "person" ? (seat.name ?? t.lobby.openSeat) : shortKindLabel(t, seat.kind);
}

function GameRow({ table }: { table: TableInfo }) {
  const { t } = useT();
  const others = table.seats
    .filter((s, i) => i + 1 !== table.your_seat && !s.open)
    .map((s) => seatLabel(t, s));
  const you = table.your_seat ? table.totals[table.your_seat - 1] : 0;
  const lowest = Math.min(...table.totals);
  const scores = { deal: table.deal, you, lowest };
  const openSeats = table.seats.filter((s) => s.open).length;

  let state: string;
  if (table.status === "open") state = fmt(openSeats === 1 ? t.lobby.waitingOne : t.lobby.waitingMany, { n: openSeats });
  else if (table.status === "finished") state = fmt(t.lobby.finished, scores);
  else if (table.status === "failed") state = t.lobby.failed;
  else if (table.your_turn) state = fmt(t.lobby.yourTurn, scores);
  else if (table.waiting_for.length) state = fmt(t.lobby.waitingFor, { ...scores, who: table.waiting_for.join(", ") });
  else state = fmt(t.lobby.playing, scores);

  const study = table.study ? ` ${t.lobby.studySuffix}` : "";
  const who = others.length ? fmt(t.lobby.withPlayers, { who: others.join(", ") }) : t.lobby.withNobody;
  return (
    <div className={`game${table.your_turn ? " turn" : ""}`}>
      <p className="who">{who}{study}</p>
      <a className={`${table.your_turn ? "primary" : "secondary"} go`} href={tablePath(table.id)}>
        {table.your_turn ? t.lobby.play : t.lobby.open}
      </a>
      <p className="state">{state}</p>
    </div>
  );
}

function statusRank(table: TableInfo): number {
  if (table.your_turn) return 0;
  if (table.status === "playing") return 1;
  if (table.status === "open") return 2;
  return 3;
}

const MINI_AREA = ["s", "w", "n", "e"];

function MiniTable({ table, onSit, busy }: { table: TableInfo; onSit: (table: TableInfo, seat: number) => void; busy: boolean }) {
  const { t } = useT();
  const people = table.seats.filter((s) => s.kind === "person" && s.name).map((s) => s.name!);
  const whose = people.length
    ? fmt(t.lobby.sitAtTable, { who: people.join(", ") })
    : t.lobby.sitHere;
  return (
    <div className="mini">
      <div className="grid">
        <span className="c" aria-hidden="true" />
        {table.seats.map((seat, i) => seat.open ? (
          <button key={i} type="button" className={`${MINI_AREA[i]} sit`} aria-label={whose} disabled={busy} onClick={() => onSit(table, i + 1)}>
            {t.lobby.sitHere}
          </button>
        ) : (
          <span key={i} className={`${MINI_AREA[i]} ${seat.kind === "person" ? "person" : "bot"}`}>{seatLabel(t, seat)}</span>
        ))}
      </div>
      <p>{table.study ? t.lobby.studyUnrated : moveTime(t, table.time_limit)}</p>
    </div>
  );
}

export function Lobby({ scrollToGames }: { scrollToGames: boolean }) {
  const { t } = useT();
  const { opponents, failed, retry } = useOpponents();
  const [tables, setTables] = useState<TableInfo[] | null>(null);
  const [unreachable, setUnreachable] = useState(false);
  const [sitError, setSitError] = useState<string | null>(null);
  const [sitting, setSitting] = useState(false);
  const games = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    api.tables().then((r) => { setTables(r.tables); setUnreachable(false); })
      .catch((e) => { if (!(e instanceof ApiError && e.status === 401)) setUnreachable(true); });
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(() => { if (!document.hidden) load(); }, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    if (scrollToGames) games.current?.scrollIntoView?.({ block: "start" });
  }, [scrollToGames, tables !== null]); // eslint-disable-line

  const sit = async (table: TableInfo, seat: number) => {
    setSitting(true);
    setSitError(null);
    try {
      await api.join(table.id, seat);
      go(tablePath(table.id));
    } catch (e) {
      setSitError(e instanceof Error ? e.message : t.common.unreachable);
      setSitting(false);
      load();
    }
  };

  const mine = (tables ?? []).filter((x) => x.your_seat).sort((a, b) => statusRank(a) - statusRank(b));
  const open = (tables ?? []).filter((x) => !x.your_seat && x.status === "open");

  return (
    <main className="lobby">
      <h1>{t.lobby.heading}</h1>
      <section className="window start" aria-labelledby="start-title">
        <h2 id="start-title">{t.lobby.startTitle}</h2>
        {opponents ? (
          <>
            <StartGame opponents={opponents} refresh={retry} />
            <Strength opponents={opponents} />
          </>
        ) : (
          <div className="body">
            {failed ? (
              <>
                <p className="error" role="alert">{t.common.unreachable}</p>
                <button type="button" className="secondary mt-3" onClick={retry}>{t.common.tryAgain}</button>
              </>
            ) : <p>{t.common.loading}</p>}
          </div>
        )}
      </section>
      <div className="side" id="games" ref={games}>
        <section className="window" aria-labelledby="games-title">
          <h2 id="games-title">{t.lobby.yourGames}</h2>
          {tables === null && <p className="empty">{t.common.loading}</p>}
          {tables !== null && mine.length === 0 && <p className="empty">{t.lobby.noGames}</p>}
          {mine.map((table) => <GameRow key={table.id} table={table} />)}
        </section>
      </div>
      <section className="open" aria-labelledby="open-title">
        <h2 className="head" id="open-title">{t.lobby.openTitle}</h2>
        {unreachable && <p className="notice" role="alert">{t.common.unreachable}</p>}
        {sitError && <p className="notice" role="alert">{sitError}</p>}
        {tables !== null && open.length === 0 && <p className="foot">{t.lobby.noOpenTables}</p>}
        <div className="tables">
          {open.map((table) => <MiniTable key={table.id} table={table} onSit={sit} busy={sitting} />)}
        </div>
      </section>
    </main>
  );
}
