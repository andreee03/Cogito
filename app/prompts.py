"""Prompts utilisés par l'application.

Le prompt système de la recherche ("Cogiter") sera ajouté au jalon 3.
"""

# Profil par défaut : il décrit tes principes d'achat. Tu peux le modifier
# à tout moment via PUT /profile ; ce texte ne sert qu'au tout premier lancement.
DEFAULT_MASTER_PROMPT = """\
Mes principes d'achat :

- Efficacité : un objet doit remplir parfaitement sa fonction, sans gadget inutile.
- Élégance : lignes sobres, belles matières, finitions soignées.
- Qualité avant tout : je préfère payer cher un objet durable plutôt qu'acheter deux fois.
  Fabrication sérieuse, matériaux nobles, marques qui assument leur savoir-faire.
- Originalité : je cherche des marques indépendantes ou de créateurs, des pièces avec
  du caractère, que tout le monde n'a pas.
- Rien de standardisé : pas de produits de grande distribution interchangeables,
  pas de best-sellers vus partout, pas de "dupes".
"""
