#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validation complète de tous les MNT par département
Vérifie que chaque VRT généré est correct et sans erreur
"""

import os
import glob
import requests
import py7zr
import pandas as pd
import csv
from pathlib import Path
from datetime import datetime
import json
import traceback

# Chemins
CSV_PATH = r"C:\Users\marya\Downloads\projet test\deps.csv"
DOWNLOADS_DIR = r"C:\Users\marya\Downloads"
WORK_DIR = os.path.join(DOWNLOADS_DIR, "mnt_work")
LOGS_DIR = os.path.join(DOWNLOADS_DIR, "mnt_logs")
REPORT_FILE = os.path.join(LOGS_DIR, f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# Créer les répertoires
os.makedirs(WORK_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Configuration
TIMEOUT_DOWNLOAD = 300
CHUNK_SIZE = 8192

# Résultats de validation
results = []

def log_message(dept_code, dept_name, step, status, message=""):
    """Enregistrer un message de log"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] D{dept_code} ({dept_name}) - {step}: {status} {message}")
    
    results.append({
        'timestamp': timestamp,
        'dept_code': dept_code,
        'dept_name': dept_name,
        'step': step,
        'status': status,
        'message': message
    })

def parse_asc_header(filepath):
    """Parse l'en-tête d'un fichier ESRI ASCII Grid"""
    params = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i in range(7):
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
        print(f"   ❌ Erreur lecture header: {e}")
    return params

def create_vrt(asc_files, output_vrt, dept_code, dept_name):
    """Crée un VRT à partir des tuiles ASC"""
    
    if not asc_files:
        log_message(dept_code, dept_name, "VRT_CREATION", "❌ FAIL", "Aucun fichier ASC trouvé")
        return False
    
    print(f"\n   📊 Traitement des tuiles...")
    
    # Lire les paramètres de chaque tuile
    tile_data = []
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    for idx, asc_file in enumerate(asc_files):
        params = parse_asc_header(asc_file)
        if all(k in params for k in ['ncols', 'nrows', 'cellsize', 'xllcorner', 'yllcorner']):
            tile_data.append((asc_file, params))
            
            x_ll = params['xllcorner']
            y_ll = params['yllcorner']
            x_ur = x_ll + params['ncols'] * params['cellsize']
            y_ur = y_ll + params['nrows'] * params['cellsize']
            
            min_x = min(min_x, x_ll)
            min_y = min(min_y, y_ll)
            max_x = max(max_x, x_ur)
            max_y = max(max_y, y_ur)
        
        # Progress
        if (idx + 1) % max(1, len(asc_files) // 10) == 0:
            print(f"      {idx + 1}/{len(asc_files)} tuiles lues")
    
    if not tile_data:
        log_message(dept_code, dept_name, "VRT_CREATION", "❌ FAIL", "Impossible de lire les en-têtes")
        return False
    
    print(f"      ✅ {len(tile_data)} tuiles valides")
    
    # Paramètres raster
    sample_params = tile_data[0][1]
    ncols = sample_params.get('ncols', 5000)
    nrows = sample_params.get('nrows', 5000)
    cellsize = sample_params.get('cellsize', 5.0)
    nodata_value = sample_params.get('nodata_value', -9999)
    
    # Calculer les dimensions
    total_width = int((max_x - min_x) / cellsize)
    total_height = int((max_y - min_y) / cellsize)
    
    print(f"      📐 Résolution: {total_width} × {total_height} pixels")
    print(f"      ⬜ Cellule: {cellsize}m, NODATA: {nodata_value}")
    
    # Créer le header du VRT
    vrt_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<VRTDataset rasterXSize="{total_width}" rasterYSize="{total_height}">
  <SRS dataAxisToSrsAxisMapping="2,1">PROJCS["Lambert93",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],PARAMETER["false_northing",6600000],UNIT["Meter",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","2154"]]</SRS>
  <GeoTransform>{min_x}, {cellsize}, 0, {max_y}, 0, -{cellsize}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>{nodata_value}</NoDataValue>
'''
    
    # Ajouter chaque tuile
    for idx, (asc_file, params) in enumerate(tile_data):
        x_ll = params['xllcorner']
        y_ll = params['yllcorner']
        cs = params['cellsize']
        cols = params['ncols']
        rows = params['nrows']
        
        # Calculer les coordonnées de destination
        dst_x = int((x_ll - min_x) / cs)
        dst_y = int((max_y - (y_ll + rows * cs)) / cs)
        
        vrt_content += f'''    <SimpleSource>
      <SourceFilename relativeToVRT="0">{asc_file}</SourceFilename>
      <SourceBand>1</SourceBand>
      <SourceProperties RasterXSize="{cols}" RasterYSize="{rows}" DataType="Float32" />
      <SrcRect xOff="0" yOff="0" xSize="{cols}" ySize="{rows}" />
      <DstRect xOff="{dst_x}" yOff="{dst_y}" xSize="{cols}" ySize="{rows}" />
      <NODATA>{nodata_value}</NODATA>
    </SimpleSource>
'''
    
    vrt_content += '''  </VRTRasterBand>
</VRTDataset>
'''
    
    # Écrire le fichier VRT
    try:
        with open(output_vrt, 'w', encoding='utf-8') as f:
            f.write(vrt_content)
        
        file_size = os.path.getsize(output_vrt) / 1024
        log_message(dept_code, dept_name, "VRT_CREATION", "✅ OK", f"{len(tile_data)} tuiles, {file_size:.1f} KB")
        
        return {
            'success': True,
            'tiles': len(tile_data),
            'width': total_width,
            'height': total_height,
            'extent_x': (max_x - min_x),
            'extent_y': (max_y - min_y),
            'cellsize': cellsize,
            'nodata': nodata_value,
            'file_size_kb': file_size
        }
    except Exception as e:
        log_message(dept_code, dept_name, "VRT_CREATION", "❌ FAIL", f"Erreur écriture: {str(e)}")
        return False

def process_department(dept_code, dept_name, download_url):
    """Traite un département complet"""
    
    print(f"\n{'='*70}")
    print(f"🌍 Traitement département: D{dept_code} - {dept_name}")
    print(f"{'='*70}")
    
    try:
        # Étape 1: Téléchargement avec validation et retries
        print(f"\n1️⃣  TÉLÉCHARGEMENT")
        download_path = os.path.join(WORK_DIR, f"RGEALTI_D{dept_code}.7z")
        MAX_RETRIES = 3
        RETRY_DELAY = 2
        
        def is_valid_7z(file_path):
            """Valide que le fichier 7z est intègre"""
            try:
                if not os.path.exists(file_path):
                    return False
                with py7zr.SevenZipFile(file_path, 'r') as archive:
                    archive.list()
                    return True
            except Exception as err:
                print(f"   ⚠️  Validation 7z échouée: {str(err)}")
                return False
        
        def download_file(url, path, max_retries=MAX_RETRIES):
            """Télécharge avec retries"""
            for attempt in range(max_retries):
                try:
                    print(f"   📥 Tentative {attempt+1}/{max_retries}...")
                    response = requests.get(url, stream=True, timeout=TIMEOUT_DOWNLOAD)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    # Créer fichier temporaire
                    temp_path = path + ".tmp"
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if downloaded % (CHUNK_SIZE * 100) == 0:
                                    percent = (downloaded / total_size * 100) if total_size else 0
                                    print(f"      {percent:.0f}% ({downloaded / (1024*1024):.1f} MB)", end="\r")
                    
                    # Renommer si le fichier est valide
                    if os.path.getsize(temp_path) > 0:
                        os.replace(temp_path, path)
                        file_size_mb = os.path.getsize(path) / (1024*1024)
                        print(f"   ✅ Téléchargement terminé ({file_size_mb:.1f} MB)")
                        return True
                    else:
                        os.remove(temp_path)
                        return False
                        
                except Exception as e:
                    print(f"      Erreur: {str(e)}")
                    if attempt < max_retries - 1:
                        print(f"      Nouvelle tentative dans {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)
            return False
        
        # Vérifier si le fichier existe et est valide
        if os.path.exists(download_path):
            if is_valid_7z(download_path):
                print(f"   ✅ Fichier déjà téléchargé et valide ({os.path.getsize(download_path) / (1024*1024):.1f} MB)")
                log_message(dept_code, dept_name, "DOWNLOAD", "✅ SKIP", "Fichier valide existant")
            else:
                # Fichier corrompu, on le supprime et retélécharge
                print(f"   ⚠️  Fichier existant mais corrompu, suppression et retéléchargement...")
                try:
                    os.remove(download_path)
                except:
                    pass
                
                if not download_file(download_url, download_path):
                    log_message(dept_code, dept_name, "DOWNLOAD", "❌ FAIL", f"Échec après {MAX_RETRIES} tentatives")
                    return False
                
                if not is_valid_7z(download_path):
                    print(f"   ❌ Fichier 7z téléchargé mais corrompu (invalid header)")
                    try:
                        os.remove(download_path)
                    except:
                        pass
                    log_message(dept_code, dept_name, "DOWNLOAD", "❌ FAIL", "Fichier corrompu (invalid header)")
                    return False
        else:
            # Nouveau téléchargement
            if not download_file(download_url, download_path):
                log_message(dept_code, dept_name, "DOWNLOAD", "❌ FAIL", f"Échec après {MAX_RETRIES} tentatives")
                return False
            
            if not is_valid_7z(download_path):
                print(f"   ❌ Fichier 7z téléchargé mais corrompu (invalid header)")
                try:
                    os.remove(download_path)
                except:
                    pass
                log_message(dept_code, dept_name, "DOWNLOAD", "❌ FAIL", "Fichier corrompu (invalid header)")
                return False
        
        # Étape 2: Extraction
        print(f"\n2️⃣  EXTRACTION")
        extract_dir = os.path.join(WORK_DIR, f"RGEALTI_D{dept_code}")
        
        try:
            if not os.path.exists(os.path.join(extract_dir, "RGEALTI")):
                print(f"   📦 Extraction en cours...")
                try:
                    with py7zr.SevenZipFile(download_path, 'r') as archive:
                        archive.extractall(path=extract_dir)
                    print(f"   ✅ Extraction terminée")
                    log_message(dept_code, dept_name, "EXTRACTION", "✅ OK", "")
                except Exception as extract_error:
                    # En cas d'erreur d'extraction, supprimer le fichier 7z
                    print(f"   ❌ Erreur extraction: {str(extract_error)}")
                    try:
                        os.remove(download_path)
                        print(f"   🗑️  Fichier 7z supprimé (sera retéléchargé à la prochaine tentative)")
                    except:
                        pass
                    log_message(dept_code, dept_name, "EXTRACTION", "❌ FAIL", str(extract_error))
                    return False
            else:
                print(f"   ✅ Déjà extrait")
                log_message(dept_code, dept_name, "EXTRACTION", "✅ SKIP", "Dossier existant")
        
        except Exception as e:
            log_message(dept_code, dept_name, "EXTRACTION", "❌ FAIL", str(e))
            return False
        
        # Étape 3: Chercher les fichiers ASC
        print(f"\n3️⃣  RECHERCHE FICHIERS ASC")
        asc_pattern = os.path.join(extract_dir, "**", "*.asc")
        asc_files = sorted(glob.glob(asc_pattern, recursive=True))
        
        if not asc_files:
            log_message(dept_code, dept_name, "ASC_SEARCH", "❌ FAIL", "Aucun fichier .asc trouvé")
            return False
        
        print(f"   ✅ {len(asc_files)} fichiers ASC trouvés")
        log_message(dept_code, dept_name, "ASC_SEARCH", "✅ OK", f"{len(asc_files)} fichiers")
        
        # Étape 4: Créer le VRT
        print(f"\n4️⃣  CRÉATION VRT")
        vrt_path = os.path.join(DOWNLOADS_DIR, f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.vrt")
        
        result = create_vrt(asc_files, vrt_path, dept_code, dept_name)
        
        if not result:
            return False
        
        # Étape 5: Validation VRT
        print(f"\n5️⃣  VALIDATION VRT")
        try:
            with open(vrt_path, 'r', encoding='utf-8') as f:
                vrt_content = f.read()
            
            # Vérifications
            checks = [
                ('<?xml' in vrt_content, "Format XML valide"),
                ('VRTDataset' in vrt_content, "Structure VRT valide"),
                ('Lambert93' in vrt_content, "Projection Lambert93 présente"),
                ('EPSG:2154' in vrt_content or 'IGN69' in vrt_content, "Projection IGN69 présente"),
                ('NoDataValue' in vrt_content, "Valeur NODATA définie"),
                (f"<NoDataValue>{result['nodata']}</NoDataValue>" in vrt_content, "NODATA correct"),
                ('SimpleSource' in vrt_content and 'SourceFilename' in vrt_content, "Sources présentes"),
            ]
            
            all_ok = True
            for check, description in checks:
                status = "✅" if check else "❌"
                print(f"   {status} {description}")
                if not check:
                    all_ok = False
            
            if all_ok:
                print(f"\n   ✅ VRT valide et complet")
                log_message(dept_code, dept_name, "VRT_VALIDATION", "✅ OK", "Tous les contrôles passed")
            else:
                log_message(dept_code, dept_name, "VRT_VALIDATION", "❌ FAIL", "Certains contrôles ont échoué")
                return False
        
        except Exception as e:
            log_message(dept_code, dept_name, "VRT_VALIDATION", "❌ FAIL", str(e))
            return False
        
        # Résumé final
        print(f"\n{'✅ SUCCÈS'} Département D{dept_code} ({dept_name})")
        print(f"   📊 {result['tiles']} tuiles | {result['width']}×{result['height']} px")
        print(f"   📦 {result['extent_x']/1000:.1f} km × {result['extent_y']/1000:.1f} km")
        print(f"   💾 {result['file_size_kb']:.1f} KB VRT")
        
        return True
    
    except Exception as e:
        print(f"\n❌ ERREUR GÉNÉRALE: {e}")
        traceback.print_exc()
        log_message(dept_code, dept_name, "GENERAL", "❌ FAIL", str(e))
        return False

def main():
    """Traiter tous les départements"""
    
    print("\n" + "="*70)
    print("🏔️  VALIDATION COMPLÈTE MNT FRANCE - TOUS LES DÉPARTEMENTS")
    print("="*70)
    print(f"Démarrage: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Charger les départements
    try:
        df = pd.read_csv(CSV_PATH, sep=';')
        print(f"✅ {len(df)} départements à traiter\n")
    except Exception as e:
        print(f"❌ Erreur chargement CSV: {e}")
        return
    
    # Traiter chaque département
    success_count = 0
    fail_count = 0
    
    for idx, row in df.iterrows():
        dept_code = str(row['DEP_CODE']).strip()
        dept_name = str(row['DEP_LIB']).strip()
        download_url = str(row['URL']).strip()
        
        print(f"\n[{idx + 1}/{len(df)}]", end="")
        
        if process_department(dept_code, dept_name, download_url):
            success_count += 1
        else:
            fail_count += 1
    
    # Résumé final
    print("\n\n" + "="*70)
    print("📊 RÉSUMÉ FINAL")
    print("="*70)
    print(f"✅ Succès: {success_count}/{len(df)}")
    print(f"❌ Échecs: {fail_count}/{len(df)}")
    print(f"Rapport: {REPORT_FILE}")
    print(f"Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Sauvegarder le rapport
    try:
        df_results = pd.DataFrame(results)
        df_results.to_csv(REPORT_FILE, index=False, encoding='utf-8')
        print(f"\n📄 Rapport sauvegardé: {REPORT_FILE}")
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde rapport: {e}")

if __name__ == "__main__":
    main()
    input("\nAppuyez sur Entrée pour fermer...")
