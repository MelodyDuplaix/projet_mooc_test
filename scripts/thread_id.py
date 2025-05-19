import os
from sql_script import base_postgres
from tqdm import tqdm  # Importer tqdm

#MongoDB
from pymongo import MongoClient

#Environnement
from dotenv import load_dotenv

load_dotenv()

def connexion_mongodb_local():
    MONGO_URL = os.getenv("MONGO_URL_LOCAL")
    client = MongoClient(MONGO_URL)
    return client

def add_thread_id():
    client = connexion_mongodb_local()
    
    # Vider la table threads pour repartir de zéro
    print("Suppression des données existantes dans la table backup.threads...")
    
    # Tronquer la table sans se soucier des contraintes (il n'y en a pas dans backup)
    truncate_query = "TRUNCATE TABLE backup.threads RESTART IDENTITY"
    base_postgres(truncate_query)
    print("Table backup.threads vidée avec succès.")
    
    # Compter le nombre total de documents pour initialiser la barre de progression
    total_docs = client['mooc']['data'].count_documents({})
    print(f"Nombre total de documents à traiter: {total_docs}")
    
    # Agréger les threads avec leur thread_id et l'identifiant du cours
    threads_data = client['mooc']['data'].find({}, {'content.id': 1, 'content.course_id': 1})
    
    # Récupérer tous les cours de la table courses
    course_map = {}
    requete = "SELECT id, name FROM test.courses"
    results = base_postgres(requete, fetch_results=True)
    
    if results is None:
        print("Erreur: Impossible de récupérer les données des cours")
        return
    
    # Créer un dictionnaire pour faire correspondre le nom du cours à son ID PostgreSQL
    for row in results:
        pg_id = row[0]
        course_name = row[1]
        course_map[course_name] = pg_id  # Le course_id de MongoDB correspond au name dans PostgreSQL
    
    # Compteurs pour les statistiques
    count = 0
    skipped = 0
    
    # Garder trace des thread_ids déjà traités
    processed_ids = set()
    
    # Utiliser tqdm pour afficher une barre de progression
    with tqdm(total=total_docs, desc="Traitement des threads", unit="doc") as pbar:
        for doc in threads_data:
            content = doc.get('content', {})
            thread_id = content.get('id')
            mongo_course_id = content.get('course_id')
            
            if thread_id and mongo_course_id and mongo_course_id in course_map:
                pg_course_id = course_map[mongo_course_id]
                
                # Vérifier si on a déjà traité ce thread_id
                if thread_id not in processed_ids:
                    try:
                        # Insérer le thread avec le course_id en une seule opération
                        insert_query = "INSERT INTO backup.threads (id, course_id) VALUES (%s, %s)"
                        base_postgres(insert_query, (thread_id, pg_course_id))
                        processed_ids.add(thread_id)
                        count += 1
                    except Exception as e:
                        # En cas d'erreur, essayer avec ON CONFLICT
                        insert_query = "INSERT INTO backup.threads (id, course_id) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING"
                        base_postgres(insert_query, (thread_id, pg_course_id))
                        processed_ids.add(thread_id)
                        print(f"Gestion d'un doublon: {thread_id}")
                
                # Mettre à jour la description de la barre de progression
                if count % 100 == 0:
                    pbar.set_postfix(traités=count, ignorés=skipped, dernier_id=thread_id[:10]+"...")
            else:
                skipped += 1
            
            # Avancer la barre de progression
            pbar.update(1)
    
    print(f"\nTraitement terminé. {count} threads mis à jour, {skipped} documents ignorés.")

def verify_threads_count():
    client = connexion_mongodb_local()
    
    print("\n" + "="*90)
    print("VÉRIFICATION DES THREADS PAR COURS ENTRE MONGODB ET POSTGRESQL")
    print("="*90)
    
    # 1. Compter les threads par cours dans MongoDB
    mongo_counts = {}
    pipeline = [
        {"$group": {"_id": "$content.course_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    mongo_results = client['mooc']['data'].aggregate(pipeline)
    
    for doc in mongo_results:
        course_id = doc['_id']
        if course_id:  # Ignorer les documents sans course_id
            mongo_counts[course_id] = doc['count']
    
    print(f"MongoDB: {len(mongo_counts)} cours différents, {sum(mongo_counts.values())} threads au total")
    
    # Compter les threads par cours dans PostgreSQL (reste identique)
    # ...

def embedding_thread():
    client = connexion_mongodb_local()
    
    # Récupérer les données de la table embedding qui n'ont pas encore de thread_id
    select_query = "SELECT id FROM backup.embedding WHERE thread_id IS NULL"
    embeddings = base_postgres(select_query, fetch_results=True)
    
    if not embeddings:
        print("Aucun embedding sans thread_id trouvé.")
        return
        
    print(f"Traitement de {len(embeddings)} embeddings sans thread_id...")
    
    # Dictionnaire pour stocker les associations message_id -> thread_id
    thread_id_cache = {}
    
    with tqdm(total=len(embeddings), desc="Association des threads", unit="embedding") as pbar:
        for (message_id,) in embeddings:  # L'id dans la table est directement le message_id
            # Vérifier si le message_id est dans le cache
            if message_id in thread_id_cache:
                thread_id = thread_id_cache[message_id]
            else:
                # Chercher le message dans la collection documents
                message = client['mooc']['documents'].find_one({"_id": message_id})
                
                if not message:
                    print(f"Message non trouvé: {message_id}")
                    pbar.update(1)
                    continue
                
                # Vérifier si le message a un thread_id direct
                thread_id = message.get('thread_id')
                
                # Si pas de thread_id direct, c'est un message de niveau 2+
                if not thread_id:
                    # Chercher le message parent (niveau 1) via parent_id
                    parent_id = message.get('parent_id')
                    
                    if parent_id:
                        parent_message = client['mooc']['documents'].find_one({"_id": parent_id})
                        if parent_message:
                            thread_id = parent_message.get('thread_id')
                    
                # Stocker dans le cache
                if thread_id:
                    thread_id_cache[message_id] = thread_id
            
            # Mettre à jour la table embedding si un thread_id a été trouvé
            if thread_id:
                update_query = "UPDATE backup.embedding SET thread_id = %s WHERE id = %s"
                base_postgres(update_query, (thread_id, message_id))
            
            pbar.update(1)
    
    # Afficher les statistiques
    count_query = "SELECT COUNT(*) FROM backup.embedding WHERE thread_id IS NOT NULL"
    result = base_postgres(count_query, fetch_results=True)
    total_with_thread = result[0][0] if result else 0
    
    count_query = "SELECT COUNT(*) FROM backup.embedding"
    result = base_postgres(count_query, fetch_results=True)
    total_embeddings = result[0][0] if result else 0
    
    print(f"\nTraitement terminé. {total_with_thread}/{total_embeddings} embeddings ont maintenant un thread_id associé.")

def verify_thread_message_mapping():
    client = connexion_mongodb_local()
    
    print("\n" + "="*90)
    print("VÉRIFICATION DE LA CORRESPONDANCE DES MESSAGES PAR THREAD")
    print("="*90)
    
    # Récupérer un échantillon de threads depuis PostgreSQL
    sample_query = "SELECT id FROM backup.threads ORDER BY RANDOM() LIMIT 100"
    thread_sample = base_postgres(sample_query, fetch_results=True)
    
    if not thread_sample:
        print("Aucun thread trouvé dans la base de données PostgreSQL.")
        return
    
    print(f"Vérification détaillée de {len(thread_sample)} threads aléatoires...")
    
    perfect_match = 0
    missing_messages = 0
    extra_messages = 0
    
    for (thread_id,) in thread_sample:
        # 1. Récupérer tous les messages liés à ce thread dans PostgreSQL
        sql_query = "SELECT id FROM backup.embedding WHERE thread_id = %s"
        sql_result = base_postgres(sql_query, (thread_id,), fetch_results=True)
        sql_messages = {row[0] for row in sql_result} if sql_result else set()
        
        # 2. Récupérer tous les messages liés à ce thread dans MongoDB
        # Les messages de niveau 1 ont directement le thread_id
        level1_messages = {doc['_id'] for doc in client['mooc']['documents'].find({'thread_id': thread_id})}
        
        # Les messages de niveau 2+ ont un parent_id qui pointe vers un message de niveau 1
        level1_ids = list(level1_messages)
        level2plus_messages = set()
        
        if level1_ids:
            # Trouver tous les messages qui ont un parent_id correspondant à un message de niveau 1
            for parent_id in level1_ids:
                children = client['mooc']['documents'].find({'parent_id': parent_id})
                for child in children:
                    level2plus_messages.add(child['_id'])
                    
                    # Récursion pour trouver les niveaux 3+ (réponses aux réponses)
                    child_id = child['_id']
                    grandchildren = client['mooc']['documents'].find({'parent_id': child_id})
                    for grandchild in grandchildren:
                        level2plus_messages.add(grandchild['_id'])
        
        # Tous les messages MongoDB liés à ce thread
        mongo_messages = level1_messages | level2plus_messages
        
        # 3. Comparer les ensembles
        missing = mongo_messages - sql_messages
        extra = sql_messages - mongo_messages
        
        # Afficher les résultats pour ce thread
        print(f"\nThread {thread_id}:")
        print(f"  - Messages dans MongoDB: {len(mongo_messages)}")
        print(f"  - Messages dans PostgreSQL: {len(sql_messages)}")
        
        if not missing and not extra:
            print("  ✓ Correspondance parfaite!")
            perfect_match += 1
        else:
            if missing:
                print(f"  ✗ {len(missing)} messages manquants dans PostgreSQL")
                missing_messages += 1
            if extra:
                print(f"  ✗ {len(extra)} messages en trop dans PostgreSQL")
                extra_messages += 1
    
    # Résumé global
    print("\n" + "="*90)
    print(f"RÉSUMÉ DE LA VÉRIFICATION ({len(thread_sample)} threads analysés)")
    print(f"- {perfect_match} threads avec correspondance parfaite")
    print(f"- {missing_messages} threads avec des messages manquants")
    print(f"- {extra_messages} threads avec des messages en trop")
    
    if perfect_match == len(thread_sample):
        print("\n✓ EXCELLENT! Tous les threads vérifiés ont une correspondance parfaite entre MongoDB et PostgreSQL.")
    else:
        print("\n⚠ ATTENTION: Des incohérences ont été détectées. Une vérification plus approfondie pourrait être nécessaire.")

if __name__ == "__main__":
    #add_thread_id()
    #verify_threads_count()
    #embedding_thread()
    verify_thread_message_mapping()