// Copyright (c) 2026 Athena Decision Systems SAS.
import { describe, expect, it } from "vitest";

import { parseRoute } from "./route";

describe("parseRoute", () => {
  it("reads the routes", () => {
    expect(parseRoute("")).toEqual({ name: "lobby", games: false });
    expect(parseRoute("#/")).toEqual({ name: "lobby", games: false });
    expect(parseRoute("#/games")).toEqual({ name: "lobby", games: true });
    expect(parseRoute("#/table/abc")).toEqual({ name: "table", id: "abc" });
    expect(parseRoute("#/table/abc/review/3")).toEqual({ name: "review", id: "abc", number: 3 });
  });

  it("treats a bad review number as the table", () => {
    expect(parseRoute("#/table/abc/review/x")).toEqual({ name: "table", id: "abc" });
  });
});
