# -*- coding: utf-8 -*-
import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
import sys

# Charger les variables d'environnement (si un fichier .env existe)
load_dotenv()

# --- Configuration de la connexion MongoDB ---
# Utilise la variable d'environnement MONGODB_URI si définie,
# sinon utilise la valeur par défaut localhost.
MONGO_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
DB_NAME = 'mooc'
POSTS_COLLECTION = 'posts_mooc'
DOCUMENTS_COLLECTION = 'documents'

def run_analysis():
    """Fonction principale pour exécuter toutes les analyses."""
    client = None # Initialiser client à None
    try:
        # --- Connexion à MongoDB ---
        print(f"Connexion à MongoDB : {MONGO_URI}...")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        posts_collection = db[POSTS_COLLECTION]
        documents_collection = db[DOCUMENTS_COLLECTION]
        print("Connexion réussie.")

        # --- 1. Nombre de messages par utilisateur ---
        print("\n--- Nombre de messages par utilisateur (Top 20) ---")
        try:
            user_message_count = posts_collection.aggregate([
                {
                    # On ne groupe que si le champ username existe
                    '$match': {
                        'content.username': {'$exists': True, '$ne': None, '$ne': ""}
                    }
                },
                {
                    '$group': {
                        '_id': '$content.username',
                        'nb_message': {
                            # Utilisation de $sum: 1 est plus courant que $count: {} pour compter les docs groupés
                            '$sum': 1
                        }
                    }
                },
                {
                    '$sort': {
                        'nb_message': -1
                    }
                },
                {
                    '$limit': 20 # Limiter aux 20 premiers pour la lisibilité
                }
            ])
            for doc in user_message_count:
                # Gérer le cas où _id pourrait être None ou vide (bien que filtré par $match)
                username = doc.get('_id', 'Utilisateur inconnu')
                count = doc.get('nb_message', 0)
                print(f"{username} : {count}")
        except Exception as e:
            print(f"Erreur lors du calcul du nombre de messages par utilisateur: {e}")

        # --- 2. Moyenne des commentaires et réponses par cours ---
        print("\n--- Moyenne des commentaires et réponses par cours ---")
        try:
            course_stats = posts_collection.aggregate([
                 {
                    # S'assurer que les champs nécessaires existent et sont numériques
                    '$match': {
                        'content.course_id': {'$exists': True},
                        'content.comments_count': {'$exists': True, '$type': "number"},
                        'content.resp_total': {'$exists': True, '$type': "number"}
                    }
                },
                {
                    '$group': {
                        '_id': "$content.course_id",
                        'avg_comments': {
                            '$avg': '$content.comments_count'
                        },
                        'avg_response': {
                            '$avg': '$content.resp_total'
                        }
                    }
                },
                {
                    '$sort': {
                        # Trier par réponses moyennes peut être plus pertinent
                        'avg_response': -1
                    }
                }
            ])
            for doc in course_stats:
                course_id = doc.get("_id", "Cours inconnu")
                avg_comments = doc.get('avg_comments', 0)
                avg_response = doc.get('avg_response', 0)
                # Utiliser f-string pour un formatage plus simple et lisible
                print(f"Cours: {course_id:<45} | Moy. Commentaires: {avg_comments:.2f}, Moy. Réponses: {avg_response:.2f}")
        except Exception as e:
            print(f"Erreur lors du calcul des moyennes par cours: {e}")


        # --- 3. Nombre total de cours distincts ---
        print("\n--- Nombre total de cours distincts ---")
        try:
            # Utiliser distinct est plus direct pour compter les valeurs uniques d'un champ
            distinct_courses = posts_collection.distinct("content.course_id")
            print(f"Total cours distincts: {len(distinct_courses)}")
        except Exception as e:
            print(f"Erreur lors du comptage des cours distincts: {e}")

        # --- 4. Dates minimales et maximales (création et mise à jour) globales ---
        print("\n--- Période d'activité globale des posts ---")
        try:
            date_range = posts_collection.aggregate([
                {
                    # Filtrer les documents où les dates existent et sont valides (format ISO date string)
                     '$match': {
                        'content.created_at': {'$exists': True, '$type': "string"},
                        'content.updated_at': {'$exists': True, '$type': "string"}
                    }
                },
                {
                    '$group': {
                        '_id': None, # Groupement global
                        'min_date': { '$min': '$content.created_at' },
                        'max_date': { '$max': '$content.created_at' },
                        'min_update': { '$min': '$content.updated_at' },
                        'max_update': { '$max': '$content.updated_at' }
                    }
                },
                {
                    '$project': {
                        '_id': 0 # Exclure le champ _id du résultat
                    }
                }
            ])
            # Il n'y aura qu'un seul document résultat (ou aucun si la collection est vide / filtrée)
            result_doc = next(date_range, None)
            if result_doc:
                print(f"Date de création min: {result_doc.get('min_date', 'N/A')}")
                print(f"Date de création max: {result_doc.get('max_date', 'N/A')}")
                print(f"Date de mise à jour min: {result_doc.get('min_update', 'N/A')}")
                print(f"Date de mise à jour max: {result_doc.get('max_update', 'N/A')}")
            else:
                 print("Aucune donnée de date trouvée.")
        except Exception as e:
            print(f"Erreur lors de la recherche des dates min/max globales: {e}")


        # --- 5. Nombre maximum de commentaires sur un post ---
        print("\n--- Nombre maximum de commentaires sur un post ---")
        try:
            max_comments_agg = posts_collection.aggregate([
                {
                    # Remplacer null ou champ manquant par 0 avant de chercher le max
                    '$project': {
                        'comments_count': {
                            '$ifNull': ['$content.comments_count', 0]
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None, # Groupement global
                        'max_comments_count': {
                            '$max': '$comments_count'
                        }
                    }
                },
                {
                    '$project': {
                        '_id': 0 # Exclure _id
                    }
                }
            ])
            result_doc = next(max_comments_agg, None)
            if result_doc:
                 print(f"Nombre max de commentaires: {result_doc.get('max_comments_count', 'N/A')}")
            else:
                 print("Aucune donnée de commentaires trouvée.")
        except Exception as e:
            print(f"Erreur lors de la recherche du max de commentaires: {e}")


        # --- 6. Période d'activité par cours ---
        print("\n--- Période d'activité par cours (Création et Mise à jour) ---")
        try:
            course_activity = posts_collection.aggregate([
                 {
                     '$match': {
                        'content.course_id': {'$exists': True},
                        'content.created_at': {'$exists': True, '$type': "string"},
                        'content.updated_at': {'$exists': True, '$type': "string"}
                    }
                },
                {
                    '$group': {
                        '_id': '$content.course_id',
                        'min_create': { '$min': '$content.created_at' },
                        'max_create': { '$max': '$content.created_at' },
                        'min_update': { '$min': '$content.updated_at' },
                        'max_update': { '$max': '$content.updated_at' }
                    }
                },
                {
                    '$sort': { '_id': 1 } # Trier par ID de cours pour la lisibilité
                }
            ])
            for doc in course_activity:
                course_id = doc.get('_id', 'Cours Inconnu')
                min_c = doc.get('min_create', 'N/A').split("T")[0] if doc.get('min_create') else 'N/A'
                max_c = doc.get('max_create', 'N/A').split("T")[0] if doc.get('max_create') else 'N/A'
                min_u = doc.get('min_update', 'N/A').split("T")[0] if doc.get('min_update') else 'N/A'
                max_u = doc.get('max_update', 'N/A').split("T")[0] if doc.get('max_update') else 'N/A'
                print(f"{course_id:<60} : Création [{min_c} -> {max_c}] | MàJ [{min_u} -> {max_u}]")
        except Exception as e:
            print(f"Erreur lors du calcul de la période d'activité par cours: {e}")


        # --- 7. Traitement récursif et insertion dans 'documents' ---
        print("\n--- Traitement récursif et insertion/mise à jour dans la collection 'documents' ---")

        # Définir la fonction récursive à l'intérieur pour qu'elle ait accès à `documents_collection`
        def process_and_insert_document(content_data, parent_id=None):
            """
            Traite un noeud de contenu (post, commentaire, réponse) et l'insère
            dans la collection 'documents' s'il n'existe pas déjà.
            Gère récursivement les enfants et les réponses.
            """
            if not isinstance(content_data, dict):
                #print(f"  Donnée invalide rencontrée (pas un dictionnaire): {content_data}")
                return # Ignorer si ce n'est pas un dictionnaire

            doc_id = content_data.get("id")
            if not doc_id:
                #print("  Document sans ID trouvé, impossible de traiter.")
                return # Impossible de traiter sans ID

            # Préparer le document à insérer/mettre à jour
            document_to_insert = content_data.copy() # Travailler sur une copie
            document_to_insert['_id'] = doc_id # Utiliser l'id comme _id MongoDB

            # Ajouter parent_id si ce document est une réponse/commentaire (profondeur > 0 ou via les listes de réponses)
            # La condition depth == 1 semble spécifique et pourrait être généralisée.
            # Ici, on se base sur le fait qu'elle est appelée récursivement avec un parent_id.
            if parent_id:
                 document_to_insert["parent_id"] = parent_id

            # Vérifier si le document existe déjà
            # Utiliser upsert=True est plus efficace que find_one + insert_one
            try:
                # Remplacer l'existant ou insérer s'il n'existe pas
                documents_collection.replace_one(
                    {'_id': doc_id},        # Filtre pour trouver le document par son ID
                    document_to_insert,     # Le nouveau document qui remplacera l'ancien ou sera inséré
                    upsert=True             # Option pour insérer si le document n'est pas trouvé
                )
            except Exception as e:
                print(f"  Erreur lors de l'upsert du document {doc_id}: {e}")
                # Peut-être décider de continuer avec les enfants ou d'arrêter ici

            # Traiter récursivement les sous-éléments
            # Correction des clés potentielles (avec/sans 's') et vérification si c'est une liste
            children = content_data.get("children", [])
            if isinstance(children, list):
                for child_doc in children:
                    process_and_insert_document(child_doc, parent_id=doc_id)

            # Correction des noms de clés pour les réponses
            endorsed = content_data.get('endorsed_responses', content_data.get('endorsed_reponses', []))
            if isinstance(endorsed, list):
                for endorsed_resp in endorsed:
                    process_and_insert_document(endorsed_resp, parent_id=doc_id)

            non_endorsed = content_data.get('non_endorsed_responses', content_data.get('non_endorsed_reponses', []))
            if isinstance(non_endorsed, list):
                for non_endorsed_resp in non_endorsed:
                    process_and_insert_document(non_endorsed_resp, parent_id=doc_id)

        # --- Exécution du traitement récursif ---
        try:
            # Récupérer seulement le champ 'content' des posts initiaux
            initial_posts = posts_collection.find(
                filter={}, # Pas de filtre initial, on prend tous les posts
                projection={'content': 1, '_id': 0} # Ne récupérer que le champ 'content'
            )

            count = 0
            total_posts = posts_collection.count_documents({}) # Pourcentage d'avancement
            print(f"Traitement de {total_posts} posts initiaux...")

            for i, doc in enumerate(initial_posts):
                content = doc.get("content")
                if content: # Vérifier si le champ content existe
                    process_and_insert_document(content) # Lancer la récursion pour chaque post initial
                    count += 1
                # Afficher la progression
                if (i + 1) % 100 == 0 or (i + 1) == total_posts:
                     progress = ((i + 1) / total_posts) * 100
                     print(f"  Progression: {i + 1}/{total_posts} ({progress:.2f}%)", end='\r')
                     sys.stdout.flush() # Forcer l'affichage sur la même ligne

            print(f"\nTraitement récursif terminé. {count} posts initiaux traités.")

        except Exception as e:
            print(f"\nErreur lors du traitement récursif et de l'insertion: {e}")


    except Exception as e:
        print(f"Une erreur majeure est survenue: {e}")

    finally:
        # --- Fermeture de la connexion ---
        if client:
            client.close()
            print("\nConnexion à MongoDB fermée.")

# --- Point d'entrée du script ---
if __name__ == "__main__":
    run_analysis()
