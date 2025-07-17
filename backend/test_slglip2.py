import os
import sys
import json
import requests
import torch
import clip
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from sklearn.cluster import KMeans
import colorsys
from collections import Counter
from io import BytesIO
import pandas as pd
from matplotlib.patches import Rectangle
import traceback
from rembg import remove
import datetime
import boto3
import argparse
from skimage.color import rgb2lab, deltaE_cie76



os.environ["TOKENIZERS_PARALLELISM"] = "false"

class NumpyJSONEncoder(json.JSONEncoder):
    """ Classe pour encoder correctement les types de données NumPy en JSON. """
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        elif isinstance(obj, np.floating): return float(obj)
        elif isinstance(obj, np.ndarray): return obj.tolist()
        elif isinstance(obj, (datetime.datetime, datetime.date)): return obj.isoformat()
        return super(NumpyJSONEncoder, self).default(obj)

TREND_MAP = {
    "Tops": ["t-shirt", "blouse", "shirt", "tank top", "crop top", "sweater", "cardigan", "hoodie", "sweatshirt", "turtleneck"],
    "Bottoms": ["jeans", "pants", "shorts", "skirt", "leggings", "joggers", "cargo pants", "wide-leg pants", "culottes"],
    "Dresses": ["dress", "maxi dress", "midi dress", "mini dress", "slip dress", "bodycon dress"],
    "Outerwear": ["jacket", "coat", "blazer", "bomber jacket", "denim jacket", "leather jacket", "trench coat", "puffer jacket"],
    "Sets & Jumpsuits": ["suit", "jumpsuit", "romper", "co-ord set", "tracksuit"],
    "Activewear": ["sports bra", "athletic shorts", "tennis skirt"],
    "Shoes": ["sneakers", "boots", "heels", "sandals", "flats", "loafers", "platform shoes", "mules"],
    "Bags": ["handbag", "backpack", "tote bag", "clutch"],
    "Accessories": ["belt", "scarf", "hat", "cap", "sunglasses", "earrings", "necklace"]
}

class FashionTrendColorAnalyzer:
    def __init__(self, image_source):
        self.image_source = image_source
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Utilisation du device : {self.device}")
        self.model, self.preprocess = clip.load("ViT-L/14@336px", device=self.device)
        self.image_paths = self._collect_image_sources()
        self.fashion_categories = [item for sublist in TREND_MAP.values() for item in sublist]
        self.pantone_library = self._load_pantone_library()
        self.fashion_styles = ["minimalist", "streetwear", "bohemian", "vintage", "preppy", "athleisure", "business casual", "formal", "avant-garde", "sustainable", "cottagecore", "y2k", "goth", "punk", "grunge", "luxury", "haute couture", "casual", "resort wear", "workwear", "retro", "urban", "hip-hop", "sporty"]
        self.fashion_color_ranges = [(0, 15, 'True Red', '#D12631', 'Pantone 18-1662 TCX'),(15, 30, 'Coral & Salmon', '#FF6F61', 'Pantone 16-1546 TCX'),(30, 45, 'Terracotta & Clay', '#BD4B37', 'Pantone 18-1438 TCX'),(45, 60, 'Amber & Caramel', '#D78A41', 'Pantone 16-1342 TCX'),(60, 75, 'Cognac & Rust', '#A5552A', 'Pantone 18-1248 TCX'),(75, 90, 'Mustard & Ochre', '#DBAF3A', 'Pantone 15-0948 TCX'),(90, 105, 'Canary & Lemon', '#F9E04C', 'Pantone 12-0643 TCX'),(105, 135, 'Olive & Moss', '#5E6738', 'Pantone 18-0430 TCX'),(135, 165, 'Sage & Mint', '#AABD8C', 'Pantone 15-6316 TCX'),(165, 195, 'Emerald & Jade', '#00A170', 'Pantone 17-5641 TCX'),(195, 225, 'Teal & Aqua', '#4799B7', 'Pantone 16-4834 TCX'),(225, 255, 'Cobalt & Denim', '#0047AB', 'Pantone 19-4045 TCX'),(255, 270, 'Navy & Indigo', '#1D334A', 'Pantone 19-4027 TCX'),(270, 285, 'Lavender & Lilac', '#B69FCB', 'Pantone 16-3416 TCX'),(285, 315, 'Violet & Amethyst', '#9678B6', 'Pantone 17-3628 TCX'),(315, 330, 'Mauve & Plum', '#8E4585', 'Pantone 19-2428 TCX'),(330, 345, 'Berry & Raspberry', '#C6174E', 'Pantone 18-2140 TCX'),(345, 360, 'Blush & Rose', '#E8B4B8', 'Pantone 14-1511 TCX')]

    def _hex_to_rgb(self, hex_code):
            """Convertit un code couleur HEX en tuple RGB."""
            hex_code = hex_code.lstrip('#')
            return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    def _load_pantone_library(self, json_path='pantone_colors.json'):
        """Charge et pré-calcule la bibliothèque de couleurs Pantone depuis un fichier JSON."""
        try:
            # Pour gérer les cas où le script est appelé depuis un autre dossier
            script_dir = os.path.dirname(__file__)
            full_path = os.path.join(script_dir, json_path)

            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            library = []
            for code, details in data.items():
                rgb = self._hex_to_rgb(details['hex'])
                library.append({
                    'name': f"PANTONE {code} {details['name'].replace('-', ' ').title()}",
                    'hex': f"#{details['hex']}",
                    'rgb': rgb
                })

            rgb_colors = np.array([item['rgb'] for item in library])
            lab_colors = rgb2lab(rgb_colors.reshape(len(rgb_colors), 1, 3).astype(np.uint8))

            for i, item in enumerate(library):
                item['lab'] = lab_colors[i][0]

            print(f"Bibliothèque Pantone chargée avec {len(library)} couleurs.")
            return library
        except FileNotFoundError:
            print(f"AVERTISSEMENT : Le fichier de la bibliothèque Pantone '{json_path}' est introuvable.")
            return None
    
    def _collect_image_sources(self):
        """Collects image sources from either a JSON file with S3 URLs or an S3 folder path."""
        image_sources = []
        source = self.image_source

        if source.lower().endswith('.json'): # From Instagram Scraper
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for post in data:
                if post.get("image_url") and post["image_url"].startswith('s3://'):
                    image_sources.append(post["image_url"])
        
        elif source.startswith('s3://'): # From Web Scraper
            print(f"Source S3 détectée : {source}")
            s3_client = boto3.client('s3')
            bucket_name, prefix = source.replace('s3://', '').split('/', 1)
            
            paginator = s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                for obj in page.get('Contents', []):
                    key = obj['Key']
                    if key.lower().endswith(('.jpg', '.jpeg')):
                        image_sources.append(f's3://{bucket_name}/{key}')
        
        if not image_sources:
            raise ValueError(f"Aucune image S3 trouvée pour la source {source}.")
            
        print(f"Found {len(image_sources)} images to analyze from S3.")
        return image_sources

    def _load_image(self, image_source):
        # This function should already be correct from previous steps
        # It must be able to handle s3:// paths
        try:
            if image_source.startswith('s3://'):
                s3_client = boto3.client('s3')
                bucket_name, key = image_source.replace('s3://', '').split('/', 1)
                response = s3_client.get_object(Bucket=bucket_name, Key=key)
                return Image.open(BytesIO(response['Body'].read())).convert('RGB')
            # ... other loading logic can remain if needed ...
        except Exception as e:
            print(f"Error loading {image_source}: {e}")
            return None

    def _isolate_subject(self, image_pil):
        try:
            return remove(image_pil.convert('RGBA'))
        except Exception as e:
            print(f"Could not remove background: {e}. Using original image.")
            return image_pil.convert('RGBA')

    def _classify_fashion_item(self, image_pil):
        image_input = self.preprocess(image_pil).unsqueeze(0).to(self.device)
        text_inputs = clip.tokenize(self.fashion_categories).to(self.device)
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
            text_features = self.model.encode_text(text_inputs)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            logits_per_image = 100.0 * image_features @ text_features.T
            probs = logits_per_image.softmax(dim=-1).squeeze().tolist()
            all_garment_scores = sorted([(cat, prob) for cat, prob in zip(self.fashion_categories, probs)], key=lambda x: x[1], reverse=True)
            style_inputs = clip.tokenize(self.fashion_styles).to(self.device)
            style_features = self.model.encode_text(style_inputs)
            style_features /= style_features.norm(dim=-1, keepdim=True)
            style_logits = 100.0 * image_features @ style_features.T
            style_probs = style_logits.softmax(dim=-1).squeeze().tolist()
            all_style_scores = sorted([(style, prob) for style, prob in zip(self.fashion_styles, style_probs)], key=lambda x: x[1], reverse=True)
            return {'garment_scores': all_garment_scores, 'style_scores': all_style_scores}

    def analyze_fashion_trends(self, num_colors=15, min_cluster_size=100, confidence_threshold=0.01):
        all_colors, all_color_objects, all_garment_types, all_style_types, self.image_analysis_results = [], [], [], [], []
        print("\n--- Starting Main Trend Analysis ---")
        for i, image_source in enumerate(self.image_paths):
            print(f"Processing image {i+1}/{len(self.image_paths)}: {os.path.basename(image_source).split('?')[0]}")
            try:
                image_original = self._load_image(image_source)
                if image_original is None: continue

                analysis_results = self._classify_fashion_item(image_original)
                garment_scores = analysis_results['garment_scores']
                style_scores = analysis_results['style_scores']
                
                found_garments_with_scores = []
                for category, score in garment_scores:
                    if score > confidence_threshold:
                        all_garment_types.append(category)
                        found_garments_with_scores.append((category, score))
                    else: break
                
                if not found_garments_with_scores and garment_scores:
                    top_garment, top_score = garment_scores[0]
                    all_garment_types.append(top_garment)
                    found_garments_with_scores.append((top_garment, top_score))

                if style_scores:
                    all_style_types.append(style_scores[0][0])
                
                image_subject_only = self._isolate_subject(image_original)
                img_array = np.array(image_subject_only)
                
                if img_array.shape[2] == 4:
                    pixels_with_alpha = img_array.reshape(-1, 4)
                    pixels = pixels_with_alpha[pixels_with_alpha[:, 3] > 50][:, :3]
                else:
                    pixels = img_array.reshape(-1, 3)

                image_colors = []
                if len(pixels) > num_colors:
                    kmeans = KMeans(n_clusters=num_colors, n_init='auto', random_state=0).fit(pixels)
                    labels = kmeans.labels_
                    cluster_sizes = np.bincount(labels)
                    for i_color, color in enumerate(kmeans.cluster_centers_):
                        if i_color < len(cluster_sizes) and cluster_sizes[i_color] >= min_cluster_size:
                            r, g, b = color
                            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                            pantone_name, hex_color = self._find_best_pantone_match(color)
                            color_obj = {'rgb': color.tolist(), 'hex': hex_color, 'hue': h * 360, 'saturation': s * 100, 'value': v * 100, 'brightness': np.mean(color), 'color_complexity': np.std(color), 'proportion': cluster_sizes[i_color] / len(pixels), 'pantone_ref': pantone_name, 'color_name': pantone_name}
                            all_colors.append(color)
                            all_color_objects.append(color_obj)
                            image_colors.append(color_obj)
                
                self.image_analysis_results.append({'source': image_source, 'garment_analysis': analysis_results, 'colors': image_colors, 'found_garments_with_scores': found_garments_with_scores})
            
            except Exception as e:
                print(f"An unexpected error occurred while processing {image_source}: {e}")
                traceback.print_exc()

        if not all_garment_types:
            print("No data could be extracted.")
            return None, None
        
        color_analysis = self._analyze_fashion_color_distribution(all_color_objects, np.array(all_colors) if all_colors else np.array([]))
        garment_counts = Counter(all_garment_types)
        style_counts = Counter(all_style_types)
        garment_distribution = {g: {'count': c} for g, c in garment_counts.most_common()}
        style_distribution = {s: {'count': c} for s, c in style_counts.most_common()}
        
        color_garment_correlations = {}
        for result in self.image_analysis_results:
            for garment, score in result['found_garments_with_scores']:
                if garment not in color_garment_correlations:
                    color_garment_correlations[garment] = []
                color_garment_correlations[garment].extend(result['colors'])
        
        garment_color_trends = {}
        for garment, colors in color_garment_correlations.items():
            if not colors: continue
            color_bins = {}
            for color in colors:
                quantized_rgb = tuple(int(c / 25) * 25 for c in color.get('rgb', [0,0,0]))
                if quantized_rgb not in color_bins: color_bins[quantized_rgb] = []
                color_bins[quantized_rgb].append(color)
            binned_colors = []
            for bin_rgb, bin_colors in color_bins.items():
                if not bin_colors: continue
                avg_r, avg_g, avg_b = np.mean([c['rgb'] for c in bin_colors], axis=0)
                rep_color = bin_colors[0].copy()
                rep_color['rgb'] = np.array([avg_r, avg_g, avg_b])
                # NOUVEAU CODE
                pantone_name, hex_color = self._find_best_pantone_match(rep_color['rgb'])
                rep_color['hex'] = hex_color
                rep_color['pantone_ref'] = pantone_name
                rep_color['color_name'] = pantone_name
                rep_color['frequency'] = sum(c['proportion'] for c in bin_colors) * 100
                binned_colors.append(rep_color)
            garment_color_trends[garment] = sorted(binned_colors, key=lambda x: x['frequency'], reverse=True)

        all_detected_garments_with_scores = [item for res in self.image_analysis_results for item in res['found_garments_with_scores']]

        fashion_trends_dict = {
            'color_trends': color_analysis,
            'garment_trends': {'distribution': garment_distribution},
            'style_trends': {'distribution': style_distribution},
            'color_garment_trends': garment_color_trends,
            'detailed_image_analysis': self.image_analysis_results
        }
        
        return fashion_trends_dict, all_detected_garments_with_scores

    
    
    # Dans le fichier test_slglip2.py, à l'intérieur de la classe FashionTrendColorAnalyzer
    def _find_best_pantone_match(self, rgb_color):
            """Trouve la couleur Pantone la plus proche en utilisant la distance Delta E dans l'espace L*a*b*."""
            if not self.pantone_library:
                hex_fallback = f"#{int(rgb_color[0]):02x}{int(rgb_color[1]):02x}{int(rgb_color[2]):02x}"
                return "Custom", hex_fallback

            input_lab = rgb2lab(np.array(rgb_color).reshape(1, 1, 3).astype(np.uint8))
            library_labs = np.array([item['lab'] for item in self.pantone_library])
            distances = deltaE_cie76(input_lab, library_labs)
            closest_index = np.argmin(distances)
            best_match = self.pantone_library[closest_index]
            return best_match['name'], best_match['hex']
    

    def _analyze_fashion_color_distribution(self, color_objects, color_array):
        if not color_objects: return {}
        full_analysis = {'color_range_distribution': {}, 'color_metrics': {}, 'pantone_distribution': {}, 'dominant_colors': []}
        for start, end, name, hex_color, pantone_code in self.fashion_color_ranges:
            if start > end: in_range = [c for c in color_objects if c.get('hue') is not None and (c['hue'] >= start or c['hue'] < end)]
            else: in_range = [c for c in color_objects if c.get('hue') is not None and start <= c['hue'] < end]
            if not in_range: continue
            full_analysis['color_range_distribution'][name] = {'count': len(in_range), 'percentage': len(in_range) / len(color_objects) * 100, 'representative_colors': [c['hex'] for c in sorted(in_range, key=lambda x: x.get('saturation', 0) * x.get('value', 0), reverse=True)[:3]], 'pantone_ref': pantone_code, 'primary_color': hex_color}
        pantone_counts = Counter(c['pantone_ref'] for c in color_objects)
        for pantone, count in pantone_counts.most_common(10):
            if matching_colors := [c for c in color_objects if c['pantone_ref'] == pantone]: full_analysis['pantone_distribution'][pantone] = {'count': count, 'percentage': count / len(color_objects) * 100, 'representative_color': matching_colors[0]['hex']}
        if color_array.size > 0:
            n_dominant = min(10, len(np.unique(color_array, axis=0)))
            if n_dominant > 0:
                kmeans = KMeans(n_clusters=n_dominant, n_init='auto', random_state=0).fit(color_array)
                labels = kmeans.labels_
                label_counts = np.bincount(labels)
                percentages = (label_counts / len(labels)) * 100 if len(labels) > 0 else []
                dominant_colors_list = []
                for i_color, color in enumerate(kmeans.cluster_centers_):
                    if i_color < len(percentages):
                        # NOUVEAU CODE
                        pantone_name, hex_color = self._find_best_pantone_match(color)
                        dominant_colors_list.append({'rgb': [int(c) for c in color], 'hex': hex_color, 'pantone_ref': pantone_name, 'color_name': pantone_name, 'percentage': percentages[i_color]})
                full_analysis['dominant_colors'] = sorted(dominant_colors_list, key=lambda x: x['percentage'], reverse=True)
        unique_hex = set(c['hex'] for c in color_objects)
        full_analysis['color_metrics'] = {'total_unique_colors': len(unique_hex), 'average_saturation': np.mean([c.get('saturation', 0) for c in color_objects]) if color_objects else 0, 'average_brightness': np.mean([c.get('value', 0) for c in color_objects]) if color_objects else 0, 'color_diversity_index': len(unique_hex) / len(color_objects) if color_objects else 0}
        return full_analysis

    def visualize_fashion_trends(self, fashion_trends, weighted_garment_counts):
        if not fashion_trends: print("Insufficient data for visualization"); return
        color_trends, style_trends, color_garment_trends = fashion_trends.get('color_trends', {}), fashion_trends.get('style_trends', {}), fashion_trends.get('color_garment_trends', {})
        
        plt.figure(figsize=(15, 20))
        plt.subplot(3, 1, 1)
        plt.title('Dominant Color Palette', fontsize=16, fontweight='bold')
        dominant_colors = color_trends.get('dominant_colors', [])
        if dominant_colors:
            top_colors = dominant_colors[:10]
            for i, color_info in enumerate(top_colors):
                plt.gca().add_patch(plt.Rectangle((i, 0), 0.8, 1, color=color_info['hex']))
                plt.text(i + 0.4, -0.15, f"{color_info.get('percentage', 0):.1f}%", ha='center', va='top', fontsize=9, fontweight='bold')
                plt.text(i + 0.4, 0.5, color_info.get('pantone_ref', '').split(' ')[-1], ha='center', va='center', fontsize=8, color='white' if self._is_dark_color(color_info.get('hex','#000000')) else 'black')
            plt.xlim(0, len(top_colors)); plt.ylim(-0.5, 1.5)
        plt.axis('off')

        plt.subplot(3, 1, 2)
        plt.title('Top Garment Types (Weighted by Confidence)', fontsize=16, fontweight='bold')
        if weighted_garment_counts:
            total_score_weight = sum(weighted_garment_counts.values())
            top_items = weighted_garment_counts.most_common(10)
            garments = [item[0].capitalize() for item in top_items]
            percentages = [(item[1] / total_score_weight) * 100 for item in top_items] if total_score_weight > 0 else []
            bars = plt.barh(garments, percentages, color='skyblue'); plt.gca().invert_yaxis()
            for i, bar in enumerate(bars): plt.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f" {percentages[i]:.1f}%", va='center')
            plt.xlabel('Share of Total Confidence (%)')
            if percentages: plt.xlim(0, max(percentages) * 1.15 if percentages else 10)

        plt.subplot(3, 1, 3)
        plt.title('Fashion Style Trends', fontsize=16, fontweight='bold')
        distribution = style_trends.get('distribution', {})
        if distribution:
            total_styles = sum(v['count'] for v in distribution.values())
            top_items = sorted(list(distribution.items()), key=lambda x: x[1]['count'], reverse=True)[:8]
            styles = [item[0].capitalize() for item in top_items]
            percentages = [(item[1]['count'] / total_styles) * 100 for item in top_items] if total_styles > 0 else []
            plt.pie(percentages, labels=styles, autopct='%1.1f%%', colors=plt.cm.Pastel1.colors, textprops={'fontsize': 10})
            plt.axis('equal')
        
        plt.tight_layout(pad=3.0)
        plt.savefig('fashion_trends_overview.png', dpi=300, bbox_inches='tight')
        plt.close()

        plt.figure(figsize=(15, 10))
        plt.suptitle('TOP COLORS BY GARMENT TYPE', fontsize=20, fontweight='bold')
        if color_garment_trends:
            garment_distribution = fashion_trends.get('garment_trends', {}).get('distribution', {})
            top_garments = sorted(garment_distribution.keys(), key=lambda g: garment_distribution.get(g, {}).get('count', 0), reverse=True)[:6]
            for i, garment in enumerate(top_garments):
                ax = plt.subplot(2, 3, i + 1)
                ax.set_title(garment.capitalize(), fontsize=12, fontweight='bold')
                colors = color_garment_trends.get(garment)
                if not colors: 
                    ax.text(0.5, 0.5, "No color data", ha='center', va='center')
                    ax.axis('off')
                    continue
                for j, color_info in enumerate(colors[:3]):
                    ax.add_patch(plt.Rectangle((0, j), 2, 0.8, color=color_info['hex']))
                    ax.text(2.2, j + 0.4, f"{color_info.get('frequency', 0):.1f}% - {color_info.get('pantone_ref', 'N/A')}", va='center', fontsize=9)
                ax.set_xlim(0, 6)
                ax.set_ylim(-0.2, 3)
                ax.axis('off')
        
        plt.tight_layout(pad=3.0)
        plt.savefig('colors_by_garment.png', dpi=300, bbox_inches='tight')
        plt.close()

        print("Graphiques sauvegardés en fichiers PNG.")

    def _is_dark_color(self, hex_color):
        hex_color = hex_color.lstrip('#'); r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return (r * 0.299 + g * 0.587 + b * 0.114) < 140

    def export_pantone_style_report(self, fashion_trends, weighted_garment_counts, output_path='fashion_trend_report.pdf'):
        from matplotlib.backends.backend_pdf import PdfPages
        if not fashion_trends: print("No data to export."); return
        with PdfPages(output_path) as pdf:
            plt.figure(figsize=(8.5, 11))
            plt.text(0.5, 0.55, 'FASHION TREND ANALYSIS REPORT', ha='center', va='center', fontsize=24, fontweight='bold')
            plt.text(0.5, 0.45, f"Generated: {pd.Timestamp.now().strftime('%B %d, %Y')}", ha='center', va='center', fontsize=12)
            plt.axis('off')
            pdf.savefig()
            plt.close()

            fig = plt.figure(figsize=(8.5, 11))
            fig.text(0.5, 0.95, 'Trend Overview', ha='center', va='center', fontsize=18, fontweight='bold')
            
            ax1 = fig.add_axes([0.1, 0.65, 0.8, 0.25])
            ax1.set_title('Macro-Trend Distribution', fontsize=14)
            item_to_macro = {item: macro for macro, items in TREND_MAP.items() for item in items}
            total_score_weight = sum(weighted_garment_counts.values())
            macro_trends = Counter()
            if total_score_weight > 0:
                for garment, score_sum in weighted_garment_counts.items():
                    macro_category = item_to_macro.get(garment)
                    if macro_category: macro_trends[macro_category] += score_sum
                macro_names = list(macro_trends.keys())
                macro_counts = list(macro_trends.values())
                ax1.pie(macro_counts, labels=macro_names, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
                ax1.axis('equal')

            ax2 = fig.add_axes([0.1, 0.1, 0.8, 0.45])
            ax2.set_title('Top 10 Micro-Trends (Weighted by Confidence)', fontsize=14)
            if weighted_garment_counts:
                top_items = weighted_garment_counts.most_common(10)
                garments = [item[0].capitalize() for item in top_items]
                percentages = [(item[1] / total_score_weight) * 100 for item in top_items] if total_score_weight > 0 else []
                bars = ax2.barh(garments, percentages, color='c')
                ax2.invert_yaxis()
                ax2.set_xlabel('Share of Total Confidence (%)')
                for bar in bars: ax2.text(bar.get_width(), bar.get_y() + bar.get_height()/2, f' {bar.get_width():.1f}%', va='center')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            
            pdf.savefig()
            plt.close()
        print(f"Rapport PDF exporté vers {output_path}")

    # À l'intérieur de la classe FashionTrendColorAnalyzer, remplacez la fonction par celle-ci

    def _transform_results_for_db(self, fashion_trends_dict):
        """
        Prend le dictionnaire d'analyse détaillé et le transforme
        pour correspondre exactement au schéma de la base de données MongoDB.
        """
        print("Transformation des résultats pour le format de la base de données...")
        db_doc = {}

        # 1. Transformer color_trends
        raw_color_trends = fashion_trends_dict.get('color_trends', {})
        db_doc['color_trends'] = {
            'dominant_colors': [
                {
                    "rgb": color.get("rgb"),
                    "hex": color.get("hex"),
                    "pantone_ref": color.get("pantone_ref"), # LIGNE CORRIGÉE
                    "proportion": color.get("percentage", 0) / 100.0,
                    "percentage": color.get("percentage"),
                    "color_name": color.get("color_name")
                } for color in raw_color_trends.get('dominant_colors', [])
            ]
        }

        # 2. Transformer garment_trends
        raw_garment_trends = fashion_trends_dict.get('garment_trends', {}).get('distribution', {})
        total_garment_count = sum(v.get('count', 0) for v in raw_garment_trends.values())
        db_garment_dist = {}
        for garment, data in raw_garment_trends.items():
            count = data.get('count', 0)
            percentage = (count / total_garment_count * 100) if total_garment_count > 0 else 0
            db_garment_dist[garment] = {'count': count, 'percentage': percentage}
        
        db_doc['garment_trends'] = {
            'distribution': db_garment_dist,
            'top_garments': [g for g, d in sorted(raw_garment_trends.items(), key=lambda item: item[1].get('count', 0), reverse=True)]
        }

        # 3. Transformer style_trends
        raw_style_trends = fashion_trends_dict.get('style_trends', {}).get('distribution', {})
        total_style_count = sum(v.get('count', 0) for v in raw_style_trends.values())
        db_style_dist = {}
        for style, data in raw_style_trends.items():
            count = data.get('count', 0)
            percentage = (count / total_style_count * 100) if total_style_count > 0 else 0
            db_style_dist[style] = {'count': count, 'percentage': percentage}

        db_doc['style_trends'] = {
            'distribution': db_style_dist,
            'top_styles': [s for s, d in sorted(raw_style_trends.items(), key=lambda item: item[1].get('count', 0), reverse=True)]
        }

        # 4. Transformer color_garment_trends
        raw_color_garment = fashion_trends_dict.get('color_garment_trends', {})
        db_color_garment = {}
        for garment, colors in raw_color_garment.items():
            db_color_garment[garment] = [
                {
                    "rgb": [int(c) for c in color.get("rgb", [])],
                    "hex": color.get("hex"),
                    "frequency": color.get("frequency"),
                    "color_name": color.get("color_name")
                } for color in colors
            ]
        db_doc['color_garment_trends'] = db_color_garment

        # 5. Transformer detailed_image_analysis
        raw_detailed_analysis = fashion_trends_dict.get('detailed_image_analysis', [])
        db_detailed_analysis = []
        for item in raw_detailed_analysis:
            garment_scores = item.get('garment_analysis', {}).get('garment_scores', [])
            style_scores = item.get('garment_analysis', {}).get('style_scores', [])
            
            db_item = {
                "source": item.get("source"),
                "garment_analysis": {
                    "primary_category": garment_scores[0][0] if garment_scores else None,
                    "confidence_category": garment_scores[0][1] if garment_scores else None,
                    "primary_style": style_scores[0][0] if style_scores else None
                },
                "colors": [
                    {
                        "rgb": [int(c) for c in color.get("rgb", [])],
                        "hex": color.get("hex"),
                        "color_name": color.get("color_name"),
                        "pantone_ref": color.get("pantone_ref") # LIGNE CORRIGÉE
                    } for color in item.get('colors', [])
                ]
            }
            db_detailed_analysis.append(db_item)
        db_doc['detailed_image_analysis'] = db_detailed_analysis

        return db_doc
    
    def export_to_json(self, data_to_export, output_path='fashion_trends_report.json'):
        try:
            final_json_data = {
                "source_file": self.image_source,
                "analyzed_at": datetime.datetime.now(),
                **data_to_export
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_json_data, f, cls=NumpyJSONEncoder, ensure_ascii=False, indent=4)
            print(f"Rapport JSON (format BDD) exporté vers {output_path}")
        except Exception as e:
            print(f"Erreur lors de l'export JSON : {e}")
            traceback.print_exc()


def post_results_to_api(json_report_path, api_url):
    """Poste le fichier JSON du rapport à l'API backend."""
    try:
        with open(json_report_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"--- Envoi du rapport à l'API : {api_url} ---")
        response = requests.post(api_url, json=data)
        response.raise_for_status()
        print(f"--- Rapport posté avec succès à l'API. Réponse : {response.status_code} ---")
        return response.json()
    except FileNotFoundError:
        print(f"ERREUR API: Fichier rapport non trouvé à {json_report_path}")
    except requests.exceptions.RequestException as e:
        print(f"ERREUR API: Échec de l'envoi du rapport à l'API : {e}")
    return None


# NOUVELLE VERSION CORRIGÉE de main()

def main():
    """
    Fonction principale pour exécuter l'analyse depuis la ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Analyseur de tendances de mode.")
    parser.add_argument("source", help="Chemin S3 ou JSON local à analyser.")
    parser.add_argument("--threshold", type=float, default=0.10, help="Seuil de confiance.")
    # CORRECTION : Utilisation cohérente du nom d'argument
    parser.add_argument("--api_endpoint", default="http://backend:3000/api/trends", help="Endpoint API.")
    args = parser.parse_args()

    image_source = args.source
    threshold = args.threshold
    # CORRECTION : Utilisation du bon nom d'attribut
    api_url = args.api_endpoint

    print(f"Lancement de l'analyse pour la source : {image_source}")

    # CORRECTION : On ne vérifie l'existence que si ce n'est pas un chemin S3
    if not image_source.startswith('s3://') and not os.path.exists(image_source):
        print(f"ERREUR : Le chemin local '{image_source}' est introuvable.")
        return

    try:
        analyzer = FashionTrendColorAnalyzer(image_source)
        fashion_trends_raw, all_detected_garments_with_scores = analyzer.analyze_fashion_trends(confidence_threshold=threshold)
        
        if fashion_trends_raw:
            print("\n--- Lancement de la Transformation et des Exports Locaux ---")
            fashion_trends_for_db = analyzer._transform_results_for_db(fashion_trends_raw)
            json_output_path = 'fashion_trends_report.json'
            analyzer.export_to_json(fashion_trends_for_db, json_output_path)
            # Les exports PDF et graphiques sont optionnels, vous pouvez les commenter si non désirés
            weighted_garment_counts = Counter(g for g, s in all_detected_garments_with_scores)
            analyzer.export_pantone_style_report(fashion_trends_raw, weighted_garment_counts, 'fashion_trend_report.pdf')
            analyzer.visualize_fashion_trends(fashion_trends_raw, weighted_garment_counts)
            if api_url:
                post_results_to_api(json_output_path, api_url)
            print("\n--- Analyse et exportation terminées avec succès ! ---")
        else:
            print("\n--- Aucune donnée n'a pu être analysée. Aucun rapport n'a été généré. ---")

    except Exception as e:
        print(f"Une erreur inattendue est survenue : {e}")
        traceback.print_exc()

if __name__ == '__main__':
    main()