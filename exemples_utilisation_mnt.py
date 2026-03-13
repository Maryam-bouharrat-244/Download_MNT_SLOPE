#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exemples d'utilisation du MNT fusionné
Montre comment lire et analyser le Modèle Numérique de Terrain
"""

import os
import sys
from pathlib import Path

def example_1_read_vrt():
    """Exemple 1: Lire le fichier VRT et afficher les statistiques basiques"""
    
    print("\n" + "="*70)
    print("EXEMPLE 1: Lire le VRT et afficher les statistiques")
    print("="*70)
    
    vrt_file = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.vrt"
    
    if not os.path.isfile(vrt_file):
        print(f"❌ Fichier VRT non trouvé: {vrt_file}")
        print("\nCréez d'abord le VRT avec: python create_mnt_vrt.py")
        return
    
    try:
        import rasterio
        import numpy as np
    except ImportError:
        print("❌ rasterio n'est pas installé")
        print("Installation: pip install rasterio")
        return
    
    print(f"\n📂 Fichier: {vrt_file}")
    print(f"📦 Taille: {os.path.getsize(vrt_file) / 1024:.2f} KB")
    
    try:
        with rasterio.open(vrt_file) as src:
            print(f"\n📊 Métadonnées:")
            print(f"  • Largeur: {src.width:,} pixels")
            print(f"  • Hauteur: {src.height:,} pixels")
            print(f"  • Résolution: {src.transform.a:.2f} m/pixel")
            print(f"  • Projection: {src.crs}")
            print(f"  • Nombre de bandes: {src.count}")
            print(f"  • Type de donnée: {src.dtypes[0]}")
            
            # Lire un petit exemple
            print(f"\n🔍 Lecture d'un échantillon (10% des données)...")
            
            # Lire les données (peut être très grand, donc on peut lire par fenêtres)
            # Ici on lit juste une petite portion pour test
            from rasterio.windows import Window
            
            # Lire une petite fenêtre pour démonstration
            window = Window(0, 0, min(1000, src.width), min(1000, src.height))
            sample_data = src.read(1, window=window)
            
            print(f"\n✨ Statistiques de l'échantillon:")
            print(f"  • Altitude minimum: {sample_data.min():.2f} m")
            print(f"  • Altitude maximum: {sample_data.max():.2f} m")
            print(f"  • Altitude moyenne: {sample_data.mean():.2f} m")
            print(f"  • Écart-type: {sample_data.std():.2f} m")
            
            # Histogramme simple
            print(f"\n📈 Distribution des altitudes (histogramme):")
            bins = np.histogram(sample_data[sample_data > -9999], bins=10)
            for i, (count, edge) in enumerate(zip(bins[0], bins[1])):
                bar = "█" * int(count / sample_data.size * 50)
                print(f"  {edge:6.0f}m: {bar}")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


def example_2_calculate_slope():
    """Exemple 2: Calculer la pente à partir du MNT"""
    
    print("\n" + "="*70)
    print("EXEMPLE 2: Calculer la pente du terrain")
    print("="*70)
    
    vrt_file = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.vrt"
    
    try:
        import rasterio
        import numpy as np
        from rasterio.windows import Window
    except ImportError:
        print("❌ Dépendances manquantes")
        return
    
    print("\n🔍 Calcul de la pente (gradient)...")
    
    try:
        with rasterio.open(vrt_file) as src:
            # Lire une petite zone pour la démonstration
            window = Window(500, 500, 100, 100)
            dem = src.read(1, window=window).astype(float)
            
            # Calculer les gradients
            cell_size = src.transform.a  # 5m
            
            # Gradient X et Y
            gy, gx = np.gradient(dem, cell_size)
            
            # Pente en degrés
            slope_deg = np.arctan(np.sqrt(gx**2 + gy**2)) * 180 / np.pi
            
            print(f"\n✨ Statistiques de pente (zone d'exemple):")
            print(f"  • Pente minimale: {slope_deg.min():.2f}°")
            print(f"  • Pente maximale: {slope_deg.max():.2f}°")
            print(f"  • Pente moyenne: {slope_deg.mean():.2f}°")
            
            # Classer les pentes
            flat = np.sum(slope_deg < 2) / slope_deg.size * 100
            moderate = np.sum((slope_deg >= 2) & (slope_deg < 10)) / slope_deg.size * 100
            steep = np.sum((slope_deg >= 10) & (slope_deg < 30)) / slope_deg.size * 100
            verysteep = np.sum(slope_deg >= 30) / slope_deg.size * 100
            
            print(f"\n📊 Classification:")
            print(f"  • Plat (<2°): {flat:.1f}%")
            print(f"  • Modéré (2-10°): {moderate:.1f}%")
            print(f"  • Escarpé (10-30°): {steep:.1f}%")
            print(f"  • Très escarpé (>30°): {verysteep:.1f}%")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")


def example_3_extract_region():
    """Exemple 3: Extraire une région spécifique"""
    
    print("\n" + "="*70)
    print("EXEMPLE 3: Extraire une zone d'intérêt")
    print("="*70)
    
    vrt_file = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.vrt"
    
    try:
        import rasterio
        from rasterio.mask import mask
        from shapely.geometry import box
    except ImportError:
        print("❌ Dépendances manquantes (rasterio, shapely)")
        return
    
    print("\n🔍 Extraction d'une région par coordonnées...")
    
    try:
        with rasterio.open(vrt_file) as src:
            # Définir une zone (Lambert93-IGN69)
            # Exemple: Région parisienne (approximatif)
            roi = box(600000, 6210000, 700000, 6310000)  # xmin, ymin, xmax, ymax
            
            print(f"\nRégion sélectionnée:")
            print(f"  • X: 600000 - 700000 m")
            print(f"  • Y: 6210000 - 6310000 m")
            print(f"  • Taille: ~100 km x ~100 km")
            
            # Extraire
            out_image, out_transform = mask(src, [roi], crop=True)
            
            print(f"\n✨ Données extraites:")
            print(f"  • Largeur: {out_image.shape[2]} pixels")
            print(f"  • Hauteur: {out_image.shape[1]} pixels")
            print(f"  • Altitude min: {out_image.min():.2f} m")
            print(f"  • Altitude max: {out_image.max():.2f} m")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")


def example_4_save_subset():
    """Exemple 4: Sauvegarder une région en GeoTIFF"""
    
    print("\n" + "="*70)
    print("EXEMPLE 4: Sauvegarder une région en GeoTIFF")
    print("="*70)
    
    vrt_file = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.vrt"
    output_file = r"C:\Users\marya\Downloads\MNT_region_example.tif"
    
    try:
        import rasterio
        from rasterio.windows import Window
    except ImportError:
        print("❌ Dépendances manquantes")
        return
    
    print("\n📝 Sauvegarde d'une région en GeoTIFF...")
    
    try:
        with rasterio.open(vrt_file) as src:
            # Extraire une région
            window = Window(1000, 1000, 100, 100)
            data = src.read(1, window=window)
            
            # Créer le fichier de sortie
            profile = src.profile.copy()
            profile.update({
                'height': data.shape[0],
                'width': data.shape[1],
                'transform': src.window_transform(window),
                'compress': 'lzw'
            })
            
            with rasterio.open(output_file, 'w', **profile) as dst:
                dst.write(data, 1)
            
            file_size_kb = os.path.getsize(output_file) / 1024
            print(f"✅ Fichier sauvegardé: {output_file}")
            print(f"   Taille: {file_size_kb:.2f} KB")
    
    except Exception as e:
        print(f"❌ Erreur: {e}")


def main():
    """Menu principal"""
    
    print("\n" + "="*70)
    print("  EXEMPLES D'UTILISATION DU MNT FUSIONNÉ")
    print("="*70)
    print("\nCes exemples montrent comment utiliser le MNT avec Python et rasterio")
    
    print("\n\nSélectionnez un exemple:")
    print("  1) Lire le VRT et afficher les statistiques")
    print("  2) Calculer la pente du terrain")
    print("  3) Extraire une région spécifique")
    print("  4) Sauvegarder une région en GeoTIFF")
    print("  0) Quitter")
    
    choice = input("\nChoix [0-4]: ").strip()
    
    if choice == "1":
        example_1_read_vrt()
    elif choice == "2":
        example_2_calculate_slope()
    elif choice == "3":
        example_3_extract_region()
    elif choice == "4":
        example_4_save_subset()
    elif choice == "0":
        print("\nAu revoir!")
        sys.exit(0)
    else:
        print("❌ Choix invalide")
    
    print("\n")
    input("Appuyez sur Entrée pour quitter...")


if __name__ == "__main__":
    main()
