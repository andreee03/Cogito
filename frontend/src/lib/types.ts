// Types partagés par l'implémentation réelle et l'implémentation démo de l'API.
// Ils reflètent exactement le contrat du back-end (clés en snake_case, dates ISO 8601).

export type Category = "vetements" | "outils" | "deco" | "autre";
export type ItemStatus = "a_chercher" | "en_recherche" | "resultats" | "achete";
export type SearchStatus = "pending" | "running" | "done" | "error";
export type Reaction = "like" | "dislike";

export interface Profile {
  master_prompt: string;
}

export interface Item {
  id: number;
  title: string;
  category: Category;
  notes: string | null;
  custom_prompt: string | null;
  budget_max: number | null;
  status: ItemStatus;
  created_at: string;
  iterations_count: number;
}

export interface ItemCreate {
  title: string;
  category: Category;
  notes?: string | null;
  custom_prompt?: string | null;
  budget_max?: number | null;
}

export type ItemUpdate = Partial<ItemCreate> & { status?: ItemStatus };

export interface Result {
  id: number;
  search_id: number;
  name: string;
  brand: string | null;
  price: number | null;
  currency: string | null;
  url: string;
  image_url: string | null;
  description: string | null;
  why_it_fits: string;
  score: number;
  link_verified: boolean;
  price_verified: boolean;
  reaction: Reaction | null;
}

export interface Search {
  id: number;
  item_id: number;
  iteration: number;
  feedback: string | null;
  status: SearchStatus;
  error: string | null;
  created_at: string;
  cost_usd: number | null;
  results: Result[];
}

export interface NotionImportResult {
  imported: number;
  skipped: number;
  items: Item[];
}

export const MAX_ITERATIONS = 3;

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "vetements", label: "Vêtements" },
  { value: "outils", label: "Outils" },
  { value: "deco", label: "Déco" },
  { value: "autre", label: "Autre" },
];

export const STATUSES: { value: ItemStatus; label: string }[] = [
  { value: "a_chercher", label: "À chercher" },
  { value: "en_recherche", label: "En recherche" },
  { value: "resultats", label: "Résultats prêts" },
  { value: "achete", label: "Acheté" },
];

export const categoryLabel = (c: Category) =>
  CATEGORIES.find((x) => x.value === c)?.label ?? c;

export const statusLabel = (s: ItemStatus) =>
  STATUSES.find((x) => x.value === s)?.label ?? s;
