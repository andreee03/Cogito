import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ItemForm } from "../components/ItemForm";
import { EmptyState, ErrorState, IterationMeter, Sheet, Spinner, StatusBadge } from "../components/ui";
import { useAsync } from "../hooks/useAsync";
import { api } from "../lib/api";
import { formatBudget } from "../lib/format";
import type { Category, ItemStatus } from "../lib/types";
import { CATEGORIES, STATUSES, categoryLabel } from "../lib/types";

export function ListPage() {
  const navigate = useNavigate();
  const { data: items, error, loading, reload } = useAsync(() => api().listItems());
  const [category, setCategory] = useState<Category | "all">("all");
  const [status, setStatus] = useState<ItemStatus | "all">("all");
  const [adding, setAdding] = useState(false);

  const filtered = useMemo(
    () =>
      (items ?? []).filter(
        (i) => (category === "all" || i.category === category) && (status === "all" || i.status === status),
      ),
    [items, category, status],
  );

  const toFind = (items ?? []).filter((i) => i.status !== "achete").length;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">{new Date().toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}</p>
          <h1 className="page-title">Ma liste</h1>
          {items && items.length > 0 && (
            <p className="page-sub">
              {toFind === 0
                ? "Tout est trouvé. Rien ne presse."
                : `${toFind} envie${toFind > 1 ? "s" : ""} en cours de réflexion.`}
            </p>
          )}
        </div>
        <button className="btn btn--primary btn--add" onClick={() => setAdding(true)}>
          <span aria-hidden>+</span> Ajouter
        </button>
      </header>

      <div className="filters">
        <div className="chips" role="group" aria-label="Filtrer par catégorie">
          <button className={`chip ${category === "all" ? "is-active" : ""}`} onClick={() => setCategory("all")}>
            Tout
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.value}
              className={`chip ${category === c.value ? "is-active" : ""}`}
              onClick={() => setCategory(c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>
        <div className="chips chips--quiet" role="group" aria-label="Filtrer par statut">
          <button className={`chip ${status === "all" ? "is-active" : ""}`} onClick={() => setStatus("all")}>
            Tous statuts
          </button>
          {STATUSES.map((s) => (
            <button
              key={s.value}
              className={`chip ${status === s.value ? "is-active" : ""}`}
              onClick={() => setStatus(s.value)}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {loading && !items ? (
        <Spinner />
      ) : error && !items ? (
        <ErrorState message={error} onRetry={() => reload()} />
      ) : items && items.length === 0 ? (
        <EmptyState
          title="Ta liste est vide"
          action={
            <button className="btn btn--primary" onClick={() => setAdding(true)}>
              + Ajouter une première envie
            </button>
          }
        >
          Note ici ce que tu aimerais acheter. Cogito cherchera pour toi des pièces qui te ressemblent.
        </EmptyState>
      ) : filtered.length === 0 ? (
        <EmptyState
          title="Aucun article ne correspond"
          action={
            <button
              className="btn btn--ghost"
              onClick={() => {
                setCategory("all");
                setStatus("all");
              }}
            >
              Effacer les filtres
            </button>
          }
        />
      ) : (
        <ol className="item-list">
          {filtered.map((item, idx) => (
            <li key={item.id} style={{ animationDelay: `${idx * 50}ms` }}>
              <Link to={`/articles/${item.id}`} className={`item-card item-card--${item.status}`}>
                <span className="item-card__num" aria-hidden>
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <div className="item-card__main">
                  <p className="eyebrow">{categoryLabel(item.category)}</p>
                  <h2 className="item-card__title">{item.title}</h2>
                  <div className="item-card__meta">
                    <StatusBadge status={item.status} />
                    <span className="item-card__budget">{formatBudget(item.budget_max)}</span>
                    <IterationMeter count={item.iterations_count} />
                  </div>
                </div>
                <svg className="item-card__arrow" viewBox="0 0 24 24" aria-hidden>
                  <path d="M9 6l6 6-6 6" />
                </svg>
              </Link>
            </li>
          ))}
        </ol>
      )}

      {adding && (
        <Sheet title="Nouvelle envie" onClose={() => setAdding(false)}>
          <ItemForm
            submitLabel="Ajouter à ma liste"
            onCancel={() => setAdding(false)}
            onSubmit={async (data) => {
              const item = await api().createItem(data);
              setAdding(false);
              navigate(`/articles/${item.id}`);
            }}
          />
        </Sheet>
      )}
    </div>
  );
}
