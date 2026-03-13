#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare les fichiers MNT téléchargés avec la liste des départements
Identifie quels départements manquent encore
"""

import os
import re
import pandas as pd
from pathlib import Path

# Chemins
MNT_DIR = r"C:\Users\marya\Downloads\MNT_BATCH_RESULTS\MNT"
CSV_FILE = r"C:\Users\marya\Downloads\projet test\deps.csv"

def extract_dept_code_from_filename(filename):
    """
    Extrait le code département du nom du fichier MNT
    Exemples:
    - MNT_D1_Ain.tif → '1'
    - MNT_D2A_Corse-du-Sud.tif → '2A'
    - MNT_D971_Guadeloupe.tif → '971'
    """
    # Pattern: MNT_D{code}_...
    match = re.match(r'MNT_D(\d+[AB]?|\d{3})', filename)
    if match:
        return match.group(1)
    return None

def sort_dept_codes(code):
    """Fonction de tri pour les codes département"""
    code_str = str(code)
    if code_str == '2A':
        return (2.1, code_str)
    elif code_str == '2B':
        return (2.2, code_str)
    else:
        return (int(code_str), code_str)

def main():
    print("=" * 80)
    print("🔍 ANALYSE DES DÉPARTEMENTS MANQUANTS")
    print("=" * 80)
    
    # 1. Lister les fichiers MNT présents
    if not os.path.exists(MNT_DIR):
        print(f"❌ Dossier MNT non trouvé: {MNT_DIR}")
        return
    
    mnt_files = [f for f in os.listdir(MNT_DIR) if f.endswith('.tif')]
    print(f"\n📂 Fichiers MNT trouvés: {len(mnt_files)}")
    
    # Extraire les codes des départements téléchargés
    downloaded_codes = set()
    for filename in mnt_files:
        code = extract_dept_code_from_filename(filename)
        if code:
            downloaded_codes.add(code)
    
    print(f"✅ Codes départements téléchargés: {len(downloaded_codes)}")
    sorted_downloaded = sorted(downloaded_codes, key=sort_dept_codes)
    print(f"   {sorted_downloaded}")
    
    # 2. Charger le CSV des départements
    if not os.path.exists(CSV_FILE):
        print(f"❌ Fichier CSV non trouvé: {CSV_FILE}")
        return
    
    df = pd.read_csv(CSV_FILE, sep=';')
    all_dept_codes = set(df['DEP_CODE'].astype(str))
    
    print(f"\n📋 Départements dans deps.csv: {len(all_dept_codes)}")
    sorted_all = sorted(all_dept_codes, key=sort_dept_codes)
    print(f"   {sorted_all}")
    
    # 3. Identifier les manquants
    missing_codes = all_dept_codes - downloaded_codes
    
    print(f"\n" + "=" * 80)
    print(f"❌ DÉPARTEMENTS MANQUANTS: {len(missing_codes)}")
    print("=" * 80)
    
    if missing_codes:
        # Trier les codes manquants
        sorted_missing = sorted(missing_codes, key=sort_dept_codes)
        
        for code in sorted_missing:
            # Trouver le nom du département dans le CSV
            dept_info = df[df['DEP_CODE'] == code]
            if not dept_info.empty:
                dept_name = dept_info.iloc[0]['DEP_LIB']
                print(f"  • D{code.ljust(3)} - {dept_name}")
            else:
                print(f"  • D{code.ljust(3)} - (nom non trouvé)")
    else:
        print("✅ Aucun département manquant! Tous les fichiers MNT ont été téléchargés.")
    
    # 4. Résumé
    print(f"\n" + "=" * 80)
    print("📊 RÉSUMÉ")
    print("=" * 80)
    print(f"  Total départements attendus: {len(all_dept_codes)}")
    print(f"  Départements téléchargés: {len(downloaded_codes)}")
    print(f"  Départements manquants: {len(missing_codes)}")
    print(f"  Pourcentage complètement: {(len(downloaded_codes)/len(all_dept_codes)*100):.1f}%")
    
    # 5. Codes manquants en format list pour copier/coller
    if missing_codes:
        sorted_missing_for_copy = sorted(missing_codes, key=sort_dept_codes)
        print(f"\n📋 Codes manquants (pour copier/coller):")
        print(f"   {', '.join(sorted_missing_for_copy)}")

if __name__ == '__main__':
    main()
