// Tous les appels réseau de l'application passent par ce fichier.
// Deux implémentations partagent la même interface `Api` :
//   - realApi : appelle le back-end Python dont l'URL est enregistrée dans les Réglages ;
//   - demoApi : données fictives en mémoire (mode démo, quand aucune URL n'est configurée).
import { buildDemoState, DEMO_CATALOG, DEMO_MASTER_PROMPT } from "./demoData";
import type {
  Item,
  ItemCreate,
  ItemUpdate,
  Profile,
  Reaction,
  Result,
  Search,
} from "./types";
import { MAX_ITERATIONS } from "./types";

export interface Api {
  health(): Promise<{ status: string }>;
  getProfile(): Promise<Profile>;
  updateProfile(profile: Profile): Promise<Profile>;
  listItems(): Promise<Item[]>;
  createItem(data: ItemCreate): Promise<Item>;
  getItem(id: number): Promise<Item>;
  updateItem(id: number, data: ItemUpdate): Promise<Item>;
  deleteItem(id: number): Promise<void>;
  cogitate(itemId: number, feedback: string | null): Promise<{ search_id: number }>;
  listSearches(itemId: number): Promise<Search[]>;
  getSearch(id: number): Promise<Search>;
  setReaction(resultId: number, reaction: Reaction | null): Promise<Result>;
}

/** Erreur renvoyée par l'API (status = 0 pour une erreur réseau). */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return "Une erreur inattendue est survenue.";
}

// ---------------------------------------------------------------------------
// Réglage : URL du back-end
// ---------------------------------------------------------------------------

const BACKEND_URL_KEY = "cogito.backendUrl";
export const BACKEND_CHANGED_EVENT = "cogito:backend-changed";

export function getBackendUrl(): string {
  try {
    return (localStorage.getItem(BACKEND_URL_KEY) ?? "").trim();
  } catch {
    return "";
  }
}

export function setBackendUrl(url: string) {
  const clean = url.trim().replace(/\/+$/, "");
  try {
    if (clean) localStorage.setItem(BACKEND_URL_KEY, clean);
    else localStorage.removeItem(BACKEND_URL_KEY);
  } catch {
    /* stockage indisponible : le réglage ne sera pas conservé */
  }
  window.dispatchEvent(new Event(BACKEND_CHANGED_EVENT));
}

export const isDemoMode = () => getBackendUrl() === "";

/** L'implémentation à utiliser, selon la présence d'une URL de back-end. */
export function api(): Api {
  const url = getBackendUrl();
  return url ? realApi(url) : demoApi;
}

// ---------------------------------------------------------------------------
// Implémentation réelle
// ---------------------------------------------------------------------------

const TIMEOUT_MS = 90_000; // le back-end gratuit peut mettre ~1 min à se réveiller

async function request<T>(
  baseUrl: string,
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(baseUrl + path, {
      method: init.method ?? "GET",
      headers: init.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: controller.signal,
    });
  } catch (err) {
    const timedOut = err instanceof DOMException && err.name === "AbortError";
    throw new ApiError(
      timedOut
        ? "Le back-end met trop de temps à répondre."
        : "Impossible de joindre le back-end. Vérifie ta connexion et l'URL dans les Réglages.",
      0,
    );
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    throw new ApiError(await readErrorDetail(res), res.status);
  }
  if (res.status === 204) return undefined as T;
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError("Réponse illisible du back-end.", res.status);
  }
}

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    // Erreurs de validation FastAPI : [{ loc, msg, type }, …]
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join(" · ");
    }
  } catch {
    /* corps non JSON */
  }
  if (res.status === 404) return "Élément introuvable.";
  if (res.status >= 500) return "Le back-end a rencontré une erreur.";
  return `Erreur ${res.status}`;
}

function realApi(base: string): Api {
  return {
    health: () => request(base, "/health"),
    getProfile: () => request(base, "/profile"),
    updateProfile: (profile) => request(base, "/profile", { method: "PUT", body: profile }),
    listItems: () => request(base, "/items"),
    createItem: (data) => request(base, "/items", { method: "POST", body: data }),
    getItem: (id) => request(base, `/items/${id}`),
    updateItem: (id, data) => request(base, `/items/${id}`, { method: "PATCH", body: data }),
    deleteItem: (id) => request(base, `/items/${id}`, { method: "DELETE" }),
    cogitate: (itemId, feedback) =>
      request(base, `/items/${itemId}/cogitate`, { method: "POST", body: { feedback } }),
    listSearches: (itemId) => request(base, `/items/${itemId}/searches`),
    getSearch: (id) => request(base, `/searches/${id}`),
    setReaction: (resultId, reaction) =>
      request(base, `/results/${resultId}`, { method: "PATCH", body: { reaction } }),
  };
}

// ---------------------------------------------------------------------------
// Implémentation démo (données fictives, conservées dans le navigateur)
// ---------------------------------------------------------------------------

const DEMO_KEY = "cogito.demo.v1";
const DEMO_SEARCH_MS = 5_000;
const DEMO_LATENCY_MS = 250;

type StoredItem = Omit<Item, "iterations_count">;
interface DemoState {
  profile: Profile;
  items: StoredItem[];
  searches: Search[];
  nextItemId: number;
  nextSearchId: number;
  nextResultId: number;
}

let demoState: DemoState | null = null;

function loadDemo(): DemoState {
  if (demoState) return demoState;
  try {
    const raw = localStorage.getItem(DEMO_KEY);
    if (raw) demoState = JSON.parse(raw) as DemoState;
  } catch {
    demoState = null;
  }
  if (!demoState) {
    demoState = { profile: { master_prompt: DEMO_MASTER_PROMPT }, ...buildDemoState() };
  }
  return demoState;
}

function saveDemo() {
  try {
    localStorage.setItem(DEMO_KEY, JSON.stringify(demoState));
  } catch {
    /* stockage indisponible : les données restent en mémoire */
  }
}

/** Remet les données de démonstration à zéro. */
export function resetDemo() {
  demoState = null;
  try {
    localStorage.removeItem(DEMO_KEY);
  } catch {
    /* rien */
  }
}

const delay = (ms = DEMO_LATENCY_MS) => new Promise((r) => setTimeout(r, ms));
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v));

/** Fait avancer les recherches fictives selon le temps écoulé depuis leur lancement. */
function advanceDemoSearches(state: DemoState) {
  let changed = false;
  for (const s of state.searches) {
    if (s.status !== "pending" && s.status !== "running") continue;
    const elapsed = Date.now() - new Date(s.created_at).getTime();
    if (elapsed >= DEMO_SEARCH_MS) {
      finishDemoSearch(state, s);
      changed = true;
    } else if (s.status === "pending" && elapsed > 800) {
      s.status = "running";
      changed = true;
    }
  }
  if (changed) saveDemo();
}

function finishDemoSearch(state: DemoState, search: Search) {
  const item = state.items.find((i) => i.id === search.item_id);
  if (!item) return;
  const pool = DEMO_CATALOG[item.category];
  const alreadyShown = new Set(
    state.searches
      .filter((s) => s.item_id === item.id && s.id !== search.id)
      .flatMap((s) => s.results.map((r) => r.name)),
  );
  // Les produits pas encore proposés d'abord, puis les autres ; ceux dans le budget en tête.
  const ordered = [...pool].sort((a, b) => {
    const seen = Number(alreadyShown.has(a.name)) - Number(alreadyShown.has(b.name));
    if (seen) return seen;
    const overA = item.budget_max !== null && (a.price ?? 0) > item.budget_max ? 1 : 0;
    const overB = item.budget_max !== null && (b.price ?? 0) > item.budget_max ? 1 : 0;
    return overA - overB || Math.random() - 0.5;
  });
  const picked = ordered.slice(0, Math.min(5, ordered.length));
  let score = 88 + Math.floor(Math.random() * 9);
  search.results = picked.map((p) => {
    const r: Result = {
      ...p,
      id: state.nextResultId++,
      search_id: search.id,
      score: Math.max(55, score),
      reaction: null,
    };
    score -= 3 + Math.floor(Math.random() * 6);
    return r;
  });
  search.status = "done";
  search.cost_usd = Math.round((0.06 + Math.random() * 0.14) * 1000) / 1000;
  if (item.status === "en_recherche") item.status = "resultats";
}

function withCount(state: DemoState, item: StoredItem): Item {
  const done = state.searches.filter((s) => s.item_id === item.id && s.status === "done").length;
  return clone({ ...item, iterations_count: done });
}

function findItem(state: DemoState, id: number): StoredItem {
  const item = state.items.find((i) => i.id === id);
  if (!item) throw new ApiError("Article introuvable", 404);
  return item;
}

const demoApi: Api = {
  async health() {
    await delay();
    return { status: "ok" };
  },
  async getProfile() {
    await delay();
    return clone(loadDemo().profile);
  },
  async updateProfile(profile) {
    await delay();
    if (!profile.master_prompt.trim()) throw new ApiError("Le profil ne peut pas être vide.", 422);
    const s = loadDemo();
    s.profile = { master_prompt: profile.master_prompt };
    saveDemo();
    return clone(s.profile);
  },
  async listItems() {
    await delay();
    const s = loadDemo();
    advanceDemoSearches(s);
    return [...s.items]
      .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id)
      .map((i) => withCount(s, i));
  },
  async createItem(data) {
    await delay();
    if (!data.title.trim()) throw new ApiError("Le titre est obligatoire.", 422);
    const s = loadDemo();
    const item: StoredItem = {
      id: s.nextItemId++,
      title: data.title.trim(),
      category: data.category,
      notes: data.notes ?? null,
      custom_prompt: data.custom_prompt ?? null,
      budget_max: data.budget_max ?? null,
      status: "a_chercher",
      created_at: new Date().toISOString(),
    };
    s.items.push(item);
    saveDemo();
    return withCount(s, item);
  },
  async getItem(id) {
    await delay();
    const s = loadDemo();
    advanceDemoSearches(s);
    return withCount(s, findItem(s, id));
  },
  async updateItem(id, data) {
    await delay();
    const s = loadDemo();
    const item = findItem(s, id);
    Object.assign(item, data);
    saveDemo();
    return withCount(s, item);
  },
  async deleteItem(id) {
    await delay();
    const s = loadDemo();
    findItem(s, id);
    s.items = s.items.filter((i) => i.id !== id);
    s.searches = s.searches.filter((x) => x.item_id !== id);
    saveDemo();
  },
  async cogitate(itemId, feedback) {
    await delay();
    const s = loadDemo();
    advanceDemoSearches(s);
    const item = findItem(s, itemId);
    const searches = s.searches.filter((x) => x.item_id === itemId);
    if (searches.some((x) => x.status === "pending" || x.status === "running")) {
      throw new ApiError("Une recherche est déjà en cours pour cet article", 409);
    }
    const done = searches.filter((x) => x.status === "done").length;
    if (done >= MAX_ITERATIONS) {
      throw new ApiError(`Limite de ${MAX_ITERATIONS} itérations atteinte pour cet article`, 409);
    }
    const search: Search = {
      id: s.nextSearchId++,
      item_id: itemId,
      iteration: done + 1,
      feedback,
      status: "pending",
      error: null,
      created_at: new Date().toISOString(),
      cost_usd: null,
      results: [],
    };
    s.searches.push(search);
    item.status = "en_recherche";
    saveDemo();
    return { search_id: search.id };
  },
  async listSearches(itemId) {
    await delay();
    const s = loadDemo();
    findItem(s, itemId);
    advanceDemoSearches(s);
    return clone(s.searches.filter((x) => x.item_id === itemId).sort((a, b) => a.id - b.id));
  },
  async getSearch(id) {
    await delay(120);
    const s = loadDemo();
    advanceDemoSearches(s);
    const search = s.searches.find((x) => x.id === id);
    if (!search) throw new ApiError("Recherche introuvable", 404);
    return clone(search);
  },
  async setReaction(resultId, reaction) {
    await delay(150);
    const s = loadDemo();
    for (const search of s.searches) {
      const r = search.results.find((x) => x.id === resultId);
      if (r) {
        r.reaction = reaction;
        saveDemo();
        return clone(r);
      }
    }
    throw new ApiError("Résultat introuvable", 404);
  },
};
