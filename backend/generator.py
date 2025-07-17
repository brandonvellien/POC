# generator.py - Utilisation de l'API Replicate pour la génération d'images

import argparse
import os
from datetime import datetime
import sys
import traceback
import boto3
from botocore.exceptions import ClientError
import requests # Import nécessaire pour télécharger l'image depuis l'URL de Replicate

# --- Import de la bibliothèque Replicate ---
import replicate
# --- FIN de l'Import Replicate ---

# --- DÉBUT DE LA FONCTION D'ENVOI S3 (Inchngée) ---
def upload_to_s3(local_file_path: str, bucket_name: str, s3_object_name: str):
    """
    Téléverse un fichier depuis un chemin local vers un bucket S3.
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(local_file_path, bucket_name, s3_object_name)
        s3_uri = f"s3://{bucket_name}/{s3_object_name}"
        print(f"✅ Fichier téléversé avec succès vers : {s3_uri}")
        return s3_uri
    except ClientError as e:
        print(f"❌ Erreur lors de l'envoi vers S3 : {e}", file=sys.stderr)
        return None
# --- FIN DE LA FONCTION D'ENVOI S3 ---


def generate_image(prompt: str, negative_prompt: str, output_folder="public/generated_images"):
    """
    Génère une image via l'API Replicate, la sauvegarde temporairement, puis l'envoie sur S3.
    """
    print(f"--- Démarrage du générateur d'image via Replicate API ---")
    print(f"Prompt: '{prompt[:70]}...'")

    # --- Vérification de la variable d'environnement REPLICATE_API_TOKEN ---
    if "REPLICATE_API_TOKEN" not in os.environ:
        print("❌ ERREUR : La variable d'environnement REPLICATE_API_TOKEN n'est pas définie.", file=sys.stderr)
        sys.exit(1)
    # --- FIN de la vérification ---

    try:
        # --- APPEL À L'API REPLICATE ---
        # Le modèle "black-forest-labs/flux-schnell" est celui de votre documentation.
        # Vous pouvez le remplacer par un autre modèle Stable Diffusion XL sur Replicate si vous préférez (ex: "stability-ai/sdxl").
        print(f"Appel à l'API Replicate pour le modèle 'black-forest-labs/flux-schnell'...")
        output_replicate = replicate.run(
            "black-forest-labs/flux-schnell", # Modèle Replicate à utiliser
            input={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                # Ajoutez ici d'autres paramètres si le modèle Replicate les supporte et que vous voulez les contrôler
                # Par exemple: "width": 1024, "height": 1024, "num_inference_steps": 50, "guidance_scale": 7.5
            }
        )
        # L'API Replicate retourne une liste d'URLs (même s'il n'y a qu'une image)
        # output_replicate est une liste d'objets Replicate.File.
        # Vous pouvez accéder à l'URL via item.url().

        if not output_replicate:
            print("❌ ERREUR : L'API Replicate n'a retourné aucune image.", file=sys.stderr)
            return None

        # Nous prenons la première image générée
        image_url = output_replicate[0] # Accès direct à l'URL si c'est déjà une chaîne # Accès à l'URL du fichier
        print(f"Image générée par Replicate : {image_url}")

        # --- TÉLÉCHARGEMENT DE L'IMAGE DEPUIS L'URL ET SAUVEGARDE TEMPORAIRE ---
        response = requests.get(image_url, stream=True)
        response.raise_for_status() # Lève une exception pour les codes d'état d'erreur HTTP

        os.makedirs(output_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Le format de l'image peut être .webp ou .png selon le modèle Replicate
        # On extrait l'extension de l'URL pour la rendre dynamique
        file_extension = os.path.splitext(image_url)[1] if '.' in image_url else '.png' # Fallback au cas où
        
        relative_path = os.path.join(output_folder, f"trend_{timestamp}{file_extension}")
        project_root = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(project_root, '..', 'backend', relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        with open(absolute_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"Image temporaire téléchargée et sauvegardée : {absolute_path}")
        # --- FIN DU TÉLÉCHARGEMENT ---
        
        # --- ENVOI VERS S3 (Inchngée) ---
        s3_bucket = "trendsproject" # Assurez-vous que c'est le bon nom de bucket
        s3_object_name = f"generated-trends/{os.path.basename(absolute_path)}"
        
        print(f"Tentative d'envoi vers S3 : {s3_bucket}/{s3_object_name}")
        s3_uri = upload_to_s3(absolute_path, s3_bucket, s3_object_name)

        # Nettoyage du fichier local après l'envoi
        if s3_uri:
            os.remove(absolute_path)
            print(f"Fichier local temporaire supprimé : {absolute_path}")
        else:
            print("L'envoi vers S3 a échoué, le fichier local n'a pas été supprimé.", file=sys.stderr)
            return None # On arrête s'il y a eu une erreur d'upload

        # On retourne l'adresse S3
        return s3_uri

    except replicate.exceptions.ReplicateException as e:
        print(f"❌ ERREUR API REPLICATE : {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ ERREUR DE TÉLÉCHARGEMENT DE L'IMAGE : {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERREUR CRITIQUE inattendue dans generator.py : {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Générateur d'images Stable Diffusion via Replicate.")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt de description de l'image.")
    parser.add_argument("--negative_prompt", type=str, default="ugly, deformed, bad anatomy, nude, nsfw, suggestive", help="Prompt négatif.")
    args = parser.parse_args()

    s3_path = generate_image(args.prompt, args.negative_prompt)

    if s3_path:
        # ON MODIFIE LA SORTIE POUR ÊTRE COHÉRENTE avec le format attendu par orchestrator.py
        print(f"S3_URI_PATH:{s3_path}")
    else:
        sys.exit(1)