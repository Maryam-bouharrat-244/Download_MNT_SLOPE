# 🔍 Guide Complet de Validation MNT

## 📋 Vue d'ensemble

Pour un projet sérieux, il est **CRÍITIQUE** de valider que chaque MNT est correct. Ce guide vous explique comment procéder.

## 🎯 Options de validation

### Option 1: Validation sélective (RECOMMANDÉ pour commencer)
**Utilisation:** Pour tester quelques départements avant de tout valider

```powershell
cd "C:\Users\marya\Downloads\projet test"
streamlit run mnt_app.py
```

**Avantages:**
- ✅ Interface graphique interactive
- ✅ Validation une à une
- ✅ Pas besoin de tout télécharger
- ✅ Peut s'arrêter et reprendre

**Processus:**
1. Sélectionnez un département
2. Cliquez "🚀 Générer MNT VRT"
3. Vérifiez le résultat
4. Téléchargez le VRT

**Vérifications automatiques:**
```
✅ Fichiers ASC trouvés
✅ En-têtes valides
✅ Coordonnées valides
✅ NODATA correct (dynamique par dept)
```

### Option 2: Validation complète (production)
**Utilisation:** Pour générer et valider TOUS les départements en batch

```powershell
Double-cliquez: C:\Users\marya\Downloads\projet test\VALIDER_TOUS_MNT.bat
```

OU en PowerShell:

```powershell
cd "C:\Users\marya\Downloads\projet test"
python validate_all_mnt.py
```

**Avantages:**
- ✅ Traite tous les 96 départements
- ✅ Validation automatique complète
- ✅ Génère un rapport détaillé

**Inconvénients:**
- ❌ Prend 48-72 heures
- ❌ Consomme 100-200 GB d'espace disque
- ❌ Connexion Internet stable requise

## 📊 Étapes de validation

### 1️⃣ Téléchargement
```
Status: ✅ OK / ❌ FAIL
Vérifie:
  • URL valide
  • Fichier 7z téléchargé
  • Taille correcte
```

### 2️⃣ Extraction
```
Status: ✅ OK / ❌ FAIL / ⏭️ SKIP (déjà extrait)
Vérifie:
  • Archive 7z valide
  • Structure RGEALTI présente
  • Dossier "1_DONNEES_LIVRAISON_*"
  • Dossier "RGEALTI_MNT_5M_ASC_LAMB93_IGN69_D*"
```

### 3️⃣ Recherche fichiers ASC
```
Status: ✅ OK / ❌ FAIL
Vérifie:
  • Au moins 1 fichier .asc
  • Généralement ~200-300 fichiers par département
  • Noms au format: RGEALTI_FXX_AAAA_BBBB_MNT_LAMB93_IGN69.asc
```

### 4️⃣ Création VRT
```
Status: ✅ OK / ❌ FAIL
Vérifie:
  • En-têtes ASC valides
  • Coordonnées Lambert93 valides
  • Dimensions correctes
  • NODATA_value lu dynamiquement
  • Fichier XML bien formé
```

### 5️⃣ Validation VRT
```
Status: ✅ OK / ❌ FAIL
Vérifie:
  ✅ Format XML valide
  ✅ Structure VRT valide
  ✅ Projection Lambert93 présente
  ✅ EPSG:2154 ou IGN69 présent
  ✅ NoDataValue défini
  ✅ NODATA correct
  ✅ Sources présentes (SimpleSource + SourceFilename)
```

## 🔧 Structure des fichiers générés

### Après téléchargement et extraction:
```
C:\Users\marya\Downloads\
├── mnt_work/
│   ├── RGEALTI_D1/              ← Département 1 (Ain)
│   │   ├── RGEALTI_D1.7z        ← Archive source (~1.5 GB)
│   │   └── RGEALTI_2-0_5M_ASC.../
│   │       └── RGEALTI/
│   │           └── 1_DONNEES_LIVRAISON_.../
│   │               └── RGEALTI_MNT_5M_ASC_LAMB93_IGN69_D001/
│   │                   ├── *.asc (200+ fichiers)
│   │                   └── *.prj
│   ├── RGEALTI_D2/
│   ├── RGEALTI_D3/
│   ...
│   └── RGEALTI_D95/
│
├── MNT_D1_Ain.vrt               ← VRT généré (149 KB)
├── MNT_D2_Aisne.vrt
├── MNT_D3_Allier.vrt
...
└── MNT_D95_Yonne.vrt
```

## 📄 Rapport de validation

**Localisation:** `C:\Users\marya\Downloads\mnt_logs\validation_report_YYYYMMDD_HHMMSS.csv`

**Colonnes du rapport:**
```
timestamp        | 2026-03-10 14:23:45
dept_code        | 1
dept_name        | Ain
step             | DOWNLOAD / EXTRACTION / ASC_SEARCH / VRT_CREATION / VRT_VALIDATION
status           | ✅ OK / ❌ FAIL / ⏭️ SKIP
message          | Détails de chaque étape
```

**Exemple de rapport:**
```
timestamp,dept_code,dept_name,step,status,message
2026-03-10 14:23:45,1,Ain,DOWNLOAD,OK,1234.5 MB
2026-03-10 14:25:30,1,Ain,EXTRACTION,OK,
2026-03-10 14:25:32,1,Ain,ASC_SEARCH,OK,272 fichiers
2026-03-10 14:25:45,1,Ain,VRT_CREATION,OK,272 tuiles, 149.9 KB
2026-03-10 14:25:46,1,Ain,VRT_VALIDATION,OK,Tous les contrôles passed
...
```

## ✅ Vérifications supplémentaires dans QGIS

Après génération du VRT, ouvrez-le dans QGIS et vérifiez:

### 1. Chargement correct
```
Oublier à vérifier:
✅ Couche s'affiche sans erreur
✅ Données visibles
✅ Pas de trous ou pixels manquants
```

### 2. Statistiques
```
Clic droit → Propriétés → Histogramme
✅ Min et Max raisonnables (ex: 400-1600m pour montagne)
✅ Pas de valeurs extrêmes anormales
✅ NODATA correctement identifié
```

### 3. Projection
```
Projet → Propriétés → Système de coordonnées
✅ EPSG:2154 (Lambert93)
✅ Unité: mètres
✅ Localisation: France métropolitaine
```

### 4. Géométrie
```
Mesurer une distance
✅ Distances correctes en mètres
✅ Aucune déformation visible
```

## 🚨 Erreurs courantes et solutions

### Erreur: "Aucun fichier ASC trouvé"
```
Cause: Extraction échouée ou structure incorrecte
Solution:
1. Vérifiez mnt_work\RGEALTI_D*\
2. Supprimez le dossier et retéléchargez
3. Vérifiez l'espace disque disponible
```

### Erreur: "NODATA invalide (-99 au lieu de -99999)"
```
Cause: Fichiers source ont différentes valeurs NODATA
Solution: ✅ CORRIGÉ - Lire dynamiquement depuis en-tête
(Version corrigée du 9 mars 2026)
```

### Erreur: "Timeout de téléchargement"
```
Cause: Connexion Internet lente ou instable
Solution:
1. Relancez le script
2. Augmentez TIMEOUT_DOWNLOAD en config
3. Téléchargez un département à la fois
```

### Erreur: "Espace disque insuffisant"
```
Cause: Chaque département = 1-2 GB
Solution:
1. Supprimez les fichiers 7z après extraction (
CLEAR_TMP_AFTER_VRT = True)
2. Utilisez un disque externe
3. Validez un département à la fois
```

## 💾 Gestion de l'espace disque

### Estimation
```
Par département:
  Archive 7z:     1.0-2.0 GB
  Fichiers ASC:   0.5-1.5 GB (après extraction)
  VRT généré:     0.1-0.2 MB
  Total:          1.5-3.5 GB

Pour 96 départements:
  Minimum:        144 GB
  Recommandé:     200-300 GB
```

### Strategies d'économie
```
Option 1: Conserver archives (pour futur)
  - Garder les 7z après extraction
  - Libère: VRT seul = 16 MB pour 96 depts

Option 2: Supprimer après génération
  - Effacer 7z et fichiers ASC
  - Garder: VRT uniquement = 16 MB total
  - Inconvénient: Peut pas régénérer

Option 3: Valider progressivement
  - 1 département à la fois
  - Supprimer entre chaque traitement
  - Recommandé pour débute
```

## 📈 Performance et timing

### Par département
```
Téléchargement:  8-15 minutes  (vitesse Internet)
Extraction:      2-5 minutes   (vitesse disque)
Recherche ASC:   < 1 minute
Création VRT:    1-3 minutes   (nombre de tuiles)
Validation:      < 1 minute
───────────────────────────────
Total/dept:      12-25 minutes (moyenne 18 min)
```

### Pour tous les départements
```
96 depts × 18 min/dept = 1728 minutes
= 28.8 heures (minimum)
= 48-72 heures (réaliste avec connexion)
```

## 🎯 Plan de validation recommendation

### Phase 1: Tests (1-2 jours)
```
1. Validez 5-10 petits départements via UI Streamlit
2. Ouvrez les VRT dans QGIS
3. Vérifiez les statistiques
4. Confirmez pas d'erreurs
```

### Phase 2: Validation complète (3 jours)
```
1. Lancez validate_all_mnt.py
2. Monitoring des logs
3. Vérifiez le rapport final
4. Archivez les VRT
```

### Phase 3: Utilisation production
```
1. Mettez à disposition les VRT
2. Importez dans votre projet SIG
3. Effectuez analyses géospatiales
```

## 📞 Support

### Fichiers d'aide
- `README_APP.md` - Documentation application
- `config.py` - Configuration paramètres
- mnt_logs/ - Rapports détaillés

### Contacts/Ressources
- IGN (Données): https://data.geopf.fr/
- QGIS (Visualisation): https://www.qgis.org/
- GDAL (Traitement): https://gdal.org/

---

**Bon travail de validation! 🗺️🔍**
