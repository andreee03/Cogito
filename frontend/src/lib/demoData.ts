// Données fictives du mode démo : 4 articles et un catalogue de produits par catégorie.
import type { Category, Item, Result, Search } from "./types";

const img = (id: string) =>
  `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=900&q=75`;

export type DemoProduct = Omit<Result, "id" | "search_id" | "reaction" | "score">;

export const DEMO_CATALOG: Record<Category, DemoProduct[]> = {
  vetements: [
    {
      name: "Veste de travail en lin lavé",
      brand: "Arket",
      price: 149,
      currency: "EUR",
      url: "https://www.arket.com/",
      image_url: img("1591047139829-d91aecb6caea"),
      description: "Coupe droite, lin européen lavé à la pierre, boutons en corozo.",
      why_it_fits:
        "Une silhouette nette sans être stricte : le lin lavé vieillit bien et la coupe workwear répond à ton goût pour les pièces utiles et durables.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Surchemise en lin et coton",
      brand: "COS",
      price: 125,
      currency: "EUR",
      url: "https://www.cos.com/",
      image_url: img("1594633312681-425c7b97ccd1"),
      description: "Mélange lin-coton, col cubain, poches plaquées.",
      why_it_fits:
        "Le col cubain apporte une touche d'originalité sans tomber dans l'excentrique, et la teinte sable se marie avec une garde-robe neutre.",
      link_verified: true,
      price_verified: false,
    },
    {
      name: "Blouson Hector en lin indigo",
      brand: "A.P.C.",
      price: 295,
      currency: "EUR",
      url: "https://www.apc.fr/",
      image_url: img("1551028719-00167b16eac5"),
      description: "Lin teint en indigo, doublure partielle, fabriqué au Portugal.",
      why_it_fits:
        "Une pièce signature : l'indigo se patine avec le temps. Un peu au-dessus du budget, mais d'une qualité qui se justifie.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Veste Andrea en lin ivoire",
      brand: "Officine Générale",
      price: 240,
      currency: "EUR",
      url: "https://www.officinegenerale.com/",
      image_url: img("1490481651871-ab68de25d43d"),
      description: "Veste déstructurée, lin italien, épaules naturelles.",
      why_it_fits:
        "L'élégance parisienne décontractée : déstructurée, elle se porte aussi bien sur un t-shirt que sur une chemise.",
      link_verified: false,
      price_verified: false,
    },
    {
      name: "Chemise oversize en lin brut",
      brand: "Sézane",
      price: 110,
      currency: "EUR",
      url: "https://www.sezane.com/",
      image_url: img("1598300042247-d088f8ab3a91"),
      description: "Lin brut non teint, coupe ample, finitions nacre.",
      why_it_fits:
        "Plus accessible, avec un grain de lin brut très présent : une texture qui fait toute la différence de près.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Veste kimono en lin teint main",
      brand: "Monsieur Lacenaire",
      price: 210,
      currency: "EUR",
      url: "https://www.monsieurlacenaire.com/",
      image_url: img("1576566588028-4147f3842f27"),
      description: "Petite série, teinture végétale, coupe kimono croisée.",
      why_it_fits:
        "La proposition la plus originale : une coupe kimono rarement vue, produite en petite série en France.",
      link_verified: false,
      price_verified: true,
    },
  ],
  deco: [
    {
      name: "Lampe de table PC en verre opalin",
      brand: "HAY",
      price: 169,
      currency: "EUR",
      url: "https://www.hay.dk/",
      image_url: img("1507473885765-e6ed057f782c"),
      description: "Abat-jour en verre opalin, pied en acier laqué.",
      why_it_fits:
        "Une lumière diffuse et douce, une forme simple mais reconnaissable : du design accessible qui ne fait pas « catalogue ».",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Lampe Panthella Mini",
      brand: "Louis Poulsen",
      price: 395,
      currency: "EUR",
      url: "https://www.louispoulsen.com/",
      image_url: img("1513506003901-1e6a229e2d15"),
      description: "Dessinée par Verner Panton, réédition en acier laqué.",
      why_it_fits:
        "Un classique du design danois, intemporel. Au-dessus du budget, mais c'est un objet que l'on garde toute une vie.",
      link_verified: true,
      price_verified: false,
    },
    {
      name: "Lampe à poser Gräshoppa",
      brand: "Gubi",
      price: 449,
      currency: "EUR",
      url: "https://www.gubi.com/",
      image_url: img("1534349762230-e0cadf78f5da"),
      description: "Création de Greta Magnusson-Grossman, 1947.",
      why_it_fits:
        "Une silhouette sculpturale, presque animale : parfaite si tu cherches une pièce qui raconte quelque chose.",
      link_verified: false,
      price_verified: false,
    },
    {
      name: "Lampe en céramique émaillée",
      brand: "Atelier Pierre",
      price: 165,
      currency: "EUR",
      url: "https://www.etsy.com/fr/",
      image_url: img("1586023492125-27b2c045efd7"),
      description: "Pied tourné à la main, émail sauge, abat-jour en lin.",
      why_it_fits:
        "Pièce unique d'artisan : chaque émail est différent. Le vert sauge rappelle les tons naturels que tu aimes.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Lampe de bureau Bestlite BL1",
      brand: "Gubi",
      price: 579,
      currency: "EUR",
      url: "https://www.gubi.com/",
      image_url: img("1618220179428-22790b461013"),
      description: "Laiton et acier, bras articulé, design de 1930.",
      why_it_fits:
        "Le laiton se patine avec le temps, une icône Bauhaus qui reste discrète sur un bureau.",
      link_verified: true,
      price_verified: true,
    },
  ],
  outils: [
    {
      name: "Coffret de tournevis Kraftform Micro",
      brand: "Wera",
      price: 54.9,
      currency: "EUR",
      url: "https://www-de.wera.de/",
      image_url: img("1581244277943-fe4a9c777189"),
      description: "12 pièces, poignées à zone de rotation rapide, étui textile.",
      why_it_fits:
        "La référence des précisionnistes : ergonomie remarquable, pensé pour durer des décennies.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Jeu de tournevis de précision en noyer",
      brand: "Iris Hantverk",
      price: 69,
      currency: "EUR",
      url: "https://www.irishantverk.se/",
      image_url: img("1530124566582-a618bc2615dc"),
      description: "Manches en noyer huilé, lames en acier S2, fabriqué en Suède.",
      why_it_fits:
        "Un outil qui est aussi un bel objet : les manches en bois le rendent agréable à laisser à vue sur un établi.",
      link_verified: false,
      price_verified: false,
    },
    {
      name: "Kit de précision Mako 64 embouts",
      brand: "iFixit",
      price: 39.95,
      currency: "EUR",
      url: "https://www.ifixit.com/",
      image_url: img("1572981779307-38b8cabb2407"),
      description: "Manche aluminium, 64 embouts, boîte magnétique.",
      why_it_fits:
        "Le plus polyvalent pour réparer l'électronique : idéal si tu veux réparer plutôt que remplacer.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Tournevis de précision PB 100",
      brand: "PB Swiss Tools",
      price: 58,
      currency: "EUR",
      url: "https://www.pbswisstools.com/",
      image_url: img("1504148455328-c376907d081c"),
      description: "Fabrication suisse, garantie à vie, poignées colorées par taille.",
      why_it_fits:
        "Garantie à vie et fabrication suisse : un achat définitif, avec un code couleur très graphique.",
      link_verified: true,
      price_verified: false,
    },
  ],
  autre: [
    {
      name: "Carnet Traveler's en cuir camel",
      brand: "Traveler's Company",
      price: 62,
      currency: "EUR",
      url: "https://www.travelers-company.com/",
      image_url: img("1531346878377-a5be20888e57"),
      description: "Cuir de vachette non traité, recharges interchangeables.",
      why_it_fits:
        "Le cuir prend une patine unique avec le temps et le système de recharges en fait un compagnon pour des années.",
      link_verified: true,
      price_verified: true,
    },
    {
      name: "Carnet relié en cuir grainé",
      brand: "Smythson",
      price: 145,
      currency: "EUR",
      url: "https://www.smythson.com/",
      image_url: img("1544816155-12df9643f363"),
      description: "Papier Featherweight bleu pâle, tranche dorée.",
      why_it_fits:
        "Le luxe discret à l'anglaise : un papier d'une finesse rare qui donne envie d'écrire.",
      link_verified: true,
      price_verified: false,
    },
    {
      name: "Carnet MD en papier Midori",
      brand: "Midori",
      price: 19.5,
      currency: "EUR",
      url: "https://www.midori-japan.co.jp/",
      image_url: img("1517842645767-c639042777db"),
      description: "Papier crème, reliure cousue qui s'ouvre à plat.",
      why_it_fits:
        "Minimalisme japonais : une couverture nue, un papier exceptionnel, rien de superflu.",
      link_verified: false,
      price_verified: true,
    },
  ],
};

const DAY = 86_400_000;
const ago = (days: number) => new Date(Date.now() - days * DAY).toISOString();

export const DEMO_MASTER_PROMPT = `J'aime les objets bien faits, durables et un peu originaux, jamais tape-à-l'œil.
Je privilégie les matières naturelles (lin, laine, cuir, bois, céramique) et les marques indépendantes ou de créateurs.
Palette : tons neutres, sable, sauge, indigo. Je déteste le logo voyant et la fast fashion.
Je préfère payer un peu plus pour quelque chose qui dure et qui se répare.`;

export function buildDemoState() {
  const items: Omit<Item, "iterations_count">[] = [
    {
      id: 1,
      title: "Veste légère en lin pour l'été",
      category: "vetements",
      notes: "Taille M. Plutôt écrue ou sable, coupe un peu ample.",
      custom_prompt: null,
      budget_max: 250,
      status: "resultats",
      created_at: ago(9),
    },
    {
      id: 2,
      title: "Lampe de bureau chaleureuse",
      category: "deco",
      notes: "Pour un bureau en chêne clair. Lumière douce, pas de LED froide.",
      custom_prompt: null,
      budget_max: 400,
      status: "resultats",
      created_at: ago(6),
    },
    {
      id: 3,
      title: "Tournevis de précision",
      category: "outils",
      notes: "Pour réparer lunettes, montres et petite électronique.",
      custom_prompt: null,
      budget_max: 70,
      status: "a_chercher",
      created_at: ago(2),
    },
    {
      id: 4,
      title: "Carnet de notes en cuir",
      category: "autre",
      notes: null,
      custom_prompt: "Un cadeau pour une amie qui écrit beaucoup, élégant mais pas ostentatoire.",
      budget_max: 80,
      status: "achete",
      created_at: ago(21),
    },
  ];

  let resultId = 1;
  const makeSearch = (
    id: number,
    itemId: number,
    iteration: number,
    feedback: string | null,
    daysAgo: number,
    cost: number,
    products: [DemoProduct, number, Result["reaction"]][],
  ): Search => ({
    id,
    item_id: itemId,
    iteration,
    feedback,
    status: "done",
    error: null,
    created_at: ago(daysAgo),
    cost_usd: cost,
    results: products.map(([p, score, reaction]) => ({
      ...p,
      id: resultId++,
      search_id: id,
      score,
      reaction,
    })),
  });

  const v = DEMO_CATALOG.vetements;
  const d = DEMO_CATALOG.deco;
  const a = DEMO_CATALOG.autre;
  const searches: Search[] = [
    makeSearch(1, 1, 1, null, 8, 0.142, [
      [v[1], 84, "dislike"],
      [v[4], 78, null],
      [v[3], 81, "like"],
    ]),
    makeSearch(2, 1, 2, "Moins classique, j'aimerais une coupe plus singulière. Le lin brut me plaît.", 7, 0.118, [
      [v[5], 93, "like"],
      [v[0], 89, null],
      [v[2], 86, null],
    ]),
    makeSearch(3, 2, 1, null, 5, 0.167, [
      [d[3], 94, null],
      [d[0], 90, "like"],
      [d[1], 85, null],
      [d[2], 79, null],
      [d[4], 72, null],
    ]),
    makeSearch(4, 4, 1, null, 20, 0.096, [
      [a[0], 95, "like"],
      [a[1], 82, null],
      [a[2], 77, null],
    ]),
  ];

  return { items, searches, nextItemId: 5, nextSearchId: 5, nextResultId: resultId };
}
