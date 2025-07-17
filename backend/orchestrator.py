# orchestrator.py - VERSION FINALE, COMPLÈTE ET CORRIGÉE

import subprocess
import os
import json
import re
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
# SECTION 1 : FONCTION UTILITAIRE D'EXÉCUTION
# ==============================================================================

def run_script(command):
    """Exécute un script et gère la sortie."""
    print(f"\n▶️ EXÉCUTION : {' '.join(command)}")
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        full_output = [line for line in iter(process.stdout.readline, '')]
        process.wait()
        output_str = "".join(full_output)
        print(output_str)
        if process.returncode != 0:
            return False, output_str
        return True, output_str
    except Exception as e:
        return False, str(e)

# ==============================================================================
# SECTION 2 : FONCTIONS "CHEF D'ORCHESTRE" PRINCIPALES (appelées par app.py)
# ==============================================================================

def run_web_analysis_flow(url_to_scrape: str):
    """Orchestre le flux complet pour l'analyse d'une URL web."""
    print("--- 🚀 DÉBUT DU FLUX D'ANALYSE WEB ---")
    scrape_command = ["python3", "bucket.py", url_to_scrape]
    success, output = run_script(scrape_command)
    if not success: return {"error": "Échec du script de scraping (bucket.py)", "details": output}
    
    match = re.search(r"S3_FOLDER_PATH:(s3://.*)", output)
    if not match: return {"error": "Impossible de trouver le chemin S3.", "details": output}
    
    s3_folder_path = match.group(1).strip()
    analysis_command = ["python3", "test_slglip2.py", s3_folder_path]
    success, output = run_script(analysis_command)
    if not success: return {"error": "Échec du script d'analyse d'images.", "details": output}

    try:
        with open('fashion_trends_report.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": "Erreur de lecture du fichier JSON final.", "details": str(e)}

def run_instagram_analysis_flow(usernames_str: str):
    """Orchestre le flux complet pour l'analyse de comptes Instagram."""
    print("--- 🚀 DÉBUT DU FLUX D'ANALYSE INSTAGRAM ---")
    scrape_command = ["python3", "scrap_posts_instagram.py", usernames_str]
    success, output = run_script(scrape_command)
    if not success: return {"error": "Échec du script de scraping Instagram.", "details": output}
        
    match = re.search(r"JSON_FILE_PATH:(.*)", output)
    if not match: return {"error": "Impossible de trouver le chemin du fichier JSON.", "details": output}
        
    json_file_path = match.group(1).strip()
    analysis_command = ["python3", "test_slglip2.py", json_file_path]
    success, output = run_script(analysis_command)
    if not success: return {"error": "Échec du script d'analyse d'images.", "details": output}
        
    try:
        with open('fashion_trends_report.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return {"error": "Erreur de lecture du fichier JSON final.", "details": str(e)}

# Dans orchestrator.py

def run_text_enrichment_flow(analysis_results: dict):
    """FLUX N°1 : Gère uniquement la recherche web et la synthèse TEXTE."""
    print("\n--- 🚀 DÉBUT DU FLUX D'ENRICHISSEMENT TEXTE ---")
    if not analysis_results or 'error' in analysis_results:
        return "Erreur : Pas de résultats d'analyse de base à enrichir."

    analysis_summary = {
        "top_vetements": [g for g, d in analysis_results.get('garment_trends', {}).get('distribution', {}).items()][:1],
        "top_styles": [s for s, d in analysis_results.get('style_trends', {}).get('distribution', {}).items()][:1],
        "couleurs_dominantes": [c.get('color_name') for c in analysis_results.get('color_trends', {}).get('dominant_colors', [])[:1]]
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

    analysis_summary = {
        "top_vetements": [g for g, d in analysis_results.get('garment_trends', {}).get('distribution', {}).items()][:1],
        "top_styles": [s for s, d in analysis_results.get('style_trends', {}).get('distribution', {}).items()][:1],
        "couleurs_dominantes": [c.get('color_name') for c in analysis_results.get('color_trends', {}).get('dominant_colors', [])[:1]]
    }
    
    sd_prompts = generate_sd_prompts(analysis_summary)
    
    if sd_prompts:
        # CORRECTION : On appelle la bonne fonction qui parle au backend
        return generate_image_on_backend(
            prompt=sd_prompts.get("prompt"),
            negative_prompt=sd_prompts.get("negative_prompt")
        )
    return None

# ==============================================================================
# SECTION 3 : FONCTIONS SPÉCIALISÉES (les "IA" et les "mains")
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
    # L'URL ci-dessous sera l'URL de votre backend Node.js déployé.
    # Pour l'instant, nous utilisons localhost pour les tests locaux.
    api_url = "http://localhost:3000/api/generation/generate-image"
    payload = {"prompt": prompt, "negative_prompt": negative_prompt}
    try:
        # Utilise une session requests pour des appels plus robustes
        with requests.Session() as session:
            response = session.post(api_url, json=payload, timeout=300) # Augmente le timeout
        response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP (4xx ou 5xx)
        result = response.json()
        image_url = result.get('imageUrl')
        print(f"✅ Backend Node.js a déclenché la génération. URL de l'image (Replicate via generator.py) : {image_url}")
        return image_url
    except requests.exceptions.RequestException as e:
        print(f"❌ ERREUR : Impossible de contacter votre backend Node.js à {api_url} pour la génération d'image. Détails : {e}")
        return None