// Copyright (c) 2026 Athena Decisions Systems SAS.
// Hash routes: the static build can be served from any path.
import { useEffect, useState } from "react";

export type Route =
  | { name: "lobby"; games: boolean }
  | { name: "table"; id: string }
  | { name: "review"; id: string; number: number };

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  if (parts[0] === "table" && parts[1]) {
    const number = Number(parts[3]);
    if (parts[2] === "review" && Number.isInteger(number) && number > 0) {
      return { name: "review", id: parts[1], number };
    }
    return { name: "table", id: parts[1] };
  }
  return { name: "lobby", games: parts[0] === "games" };
}

export function tablePath(id: string): string { return `#/table/${id}`; }
export function reviewPath(id: string, number: number): string { return `#/table/${id}/review/${number}`; }

export function go(path: string) { window.location.hash = path; }

export function useRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
