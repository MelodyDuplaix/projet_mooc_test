Utilisateur       API Authentification     Base de données (Utilisateurs)   (Optionnel) Blacklist JWT
     |                 |                              |                              |
     |--Demande connexion (login)-->|                 |                              |
     |                 |--Vérifier identifiants------>|                              |
     |                 |<--Résultat vérification------|                              |
     |<--Recevoir jeton JWT----------|                 |                              |
     |                 |                              |                              |
     |--Utiliser jeton pour requêtes sécurisées-->|    |                              |
     |                 |--Valider jeton JWT---------->|                              |
     |                 |<--OK / Non valide-------------|                              |
     |                 |                              |                              |
     |--Demande déconnexion (logout)-->|              |                              |
     |                 |--Ajouter jeton à blacklist (si géré)--->|                   |
     |<--Confirmation déconnexion-----|              |                              |
