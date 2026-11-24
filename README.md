# Agent Vinted

Deux façons de l'utiliser : le **site web** (à partager) et le **script** (pour toi, avec la recherche complète).

Donne-lui un lien de page produit (Zalando, Nike, Asos…) ou une photo de vêtement :
il identifie l'article puis cherche sur Vinted les annonces du même article, ou à défaut les plus proches.

## Installation (une fois)

Il faut Python 3.10 ou plus récent.

```bash
cd vinted-agent
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Pour les photos (et de meilleures recherches à partir d'un lien), il faut une clé API Claude,
à créer sur https://platform.claude.com :

```bash
export ANTHROPIC_API_KEY="ta-clé"   # Windows PowerShell : $env:ANTHROPIC_API_KEY="ta-clé"
```

Sans clé, les liens fonctionnent quand même (lecture de la page produit uniquement).

## Utilisation

```bash
python -m vinted_agent "https://www.site.com/page-du-produit"
python -m vinted_agent ma-photo.jpg --taille M --prix-max 40
```

Options : `--taille`, `--prix-max` (en euros), `--nombre` (annonces affichées, 10 par défaut).

Exemple de sortie :

```
Article identifié :
  Marque : Nike
  Modèle : Nike Air Force 1 '07 Blanche
  Couleur : blanc
  Prix neuf : 119.99 €
  Recherches : nike air force 1 blanche, nike air force

✅ Même article trouvé (1) :
  • Nike Air Force 1 blanche
    45.00 EUR  (62 % sous le neuf) · 42 · Très bon état  [score 0.90]
    https://www.vinted.fr/items/...
```

## Comment ça marche

| Fichier | Rôle |
|---|---|
| `vinted_agent/identify.py` | Lit la page produit (données JSON-LD et balises og:) ou envoie la photo à Claude, qui renvoie marque, modèle, couleur et requêtes de recherche |
| `vinted_agent/vinted.py` | Interroge la recherche de vinted.fr comme le ferait le navigateur, avec 2 s de pause entre deux appels |
| `vinted_agent/ranking.py` | Note chaque annonce de 0 à 1 (marque, modèle, couleur, taille). À partir de 0,75 c'est « le même article » |
| `vinted_agent/agent.py` | Enchaîne les trois étapes. C'est ce module que l'appli web réutilisera |

## À savoir

- Vinted n'a pas d'API publique et ses conditions d'utilisation interdisent la collecte automatisée.
  Garde-le pour un usage perso, sans lancer des centaines de recherches d'affilée.
- Si Vinted répond 403 ou 429, c'est sa protection anti-robot : attends quelques minutes.
- Le modèle Claude utilisé est `claude-opus-5-5` ; tu peux en changer avec la variable
  `VINTED_AGENT_MODEL` (par exemple `claude-haiku-5-5`, beaucoup moins cher pour ce genre de tâche).

## Le site web

Le site identifie l'article (lien ou photo) et propose des boutons qui ouvrent la recherche
filtrée directement sur Vinted. Il ne collecte rien sur Vinted : aucun risque de blocage.

### Le lancer sur ton ordi

```bash
pip install -r requirements.txt
uvicorn web.app:app --reload
```

Puis ouvre http://localhost:8000.

### Le mettre en ligne (Render, gratuit)

1. Mets le dossier `vinted-agent` sur un dépôt GitHub.
2. Sur https://render.com, crée un compte puis **New > Blueprint** et choisis ce dépôt :
   le fichier `render.yaml` configure tout.
3. Render te demande `ANTHROPIC_API_KEY` : colle ta clé Claude (sinon seuls les liens marchent).
4. Après quelques minutes, ton site est en ligne sur une adresse en `onrender.com`, à partager.

Sur l'offre gratuite, le site s'endort après 15 minutes sans visite : la première visite
suivante prend environ 30 secondes.

### Photos gratuites avec Gemini

Sans clé Claude, l'onglet Photo peut utiliser Gemini, l'IA de Google, sur son offre gratuite.
Crée une clé sur https://aistudio.google.com/apikey (gratuit, sans carte) et colle-la dans
`GEMINI_API_KEY` (Render > Environment). Le quota gratuit est limité à un certain nombre de photos
par jour, fixé et modifié par Google ; une fois épuisé, le site invite à réessayer le lendemain.
Sur l'offre gratuite, Google peut utiliser les images envoyées pour améliorer ses produits.
Le modèle se change avec `GEMINI_MODEL` (par défaut `gemini-flash-lite-latest`).

### Sur quels sites

Après l'identification, le site affiche une ligne par site (Vinted, eBay, Leboncoin en France,
Vestiaire Collective) avec un bouton qui ouvre la recherche sur ce site.
(Le module `vinted_agent/sites.py` sait encore compter les annonces eBay via l'API officielle
si on le rebranche, avec `EBAY_CLIENT_ID` et `EBAY_CLIENT_SECRET`.)

### Ça ressemble, d'autres marques

Le site repère dans le titre du produit le type (veste, robe, baskets…), la couleur et la matière,
puis propose une recherche « toutes marques » (avec les mêmes sites)
et 3 à 4 marques du même style (liste `BRANDS` dans `vinted_agent/similar.py`, à compléter).

### Maîtriser le coût

| Variable | Rôle | Par défaut |
|---|---|---|
| `CLAUDE_PER_DAY` | Nombre max d'analyses Claude par jour, tous visiteurs confondus. C'est ton plafond de dépense | 300 |
| `PER_IP_PER_HOUR` | Recherches max par visiteur et par heure | 20 |
| `VINTED_AGENT_MODEL` | Modèle Claude. `claude-haiku-5-5` coûte environ 40 fois moins cher | `claude-opus-5-5` |

Fixe aussi une limite de dépense mensuelle dans la console Claude (Settings > Limits).
