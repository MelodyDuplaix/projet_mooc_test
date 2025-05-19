import json

# Charger le fichier ligne par ligne
with open('MOOC_forum.json', 'r', encoding='utf-8') as f:
    data = [json.loads(line) for line in f]

# Compter le nombre de threads (niveau 0) par utilisateur
compte_utilisateurs = {}

for thread in data:
    username = thread['content'].get('username', 'inconnu')
    if username in compte_utilisateurs:
        compte_utilisateurs[username] += 1
    else:
        compte_utilisateurs[username] = 1

# Trier les utilisateurs par nombre décroissant de threads créés
classement = sorted(compte_utilisateurs.items(), key=lambda x: x[1], reverse=True)

# Afficher le top 10
print("\nPareto des créateurs de threads (niveau 0) :")
for i, (user, count) in enumerate(classement[:10], 1):
    print(f"{i}. {user} : {count} threads")
