import { useCallback, useEffect, useRef, useState } from "react";
import { BACKEND_CHANGED_EVENT, errorMessage } from "../lib/api";

/** Charge une donnée asynchrone, avec état de chargement, erreur et rechargement.
 *  Recharge automatiquement quand l'URL du back-end change. */
export function useAsync<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const callId = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const load = useCallback(loader, deps);

  const reload = useCallback(
    async (opts: { silent?: boolean } = {}) => {
      const id = ++callId.current;
      if (!opts.silent) {
        setLoading(true);
        setError(null);
      }
      try {
        const value = await load();
        if (id === callId.current) {
          setData(value);
          setError(null);
        }
      } catch (err) {
        if (id === callId.current) setError(errorMessage(err));
      } finally {
        if (id === callId.current) setLoading(false);
      }
    },
    [load],
  );

  useEffect(() => {
    reload();
    const onChange = () => reload();
    window.addEventListener(BACKEND_CHANGED_EVENT, onChange);
    return () => window.removeEventListener(BACKEND_CHANGED_EVENT, onChange);
  }, [reload]);

  return { data, setData, error, loading, reload };
}
