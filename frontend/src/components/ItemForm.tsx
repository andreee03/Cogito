import { useState, type FormEvent } from "react";
import type { Category, ItemCreate } from "../lib/types";
import { CATEGORIES } from "../lib/types";

interface Props {
  initial?: Partial<ItemCreate>;
  submitLabel: string;
  onSubmit: (data: ItemCreate) => Promise<void>;
  onCancel?: () => void;
}

/** Formulaire d'article, utilisé pour l'ajout et la modification. */
export function ItemForm({ initial, submitLabel, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [category, setCategory] = useState<Category>(initial?.category ?? "vetements");
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [budget, setBudget] = useState(
    initial?.budget_max !== null && initial?.budget_max !== undefined ? String(initial.budget_max) : "",
  );
  const [customPrompt, setCustomPrompt] = useState(initial?.custom_prompt ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const budgetValue = budget.trim() === "" ? null : Number(budget.replace(",", "."));
  const budgetInvalid = budgetValue !== null && (Number.isNaN(budgetValue) || budgetValue < 0);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || budgetInvalid) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit({
        title: title.trim(),
        category,
        notes: notes.trim() || null,
        custom_prompt: customPrompt.trim() || null,
        budget_max: budgetValue,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enregistrement impossible.");
      setBusy(false);
    }
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <label className="field">
        <span className="field__label">Titre</span>
        <input
          className="input input--title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Ex. : une veste en lin"
          maxLength={200}
          required
        />
      </label>

      <fieldset className="field">
        <legend className="field__label">Catégorie</legend>
        <div className="segmented" role="radiogroup">
          {CATEGORIES.map((c) => (
            <label key={c.value} className={`segmented__opt ${category === c.value ? "is-active" : ""}`}>
              <input
                type="radio"
                name="category"
                value={c.value}
                checked={category === c.value}
                onChange={() => setCategory(c.value)}
              />
              {c.label}
            </label>
          ))}
        </div>
      </fieldset>

      <label className="field">
        <span className="field__label">Notes</span>
        <textarea
          className="input"
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Taille, couleur, usage, ce que tu veux éviter…"
        />
      </label>

      <label className="field">
        <span className="field__label">Budget max</span>
        <span className="input-affix">
          <input
            className="input"
            inputMode="decimal"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="Sans limite"
            aria-invalid={budgetInvalid}
          />
          <span className="input-affix__suffix">€</span>
        </span>
        {budgetInvalid && <span className="field__error">Indique un montant positif.</span>}
      </label>

      <details className="disclosure" open={Boolean(initial?.custom_prompt)}>
        <summary>Prompt personnalisé (optionnel)</summary>
        <label className="field">
          <span className="field__hint">Laisse vide pour utiliser ton profil de goûts.</span>
          <textarea
            className="input"
            rows={4}
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            placeholder="Ex. : c'est un cadeau pour mon père, qui aime les objets robustes et sans fioritures."
          />
        </label>
      </details>

      {error && (
        <p className="form__error" role="alert">
          {error}
        </p>
      )}

      <div className="form__actions">
        {onCancel && (
          <button type="button" className="btn btn--ghost" onClick={onCancel}>
            Annuler
          </button>
        )}
        <button className="btn btn--primary" disabled={busy || !title.trim() || budgetInvalid}>
          {busy ? "Enregistrement…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
