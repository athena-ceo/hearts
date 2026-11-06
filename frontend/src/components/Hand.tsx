// Copyright (c) 2026 Athena Decisions Systems SAS.
// Your hand: tap to choose, arrow keys and Enter, or drag a card up to the trick.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { createPortal } from "react-dom";
import { motion } from "motion/react";

import { flyIn, prefersReducedMotion } from "../game/fly";
import { useT } from "../i18n";
import { cardName } from "../game/cards";
import { CardFace, Card, cardClass } from "./Card";

const NEAREST_TAP_TARGET = 44;
const NORMAL_GAP = 8;
const DRAG_START = 10;
const DROP_DISTANCE = 70;

/** How far apart cards sit so a whole hand fits, while each keeps a target wide enough to tap. */
export function cardGap(available: number, cardWidth: number, count: number): number {
  if (count < 2) return NORMAL_GAP;
  const fit = (available - count * cardWidth) / (count - 1);
  return Math.max(Math.min(NORMAL_GAP, fit), NEAREST_TAP_TARGET - cardWidth);
}

interface HandProps {
  cards: string[];
  /** Whether cards may be chosen at all right now, and whether each one may. */
  active: boolean;
  isLegal: (card: string) => boolean;
  reasonFor: (card: string) => string | null;
  selected: string[];
  received: string[];
  pending: string[];
  onTap: (card: string) => void;
  /** Dragging plays straight away, so it's only offered when a single card is wanted. */
  canDrag: (card: string) => boolean;
  dropTarget: () => DOMRect | null;
  onDrop: (card: string, rect: DOMRect) => void;
  onDragChange: (dragging: boolean) => void;
  entranceFor: (card: string, index: number) => { from: DOMRect; delay: number } | null;
  registerCard: (card: string, el: HTMLElement | null) => void;
}

function HandCard(props: {
  card: string; gap: number; index: number; tabbable: boolean; label: string; active: boolean; illegal: boolean;
  reason: string | null; selected: boolean; received: boolean; pending: boolean; dragging: boolean;
  entrance: { from: DOMRect; delay: number } | null;
  register: (card: string, el: HTMLElement | null) => void;
  onClick: () => void; onFocus: () => void;
  onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => void;
}) {
  const { card, entrance, register } = props;
  const lift = useRef<HTMLDivElement>(null);
  const button = useRef<HTMLButtonElement>(null);
  useLayoutEffect(() => {
    if (entrance && lift.current) flyIn(lift.current, entrance.from, { delay: entrance.delay, duration: 0.42 });
    // Only when the card arrives.
    // eslint-disable-next-line
  }, []);
  useLayoutEffect(() => {
    register(card, button.current);
    return () => register(card, null);
  }, [card, register]);

  const classes = [
    cardClass(card),
    props.illegal ? "dim" : "",
    props.active && !props.illegal ? "live" : "",
    props.received ? "received" : "",
    props.pending ? "pending" : "",
    props.dragging ? "lifted" : "",
  ].filter(Boolean).join(" ");

  return (
    <motion.div className="hand-slot" layout={prefersReducedMotion() ? false : "position"}
      transition={{ duration: 0.25 }} style={{ marginLeft: props.index ? props.gap : 0 }}>
      <div ref={lift}>
        <button ref={button} type="button" className={classes} tabIndex={props.tabbable ? 0 : -1}
          aria-pressed={props.selected} aria-disabled={!props.active || props.illegal}
          aria-label={props.label} title={props.reason ?? undefined} data-card={card}
          onClick={props.onClick} onFocus={props.onFocus} onPointerDown={props.onPointerDown}>
          <CardFace code={card} />
        </button>
      </div>
    </motion.div>
  );
}

export function Hand(props: HandProps) {
  const { t } = useT();
  const { cards, canDrag, dropTarget, onDrop, onDragChange } = props;
  const box = useRef<HTMLDivElement>(null);
  const [gap, setGap] = useState(NORMAL_GAP);
  const [overflowing, setOverflowing] = useState(false);
  const [focused, setFocused] = useState(0);
  const [ghost, setGhost] = useState<{ card: string; x: number; y: number } | null>(null);
  const ghostEl = useRef<HTMLDivElement>(null);
  const justDragged = useRef(false);
  const hadFocus = useRef(false);

  // Fit the hand to the space, whatever the screen.
  useLayoutEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => {
      const style = getComputedStyle(el);
      const inner = el.clientWidth - parseFloat(style.paddingLeft || "0") - parseFloat(style.paddingRight || "0");
      const cardWidth = (el.querySelector(".card") as HTMLElement | null)?.offsetWidth ?? 0;
      if (!cardWidth) return;
      const next = cardGap(inner, cardWidth, cards.length);
      setGap(next);
      setOverflowing(cards.length * cardWidth + (cards.length - 1) * next > inner + 1);
    };
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, [cards.length]);

  useEffect(() => {
    if (focused >= cards.length && cards.length) setFocused(cards.length - 1);
  }, [cards.length, focused]);

  // Playing a card by keyboard removes the focused button, so keep the keyboard in the hand.
  useEffect(() => {
    if (hadFocus.current && document.activeElement === document.body && cards.length) {
      box.current?.querySelectorAll<HTMLElement>("button.card")[Math.min(focused, cards.length - 1)]?.focus();
    }
  }, [cards.length, focused]);

  // When the hand scrolls, bring the first card you can choose into view as your turn starts.
  const firstLive = props.active ? cards.find(props.isLegal) : undefined;
  useEffect(() => {
    const el = box.current;
    if (!firstLive || !overflowing || !el) return;
    const card = el.querySelector<HTMLElement>(`[data-card="${firstLive}"]`);
    if (!card) return;
    const left = card.getBoundingClientRect().left - el.getBoundingClientRect().left;
    if (left < 0 || left > el.clientWidth - card.offsetWidth) el.scrollLeft += left - 8;
  }, [firstLive, overflowing]);

  const moveFocus = (event: KeyboardEvent<HTMLDivElement>) => {
    const last = cards.length - 1;
    let next: number | null = null;
    if (event.key === "ArrowRight") next = Math.min(last, focused + 1);
    if (event.key === "ArrowLeft") next = Math.max(0, focused - 1);
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = last;
    if (next === null) return;
    event.preventDefault();
    setFocused(next);
    box.current?.querySelectorAll<HTMLElement>("button.card")[next]?.focus();
  };

  const startDrag = useCallback((card: string, event: ReactPointerEvent<HTMLButtonElement>) => {
    if (event.button !== 0 || !canDrag(card)) return;
    const startX = event.clientX;
    const startY = event.clientY;
    const source = event.currentTarget;
    let lifted = false;

    const finish = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onCancel);
      setGhost(null);
      if (lifted) onDragChange(false);
    };
    const onMove = (e: PointerEvent) => {
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      if (!lifted) {
        // On a touch screen a sideways gesture is scrolling the hand.
        if (Math.hypot(dx, dy) < DRAG_START || (e.pointerType === "touch" && Math.abs(dy) < Math.abs(dx))) return;
        lifted = true;
        onDragChange(true);
      }
      setGhost({ card, x: e.clientX, y: e.clientY });
    };
    const onUp = (e: PointerEvent) => {
      // A quick flick can end before the dragged card has been drawn.
      const rect = (ghostEl.current ?? source).getBoundingClientRect();
      const wasLifted = lifted;
      finish();
      if (!wasLifted) return;
      justDragged.current = true;
      window.setTimeout(() => { justDragged.current = false; }, 0);
      const target = dropTarget();
      const inside = target && e.clientX >= target.left && e.clientX <= target.right
        && e.clientY >= target.top && e.clientY <= target.bottom;
      if (inside || startY - e.clientY > DROP_DISTANCE) onDrop(card, rect);
    };
    const onCancel = () => finish();
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onCancel);
  }, [canDrag, dropTarget, onDragChange, onDrop]);

  return (
    <>
      <div ref={box} className={`hand${overflowing ? " scrolls" : ""}`} role="group" aria-label={t.table.yourHand}
        onKeyDown={moveFocus}
        onFocusCapture={() => { hadFocus.current = true; }}
        onBlurCapture={(e) => { if (e.relatedTarget) hadFocus.current = false; }}>
        {cards.map((card, index) => {
          const legal = props.isLegal(card);
          const reason = props.active && !legal ? props.reasonFor(card) : null;
          const name = cardName(t, card);
          return (
            <HandCard key={card} card={card} gap={gap} index={index}
              tabbable={index === Math.min(focused, cards.length - 1)}
              label={reason ? `${name}. ${reason}` : name}
              active={props.active} illegal={props.active && !legal} reason={reason}
              selected={props.selected.includes(card)} received={props.received.includes(card)}
              pending={props.pending.includes(card)} dragging={ghost?.card === card}
              entrance={props.entranceFor(card, index)} register={props.registerCard}
              onFocus={() => setFocused(index)}
              onClick={() => { if (!justDragged.current) props.onTap(card); }}
              onPointerDown={(event) => startDrag(card, event)} />
          );
        })}
      </div>
      {ghost && createPortal(
        <div ref={ghostEl} className="drag-ghost" style={{ left: ghost.x, top: ghost.y }}>
          <Card code={ghost.card} />
        </div>,
        document.body,
      )}
    </>
  );
}
