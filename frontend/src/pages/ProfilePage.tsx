import { useEffect, useState } from "react";
import { ErrorState, Spinner } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage } from "../lib/api";

export function ProfilePage() {
  const { data, setData, error, loading, reload } = useAsync(() => api().getProfile());
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    if (data) setDraft(data.master_prompt);
  }, [data]);

  const dirty = data !== null && draft !== data.master_prompt;

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      setData(await api().updateProfile({ master_prompt: draft }));
      setSavedAt(Date.now());
    } catch (err) {
      setSaveError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page page--narrow">
      <header className="page-head page-head--stack">
        <p className="eyebrow">Ce qui guide chaque recherche</p>
        <h1 className="page-title">Mon profil de goûts</h1>
        <p className="page-sub">
          Tes principes d'achat : matières, couleurs, marques, ce que tu fuis. Cogito s'en sert pour chaque article ; le
          prompt spécifique d'un article l'emporte en cas de conflit.
        </p>
      </header>

      {loading && !data ? (
        <Spinner />
      ) : error && !data ? (
        <ErrorState message={error} onRetry={() => reload()} />
      ) : (
        <div className="profile">
          <textarea
            className="input profile__text"
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value);
              setSavedAt(null);
            }}
            rows={16}
            aria-label="Profil de goûts"
            placeholder="J'aime les objets bien faits, les matières naturelles…"
          />
          <div className="profile__bar">
            <span className="profile__status" aria-live="polite">
              {saveError ? (
                <span className="text-error">{saveError}</span>
              ) : dirty ? (
                "Modifications non enregistrées"
              ) : savedAt ? (
                "Enregistré ✓"
              ) : (
                `${draft.length.toLocaleString("fr-FR")} caractères`
              )}
            </span>
            <button className="btn btn--primary" onClick={save} disabled={!dirty || saving || !draft.trim()}>
              {saving ? "Enregistrement…" : "Enregistrer"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
