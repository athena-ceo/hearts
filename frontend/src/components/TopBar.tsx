// Copyright (c) 2026 Athena Decisions Systems SAS.
import { useT } from "../i18n";
import type { Route } from "../route";
import type { Player } from "../types";

function LanguageSwitch() {
  const { lang, setLang, t } = useT();
  return (
    <div className="lang" role="group" aria-label={t.nav.language}>
      <button type="button" aria-pressed={lang === "en"} aria-label={t.nav.english} onClick={() => setLang("en")}>{t.nav.en}</button>
      <button type="button" aria-pressed={lang === "fr"} aria-label={t.nav.french} onClick={() => setLang("fr")}>{t.nav.fr}</button>
    </div>
  );
}

export function TopBar({ route, player, onSignOut }: { route: Route; player: Player | null; onSignOut: () => void }) {
  const { t } = useT();
  const atLobby = route.name === "lobby";
  return (
    <header className="bar">
      <a className="mark" href="#/"><span aria-hidden="true">♥</span> {t.app.name}</a>
      {player ? (
        <nav aria-label={t.nav.main}>
          <a href="#/" aria-current={atLobby && !route.games ? "page" : undefined}>{t.nav.play}</a>
          <a href="#/games" aria-current={atLobby && route.games ? "page" : undefined}>{t.nav.myGames}</a>
        </nav>
      ) : <span className="grow" />}
      <div className="bar-end">
        <LanguageSwitch />
        {player && route.name === "table" && <a className="secondary" href="#/">{t.nav.leaveTable}</a>}
        {player && route.name === "review" && <a className="primary" href={`#/table/${route.id}`}>{t.nav.backToTable}</a>}
        {player && atLobby && (
          <>
            <span className="who">{player.name}</span>
            <button type="button" className="secondary" onClick={onSignOut}>{t.nav.signOut}</button>
          </>
        )}
      </div>
    </header>
  );
}
