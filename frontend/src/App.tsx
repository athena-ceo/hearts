// Copyright (c) 2026 Athena Decision Systems SAS.
import { useEffect, useState } from "react";
import { MotionConfig } from "motion/react";

import { api, ApiError, authToken, onSignedOut, setAuthToken } from "./api";
import { Lobby } from "./components/Lobby";
import { Review } from "./components/Review";
import { SignIn } from "./components/SignIn";
import { TableScreen } from "./components/TableScreen";
import { TopBar } from "./components/TopBar";
import { useT } from "./i18n";
import { useRoute } from "./route";
import type { Player } from "./types";

type Session =
  | { state: "checking" }
  | { state: "signed-out" }
  | { state: "signed-in"; player: Player }
  | { state: "unreachable" };

export default function App() {
  const { t } = useT();
  const route = useRoute();
  const [session, setSession] = useState<Session>(() => (authToken() ? { state: "checking" } : { state: "signed-out" }));
  const [attempt, setAttempt] = useState(0);

  useEffect(() => { onSignedOut(() => setSession({ state: "signed-out" })); }, []);

  useEffect(() => {
    if (!authToken()) return;
    let live = true;
    api.me().then((r) => { if (live) setSession({ state: "signed-in", player: r.player }); })
      .catch((e) => {
        if (!live) return;
        setSession(e instanceof ApiError && e.status === 401 ? { state: "signed-out" } : { state: "unreachable" });
      });
    return () => { live = false; };
  }, [attempt]);

  const signOut = () => {
    api.logout().catch(() => {});
    setAuthToken(null);
    setSession({ state: "signed-out" });
  };

  const player = session.state === "signed-in" ? session.player : null;

  return (
    <MotionConfig reducedMotion="user">
      <TopBar route={route} player={player} onSignOut={signOut} />
      {session.state === "checking" && <p className="loading">{t.common.loading}</p>}
      {session.state === "unreachable" && (
        <div className="loading">
          <p>{t.common.unreachable}</p>
          <button type="button" className="secondary mt-3" onClick={() => { setSession({ state: "checking" }); setAttempt((a) => a + 1); }}>
            {t.common.tryAgain}
          </button>
        </div>
      )}
      {session.state === "signed-out" && <SignIn onSignedIn={(p) => setSession({ state: "signed-in", player: p })} />}
      {player && route.name === "lobby" && <Lobby scrollToGames={route.games} />}
      {player && route.name === "table" && <TableScreen key={route.id} tableId={route.id} />}
      {player && route.name === "review" && <Review key={`${route.id}/${route.number}`} tableId={route.id} number={route.number} />}
    </MotionConfig>
  );
}
