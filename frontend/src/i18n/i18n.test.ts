// Copyright (c) 2026 Athena Decisions Systems SAS.
import { describe, expect, it } from "vitest";

import { en } from "./en";
import { fr } from "./fr";
import { fmt, initialLang } from "./index";

function keys(value: unknown, prefix = ""): string[] {
  if (typeof value !== "object" || value === null) return [prefix];
  return Object.entries(value).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k)).sort();
}

function leaves(value: unknown, path = ""): [string, string][] {
  if (typeof value === "string") return [[path, value]];
  return Object.entries(value as object).flatMap(([k, v]) => leaves(v, path ? `${path}.${k}` : k));
}

const placeholders = (s: string) => (s.match(/\{\w+\}/g) ?? []).sort();

describe("the dictionaries", () => {
  it("have the same keys", () => {
    expect(keys(fr)).toEqual(keys(en));
  });

  it("have the same placeholders in each string", () => {
    const french = new Map(leaves(fr));
    for (const [path, text] of leaves(en)) {
      expect(placeholders(french.get(path) ?? ""), path).toEqual(placeholders(text));
    }
  });

  it("have nothing empty", () => {
    for (const [path, text] of [...leaves(en), ...leaves(fr)]) expect(text, path).not.toBe("");
  });
});

describe("fmt", () => {
  it("fills placeholders and leaves unknown ones", () => {
    expect(fmt("Deal {deal}, trick {trick}.", { deal: 5, trick: 6 })).toBe("Deal 5, trick 6.");
    expect(fmt("{x}", {})).toBe("{x}");
  });
});

describe("choosing a language", () => {
  const withLanguage = (language: string) => Object.defineProperty(navigator, "language", { value: language, configurable: true });

  it("follows the browser, defaulting to English", () => {
    withLanguage("fr-FR");
    expect(initialLang()).toBe("fr");
    withLanguage("de-DE");
    expect(initialLang()).toBe("en");
    withLanguage("en-US");
    expect(initialLang()).toBe("en");
  });

  it("lets a saved choice win", () => {
    withLanguage("en-US");
    localStorage.setItem("hearts.lang", "fr");
    expect(initialLang()).toBe("fr");
  });
});
