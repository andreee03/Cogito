# Shopping réfléchi — back-end

API d'une application personnelle de "shopping réfléchi" : je tiens une liste
d'envies d'achat et, pour un article, je clique sur **Cogiter**. Le back-end demande
alors à Claude Haiku 4.5 (avec la recherche web) de trouver des produits adaptés à
mes goûts, vérifie lui-même chaque lien, et renvoie une liste de produits. Je peux
relancer jusqu'à 3 itérations avec un retour ("trop classique", "moins cher"…).

**Stack :** Python 3.12 · FastAPI · SQLModel (SQLite en local, Postgres en ligne) ·
SDK `anthropic` · httpx + BeautifulSoup · pytest.

---

## 1. Installation (une seule fois)

Prérequis : Python 3.12 et Git.

```powershell
git clone https://github.com/andreee03/Cogito.git
cd Cogito
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS / Linux : source .venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env          # macOS / Linux : cp .env.example .env
```

Si PowerShell refuse `Activate.ps1` ("l'exécution de scripts est désactivée") :
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, puis relancer l'activation.

Puis ouvrir `.env` et le remplir :

| Variable | Rôle | Exemple |
|---|---|---|
| `ANTHROPIC_API_KEY` | Clé API Claude ([console.anthropic.com](https://console.anthropic.com)) | `sk-ant-…` |
| `DATABASE_URL` | Base de données | `sqlite:///./shopping.db` |
| `ALLOWED_ORIGINS` | Adresses du front-end autorisées (CORS), séparées par des virgules | `http://localhost:5173` |
| `FAKE_CLAUDE` | `1` = faux Claude gratuit (voir plus bas) | `0` |

`.env` contient des secrets : il est dans `.gitignore` et ne doit jamais être commité.

## 2. Lancement en local

À chaque nouveau terminal, réactiver d'abord l'environnement :
`.venv\Scripts\Activate.ps1`.

```powershell
uvicorn app.main:app --reload
```

- API : http://localhost:8000
- Documentation interactive (tester toutes les routes) : http://localhost:8000/docs

`--reload` relance le serveur quand un fichier `.py` change, mais **pas** quand `.env`
change : après une modification de `.env`, faire `Ctrl+C` puis relancer.

### Développer sans payer : `FAKE_CLAUDE=1`

Une vraie recherche coûte environ 0,05 à 0,30 $. Avec `FAKE_CLAUDE=1` dans `.env`,
le serveur n'appelle pas Claude : il répond en 3 secondes avec 5 produits fictifs
(0 $, aucune clé nécessaire). Leurs liens n'existent pas et ressortent donc en
`link_verified: false`. Remettre `FAKE_CLAUDE=0` pour utiliser le vrai Claude.

## 3. Tests

```powershell
python -m pytest -q
```

Aucun test n'appelle la vraie API Claude ni Internet : Claude est remplacé par un
faux client, les pages produit par des fichiers HTML d'exemple (`tests/fixtures`).
Les tests utilisent une base SQLite temporaire et ne touchent jamais à `shopping.db`.

Pour lancer les tests sur une base Postgres **de test** (elle est vidée à chaque
test) : définir `TEST_DATABASE_URL=postgresql://…` avant `pytest`.

## 4. Organisation du code

```
app/
  main.py         routes de l'API
  models.py       tables de la base + schémas JSON (entrée / sortie)
  db.py           connexion à la base (SQLite ou Postgres)
  cogitate.py     recherche "Cogiter" : prompt, appel à Claude, lecture du JSON, coût
  verify.py       vérification des liens produits (prix, image)
  prompts.py      prompt système + profil par défaut
  fake_claude.py  faux Claude gratuit (FAKE_CLAUDE=1)
tests/            tests pytest (+ fixtures HTML)
render.yaml       configuration du déploiement Render
```

## 5. L'API en bref

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET / PUT | `/profile` | Lire / modifier mon `master_prompt` (mes goûts) |
| GET / POST | `/items` | Lister (récents d'abord) / créer un article |
| GET / PATCH / DELETE | `/items/{id}` | Lire / modifier / supprimer un article |
| POST | `/items/{id}/cogitate` | Lancer une recherche → `202 {"search_id"}` ; `409` si une recherche est en cours ou si 3 itérations ont réussi |
| GET | `/items/{id}/searches` | Toutes les recherches de l'article, avec leurs résultats |
| GET | `/searches/{id}` | Une recherche (le front l'interroge toutes les 3 s) |
| PATCH | `/results/{id}` | `{"reaction": "like" \| "dislike" \| null}` |

Le détail de chaque route et de chaque champ est sur `/docs`.

Fonctionnement d'une recherche : `pending` → `running` (Claude cherche, puis chaque
lien est vérifié) → `done` ou `error` (message dans `error`). Une recherche en
erreur ne consomme pas d'itération. À partir de la 2ᵉ itération, Claude reçoit un
résumé compact des produits déjà proposés (nom, marque, prix, like/dislike) et mon
retour. Le coût estimé est dans `cost_usd`.

---

## 6. Déploiement : Render (API) + Neon (Postgres)

Les deux ont une offre gratuite suffisante pour un usage personnel.

### Étape 1 — La base Postgres sur Neon

1. Créer un compte sur [neon.tech](https://neon.tech), puis **New project**
   (région conseillée : *AWS Europe Central 1 (Frankfurt)*, proche de Render Frankfurt).
2. Sur le tableau de bord du projet, cliquer **Connect**.
3. **Désactiver "Connection pooling"**, puis copier la chaîne de connexion. Elle
   ressemble à :
   `postgresql://neondb_owner:xxxx@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require`

   Pas besoin de la modifier : l'application la convertit d'elle-même pour le
   pilote `psycopg`. Les tables sont créées automatiquement au premier démarrage.

### Étape 2 — L'API sur Render

1. Pousser le code sur GitHub, sur la branche que Render déploiera (en général `main`).
2. Créer un compte sur [render.com](https://render.com) et le relier à GitHub.
3. **New → Blueprint**, choisir le dépôt `Cogito` : Render lit `render.yaml` et
   prépare le service `shopping-reflechi-api`.
4. Render demande les valeurs secrètes :
   - `DATABASE_URL` : la chaîne Neon de l'étape 1 ;
   - `ANTHROPIC_API_KEY` : la clé Claude ;
   - `ALLOWED_ORIGINS` : l'adresse du front-end en ligne, par ex.
     `https://mon-front.onrender.com` (sans `/` final ; ajouter
     `,http://localhost:5173` pour aussi tester depuis le front local).
5. **Apply**. Le premier déploiement prend quelques minutes. Une fois terminé,
   vérifier `https://<nom-du-service>.onrender.com/health` puis `/docs`.

Chaque `git push` sur la branche déployée redéploie automatiquement l'API.
Pour changer une variable : service → **Environment** (Render redémarre le service).

Sans Blueprint (création manuelle d'un **Web Service**) : *Build command*
`pip install -r requirements.txt`, *Start command*
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`, *Health check path* `/health`,
et les mêmes variables d'environnement.

Python : Render lit la version dans `.python-version` (3.12). En cas d'erreur de
version au build, ajouter la variable `PYTHON_VERSION` avec une version complète
(par ex. `3.12.11`).

### À savoir sur les offres gratuites

- **Render** met le service en veille après 15 min sans requête : la première
  requête suivante prend ~1 minute. Pendant une recherche, le front interroge
  l'API toutes les 3 s, ce qui la garde éveillée. Si le service redémarre en
  pleine recherche, celle-ci passe en `error` au redémarrage et peut être relancée.
- **Neon** met la base en veille quand elle ne sert pas ; elle se réveille en
  une seconde environ à la requête suivante.

### ⚠️ Sécurité et coûts

L'API n'a **pas d'authentification** : toute personne qui connaît son adresse peut
lancer des recherches, payées avec ta clé Claude. Avant de partager l'adresse, ou
par simple prudence :

- fixer une **limite de dépense mensuelle** dans la console Anthropic
  (*Settings → Limits*) ;
- ne pas publier l'adresse de l'API ;
- au besoin, ajouter un mot de passe d'accès à l'API (évolution possible).
