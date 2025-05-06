import json

# Charger le fichier ligne par ligne
with open('MOOC_forum.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# Fonction récursive pour calculer la profondeur maximale d'un thread
def profondeur_max(thread_content, niveau=1):
    max_niveau = niveau
    if 'children' in thread_content and thread_content['children']:
        for child in thread_content['children']:
            if 'content' in child:
                profondeur = profondeur_max(child['content'], niveau + 1)
                if profondeur > max_niveau:
                    max_niveau = profondeur
            else:
                if niveau + 1 > max_niveau:
                    max_niveau = niveau + 1
    return max_niveau

# Calculer la profondeur maximale pour chaque thread
profondeurs = []
for thread in data:
    profondeurs.append(profondeur_max(thread['content']))

# Profondeur maximale sur tout le forum
profondeur_maximale = max(profondeurs)
print("Profondeur maximale des réponses pour un fil :", profondeur_maximale)