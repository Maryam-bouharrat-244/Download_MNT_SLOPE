#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour fusionner les tuiles raster du MNT (Modèle Numérique de Terrain)
et produire un raster final (mosaïquage)
"""

import os
import glob
import subprocess
import sys
from pathlib import Path

def merge_mnt_tiles():
    """
    Fusionne tous les tuiles raster ASC du répertoire d'entrée
    et sauvegarde le résultat final en format GeoTIFF
    """
    
    # Répertoire source (tuiles à fusionner)
    source_dir = r"C:\Users\marya\Desktop\MNT FRANCE\mnt_downloader\work\extracted\D1\RGEALTI_2-0_5M_ASC_LAMB93-IGN69_D001_2023-08-08\RGEALTI\1_DONNEES_LIVRAISON_2023-10-00126\RGEALTI_MNT_5M_ASC_LAMB93_IGN69_D001"
    
    # Répertoire de sortie (téléchargement)
    output_dir = r"C:\Users\marya\Downloads"
    output_file = os.path.join(output_dir, "MNT_FRANCE_merged.tif")
    
    # Fichier texte listant tous les fichiers d'entrée (pour gdal_merge)
    file_list = os.path.join(output_dir, "mnt_tiles_list.txt")
    
    print("=" * 70)
    print("FUSION DES TUILES RASTER DU MNT")
    print("=" * 70)
    
    # Vérer que le répertoire source existe
    if not os.path.isdir(source_dir):
        print(f"❌ Erreur: Le répertoire source n'existe pas: {source_dir}")
        sys.exit(1)
    
    # Chercher tous les fichiers ASC
    asc_files = sorted(glob.glob(os.path.join(source_dir, "*.asc")))
    
    if not asc_files:
        print(f"❌ Erreur: Aucun fichier .asc trouvé dans {source_dir}")
        sys.exit(1)
    
    print(f"\n📁 Répertoire source: {source_dir}")
    print(f"📊 Nombre de tuiles trouvées: {len(asc_files)}")
    print(f"📍 Fichiers:")
    for i, file in enumerate(asc_files[:5], 1):
        print(f"   {i}. {os.path.basename(file)}")
    if len(asc_files) > 5:
        print(f"   ... et {len(asc_files) - 5} autres fichiers")
    
    # Créer le fichier liste pour gdal_merge
    print(f"\n📝 Création du fichier liste...")
    with open(file_list, 'w') as f:
        for asc_file in asc_files:
            f.write(asc_file + '\n')
    
    print(f"✅ Fichier liste créé: {file_list}")
    
    # Utiliser gdal_merge pour fusionner les fichiers
    print(f"\n🔄 Fusion des tuiles en cours...")
    print(f"💾 Fichier de sortie: {output_file}")
    
    # Préparer la commande gdal_merge
    cmd = [
        'gdal_merge.py',
        '-o', output_file,
        '-of', 'GTiff',  # Format GeoTIFF
        '-co', 'COMPRESS=LZW',  # Compression
        '-co', 'TILED=YES',      # Tuilage interne
    ] + asc_files
    
    try:
        # Essayer d'abord avec gdal_merge.py
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("✅ Fusion réussie avec gdal_merge.py")
        else:
            print("⚠️ Tentative avec rasterio...")
            merge_with_rasterio(asc_files, output_file)
            
    except FileNotFoundError:
        print("⚠️ gdal_merge.py non trouvé, utilisation de rasterio...")
        merge_with_rasterio(asc_files, output_file)
    except Exception as e:
        print(f"❌ Erreur lors de la fusion avec gdal_merge: {e}")
        print("⚠️ Tentative avec rasterio...")
        merge_with_rasterio(asc_files, output_file)
    
    # Vérifier le résultat
    if os.path.isfile(output_file):
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print("\n" + "=" * 70)
        print("✅ SUCCÈS - Fusion terminée!")
        print("=" * 70)
        print(f"📂 Fichier final: {output_file}")
        print(f"📊 Taille du fichier: {file_size_mb:.2f} MB")
        print(f"✨ Les tuiles MNT ont été fusionnées avec succès!")
    else:
        print("\n❌ Erreur: Le fichier de sortie n'a pas été créé.")
        sys.exit(1)


def merge_with_rasterio(asc_files, output_file):
    """
    Alternative: Fusion avec rasterio si GDAL n'est pas disponible
    """
    try:
        import numpy as np
        import rasterio
        from rasterio.transform import from_bounds
        from rasterio.crs import CRS
        
        print("Fusion avec rasterio en cours...")
        
        # Lire tous les fichiers et déterminer les limites
        datasets = []
        bounds_list = []
        
        for asc_file in asc_files:
            with rasterio.open(asc_file) as src:
                datasets.append(src.read(1))  # Lire la première bande
                bounds_list.append(src.bounds)
                crs = src.crs
                transform = src.transform
                dtype = src.dtypes[0]
        
        # Calculer les limites globales
        min_left = min(b.left for b in bounds_list)
        max_right = max(b.right for b in bounds_list)
        min_bottom = min(b.bottom for b in bounds_list)
        max_top = max(b.top for b in bounds_list)
        
        # Créer l'array fusionné (mosaïque)
        pixel_size = transform.a  # Taille des pixels
        height = int((max_top - min_bottom) / abs(transform.e))
        width = int((max_right - min_left) / pixel_size)
        
        merged_array = np.full((height, width), -9999, dtype=dtype)
        
        # Remplir la mosaïque
        for i, asc_file in enumerate(asc_files):
            with rasterio.open(asc_file) as src:
                data = src.read(1)
                # Calculer les positions dans le tableau fusionné
                col_offset = int((src.bounds.left - min_left) / pixel_size)
                row_offset = int((max_top - src.bounds.top) / abs(transform.e))
                
                rows, cols = data.shape
                merged_array[row_offset:row_offset+rows, col_offset:col_offset+cols] = data
        
        # Créer le fichier de sortie
        new_transform = from_bounds(min_left, min_bottom, max_right, max_top, 
                                     merged_array.shape[1], merged_array.shape[0])
        
        with rasterio.open(
            output_file, 'w',
            driver='GTiff',
            dtype=dtype,
            nodata=-9999,
            width=merged_array.shape[1],
            height=merged_array.shape[0],
            count=1,
            crs=crs,
            transform=new_transform,
            compress='lzw'
        ) as dst:
            dst.write(merged_array, 1)
        
        print("✅ Fusion réussie avec rasterio")
        
    except ImportError:
        print("❌ Les bibliothèques rasterio/numpy ne sont pas installées.")
        print("Installation requise: pip install rasterio numpy")
        sys.exit(1)


if __name__ == "__main__":
    try:
        merge_mnt_tiles()
    except KeyboardInterrupt:
        print("\n⚠️ Opération annulée par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
