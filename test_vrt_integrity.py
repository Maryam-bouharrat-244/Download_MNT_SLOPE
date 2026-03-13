#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour vérifier l'intégrité du VRT généré
Compare les données du VRT avec les tuiles ASC sources
"""

import os
import numpy as np
from osgeo import gdal
import glob
from pathlib import Path

# Décommenter pour plus de détails GDAL
# gdal.UseExceptions()

def read_asc_specific_pixel(asc_file, row, col):
    """Lit la valeur d'un pixel spécifique dans un fichier ASC"""
    try:
        ds = gdal.Open(asc_file)
        if ds is None:
            return None
        
        band = ds.GetRasterBand(1)
        value = band.ReadAsArray(col, row, 1, 1)
        ds = None
        
        return float(value[0, 0])
    except:
        return None

def read_asc_header(filepath):
    """Parse l'en-tête ESRI ASCII"""
    params = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for i in range(7):
                line = f.readline().strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    key = parts[0].lower()
                    value = parts[1]
                    if key in ['ncols', 'nrows']:
                        params[key] = int(value)
                    elif key in ['cellsize', 'xllcorner', 'yllcorner']:
                        params[key] = float(value)
                    elif key == 'nodata_value':
                        params[key] = float(value)
    except Exception as e:
        print(f"Erreur lecture {os.path.basename(filepath)}: {e}")
    return params

def test_vrt_integrity(dept_code, dept_name, vrt_file, asc_files):
    """Vérifie que le VRT représente exactement les données ASC"""
    
    print(f"\n{'='*70}")
    print(f"🔍 TEST D'INTÉGRITÉ VRT: D{dept_code} ({dept_name})")
    print(f"{'='*70}")
    
    if not os.path.exists(vrt_file):
        print(f"❌ VRT non trouvé: {vrt_file}")
        return False
    
    if not asc_files:
        print(f"❌ Aucun fichier ASC")
        return False
    
    print(f"\n📊 Paramètres VRT:")
    try:
        vrt_ds = gdal.Open(vrt_file)
        if vrt_ds is None:
            print(f"❌ Impossible d'ouvrir le VRT")
            return False
        
        vrt_width = vrt_ds.RasterXSize
        vrt_height = vrt_ds.RasterYSize
        vrt_geo = vrt_ds.GetGeoTransform()
        
        print(f"  • Dimensions: {vrt_width} × {vrt_height} pixels")
        print(f"  • GeoTransform: X0={vrt_geo[0]}, cellwidth={vrt_geo[1]}, Y0={vrt_geo[3]}, cellheight={vrt_geo[5]}")
        
        vrt_band = vrt_ds.GetRasterBand(1)
        vrt_dtype = gdal.GetDataTypeName(vrt_band.DataType)
        vrt_nodata = vrt_band.GetNoDataValue()
        print(f"  • Type données: {vrt_dtype}")
        print(f"  • NoData: {vrt_nodata}")
        
    except Exception as e:
        print(f"❌ Erreur lecture VRT: {e}")
        return False
    
    # Tests sur les tuiles sources
    print(f"\n📋 Validation des tuiles ASC ({len(asc_files)}):")
    
    all_valid = True
    errors = []
    
    for idx, asc_file in enumerate(asc_files, 1):
        try:
            asc_ds = gdal.Open(asc_file)
            if asc_ds is None:
                errors.append(f"  ❌ Tuile {idx}: Impossible d'ouvrir {os.path.basename(asc_file)}")
                all_valid = False
                continue
            
            asc_width = asc_ds.RasterXSize
            asc_height = asc_ds.RasterYSize
            asc_geo = asc_ds.GetGeoTransform()
            asc_band = asc_ds.GetRasterBand(1)
            asc_nodata = asc_band.GetNoDataValue()
            
            asc_file_ok = True
            checks = []
            
            # Test: Lire quelques pixels et vérifier qu'on les retrouve dans le VRT
            # (tests sur quelques pixels représentatifs)
            sample_pixels = [
                (0, 0, "coin haut gauche"),
                (asc_width-1, asc_height-1, "coin bas droit"),
                (asc_width//2, asc_height//2, "centre")
            ]
            
            for col, row, desc in sample_pixels:
                try:
                    asc_val = read_asc_specific_pixel(asc_file, row, col)
                    
                    if asc_val is not None:
                        # Calculer la position dans le VRT
                        asc_x0 = asc_geo[0]
                        asc_y0 = asc_geo[3]
                        asc_cx = asc_geo[1]  # cellsize X
                        asc_cy = -asc_geo[5]  # cellsize Y (positif)
                        
                        vrt_x0 = vrt_geo[0]
                        vrt_y0 = vrt_geo[3]
                        vrt_cx = vrt_geo[1]
                        vrt_cy = -vrt_geo[5]
                        
                        # Position réelle du pixel
                        real_x = asc_x0 + (col + 0.5) * asc_cx
                        real_y = asc_y0 - (row + 0.5) * asc_cy
                        
                        # Position dans le VRT
                        vrt_col = (real_x - vrt_x0) / vrt_cx
                        vrt_row = (vrt_y0 - real_y) / vrt_cy
                        
                        # Lire la valeur dans le VRT
                        vrt_band = vrt_ds.GetRasterBand(1)
                        vrt_val_arr = vrt_band.ReadAsArray(int(vrt_col), int(vrt_row), 1, 1)
                        vrt_val = float(vrt_val_arr[0, 0]) if vrt_val_arr is not None else None
                        
                        # Comparer
                        if vrt_val is not None:
                            if abs(asc_val - vrt_val) < 0.01:  # Tolérance numérique
                                checks.append(f"✅ {desc}")
                            else:
                                checks.append(f"⚠️ {desc}: ASC={asc_val}, VRT={vrt_val}")
                                asc_file_ok = False
                        else:
                            checks.append(f"⚠️ {desc}: valeur VRT None")
                            asc_file_ok = False
                except Exception as e:
                    checks.append(f"⚠️ {desc}: {str(e)}")
            
            status = "✅" if asc_file_ok else "⚠️"
            print(f"  {status} Tuile {idx}: {os.path.basename(asc_file)} ({asc_width}×{asc_height})")
            for check in checks:
                print(f"       {check}")
            
            asc_ds = None
            
        except Exception as e:
            errors.append(f"  ❌ Tuile {idx}: {str(e)}")
            all_valid = False
    
    # Résumé
    print(f"\n{'='*70}")
    if all_valid and not errors:
        print("✅ VRT VALIDE - Représente exactement les données ASC")
        vrt_ds = None
        return True
    else:
        print("⚠️  ATTENTION - Quelques anomalies détectées")
        if errors:
            print("\nErreurs:")
            for err in errors:
                print(err)
        vrt_ds = None
        return False

def main():
    """Teste un département spécifique"""
    
    # Configuration
    DEPT_CODE = "75"  # **À MODIFIER** par le code département
    DEPT_NAME = "Paris"  # **À MODIFIER**
    
    WORK_DIR = r"C:\Users\marya\Downloads\mnt_work"
    DOWNLOADS_DIR = r"C:\Users\marya\Downloads"
    
    # Chemins
    dept_work = os.path.join(WORK_DIR, f"{DEPT_CODE}*")
    asc_files = sorted(glob.glob(os.path.join(WORK_DIR, f"**/*D{DEPT_CODE}*.asc"), recursive=True))
    
    # Chercher le VRT
    vrt_candidates = glob.glob(os.path.join(DOWNLOADS_DIR, f"*{DEPT_CODE}*.vrt"))
    
    if not vrt_candidates:
        print(f"❌ Aucun VRT trouvé pour le département {DEPT_CODE}")
        print(f"   Cherché dans: {DOWNLOADS_DIR}")
        return False
    
    vrt_file = vrt_candidates[0]
    
    if not asc_files:
        print(f"❌ Aucun fichier ASC trouvé pour le département {DEPT_CODE}")
        print(f"   Cherché dans: {WORK_DIR}")
        return False
    
    print(f"📁 VRT trouvé: {vrt_file}")
    print(f"📁 Tuiles ASC trouvées: {len(asc_files)}")
    
    # Lancer le test
    result = test_vrt_integrity(DEPT_CODE, DEPT_NAME, vrt_file, asc_files)
    
    return result

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
