import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { ItemStatus } from "../lib/types";
import { MAX_ITERATIONS, statusLabel } from "../lib/types";

export function StatusBadge({ status }: { status: ItemStatus }) {
  return (
    <span className={`status status--${status}`}>
      <span className="status__dot" aria-hidden />
      {statusLabel(status)}
    </span>
  );
}

export function IterationMeter({ count }: { count: number }) {
  return (
    <span className="iter" title={`${count} itération${count > 1 ? "s" : ""} sur ${MAX_ITERATIONS}`}>
      <span className="iter__dots" aria-hidden>
        {Array.from({ length: MAX_ITERATIONS }, (_, i) => (
          <span key={i} className={i < count ? "is-on" : ""} />
        ))}
      </span>
      {Math.min(count, MAX_ITERATIONS)}/{MAX_ITERATIONS}
    </span>
  );
}

export function Spinner({ label = "Chargement…" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner__ring" aria-hidden />
      <span className="spinner__label">{label}</span>
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  compact = false,
}: {
  message: string;
  onRetry?: () => void;
  compact?: boolean;
}) {
  return (
    <div className={`error-state ${compact ? "error-state--compact" : ""}`} role="alert">
      <p className="error-state__title">Quelque chose s'est mal passé</p>
      <p className="error-state__msg">{message}</p>
      {onRetry && (
        <button className="btn btn--ghost" onClick={onRetry}>
          Réessayer
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <svg className="empty-state__mark" viewBox="0 0 80 80" aria-hidden>
        <circle cx="40" cy="40" r="30" />
        <path d="M28 44c4 5 20 5 24 0" />
        <circle cx="31" cy="34" r="1.6" className="fill" />
        <circle cx="49" cy="34" r="1.6" className="fill" />
      </svg>
      <h2 className="empty-state__title">{title}</h2>
      {children && <div className="empty-state__body">{children}</div>}
      {action}
    </div>
  );
}

/** Feuille modale : glisse du bas sur mobile, centrée sur ordinateur. */
export function Sheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    ref.current?.querySelector<HTMLElement>("input, textarea, select")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  // Portail : la feuille sort du conteneur animé de la page (sinon position: fixed est piégée).
  return createPortal(
    <div className="sheet-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} ref={ref}>
        <div className="sheet__head">
          <h2 className="sheet__title">{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label="Fermer">
            <svg viewBox="0 0 24 24" aria-hidden>
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}
