import json

# Charger le fichier ligne par ligne
with open('MOOC_forum.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# Fonction récursive pour compter tous les messages d'un thread
def count_messages(thread_content):
    count = 1  # message principal
    if 'children' in thread_content and thread_content['children']:
        for child in thread_content['children']:
            if 'content' in child:
                count += count_messages(child['content'])
            else:
                count += 1
    return count

# Dictionnaires pour stocker les résultats
threads_par_cours = {}
messages_par_cours = {}

for thread in data:
    course_id = thread['content'].get('course_id', 'inconnu')
    # Compter les threads
    threads_par_cours[course_id] = threads_par_cours.get(course_id, 0) + 1
    # Compter les messages
    nb_messages = count_messages(thread['content'])
    messages_par_cours[course_id] = messages_par_cours.get(course_id, 0) + nb_messages

# Trier les résultats (Pareto)
threads_pareto = sorted(threads_par_cours.items(), key=lambda x: x[1], reverse=True)
messages_pareto = sorted(messages_par_cours.items(), key=lambda x: x[1], reverse=True)

print("Pareto des threads par cours :")
for course, count in threads_pareto[:10]:
    print(f"{course} : {count} threads")

print("\nPareto des messages par cours :")
for course, count in messages_pareto[:10]:
    print(f"{course} : {count} messages")