#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de traitement batch pour tous les départements MNT
"""

import os
import subprocess
import shutil
from pathlib import Path
import logging
from datetime import datetime
import json
import time
import glob

def setup_logging(log_dir, reuse_existing_log=True):
    """
    Configure le logging pour le batch
    
    Args:
        log_dir: Répertoire des logs
        reuse_existing_log: Si True et qu'un log existe, l'ajouter au lieu d'en créer un nouveau
    """
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = None
    
    # Si on doit réutiliser un log existant, chercher le plus récent
    if reuse_existing_log:
        existing_logs = sorted(glob.glob(os.path.join(log_dir, "batch_processing_*.log")))
        if existing_logs:
            log_file = existing_logs[-1]  # Le plus récent
    
    # Si aucun log existant ou on ne veut pas le réutiliser, créer un nouveau
    if not log_file:
        log_file = os.path.join(log_dir, f"batch_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Utiliser UTF-8 pour les fichiers logs (supporte les emojis)
    # Mais éviter les emojis dans la sortie console (Windows cp1252)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ],
        force=True  # Pour réinitialiser le logging si déjà configuré
    )
    
    return logging.getLogger(__name__), log_file

class BatchProcessor:
    """Processeur batch pour tous les départements"""
    
    def __init__(self, batch_output_base, gdaldem_path, download_func=None, vrt_func=None, 
                 tiff_func=None, slope_func=None, compare_func=None, verify_func=None,
                 reuse_existing_log=True):
        self.batch_output_base = batch_output_base
        self.gdaldem_path = gdaldem_path
        self.results = []
        self.logger, self.log_file = setup_logging(os.path.join(batch_output_base, 'LOGS'), 
                                                     reuse_existing_log=reuse_existing_log)
        
        # Fonctions de traitement passées en paramètre
        self.download_func = download_func
        self.vrt_func = vrt_func
        self.tiff_func = tiff_func
        self.slope_func = slope_func
        self.compare_func = compare_func
        self.verify_func = verify_func
        
        # Répertoires de sortie
        self.dirs = {
            'mnt': os.path.join(batch_output_base, 'MNT'),
            'pente': os.path.join(batch_output_base, 'PENTE'),
            'pente_gt5': os.path.join(batch_output_base, 'PENTE_SUP5'),
            'pente_gt10': os.path.join(batch_output_base, 'PENTE_SUP10'),
        }
        
        # Créer les répertoires
        for dir_path in self.dirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def process_department(self, dept_code, dept_name, download_url, extract_base, progress_callback=None):
        """
        Traite un seul département avec toutes les étapes
        
        Returns:
            dict: Résultat du traitement avec statut et fichiers générés
        """
        
        result = {
            'code': dept_code,
            'name': dept_name,
            'status': 'processing',
            'files': {},
            'validations': {},
            'metrics': {
                'start_time': time.time(),
                'sizes': {}
            },
            'errors': []
        }
        
        try:
            # Étape 1: Télécharger
            if progress_callback:
                progress_callback(f"Download {dept_code}...", 10)
            
            extract_dir = os.path.join(extract_base, f"D{dept_code}_extracted")
            
            if self.download_func:
                download_result = self.download_func(download_url, extract_dir, dept_code, dept_name)
                if not download_result.get('success'):
                    raise Exception(f"Téléchargement échoué: {download_result.get('message', 'Erreur inconnue')}")
                result['metrics']['download_files'] = download_result.get('files_count', 0)
            
            # Étape 2: Créer le VRT
            if progress_callback:
                progress_callback(f"VRT {dept_code}...", 25)
            
            # Chercher les fichiers ASC récursivement (ils peuvent être dans RGEALTI/)
            asc_pattern = os.path.join(extract_dir, "**", "*.asc")
            asc_files = sorted(glob.glob(asc_pattern, recursive=True))
            if not asc_files:
                raise Exception(f"Aucun fichier ASC trouve dans {extract_dir}")
            
            vrt_path = os.path.join(extract_dir, f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.vrt")
            
            if self.vrt_func:
                vrt_result = self.vrt_func(asc_files, vrt_path)
                if not vrt_result.get('success'):
                    raise Exception(f"VRT échoué: {vrt_result.get('message', 'Erreur inconnue')}")
                result['validations']['vrt'] = vrt_result.get('validation', {})
            
            # Étape 3: Convertir en TIFF (MNT)
            if progress_callback:
                progress_callback(f"TIFF {dept_code}...", 40)
            
            tiff_output = os.path.join(self.dirs['mnt'], f"MNT_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
            
            if self.tiff_func:
                tiff_result = self.tiff_func(vrt_path, self.dirs['mnt'], dept_code, dept_name, self.gdaldem_path)
                if not tiff_result.get('success'):
                    raise Exception(f"Conversion TIFF échouée: {tiff_result.get('message', 'Erreur inconnue')}")
                
                tiff_output = tiff_result['file_path']
                result['files']['mnt'] = tiff_output
                result['metrics']['sizes']['mnt'] = tiff_result.get('file_size', 0)
                
                # Vérifier la conversion
                if self.verify_func and os.path.exists(vrt_path):
                    verify_result = self.verify_func(vrt_path, tiff_output)
                    if verify_result.get('success'):
                        result['validations']['conversion'] = {
                            'pixels_match': verify_result['verification']['comparison']['pixels_match'],
                            'max_difference': verify_result['verification']['comparison'].get('max_difference', 0)
                        }
            
            # Étape 4: Calculer la pente complète
            if progress_callback:
                progress_callback(f"Slope {dept_code}...", 55)
            
            pente_output = os.path.join(self.dirs['pente'], f"PENTE_D{dept_code}_{dept_name.replace(' ', '_')}.tif")
            
            if self.slope_func:
                slope_result = self.slope_func(vrt_path, pente_output, 0, self.dirs['pente'], dept_code, dept_name, self.gdaldem_path)
                if slope_result.get('success'):
                    result['files']['pente'] = pente_output
                    result['metrics']['sizes']['pente'] = slope_result.get('file_size', 0)
            
            # Étape 5: Générer binaires > 5% et > 10%
            if progress_callback:
                progress_callback(f"Binary filters {dept_code}...", 70)
            
            if self.slope_func:
                # > 5%
                slope_5_result = self.slope_func(vrt_path, None, 5.0, self.dirs['pente_gt5'], dept_code, dept_name, self.gdaldem_path)
                if slope_5_result.get('success'):
                    result['files']['pente_gt5'] = slope_5_result.get('file_path')
                    result['metrics']['sizes']['pente_gt5'] = slope_5_result.get('file_size', 0)
                
                # > 10%
                slope_10_result = self.slope_func(vrt_path, None, 10.0, self.dirs['pente_gt10'], dept_code, dept_name, self.gdaldem_path)
                if slope_10_result.get('success'):
                    result['files']['pente_gt10'] = slope_10_result.get('file_path')
                    result['metrics']['sizes']['pente_gt10'] = slope_10_result.get('file_size', 0)
            
            # Étape 6: Valider les fichiers
            if progress_callback:
                progress_callback(f"Validation {dept_code}...", 90)
            
            for file_type, file_path in result['files'].items():
                if os.path.exists(file_path):
                    result['validations'][f'{file_type}_exists'] = True
                    result['metrics']['sizes'][file_type] = os.path.getsize(file_path) / (1024*1024)
                else:
                    result['errors'].append(f"{file_type} fichier non trouvé")
            
            result['status'] = 'success' if not result['errors'] else 'partial'
            result['metrics']['duration'] = time.time() - result['metrics']['start_time']
            
            self.logger.info(f"[OK] {dept_code} - {dept_name}: {result['status']}")
            
        except Exception as e:
            result['status'] = 'failed'
            result['errors'].append(str(e))
            self.logger.error(f"[ERROR] {dept_code} - Erreur: {str(e)}")
        
        # Ajouter à la liste des résultats
        self.results.append(result)
        return result
    
    def generate_report(self):
        """Génère un rapport de synthèse"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total': len(self.results),
            'success': sum(1 for r in self.results if r['status'] == 'success'),
            'partial': sum(1 for r in self.results if r['status'] == 'partial'),
            'failed': sum(1 for r in self.results if r['status'] == 'failed'),
            'results': self.results,
            'log_file': self.log_file
        }
        
        # Sauvegarder aussi en JSON
        json_path = os.path.join(os.path.dirname(self.log_file), 'batch_report.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        report['json_file'] = json_path
        
        return report

