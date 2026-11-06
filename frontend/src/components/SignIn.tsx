// Copyright (c) 2026 Athena Decisions Systems SAS.
import { useState, type FormEvent } from "react";

import { api, setAuthToken } from "../api";
import { useT } from "../i18n";
import type { Player } from "../types";

export function inviteFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get("invite");
}

function forgetInvite() {
  window.history.replaceState(null, "", window.location.pathname + window.location.hash);
}

export function SignIn({ onSignedIn }: { onSignedIn: (player: Player) => void }) {
  const { t } = useT();
  const [invite] = useState(inviteFromUrl);
  const [mode, setMode] = useState<"sign-in" | "register">(invite ? "register" : "sign-in");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState(invite ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const registering = mode === "register";

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session = registering
        ? await api.register(name.trim(), password, code.trim())
        : await api.login(name.trim(), password);
      setAuthToken(session.token);
      forgetInvite();
      onSignedIn(session.player);
    } catch (e) {
      setError(e instanceof Error ? e.message : t.common.unreachable);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="signin">
      <h1>{registering ? t.auth.registerHeading : t.auth.signInHeading}</h1>
      <form className="window" onSubmit={submit}>
        <h2>{registering ? t.auth.registerTitle : t.auth.signInTitle}</h2>
        <div className="body">
          {registering && <p className="how">{t.auth.inviteOnly}</p>}
          <label htmlFor="name">{t.auth.name}</label>
          <input id="name" value={name} onChange={(e) => setName(e.target.value)} autoComplete="username" maxLength={24} required />
          <label htmlFor="password">{t.auth.password}</label>
          <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete={registering ? "new-password" : "current-password"} required />
          {registering && (
            <>
              <label htmlFor="code">{t.auth.code}</label>
              <input id="code" value={code} onChange={(e) => setCode(e.target.value)} autoComplete="off" required />
            </>
          )}
          {error && <p className="error" role="alert">{error}</p>}
          <button type="submit" className="primary" disabled={busy}>{registering ? t.auth.registerAction : t.auth.signInAction}</button>
          <button type="button" className="switch" onClick={() => { setMode(registering ? "sign-in" : "register"); setError(null); }}>
            {registering ? t.auth.haveAccount : t.auth.haveInvitation}
          </button>
        </div>
      </form>
    </main>
  );
}
