import requests
import json

# L'URL de l'endpoint que vous avez créé dans votre backend Node.js
API_URL = "http://localhost:3000/api/generation/generate-image"

# Un prompt de test simple et clair
PROMPT_DE_TEST = "Photographie de mode haute qualité d'une mannequin portant un blazer bleu électrique et un pantalon assorti, style années 80, dans une rue de Tokyo la nuit."

# Un prompt négatif standard
NEGATIVE_PROMPT_DE_TEST = "dessin, 3d, render, cartoon, grain, blurry, malformed, disfigured, bad anatomy, moches"

def test_image_generation():
    """
    Envoie une requête de test directement à l'API de génération d'images.
    """
    print(f"--- Lancement du test d'appel API vers : {API_URL} ---")

    payload = {
        "prompt": PROMPT_DE_TEST,
        "negative_prompt": NEGATIVE_PROMPT_DE_TEST
    }

    try:
        print("Envoi de la requête au backend...")
        response = requests.post(API_URL, json=payload, timeout=300) # Timeout de 5 minutes

        # Vérifie si la requête a réussi (code de statut 2xx)
        response.raise_for_status()

        print("\n✅ Succès ! Réponse du backend :")
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.RequestException as e:
        print(f"\n❌ Erreur ! Impossible de contacter le backend.")
        print(f"   Assurez-vous que votre serveur backend Node.js est bien lancé sur le port 3000.")
        print(f"   Détails de l'erreur : {e}")
    except Exception as e:
        print(f"\n❌ Une erreur inattendue est survenue : {e}")

if __name__ == '__main__':
    test_image_generation()