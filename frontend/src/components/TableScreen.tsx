// Copyright (c) 2026 Athena Decision Systems SAS.
import { useCallback, useEffect, useRef, useState } from "react";
import { animate } from "motion";

import { api } from "../api";
import { cardName, cardNameWithArticle, sortHand } from "../game/cards";
import { prefersReducedMotion } from "../game/fly";
import { kindLabel, useOpponents } from "../game/opponents";
import { canPass, canPlay, type Action, type PlayedCard, type TableState } from "../game/reducer";
import { turnHint, whyNot, type CardReason, type TurnHint } from "../game/reasons";
import { passTarget, positionOf, seatAt, type Position } from "../game/seats";
import { useTableGame } from "../game/useTableGame";
import { fmt, pointsText, useT, type Dict } from "../i18n";
import { reviewPath } from "../route";
import type { Direction, SeatInfo } from "../types";
import { Card } from "./Card";
import { Hand } from "./Hand";
import { DealEndPanel, GameEndPanel, WaitingPanel } from "./Panels";
import { Thoughts } from "./Thoughts";
import { Trick } from "./Trick";

const PASS_COUNT = 3;

function reasonText(t: Dict, reason: CardReason): string {
  switch (reason.kind) {
    case "follow": return fmt(t.reasons.follow, { suit: t.cards.suits[reason.suit] });
    case "two-of-clubs": return t.reasons.twoOfClubs;
    case "hearts-unbroken": return t.reasons.heartsUnbroken;
    case "no-points-first-trick": return t.reasons.noPointsFirstTrick;
    default: return t.reasons.other;
  }
}

function hintText(t: Dict, hint: TurnHint): string {
  switch (hint.kind) {
    case "lead": return t.hints.lead;
    case "two-of-clubs": return t.hints.twoOfClubs;
    case "follow": return fmt(t.hints.follow, { suit: t.cards.suits[hint.suit] });
    case "void": return fmt(t.hints.void, { suit: t.cards.suits[hint.suit] });
    case "void-first-trick": return fmt(t.hints.voidFirstTrick, { suit: t.cards.suits[hint.suit] });
  }
}

export function directionText(t: Dict, direction: Direction): string {
  if (direction === "Left") return t.table.toLeft;
  if (direction === "Across") return t.table.toAcross;
  if (direction === "Right") return t.table.toRight;
  return "";
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.ceil(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const rest = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${rest}` : `${m}:${rest}`;
}

function Clock({ deadline }: { deadline: number }) {
  const { t } = useT();
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now() / 1000), 250);
    return () => clearInterval(timer);
  }, []);
  return <span className="clock" role="timer" aria-label={t.table.timeLeft}>{formatClock(deadline - now)}</span>;
}

function SeatPlate({ position, seat, info, taken, total, turn, status, kind, onSit, plateRef }: {
  position: Position; seat: number; info: SeatInfo | undefined; taken: number; total: number; turn: boolean;
  status: string | null; kind: string | null; onSit: ((seat: number) => void) | null;
  plateRef: (el: HTMLElement | null) => void;
}) {
  const { t } = useT();
  const open = info?.open;
  return (
    <div className={`seat ${position}${turn ? " to-play" : ""}`} ref={plateRef} aria-current={turn ? "true" : undefined}>
      {open ? (
        onSit
          ? <button type="button" className="primary" onClick={() => onSit(seat)}>{t.lobby.sitHere}</button>
          : <h2 className="open-seat">{t.lobby.openSeat}</h2>
      ) : (
        <>
          <h2>{info?.name ?? ""}</h2>
          {kind && <p className="kind">{kind}</p>}
          <p className="score"><b>{taken}</b> {fmt(t.table.scoreLine, { total })}</p>
          {status && <p className="kind status">{status}</p>}
        </>
      )}
    </div>
  );
}

interface Flight { id: string; card: string; from: DOMRect; to: DOMRect; }

function FlyingCard({ flight, onDone }: { flight: Flight; onDone: () => void }) {
  const el = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!el.current) return;
    const { from, to } = flight;
    const controls = animate(el.current, {
      x: [0, to.left + to.width / 2 - from.left - from.width / 2],
      y: [0, to.top + to.height / 2 - from.top - from.height / 2],
      scale: [1, 0.6], opacity: [1, 1, 0],
    }, { duration: 0.55, ease: [0.3, 0.6, 0.3, 1] });
    controls.then(onDone);
    return () => controls.cancel();
    // eslint-disable-next-line
  }, []);
  return (
    <div ref={el} className="flying" style={{ left: flight.from.left, top: flight.from.top }}>
      <Card code={flight.card} />
    </div>
  );
}

export function TableScreen({ tableId }: { tableId: string }) {
  const { t } = useT();
  const { opponents } = useOpponents();
  const [selected, setSelected] = useState<string[]>([]);
  const [hint, setHint] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const [flights, setFlights] = useState<Flight[]>([]);
  const [fillError, setFillError] = useState<string | null>(null);

  const plates = useRef<Partial<Record<Position, HTMLElement>>>({});
  const handCards = useRef(new Map<string, HTMLElement>());
  const flySource = useRef(new Map<string, DOMRect>());
  const trickEl = useRef<HTMLDivElement>(null);
  const handEl = useRef<HTMLDivElement>(null);
  const flightId = useRef(0);

  const seatInfo = useRef<(seat: number) => string>(() => "");

  const before = useCallback((action: Action, state: TableState) => {
    const me = state.seat;
    const say = (text: string) => setAnnouncement(text);
    switch (action.type) {
      case "card": {
        if (action.seat === me && !flySource.current.has(action.card)) {
          const el = handCards.current.get(action.card);
          if (el) flySource.current.set(action.card, el.getBoundingClientRect());
        }
        say(fmt(t.announce.played, { who: seatInfo.current(action.seat), card: cardName(t, action.card) }));
        break;
      }
      case "trick":
        say(fmt(t.announce.tookTrick, { who: seatInfo.current(action.winner), points: pointsText(t, action.points) }));
        break;
      case "passed": {
        if (action.seat !== me || !action.cards || !me || prefersReducedMotion()) break;
        const target = passTarget(me, state.direction);
        const plate = target ? plates.current[positionOf(target, me)] : null;
        if (!plate) break;
        const to = plate.getBoundingClientRect();
        const launched = action.cards.flatMap((card) => {
          const el = handCards.current.get(card);
          return el ? [{ id: `${flightId.current++}`, card, from: el.getBoundingClientRect(), to }] : [];
        });
        setFlights((f) => [...f, ...launched]);
        break;
      }
      case "received":
        if (action.cards) {
          say(fmt(t.announce.received, { cards: action.cards.map((c) => cardName(t, c)).join(", ") }));
        }
        break;
      case "turn":
        if (me && action.waiting.includes(me) && action.view) {
          say(action.view.decision === "pass" ? t.announce.yourPass : t.announce.yourTurn);
        }
        break;
      case "deal_end":
        say(fmt(t.table.dealOver, { n: action.number }));
        break;
      case "game_end":
        say(t.table.gameOver);
        break;
      default:
        break;
    }
  }, [t]);

  const { state, status, gone, play, pass, nextDeal, reconnect } = useTableGame(tableId, before);
  const { seat: me, table, view } = state;

  const nameOf = useCallback((seat: number) => {
    if (seat === me) return t.common.you;
    const info = table?.seats[seat - 1];
    return info?.name ?? t.lobby.openSeat;
  }, [me, table, t]);
  seatInfo.current = nameOf;

  const kindOf = useCallback((seat: number) => {
    const info = table?.seats[seat - 1];
    return info && info.kind !== "person" ? kindLabel(t, info.kind, opponents) : null;
  }, [table, t, opponents]);

  const passing = canPass(state);
  const playing = canPlay(state);
  const active = passing || playing;
  const legal = view?.legal;
  const passDirection = directionText(t, state.direction);

  // A choice only lasts as long as the decision it was for.
  const decision = passing ? "pass" : playing ? `play-${state.tricksDone}-${state.trick.length}` : "none";
  useEffect(() => { setSelected([]); setHint(null); }, [decision]);

  const isLegal = useCallback((card: string) => passing || Boolean(legal?.includes(card)), [passing, legal]);
  const reasonFor = useCallback((card: string) => (view ? reasonText(t, whyNot(card, view)) : null), [view, t]);

  const onTap = (card: string) => {
    if (passing) {
      setHint(null);
      if (selected.includes(card)) setSelected(selected.filter((c) => c !== card));
      else if (selected.length < PASS_COUNT) setSelected([...selected, card]);
      else setHint(t.table.threeOnly);
      return;
    }
    if (!playing) return;
    if (!isLegal(card)) {
      setHint(reasonFor(card));
      return;
    }
    setHint(null);
    if (selected[0] === card) {
      if (!play(card)) setHint(t.table.notConnected);
    } else {
      setSelected([card]);
    }
  };

  const onPlayButton = () => {
    if (selected[0] && !play(selected[0])) setHint(t.table.notConnected);
  };

  const onPassButton = () => {
    if (selected.length === PASS_COUNT && !pass(selected)) setHint(t.table.notConnected);
  };

  const onDrop = useCallback((card: string, rect: DOMRect) => {
    flySource.current.set(card, rect);
    if (!play(card)) setHint(t.table.notConnected);
  }, [play, t]);

  const canDrag = useCallback((card: string) => playing && Boolean(legal?.includes(card)), [playing, legal]);

  const registerCard = useCallback((card: string, el: HTMLElement | null) => {
    if (el) handCards.current.set(card, el); else handCards.current.delete(card);
  }, []);

  const dropTarget = useCallback(() => trickEl.current?.getBoundingClientRect() ?? null, []);

  const plateRect = useCallback((seat: number): DOMRect | null => {
    const position = positionOf(seat, state.seat);
    const el = position === "south" ? handEl.current : plates.current[position];
    return el?.getBoundingClientRect() ?? null;
  }, [state.seat]);

  const fromRect = useCallback((played: PlayedCard) => {
    if (played.seat === state.seat) {
      return flySource.current.get(played.card) ?? null;
    }
    return plateRect(played.seat);
  }, [plateRect, state.seat]);

  const entranceFor = useCallback((card: string, index: number) => {
    if (state.entering === "deal") {
      const from = trickEl.current?.getBoundingClientRect();
      return from ? { from, delay: index * 0.035 } : null;
    }
    if (state.entering === "received" && state.received.includes(card) && state.receivedFrom) {
      const from = plateRect(state.receivedFrom);
      return from ? { from, delay: 0 } : null;
    }
    return null;
  }, [state.entering, state.received, state.receivedFrom, plateRect]);

  const sit = async (seat: number) => {
    try {
      await api.join(tableId, seat);
      reconnect();
    } catch (e) {
      setFillError(e instanceof Error ? e.message : t.common.unreachable);
    }
  };

  const fill = async () => {
    setFillError(null);
    try {
      await api.fill(tableId);
    } catch (e) {
      setFillError(e instanceof Error ? e.message : t.common.unreachable);
    }
  };

  if (gone) {
    return (
      <main className="message-page">
        <p>{t.table.gone}</p>
        <a className="primary" href="#/">{t.table.backToLobby}</a>
      </main>
    );
  }

  if (!state.ready || !table) {
    return <main className="message-page"><p>{status === "reconnecting" ? t.table.reconnecting : t.table.connecting}</p></main>;
  }

  const waitingForPlayers = table.status === "open";
  const failed = table.status === "failed" || Boolean(state.failure);
  const finished = Boolean(state.gameEnd);
  const watching = me === null;
  const expertOffered = Boolean(opponents?.some((o) => o.kind === "expert"));

  const stateLabel = (seat: number): string | null => {
    if (state.phase !== "pass" || waitingForPlayers) return null;
    return state.passedSeats.includes(seat) || !state.waiting.includes(seat) ? t.table.passed : t.table.choosing;
  };

  const waitingNames = state.waiting.filter((s) => s !== me).map(nameOf).join(", ");
  const youTaken = me ? state.taken[me - 1] : 0;
  const youTotal = me ? state.totals[me - 1] : 0;

  let line: JSX.Element | string | null = null;
  if (waitingForPlayers) line = null;
  else if (hint && active) line = <><b>{passing ? t.table.chooseThree : t.table.yourTurn}</b> {hint}</>;
  else if (passing) line = <><b>{t.table.chooseThree}</b> {fmt(t.table.passThem, { direction: passDirection })}</>;
  else if (playing && view) line = <><b>{t.table.yourTurn}</b> {hintText(t, turnHint(view))}</>;
  else if (state.pending) line = t.table.sending;
  else if (state.received.length && state.receivedFrom) line = fmt(t.table.receivedFrom, { who: nameOf(state.receivedFrom) });
  else if (state.phase === "pass" && me && state.passedSeats.includes(me)) {
    line = waitingNames ? fmt(t.table.passedWaiting, { who: waitingNames }) : t.table.passed;
  } else if (state.waiting.length && waitingNames) line = fmt(t.table.waitingFor, { who: waitingNames });

  let progress: string;
  if (waitingForPlayers || !state.number) progress = t.table.notStarted;
  else if (state.phase === "pass") {
    progress = fmt(t.table.dealPassing, { deal: state.number, direction: passDirection });
  } else if (state.phase === "done" || state.tricksDone >= 13) {
    progress = fmt(t.table.dealDone, { deal: state.number });
  } else {
    progress = fmt(t.table.dealTrick, { deal: state.number, trick: state.tricksDone + 1 });
  }

  const seatPlate = (position: Position) => {
    const seat = seatAt(position, me);
    return (
      <SeatPlate key={position} position={position} seat={seat} info={table.seats[seat - 1]}
        taken={state.taken[seat - 1]} total={state.totals[seat - 1]}
        turn={!waitingForPlayers && state.phase === "play" && state.waiting.includes(seat)}
        status={stateLabel(seat)} kind={kindOf(seat)}
        onSit={watching && table.seats[seat - 1]?.open ? sit : null}
        plateRef={(el) => { if (el) plates.current[position] = el; else delete plates.current[position]; }} />
    );
  };

  return (
    <main className={`layout${table.study ? " study" : ""}`}>
      <section className="stage" aria-label={t.table.stageLabel}>
        <div className="note">
          <p>{progress}</p>
          {table.study && <p>{t.table.studyNote}</p>}
          {watching && <p>{t.table.watching}</p>}
          {state.lastDeal > 0 && !finished && (
            <p><a href={reviewPath(tableId, state.lastDeal)}>{fmt(t.table.reviewDealN, { n: state.lastDeal })}</a></p>
          )}
        </div>
        {(["north", "west", "east"] as Position[]).map(seatPlate)}
        <Trick ref={trickEl} me={me} cards={state.trick} leader={state.leader} sweep={state.sweep}
          showYourSlot={!watching && state.phase === "play" && !finished}
          dragging={dragging} fromRect={fromRect} winnerRect={plateRect} />
        <div className="banners">
          {status !== "open" && <p className="notice" role="status">{t.table.reconnecting}</p>}
          {state.refused && <p className="notice" role="alert">{state.refused}</p>}
          {state.timedOut && <p className="notice" role="status">{t.table.timedOut}</p>}
          {failed && <p className="notice" role="alert">{state.failure ?? t.table.failed}</p>}
        </div>
        <div className="you" ref={handEl}>
          {watching ? seatPlate("south") : (
            <>
              <div className="turn">
                {line && <p aria-live="off">{line}</p>}
                {state.deadline && <Clock deadline={state.deadline} />}
                {!waitingForPlayers && (
                  <span className="scoreline">
                    {fmt(t.table.youScore, { taken: youTaken, total: youTotal })}
                  </span>
                )}
                {passing && (
                  <button type="button" className="primary" disabled={selected.length < PASS_COUNT} onClick={onPassButton}>
                    {selected.length < PASS_COUNT
                      ? fmt(t.table.chooseMore, { n: PASS_COUNT - selected.length })
                      : fmt(t.table.passButton, { direction: passDirection })}
                  </button>
                )}
                {playing && (
                  <button type="button" className="primary" disabled={!selected[0]} onClick={onPlayButton}>
                    {selected[0] ? fmt(t.table.playCard, { card: cardNameWithArticle(t, selected[0]) }) : t.table.chooseCard}
                  </button>
                )}
              </div>
              {state.hand.length > 0 && (
                <Hand cards={sortHand(state.hand)} active={active} isLegal={isLegal} reasonFor={reasonFor}
                  selected={selected} received={state.received} pending={state.pending?.kind === "play" ? state.pending.cards : []}
                  onTap={onTap} canDrag={canDrag} dropTarget={dropTarget} onDrop={onDrop} onDragChange={setDragging}
                  entranceFor={entranceFor} registerCard={registerCard} />
              )}
            </>
          )}
        </div>
        {waitingForPlayers && (
          <WaitingPanel tableId={tableId} seated={!watching} canFill={expertOffered} onFill={fill} error={fillError} />
        )}
        {state.gameEnd ? (
          <GameEndPanel tableId={tableId} totals={state.gameEnd.totals} winners={state.gameEnd.winners}
            lastDeal={state.lastDeal} me={me} nameOf={nameOf} />
        ) : state.dealEnd && (
          <DealEndPanel tableId={tableId} number={state.dealEnd.number} scores={state.dealEnd.scores} totals={state.totals}
            me={me} nameOf={nameOf} onNext={nextDeal} />
        )}
      </section>
      {table.study && !(finished && state.thoughts.length === 0) && <Thoughts state={state} nameOf={nameOf} kindOf={kindOf} />}
      <p className="sr-only" aria-live="polite">{announcement}</p>
      {flights.map((flight) => (
        <FlyingCard key={flight.id} flight={flight} onDone={() => setFlights((f) => f.filter((x) => x.id !== flight.id))} />
      ))}
    </main>
  );
}


