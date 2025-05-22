import json
import os
import time
import requests
from bs4 import BeautifulSoup

# Informations d'authentification
USERNAME = "dc912312@gmail.com"
PASSWORD = "Chevallier@37"

# URL du forum
FORUM_URL = "https://lms.fun-mooc.fr/courses/course-v1:CNFPT+87067+session01/ada0fd1827ec4185afff6728de923028/"

def connexion_fun_mooc():
    """Établit une session authentifiée avec FUN MOOC"""
    session = requests.Session()
    
    try:
        # Récupérer la page de connexion pour obtenir le token CSRF
        login_page = session.get("https://lms.fun-mooc.fr/login?next=richie/fr/")
        soup = BeautifulSoup(login_page.content, "html.parser")
        
        # Trouver le token CSRF
        csrf_token = None
        # Chercher dans les balises input
        csrf_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
        if csrf_input:
            csrf_token = csrf_input.get("value")
        
        # Si pas trouvé dans les inputs, chercher dans les scripts
        if not csrf_token:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "csrfToken" in script.string:
                    try:
                        # Extraire la valeur par une approche simplifiée
                        start = script.string.find('"csrfToken":"') + 13
                        end = script.string.find('"', start)
                        if start > 13 and end > start:
                            csrf_token = script.string[start:end]
                            break
                    except:
                        continue
        
        if not csrf_token:
            print("Impossible de trouver le token CSRF")
            print("Contenu de la page:")
            print(login_page.text[:500])  # Affiche les 500 premiers caractères pour déboguer
            return None
        
        print(f"Token CSRF trouvé: {csrf_token}")
        
        # Préparer les données d'authentification
        login_data = {
            "email": USERNAME, 
            "mot de passe": PASSWORD,
            "csrfmiddlewaretoken": csrf_token
        }
        
        # En-têtes pour simuler un navigateur
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://lms.fun-mooc.fr/login?next=richie/fr/",
            "Origin": "https://lms.fun-mooc.fr"
        }
        
        # Soumettre le formulaire de connexion
        login_response = session.post(
            "https://lms.fun-mooc.fr/login",
            data=login_data,
            headers=headers,
            allow_redirects=True
        )
        
        # Vérifier si la connexion a réussi
        if login_response.status_code == 200:
            # Vérifier si nous sommes redirigés vers la page de tableau de bord ou si un élément spécifique est présent
            if "dashboard" in login_response.url:
                print("Connexion réussie via URL redirect!")
                return session
            
            # Vérifier la présence d'un élément qui indiquerait que nous sommes connectés
            soup = BeautifulSoup(login_response.content, "html.parser")
            if soup.find("a", {"class": "user-link"}) or soup.find("li", {"class": "user-account"}):
                print("Connexion réussie via vérification d'élément!")
                return session
            
            # Dernière vérification: essayer d'accéder à une page protégée
            test_page = session.get("https://lms.fun-mooc.fr/dashboard")
            if test_page.status_code == 200 and "login" not in test_page.url:
                print("Connexion vérifiée via accès à une page protégée!")
                return session
            
            print("La connexion semble avoir échoué. Vérifiez les identifiants.")
            return None
        else:
            print(f"Erreur lors de la connexion: {login_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Exception lors de la connexion: {e}")
        return None

def recuperer_donnees_forum(session):
    """Récupère les données JSON du forum"""
    donnees_forum = []
    
    if not session:
        print("Aucune session active. Impossible de récupérer les données.")
        return donnees_forum
    
    try:
        # Accéder au forum
        print(f"Accès à l'URL du forum: {FORUM_URL}")
        response = session.get(FORUM_URL)
        
        if response.status_code != 200:
            print(f"Erreur lors de l'accès au forum: {response.status_code}")
            return donnees_forum
        
        # Analyse de la page HTML
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 1. Rechercher des balises script contenant des données JSON
        print("Recherche de données JSON dans les balises script...")
        scripts = soup.find_all("script")
        json_data_count = 0
        
        for script in scripts:
            if not script.string:
                continue
                
            script_content = script.string.strip()
            if script_content.startswith('{') or script_content.startswith('['):
                try:
                    data = json.loads(script_content)
                    json_data_count += 1
                    
                    # Si les données contiennent un champ 'content', c'est probablement ce que nous cherchons
                    if isinstance(data, dict) and "content" in data:
                        print(f"Trouvé un script avec données JSON contenant 'content'")
                        donnees_forum.append(data)
                    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                        # Pour les listes de dictionnaires, vérifier si chaque élément contient 'content'
                        formatted_items = []
                        for item in data:
                            if "content" in item:
                                formatted_items.append(item)
                            elif isinstance(item, dict):
                                # Essayer de formater au format attendu
                                formatted_item = {
                                    "_id": item.get("id", str(hash(str(item)))),
                                    "content": item
                                }
                                formatted_items.append(formatted_item)
                        
                        if formatted_items:
                            print(f"Trouvé {len(formatted_items)} éléments formatés dans un tableau JSON")
                            donnees_forum.extend(formatted_items)
                except json.JSONDecodeError:
                    continue
        
        print(f"Nombre de scripts JSON analysés: {json_data_count}")
        
        # 2. Si peu/pas de données JSON, chercher l'API REST pour les données du forum
        if len(donnees_forum) < 3:
            print("Tentative d'accès à l'API du forum...")
            
            # Essayer d'accéder à différents points d'API possibles
            api_urls = [
                f"{FORUM_URL}/api/discussion/v1/threads/",
                f"{FORUM_URL}/api/discussion/v1/forum/",
                # Retirer la partie finale de l'URL et essayer d'autres chemins d'API
                "/".join(FORUM_URL.split("/")[:-2]) + "/api/discussion/threads"
            ]
            
            for api_url in api_urls:
                try:
                    api_response = session.get(api_url)
                    if api_response.status_code == 200:
                        try:
                            api_data = api_response.json()
                            print(f"Données trouvées via API: {api_url}")
                            
                            # Formater les données selon la structure attendue
                            if isinstance(api_data, list):
                                for item in api_data:
                                    formatted_item = {
                                        "_id": item.get("id", str(hash(str(item)))),
                                        "content": item
                                    }
                                    donnees_forum.append(formatted_item)
                            elif isinstance(api_data, dict) and "results" in api_data:
                                for item in api_data["results"]:
                                    formatted_item = {
                                        "_id": item.get("id", str(hash(str(item)))),
                                        "content": item
                                    }
                                    donnees_forum.append(formatted_item)
                        except json.JSONDecodeError:
                            print(f"L'API {api_url} n'a pas retourné de JSON valide")
                except Exception as e:
                    print(f"Erreur lors de l'accès à l'API {api_url}: {e}")
        
        # 3. Si toujours pas de données, essayer d'extraire les discussions du HTML
        if len(donnees_forum) < 1:
            print("Extraction des discussions du HTML...")
            discussions = soup.find_all(class_=["forum-thread", "discussion", "post", "thread"])
            print(f"Nombre de discussions trouvées dans le HTML: {len(discussions)}")
            
            for disc in discussions:
                try:
                    # Chercher différents éléments possibles selon la structure
                    title_elem = (
                        disc.find(class_=["post-title", "discussion-title", "thread-title"]) or
                        disc.find("h3") or
                        disc.find("h4")
                    )
                    
                    body_elem = (
                        disc.find(class_=["post-body", "discussion-body", "thread-body", "content"]) or
                        disc.find("div", class_="body")
                    )
                    
                    author_elem = (
                        disc.find(class_=["author", "username", "user-info"]) or
                        disc.find("a", class_="username")
                    )
                    
                    date_elem = (
                        disc.find("time") or
                        disc.find(class_=["date", "timestamp", "post-date"])
                    )
                    
                    if title_elem or body_elem:
                        discussion_id = disc.get("id") or disc.get("data-id") or str(hash(str(disc)))
                        formatted_discussion = {
                            "_id": discussion_id,
                            "content": {
                                "title": title_elem.text.strip() if title_elem else "Sans titre",
                                "body": body_elem.text.strip() if body_elem else "",
                                "user_id": author_elem.text.strip() if author_elem else "Anonymous",
                                "created_at": date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else 
                                             date_elem.text.strip() if date_elem else "",
                                "type": "thread",
                            }
                        }
                        donnees_forum.append(formatted_discussion)
                except Exception as e:
                    print(f"Erreur lors de l'extraction d'une discussion: {e}")
        
        print(f"Total de données récupérées: {len(donnees_forum)}")
        
    except Exception as e:
        print(f"Erreur lors de la récupération des données du forum: {e}")
        import traceback
        traceback.print_exc()
    
    return donnees_forum

def sauvegarder_donnees(donnees, nom_fichier="MOOC_forum_scrapped.json"):
    """Sauvegarde les données dans un fichier JSON"""
    if not donnees:
        print("Aucune donnée à sauvegarder.")
        return
    
    chemin_fichier = os.path.join(os.path.dirname(__file__), nom_fichier)
    
    # Sauvegarde en format une ligne par objet JSON
    try:
        with open(chemin_fichier, "w", encoding="utf-8") as fichier:
            for item in donnees:
                json_line = json.dumps(item, ensure_ascii=False)
                fichier.write(json_line + "\n")
        print(f"Données sauvegardées dans {chemin_fichier}")
    
    except IOError as e:
        print(f"Erreur lors de la sauvegarde du fichier: {e}")

def main():
    """Fonction principale du script"""
    print("Début du scraping des forums FUN MOOC...")
    
    # Établir une session authentifiée
    session = connexion_fun_mooc()
    
    if session:
        # Récupérer les données du forum
        donnees_forum = recuperer_donnees_forum(session)
        
        # Sauvegarder les données
        sauvegarder_donnees(donnees_forum)
        
        print(f"Opération terminée. {len(donnees_forum)} entrées récupérées.")
    else:
        print("Impossible de continuer sans connexion.")

if __name__ == "__main__":
    main()
