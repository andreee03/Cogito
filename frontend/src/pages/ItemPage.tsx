import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ItemForm } from "../components/ItemForm";
import { ProductCard } from "../components/ProductCard";
import { Thinking } from "../components/Thinking";
import { EmptyState, ErrorState, IterationMeter, Sheet, Spinner, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api, errorMessage } from "../lib/api";
import { formatBudget, formatCost, formatDate, formatDateTime } from "../lib/format";
import type { Item, Reaction, Result, Search } from "../lib/types";
import { MAX_ITERATIONS, categoryLabel } from "../lib/types";

const POLL_MS = 3_000;
const isActive = (s: Search) => s.status === "pending" || s.status === "running";

export function ItemPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();

  const { data, setData, error, loading, reload } = useAsync(async () => {
    const [item, searches] = await Promise.all([api().getItem(id), api().listSearches(id)]);
    return { item, searches };
  }, [id]);

  const item = data?.item;
  const searches = useMemo(() => data?.searches ?? [], [data]);
  const doneSearches = useMemo(() => searches.filter((s) => s.status === "done"), [searches]);
  const active = searches.find(isActive) ?? null;
  const lastSearch = searches[searches.length - 1];
  const failed = !active && lastSearch?.status === "error" ? lastSearch : null;

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const selected =
    doneSearches.find((s) => s.id === selectedId) ?? doneSearches[doneSearches.length - 1] ?? null;

  const [launching, setLaunching] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [editing, setEditing] = useState(false);
  const [pollError, setPollError] = useState<string | null>(null);
  const [pollKey, setPollKey] = useState(0);

  const patchSearch = useCallback(
    (next: Search) =>
      setData((d) => d && { ...d, searches: d.searches.map((s) => (s.id === next.id ? next : s)) }),
    [setData],
  );
  const patchItem = useCallback((next: Item) => setData((d) => d && { ...d, item: next }), [setData]);

  // Interrogation toutes les 3 s tant qu'une recherche est en attente ou en cours.
  const activeId = active?.id;
  const failures = useRef(0);
  useEffect(() => {
    if (activeId === undefined) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    failures.current = 0;
    setPollError(null);

    const tick = async () => {
      try {
        const s = await api().getSearch(activeId);
        if (stopped) return;
        failures.current = 0;
        patchSearch(s);
        if (!isActive(s)) {
          if (s.status === "done") setSelectedId(s.id);
          await reload({ silent: true }); // statut et compteur d'itérations à jour
          return;
        }
      } catch (err) {
        if (stopped) return;
        if (++failures.current >= 3) {
          setPollError(errorMessage(err));
          return;
        }
      }
      timer = setTimeout(tick, POLL_MS);
    };
    timer = setTimeout(tick, POLL_MS);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [activeId, pollKey, patchSearch, reload]);

  async function cogitate(withFeedback: string | null) {
    setLaunching(true);
    setActionError(null);
    try {
      await api().cogitate(id, withFeedback);
      setFeedback("");
      await reload({ silent: true });
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setLaunching(false);
    }
  }

  async function react(result: Result, reaction: Reaction | null) {
    const previous = result.reaction;
    const apply = (r: Reaction | null) =>
      setData(
        (d) =>
          d && {
            ...d,
            searches: d.searches.map((s) =>
              s.id !== result.search_id
                ? s
                : { ...s, results: s.results.map((x) => (x.id === result.id ? { ...x, reaction: r } : x)) },
            ),
          },
      );
    apply(reaction); // mise à jour immédiate, annulée en cas d'échec
    try {
      await api().setReaction(result.id, reaction);
    } catch (err) {
      apply(previous);
      setActionError(errorMessage(err));
    }
  }

  async function toggleBought() {
    if (!item) return;
    setActionError(null);
    const status = item.status === "achete" ? (item.iterations_count > 0 ? "resultats" : "a_chercher") : "achete";
    try {
      patchItem(await api().updateItem(id, { status }));
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  async function remove() {
    if (!item || !window.confirm(`Supprimer « ${item.title} » et toutes ses recherches ?`)) return;
    try {
      await api().deleteItem(id);
      navigate("/");
    } catch (err) {
      setActionError(errorMessage(err));
    }
  }

  if (loading && !data) return <div className="page"><Spinner /></div>;
  if (error && !data) {
    return (
      <div className="page">
        <BackLink />
        <ErrorState message={error} onRetry={() => reload()} />
      </div>
    );
  }
  if (!item) return null;

  const limitReached = item.iterations_count >= MAX_ITERATIONS;
  const canCogitate = !active && !limitReached && !launching;
  const sortedResults = selected ? [...selected.results].sort((a, b) => b.score - a.score) : [];

  return (
    <div className="page page--detail">
      <BackLink />

      <header className="detail-head">
        <div className="detail-head__info">
          <p className="eyebrow">
            {categoryLabel(item.category)} · ajouté le {formatDate(item.created_at)}
          </p>
          <h1 className="page-title page-title--detail">{item.title}</h1>
          <div className="detail-head__meta">
            <StatusBadge status={item.status} />
            <span className="meta-pill">{formatBudget(item.budget_max)}</span>
            <IterationMeter count={item.iterations_count} />
          </div>
          {item.notes && <p className="detail-head__notes">{item.notes}</p>}
          {item.custom_prompt && (
            <blockquote className="detail-head__prompt">
              <span className="eyebrow">Prompt spécifique</span>
              {item.custom_prompt}
            </blockquote>
          )}
          <div className="detail-head__tools">
            <button className="link-btn" onClick={() => setEditing(true)}>
              Modifier
            </button>
            <button className="link-btn" onClick={toggleBought}>
              {item.status === "achete" ? "Remettre dans la liste" : "Marquer comme acheté"}
            </button>
            <button className="link-btn link-btn--danger" onClick={remove}>
              Supprimer
            </button>
          </div>
        </div>

        <div className="detail-head__cta">
          <button className="btn btn--cogito" disabled={!canCogitate} onClick={() => cogitate(null)}>
            <span className="btn--cogito__label">
              {launching ? "Lancement…" : active ? "En réflexion…" : doneSearches.length ? "Cogiter encore" : "Cogiter"}
            </span>
            <span className="btn--cogito__sub">
              {limitReached
                ? "3 itérations atteintes"
                : `Itération ${item.iterations_count + 1} sur ${MAX_ITERATIONS}`}
            </span>
          </button>
        </div>
      </header>

      {actionError && (
        <div className="notice notice--error" role="alert">
          <p>{actionError}</p>
          <button className="icon-btn" aria-label="Fermer" onClick={() => setActionError(null)}>
            <svg viewBox="0 0 24 24" aria-hidden>
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
      )}

      {active &&
        (pollError ? (
          <ErrorState
            compact
            message={`Impossible de suivre la recherche en cours : ${pollError}`}
            onRetry={() => setPollKey((k) => k + 1)}
          />
        ) : (
          <Thinking since={active.created_at} iteration={active.iteration} />
        ))}

      {failed && (
        <div className="notice notice--error">
          <p>
            <strong>La dernière recherche a échoué.</strong> {failed.error ?? "Erreur inconnue."} Elle ne compte pas
            comme une itération : tu peux relancer.
          </p>
        </div>
      )}

      {doneSearches.length > 0 && (
        <section className="results">
          <div className="iter-tabs" role="tablist" aria-label="Historique des itérations">
            {doneSearches.map((s) => (
              <button
                key={s.id}
                role="tab"
                aria-selected={selected?.id === s.id}
                className={`iter-tab ${selected?.id === s.id ? "is-active" : ""}`}
                onClick={() => setSelectedId(s.id)}
              >
                <span className="iter-tab__n">Itération {s.iteration}</span>
                <span className="iter-tab__date">{formatDateTime(s.created_at)}</span>
              </button>
            ))}
          </div>

          {selected && (
            <div className="iter-panel" key={selected.id}>
              <div className="iter-panel__meta">
                {selected.feedback ? (
                  <p className="iter-panel__feedback">
                    <span className="eyebrow">Ton retour</span>« {selected.feedback} »
                  </p>
                ) : (
                  <p className="iter-panel__feedback iter-panel__feedback--none">
                    {selected.iteration === 1 ? "Première recherche, d'après ton profil." : "Relancée sans retour."}
                  </p>
                )}
                <p className="iter-panel__cost">
                  {selected.results.length} proposition{selected.results.length > 1 ? "s" : ""} · recherche :{" "}
                  {formatCost(selected.cost_usd)}
                </p>
              </div>

              {sortedResults.length === 0 ? (
                <EmptyState title="Aucun résultat">
                  Cogito n'a rien trouvé de convaincant cette fois-ci. Précise ta demande ci-dessous et relance.
                </EmptyState>
              ) : (
                <div className="pgrid">
                  {sortedResults.map((r, i) => (
                    <ProductCard key={r.id} result={r} index={i} onReact={react} />
                  ))}
                </div>
              )}
            </div>
          )}

          <section className="refine">
            <div>
              <h2 className="section-title">Affiner</h2>
              <p className="refine__hint">
                {limitReached
                  ? "Les 3 itérations ont été utilisées pour cet article."
                  : "Dis à Cogito ce qui te plaît ou non : tes 👍 / 👎 sont aussi pris en compte."}
              </p>
            </div>
            <textarea
              className="input"
              rows={3}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Ex. : trop classique, moins cher, plutôt en laine…"
              disabled={limitReached}
            />
            <button
              className="btn btn--primary"
              disabled={!canCogitate || !feedback.trim()}
              onClick={() => cogitate(feedback.trim())}
            >
              Relancer avec ce retour
            </button>
          </section>
        </section>
      )}

      {!active && !failed && doneSearches.length === 0 && (
        <EmptyState title="Pas encore de recherche">
          Appuie sur <strong>Cogiter</strong> : Cogito cherchera des produits qui correspondent à cet article et à tes
          goûts.
        </EmptyState>
      )}

      {editing && (
        <Sheet title="Modifier l'article" onClose={() => setEditing(false)}>
          <ItemForm
            initial={item}
            submitLabel="Enregistrer"
            onCancel={() => setEditing(false)}
            onSubmit={async (values) => {
              patchItem(await api().updateItem(id, values));
              setEditing(false);
            }}
          />
        </Sheet>
      )}
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/" className="back-link">
      <svg viewBox="0 0 24 24" aria-hidden>
        <path d="M15 6l-6 6 6 6" />
      </svg>
      Ma liste
    </Link>
  );
}
