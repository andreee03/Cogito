import { useState, type FormEvent } from "react";
import { useDemoMode } from "../hooks/useDemoMode";
import { ApiError, getBackendUrl, resetDemo, setBackendUrl } from "../lib/api";
import { getTheme, setTheme, type ThemeChoice } from "../lib/theme";

type TestState = { kind: "idle" } | { kind: "testing" } | { kind: "ok"; ms: number } | { kind: "error"; message: string };

const THEMES: { value: ThemeChoice; label: string }[] = [
  { value: "system", label: "Automatique" },
  { value: "light", label: "Clair" },
  { value: "dark", label: "Sombre" },
];

export function SettingsPage() {
  const demo = useDemoMode();
  const [url, setUrl] = useState(getBackendUrl());
  const [saved, setSaved] = useState(false);
  const [test, setTest] = useState<TestState>({ kind: "idle" });
  const [theme, setThemeState] = useState<ThemeChoice>(getTheme());

  const clean = url.trim().replace(/\/+$/, "");
  const invalid = clean !== "" && !/^https?:\/\/[^\s]+$/i.test(clean);

  function save(e: FormEvent) {
    e.preventDefault();
    if (invalid) return;
    setBackendUrl(clean);
    setUrl(clean);
    setSaved(true);
  }

  async function testConnection() {
    const target = clean || getBackendUrl();
    if (!target) {
      setTest({ kind: "error", message: "Indique d'abord l'URL du back-end." });
      return;
    }
    setTest({ kind: "testing" });
    const t0 = performance.now();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90_000);
    try {
      const res = await fetch(`${target}/health`, { signal: controller.signal });
      if (!res.ok) throw new ApiError(`Le back-end a répondu avec l'erreur ${res.status}.`, res.status);
      const body = await res.json().catch(() => null);
      if (body?.status !== "ok") throw new ApiError("Réponse inattendue de /health.", res.status);
      setTest({ kind: "ok", ms: Math.round(performance.now() - t0) });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof DOMException && err.name === "AbortError"
            ? "Pas de réponse après 90 secondes."
            : "Impossible de joindre cette adresse. Vérifie l'URL, et que le back-end autorise cette origine (ALLOWED_ORIGINS).";
      setTest({ kind: "error", message });
    } finally {
      clearTimeout(timer);
    }
  }

  return (
    <div className="page page--narrow">
      <header className="page-head page-head--stack">
        <p className="eyebrow">Configuration</p>
        <h1 className="page-title">Réglages</h1>
      </header>

      <section className="settings-block">
        <h2 className="section-title">Back-end</h2>
        <p className="settings-block__hint">
          {demo
            ? "Aucune URL configurée : l'application fonctionne en mode démo, avec des données fictives."
            : "Les données viennent de ton back-end Cogito."}
        </p>
        <form className="form" onSubmit={save}>
          <label className="field">
            <span className="field__label">URL du back-end</span>
            <input
              className="input"
              type="url"
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setSaved(false);
                setTest({ kind: "idle" });
              }}
              placeholder="https://mon-api.onrender.com"
              aria-invalid={invalid}
            />
            {invalid && <span className="field__error">L'adresse doit commencer par http:// ou https://</span>}
            <span className="field__hint">Laisse vide pour revenir au mode démo.</span>
          </label>
          <div className="form__actions form__actions--start">
            <button className="btn btn--primary" disabled={invalid || clean === getBackendUrl()}>
              Enregistrer
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={testConnection}
              disabled={test.kind === "testing" || invalid}
            >
              {test.kind === "testing" ? "Test en cours…" : "Tester la connexion"}
            </button>
          </div>
          {saved && <p className="text-ok">Réglage enregistré.</p>}
          {test.kind === "ok" && <p className="text-ok">Connexion réussie ({test.ms} ms).</p>}
          {test.kind === "error" && <p className="text-error">{test.message}</p>}
        </form>
      </section>

      <section className="settings-block">
        <h2 className="section-title">Apparence</h2>
        <div className="segmented" role="radiogroup" aria-label="Thème">
          {THEMES.map((t) => (
            <label key={t.value} className={`segmented__opt ${theme === t.value ? "is-active" : ""}`}>
              <input
                type="radio"
                name="theme"
                checked={theme === t.value}
                onChange={() => {
                  setTheme(t.value);
                  setThemeState(t.value);
                }}
              />
              {t.label}
            </label>
          ))}
        </div>
      </section>

      {demo && (
        <section className="settings-block">
          <h2 className="section-title">Données de démo</h2>
          <p className="settings-block__hint">Remet les 4 articles d'exemple dans leur état initial.</p>
          <button
            className="btn btn--ghost"
            onClick={() => {
              resetDemo();
              setBackendUrl(""); // prévient les pages ouvertes qu'il faut recharger
            }}
          >
            Réinitialiser la démo
          </button>
        </section>
      )}
    </div>
  );
}
