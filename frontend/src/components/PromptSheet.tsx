import { useEffect, useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { Item } from "../lib/types";
import { ErrorState, Sheet, Spinner } from "./ui";

/** Prompt complet (Markdown) envoyé à Claude lors de la 1re itération. */
export function PromptSheet({ item, onClose }: { item: Item; onClose: () => void }) {
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    api()
      .getInitialPrompt(item.id)
      .then((r) => !cancelled && setMarkdown(r.markdown))
      .catch((err) => !cancelled && setError(errorMessage(err)));
    return () => {
      cancelled = true;
    };
  }, [item.id, attempt]);

  async function copy() {
    if (markdown === null) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
    } catch {
      setError("Impossible de copier : sélectionne le texte à la main.");
    }
  }

  function download() {
    if (markdown === null) return;
    const slug =
      item.title
        .normalize("NFD")
        .replace(/[̀-ͯ]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "") || "article";
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `prompt-${slug}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Sheet title="Prompt envoyé" onClose={onClose}>
      <p className="prompt-sheet__hint">
        Prompt de la première itération, avec ton profil et l'article tels qu'ils sont maintenant. Les itérations
        suivantes y ajoutent tes retours et les produits déjà proposés.
      </p>
      {error ? (
        <ErrorState compact message={error} onRetry={() => setAttempt((n) => n + 1)} />
      ) : markdown === null ? (
        <Spinner />
      ) : (
        <>
          <pre className="prompt-sheet__text">{markdown}</pre>
          <div className="prompt-sheet__bar">
            <button className="btn btn--ghost" onClick={copy}>
              {copied ? "Copié ✓" : "Copier"}
            </button>
            <button className="btn btn--primary" onClick={download}>
              Télécharger (.md)
            </button>
          </div>
        </>
      )}
    </Sheet>
  );
}
