// Copyright (c) 2026 Athena Decision Systems SAS.
import { useT } from "../i18n";
import { cardName, cardShort, isRed, rankOf, SUIT_GLYPH, suitOf } from "../game/cards";

export function CardFace({ code }: { code: string }) {
  const glyph = SUIT_GLYPH[suitOf(code)];
  return (
    <>
      <span className="rank" aria-hidden="true">{rankOf(code)}</span>
      <span className="pip" aria-hidden="true">{glyph}</span>
      <span className="big" aria-hidden="true">{glyph}</span>
    </>
  );
}

export function cardClass(code: string, small?: boolean): string {
  return `card${isRed(code) ? " red" : ""}${small ? " small" : ""}`;
}

/** A card that can only be looked at. */
export function Card({ code, small }: { code: string; small?: boolean }) {
  const { t } = useT();
  return (
    <span className={cardClass(code, small)} role="img" aria-label={cardName(t, code)}>
      <CardFace code={code} />
    </span>
  );
}

/** "Q♠" within a sentence. */
export function InlineCard({ code }: { code: string }) {
  return <span className={`inline-card${isRed(code) ? " red" : ""}`}>{cardShort(code)}</span>;
}
