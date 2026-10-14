"""Migrations de données à appliquer une seule fois.

Chaque migration a un nom ; une fois appliquée, ce nom est noté dans la table
appliedmigration et elle n'est plus jamais rejouée. Le profil reste ensuite
modifiable dans l'app comme d'habitude.
"""

from sqlmodel import Session

# Texte qui remplace le profil de goûts lors de la migration "profile_prompt_v2".
PROFILE_PROMPT = """\
Mes principes d'achat par défaut

Statut de ces principes : ils s'appliquent seulement quand la demande spécifique \
ne dit rien sur le sujet. Dès que la demande spécifique précise un point (style, \
origine, état, type de marque, nombre de produits…), elle l'emporte sur ces \
principes, sans exception.

1. Composition de la sélection lors de la première recherche
La première recherche sur une demande est celle qui a lieu avant tout retour de \
ma part sur une sélection. Elle contient :
- 2 à 3 best-sellers : les produits les plus achetés et les plus recommandés de \
la catégorie, choisis uniquement parmi ceux qui respectent toutes les contraintes \
(budget, fabrication européenne, demande spécifique).
- 3 à 4 produits plus originaux : marques indépendantes, de créateurs ou \
d'ateliers, qui respectent les mêmes contraintes.
Ne fais pas d'arbitrage entre ces deux familles : si un best-seller et une marque \
originale conviennent tous les deux, propose les deux.
Commence le champ "why_it_fits" de chaque best-seller par « Best-seller : », \
suivi des sources qui le recommandent.
S'il n'existe pas assez de best-sellers qui respectent les contraintes, propose \
ceux qui existent et ne comble pas le manque avec des produits qui ne conviennent pas.
Lors des recherches suivantes, quand je réagis à une sélection, suis mes retours. \
La règle des 2 à 3 best-sellers ne s'applique plus.

2. Méthode pour identifier les best-sellers
Avant de chercher les pages produit, fais des recherches intermédiaires :
a. Cherche des comparatifs et classements récents sur la catégorie : tests de \
magazines spécialisés, associations de consommateurs, articles « top 10 » ou \
« meilleur [produit] [année] », classements des meilleures ventes des boutiques.
b. Retiens les produits cités dans plusieurs sources, puis écarte ceux qui ne \
respectent pas les contraintes.
c. Cherche ensuite la page produit de chaque produit retenu sur un site marchand.
Ces articles servent uniquement à te documenter. Ne les propose jamais comme résultat.

3. Fabrication en Europe
Les produits doivent être fabriqués dans un pays européen. Vérifie le lieu de \
fabrication sur la page produit ou sur le site de la marque. « Conçu en France » \
ou « marque française » ne suffit pas : c'est le lieu de fabrication qui compte. \
Écarte tout produit dont la fabrication hors d'Europe est établie. Si l'origine \
reste introuvable, tu peux proposer le produit à condition de le signaler \
clairement dans "why_it_fits".

4. Avis clients
Les avis comptent beaucoup. Privilégie les produits notés au moins 4/5 avec un \
nombre d'avis significatif, et relève la note et le nombre d'avis affichés sur la \
page produit. Un produit sans avis n'est acceptable que s'il présente d'autres \
gages sérieux de qualité (savoir-faire documenté, garantie longue, matériaux \
détaillés). Dans ce cas, signale l'absence d'avis dans "why_it_fits".

5. État
Produits neufs uniquement. Pas d'occasion, de reconditionné ni de vintage, sauf \
si la demande le précise.

6. En dehors des best-sellers
Évite les produits standardisés : articles de grande distribution \
interchangeables, marques génériques sans identité, copies et « dupes ».
"""


def _profile_prompt_v2(session: Session) -> None:
    """Remplace le profil de goûts par PROFILE_PROMPT."""
    from app.db import get_or_create_profile

    profile = get_or_create_profile(session)
    profile.master_prompt = PROFILE_PROMPT
    session.add(profile)


MIGRATIONS = [
    ("profile_prompt_v2", _profile_prompt_v2),
]


def run_migrations(session: Session) -> None:
    """Applique, dans l'ordre, les migrations pas encore appliquées."""
    from app.models import AppliedMigration

    for name, migrate in MIGRATIONS:
        if session.get(AppliedMigration, name) is None:
            migrate(session)
            session.add(AppliedMigration(name=name))
            session.commit()
