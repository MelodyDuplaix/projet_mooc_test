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

## Architecture


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




