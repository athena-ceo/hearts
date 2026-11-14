// Copyright (c) 2026 Athena Decision Systems SAS.
import { forwardRef, useLayoutEffect, useRef } from "react";

import { flyIn, flyOut, prefersReducedMotion } from "../game/fly";
import type { PlayedCard, Sweep } from "../game/reducer";
import { positionOf, type Position } from "../game/seats";
import { useT } from "../i18n";
import { Card } from "./Card";

const SLOT: Record<Position, string> = { south: "s", west: "w", north: "n", east: "e" };

function TrickCard({ played, position, led, from }: {
  played: PlayedCard; position: Position; led: boolean; from: () => DOMRect | null;
}) {
  const { t } = useT();
  const el = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const rect = played.still ? null : from();
    if (rect && el.current) flyIn(el.current, rect);
    // Only when the card arrives.
    // eslint-disable-next-line
  }, []);
  return (
    <div className={`slot ${SLOT[position]}`}>
      <div ref={el}><Card code={played.card} /></div>
      {led && <span className="tag">{t.table.led}</span>}
    </div>
  );
}

function SweptCard({ played, position, index, to }: {
  played: PlayedCard; position: Position; index: number; to: () => DOMRect | null;
}) {
  const el = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const rect = to();
    if (rect && el.current) flyOut(el.current, rect, { delay: index * 0.02 });
    // eslint-disable-next-line
  }, []);
  return (
    <div className={`slot ${SLOT[position]} swept`}>
      <div ref={el}><Card code={played.card} /></div>
    </div>
  );
}

interface TrickProps {
  me: number | null;
  cards: PlayedCard[];
  leader: number | null;
  sweep: Sweep | null;
  showYourSlot: boolean;
  dragging: boolean;
  fromRect: (played: PlayedCard) => DOMRect | null;
  winnerRect: (seat: number) => DOMRect | null;
}

export const Trick = forwardRef<HTMLDivElement, TrickProps>(function Trick(props, ref) {
  const { t } = useT();
  const { me, cards, sweep } = props;
  const reduced = prefersReducedMotion();
  const southFilled = cards.some((c) => positionOf(c.seat, me) === "south");
  return (
    <div className="trick" ref={ref} aria-label={t.table.trickLabel} role="group">
      {props.showYourSlot && !southFilled && (
        <div className={`slot s empty${props.dragging ? " drop" : ""}`}>{t.table.yourCard}</div>
      )}
      {sweep && !reduced && sweep.cards.map((played, i) => (
        <SweptCard key={`${sweep.id}-${played.card}`} played={played} index={i} position={positionOf(played.seat, me)}
          to={() => props.winnerRect(sweep.winner)} />
      ))}
      {cards.map((played) => (
        <TrickCard key={played.card} played={played} position={positionOf(played.seat, me)}
          led={played.seat === props.leader} from={() => props.fromRect(played)} />
      ))}
    </div>
  );
});
