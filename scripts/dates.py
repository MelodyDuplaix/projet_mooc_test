import json
from datetime import datetime

# Charger le fichier ligne par ligne
with open('MOOC_forum.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# Fonction récursive pour récupérer toutes les dates de création
def collect_dates(thread_content):
    dates = []
    if 'created_at' in thread_content:
        dates.append(thread_content['created_at'])
    if 'children' in thread_content and thread_content['children']:
        for child in thread_content['children']:
            if 'content' in child:
                dates.extend(collect_dates(child['content']))
            elif 'created_at' in child:
                dates.append(child['created_at'])
    return dates

# Récupérer toutes les dates
all_dates = []
for thread in data:
    all_dates.extend(collect_dates(thread['content']))

# Convertir les dates en objets datetime pour comparaison
all_dates_dt = [datetime.fromisoformat(date.replace('Z', '+00:00')) for date in all_dates]

# Trouver la date la plus ancienne et la plus récente
date_debut = min(all_dates_dt)
date_fin = max(all_dates_dt)

print("Date de début :", date_debut)
print("Date de fin   :", date_fin)