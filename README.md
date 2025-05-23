# Projet de Formation : Monitoring de Formations à Distance via l'IA

Ce projet vise à monitorer une formation à distance en utilisant des techniques avancées de traitement de données et d'intelligence artificielle.  L'analyse se concentrera sur les interactions des forums de MOOC, les notes étant indisponibles.

## Objectifs

- Fournir une application permettant de poser des questions et de retrouver des fils de discussion pertinents, avec une réponse adaptée si possible (RAG).
- Regrouper les fils de discussion par thèmes communs (clustering) et analyser la pertinence de la classification manuelle existante.
- Proposer une analyse de sentiment sur les messages d'un fil de discussion sélectionné.
- Identifier les participants "proches" (ayant suivi les mêmes cours, répondu aux mêmes fils...).

## Technologies Utilisées
 
- **MongoDB:** Base de données pour le stockage des données.
- **Git:** Gestion de version du code.
- **Python:** API et Application web
- **PostgreSQL:** Utilisée pour le stockage des embeddings, des documents et des similarités.
- **Hugging Face:** Utilisée pour le modèle de langage, d'embedding et de clustering.

## Données

Les données utilisées proviennent d'extractions de forums de MOOC, anciennes et récentes. Elles sont stockées dans la base de données MongoDB
sous forme de documents JSON.

Les données sont ensuite exportées dans la base de données PostgreSQL pour le stockage des embeddings, des documents et des similarités.

## Livrables

- Projet GitHub documenté.
- Application déployée sur le cloud.
- Notebook d'analyse fonctionnel, documenté et commenté (`notebooks/analyse_posts_mooc.ipynb`).
- Schéma et documentation de la base de données MongoDB.
- Tests unitaires et d'intégration.

## Bonus

- Gestion des erreurs robuste.
- Enrichissement des données (scraping de forums supplémentaires).
- Fonctionnalités supplémentaires.
- Rapport de données complet.

## Installation (local)

### Prérequis

- Python 3.x
- MongoDB
- Git

### Cloner le repository

```bash
git clone https://github.com/yourusername/projet_mooc.git
cd projet_mooc
```

### Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate # Linux/Mac
.\venv\Scripts\activate # Windows
```

### Installer les dépendances

```bash
pip install -r requirements.txt
```

## Utilisation

```bash
python main.py
```

## Base de données
Aller récupérer les fichiers csv sur le drive, dans production apprenants.
Base de données mongodb + postgres avec pgvector, puis importer l'ensemble des données depuis les fichiers csv.

## Architecture

```
projet_mooc_test/
├── analyse/           # Outils d'analyse de données et modèles statistiques
├── api/               # API REST pour l'interface avec l'application web
├── data/              # Données brutes et traitées (MongoDB et PostgreSQL)
├── docs/              # Documentation du projet
├── graphique/         # Composants de visualisation et graphiques
├── images/            # Ressources statiques (logos, icônes)
├── notebooks/         # Notebooks Jupyter pour l'analyse et le prototypage
├── scripts/           # Scripts utilitaires (import de données, etc.)
├── .env               # Variables d'environnement (non versionnées)
├── .env.exemple       # Exemple de configuration des variables d'environnement
├── .gitignore         # Fichiers à ignorer pour Git
├── main.py            # Point d'entrée principal de l'application
├── rapport.md         # Rapport de présentation du projet
├── README.md          # Documentation principale
└── requirements.txt   # Dépendances Python
```


## Fonctionnalités principales

1. **Recherche de discussions**
   - Utilisation d'une base de données MongoDB pour stocker les discussions.
   - Recherche avancée par mot-clé, titre ou contenu.

2. **Analyse de sentiments**
   - Analyse des sentiments des messages des utilisateurs.
   - Classification des messages en positif, négatif ou neutre.

3. **Clustering des discussions**
   - Clustering des discussions en fonction de leur contenu.
   - Utilisation de l'algorithme K-Means pour regrouper les discussions.

4. **Clustering des utilisateurs**
   - Clustering des utilisateurs en fonction de leur activité.
   - Utilisation de l'algorithme K-Means pour regrouper les utilisateurs.

