// Copyright (c) 2026 Athena Decision Systems SAS.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { en } from "./en";
import { fr } from "./fr";

export type Language = "en" | "fr";
export type Dict = typeof en;

export const dictionaries: Record<Language, Dict> = { en, fr };

interface I18nContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: Dict;
}

const I18nContext = createContext<I18nContextValue | null>(null);

const STORAGE_KEY = "hearts.lang";

/** A saved choice wins, then the browser's language, then English. */
export function initialLang(): Language {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "fr") return saved;
  } catch { /* ignore */ }
  return navigator.language?.toLowerCase().startsWith("fr") ? "fr" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(initialLang);

  useEffect(() => { document.documentElement.lang = lang; }, [lang]);

  function setLang(next: Language) {
    setLangState(next);
    try { localStorage.setItem(STORAGE_KEY, next); } catch { /* ignore */ }
  }

  return (
    <I18nContext.Provider value={{ lang, setLang, t: dictionaries[lang] }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useT() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useT must be used within I18nProvider");
  return ctx;
}

/** Fill a string's {placeholders}. */
export function fmt(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (whole, key: string) => (key in values ? String(values[key]) : whole));
}

/** "1 point", "0 points" or "0 point" as the language has it. */
export function pointsText(t: Dict, n: number): string {
  if (n === 0) return t.common.points.zero;
  if (n === 1) return t.common.points.one;
  return fmt(t.common.points.many, { n });
}
