// Copyright (c) 2026 Athena Decision Systems SAS.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { TABLE } from "../test/fixtures";
import { forgetOpponents } from "../game/opponents";
import { I18nProvider } from "../i18n";
import { en } from "../i18n/en";
import { defaultSeats, Lobby, moveTime } from "./Lobby";

function serve(opponents: { kind: string; label: string }[], tables: unknown[]) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(
    url.endsWith("/opponents") ? { opponents } : { tables },
  ))));
}

beforeEach(() => {
  forgetOpponents();
  localStorage.setItem("hearts.token", "tok");
  localStorage.setItem("hearts.lang", "en");
});
afterEach(() => { vi.unstubAllGlobals(); });

const TWO = [{ kind: "clown", label: "Clown" }, { kind: "network", label: "Neural network" }];
const FOUR = [...TWO, { kind: "conservative", label: "Conservative" }, { kind: "expert", label: "Expert, 1986" }];

const lobby = () => render(<I18nProvider><Lobby scrollToGames={false} /></I18nProvider>);

describe("the seat menus", () => {
  it("offer only what the server offers, plus a person", async () => {
    serve(TWO, []);
    lobby();
    const across = await screen.findByLabelText("Across");
    expect(within(across).getAllByRole("option").map((o) => o.textContent)).toEqual(["Find a person", "Clown", "Neural network"]);
  });

  it("show the Expert option and its fill promise only when an Expert exists", async () => {
    serve(TWO, []);
    const { unmount } = lobby();
    await screen.findByLabelText("Across");
    expect(screen.queryByText(/an Expert takes the seat/)).not.toBeInTheDocument();
    unmount();

    forgetOpponents();
    serve(FOUR, []);
    lobby();
    expect(await screen.findByText(/an Expert takes the seat/)).toBeInTheDocument();
  });

  it("default to a table that can start without an Expert to fill it", () => {
    expect(defaultSeats(TWO)).not.toContain("person");
    expect(defaultSeats(FOUR)).toEqual(["person", "expert", "network"]);
  });

  it("list strengths only for what's offered", async () => {
    serve(TWO, []);
    lobby();
    await screen.findByLabelText("Across");
    expect(screen.getByText("Taught itself by self-play. Gives no reasons.")).toBeInTheDocument();
    expect(screen.queryByText("97 rules, and it tells you which one it used.")).not.toBeInTheDocument();
  });
});

describe("players a Medley offers", () => {
  const OFFERED = [...FOUR, { kind: "medley:ab12:0", label: "Expert on Medley" }];

  it("are in the seat menus under the Medley's name for them, and not in the strength table", async () => {
    serve(OFFERED, []);
    lobby();
    const across = await screen.findByLabelText("Across");
    expect(within(across).getAllByRole("option").map((o) => o.textContent)).toContain("Expert on Medley");
    expect(within(screen.getByRole("table")).queryByText("Expert on Medley")).not.toBeInTheDocument();
  });

  it("when someone else took them first: say so, ask again who is offered, and put a house player back", async () => {
    let listed = OFFERED;
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url.replace(/^.*\/api/, "")}`);
      if (url.endsWith("/opponents")) return new Response(JSON.stringify({ opponents: listed }));
      if (init?.method === "POST") {
        listed = FOUR;
        return new Response(JSON.stringify({ detail: "Those Medley players have just been taken. Choose again." }), { status: 400 });
      }
      return new Response(JSON.stringify({ tables: [] }));
    }));
    lobby();
    const across = await screen.findByLabelText("Across") as HTMLSelectElement;
    fireEvent.change(across, { target: { value: "medley:ab12:0" } });
    fireEvent.click(screen.getByRole("button", { name: en.lobby.dealMeIn }));
    expect(await screen.findByRole("alert")).toHaveTextContent(en.lobby.medleyTaken);
    await waitFor(() => expect(within(screen.getByLabelText("Across")).queryByText("Expert on Medley")).not.toBeInTheDocument());
    expect((screen.getByLabelText("Across") as HTMLSelectElement).value).not.toContain("medley:");
    expect(calls.filter((c) => c === "GET /opponents")).toHaveLength(2);
  });
});

describe("the lists", () => {
  it("say whose turn it is, and put your turn first", async () => {
    serve(TWO, [
      { ...TABLE, id: "a", your_seat: 1, your_turn: false, waiting_for: ["Mei"], deal: 2, totals: [14, 3, 5, 6] },
      { ...TABLE, id: "b", your_seat: 1, your_turn: true, deal: 5, totals: [31, 22, 40, 50] },
    ]);
    lobby();
    expect(await screen.findByText("Your turn, deal 5. You 31, lowest 22.")).toBeInTheDocument();
    expect(screen.getByText("Waiting for Mei, deal 2. You 14, lowest 3.")).toBeInTheDocument();
    const states = [...document.querySelectorAll(".game .state")].map((e) => e.textContent);
    expect(states[0]).toContain("Your turn");
    expect(screen.getByRole("link", { name: "Play" })).toHaveAttribute("href", "#/table/b");
  });

  it("draw open tables with a Sit here for each open seat", async () => {
    const seats = [
      { kind: "person", name: "Ana", open: false },
      { kind: "person", name: null, open: true },
      { kind: "expert", name: "Kant", open: false },
      { kind: "network", name: "Proust", open: false },
    ];
    serve(TWO, [{ ...TABLE, id: "c", status: "open", your_seat: null, seats, time_limit: 90 }]);
    lobby();
    const sit = await screen.findByRole("button", { name: "Sit at Ana's table" });
    expect(sit).toHaveTextContent("Sit here");
    const mini = sit.closest(".mini") as HTMLElement;
    expect(within(mini).getByText("90 seconds a move")).toBeInTheDocument();
    expect(within(mini).getByText("Expert")).toBeInTheDocument();
  });
});

describe("moveTime", () => {
  it("reads naturally", () => {
    expect(moveTime(en, null)).toBe("No time limit");
    expect(moveTime(en, 30)).toBe("30 seconds a move");
    expect(moveTime(en, 300)).toBe("5 minutes a move");
    expect(moveTime(en, 86400)).toBe("A day a move");
  });
});
