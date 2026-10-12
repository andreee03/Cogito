import { useState } from "react";
import { formatPrice, hostname } from "../lib/format";
import type { Reaction, Result } from "../lib/types";

export function ProductImage({ src, alt, brand }: { src: string | null; alt: string; brand: string | null }) {
  const [state, setState] = useState<"loading" | "ok" | "error">(src ? "loading" : "error");
  return (
    <div className={`pimg pimg--${state}`}>
      {src && state !== "error" && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onLoad={() => setState("ok")}
          onError={() => setState("error")}
        />
      )}
      {state === "error" && (
        <div className="pimg__placeholder" aria-hidden>
          <span className="pimg__mono">{(brand || alt).trim().charAt(0).toUpperCase()}</span>
          <span className="pimg__caption">{brand || "Sans image"}</span>
        </div>
      )}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, Math.round(score)));
  const c = 2 * Math.PI * 16;
  return (
    <div className="score" title={`Correspondance : ${s}/100`}>
      <svg viewBox="0 0 40 40" aria-hidden>
        <circle cx="20" cy="20" r="16" className="score__track" />
        <circle
          cx="20"
          cy="20"
          r="16"
          className="score__fill"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - s / 100)}
        />
      </svg>
      <span className="score__value">{s}</span>
      <span className="sr-only">sur 100 de correspondance</span>
    </div>
  );
}

interface Props {
  result: Result;
  index: number;
  onReact: (result: Result, reaction: Reaction | null) => void;
}

export function ProductCard({ result, index, onReact }: Props) {
  const toggle = (r: Reaction) => onReact(result, result.reaction === r ? null : r);

  return (
    <article
      className={`pcard ${result.reaction === "dislike" ? "pcard--dimmed" : ""}`}
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <div className="pcard__media">
        <ProductImage src={result.image_url} alt={result.name} brand={result.brand} />
        <ScoreRing score={result.score} />
      </div>

      <div className="pcard__body">
        <div className="pcard__head">
          {result.brand && <p className="eyebrow">{result.brand}</p>}
          <h3 className="pcard__name">{result.name}</h3>
          <p className="pcard__price">{formatPrice(result.price, result.currency)}</p>
        </div>

        <ul className="badges">
          <li className={`badge ${result.link_verified ? "badge--ok" : "badge--warn"}`}>
            {result.link_verified ? "Lien vérifié" : "Lien non vérifié"}
          </li>
          <li className={`badge ${result.price_verified ? "badge--ok" : "badge--warn"}`}>
            {result.price_verified ? "Prix vérifié" : "Prix à vérifier"}
          </li>
        </ul>

        <div className="pcard__why">
          <p className="pcard__why-label">Pourquoi ça te correspond</p>
          <p>{result.why_it_fits}</p>
        </div>

        {result.description && <p className="pcard__desc">{result.description}</p>}

        <div className="pcard__actions">
          <div className="react" role="group" aria-label="Ta réaction">
            <button
              className={`react__btn ${result.reaction === "like" ? "is-active" : ""}`}
              onClick={() => toggle("like")}
              aria-pressed={result.reaction === "like"}
              aria-label="J'aime"
            >
              👍
            </button>
            <button
              className={`react__btn ${result.reaction === "dislike" ? "is-active" : ""}`}
              onClick={() => toggle("dislike")}
              aria-pressed={result.reaction === "dislike"}
              aria-label="Je n'aime pas"
            >
              👎
            </button>
          </div>
          <a className="btn btn--dark btn--sm" href={result.url} target="_blank" rel="noopener noreferrer">
            Voir / Acheter
            <svg viewBox="0 0 24 24" className="btn__icon" aria-hidden>
              <path d="M7 17L17 7M9 7h8v8" />
            </svg>
          </a>
        </div>
        <p className="pcard__host">{hostname(result.url)}</p>
      </div>
    </article>
  );
}
