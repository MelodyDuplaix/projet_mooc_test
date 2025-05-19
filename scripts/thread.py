import json

# Charger le fichier ligne par ligne
with open('MOOC_forum.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# Fonction récursive pour compter les messages dans un thread
def count_messages(thread_content):
    count = 1  # le message principal
    if 'children' in thread_content and thread_content['children']:
        for child in thread_content['children']:
            # Certains enfants peuvent ne pas avoir de 'content', on vérifie
            if 'content' in child:
                count += count_messages(child['content'])
            else:
                count += 1  # Si pas de 'content', on compte juste le message
    return count

# Calculer la moyenne
total_messages = 0
for thread in data:
    total_messages += count_messages(thread['content'])

moyenne = total_messages / len(data)
print("Moyenne de messages par thread :", moyenne)

print("Nombre de threads dans le fichier :", len(data))