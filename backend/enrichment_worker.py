import sys
import json
import os
import traceback
from openai import OpenAI
from tavily import TavilyClient
from datetime import datetime
from dotenv import load_dotenv

# --- Configuration (inchangée) ---
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

# --- Fonctions Spécialisées ---

def search_external_web_with_tavily(query: str):
    print(f"\n[Worker] Recherche web TAVILY pour : '{query}'", file=sys.stderr)
    if not TAVILY_API_KEY:
        return [{"error": "Clé API Tavily non configurée."}]
    try:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily_client.search(query=query, search_depth="advanced", max_results=3, topic="general")
        return [{"title": item.get("title"), "url": item.get("url"), "content": item.get("content")} for item in response.get("results", [])]
    except Exception as e:
        return [{"error": f"Erreur de connexion à Tavily: {e}"}]

def expand_concepts_with_ai(user_selections: dict):
    print("\n[Worker] IA : Étape A - Expansion des concepts...", file=sys.stderr)
    focus_parts = []
    if "garments" in user_selections and user_selections["garments"]: focus_parts.append("le vêtement '" + " ".join(user_selections["garments"]) + "'")
    if "style" in user_selections and user_selections["style"]: focus_parts.append("le style '" + user_selections["style"] + "'")
    if "color" in user_selections and user_selections["color"]: focus_parts.append("la couleur '" + user_selections["color"] + "'")
    focus_str = " et ".join(focus_parts) if focus_parts else "la mode en général"

    prompt = f"""
    Je suis un analyste de tendances. Mon sujet d'étude est {focus_str}.
    Pour préparer une recherche transversale, génère des concepts et des mots-clés associés dans les domaines suivants.
    Sois concis et pertinent. Retourne UNIQUEMENT un objet JSON.

    Exemple pour "slip dress":
    {{
      "mode": ["Kate Moss", "années 90", "satin", "minimalisme", "sous-vêtement apparent"],
      "design": ["fluidité", "formes organiques", "intérieur boudoir", "tissus drapés"],
      "culture": ["icônes grunge", "Sex and the City", "esthétique héroïne chic"]
    }}

    Génère le JSON pour le sujet : {focus_str}.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Tu es un assistant expert en tendances culturelles et design. Tu retournes uniquement du JSON valide."},
                {"role": "user", "content": prompt}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur lors de l'expansion des concepts : {e}", file=sys.stderr)
        return {}

def determine_search_queries(expanded_concepts: dict):
    print("\n[Worker] IA : Étape B - Création des requêtes de recherche ciblées...", file=sys.stderr)
    next_year = datetime.now().year + 1
    mode_keywords = " ".join(expanded_concepts.get("mode", []))
    design_keywords = " ".join(expanded_concepts.get("design", []))
    culture_keywords = " ".join(expanded_concepts.get("culture", []))

    search_plan = {
      "recherche_mode": [f"tendance mode {mode_keywords} {next_year}"] if mode_keywords else [],
      "recherche_design": [f"tendance design d'intérieur {design_keywords} {next_year}"] if design_keywords else [],
      "recherche_culture_medias": [f"analyse culturelle {culture_keywords} films musique"] if culture_keywords else []
    }
    return search_plan

def generate_final_synthesis(analysis_summary: dict, web_results: dict):
    print("\n[Worker] IA : Rédaction de l'analyse...", file=sys.stderr)
    next_year = datetime.now().year + 1
    sujet_principal = ", ".join(filter(None, [
        analysis_summary.get('style'),
        " ".join(analysis_summary.get('garments', [])),
        analysis_summary.get('color')
    ])) if analysis_summary else "la tendance analysée"

    system_prompt = f"""
    Tu es un analyste de tendances senior pour un cabinet de conseil de renommée mondiale.
    Ton sujet principal est : **{sujet_principal}**.
    Rédige un rapport prospectif, pointu et concis en te basant exclusivement sur les sources fournies.
    IMPORTANT : Chaque phrase et chaque idée que tu présentes doit être **directement et explicitement liée** à ton sujet principal. Ne parle pas de tendances générales si tu ne peux pas expliquer leur pertinence spécifique pour **{sujet_principal}**.
    Cite chaque source utilisée au format (Source : [Titre](URL)).
    """
    user_prompt = f"""
    **DONNÉES BRUTES :**
    - Résultats de la recherche web : {json.dumps(web_results, indent=2, ensure_ascii=False)}
    **MISSION : Rédige le rapport en suivant la structure ci-dessous et en restant focalisé sur le sujet.**
    ---
    # Analyse Prospective des Tendances {next_year}
    ## Vision Stratégique
    *(En 2-3 phrases, quelle est l'histoire principale qui se dégage des informations fournies à propos de **{sujet_principal}** ?)*
    ## Évaluation de la Tendance Mode
    *(Comment **{sujet_principal}** se manifeste-t-il dans la mode ? Cite tes sources.)*
    ## Connexions Transversales
    - **Design & Architecture :** *(Comment l'esthétique de **{sujet_principal}** se traduit-elle dans d'autres domaines créatifs ? Cite ta source.)*
    - **Culture & Médias :** *(Quels signaux culturels confirment la tendance de **{sujet_principal}** ? Cite ta source.)*
    ---
    """
    try:
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}])
        return response.choices[0].message.content
    except Exception as e:
        return f"### Erreur\n\nImpossible de générer le rapport final : {e}"

# --- FONCTION PRINCIPALE MISE À JOUR ---
def run_text_enrichment_flow(user_selections: dict):
    """Orchestre le flux complet de l'enrichissement de texte."""
    
    expanded_concepts = expand_concepts_with_ai(user_selections)
    search_plan = determine_search_queries(expanded_concepts)
    
    web_results = {}
    if search_plan:
        all_queries = [q for sublist in search_plan.values() for q in sublist if q]
        tavily_results = {query: search_external_web_with_tavily(query) for query in all_queries}
        
        # --- CORRECTION DE LA LIGNE EN ERREUR ---
        for key in search_plan:
            # On boucle sur les queries, puis sur les résultats de chaque query
            web_results[key] = [
                result_item 
                for query in search_plan.get(key, []) 
                for result_item in tavily_results.get(query, [])
            ]
        # --- FIN DE LA CORRECTION ---

    return generate_final_synthesis(user_selections, web_results)


# --- Point d'entrée du script (inchangé) ---
if __name__ == '__main__':
    input_data = sys.stdin.read()
    user_selections = json.loads(input_data)
    enriched_text = run_text_enrichment_flow(user_selections)
    print(enriched_text)