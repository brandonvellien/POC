import sys, json, os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def generate_sd_prompts(user_choices: dict):
    """Génère les prompts Stable Diffusion à partir des choix de l'utilisateur."""
    print("\n[Worker] IA : Création du brief créatif...", file=sys.stderr)
    
    # --- MODIFICATION ICI ---
    # On récupère le style et la nouvelle liste de vêtements colorés
    style = user_choices.get("style", "fashion")
    colored_garments = user_choices.get("coloredGarments", [])
    
    if not colored_garments:
        print("❌ Erreur: La liste 'coloredGarments' est vide.", file=sys.stderr)
        return None

    # On construit une description plus complexe
    # ex: "(Pantone Red Handbag:1.3) and (Pantone Blue Coat:1.3)"
    garments_str_parts = []
    for item in colored_garments:
        # On utilise le nom de la couleur (plus descriptif) plutôt que le code hexadécimal
        color_name = item.get("color", {}).get("name", "any color")
        garment_name = item.get("garment", "clothing")
        garments_str_parts.append(f"({color_name} {garment_name}:1.3)")
    
    garments_str = " and ".join(garments_str_parts)
    # --- FIN DE LA MODIFICATION ---
    
    prompt_template = f"""
    # MISSION
    Tu es un directeur artistique. Crée un prompt pour Stable Diffusion pour visualiser une tendance.
    # MOTS-CLÉS
    - Tenue : "{garments_str}"
    - Style : "{style}"
    # INSTRUCTIONS
    1.  Sujet : Décris un mannequin (homme ou femme) avec une posture neutre et élégante. Évite toute sexualisation.
    2.  Prompt Positif : Structure : Qualité (`(masterpiece, 8k, photorealistic:1.2)`), Sujet, Tenue (`wearing elegant {garments_str} in a {style} aesthetic`), Arrière-plan, Ambiance.
    3.  Prompt Négatif : Inclus `EasyNegative`, défauts (`ugly, deformed, bad anatomy`), et termes de non-sexualisation (`nude, nsfw, suggestive`).
    4.  Format de Sortie : UNIQUEMENT un objet JSON avec les clés "prompt" et "negative_prompt".
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o", response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a creative director. You output only valid JSON."},
                {"role": "user", "content": prompt_template}
            ]
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Erreur lors de la génération des prompts : {e}", file=sys.stderr)
        return None

if __name__ == '__main__':
    input_data = sys.stdin.read()
    user_selections = json.loads(input_data)
    prompts = generate_sd_prompts(user_selections)
    if prompts:
        print(json.dumps(prompts)) # Imprime le JSON des prompts en sortie