from pymongo import MongoClient
from transformers import AutoTokenizer, AutoModelForSequenceClassification # type: ignore
import numpy as np
import os
from dotenv import load_dotenv
import torch
load_dotenv()

def analyse_sentiment_long_texte(texte, model_name="tabularisai/multilingual-sentiment-analysis", 
                               taille_fenetre=384, chevauchement=128):
    """
    Analyse un long texte en utilisant une fenêtre glissante
    """
    # Charger le tokenizer et le modèle
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    
    # Tokeniser le texte complet
    tokens = tokenizer.encode(texte)
    
    # Si le texte est plus court que la taille de fenêtre maximale
    if len(tokens) <= taille_fenetre:
        inputs = tokenizer(texte, return_tensors="pt", truncation=True, max_length=taille_fenetre)
        with torch.no_grad():
            outputs = model(**inputs)
        
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        label_id = torch.argmax(probs, dim=-1).item()
        score = probs[0, label_id].item()
        
        return {
            "label": model.config.id2label[label_id],
            "score": score,
            "methode": "direct"
        }
    
    # Pour les textes plus longs, utiliser une fenêtre glissante
    scores_segments = []
    labels_segments = []
    
    # Créer des segments qui se chevauchent
    for i in range(0, len(tokens) - 2, taille_fenetre - chevauchement):
        # Extraire un segment de tokens
        segment_tokens = tokens[i:i + taille_fenetre]
        
        # Convertir les tokens en texte
        segment_text = tokenizer.decode(segment_tokens)
        
        # Tokeniser à nouveau pour obtenir les tenseurs d'entrée corrects
        inputs = tokenizer(segment_text, return_tensors="pt", truncation=True)
        
        # Faire l'inférence
        with torch.no_grad():
            outputs = model(**inputs)
        
        # Obtenir les probabilités
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Stocker les scores et labels pour chaque segment
        for label_id in range(len(model.config.id2label)):

            scores_segments.append(probs[0][label_id].item())
            labels_segments.append(model.config.id2label[label_id])
    
    # Réorganiser les scores par label
    label_scores = {}
    for label, score in zip(labels_segments, scores_segments):
        if label not in label_scores:
            label_scores[label] = []
        label_scores[label].append(score)
    
    # Calculer la moyenne des scores pour chaque label
    avg_scores = {label: np.mean(scores) for label, scores in label_scores.items()}
    
    # Trouver le label avec le score moyen le plus élevé
    final_label = max(avg_scores.items(), key=lambda x: x[1])[0]
    final_score = avg_scores[final_label]
    
    return {
        "label": final_label,
        "score": final_score,
        "methode": "fenetre_glissante",
        "details": {
            "segments": len(tokens) // (taille_fenetre - chevauchement) + 1,
            "scores_par_label": avg_scores
        }

    }
    
def get_message_for_thread(id: str, mongo_url: str, collec_name: str):
    """
    Fonction qui récupère l'ensemble des messages dans la base de données et applique l'analyse de sentiments sur les messages

    Args:
        id (str): identifiant du thread à analyser
    """
    client = MongoClient(mongo_url)
    messages = client[collec_name]["threads"].find({"_id": id})
    messages_list = []

    for message in messages:
        message_data = {key: value for key, value in message.items() if key != "content"}
        message_data["content"] = {key: value for key, value in message["content"].items() if key != "children"}
        messages_list.append(message_data)

        if "children" in message["content"]:
            for child in message["content"]["children"]:
                messages_list.append(child)

    print(f"Nombre de messages : {len(messages_list)}")
    result_list = []
    print(messages_list)

    for message in messages_list:
        body = message["body"] if "body" in message else message.get("content", {}).get("body", "")
        result = analyse_sentiment_long_texte(body)

        result_list.append({
            "message": message,
            "label": result["label"],
            "score": result["score"]
        })

    return result_list
    
if __name__ == "__main__":
    id = "52ef4f99344caaf903000158"
    mongo_url = os.getenv("MONGO_URL")
    collec_name = "G1"
    if not mongo_url:
        raise ValueError("MONGO_URL environment variable is not set")
    print(get_message_for_thread(id, mongo_url, collec_name))
 
