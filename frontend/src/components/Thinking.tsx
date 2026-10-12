import { useEffect, useState } from "react";

const PHRASES = [
  "Parcourt les boutiques…",
  "Compare les matières et les finitions…",
  "Écarte ce qui est trop banal…",
  "Relit ton profil de goûts…",
  "Vérifie les liens et les prix…",
  "Pèse le pour et le contre…",
];

/** État d'attente pendant une recherche (30 s à 3 min). */
export function Thinking({ since, iteration }: { since: string; iteration: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  const start = new Date(since).getTime();
  const elapsed = Math.max(0, Math.floor((now - (Number.isNaN(start) ? now : start)) / 1000));
  const phrase = PHRASES[Math.floor(elapsed / 6) % PHRASES.length];
  const mm = Math.floor(elapsed / 60);
  const ss = String(elapsed % 60).padStart(2, "0");

  return (
    <section className="thinking" aria-live="polite">
      <svg className="thinking__enso" viewBox="0 0 120 120" aria-hidden>
        <circle className="thinking__track" cx="60" cy="60" r="46" />
        <circle className="thinking__stroke" cx="60" cy="60" r="46" />
        <circle className="thinking__orb" cx="60" cy="14" r="4" />
      </svg>
      <p className="eyebrow">Itération {iteration}</p>
      <h2 className="thinking__title">
        Cogito réfléchit<span className="thinking__dots" aria-hidden><span>.</span><span>.</span><span>.</span></span>
      </h2>
      <p key={phrase} className="thinking__phrase">
        {phrase}
      </p>
      <p className="thinking__time">
        {mm}:{ss} · une recherche prend de 30 secondes à 3 minutes
      </p>
    </section>
  );
}
