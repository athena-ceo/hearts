// Copyright (c) 2026 Athena Decision Systems SAS.
// Cards move as objects: from one place on screen to another, whatever the layout, phone or desktop.
import { animate } from "motion";

export function prefersReducedMotion(): boolean {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
}

const center = (r: DOMRect) => ({ x: r.left + r.width / 2, y: r.top + r.height / 2 });

const EASE: [number, number, number, number] = [0.2, 0.8, 0.2, 1];

/** Animate an element from `from` to where it now sits. */
export function flyIn(el: HTMLElement, from: DOMRect, options: { duration?: number; delay?: number; turn?: number } = {}) {
  if (prefersReducedMotion()) return;
  const to = el.getBoundingClientRect();
  if (!to.width) return;
  const a = center(from);
  const b = center(to);
  // From a card, its own size; from a seat's plate, which is wider than a card, as if drawn from a held hand.
  const scale = from.width > to.width * 1.2 ? 0.6 : Math.max(0.3, from.width / to.width);
  const delay = options.delay ?? 0;
  if (delay) el.style.opacity = "0";
  animate(el, {
    x: [a.x - b.x, 0], y: [a.y - b.y, 0], scale: [scale, 1], rotate: [options.turn ?? 0, 0],
  }, { duration: options.duration ?? 0.38, delay, ease: EASE });
  if (delay) window.setTimeout(() => { el.style.opacity = ""; }, delay * 1000);
}

/** Animate an element from where it sits to `to`, fading as it arrives. */
export function flyOut(el: HTMLElement, to: DOMRect, options: { duration?: number; delay?: number } = {}) {
  if (prefersReducedMotion()) return;
  const a = center(el.getBoundingClientRect());
  const b = center(to);
  animate(el, { x: [0, b.x - a.x], y: [0, b.y - a.y], scale: [1, 0.5], opacity: [1, 1, 0] }, {
    duration: options.duration ?? 0.5, delay: options.delay ?? 0, ease: EASE,
  });
}
