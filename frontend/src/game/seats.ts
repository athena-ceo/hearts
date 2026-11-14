// Copyright (c) 2026 Athena Decision Systems SAS.
// Seats are 1-4 clockwise, and a seat's left neighbour is the next number. You always sit at the bottom.
import type { Direction } from "../types";

export type Position = "south" | "west" | "north" | "east";

const AROUND: Position[] = ["south", "west", "north", "east"];

/** Where a seat is drawn for someone in `me`. Someone watching sees the table from seat 1. */
export function positionOf(seat: number, me: number | null): Position {
  const viewpoint = me ?? 1;
  return AROUND[((seat - viewpoint) % 4 + 4) % 4];
}

/** The seat drawn at a position, the inverse of positionOf. */
export function seatAt(position: Position, me: number | null): number {
  const viewpoint = me ?? 1;
  return ((viewpoint - 1 + AROUND.indexOf(position)) % 4) + 1;
}

/** Seats in the order you read them around the table, starting with you. */
export function seatsFrom(me: number | null): number[] {
  return AROUND.map((position) => seatAt(position, me));
}

const OFFSET: Record<Exclude<Direction, null>, number> = { Left: 1, Across: 2, Right: 3 };

/** Who this seat passes to. */
export function passTarget(seat: number, direction: Direction): number | null {
  return direction ? ((seat - 1 + OFFSET[direction]) % 4) + 1 : null;
}

/** Who passes to this seat. */
export function passSource(seat: number, direction: Direction): number | null {
  return direction ? ((seat - 1 + 4 - OFFSET[direction]) % 4) + 1 : null;
}

/** The seat clockwise from this one. */
export function nextSeat(seat: number): number {
  return (seat % 4) + 1;
}
