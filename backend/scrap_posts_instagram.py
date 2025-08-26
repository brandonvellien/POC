# scrap_posts_instagram.py - Version robuste
import http.client
import json
import os
import sys # Importé pour sys.exit et sys.stderr
import requests
from io import BytesIO
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

API_HOST = "instagram-scraper-api2.p.rapidapi.com"
API_KEY = os.environ.get("INSTAGRAM_API_KEY")
S3_BUCKET_NAME = 'trendsproject'

if not API_KEY:
    print("❌ Erreur: INSTAGRAM_API_KEY n'est pas définie dans .env", file=sys.stderr)
    sys.exit(1)

def upload_fileobj_to_s3(fileobj, bucket, object_name):
    """Téléverse un objet fichier vers S3 et arrête le script en cas d'erreur."""
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_fileobj(fileobj, bucket, object_name)
        s3_uri = f"s3://{bucket}/{object_name}"
        print(f"✅ Image téléversée vers : {s3_uri}")
        return s3_uri
    except ClientError as e:
        # MODIFICATION CRUCIALE : Arrête le script en cas d'erreur S3
        print(f"❌ Erreur S3 lors du téléversement de {object_name}: {e}", file=sys.stderr)
        sys.exit(1)

def get_posts_by_user(username):
    conn = http.client.HTTPSConnection(API_HOST)
    headers = {'x-rapidapi-key': API_KEY, 'x-rapidapi-host': API_HOST}
    endpoint = f"/v1.2/posts?username_or_id_or_url={username}"
    try:
        conn.request("GET", endpoint, headers=headers)
        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        print(f"Erreur de connexion ou de décodage JSON pour {username}: {e}", file=sys.stderr)
        return {}

def get_image_url(post):
    try:
        if isinstance(post, dict):
            if 'image_versions' in post and 'items' in post['image_versions']:
                return post['image_versions']['items'][0]['url']
            if post.get('media_type') == 8 and 'carousel_media' in post:
                for media in post['carousel_media']:
                    if 'image_versions' in media and 'items' in media['image_versions']:
                        return media['image_versions']['items'][0]['url']
    except Exception as e:
        print(f"Erreur lors de l'extraction de l'URL d'image: {e}", file=sys.stderr)
    return ''

def extract_post_id(post):
    return post.get('pk') or post.get('id') or ''

def main():
    if len(sys.argv) > 1:
        usernames = [name.strip() for name in sys.argv[1].split(',')]
    else:
        print("❌ Erreur: Veuillez fournir au moins un nom d'utilisateur.", file=sys.stderr)
        sys.exit(1)

    all_posts = []
    for username in usernames:
        print(f"\n📸 Récupération des posts pour : {username}")
        response_data = get_posts_by_user(username)
        if isinstance(response_data, dict) and response_data.get('data'):
            posts = response_data['data']
            print(f"✅ {len(posts)} posts trouvés. Traitement...")
            for post_key, post_value in posts.items():
                if isinstance(post_value, list):
                    for post in post_value:
                        if isinstance(post, dict):
                            try:
                                original_image_url = get_image_url(post)
                                post_id = extract_post_id(post)
                                s3_image_uri = None
                                if original_image_url and post_id:
                                    response = requests.get(original_image_url, timeout=20)
                                    response.raise_for_status()
                                    image_in_memory = BytesIO(response.content)
                                    s3_object_name = f"images/instagram/{username}/{post_id}.jpg"
                                    s3_image_uri = upload_fileobj_to_s3(image_in_memory, S3_BUCKET_NAME, s3_object_name)
                                post_data = {
                                    'username': username, 'id': post_id,
                                    'caption_text': post.get('caption', {}).get('text', ''),
                                    'image_url': s3_image_uri,
                                    'original_image_url': original_image_url,
                                    'media_type': post.get('media_type', '')}
                                all_posts.append(post_data)
                            except Exception as e:
                                print(f"⚠️ Erreur lors du traitement d'un post: {e}", file=sys.stderr)
        else:
            print(f"🚨 Échec de la récupération des données pour {username}.", file=sys.stderr)

    if not all_posts:
        print("\n❌ Aucun post traité. Fichier JSON non créé.", file=sys.stderr)
        sys.exit(1)

    # MODIFICATION : Enregistre le fichier dans le répertoire /tmp du conteneur
    json_filename = f'/tmp/instagram_posts_{"_".join(usernames)}.json'
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
    
    print(f"\n📂 Données enregistrées dans {json_filename} ✅")
    # Affiche le chemin absolu pour que Node.js le récupère
    print(f"JSON_FILE_PATH:{json_filename}")

if __name__ == "__main__":
    main()