import streamlit as st
import os
import json
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import sys 
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(current_dir, 'backend')
sys.path.append(backend_path)
# CORRECTION : On importe bien les deux fonctions séparées de l'orchestrateur
from orchestrator import run_web_analysis_flow, run_instagram_analysis_flow, run_text_enrichment_flow, run_image_generation_flow

# --- Configuration ---
load_dotenv()
st.set_page_config(layout="wide", page_title="TrendsAI Pro")

# --- Initialisation de l'état de session ---
# On s'assure que toutes nos clés existent au démarrage pour éviter les erreurs
def init_session_state():
    keys_to_init = ['analysis_results', 'final_report', 'generated_image_url', 'error_message', 'error_details']
    for key in keys_to_init:
        if key not in st.session_state:
            st.session_state[key] = None

init_session_state()

# --- Fonctions de l'UI ---
def reset_all_states():
    """Réinitialise uniquement les clés de résultats, pas les clés des widgets."""
    keys_to_reset = ['analysis_results', 'final_report', 'generated_image_url', 'error_message', 'error_details']
    for key in keys_to_reset:
        if key in st.session_state:
            st.session_state[key] = None

# --- Interface Utilisateur ---
st.title("✨ TrendsAI Pro - Analyse & Création")
st.caption("De l'analyse de données à la visualisation créative des tendances futures.")

tab1, tab2 = st.tabs(["Analyse depuis une URL Web (Défilés)", "Analyse depuis des comptes Instagram"])

with tab1:
    st.header("Analyser les images d'un défilé")
    url_input = st.text_input("URL de la collection", "https://www.tag-walk.com/en/collection/woman/acne-studios/spring-summer-2025", key="url_input")
    if st.button("🚀 Lancer l'analyse Web", key="web_button"):
        reset_all_states()
        with st.spinner("Analyse de base en cours (peut prendre quelques minutes)..."):
            results = run_web_analysis_flow(url_input)
            if isinstance(results, dict) and 'error' in results:
                st.session_state.error_message = results.get('error')
                st.session_state.error_details = results.get('details')
            else:
                st.session_state.analysis_results = results
                st.success("Analyse de base terminée ! Prêt pour l'enrichissement et la création.")
                st.rerun()

with tab2:
    st.header("Analyser des comptes Instagram")
    insta_accounts_input = st.text_input("Comptes (séparés par virgule)", "dior,balenciaga", key="insta_input")
    if st.button("🚀 Lancer l'analyse Instagram", key="insta_button"):
        reset_all_states()
        with st.spinner("Analyse en cours..."):
            results = run_instagram_analysis_flow(insta_accounts_input)
            if isinstance(results, dict) and 'error' in results:
                st.session_state.error_message = results.get('error')
                st.session_state.error_details = results.get('details')
            else:
                st.session_state.analysis_results = results
                st.success("Analyse de base terminée ! Prêt pour l'enrichissement et la création.")
                st.rerun()

# --- Section d'affichage des résultats ---
st.divider()

if st.session_state.error_message:
    st.error(f"**Erreur :** {st.session_state.error_message}")
    with st.expander("Détails de l'erreur"):
        st.code(st.session_state.error_details, language='bash')

if st.session_state.analysis_results:
    st.header("📊 Résultats de l'Analyse de Base")
    results = st.session_state.analysis_results
    
    with st.expander("Voir les images analysées"):
        image_list = results.get('detailed_image_analysis', [])
        if image_list:
            aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
            if not aws_access_key or not aws_secret_key:
                st.error("Clés AWS non configurées dans .env. Impossible d'afficher les images.")
            else:
                try:
                    s3_client = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, region_name='eu-north-1')
                    presigned_urls = []
                    for img in image_list:
                        source_url = img.get('source', '')
                        if source_url and source_url.startswith('s3://'):
                            bucket_name, key = source_url.replace('s3://', '').split('/', 1)
                            url = s3_client.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': key}, ExpiresIn=3600)
                            presigned_urls.append(url)
                    
                    if presigned_urls:
                        st.image(presigned_urls, width=150)
                    else:
                        st.info("Aucune image S3 n'a été trouvée dans le rapport à afficher.")
                except ClientError as e:
                    st.error(f"Erreur d'accès à S3. Détails: {e}")
                except Exception as e:
                    st.error(f"Une erreur inattendue est survenue lors de la récupération des images: {e}")
        else:
            st.info("Aucune image détaillée disponible dans ce rapport.")

    st.subheader("Vue d'ensemble des tendances détectées")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Palette de couleurs**")
        dominant_colors = results.get('color_trends', {}).get('dominant_colors', [])
        if dominant_colors:
            for color in dominant_colors[:8]:
                hex_code = color.get('hex', '#FFFFFF'); percentage = color.get('percentage', 0)
                st.markdown(f"""<div style="display:flex;align-items:center;margin-bottom:5px;"><div style="width:20px;height:20px;background-color:{hex_code};border:1px solid #ccc;margin-right:10px;border-radius:3px;"></div><div>{color.get('color_name')} ({percentage:.1f}%)</div></div>""", unsafe_allow_html=True)
        else: 
            st.info("Aucune donnée sur les couleurs.")
            
    with col2:
        st.markdown("**Vêtements fréquents**")
        garment_dist = results.get('garment_trends', {}).get('distribution', {})
        if garment_dist:
            total_garments = sum(v.get('count', 0) for v in garment_dist.values())
            if total_garments > 0:
                sorted_garments = sorted(garment_dist.items(), key=lambda item: item[1]['count'], reverse=True)
                for g, d in sorted_garments[:5]:
                    percentage = (d.get('count', 0) / total_garments) * 100
                    st.markdown(f"- `{g.capitalize()}` ({percentage:.1f}%)")
            else: 
                st.info("Aucune donnée sur les vêtements.")
        else: 
            st.info("Aucune donnée sur les vêtements.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Styles principaux**")
        style_dist = results.get('style_trends', {}).get('distribution', {})
        if style_dist:
            total_styles = sum(v.get('count', 0) for v in style_dist.values())
            if total_styles > 0:
                sorted_styles = sorted(style_dist.items(), key=lambda item: item[1]['count'], reverse=True)
                for s, d in sorted_styles[:5]:
                    percentage = (d.get('count', 0) / total_styles) * 100
                    st.markdown(f"- `{s.capitalize()}` ({percentage:.1f}%)")
            else: 
                st.info("Aucune donnée sur les styles.")
        else: 
            st.info("Aucune donnée sur les styles.")

    # --- SECTION GRAPHIQUES (CONSERVÉE) ---
    with st.expander("Voir les graphiques de l'analyse"):
        st.subheader("Graphiques de l'analyse")
        img_col1, img_col2 = st.columns(2)
        with img_col1:
            if os.path.exists("fashion_trends_overview.png"):
                st.image("fashion_trends_overview.png", caption="Vue d'ensemble des tendances")
        with img_col2:
            if os.path.exists("colors_by_garment.png"):
                st.image("colors_by_garment.png", caption="Couleurs par type de vêtement")
        
        # Le JSON brut n'est plus affiché ici
    
    # --- SECTION D'ENRICHISSEMENT ET DE CRÉATION (MODIFIÉE) ---
    st.divider()
    st.header("🧠 Enrichissement & Création Visuelle")
    
    col_report, col_image = st.columns(2)

    with col_report:
        st.subheader("Rapport de Synthèse Stratégique")
        if st.button("Générer le Rapport Texte ✨", key="text_report_button", type="primary"):
            with st.spinner("Rédaction du rapport par l'IA..."):
                # On appelle la fonction pour le texte
                st.session_state.final_report = run_text_enrichment_flow(st.session_state.analysis_results)
        
        if st.session_state.final_report:
            st.markdown(st.session_state.final_report, unsafe_allow_html=True)

    with col_image:
        st.subheader("Visualisation de la Tendance par l'IA")
        if st.button("Générer l'Image Concept 🎨", key="image_gen_button"):
             with st.spinner("Création du concept visuel... (peut prendre plusieurs minutes)"):
                # On appelle la fonction pour l'image
                st.session_state.generated_image_url = run_image_generation_flow(st.session_state.analysis_results)
        
        if st.session_state.generated_image_url:
            st.image(st.session_state.generated_image_url, caption="Concept visuel généré par IA", use_container_width=True)
        else:
            st.info("Cliquez sur le bouton pour générer une visualisation de la tendance principale.")
        
elif not st.session_state.error_message:
    st.info("Lancez une analyse depuis l'un des onglets pour commencer.")