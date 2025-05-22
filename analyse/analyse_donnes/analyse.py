import json
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import seaborn as sns
from collections import Counter, defaultdict

def charger_donnees(chemin_fichier):
    """Charge les données du fichier JSON (une ligne par objet)"""
    donnees = []
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as fichier:
            for ligne in fichier:
                if ligne.strip():  # Ignorer les lignes vides
                    try:
                        donnees.append(json.loads(ligne))
                    except json.JSONDecodeError:
                        print(f"Erreur lors du décodage d'une ligne JSON")
        
        print(f"{len(donnees)} entrées chargées depuis {chemin_fichier}")
        return donnees
    
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")
        return []

def analyser_messages_par_thread(donnees):
    """Calcule le nombre moyen de messages par thread de discussion"""
    # Initialiser un dictionnaire pour compter les messages par thread
    messages_par_thread = defaultdict(int)
    thread_ids = set()
    
    for item in donnees:
        content = item.get('content', {})
        thread_type = content.get('type')
        thread_id = content.get('commentable_id')
        
        # Si c'est un thread ou s'il y a un identifiant de thread
        if thread_type == 'thread' or thread_id:
            if thread_id:
                thread_ids.add(thread_id)
                messages_par_thread[thread_id] += 1
    
    # Calculer la moyenne
    if thread_ids:
        nb_threads = len(thread_ids)
        nb_messages = sum(messages_par_thread.values())
        moyenne = nb_messages / nb_threads
        
        print(f"\nAnalyse des messages par thread:")
        print(f"Nombre total de threads: {nb_threads}")
        print(f"Nombre total de messages: {nb_messages}")
        print(f"Moyenne de messages par thread: {moyenne:.2f}")
        
        # Distribution du nombre de messages par thread
        plt.figure(figsize=(10, 6))
        plt.hist(list(messages_par_thread.values()), bins=20)
        plt.title('Distribution du nombre de messages par thread')
        plt.xlabel('Nombre de messages')
        plt.ylabel('Nombre de threads')
        plt.savefig('messages_par_thread.png')
        print(f"Graphique sauvegardé: messages_par_thread.png")
        
        return messages_par_thread
    else:
        print("Aucun thread identifié dans les données")
        return {}

def analyser_messages_par_utilisateur(donnees):
    """Calcule le nombre de messages par utilisateur et génère un graphique Pareto"""
    messages_par_utilisateur = Counter()
    
    for item in donnees:
        content = item.get('content', {})
        user_id = content.get('user_id')
        
        # Certaines structures peuvent avoir l'utilisateur à différents endroits
        if not user_id and 'username' in content:
            user_id = content.get('username')
        
        if user_id:
            messages_par_utilisateur[user_id] += 1
    
    # Tri par nombre de messages (décroissant)
    utilisateurs_tries = messages_par_utilisateur.most_common()
    
    if utilisateurs_tries:
        print(f"\nAnalyse des messages par utilisateur:")
        print(f"Nombre d'utilisateurs uniques: {len(utilisateurs_tries)}")
        
        # Top 10 des utilisateurs les plus actifs
        print("Top 10 des utilisateurs les plus actifs:")
        for i, (user, count) in enumerate(utilisateurs_tries[:10], 1):
            print(f"{i}. Utilisateur {user}: {count} messages")
        
        # Création du graphique Pareto
        users, counts = zip(*utilisateurs_tries)
        cumsum = pd.Series(counts).cumsum()
        percent_cumsum = 100 * cumsum / cumsum.iloc[-1]
        
        fig, ax1 = plt.subplots(figsize=(12, 7))
        
        # Limiter aux 20 premiers utilisateurs pour la lisibilité
        limit = min(20, len(utilisateurs_tries))
        ax1.bar(range(limit), counts[:limit], color='b')
        ax1.set_xlabel('Utilisateurs')
        ax1.set_ylabel('Nombre de messages', color='b')
        ax1.tick_params(axis='y', labelcolor='b')
        
        ax2 = ax1.twinx()
        ax2.plot(range(limit), percent_cumsum[:limit], 'r-', marker='o')
        ax2.set_ylabel('Pourcentage cumulé', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        plt.title('Pareto: Messages par utilisateur')
        plt.xticks(range(limit), [f"User {i+1}" for i in range(limit)], rotation=45)
        plt.tight_layout()
        plt.savefig('pareto_utilisateurs.png')
        print(f"Graphique sauvegardé: pareto_utilisateurs.png")
        
        return utilisateurs_tries
    else:
        print("Aucun utilisateur identifié dans les données")
        return []

def analyser_periode_discussions(donnees):
    """Analyse les dates de début et de fin des discussions"""
    dates = []
    
    for item in donnees:
        content = item.get('content', {})
        created_at = content.get('created_at')
        
        if created_at:
            try:
                # Différents formats de date possibles
                for format_date in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        date = datetime.strptime(created_at, format_date)
                        dates.append(date)
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Erreur lors du parsing de la date: {created_at}, {e}")
    
    if dates:
        date_min = min(dates)
        date_max = max(dates)
        
        print(f"\nAnalyse de la période des discussions:")
        print(f"Premier message: {date_min.strftime('%d/%m/%Y %H:%M')}")
        print(f"Dernier message: {date_max.strftime('%d/%m/%Y %H:%M')}")
        print(f"Durée totale: {(date_max - date_min).days} jours")
        
        # Création d'un histogramme des dates
        plt.figure(figsize=(12, 6))
        plt.hist([d.date() for d in dates], bins=30)
        plt.title('Distribution des messages par date')
        plt.xlabel('Date')
        plt.ylabel('Nombre de messages')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('distribution_dates.png')
        print(f"Graphique sauvegardé: distribution_dates.png")
        
        return date_min, date_max
    else:
        print("Aucune date valide trouvée dans les données")
        return None, None

def analyser_messages_par_cours(donnees):
    """Analyse le nombre de threads et messages par cours (avec Pareto)"""
    threads_par_cours = Counter()
    messages_par_cours = Counter()
    
    for item in donnees:
        content = item.get('content', {})
        course_id = content.get('course_id', 'inconnu')
        thread_type = content.get('type')
        
        if course_id:
            messages_par_cours[course_id] += 1
            
            # Si c'est un thread (discussion principale)
            if thread_type == 'thread':
                threads_par_cours[course_id] += 1
    
    # Tri par nombre de messages (décroissant)
    cours_tries = messages_par_cours.most_common()
    
    if cours_tries:
        print(f"\nAnalyse des messages par cours:")
        print(f"Nombre de cours uniques: {len(cours_tries)}")
        
        # Top cours avec le plus de messages
        print("Cours avec le plus de messages:")
        for i, (course, count) in enumerate(cours_tries[:5], 1):
            thread_count = threads_par_cours.get(course, 0)
            print(f"{i}. Cours {course}: {count} messages, {thread_count} threads")
        
        # Création du graphique Pareto
        courses, counts = zip(*cours_tries)
        cumsum = pd.Series(counts).cumsum()
        percent_cumsum = 100 * cumsum / cumsum.iloc[-1]
        
        fig, ax1 = plt.subplots(figsize=(12, 7))
        
        # Limiter aux 10 premiers cours pour la lisibilité
        limit = min(10, len(cours_tries))
        ax1.bar(range(limit), counts[:limit], color='g')
        ax1.set_xlabel('Cours')
        ax1.set_ylabel('Nombre de messages', color='g')
        ax1.tick_params(axis='y', labelcolor='g')
        
        ax2 = ax1.twinx()
        ax2.plot(range(limit), percent_cumsum[:limit], 'r-', marker='o')
        ax2.set_ylabel('Pourcentage cumulé', color='r')
        ax2.tick_params(axis='y', labelcolor='r')
        
        plt.title('Pareto: Messages par cours')
        plt.xticks(range(limit), [f"Cours {i+1}" for i in range(limit)], rotation=45)
        plt.tight_layout()
        plt.savefig('pareto_cours.png')
        print(f"Graphique sauvegardé: pareto_cours.png")
        
        return cours_tries, threads_par_cours
    else:
        print("Aucun cours identifié dans les données")
        return [], {}

def main():
    """Fonction principale du script"""
    # Chemin vers le fichier JSON
    chemin_fichier = os.path.join(os.path.dirname(__file__), "data", "MOOC_forum.json")
    
    # Charger les données
    donnees = charger_donnees(chemin_fichier)
    
    if not donnees:
        print("Aucune donnée à analyser. Vérifiez le chemin du fichier.")
        return
    
    # Réaliser les analyses demandées
    analyser_messages_par_thread(donnees)
    analyser_messages_par_utilisateur(donnees)
    analyser_periode_discussions(donnees)
    analyser_messages_par_cours(donnees)
    
    print("\nAnalyse terminée. Les graphiques ont été sauvegardés dans le répertoire courant.")

if __name__ == "__main__":
    main()
