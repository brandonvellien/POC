import sys
import json
import os
from openai import OpenAI
from tavily import TavilyClient
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# --- Fonctions Spécialisées (Helpers) ---

def search_external_web_with_tavily(query: str):
    """Effectue une recherche web avec l'API Tavily."""
    print(f"\n[Worker] Recherche web TAVILY pour : '{query}'", file=sys.stderr)
    if not TAVILY_API_KEY:
        return [{"error": "Clé API Tavily non configurée."}]
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily_client.search(query=query, search_depth="advanced", max_results=3)
        return [{"title": item.get("title"), "url": item.get("url"), "content": item.get("content")} for item in response.get("results", [])]
    except Exception as e:
        return [{"error": "Erreur de connexion à Tavily.", "details": str(e)}]

def determine_search_queries(analysis_summary: dict):
    """Détermine les requêtes de recherche stratégiques à effectuer."""
    print("\n[Worker] IA : Création du plan de recherche...", file=sys.stderr)
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
        print(f"❌ Erreur lors de la génération du plan de recherche : {e}", file=sys.stderr)
        return {}

def generate_final_synthesis(analysis_summary: dict, web_results: dict):
    """Génère le rapport final en Markdown à partir des données collectées."""
    print("\n[Worker] IA : Rédaction de l'analyse...", file=sys.stderr)
    next_year = datetime.now().year + 1
    system_prompt = "Tu es un analyste de tendances senior. Rédige un rapport prospectif, pointu et concis en te basant exclusivement sur les sources fournies. Cite chaque source utilisée au format (Source : [Titre](URL)). Si une information n'est pas dans les sources, indique 'Aucun signal pertinent détecté dans les sources'."
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

# --- FONCTION PRINCIPALE (celle qui manquait) ---

def run_text_enrichment_flow(analysis_results: dict):
    """Orchestre le flux complet de l'enrichissement de texte."""
    if not analysis_results or 'error' in analysis_results:
        return "Erreur : Pas de résultats d'analyse de base à enrichir."

    # Prépare un résumé des données d'entrée
    analysis_summary = {
        "top_vetements": [g for g, d in analysis_results.get('garment_trends', {}).get('distribution', {}).items()][:1],
        "top_styles": [s for s, d in analysis_results.get('style_trends', {}).get('distribution', {}).items()][:1],
        "couleurs_dominantes": [c.get('color_name') for c in analysis_results.get('color_trends', {}).get('dominant_colors', [])[:1]]
    }
    
    # Exécute les étapes
    search_plan = determine_search_queries(analysis_summary)
    web_results = {}
    if search_plan:
        all_queries = list(set(q for sublist in search_plan.values() for q in sublist))
        tavily_results = {query: search_external_web_with_tavily(query) for query in all_queries}
        for key in search_plan:
            web_results[key] = [result for query in search_plan.get(key, []) for result in tavily_results.get(query, [])]
    
    return generate_final_synthesis(analysis_summary, web_results)


# --- Point d'entrée du script ---
if __name__ == '__main__':
    # 1. Lire le rapport JSON depuis l'entrée standard (stdin)
    input_data = sys.stdin.read()
    analysis_report = json.loads(input_data)
    
    # 2. Lancer le flux d'enrichissement
    enriched_text = run_text_enrichment_flow(analysis_report)
    
    # 3. Imprimer le résultat final sur la sortie standard (stdout)
    print(enriched_text)