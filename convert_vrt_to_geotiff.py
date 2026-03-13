#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tente de convertir le VRT résultant en GeoTIFF compressé et mosaïqué
Utilise gdalwarp si disponible, sinon fournit des instructions
"""

import os
import subprocess
import sys
from pathlib import Path

def convert_vrt_to_geotiff():
    """
    Convertit le VRT en GeoTIFF avec compression
    """
    
    vrt_file = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.vrt"
    output_tif = r"C:\Users\marya\Downloads\MNT_FRANCE_merged.tif"
    
    print("=" * 80)
    print("CONVERSION VRT → GeoTIFF")
    print("=" * 80)
    
    if not os.path.isfile(vrt_file):
        print(f"❌ Erreur: Le fichier VRT n'existe pas")
        print(f"   {vrt_file}")
        print(f"\n💡 Exécutez d'abord: create_mnt_vrt.py")
        sys.exit(1)
    
    print(f"\n📄 Fichier VRT source: {vrt_file}")
    print(f"📦 Taille VRT: {os.path.getsize(vrt_file) / 1024:.2f} KB")
    
    # Vérifier si gdalwarp est disponible
    print(f"\n🔍 Recherche de gdalwarp...")
    
    gdal_locations = [
        'gdalwarp',  # Dans PATH
        r'C:\OSGeo4W\bin\gdalwarp.exe',  # OSGeo4W installation standard
        r'C:\Program Files\GDAL\bin\gdalwarp.exe',
        # Autres locations possibles
    ]
    
    gdalwarp_path = None
    gdal_version = None
    
    for loc in gdal_locations:
        try:
            result = subprocess.run([loc, '--version'], 
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gdalwarp_path = loc
                gdal_version = result.stdout.strip()
                print(f"✅ gdalwarp trouvé: {loc}")
                print(f"   Version: {gdal_version}")
                break
        except Exception:
            continue
    
    if not gdalwarp_path:
        print("\n❌ gdalwarp n'est pas disponible")
        print("\n💡 Solutions pour installer GDAL en Windows:")
        print("\n   Option 1: OSGeo4W (Recommandé)")
        print("      1. Télécharger: https://trac.osgeo.org/osgeo4w/")
        print("      2. Installer GDAL lors de la sélection des paquets")
        print("")
        print("   Option 2: Anaconda/Conda")
        print("      $ conda install gdal")
        print("")
        print("   Option 3: Docker")
        print("      $ docker run -v C:\\path:/data osgeo/gdal:latest")
        print("")
        print("⚠️ En attendant, vous pouvez:")
        print("   • Ouvrir le VRT dans QGIS (https://qgis.org/)")
        print("   • Exporter ensuite en GeoTIFF depuis QGIS")
        print("")
        print(f"   Fichier VRT prêt: {vrt_file}")
        sys.exit(0)
    
    # Utiliser gdalwarp pour convertir
    print(f"\n🔄 Conversion du VRT en GeoTIFF (cela peut prendre du temps)...")
    
    cmd = [
        gdalwarp_path,
        '-of', 'GTiff',           # Format output
        '-co', 'COMPRESS=LZW',    # Compression
        '-co', 'TILED=YES',       # Tiling interne
        '-co', 'BLOCKXSIZE=512',  # Taille des blocs
        '-co', 'BLOCKYSIZE=512',
        '-multi',                 # Multi-threading
        '-wm', '256',             # Working memory
        vrt_file,
        output_tif
    ]
    
    try:
        print(f"\n  Commande: {' '.join(cmd[:6])} ...")
        print(f"  Cela peut prendre plusieurs minutes...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            if os.path.isfile(output_tif):
                file_size_mb = os.path.getsize(output_tif) / (1024 * 1024)
                
                print("\n" + "=" * 80)
                print("✅ SUCCÈS - Conversion réussie!")
                print("=" * 80)
                print(f"\n📦 Fichier GeoTIFF créé:")
                print(f"   {output_tif}")
                print(f"\n📊 Infos:")
                print(f"   • Taille: {file_size_mb:.2f} MB")
                print(f"   • Format: GeoTIFF avec compression LZW")
                print(f"   • Tuiles internes: 512x512 pixels")
                print(f"   • Projection: Lambert93-IGN69")
                print(f"\n✨ Le MNT fusionné est prêt à l'emploi!")
                
                return True
            else:
                print(f"\n⚠️ La commande s'est exécutée, mais le fichier n'a pas été créé")
                print(f"   Erreur: {result.stderr}")
                return False
        else:
            print(f"\n❌ Erreur lors de la conversion")
            print(f"   Code: {result.returncode}")
            print(f"   Message: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ La conversion a dépassé 1 heure (timeout)")
        return False
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False


if __name__ == "__main__":
    try:
        success = convert_vrt_to_geotiff()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Annulé par l'utilisateur")
        sys.exit(1)
