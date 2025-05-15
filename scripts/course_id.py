import os
from sql_script import base_postgres

#MongoDB
from pymongo import MongoClient

#Environnement
from dotenv import load_dotenv

import time 

load_dotenv()

def connexion_mongodb_local():
    MONGO_URL = os.getenv("MONGO_URL_LOCAL")
    client = MongoClient(MONGO_URL)
    return client

def get_unique_course_ids():
    client = connexion_mongodb_local()
    db = client["mooc"]  # Base de données mooc
    collection = db["data"]  # Collection data
    
    print(f"Nombre total de documents: {collection.count_documents({})}")
    
    print("Récupération des course_id uniques avec agrégation...")
    start_time = time.time()
    
    # Utiliser l'agrégation MongoDB pour récupérer les course_id uniques
    result = collection.aggregate([
        {
            '$group': {
                '_id': '$content.course_id'
            }
        }, 
        {
            '$project': {
                '_id': 0,
                'course_id': '$_id'
            }
        }
    ])
    
    # Convertir le résultat en liste
    unique_course_ids = [doc['course_id'] for doc in result if 'course_id' in doc]
    
    print(f"Temps écoulé: {time.time() - start_time:.2f} secondes")
    print(f"Nombre de course_id uniques trouvés: {len(unique_course_ids)}")
    
    client.close()
    return unique_course_ids

def add_course_ids_to_postgres():
    # Récupérer les course_id uniques de MongoDB
    unique_course_ids = get_unique_course_ids()
    
    if not unique_course_ids:
        print("Aucun course_id trouvé dans MongoDB!")
        return
    
    # Compter les insertions réussies
    count = 0
    
    # Pour chaque course_id, l'insérer dans PostgreSQL
    for course_id in unique_course_ids:
        if course_id:  # Vérifier que le course_id n'est pas None ou vide
            try:
                # Vérifier si le course_id existe déjà dans la table
                check_query = "SELECT id FROM test.courses WHERE name = %s"
                result = base_postgres(check_query, (course_id,))
                
                # Si le résultat est vide (None ou liste vide), insérer le course_id
                if not result:
                    # Insérer le nouveau course_id dans la colonne name
                    insert_query = "INSERT INTO test.courses (name) VALUES (%s)"
                    base_postgres(insert_query, (course_id,))
                    count += 1
                    if count % 100 == 0:  # Afficher le progrès tous les 100 éléments
                        print(f"Progression: {count}/{len(unique_course_ids)} courses insérés")
            except Exception as e:
                print(f"Erreur lors de l'insertion de {course_id}: {str(e)}")
    
    print(f"Opération terminée! {count} nouveaux cours ajoutés à PostgreSQL.")

if __name__ == "__main__":
    add_course_ids_to_postgres()
