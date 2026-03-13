#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour créer un VRT (Virtual Raster Dataset) à partir des tuiles MNT
Le VRT agit comme une "vue fusionnée" des tuiles sans consommer beaucoup d'espace disque
"""

import os
import glob
import sys
import subprocess
from pathlib import Path

def parse_asc_header(filepath):
    """Parse l'en-tête d'un fichier ESRI ASCII Grid"""
    params = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i in range(7):  # Lire 7 lignes pour inclure NODATA_value
                line = f.readline().strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    key, value = parts[0].lower(), parts[1]
                    if key in ['ncols', 'nrows']:
                        params[key] = int(value)
                    elif key in ['cellsize', 'xllcorner', 'yllcorner']:
                        params[key] = float(value)
                    elif key == 'nodata_value':
                        params[key] = float(value)
    except Exception as e:
        print(f"⚠️ Erreur lecture header {filepath}: {e}")
    return params


def create_mnt_vrt():
    """
    Crée un VRT (Virtual Raster Dataset) à partir des tuiles ASC avec positionnement correct
    """
    
    # Répertoire source (tuiles à fusionner)
    source_dir = r"C:\Users\marya\Downloads\RGEALTI_2-0_5M_ASC_LAMB93-IGN69_D087_2021-10-26\RGEALTI_2-0_5M_ASC_LAMB93-IGN69_D087_2021-10-26\RGEALTI\1_DONNEES_LIVRAISON_2021-11-00179\RGEALTI_MNT_5M_ASC_LAMB93_IGN69_D087"
    
    # Répertoire de sortie (téléchargement)
    output_dir = r"C:\Users\marya\Downloads"
    vrt_file = os.path.join(output_dir, "MNT_D023.vrt")
    output_tif = os.path.join(output_dir, "MNT_D023.tif")
    
    print("=" * 80)
    print("FUSION DES TUILES RASTER DU MNT - Création d'une Mosaïque VRT")
    print("=" * 80)
    
    # Vérifier que le répertoire source existe
    if not os.path.isdir(source_dir):
        print(f"❌ Erreur: Le répertoire source n'existe pas")
        print(f"   {source_dir}")
        sys.exit(1)
    
    # Chercher tous les fichiers ASC
    asc_files = sorted(glob.glob(os.path.join(source_dir, "*.asc")))
    
    if not asc_files:
        print(f"❌ Erreur: Aucun fichier .asc trouvé dans {source_dir}")
        sys.exit(1)
    
    print(f"\n📁 Répertoire source:")
    print(f"   {source_dir}")
    print(f"\n📊 Nombre de tuiles trouvées: {len(asc_files)}")
    
    print(f"\n📍 Fichiers (affichage des 10 premiers):")
    for i, file in enumerate(asc_files[:10], 1):
        print(f"   {i:3d}. {os.path.basename(file)}")
    if len(asc_files) > 10:
        print(f"   ... et {len(asc_files) - 10} autres fichiers")
    
    # Créer le VRT
    print(f"\n📝 Lecture des paramètres des tuiles...")
    
    # Lire les paramètres de chaque tuile
    tile_data = []
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for asc_file in asc_files:
        params = parse_asc_header(asc_file)
        if all(k in params for k in ['ncols', 'nrows', 'cellsize', 'xllcorner', 'yllcorner']):
            tile_data.append((asc_file, params))
            # Calculer les extents
            x_ll = params['xllcorner']
            y_ll = params['yllcorner']
            x_ur = x_ll + params['ncols'] * params['cellsize']
            y_ur = y_ll + params['nrows'] * params['cellsize']
            
            min_x = min(min_x, x_ll)
            min_y = min(min_y, y_ll)
            max_x = max(max_x, x_ur)
            max_y = max(max_y, y_ur)
    
    if not tile_data:
        print(f"❌ Erreur: Impossible de lire les en-têtes des fichiers ASC")
        sys.exit(1)
    
    print(f"✅ {len(tile_data)} tuiles avec en-têtes valides trouvées")
    
    # Paramètres raster (supposer qu'ils sont identiques pour toutes les tuiles)
    sample_params = tile_data[0][1]
    ncols = sample_params.get('ncols', 5000)
    nrows = sample_params.get('nrows', 5000)
    cellsize = sample_params.get('cellsize', 5.0)
    nodata_value = sample_params.get('nodata_value', -9999)  # Lire la vraie valeur NODATA
    
    print(f"\n📐 Paramètres raster (type de tuile):")
    print(f"   Colonnes: {ncols}")
    print(f"   Lignes: {nrows}")
    print(f"   Taille cellule: {cellsize} m")
    print(f"\n📍 Extent de la mosaïque:")
    print(f"   X: {min_x:.0f} à {max_x:.0f} ({max_x - min_x:.0f} m)")
    print(f"   Y: {min_y:.0f} à {max_y:.0f} ({max_y - min_y:.0f} m)")
    
    # Calculer les dimensions totales du raster
    total_width = int((max_x - min_x) / cellsize)
    total_height = int((max_y - min_y) / cellsize)
    
    print(f"   Résolution totale: {total_width} x {total_height} pixels")
    
    # Créer le header du VRT avec projection Lambert93 correcte
    vrt_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<VRTDataset rasterXSize="{total_width}" rasterYSize="{total_height}">
  <SRS dataAxisToSrsAxisMapping="2,1">PROJCS["Lambert93",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],PARAMETER["false_northing",6600000],UNIT["Meter",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","2154"]]</SRS>
  <GeoTransform>{min_x}, {cellsize}, 0, {max_y}, 0, -{cellsize}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>{nodata_value}</NoDataValue>
'''
    
    # Ajouter chaque tuile
    print(f"\n📋 Ajout des tuiles au VRT...")
    for asc_file, params in tile_data:
        x_ll = params['xllcorner']
        y_ll = params['yllcorner']
        cs = params['cellsize']
        cols = params['ncols']
        rows = params['nrows']
        
        # Calculer les coordonnées de destination dans la mosaïque
        dst_x = int((x_ll - min_x) / cs)
        dst_y = int((max_y - (y_ll + rows * cs)) / cs)
        
        vrt_content += f'''    <SimpleSource>
      <SourceFilename relativeToVRT="0">{asc_file}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="{cols}" RasterYSize="{rows}" DataType="Float32" />
      <SrcRect xOff="0" yOff="0" xSize="{cols}" ySize="{rows}" />
      <DstRect xOff="{dst_x}" yOff="{dst_y}" xSize="{cols}" ySize="{rows}" />
      <NODATA>-9999</NODATA>
    </SimpleSource>
'''
    
    vrt_content += '''  </VRTRasterBand>
</VRTDataset>
'''
    
    # Écrire le fichier VRT
    print(f"\n💾 Écriture du fichier VRT...")
    try:
        with open(vrt_file, 'w', encoding='utf-8') as f:
            f.write(vrt_content)
        file_size_kb = os.path.getsize(vrt_file) / 1024
        print(f"✅ Fichier VRT créé: {vrt_file}")
        print(f"   Taille: {file_size_kb:.1f} KB")
    except Exception as e:
        print(f"❌ Erreur lors de l'écriture du VRT: {e}")
        sys.exit(1)
    
    # Essayer de trouver GDAL depuis QGIS (Windows)
    print(f"\n🔍 Recherche de GDAL...")
    gdal_bin = None
    
    # Emplacements possibles de QGIS/GDAL sur Windows
    possible_paths = [
        r"C:\Program Files\QGIS 3.36\bin\gdalwarp.exe",
        r"C:\Program Files\QGIS 3.32\bin\gdalwarp.exe",
        r"C:\Program Files (x86)\QGIS 3.36\bin\gdalwarp.exe",
        r"C:\Program Files (x86)\QGIS 3.32\bin\gdalwarp.exe",
        r"C:\OSGeo4W\bin\gdalwarp.exe",
    ]
    
    for path in possible_paths:
        if os.path.isfile(path):
            gdal_bin = path
            break
    
    # Sinon, chercher dans PATH
    if not gdal_bin:
        try:
            result = subprocess.run(['where', 'gdalwarp'], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gdal_bin = result.stdout.strip().split('\n')[0]
        except:
            pass
    
    if gdal_bin and os.path.isfile(gdal_bin):
        gdal_dir = os.path.dirname(gdal_bin)
        print(f"✅ GDAL trouvé: {gdal_dir}")
        
        try:
            print(f"\n💾 Conversion du VRT en GeoTIFF...")
            print(f"   Fichier de sortie: {output_tif}")
            print(f"   ⏳ Cela peut prendre plusieurs minutes selon la taille...")
            
            result = subprocess.run(
                [gdal_bin, '-of', 'GTiff', 
                 '-co', 'COMPRESS=LZW',
                 '-co', 'TILED=YES',
                 '-co', 'BLOCKXSIZE=512',
                 '-co', 'BLOCKYSIZE=512',
                 vrt_file, output_tif],
                capture_output=True, text=True, timeout=3600
            )
            
            if result.returncode == 0 and os.path.isfile(output_tif):
                file_size_mb = os.path.getsize(output_tif) / (1024 * 1024)
                print(f"✅ GeoTIFF créé avec succès!")
                print(f"   Taille: {file_size_mb:.2f} MB")
            else:
                print(f"⚠️ La conversion GDAL a échoué")
                if result.stderr:
                    print(f"   Erreur: {result.stderr[:200]}")
                print(f"   👉 Vous pouvez ouvrir le VRT directement dans QGIS")
                
        except subprocess.TimeoutExpired:
            print(f"⚠️ La conversion GDAL a dépassé le délai (timeout)")
            print(f"   👉 Vous pouvez ouvrir le VRT directement dans QGIS")
        except Exception as e:
            print(f"⚠️ Erreur lors de la conversion: {e}")
            print(f"   👉 Vous pouvez ouvrir le VRT directement dans QGIS")
    else:
        print(f"⚠️ GDAL non trouvé")
        print(f"   👉 Vous pouvez ouvrir le VRT directement dans QGIS sans conversion")
    
    # Résumé final
    print("\n" + "=" * 80)
    print("✅ SUCCÈS - Fichiers de mosaïquage créés!")
    print("=" * 80)
    
    print(f"\n📂 Fichiers créés dans: {output_dir}")
    print(f"\n1️⃣  VRT (Virtual Raster Dataset):")
    print(f"    └─ MNT_D023.vrt")
    print(f"       Ce fichier lie toutes les {len(tile_data)} tuiles sans les copier")
    print(f"       👉 Ouvrez-le directement avec QGIS!")
    
    if os.path.isfile(output_tif):
        print(f"\n2️⃣  GeoTIFF (Raster fusionné):")
        file_size_mb = os.path.getsize(output_tif) / (1024 * 1024)
        print(f"    └─ MNT_D023.tif")
        print(f"       Fichier raster final fusionné ({file_size_mb:.2f} MB)")
    
    print(f"\n📊 Résumé:")
    print(f"   • {len(tile_data)} tuiles fusionnées")
    print(f"   • Projection: Lambert93 (EPSG:2154)")
    print(f"   • Format: Raster d'altitude MNT FRANCE - Département 023 (Creuse)")
    print(f"   • Étendue: {max_x - min_x:.0f} x {max_y - min_y:.0f} m")
    
    print(f"\n💡 Prochaines étapes:")
    print(f"   1. Ouvrir le fichier MNT_D023.vrt dans QGIS")
    print(f"   2. Le MNT complet du département s'affichera")
    print(f"   3. Les données sont prêtes pour l'analyse géospatiale")
    
    return True


if __name__ == "__main__":
    try:
        create_mnt_vrt()
    except KeyboardInterrupt:
        print("\n⚠️ Opération annulée par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
