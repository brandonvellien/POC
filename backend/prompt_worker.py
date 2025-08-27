import sys
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_art_director_prompts(user_choices: dict):
    """
    Agit comme un directeur artistique : interprète les choix de l'utilisateur
    pour créer le prompt parfait pour l'IA de génération d'image.
    """
    print("\n[Worker] IA : Interprétation du brief par le Directeur Artistique...", file=sys.stderr)
    
    style = user_choices.get("style", "fashion")
    colored_garments = user_choices.get("coloredGarments", [])
    
    if not colored_garments:
        return None

    # --- NOUVELLE LOGIQUE DE TRADUCTION ---

    # 1. On prépare une description détaillée pour chaque vêtement
    garment_details_list = []
    for item in colored_garments:
        color_obj = item.get("color", {})
        full_color_name = color_obj.get("color_name", "any color")
        color_hex = color_obj.get("hex", "#FFFFFF") # On inclut le code HEX !
        garment_name = item.get("garment", "clothing")
        
        garment_details_list.append(
            f"- Vêtement: '{garment_name}', Couleur: '{full_color_name}' (HEX: {color_hex})"
        )
    
    garment_brief = "\n".join(garment_details_list)

    # 2. On crée un template de prompt ultra-précis pour GPT-4o
    prompt_template = f"""
    # MISSION
    Tu es un directeur artistique expert en IA générative. Ta mission est de traduire un brief de mode en un prompt parfait pour un modèle d'image comme Stable Diffusion (utilisé via Replicate).

    # BRIEF CLIENT (DONNÉES BRUTES)
    {garment_brief}
    - Style global : "{style}"

    # TES INSTRUCTIONS (TRÈS IMPORTANTES)
    1.  **INTERPRÈTE LA COULEUR** : Le client donne des noms de couleurs Pantone (ex: "Driftwood") et leur code HEX. Le modèle d'image ne comprend pas ces noms. Ta tâche est de **décrire la couleur** en termes simples et universels. Par exemple, pour "Driftwood" (HEX: #A69489), tu décriras "a warm, sandy beige color". Pour "Jazzy" (HEX: #D93A83), tu décriras "a vibrant, bold pink color".
    2.  **CHOISIS LE GENRE** : Analyse les vêtements. Pour "slip dress", "skirt", "blouse", choisis "a female model". Pour "suit", "jacket", "pants", choisis "a male or female model". Sois logique.
    3.  **CONSTRUIS LE PROMPT POSITIF** :
        - Commence TOUJOURS par la qualité : `masterpiece, 8k, photorealistic, professional fashion photography,`
        - Décris le sujet et la tenue en utilisant ta **description de couleur** : `full body shot of [ton choix de genre] wearing [description de la tenue avec la couleur interprétée]`
        - Sois créatif pour le décor : Invente un arrière-plan qui correspond au style "{style}".
    4.  **CONSTRUIS LE PROMPT NÉGATIF** : `EasyNegative, ugly, deformed, bad anatomy, blurry, text, watermark, logo, nude, nsfw, sexually suggestive`
    5.  **FORMAT DE SORTIE** : Réponds UNIQUEMENT avec un objet JSON valide contenant les clés "prompt" et "negative_prompt". Ne mets rien d'autre.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are an expert AI art director. You only output valid JSON."},
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
    prompts = generate_art_director_prompts(user_selections)
    if prompts:
        print(json.dumps(prompts))