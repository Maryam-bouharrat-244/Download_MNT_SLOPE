#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application Streamlit pour télécharger et générer les MNT par département
"""

import streamlit as st
import pandas as pd
import os
import glob
import requests
import py7zr
import shutil
from pathlib import Path
import re
try:
    from osgeo import gdal
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False

import subprocess

# Importer le batch processor
try:
    from batch_processor import BatchProcessor
    BATCH_PROCESSOR_AVAILABLE = True
except ImportError:
    BATCH_PROCESSOR_AVAILABLE = False

# Chercher gdaldem depuis QGIS
def find_gdaldem():
    """Cherche gdaldem.exe depuis QGIS - cherche dans plusieurs emplacements"""
    
    # Liste des chemins possibles (plus les version-spécifiques)
    possible_paths = [
        r"C:\Program Files\QGIS\bin\gdaldem.exe",
        r"C:\Program Files (x86)\QGIS\bin\gdaldem.exe",
        r"C:\Program Files\QGIS 3.36\bin\gdaldem.exe",
        r"C:\Program Files\QGIS 3.38\bin\gdaldem.exe",
        r"C:\Program Files\QGIS 3.40\bin\gdaldem.exe",
        r"C:\Program Files\QGIS 3.40.15\bin\gdaldem.exe",
        r"C:\OSGeo4W\bin\gdaldem.exe",
        r"C:\Program Files\OSGeo4W\bin\gdaldem.exe",
    ]
    
    # 1. Chercher dans PATH
    gdaldem_path = shutil.which("gdaldem.exe")
    if gdaldem_path:
        return gdaldem_path
    
    # 2. Chercher dans les chemins connus
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # 3. Cherche récursif dans Program Files avec QGIS
    try:
        qgis_dir = r"C:\Program Files\QGIS"
        if os.path.exists(qgis_dir):
            # Chercher toutes les versions de QGIS
            for item in os.listdir(qgis_dir):
                qgis_version_dir = os.path.join(qgis_dir, item)
                if os.path.isdir(qgis_version_dir):
                    gdaldem_candidate = os.path.join(qgis_version_dir, "bin", "gdaldem.exe")
                    if os.path.exists(gdaldem_candidate):
                        return gdaldem_candidate
    except Exception as e:
        pass
    
    return None

GDALDEM_PATH = find_gdaldem()
HAS_GDALDEM = GDALDEM_PATH is not None

import numpy as np
import time

# Configuration Streamlit
st.set_page_config(
    page_title="🏔️ MNT France Generator",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS personnalisé
st.markdown("""
    <style>
    .big-font {
        font-size:2rem !important;
        font-weight:bold !important;
    }
    .info-box {
        background-color: #f0f2f6;
        border-left: 5px solid #1f77b4;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Titre
st.markdown('<p class="big-font">🏔️ Générateur MNT France</p>', unsafe_allow_html=True)
st.markdown("**Créez des mosaïques VRT personnalisées à partir des données d'altitude (MNT) de n'importe quel département**")
st.divider()

# Chemins
CSV_PATH = r"C:\Users\marya\Downloads\projet test\deps.csv"
DOWNLOADS_DIR = r"C:\Users\marya\Downloads"
WORK_DIR = os.path.join(DOWNLOADS_DIR, "mnt_work")

# Créer le répertoire de travail s'il n'existe pas
os.makedirs(WORK_DIR, exist_ok=True)

# Structure de dossiers pour batch processing
BATCH_OUTPUT_BASE = os.path.join(DOWNLOADS_DIR, "MNT_BATCH_RESULTS")

def create_batch_directories():
    """Crée la structure de dossiers pour le batch processing"""
    dirs = {
        'base': BATCH_OUTPUT_BASE,
        'mnt': os.path.join(BATCH_OUTPUT_BASE, 'MNT'),
        'pente': os.path.join(BATCH_OUTPUT_BASE, 'PENTE'),
        'pente_gt5': os.path.join(BATCH_OUTPUT_BASE, 'PENTE_SUP5'),
        'pente_gt10': os.path.join(BATCH_OUTPUT_BASE, 'PENTE_SUP10'),
        'logs': os.path.join(BATCH_OUTPUT_BASE, 'LOGS')
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return dirs

def get_batch_output_paths(dept_code, dept_name, dirs):
    """Retourne les chemins de sortie pour un département dans le batch"""
    return {
        'mnt': os.path.join(dirs['mnt'], f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.tif"),
        'pente': os.path.join(dirs['pente'], f"PENTE_D{dept_code}_{dept_name.replace(' ', '_')}.tif"),
        'pente_gt5': os.path.join(dirs['pente_gt5'], f"PENTE_BINAIRE_GT5_D{dept_code}_{dept_name.replace(' ', '_')}.tif"),
        'pente_gt10': os.path.join(dirs['pente_gt10'], f"PENTE_BINAIRE_GT10_D{dept_code}_{dept_name.replace(' ', '_')}.tif"),
    }

def download_and_extract_mnt(download_url, extract_base, dept_code, dept_name):
    """Télécharge et extrait le fichier MNT d'un département avec validation et retries
    
    Returns:
        dict: {'success': bool, 'files_count': int, 'message': str, 'extract_dir': str}
    """
    try:
        download_path = os.path.join(WORK_DIR, f"RGEALTI_D{dept_code}.7z")
        MAX_RETRIES = 3
        RETRY_DELAY = 2
        
        def is_valid_7z(file_path):
            """Valide que le fichier 7z est intègre"""
            try:
                if not os.path.exists(file_path):
                    return False
                with py7zr.SevenZipFile(file_path, 'r') as archive:
                    # Test en listant les fichiers
                    archive.list()
                    return True
            except Exception:
                return False
        
        def download_file(url, path, max_retries=MAX_RETRIES):
            """Télécharge avec retries"""
            for attempt in range(max_retries):
                try:
                    response = requests.get(url, stream=True, timeout=300)
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    # Créer fichier temporaire
                    temp_path = path + ".tmp"
                    with open(temp_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                    
                    # Renommer si valide
                    if os.path.getsize(temp_path) > 0:
                        os.replace(temp_path, path)
                        return True
                    else:
                        os.remove(temp_path)
                        return False
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(RETRY_DELAY)
                        continue
                    else:
                        return False
            return False
        
        # Vérifier si le fichier existe et est valide
        if os.path.exists(download_path):
            if is_valid_7z(download_path):
                # Fichier valide, on peut utiliser la version existante
                pass
            else:
                # Fichier corrompu, on le supprime et retélécharge
                try:
                    os.remove(download_path)
                    if not download_file(download_url, download_path):
                        return {
                            'success': False,
                            'files_count': 0,
                            'message': f"Échec téléchargement après {MAX_RETRIES} tentatives",
                            'extract_dir': ''
                        }
                    if not is_valid_7z(download_path):
                        os.remove(download_path)
                        return {
                            'success': False,
                            'files_count': 0,
                            'message': f"Fichier 7z téléchargé mais corrompu (invalid header)",
                            'extract_dir': ''
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'files_count': 0,
                        'message': f"Erreur lors de la suppression/retéléchargement: {str(e)}",
                        'extract_dir': ''
                    }
        else:
            # Nouveau téléchargement
            if not download_file(download_url, download_path):
                return {
                    'success': False,
                    'files_count': 0,
                    'message': f"Échec téléchargement après {MAX_RETRIES} tentatives",
                    'extract_dir': ''
                }
            if not is_valid_7z(download_path):
                os.remove(download_path)
                return {
                    'success': False,
                    'files_count': 0,
                    'message': f"Fichier 7z téléchargé mais corrompu (invalid header)",
                    'extract_dir': ''
                }
        
        # Extraire
        extract_dir = os.path.join(extract_base, f"D{dept_code}_extracted")
        os.makedirs(extract_dir, exist_ok=True)
        
        # Vérifier si l'extraction est déjà faite (chercher ASC files)
        asc_pattern = os.path.join(extract_dir, "**", "*.asc")
        asc_files = glob.glob(asc_pattern, recursive=True)
        
        if not asc_files:
            # Extraction nécessaire
            try:
                with py7zr.SevenZipFile(download_path, 'r') as archive:
                    archive.extractall(path=extract_dir)
            except Exception as e:
                # En cas d'erreur d'extraction, supprimer le fichier 7z et signaler
                try:
                    os.remove(download_path)
                except:
                    pass
                return {
                    'success': False,
                    'files_count': 0,
                    'message': f"Erreur extraction (fichier 7z supprimé): {str(e)}",
                    'extract_dir': extract_dir
                }
            
            # Après extraction, chercher derechef les ASC
            asc_files = glob.glob(asc_pattern, recursive=True)
        
        return {
            'success': len(asc_files) > 0,
            'files_count': len(asc_files),
            'message': f"{len(asc_files)} fichiers ASC trouvés",
            'extract_dir': extract_dir
        }
    
    except Exception as e:
        return {
            'success': False,
            'files_count': 0,
            'message': f"Erreur générale: {str(e)}",
            'extract_dir': ''
        }

# Charger les données des départements
@st.cache_data
def load_departments():
    try:
        df = pd.read_csv(CSV_PATH, sep=';')
        return df
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du CSV: {e}")
        return None

def parse_asc_header(filepath):
    """Parse l'en-tête d'un fichier ESRI ASCII Grid"""
    params = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i in range(7):  # Lire 7 lignes (ajout NODATA_value)
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
        st.warning(f"⚠️ Erreur lecture header {os.path.basename(filepath)}: {e}")
    return params

def create_vrt(asc_files, output_vrt):
    """Crée un VRT à partir des tuiles ASC"""
    
    if not asc_files:
        st.error("❌ Aucun fichier ASC trouvé!")
        return False
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Lire les paramètres de chaque tuile
    tile_data = []
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    
    total_files = len(asc_files)
    
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
        
        # Mise à jour de la barre de progression
        progress = (idx + 1) / total_files
        progress_bar.progress(progress)
        status_text.text(f"📖 Lecture des en-têtes: {idx + 1}/{total_files}")
    
    if not tile_data:
        st.error("❌ Impossible de lire les en-têtes des fichiers ASC")
        return False
    
    status_text.text(f"✅ {len(tile_data)} tuiles trouvées")
    
    # Paramètres raster
    sample_params = tile_data[0][1]
    ncols = sample_params.get('ncols', 5000)
    nrows = sample_params.get('nrows', 5000)
    cellsize = sample_params.get('cellsize', 5.0)
    nodata_value = sample_params.get('nodata_value', -9999)  # Lire la vraie valeur NODATA
    
    # Calculer les dimensions
    total_width = int((max_x - min_x) / cellsize)
    total_height = int((max_y - min_y) / cellsize)
    
    # Créer le header du VRT
    vrt_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<VRTDataset rasterXSize="{total_width}" rasterYSize="{total_height}">
  <SRS dataAxisToSrsAxisMapping="2,1">PROJCS["Lambert93",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],PARAMETER["false_northing",6600000],UNIT["Meter",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","2154"]]</SRS>
  <GeoTransform>{min_x}, {cellsize}, 0, {max_y}, 0, -{cellsize}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>{nodata_value}</NoDataValue>
'''
    
    # Ajouter chaque tuile
    status_text.text(f"📝 Construction du VRT...")
    progress_bar.progress(0)
    
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
      <NODATA>-9999</NODATA>
    </SimpleSource>
'''
        
        progress = (idx + 1) / len(tile_data)
        progress_bar.progress(progress)
    
    vrt_content += '''  </VRTRasterBand>
</VRTDataset>
'''
    
    # Écrire le fichier VRT
    try:
        with open(output_vrt, 'w', encoding='utf-8') as f:
            f.write(vrt_content)
        status_text.text("✅ VRT créé avec succès!")
        progress_bar.progress(1.0)
        
        return {
            'success': True,
            'tiles': len(tile_data),
            'width': total_width,
            'height': total_height,
            'extent_x': (max_x - min_x),
            'extent_y': (max_y - min_y),
            'cellsize': cellsize
        }
    except Exception as e:
        st.error(f"❌ Erreur lors de l'écriture du VRT: {e}")
        return False

def test_vrt_quality(vrt_path, asc_files):
    """Teste la qualité du VRT généré"""
    
    if not os.path.exists(vrt_path):
        return {'success': False, 'message': 'VRT non trouvé'}
    
    if not asc_files:
        return {'success': False, 'message': 'Aucun fichier ASC'}
    
    test_results = {
        'success': True,
        'message': 'VRT valide',
        'checks': [],
        'tiles_tested': 0,
        'issues': []
    }
    
    # Test 1: Vérifier que le fichier VRT existe et est valide
    try:
        with open(vrt_path, 'r', encoding='utf-8') as f:
            vrt_content = f.read()
        
        if '<VRTDataset' not in vrt_content or '</VRTDataset>' not in vrt_content:
            test_results['success'] = False
            test_results['issues'].append("Structure XML incomplète")
            return test_results
        
        test_results['checks'].append("✅ Fichier VRT bien formé (XML valide)")
    except Exception as e:
        test_results['success'] = False
        test_results['issues'].append(f"Lecture VRT: {str(e)}")
        return test_results
    
    # Test 2: Vérifier que toutes les tuiles ASC sont référencées
    try:
        missing_tiles = []
        for asc_file in asc_files:
            if os.path.basename(asc_file) not in vrt_content:
                missing_tiles.append(os.path.basename(asc_file))
        
        if missing_tiles:
            test_results['issues'].append(f"{len(missing_tiles)} tuiles non trouvées dans le VRT")
            test_results['success'] = False
        else:
            test_results['checks'].append(f"✅ Toutes les {len(asc_files)} tuiles référencées")
            test_results['tiles_tested'] = len(asc_files)
    except Exception as e:
        test_results['issues'].append(f"Vérification tuiles: {str(e)}")
        test_results['success'] = False
    
    # Test 3: Vérifier les en-têtes des tuiles
    try:
        all_params_valid = True
        sample_cellsize = None
        
        for orig_asc_file in asc_files[:min(3, len(asc_files))]:  # Tester max 3 tuiles
            params = parse_asc_header(orig_asc_file)
            
            required_keys = ['ncols', 'nrows', 'cellsize', 'xllcorner', 'yllcorner']
            if not all(k in params for k in required_keys):
                test_results['issues'].append(f"En-tête invalide: {os.path.basename(orig_asc_file)}")
                all_params_valid = False
            else:
                if sample_cellsize is None:
                    sample_cellsize = params['cellsize']
                
                if params['cellsize'] != sample_cellsize:
                    test_results['issues'].append(f"Cellsize inconsistent en {os.path.basename(orig_asc_file)}")
                    all_params_valid = False
        
        if all_params_valid:
            test_results['checks'].append("✅ En-têtes ASC valides et cohérents")
        else:
            test_results['success'] = False
    except Exception as e:
        test_results['issues'].append(f"Vérification en-têtes: {str(e)}")
        test_results['success'] = False
    
    # Test 4: Vérifier la projection et les métadonnées VRT
    try:
        if 'Lambert93' in vrt_content and ('EPSG:2154' in vrt_content or 'EPSG","2154' in vrt_content):
            test_results['checks'].append("✅ Projection Lambert93 (EPSG:2154) détectée")
        else:
            test_results['issues'].append("Projection non trouvée ou incorrecte")
            test_results['success'] = False
        
        if '<GeoTransform>' in vrt_content:
            test_results['checks'].append("✅ GeoTransform présent")
        else:
            test_results['issues'].append("GeoTransform manquant")
            test_results['success'] = False
        
        if '<NoDataValue>' in vrt_content:
            test_results['checks'].append("✅ Valeur NoData définie")
        else:
            test_results['issues'].append("NoData non défini")
            test_results['success'] = False
    
    except Exception as e:
        test_results['issues'].append(f"Vérification métadonnées: {str(e)}")
        test_results['success'] = False
    
    # Test 5: Si GDAL est disponible, test approfondi
    if GDAL_AVAILABLE:
        try:
            vrt_ds = gdal.Open(vrt_path)
            if vrt_ds is not None:
                vrt_width = vrt_ds.RasterXSize
                vrt_height = vrt_ds.RasterYSize
                vrt_geo = vrt_ds.GetGeoTransform()
                
                if vrt_width > 0 and vrt_height > 0:
                    test_results['checks'].append(f"✅ Dimensions VRT valides: {vrt_width}×{vrt_height} px")
                else:
                    test_results['issues'].append("Dimensions VRT invalides")
                    test_results['success'] = False
                
                # Lire un pixel de test
                try:
                    band = vrt_ds.GetRasterBand(1)
                    test_pixel = band.ReadAsArray(0, 0, 1, 1)
                    if test_pixel is not None:
                        test_results['checks'].append("✅ Lecture pixels VRT OK")
                    else:
                        test_results['issues'].append("Impossible de lire les pixels VRT")
                        test_results['success'] = False
                except:
                    pass
                
                vrt_ds = None
            else:
                test_results['issues'].append("GDAL: impossible d'ouvrir le VRT")
                test_results['success'] = False
        except Exception as e:
            # GDAL n'est pas disponible, ça peut être normal
            pass
    
    return test_results

def calculate_slope(vrt_path, output_slope_path):
    """Calcule la pente en % à partir du VRT MNT usando gdaldem"""
    
    # Utiliser le chemin personnalisé si l'utilisateur l'a fourni
    gdaldem_to_use = st.session_state.get('custom_gdaldem_path')
    if not gdaldem_to_use:
        gdaldem_to_use = GDALDEM_PATH
    
    if not gdaldem_to_use:
        return {'success': False, 'message': 'gdaldem non trouvé - Installez QGIS avec les outils GDAL'}
    
    if not os.path.exists(gdaldem_to_use):
        return {'success': False, 'message': f'gdaldem introuvable au chemin: {gdaldem_to_use}'}
    
    try:
        progress_slope = st.progress(0)
        status_slope = st.empty()
        metrics_slope = st.empty()
        
        # Vérifier que le VRT existe
        if not os.path.exists(vrt_path):
            return {'success': False, 'message': f'VRT non trouvé: {vrt_path}'}
        
        status_slope.text("📖 Préparation du calcul de pente...")
        progress_slope.progress(10)
        
        # Utiliser gdaldem pour calculer la pente en %
        # -p : output in percent slope
        # -s : scale factor
        cmd = [
            gdaldem_to_use,
            'slope',
            '-p',           # en pourcentage
            '-s', '1.0',    # facteur d'échelle
            vrt_path,
            output_slope_path
        ]
        
        metrics_slope.metric(
            "⏱️ Statut",
            "Calcul en cours...",
            delta="Allocation des ressources"
        )
        
        status_slope.text("📊 Calcul de la pente avec gdaldem...")
        progress_slope.progress(20)
        
        # Exécuter gdaldem
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 heure max
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Erreur inconnue de gdaldem"
            return {
                'success': False,
                'message': f'gdaldem erreur: {error_msg}'
            }
        
        progress_slope.progress(50)
        status_slope.text("📝 Calcul de la pente en cours...")
        
        # Ouvrir le résultat avec GDAL si disponible pour les stats
        if GDAL_AVAILABLE:
            try:
                ds = gdal.Open(output_slope_path)
                if ds:
                    band = ds.GetRasterBand(1)
                    stats = band.GetStatistics(False, True)
                    
                    min_slope = float(stats[0])
                    max_slope = float(stats[1])
                    mean_slope = float(stats[2])
                    std_slope = float(stats[3])
                    
                    ds = None
                else:
                    # Valeurs par défaut si on peut pas lire
                    min_slope = max_slope = mean_slope = std_slope = 0
            except:
                min_slope = max_slope = mean_slope = std_slope = 0
        else:
            min_slope = max_slope = mean_slope = std_slope = 0
        
        progress_slope.progress(90)
        status_slope.text("💾 Finalisation...")
        
        # Obtenir la taille du fichier
        file_size = os.path.getsize(output_slope_path) / (1024*1024)
        
        progress_slope.progress(100)
        status_slope.text("✅ Pente calculée avec succès!")
        
        metrics_slope.metric(
            "⏱️ Temps de traitement",
            f"{int(elapsed)}s",
            delta=f"Fichier: {file_size:.1f} MB"
        )
        
        return {
            'success': True,
            'message': 'Pente calculée avec gdaldem',
            'min_slope': min_slope,
            'max_slope': max_slope,
            'mean_slope': mean_slope,
            'std_slope': std_slope,
            'file_size': file_size,
            'processing_time': int(elapsed),
            'method': 'gdaldem (rapide et efficace)'
        }
        
    except subprocess.TimeoutExpired:
        return {'success': False, 'message': 'Calcul dépassé le délai d\'exécution (>1h)'}
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def create_slope_filters(slope_raster_path, output_dir, dept_code, dept_name, threshold=5.0):
    """Crée un raster filtré: pentes > threshold"""
    
    if not GDAL_AVAILABLE:
        return {'success': False, 'message': 'GDAL Python non disponible pour les filtres'}
    
    try:
        progress_filter = st.progress(0)
        status_filter = st.empty()
        
        status_filter.text(f"📖 Lecture du raster de pente (filtre > {threshold}%)...")
        progress_filter.progress(10)
        
        # Ouvrir le raster de pente
        ds = gdal.Open(slope_raster_path)
        if ds is None:
            return {'success': False, 'message': 'Impossible d\'ouvrir le raster de pente'}
        
        band = ds.GetRasterBand(1)
        slope_data = band.ReadAsArray().astype(np.float32)
        
        width = ds.RasterXSize
        height = ds.RasterYSize
        geo = ds.GetGeoTransform()
        srs = ds.GetProjection()
        
        progress_filter.progress(20)
        status_filter.text(f"🔧 Création du filtre pentes > {threshold}%...")
        
        # Créer le raster filtré
        driver = gdal.GetDriverByName('GTiff')
        
        # Filtre custom
        slope_filtered = slope_data.copy()
        slope_filtered[slope_filtered <= threshold] = -9999  # Marquer comme NoData
        
        # Déterminer le nom du fichier
        if threshold == 5.0:
            file_output = os.path.join(output_dir, f"PENTE_GT5_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        elif threshold == 10.0:
            file_output = os.path.join(output_dir, f"PENTE_GT10_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        else:
            file_output = os.path.join(output_dir, f"PENTE_GT{int(threshold)}_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        
        out_ds = driver.Create(file_output, width, height, 1, gdal.GDT_Float32)
        out_ds.SetGeoTransform(geo)
        out_ds.SetProjection(srs)
        out_band = out_ds.GetRasterBand(1)
        out_band.WriteArray(slope_filtered)
        out_band.SetNoDataValue(-9999)
        out_band.FlushCache()
        out_ds = None
        
        progress_filter.progress(80)
        status_filter.text("📊 Calcul des statistiques...")
        
        # Statistiques filtrées
        slope_valid = slope_filtered[slope_filtered > 0]
        
        stats = {
            'count': len(slope_valid),
            'percent': 100 * len(slope_valid) / (width * height) if width * height > 0 else 0,
            'mean': float(np.mean(slope_valid)) if len(slope_valid) > 0 else 0,
            'file_size': os.path.getsize(file_output) / (1024*1024)
        }
        
        progress_filter.progress(100)
        status_filter.text("✅ Filtre créé!")
        
        ds = None
        
        return {
            'success': True,
            'file_path': file_output,
            'stats': stats
        }
        
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def calculate_and_write_statistics(tiff_path, nodata_value=-99999):
    """Calcule les statistiques réelles (sans NoData) et crée le fichier .aux.xml"""
    
    try:
        import rasterio
        from rasterio.io import MemoryFile
        
        # Lire les données
        with rasterio.open(tiff_path) as src:
            data = src.read(1).astype(np.float32)
            profile = src.profile
        
        # Exclure les NoData
        valid_data = data[data != nodata_value]
        
        if len(valid_data) == 0:
            return {'success': False, 'message': 'Aucune donnée valide trouvée'}
        
        # Calculer les stats réelles
        stats = {
            'min': float(np.min(valid_data)),
            'max': float(np.max(valid_data)),
            'mean': float(np.mean(valid_data)),
            'std': float(np.std(valid_data)),
            'count': int(len(valid_data))
        }
        
        # Créer le fichier .aux.xml avec les statistiques
        aux_path = tiff_path + '.aux.xml'
        
        aux_content = f'''<PAMDataset>
  <Item name="STATISTICS_APPROXIMATE">YES</Item>
  <Item name="STATISTICS_MINIMUM">{stats['min']:.2f}</Item>
  <Item name="STATISTICS_MAXIMUM">{stats['max']:.2f}</Item>
  <Item name="STATISTICS_MEAN">{stats['mean']:.2f}</Item>
  <Item name="STATISTICS_STDDEV">{stats['std']:.2f}</Item>
  <Item name="STATISTICS_VALID_PERCENT">100</Item>
</PAMDataset>'''
        
        with open(aux_path, 'w') as f:
            f.write(aux_content)
        
        return {
            'success': True,
            'stats': stats,
            'aux_path': aux_path
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def deep_verify_conversion(vrt_path, tiff_path):
    """Vérification profonde: compare les données pixel par pixel et les métadonnées"""
    
    try:
        import rasterio
        
        verification = {
            'vrt': {},
            'tiff': {},
            'comparison': {}
        }
        
        # Lire VRT
        with rasterio.open(vrt_path) as src_vrt:
            vrt_data = src_vrt.read()
            vrt_profile = src_vrt.profile
            
            verification['vrt'] = {
                'shape': vrt_data.shape,
                'dtype': str(vrt_data.dtype),
                'bands': vrt_profile.get('count', 1),
                'nodata': vrt_profile.get('nodata'),
                'projection': vrt_profile.get('crs'),
            }
            
            # Stats par bande
            for i in range(vrt_data.shape[0]):
                band_data = vrt_data[i]
                valid = band_data[band_data != vrt_profile.get('nodata', -9999)]
                if len(valid) > 0:
                    verification['vrt'][f'band_{i+1}_stats'] = {
                        'min': float(np.min(valid)),
                        'max': float(np.max(valid)),
                        'mean': float(np.mean(valid)),
                        'valid_pixels': int(len(valid))
                    }
        
        # Lire TIFF
        with rasterio.open(tiff_path) as src_tiff:
            tiff_data = src_tiff.read()
            tiff_profile = src_tiff.profile
            
            verification['tiff'] = {
                'shape': tiff_data.shape,
                'dtype': str(tiff_data.dtype),
                'bands': tiff_profile.get('count', 1),
                'nodata': tiff_profile.get('nodata'),
                'projection': tiff_profile.get('crs'),
            }
            
            # Stats par bande
            for i in range(tiff_data.shape[0]):
                band_data = tiff_data[i]
                valid = band_data[band_data != tiff_profile.get('nodata', -9999)]
                if len(valid) > 0:
                    verification['tiff'][f'band_{i+1}_stats'] = {
                        'min': float(np.min(valid)),
                        'max': float(np.max(valid)),
                        'mean': float(np.mean(valid)),
                        'valid_pixels': int(len(valid))
                    }
        
        # Comparaison
        if vrt_data.shape == tiff_data.shape:
            pixel_match = np.allclose(vrt_data, tiff_data, rtol=0.001, equal_nan=True)
            verification['comparison']['shapes_match'] = True
            verification['comparison']['pixels_match'] = bool(pixel_match)
            verification['comparison']['pixel_tolerance'] = '0.1%'
            
            # Différence maximale
            diff = np.abs(vrt_data - tiff_data)
            verification['comparison']['max_difference'] = float(np.nanmax(diff))
            verification['comparison']['mean_difference'] = float(np.nanmean(diff))
        else:
            verification['comparison']['shapes_match'] = False
            verification['comparison']['vrt_shape'] = vrt_data.shape
            verification['comparison']['tiff_shape'] = tiff_data.shape
        
        return {
            'success': True,
            'verification': verification
        }
    
    except Exception as e:
        import traceback
        return {
            'success': False,
            'message': f'Erreur: {str(e)}',
            'traceback': traceback.format_exc()
        }

def compare_vrt_and_tiff(vrt_path, tiff_path):
    """Compare les statistiques du VRT et du TIFF pour vérifier la conversion"""
    
    try:
        import rasterio
        
        stats_compare = {}
        
        # Lire le VRT
        with rasterio.open(vrt_path) as src:
            vrt_data = src.read(1)
            stats_compare['vrt'] = {
                'dtype': str(vrt_data.dtype),
                'min': float(np.nanmin(vrt_data)),
                'max': float(np.nanmax(vrt_data)),
                'mean': float(np.nanmean(vrt_data)),
                'nodata': src.profile.get('nodata'),
                'count_valid': int(np.count_nonzero(~np.isnan(vrt_data)))
            }
        
        # Lire le TIFF
        with rasterio.open(tiff_path) as src:
            tiff_data = src.read(1)
            stats_compare['tiff'] = {
                'dtype': str(tiff_data.dtype),
                'min': float(np.nanmin(tiff_data)),
                'max': float(np.nanmax(tiff_data)),
                'mean': float(np.nanmean(tiff_data)),
                'nodata': src.profile.get('nodata'),
                'count_valid': int(np.count_nonzero(~np.isnan(tiff_data)))
            }
        
        # Comparaison
        are_equal = np.allclose(vrt_data, tiff_data, rtol=0.01, equal_nan=True)
        
        return {
            'success': True,
            'stats': stats_compare,
            'data_equal': are_equal,
            'difference': abs(stats_compare['vrt']['max'] - stats_compare['tiff']['max']) if stats_compare['vrt']['max'] > 0 else 0
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def convert_vrt_to_tiff(vrt_path, output_dir, dept_code, dept_name, gdaldem_path=None):
    """Convertit un VRT en TIFF avec gdal_translate"""
    
    try:
        # Chemin du fichier TIFF de sortie
        tiff_path = os.path.join(output_dir, f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        
        # Trouver gdal_translate
        gdal_translate_path = None
        
        # 1. Chercher dans le PATH
        gdal_translate_path = shutil.which('gdal_translate')
        
        # 2. Si gdaldem_path est fourni, utiliser son répertoire
        if not gdal_translate_path and gdaldem_path:
            gdaldem_dir = os.path.dirname(gdaldem_path)
            candidate_path = os.path.join(gdaldem_dir, 'gdal_translate.exe')
            if os.path.exists(candidate_path):
                gdal_translate_path = candidate_path
        
        # 3. Chercher dans les installations QGIS connues
        if not gdal_translate_path:
            qgis_search_paths = [
                'C:\\Program Files\\QGIS',
                'C:\\Program Files (x86)\\QGIS',
                'C:\\OSGeo4W',
                os.path.expandvars('%PROGRAMFILES%\\QGIS'),
                os.path.expandvars('%PROGRAMFILES(X86)%\\QGIS'),
            ]
            
            for base_path in qgis_search_paths:
                if os.path.exists(base_path):
                    # Chercher récursivement
                    for root, dirs, files in os.walk(base_path):
                        if 'gdal_translate.exe' in files:
                            gdal_translate_path = os.path.join(root, 'gdal_translate.exe')
                            break
                    if gdal_translate_path:
                        break
        
        if not gdal_translate_path or not os.path.exists(gdal_translate_path):
            return {'success': False, 'message': 'gdal_translate non trouvé'}
        
        # Utiliser la version silent si on n'est pas en contexte Streamlit
        try:
            progress = st.progress(0)
            status = st.empty()
            
            status.text("📦 Compression en cours avec gdal_translate...")
            progress.progress(20)
        except:
            # Context Streamlit non disponible, ignorez
            progress = None
            status = None
        
        # Commande de conversion avec compression
        cmd = [
            gdal_translate_path,
            '-of', 'GTiff',
            '-co', 'COMPRESS=LZW',  # Compression LZW
            '-co', 'TILED=YES',      # Format tuilé
            '-co', 'BLOCKXSIZE=512', 
            '-co', 'BLOCKYSIZE=512',
            vrt_path,
            tiff_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        
        if progress:
            progress.progress(80)
        
        if result.returncode != 0:
            return {'success': False, 'message': f'Erreur gdal_translate: {result.stderr}'}
        
        if progress:
            progress.progress(100)
        if status:
            status.text("✅ Conversion TIFF terminée!")
        
        # Obtenir la taille du fichier
        file_size = os.path.getsize(tiff_path) / (1024*1024)
        
        return {
            'success': True,
            'file_path': tiff_path,
            'file_size': file_size
        }
    
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def calculate_and_export_slope_with_filter(vrt_path, threshold, output_dir, dept_code, dept_name, gdaldem_path):
    """Calcule la pente avec gdaldem et crée raster binaire avec calculatrice raster (rasterio + numpy)"""
    
    if not os.path.exists(gdaldem_path):
        return {'success': False, 'message': f'gdaldem non trouvé: {gdaldem_path}'}
    
    try:
        import rasterio
        
        # Try to get Streamlit context, but don't fail if not available
        try:
            progress_all = st.progress(0)
            status_all = st.empty()
            debug_info = st.empty()
        except:
            progress_all = None
            status_all = None
            debug_info = None
        
        def update_progress(pct, msg):
            if progress_all:
                progress_all.progress(pct)
            if status_all:
                status_all.text(msg)
        
        def debug_message(msg):
            if debug_info:
                debug_info.markdown(msg)
        
        # Fichiers
        temp_slope_file = os.path.join(output_dir, f"_temp_slope_D{dept_code}.tif")
        pente_complete = os.path.join(output_dir, f"PENTE_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        pente_binaire = os.path.join(output_dir, f"PENTE_BINAIRE_GT{int(threshold)}_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
        
        update_progress(10, f"📊 Étape 1: Calcul de la pente avec gdaldem...")
        
        # Étape 1: Calculer la pente avec gdaldem
        cmd = [
            gdaldem_path,
            'slope',
            '-p',           # en pourcentage
            '-s', '1.0',    # facteur d'échelle
            vrt_path,
            temp_slope_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode != 0:
            return {'success': False, 'message': f'Erreur gdaldem: {result.stderr}'}
        
        update_progress(35, f"📖 Lecture et analyse des données de pente...")
        
        # Lire et analyser les données
        with rasterio.open(temp_slope_file) as src:
            slope_data = src.read(1).astype(np.float32)
            profile = src.profile
            
            # DEBUG: Afficher les stats de la pente complète
            slope_min = np.nanmin(slope_data)
            slope_max = np.nanmax(slope_data)
            slope_mean = np.nanmean(slope_data)
            slope_count_valid = np.sum(~np.isnan(slope_data))
            
            debug_text = f"""
            **📊 DEBUG - Statistiques de la pente calculée (avant filtrage):**
            • Min: {slope_min:.2f}%
            • Max: {slope_max:.2f}%
            • Moyenne: {slope_mean:.2f}%
            • Pixels valides: {slope_count_valid:,}
            • Shape: {slope_data.shape}
            • Seuil appliqué: > {threshold}%
            """
            debug_message(debug_text)
        
        update_progress(50, f"📋 Étape 2: Copie de la pente complète...")
        
        # Étape 2: Copier la pente complète AVEC les bonnes stats
        with rasterio.open(temp_slope_file) as src:
            data = src.read(1)
            profile_copy = src.profile.copy()
        
        with rasterio.open(pente_complete, 'w', **profile_copy) as dst:
            dst.write(data, 1)
        
        update_progress(65, f"🔧 Étape 3: Création du raster binaire (calculatrice raster)...")
        
        # Étape 3: Lire et créer le binaire
        with rasterio.open(temp_slope_file) as src:
            slope_data = src.read(1).astype(np.float32)
            profile = src.profile
            
            # DEBUG: Compter avant/après
            count_above = np.sum(slope_data > threshold)
            count_below = np.sum(slope_data <= threshold)
            
            # Calculatrice raster: binary = (slope > threshold) ? 1 : 0
            binary_data = np.where(slope_data > threshold, 1, 0).astype(np.uint8)
            
            # DEBUG: Vérifier le résultat
            debug_binary = f"""
            **🔍 Vérification du filtrage:**
            • Pixels pente > {threshold}%: {count_above:,} → valeur 1
            • Pixels pente ≤ {threshold}%: {count_below:,} → valeur 0
            • Total: {count_above + count_below:,}
            • Min binaire: {np.min(binary_data)} | Max binaire: {np.max(binary_data)}
            """
            debug_message(debug_binary)
            
            # Créer le raster binaire
            binary_profile = profile.copy()
            binary_profile.update(dtype=rasterio.uint8, nodata=255)
            
            with rasterio.open(pente_binaire, 'w', **binary_profile) as dst:
                dst.write(binary_data, 1)
        
        update_progress(85, f"📊 Calcul des statistiques...")
        
        # Calcul des statistiques
        slope_valid = slope_data[(slope_data > 0) & (slope_data != -9999)]
        pixels_above_threshold = np.sum(binary_data == 1)
        total_pixels = binary_data.size
        
        stats = {
            'count': int(pixels_above_threshold),
            'percent': 100 * pixels_above_threshold / total_pixels if total_pixels > 0 else 0,
            'mean': float(np.mean(slope_valid)) if len(slope_valid) > 0 else 0,
            'max': float(np.max(slope_valid)) if len(slope_valid) > 0 else 0,
            'file_size': os.path.getsize(pente_binaire) / (1024*1024)
        }
        
        # Nettoyage fichier temporaire
        if os.path.exists(temp_slope_file):
            os.remove(temp_slope_file)
        
        update_progress(100, f"✅ Pente complète et binaire > {threshold}% crées!")
        
        return {
            'success': True,
            'file_path': pente_binaire,
            'pente_complete': pente_complete,
            'stats': stats
        }
    
    except Exception as e:
        import traceback
        return {'success': False, 'message': f'Erreur: {str(e)}\n{traceback.format_exc()}'}
    
    except Exception as e:
        return {'success': False, 'message': f'Erreur: {str(e)}'}

def find_previous_batch_logs():
    """
    Cherche le dossier du batch processing PRÉCÉDENT
    Cherche dans MNT_BATCH_RESULTS et les variantes datées
    
    Returns:
        tuple: (logs_dir_path, batch_folder_name) ou (None, None)
    """
    parent_dir = DOWNLOADS_DIR
    
    if not os.path.exists(parent_dir):
        return None, None
    
    candidate_dirs = []
    
    # Chercher tous les dossiers de batch processing
    try:
        for item in os.listdir(parent_dir):
            item_path = os.path.join(parent_dir, item)
            if os.path.isdir(item_path):
                # Chercher les dossiers qui contiennent MNT_BATCH
                if 'MNT_BATCH' in item:
                    logs_dir = os.path.join(item_path, 'LOGS')
                    if os.path.exists(logs_dir):
                        # Vérifier qu'il y a au moins un fichier log
                        log_files = glob.glob(os.path.join(logs_dir, "batch_processing_*.log"))
                        if log_files:
                            # Récupérer la date de modification
                            try:
                                mtime = os.path.getmtime(logs_dir)
                                candidate_dirs.append((mtime, logs_dir, item))
                            except:
                                pass
    except Exception as e:
        return None, None
    
    if not candidate_dirs:
        return None, None
    
    # Trier par date (plus récent en dernier)
    candidate_dirs.sort(key=lambda x: x[0])
    
    # Retourner le dossier LOGS du PLUS RÉCENT
    # (on veut le dernier batch qui a tourné, pas le nouveau vide)
    logs_dir = candidate_dirs[-1][1]
    batch_name = candidate_dirs[-1][2]
    
    return logs_dir, batch_name

def read_batch_logs(logs_dir):
    """
    Lit les fichiers logs du batch pour déterminer le statut des départements
    Format attendu:
    - 2026-03-11 18:37:16,611 - INFO - [OK] 1 - Ain: success
    - 2026-03-11 18:37:48,136 - ERROR - [ERROR] 7 - Erreur: message...
    
    Returns:
        dict: {dept_code: {'status': 'success'|'error', 'error_msg': str}}
    """
    import re
    
    dept_status = {}
    
    if not os.path.exists(logs_dir):
        return dept_status
    
    # Chercher tous les fichiers logs
    log_files = sorted(glob.glob(os.path.join(logs_dir, "batch_processing_*.log")))
    
    if not log_files:
        return dept_status
    
    # Lire le LOG LE PLUS RÉCENT
    latest_log = log_files[-1]
    
    try:
        with open(latest_log, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Pattern: [OK] DD - ...
                ok_match = re.search(r'\[OK\]\s+(\d+|2[AB])\s*-', line)
                if ok_match:
                    dept_code = ok_match.group(1)
                    dept_status[dept_code] = {'status': 'success', 'error_msg': ''}
                    continue
                
                # Pattern: [ERROR] DD - Erreur: ...
                error_match = re.search(r'\[ERROR\]\s+(\d+|2[AB])\s*-\s*(.+?)(?:\n|$)', line)
                if error_match:
                    dept_code = error_match.group(1)
                    error_msg = error_match.group(2).strip() if error_match.group(2) else "Erreur inconnue"
                    dept_status[dept_code] = {'status': 'error', 'error_msg': error_msg[:120]}
                    continue
                    
    except Exception as e:
        try:
            st.warning(f"⚠️ Erreur lecture logs: {str(e)}")
        except:
            pass
    
    return dept_status

def check_department_completion(dept_code, dept_name, dirs, log_status=None):
    """
    Vérifie si un département a déjà été entièrement traité
    Combine l'info des LOGS et des FICHIERS (dans nouveau ET ancien batch)
    
    Returns:
        tuple: (is_complete, status, missing_files)
            - is_complete: bool - True si tous les fichiers existent et pas d'erreur
            - status: str - 'success' | 'error' | 'partial' | 'not_started'
            - missing_files: list - Liste des fichiers manquants
    """
    
    # Vérifier d'abord les logs
    log_status = log_status or {}
    if dept_code in log_status:
        log_info = log_status[dept_code]
        if log_info['status'] == 'success':
            # Marqué comme succès en log - chercher les fichiers
            required_files = {
                'mnt': f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
                'pente': f"PENTE_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
                'pente_gt5': f"PENTE_BINAIRE_GT5_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
                'pente_gt10': f"PENTE_BINAIRE_GT10_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
            }
            
            missing = []
            for file_type, file_name in required_files.items():
                # Chercher dans le nouveau batch
                file_path = os.path.join(dirs[file_type], file_name)
                
                # Si pas trouvé, chercher dans les anciens batch
                if not os.path.exists(file_path):
                    found = False
                    for item in os.listdir(DOWNLOADS_DIR):
                        item_path = os.path.join(DOWNLOADS_DIR, item)
                        if os.path.isdir(item_path) and ('MNT_BATCH' in item):
                            old_file_path = os.path.join(item_path, file_type, file_name)
                            if os.path.exists(old_file_path):
                                found = True
                                break
                    if not found:
                        missing.append(file_type)
                
            if len(missing) == 0:
                # Tout bon!
                return True, 'success', missing
            else:
                # Marqué comme succès en log mais fichiers manquants = problème
                return False, 'partial', missing
        
        elif log_info['status'] == 'error':
            # Erreur en log
            return False, 'error', [log_info['error_msg']]
    
    # Pas dans les logs = not_started
    # Vérifier quand même les fichiers (nouveau + anciens batch)
    required_files = {
        'mnt': f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
        'pente': f"PENTE_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
        'pente_gt5': f"PENTE_BINAIRE_GT5_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
        'pente_gt10': f"PENTE_BINAIRE_GT10_D{dept_code}_{dept_name.replace(' ', '_')}.tif",
    }
    
    missing = []
    for file_type, file_name in required_files.items():
        # Chercher dans le nouveau batch
        file_path = os.path.join(dirs[file_type], file_name)
        
        # Si pas trouvé, chercher dans les anciens batch
        if not os.path.exists(file_path):
            found = False
            try:
                for item in os.listdir(DOWNLOADS_DIR):
                    item_path = os.path.join(DOWNLOADS_DIR, item)
                    if os.path.isdir(item_path) and ('MNT_BATCH' in item):
                        old_file_path = os.path.join(item_path, file_type, file_name)
                        if os.path.exists(old_file_path):
                            found = True
                            break
            except:
                pass
            
            if not found:
                missing.append(file_type)
    
    if len(missing) == 0:
        return True, 'success', missing
    else:
        return False, 'not_started', missing

# Charger les départements
departments = load_departments()

if departments is None:
    st.stop()

st.divider()

# Mode de traitement
st.subheader("🚀 Sélectionner le mode de traitement")

mode = st.radio(
    "Mode:",
    options=[
        "📍 Mode simple (1 département)", 
        "🔄 Mode batch (tous les départements)"
    ],
    horizontal=True
)

st.divider()

# Colonnes pour l'interface
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📍 Sélectionner un département")
    
    # Créer une liste lisible
    dept_options = [f"{row['DEP_CODE']} - {row['DEP_LIB']}" for _, row in departments.iterrows()]
    selected_option = st.selectbox("Département:", dept_options)
    
    # Récupérer les données du département sélectionné
    selected_idx = dept_options.index(selected_option)
    selected_dept = departments.iloc[selected_idx]

with col2:
    st.subheader("ℹ️ Informations")
    
    info_html = f"""
    <div class="info-box">
        <strong>Code:</strong> {selected_dept['DEP_CODE']}<br>
        <strong>Département:</strong> {selected_dept['DEP_LIB']}<br>
        <strong>URL source:</strong> {selected_dept['URL'][:60]}...<br>
    </div>
    """
    st.markdown(info_html, unsafe_allow_html=True)

# Afficher le contenu selon le mode sélectionné
if "Mode batch" in mode:
    st.divider()
    st.subheader("🔄 TRAITEMENT BATCH - TOUS LES DÉPARTEMENTS")
    st.write("Cette section va télécharger et traiter les MNT de TOUS les départements.")
    st.write("Les résultats seront organisés dans: `MNT_BATCH_RESULTS/`")
    
    # Les étapes du batch processing seront ajoutées ici
    st.info("⏳ Section en construction - les étapes du batch processing seront exécutées ici")
    
    # Afficher les options de batch processing
    if BATCH_PROCESSOR_AVAILABLE:
        st.subheader("⚙️ Configuration du batch")
        
        col_config1, col_config2 = st.columns(2)
        
        with col_config1:
            # Sélection du range de départements
            dept_options_list = [f"{row['DEP_CODE']} - {row['DEP_LIB']}" for _, row in departments.iterrows()]
            min_dept = st.number_input("Depuis le département (index):", min_value=0, max_value=len(departments)-1, value=0)
            max_dept = st.number_input("Jusqu'au département (index):", min_value=0, max_value=len(departments)-1, value=len(departments)-1)
        
        with col_config2:
            st.write(f"**Sélection:** {max_dept - min_dept + 1} département(s)")
            st.write(f"- De: {dept_options_list[min_dept]}")
            st.write(f"- À: {dept_options_list[max_dept]}")
        
        # Bouton de lancement
        col_btn_batch = st.columns(1)[0]
        with col_btn_batch:
            start_batch = st.button(
                "🚀 LANCER LE BATCH PROCESSING",
                key="start_batch",
                type="primary",
                use_container_width=True
            )
        
        if start_batch:
            # Préparer les données
            selected_depts = departments.iloc[min_dept:max_dept+1]
            
            st.warning(f"⏳ Traitement de {len(selected_depts)} département(s)... Cette opération peut prendre plusieurs heures.")
            
            # Créer les répertoires de sortie
            dirs = create_batch_directories()
            st.success(f"📁 Répertoires créés dans: `{dirs['base']}`")
            
            # Initialiser le batch processor
            gdaldem_to_use = st.session_state.get('custom_gdaldem_path') or GDALDEM_PATH
            
            # Définir les wrappers pour le batch processor
            def batch_download(download_url, extract_base, dept_code, dept_name):
                """Wrapper pour le download dans le batch"""
                return download_and_extract_mnt(download_url, extract_base, dept_code, dept_name)
            
            def batch_vrt(asc_files, vrt_path):
                """Wrapper pour VRT sans UI Streamlit"""
                try:
                    # Lire les paramètres de chaque tuile
                    tile_data = []
                    min_x = min_y = float('inf')
                    max_x = max_y = float('-inf')
                    
                    for asc_file in asc_files:
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
                    
                    if not tile_data:
                        return {'success': False, 'message': 'Impossible de lire les en-têtes des fichiers ASC', 'validation': {}}
                    
                    # Créer le VRT
                    sample_params = tile_data[0][1]
                    ncols = sample_params.get('ncols', 5000)
                    nrows = sample_params.get('nrows', 5000)
                    cellsize = sample_params.get('cellsize', 5.0)
                    nodata_value = sample_params.get('nodata_value', -9999)
                    
                    total_width = int((max_x - min_x) / cellsize)
                    total_height = int((max_y - min_y) / cellsize)
                    
                    # Construire le contenu VRT
                    vrt_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<VRTDataset rasterXSize="{total_width}" rasterYSize="{total_height}">
  <SRS dataAxisToSrsAxisMapping="2,1">PROJCS["Lambert93",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Lambert_Conformal_Conic_2SP"],PARAMETER["standard_parallel_1",49],PARAMETER["standard_parallel_2",44],PARAMETER["latitude_of_origin",46.5],PARAMETER["central_meridian",3],PARAMETER["false_easting",700000],PARAMETER["false_northing",6600000],UNIT["Meter",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","2154"]]</SRS>
  <GeoTransform>{min_x}, {cellsize}, 0, {max_y}, 0, -{cellsize}</GeoTransform>
  <VRTRasterBand dataType="Float32" band="1">
    <NoDataValue>{nodata_value}</NoDataValue>
'''
                    
                    for asc_file, params in tile_data:
                        x_ll = params['xllcorner']
                        y_ll = params['yllcorner']
                        cs = params['cellsize']
                        cols = params['ncols']
                        rows = params['nrows']
                        
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
                    with open(vrt_path, 'w', encoding='utf-8') as f:
                        f.write(vrt_content)
                    
                    # Validation basique
                    vrt_validation = test_vrt_quality(vrt_path, asc_files) if os.path.exists(vrt_path) else {}
                    
                    return {
                        'success': os.path.exists(vrt_path),
                        'message': f"VRT créé avec {len(tile_data)} tuiles",
                        'validation': vrt_validation if isinstance(vrt_validation, dict) else {}
                    }
                except Exception as e:
                    return {'success': False, 'message': f"Erreur VRT: {str(e)}", 'validation': {}}
            
            def batch_tiff(vrt_path, output_dir, dept_code, dept_name, gdaldem_path):
                """Wrapper pour conversion TIFF dans le batch"""
                try:
                    result = convert_vrt_to_tiff(vrt_path, output_dir, dept_code, dept_name, gdaldem_path)
                    if isinstance(result, dict) and result.get('success'):
                        file_path = result.get('file_path')
                        file_size = os.path.getsize(file_path) / (1024*1024) if file_path and os.path.exists(file_path) else 0
                        return {
                            'success': True,
                            'message': 'TIFF converti',
                            'file_path': file_path,
                            'file_size': file_size
                        }
                    else:
                        return {'success': False, 'message': 'Conversion TIFF échouée', 'file_path': None, 'file_size': 0}
                except Exception as e:
                    return {'success': False, 'message': f"Erreur TIFF: {str(e)}", 'file_path': None, 'file_size': 0}
            
            def batch_slope(vrt_path, output_path, threshold, output_dir, dept_code, dept_name, gdaldem_path):
                """Wrapper pour calcul de pente dans le batch"""
                try:
                    result = calculate_and_export_slope_with_filter(vrt_path, threshold, output_dir, dept_code, dept_name, gdaldem_path)
                    if isinstance(result, dict) and result.get('success'):
                        file_path = result.get('file_path') or output_path
                        file_size = os.path.getsize(file_path) / (1024*1024) if file_path and os.path.exists(file_path) else 0
                        return {
                            'success': True,
                            'message': f"Pente calculée (threshold={threshold})",
                            'file_path': file_path,
                            'file_size': file_size
                        }
                    else:
                        return {'success': False, 'message': 'Calcul pente échoué', 'file_path': None, 'file_size': 0}
                except Exception as e:
                    return {'success': False, 'message': f"Erreur pente: {str(e)}", 'file_path': None, 'file_size': 0}
            
            def batch_verify(vrt_path, tiff_path):
                """Wrapper pour vérification dans le batch"""
                try:
                    result = deep_verify_conversion(vrt_path, tiff_path)
                    if isinstance(result, dict) and result.get('success'):
                        return {
                            'success': True,
                            'verification': result.get('verification', {
                                'comparison': {'pixels_match': True, 'max_difference': 0}
                            })
                        }
                    else:
                        return {'success': False, 'verification': {}}
                except Exception as e:
                    return {'success': False, 'verification': {}}
            
            # ÉTAPE 0: TROUVER ET LIRE LES LOGS PRÉCÉDENTS
            st.subheader("🔍 ÉTAPE 0: Lecture des logs précédents")
            st.write("Recherche du batch processing précédent...")
            old_logs_dir, batch_folder_name = find_previous_batch_logs()
            
            if old_logs_dir:
                st.success(f"✅ Logs trouvés dans: **{batch_folder_name}**")
                st.caption(f"📂 Chemin: `{old_logs_dir}`")
                log_status = read_batch_logs(old_logs_dir)
                st.info(f"📊 {len(log_status)} département(s) trouvé(s) dans les logs précédents")
                
                # Compter succès et erreurs
                success_count = sum(1 for v in log_status.values() if v['status'] == 'success')
                error_count = sum(1 for v in log_status.values() if v['status'] == 'error')
                st.write(f"  • ✅ **{success_count} succès**")
                st.write(f"  • ❌ **{error_count} erreurs** (à retenter)")
            else:
                st.warning("⚠️ Aucun batch processing précédent trouvé - démarrage à 0")
                log_status = {}
            
            st.divider()
            
            # ÉTAPE 1: VÉRIFICATION DE COMPLÉTION DES DÉPARTEMENTS
            st.subheader("🔍 ÉTAPE 1: Classification des départements")
            st.write("Analyse de l'état de chaque département...")
            
            success_list = []
            error_list = []
            to_process_list = []
            summary_area = st.empty()
            
            for _, dept in selected_depts.iterrows():
                dept_code = dept['DEP_CODE']
                dept_name = dept['DEP_LIB']
                is_complete, status, missing = check_department_completion(dept_code, dept_name, dirs, log_status)
                
                if status == 'success' and is_complete:
                    # ✅ Complètement traité
                    success_list.append({
                        'dept_code': dept_code,
                        'dept_name': dept_name,
                        'status': 'success'
                    })
                elif status == 'error':
                    # ❌ En erreur - à retrier
                    error_list.append({
                        'dept_code': dept_code,
                        'dept_name': dept_name,
                        'error': missing[0] if missing else 'Erreur inconnue'
                    })
                else:
                    # ⏳ Pas encore traité ou partiellement traité
                    to_process_list.append({
                        'dept_code': dept_code,
                        'dept_name': dept_name,
                        'missing': missing,
                        'status': status
                    })
            
            # Afficher le résumé
            with summary_area.container():
                col_s1, col_s2, col_s3 = st.columns(3)
                
                with col_s1:
                    st.success(f"✅ **Complètement réussis:** {len(success_list)}")
                    if success_list:
                        st.caption(f"Ces {len(success_list)} département(s) seront **ignorés** (déjà traités):")
                        for item in success_list[:5]:
                            st.write(f"  • {item['dept_code']} - {item['dept_name']}")
                        if len(success_list) > 5:
                            st.write(f"  ... et {len(success_list) - 5} autres")
                
                with col_s2:
                    st.error(f"❌ **En erreur:** {len(error_list)}")
                    if error_list:
                        st.caption(f"Ces {len(error_list)} département(s) seront **retentés** en priorité 🔄:")
                        for item in error_list[:5]:
                            st.write(f"  • {item['dept_code']} - {item['dept_name']}")
                        if len(error_list) > 5:
                            st.write(f"  ... et {len(error_list) - 5} autres")
                
                with col_s3:
                    st.warning(f"⏳ **À traiter (nouveaux):** {len(to_process_list)}")
                    if to_process_list:
                        st.caption(f"Ces {len(to_process_list)} département(s) n'ont **jamais été traités**:")
                        for item in to_process_list[:5]:
                            st.write(f"  • {item['dept_code']} - {item['dept_name']}")
                        if len(to_process_list) > 5:
                            st.write(f"  ... et {len(to_process_list) - 5} autres")
            
            st.divider()
            
            # CRÉER LE PROCESSOR MAINTENANT (après avoir lu les anciens logs)
            processor = BatchProcessor(
                dirs['base'], 
                gdaldem_to_use,
                download_func=batch_download,
                vrt_func=batch_vrt,
                tiff_func=batch_tiff,
                slope_func=batch_slope,
                verify_func=batch_verify,
                reuse_existing_log=True  # Continuer le log existant au lieu d'en créer un nouveau
            )
            
            st.info(f"📂 Fichier log utilisé: `{os.path.basename(processor.log_file)}`")
            
            # ÉTAPE 2: TRAITEMENT DES DÉPARTEMENTS À FAIRE
            all_to_do = error_list + to_process_list  # Retrier d'abord les en erreur
            
            if len(all_to_do) == 0:
                st.success("🎉 Tous les départements sélectionnés ont déjà été traités avec succès! Aucun traitement nécessaire.")
            else:
                st.subheader(f"📊 ÉTAPE 2: Traitement des {len(all_to_do)} département(s) à faire")
                st.info(f"ℹ️ Priorités: {len(error_list)} en erreur → retentées | {len(to_process_list)} non traités → premiers traitements")
                st.warning(f"⏳ Traitement de {len(all_to_do)} département(s)... Cette opération peut prendre plusieurs heures.")
                
                # Afficher la progression
                progress_container = st.container()
                status_container = st.container()
                
                with progress_container:
                    progress_bar = st.progress(0)
                    progress_text = st.empty()
                
                with status_container:
                    st.subheader("📍 Progression du traitement")
                    status_area = st.empty()
                
                # Boucle de traitement batch SEULEMENT LES À FAIRE
                results_list = []
                errors_summary = []
                
                for idx, item in enumerate(all_to_do):
                    dept_code = item['dept_code']
                    dept_name = item['dept_name']
                    item_status = item.get('status', 'not_started')
                    
                    # Trouver la ligne du département dans le dataframe original
                    dept_row = departments[departments['DEP_CODE'] == dept_code].iloc[0]
                    dept_url = dept_row['URL']
                    
                    # Calcul de la progression globale
                    overall_progress = int(5 + (idx / len(all_to_do)) * 85)
                    progress_bar.progress(overall_progress)
                    
                    # Mise à jour du texte de progression - indiquer si c'est une retry
                    retry_indicator = "🔄 (retry)" if dept_code in [e['dept_code'] for e in error_list] else ""
                    progress_text.text(f"📍 Département {idx+1}/{len(all_to_do)}: {dept_code} - {dept_name} {retry_indicator}")
                    
                    try:
                        # Appeler le traitement du département
                        result = processor.process_department(
                            dept_code,
                            dept_name,
                            dept_url,
                            WORK_DIR,
                            progress_callback=lambda msg, pct: progress_text.text(f"📍 {dept_code} - {dept_name}\n{msg}")
                        )
                        
                        results_list.append(result)
                        
                        # Afficher le résultat du département
                        if result['status'] == 'success':
                            status_area.success(f"✅ {dept_code}: {result.get('file_count', 0)} fichiers générés")
                        elif result['status'] == 'partial':
                            status_area.warning(f"⚠️ {dept_code}: Traitement partiel - {result.get('errors', [])}")
                        else:
                            status_area.error(f"❌ {dept_code}: {result.get('error_message', 'Erreur inconnue')}")
                            errors_summary.append({'dept': f"{dept_code} - {dept_name}", 'error': result.get('error_message', 'Erreur inconnue')})
                    
                    except Exception as e:
                        st.error(f"❌ Erreur pour {dept_code}: {str(e)}")
                        errors_summary.append({'dept': f"{dept_code} - {dept_name}", 'error': str(e)})
                        results_list.append({'dept_code': dept_code, 'status': 'failed', 'error_message': str(e)})
                
                # Marquer comme terminé
                progress_bar.progress(100)
                progress_text.text("✅ Traitement TERMINÉ!")
                
                st.divider()
            
            # ÉTAPE 3: RAPPORT FINAL
            st.subheader("📊 RAPPORT FINAL DU BATCH PROCESSING")
            
            # Compter les statuts
            total_processed = len(all_to_do)
            success_count = sum(1 for r in results_list if r.get('status') == 'success') if results_list else 0
            partial_count = sum(1 for r in results_list if r.get('status') == 'partial') if results_list else 0
            failed_count = sum(1 for r in results_list if r.get('status') == 'failed') if results_list else 0
            retry_count = len(error_list)
            
            col_r1, col_r2, col_r3, col_r4, col_r5, col_r6 = st.columns(6)
            with col_r1:
                st.metric("✅ Succès antérieurs", len(success_list))
            with col_r2:
                st.metric("🔄 Retentés", retry_count)
            with col_r3:
                st.metric("📊 Traité maintenant", total_processed)
            with col_r4:
                st.metric("✅ Réussis", success_count)
            with col_r5:
                st.metric("⚠️ Partiels", partial_count)
            with col_r6:
                st.metric("❌ Erreurs", failed_count)
            
            # Afficher les résultats détaillés (seulement les nouveaux traitements)
            if results_list:
                st.write("**Détail des résultats (de ce batch):**")
                results_details = []
                for r in results_list:
                    results_details.append({
                        'Département': r.get('dept_code', 'N/A'),
                        'Statut': r.get('status', 'unknown'),
                        'Fichiers': r.get('file_count', 0),
                        'Taille (MB)': round(r.get('total_size_mb', 0), 2),
                        'Erreurs': len(r.get('errors', []))
                    })
                
                results_df = pd.DataFrame(results_details)
                st.dataframe(results_df, use_container_width=True)
            
            # Afficher les erreurs détaillées si présentes
            if errors_summary:
                st.divider()
                st.warning("⚠️ ERREURS RENCONTRÉES DANS CE BATCH:")
                for err in errors_summary:
                    st.error(f"**{err['dept']}**: {err['error']}")
            
            # Information sur les fichiers générés
            st.divider()
            st.success(f"📁 **Tous les fichiers ont été sauvegardés dans:** `{dirs['base']}`")
            st.write("""
            **Structure des résultats:**
            - `MNT/` - Fichiers TIFF des modèles numériques de terrain
            - `PENTE/` - Fichiers de pente (%) complets
            - `PENTE_SUP5/` - Rasters binaires (pente > 5%)
            - `PENTE_SUP10/` - Rasters binaires (pente > 10%)
            - `LOGS/` - Fichiers de validation et logs
            """)
            
    else:
        st.warning("⚠️ Le module batch_processor n'est pas disponible. Assurez-vous que batch_processor.py est présent.")

st.divider()

# MODE SIMPLE - Afficher seulement en mode simple
if "Mode simple" in mode:
    # Section de traitement
    col_process, col_empty = st.columns([1, 2])

    with col_process:
        process_button = st.button("🚀 Générer MNT VRT", key="process", type="primary", use_container_width=True)

    if process_button:
        # Stocker les données dans la session
        st.session_state.dept_code = selected_dept['DEP_CODE']
        st.session_state.dept_name = selected_dept['DEP_LIB']
        st.session_state.download_url = selected_dept['URL']
        st.session_state.processing = True

    # Si un traitement est en cours, continuer
    if st.session_state.get('processing', False):
        dept_code = st.session_state.dept_code
        dept_name = st.session_state.dept_name
        download_url = st.session_state.download_url
        
        # Créer un conteneur pour les étapes
        with st.spinner("⏳ Processus en cours..."):
            
            # Étape 1-2: Téléchargement + Extraction (AMÉLIORÉ)
            st.subheader("📥 Étape 1: Téléchargement")
            st.subheader("📦 Étape 2: Extraction")
            
            # Utiliser la fonction améliorée avec validation et retries
            download_result = download_and_extract_mnt(download_url, WORK_DIR, dept_code, dept_name)
            
            if not download_result.get('success'):
                st.error(f"❌ Erreur: {download_result.get('message', 'Erreur inconnue')}")
                st.session_state.processing = False
                st.stop()
            
            st.success(f"✅ Téléchargement et extraction terminés")
            st.info(f"✅ {download_result.get('files_count', 0)} fichiers ASC trouvés")
            
            extract_dir = download_result.get('extract_dir', '')
            
            # Étape 3: Rechercher les fichiers ASC
            st.subheader("🔍 Étape 3: Recherche des fichiers ASC")
            
            # Chercher les fichiers ASC récursivement
            asc_pattern = os.path.join(extract_dir, "**", "*.asc")
            asc_files = sorted(glob.glob(asc_pattern, recursive=True))
            
            if asc_files:
                st.success(f"✅ {len(asc_files)} fichiers ASC trouvés")
            else:
                st.error("❌ Aucun fichier ASC trouvé!")
                st.session_state.processing = False
                st.stop()
            
            # Stocker les fichiers ASC dans la session
            st.session_state.asc_files = asc_files
            st.session_state.extract_dir = extract_dir
            
            # Étape 4: Créer le VRT
            st.subheader("🗺️ Étape 4: Création du VRT")
            
            vrt_path = os.path.join(DOWNLOADS_DIR, f"MNT_D{st.session_state.dept_code}_{st.session_state.dept_name.replace(' ', '_')}.vrt")
            
            result = create_vrt(st.session_state.asc_files, vrt_path)
            
            if result and result.get('success'):
                # Stocker le chemin VRT dans la session
                st.session_state.vrt_path = vrt_path
                
                st.markdown(f"""
                <div class="success-box">
                <strong>✅ VRT créé avec succès!</strong><br><br>
                📊 <strong>Statistiques:</strong><br>
                • Tuiles fusionnées: {result['tiles']}<br>
                • Résolution: {result['width']} × {result['height']} pixels<br>
                • Étendue: {result['extent_x']:.0f} m × {result['extent_y']:.0f} m<br>
                • Taille cellule: {result['cellsize']} m<br>
                • Projection: Lambert93 (EPSG:2154)<br>
                </div>
                """, unsafe_allow_html=True)
                
                # Tester la qualité du VRT
                st.subheader("🔍 Étape 5: Test de validation VRT")
                
                with st.spinner("🧪 Tests en cours..."):
                    test_result = test_vrt_quality(vrt_path, st.session_state.asc_files)
                
                # Afficher les résultats des tests
                if test_result['success']:
                    st.markdown("""
                    <div class="success-box">
                    <strong>✅ TOUS LES TESTS PASSÉS - VRT VALIDE!</strong><br>
                    Le fichier VRT représente exactement les données des tuiles ASC.
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                    <div style="background-color: #fff3cd; border-left: 5px solid #ffc107; padding: 15px; border-radius: 5px; margin: 10px 0;">
                    <strong>⚠️ ATTENTION - Les tests ont détecté des anomalies</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Afficher les checks
                if test_result['checks']:
                    st.write("**Vérifications réussies:**")
                    for check in test_result['checks']:
                        st.write(f"  {check}")
                
                # Afficher les issues
                if test_result['issues']:
                    st.write("**⚠️ Problèmes détectés:**")
                    for issue in test_result['issues']:
                        st.error(f"  • {issue}")
                
                st.divider()
                
                # Afficher le fichier VRT à télécharger
                file_size = os.path.getsize(vrt_path) / 1024
                st.info(f"📁 Fichier VRT: **{os.path.basename(vrt_path)}** ({file_size:.1f} KB)")
                
                # Bouton de téléchargement
                with open(vrt_path, 'r', encoding='utf-8') as f:
                    vrt_content_download = f.read()
                
                st.download_button(
                    label="⬇️ Télécharger le fichier VRT",
                    data=vrt_content_download,
                    file_name=os.path.basename(vrt_path),
                    mime="application/xml",
                    use_container_width=True
                )
            else:
                st.error("❌ Erreur lors de la création du VRT")
                st.session_state.processing = False

# Afficher le bouton Calculer la pente si un VRT existe
if 'vrt_path' in st.session_state:
    st.divider()
    st.subheader("⛰️ Étape 6: Calcul et export des pentes filtrées")
    
    st.write("Générez directement les rasters de pentes avec filtres:")
    
    # Afficher un avertissement si gdaldem n'est pas disponible
    gdaldem_to_use = st.session_state.get('custom_gdaldem_path') or GDALDEM_PATH
    gdaldem_available = gdaldem_to_use is not None
    
    if not gdaldem_available:
        st.error("""
        ❌ **gdaldem non trouvé**
        
        Pour calculer la pente, configurez le chemin vers gdaldem dans la barre latérale (⚙️ Configuration GDAL)
        """)
    else:
        col_btn5, col_btn10 = st.columns(2)
        
        with col_btn5:
            btn_gt5 = st.button("📊 Pentes > 5% (TIFF)", key="btn_slope_gt5_export", use_container_width=True)
        
        with col_btn10:
            btn_gt10 = st.button("📊 Pentes > 10% (TIFF)", key="btn_slope_gt10_export", use_container_width=True)
        
        # Traiter pentes > 5%
        if btn_gt5:
            with st.spinner("⏳ Calcul de pentes > 5% et export en TIFF..."):
                vrt_path = st.session_state.vrt_path
                dept_code = st.session_state.dept_code
                dept_name = st.session_state.dept_name
                
                result = calculate_and_export_slope_with_filter(
                    vrt_path,
                    threshold=5.0,
                    output_dir=DOWNLOADS_DIR,
                    dept_code=dept_code,
                    dept_name=dept_name,
                    gdaldem_path=gdaldem_to_use
                )
            
            if result['success']:
                st.markdown(f"""
                <div class="success-box">
                <strong>✅ Calcul terminé!</strong><br><br>
                📊 <strong>Statistiques (zones > 5%):</strong><br>
                • Pixels au-dessus du seuil: {result['stats']['count']:,}<br>
                • Couverture: {result['stats']['percent']:.2f}% du département<br>
                • Pente moyenne (complète): {result['stats']['mean']:.2f}%<br>
                • Pente max: {result['stats']['max']:.2f}%<br>
                </div>
                """, unsafe_allow_html=True)
                
                # Afficher les deux fichiers à télécharger
                st.subheader("📥 Télécharger les fichiers")
                
                col_complete, col_binary = st.columns(2)
                
                with col_complete:
                    st.write("**📋 Pente complète (valeurs en %)**")
                    with open(result['pente_complete'], 'rb') as f:
                        st.download_button(
                            label="⬇️ PENTE complète",
                            data=f.read(),
                            file_name=os.path.basename(result['pente_complete']),
                            mime="image/tiff",
                            use_container_width=True,
                            key="download_complete_5"
                        )
                
                with col_binary:
                    st.write("**🔲 Binaire > 5% (1=oui, 0=non)**")
                    with open(result['file_path'], 'rb') as f:
                        st.download_button(
                            label="⬇️ Binaire > 5%",
                            data=f.read(),
                            file_name=os.path.basename(result['file_path']),
                            mime="image/tiff",
                            use_container_width=True,
                            key="download_binary_5"
                        )
            else:
                st.error(f"❌ Erreur: {result['message']}")
        
        # Traiter pentes > 10%
        if btn_gt10:
            with st.spinner("⏳ Calcul de pentes > 10% et export en TIFF..."):
                vrt_path = st.session_state.vrt_path
                dept_code = st.session_state.dept_code
                dept_name = st.session_state.dept_name
                
                result = calculate_and_export_slope_with_filter(
                    vrt_path,
                    threshold=10.0,
                    output_dir=DOWNLOADS_DIR,
                    dept_code=dept_code,
                    dept_name=dept_name,
                    gdaldem_path=gdaldem_to_use
                )
            
            if result['success']:
                st.markdown(f"""
                <div class="success-box">
                <strong>✅ Calcul terminé!</strong><br><br>
                📊 <strong>Statistiques (zones > 10%):</strong><br>
                • Pixels au-dessus du seuil: {result['stats']['count']:,}<br>
                • Couverture: {result['stats']['percent']:.2f}% du département<br>
                • Pente moyenne (complète): {result['stats']['mean']:.2f}%<br>
                • Pente max: {result['stats']['max']:.2f}%<br>
                </div>
                """, unsafe_allow_html=True)
                
                # Afficher les deux fichiers à télécharger
                st.subheader("📥 Télécharger les fichiers")
                
                col_complete, col_binary = st.columns(2)
                
                with col_complete:
                    st.write("**📋 Pente complète (valeurs en %)**")
                    with open(result['pente_complete'], 'rb') as f:
                        st.download_button(
                            label="⬇️ PENTE complète",
                            data=f.read(),
                            file_name=os.path.basename(result['pente_complete']),
                            mime="image/tiff",
                            use_container_width=True,
                            key="download_complete_10"
                        )
                
                with col_binary:
                    st.write("**🔲 Binaire > 10% (1=oui, 0=non)**")
                    with open(result['file_path'], 'rb') as f:
                        st.download_button(
                            label="⬇️ Binaire > 10%",
                            data=f.read(),
                            file_name=os.path.basename(result['file_path']),
                            mime="image/tiff",
                            use_container_width=True,
                            key="download_binary_10"
                        )
            else:
                st.error(f"❌ Erreur: {result['message']}")
