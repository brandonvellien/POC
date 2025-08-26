# orchestrator.py - VERSION MISE À JOUR AVEC TÂCHES ASYNCHRONES

import os
import json
import time # Ajout de l'import pour le polling
import requests
from openai import OpenAI
from tavily import TavilyClient
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# ==============================================================================
# SECTION 1 : FONCTIONS "CHEF D'ORCHESTRE" PRINCIPALES (appelées par app.py)
# ==============================================================================

API_BASE_URL = "https://trends-ai-backend-image2-382329904395.europe-west1.run.app"

def run_analysis_flow(payload: dict):
    """
    Fonction générique pour lancer une tâche d'analyse et sonder (poll) le résultat.
    C'est le nouveau cœur de l'orchestration de l'analyse.
    """
    start_url = f"{API_BASE_URL}/api/analysis/start"
    
    try:
        # 1. Lancer la tâche et obtenir un ID de job
        print(f"▶️ Lancement de la tâche avec les données : {payload}")
        start_response = requests.post(start_url, json=payload)
        start_response.raise_for_status()
        job_id = start_response.json().get('jobId')
        
        if not job_id:
            return {"error": "L'API n'a pas retourné de Job ID.", "details": start_response.text}
            
        print(f"✅ Tâche démarrée avec l'ID : {job_id}")

        status_url = f"{API_BASE_URL}/api/analysis/status/{job_id}"
        
        # 2. Sonder l'API toutes les 15 secondes jusqu'à ce que la tâche soit terminée
        timeout_seconds = 1200 # Timeout de 20 minutes pour éviter une boucle infinie
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            print(f"🔄 Vérification du statut de la tâche {job_id}...")
            status_response = requests.get(status_url)
            
            if status_response.ok:
                data = status_response.json()
                status = data.get('status')
                
                if status == 'completed':
                    print("✅ Analyse terminée avec succès !")
                    return data.get('result') # On retourne le rapport d'analyse complet
                elif status == 'failed':
                    print("❌ L'analyse a échoué.")
                    return {"error": "L'analyse a échoué côté backend.", "details": data.get('error')}
                # Si le statut est 'pending' ou 'processing', on continue la boucle
                
            else:
                print(f"⚠️ Erreur lors de la récupération du statut : {status_response.status_code}")

            time.sleep(15) # Attendre 15 secondes avant la prochaine vérification

        return {"error": "Timeout", "details": "L'analyse a pris plus de 20 minutes à répondre."}

    except requests.exceptions.RequestException as e:
        return {"error": "Échec de la communication avec l'API", "details": str(e)}


def run_web_analysis_flow(url_to_scrape: str):
    """Orchestre le flux web via une tâche asynchrone."""
    print("--- 🚀 Lancement de la tâche d'analyse WEB ---")
    payload = {"sourceType": "web", "sourceInput": url_to_scrape}
    return run_analysis_flow(payload)


def run_instagram_analysis_flow(usernames_str: str):
    """Orchestre le flux Instagram via une tâche asynchrone."""
    print("--- 🚀 Lancement de la tâche d'analyse INSTAGRAM ---")
    payload = {"sourceType": "instagram", "sourceInput": usernames_str}
    return run_analysis_flow(payload)


def run_text_enrichment_flow(analysis_results: dict):
    """FLUX N°1 : Gère uniquement la recherche web et la synthèse TEXTE."""
    print("\n--- 🚀 DÉBUT DU FLUX D'ENRICHISSEMENT TEXTE ---")
    if not analysis_results or 'error' in analysis_results:
        return "Erreur : Pas de résultats d'analyse de base à enrichir."

    # Cette partie de l'analyse des résultats reste identique
    analysis_data = analysis_results.get('result', analysis_results) # Gère les deux formats de retour

    analysis_summary = {
        "top_vetements": [g for g, d in analysis_data.get('garment_trends', {}).get('distribution', {}).items()][:1],
        "top_styles": [s for s, d in analysis_data.get('style_trends', {}).get('distribution', {}).items()][:1],
        "couleurs_dominantes": [c.get('color_name') for c in analysis_data.get('color_trends', {}).get('dominant_colors', [])[:1]]
    }
    search_plan = determine_search_queries(analysis_summary)
    web_results = {}
    if search_plan:
        all_queries = list(set(q for sublist in search_plan.values() for q in sublist))
        tavily_results = {query: search_external_web_with_tavily(query) for query in all_queries}
        for key in search_plan:
            web_results[key] = [result for query in search_plan.get(key, []) for result in tavily_results.get(query, [])]
    return generate_final_synthesis(analysis_summary, web_results)


def run_image_generation_flow(analysis_results: dict):
    """FLUX N°2 : Gère uniquement la génération d'IMAGE."""
    print("\n--- 🚀 DÉBUT DU FLUX DE GÉNÉRATION D'IMAGE ---")
    if not analysis_results or 'error' in analysis_results:
        return None

    analysis_data = analysis_results.get('result', analysis_results) # Gère les deux formats de retour

    analysis_summary = {
        "top_vetements": [g for g, d in analysis_data.get('garment_trends', {}).get('distribution', {}).items()][:1],
        "top_styles": [s for s, d in analysis_data.get('style_trends', {}).get('distribution', {}).items()][:1],
        "couleurs_dominantes": [c.get('color_name') for c in analysis_data.get('color_trends', {}).get('dominant_colors', [])[:1]]
    }
    
    sd_prompts = generate_sd_prompts(analysis_summary)
    
    if sd_prompts:
        return generate_image_on_backend(
            prompt=sd_prompts.get("prompt"),
            negative_prompt=sd_prompts.get("negative_prompt")
        )
    return None

# ==============================================================================
# SECTION 2 : FONCTIONS SPÉCIALISÉES (les "IA" et les "mains")
# ==============================================================================

def search_external_web_with_tavily(query: str):
    print(f"\n🌐 Recherche web TAVILY pour : '{query}'")
    if not TAVILY_API_KEY: return [{"error": "Clé API Tavily non configurée."}]
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily_client.search(query=query, search_depth="advanced", max_results=3)
        return [{"title": item.get("title"), "url": item.get("url"), "content": item.get("content")} for item in response.get("results", [])]
    except Exception as e:
        return [{"error": "Erreur de connexion à Tavily.", "details": str(e)}]

def determine_search_queries(analysis_summary: dict):
    print("\n🧠 IA n°1 (Le Stratège) : Création du plan de recherche...")
    next_year = datetime.now().year + 1
    top_color = (analysis_summary.get("couleurs_dominantes") or ["neutrals"])[0] or "neutres"
    top_garment = (analysis_summary.get("top_vetements") or ["clothing"])[0] or "vêtements"
    top_style = (analysis_summary.get("top_styles") or ["fashion"])[0] or "tendance"
    prompt = f"""
    En tant que prévisionniste de tendances, crée un plan de recherche au format JSON pour les tendances à venir ({next_year}).
    Tendances clés : Couleur='{top_color}', Vêtement='{top_garment}', Style='{top_style}'.
    Génère des requêtes précises pour chaque catégorie ci-dessous.
    {{
      "recherche_mode": ["tendance {top_garment} défilés {next_year}"],
      "recherche_design": ["influence couleur {top_color} design intérieur {next_year}"],
      "recherche_culture_medias": ["{top_style} dans les films récents ou la musique"]
    }}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a strategic Trend Forecaster assistant. You output only valid JSON."},
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur lors de la génération du plan de recherche : {e}")
        return {}

def generate_final_synthesis(analysis_summary: dict, web_results: dict):
    print("\n🧠 IA n°2 (Le Rédacteur Stratège) : Rédaction de l'analyse...")
    next_year = datetime.now().year + 1
    system_prompt = "Tu es un analyste de tendances senior pour un cabinet de conseil de renommée mondiale. Rédige un rapport prospectif, pointu et concis en te basant exclusivement sur les sources fournies. Cite chaque source utilisée au format (Source : [Titre](URL)). Si une information n'est pas dans les sources, indique 'Aucun signal pertinent détecté dans les sources'."
    user_prompt = f"""
    **DONNÉES BRUTES :**
    - Tendances identifiées : {json.dumps(analysis_summary, ensure_ascii=False)}
    - Résultats de la recherche web : {json.dumps(web_results, indent=2, ensure_ascii=False)}
    **MISSION : Rédige le rapport en suivant la structure ci-dessous.**
    ---
    # Analyse Prospective des Tendances {next_year}
    ## Vision Stratégique
    *(En 2-3 phrases, quelle est l'histoire principale ?)*
    ## Évaluation de la Tendance Mode
    *(Synthétise les informations "recherche_mode". Sois analytique sur la validation et la trajectoire future. Cite tes sources.)*
    ## Connexions Transversales
    - **Design & Architecture :** *(Synthèse de "recherche_design". Cite ta source.)*
    - **Culture & Médias :** *(Synthèse de "recherche_culture_medias". Cite ta source.)*
    ---
    """
    try:
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
        return response.choices[0].message.content
    except Exception as e:
        return f"### Erreur\n\nImpossible de générer le rapport final : {e}"

def generate_sd_prompts(analysis_summary: dict):
    """L'IA 'Directeur Artistique' crée le brief pour Stable Diffusion."""
    print("\n🎨 IA n°3 (Le Directeur Artistique) : Création du brief créatif...")
    top_garment = (analysis_summary.get("top_vetements") or ["a stylish outfit"])[0]
    top_style = (analysis_summary.get("top_styles") or ["fashion"])[0]
    top_color = (analysis_summary.get("couleurs_dominantes") or ["any color"])[0]
    prompt_template = f"""
    # MISSION
    Tu es un directeur artistique. Crée un prompt pour Stable Diffusion pour visualiser une tendance.
    # MOTS-CLÉS
    - Vêtement : "{top_garment}"
    - Style : "{top_style}"
    - Couleur : "{top_color}"
    # INSTRUCTIONS
    1.  **Sujet :** Décris un mannequin (homme ou femme) avec une posture neutre et élégante. Évite toute sexualisation.
    2.  **Prompt Positif :** Structure : Qualité (`(masterpiece, 8k, photorealistic:1.2)`), Sujet, Tenue (`wearing elegant ({top_color} {top_garment}:1.3) in a {top_style} aesthetic`), Arrière-plan, Ambiance.
    3.  **Prompt Négatif :** Inclus `EasyNegative`, défauts (`ugly, deformed, bad anatomy`), et termes de non-sexualisation (`nude, nsfw, suggestive`).
    4.  **Format de Sortie :** UNIQUEMENT un objet JSON avec les clés "prompt" et "negative_prompt".
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o", response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a creative director for fashion photography. You output only valid JSON."},
                {"role": "user", "content": prompt_template}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur lors de la génération des prompts : {e}")
        return None

def generate_image_on_backend(prompt: str, negative_prompt: str):
    """
    Appelle l'API du backend Node.js pour déclencher la génération d'image
    via Replicate.
    """
    print("\n🤖 Délégation de la génération d'image au service backend Node.js...")
    api_url = "https://trends-ai-backend-image2-382329904395.europe-west1.run.app/api/generation/generate-image"
    payload = {"prompt": prompt, "negative_prompt": negative_prompt}
    try:
        with requests.Session() as session:
            response = session.post(api_url, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        image_url = result.get('imageUrl')
        print(f"✅ Backend Node.js a déclenché la génération. URL de l'image : {image_url}")
        return image_url
    except requests.exceptions.RequestException as e:
        print(f"❌ ERREUR : Impossible de contacter votre backend Node.js pour la génération d'image. Détails : {e}")
        return None