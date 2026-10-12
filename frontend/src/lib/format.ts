const priceFormatters = new Map<string, Intl.NumberFormat>();

/** Prix au format français : « 1 299,00 € ». */
export function formatPrice(value: number | null, currency: string | null = "EUR"): string {
  if (value === null || value === undefined) return "Prix inconnu";
  const code = (currency || "EUR").toUpperCase();
  let fmt = priceFormatters.get(code);
  if (!fmt) {
    try {
      fmt = new Intl.NumberFormat("fr-FR", { style: "currency", currency: code });
    } catch {
      // Devise inconnue : on retombe sur l'euro plutôt que de planter.
      fmt = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" });
    }
    priceFormatters.set(code, fmt);
  }
  return fmt.format(value);
}

/** Budget : « 250 € » (sans décimales quand elles sont nulles). */
export function formatBudget(value: number | null): string {
  if (value === null || value === undefined) return "Budget libre";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: Number.isInteger(value) ? 0 : 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/** Coût d'une recherche en dollars : « 0,12 $ ». */
export function formatCost(value: number | null): string {
  if (value === null || value === undefined) return "coût inconnu";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "USD",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 2,
    maximumFractionDigits: value < 0.01 ? 4 : 2,
  }).format(value);
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("fr-FR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
