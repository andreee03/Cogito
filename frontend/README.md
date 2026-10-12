# Cogito — front-end

Interface web (React + TypeScript + Vite) de Cogito, l'assistant de shopping réfléchi.
Uniquement un front-end : pas d'authentification ni de base de données. Toutes les
données viennent du back-end Python (dossier parent) via son API REST.

## Lancer en local

Prérequis : Node.js 20 ou plus.

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Sans URL de back-end, l'app tourne en **mode démo** (4 articles fictifs, recherche
simulée de 5 s, données gardées dans le navigateur). Pour utiliser le vrai back-end :
**Réglages → URL du back-end** (ex. `http://localhost:8000`), puis « Tester la
connexion ». L'adresse du front doit figurer dans `ALLOWED_ORIGINS` du back-end
(`http://localhost:5173` est autorisée par défaut).

## Construire

```bash
npm run build      # vérification TypeScript + build dans dist/
npm run preview    # sert dist/ sur http://localhost:4173
```

## Organisation

```
src/
  lib/api.ts        TOUS les appels réseau : implémentation réelle + démo (même interface)
  lib/types.ts      types du contrat d'API (snake_case)
  lib/demoData.ts   données fictives du mode démo
  lib/format.ts     prix au format français, dates, coût
  pages/            Ma liste, Détail d'un article, Mon profil de goûts, Réglages
  components/       carte produit, formulaire d'article, attente « Cogito réfléchit… »
public/             manifest PWA, icônes, service worker
```

## Déploiement (Render, site statique)

New → **Static Site**, dépôt `Cogito` :
- *Root directory* : `frontend`
- *Build command* : `npm install && npm run build`
- *Publish directory* : `dist`
- *Redirects/Rewrites* : ajouter une règle **Rewrite** `/*` → `/index.html`
  (sinon un rechargement sur `/articles/3` renvoie une 404).

Puis ajouter l'adresse du site (sans `/` final) à `ALLOWED_ORIGINS` du back-end et
saisir l'URL de l'API dans les Réglages de l'app. Sur téléphone, « Ajouter à l'écran
d'accueil » installe l'app (PWA).
