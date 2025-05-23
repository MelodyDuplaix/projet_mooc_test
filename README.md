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

Les fichiers CSV nécessaires sont disponibles sur le Google Drive (dossier "production apprenants"). Voici comment les importer dans les bases de données :

### PostgreSQL (avec pgvector)

- **embedding.csv** : à importer dans la table `embedding` (contient les identifiants, vecteurs d'embedding, liens vers threads/messages).
- **courses.csv** : à importer dans la table `courses` (liste des cours, identifiants, noms).
- **threads.csv** : à importer dans la table `threads` de PostgreSQL (structure relationnelle, liens entre threads, cours, etc.).

Pour importer un CSV dans PostgreSQL (exemple sous Windows PowerShell) :
```powershell
psql -U <user> -d <database> -c "\copy embedding FROM 'chemin\\vers\\embedding.csv' DELIMITER ',' CSV HEADER;"
psql -U <user> -d <database> -c "\copy courses FROM 'chemin\\vers\\courses.csv' DELIMITER ',' CSV HEADER;"
psql -U <user> -d <database> -c "\copy threads FROM 'chemin\\vers\\threads.csv' DELIMITER ',' CSV HEADER;"
```

### MongoDB

- **threads.csv** : à importer dans la collection `threads` de la base MongoDB (`G1`).
  - Ce fichier contient les threads complets (structure JSON, titres, contenus, métadonnées, etc.).
- **documents.csv** : à importer dans la collection `documents` de la base MongoDB (`G1`).
  - Ce fichier contient les messages individuels (posts/messages isolés, avec leur contenu et leurs métadonnées).
  - Selon les besoins de l'application, les deux collections sont utilisées pour différentes fonctionnalités (recherche, affichage, etc.).

Pour importer un CSV dans MongoDB :
```powershell
mongoimport --uri "mongodb://localhost:27017/G1" --collection threads --type csv --headerline --file chemin\vers\threads.csv
mongoimport --uri "mongodb://localhost:27017/G1" --collection documents --type csv --headerline --file chemin\vers\documents.csv
```

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

