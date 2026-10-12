import { useEffect, useState } from "react";
import { BACKEND_CHANGED_EVENT, isDemoMode } from "../lib/api";

export function useDemoMode() {
  const [demo, setDemo] = useState(isDemoMode);
  useEffect(() => {
    const update = () => setDemo(isDemoMode());
    window.addEventListener(BACKEND_CHANGED_EVENT, update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener(BACKEND_CHANGED_EVENT, update);
      window.removeEventListener("storage", update);
    };
  }, []);
  return demo;
}
